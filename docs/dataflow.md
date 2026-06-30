# Data Flow

## Data Models

### Prisma Schema Overview

Source: [`prisma/schema.prisma`](prisma/schema.prisma)

The Prisma client is generated to `src/generated/prisma`. The datasource provider is `postgresql`.

#### Organisation
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| name | String | |
| anthropicApiKeyEnc | String? | AES-256-GCM encrypted Anthropic API key (IV+authTag+ciphertext, base64). Never returned to client. |
| anthropicKeyHint | String? | Obscured hint shown to MANAGER on install page (e.g. `sk-ant-api0...abcd`). |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

Relations: `memberships`, `teams`, `projects`, `prompts`, `activityEvents`, `intelligence`, `intelligenceHighlights`, `auditEntries`, `memberDailyTime`, `productiveRules`, `executiveSummaries`, `invitations`, `githubInstallations`, `userTokens`, `readinessSnapshots`, `codeHealthSnapshots`

#### User
Identity and credentials only. Organisation, role, and team assignment are in `Membership`. The `role`, `teamId`, `isLineManager`, and `organisationId` columns were dropped in PM6 (migration `20260622000001_drop_user_legacy_cols`).

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| email | String @unique | |
| name | String | |
| passwordHash | String | bcrypt hash |
| isActive | Boolean @default(true) | login lockout |
| failedLogins | Int @default(0) | lockout counter |
| lockedUntil | DateTime? | null = not locked |
| sessionVersion | Int @default(0) | incremented on forced re-login |
| bio | String? | |
| jobTitle | String? | |
| location | String? | |
| hasOnboarded | Boolean @default(false) | tracks whether user has completed onboarding flow; read by AppShell server component and passed to AppShellClient as prop |
| tenantKey | String? | |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

#### Membership
**Sole source of truth for role, team, and org assignment.** One row per `(user, organisation)` pair. `withAuthScoped` reads this table on every authenticated request to verify that the JWT's `activeOrganisationId` claim corresponds to a real membership; the row is the credential and the RBAC authority. Backfilled atomically by the PM2 migration; runtime writes added in PM3 (signup creates User+Membership in a `$transaction`; management routes write `role`/`teamId`/`isLineManager` exclusively to Membership). The `User.role/teamId/isLineManager/organisationId` columns were dropped in PM6.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | cuid primary key |
| userId | String | FK → User, onDelete: Cascade; part of composite unique with organisationId |
| organisationId | String | FK → Organisation, onDelete: Cascade |
| role | Role @default(MEMBER) | source of `ctx.role` post-PM3 |
| teamId | String? | nullable FK → Team, onDelete: SetNull; source of `ctx.teamId` post-PM3 |
| isLineManager | Boolean @default(false) | source of `ctx.isLineManager` post-PM3 |
| createdAt | DateTime @default(now()) | login picks user's first Membership by `createdAt ASC` |
| updatedAt | DateTime @updatedAt | |
| status | MembershipStatus @default(ACTIVE) | PM5: `ACTIVE` (full access) or `PENDING` (invite sent, no access). Added in migration `20260621203926_membership_status`. |

@@unique([userId, organisationId])
@@index([userId])
@@index([organisationId])
@@index([userId, status]) — PM5

##### Invariants (PM6)
- `Membership.count() === User.count()` (PM2 backfill invariant; signup keeps it true via `$transaction`).
- `Membership` is the **sole authority** for `role`, `teamId`, and `isLineManager`. The corresponding `User` columns no longer exist (dropped in PM6).
- `withAuthScoped` returns `null` if no `Membership(session.user.id, session.user.activeOrganisationId)` row exists. The composite unique index is the lookup key.
- `withAuthScoped` also returns `null` if the matching Membership row has `status !== "ACTIVE"`. A PENDING membership grants no authenticated access (PM5).

##### Auth request flow (PM3)
1. NextAuth's `auth()` decodes and signature-verifies the JWT.
2. `withAuthScoped` reads `session.user.id` (from verified `token.sub`) and `session.user.activeOrganisationId` (the hint).
3. The existing sessionVersion drift gate fires if the DB version > JWT version.
4. `db.membership.findUnique({ where: { userId_organisationId: { userId, organisationId: activeOrganisationId } } })`.
5. **PM5 status gate**: if `membership.status !== "ACTIVE"` → returns null (→ 401). PENDING members cannot access any protected route.
6. If null (no row) → caller returns 401. Otherwise → return `AuthContext` populated from the row.

#### Team
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| name | String | |
| description | String? | |
| timeTrackingEnabled | Boolean @default(false) | gates /api/ingest/time |
| aiUsesTime | Boolean @default(false) | enriches narration prompt |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

#### Project
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| name | String | |
| description | String? | |
| clientName | String? | |
| status | ProjectStatus @default(ACTIVE) | ACTIVE / PAUSED / ARCHIVED |
| teamId | String | FK → Team |
| agentTokenHash | String? | legacy bcrypt hash — project-level token |
| agentTokenPreview | String? | last 4 chars for display |
| tokenLastRotated | DateTime? | |
| previousTokenHash | String? | grace-window support |
| previousTokenExpiresAt | DateTime? | grace window expiry |
| devTokenBudget | Int? | visibility-only dev Claude Code token budget |
| githubRepoFullName | String? | e.g. "org/repo" |
| githubInstallationId | String? | |
| repoMetadata | Json? | fetched from GitHub API |
| repoSnapshot | Json? | top-level tree + key config excerpts |
| repoContextRefreshedAt | DateTime? | |
| repoContextStatus | RepoContextStatus @default(NONE) | NONE / LINKED / REFRESHING / ERROR |
| repoContextError | String? | last error message (max 500 chars) |
| contextBranchBaselineSha | String? | baseline commit SHA for drift detection; set by POST /drift/baseline |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

#### Prompt
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| pNumber | Int | prompt library number (e.g. P34) |
| title | String | |
| category | String? | context / feature / ops / review / testing / docs |
| body | String | full prompt text |
| fingerprint | String | first 200 chars tokenised, for matching |
| isActive | Boolean @default(true) | |
| createdBy | String? | FK → User (nullable, onDelete: SetNull) |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

@@unique([organisationId, pNumber])

#### ActivityEvent
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| userId | String? | FK → User (nullable, onDelete: SetNull) |
| kind | EventKind | CLAUDE_HOOK / MANUAL_STATUS |
| pNumberDetected | Int? | matched prompt P-number |
| promptId | String? | FK → Prompt |
| sessionExcerpt | String? | last 1500 chars of session (redacted) |
| filesChanged | String[] | |
| gitSummary | String? | redacted git log |
| gitCommitSha | String? | |
| manualText | String? | redacted manual status text |
| hookSource | String? | UserPromptSubmit / Stop / etc. |
| feedSummary | String? | AI one-liner written async after Stop event (Anthropic Haiku primary, free model fallback) |
| redactionCount | Int @default(0) | number of redactions applied |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| ingestedAt | DateTime @default(now()) | |
| claudeInputTokens | Int? | populated by Stop hook |
| claudeOutputTokens | Int? | |
| claudeCacheCreateTokens | Int? | |
| claudeCacheReadTokens | Int? | |
| claudeModel | String? | e.g. "claude-sonnet-4-6" |
| claudeSpendUSD | Float? | pre-computed cost (model-aware) |
| sourceMessageUuid | String? | dedup key — uuid of last transcript message |
| sessionDurationSeconds | Int? | Claude Code session span (seconds); lastTimestamp − firstTimestamp from transcript delta; Stop events only |

@@unique([projectId, sourceMessageUuid]) — Postgres NULLs treated as distinct, so existing null rows don't conflict.

#### Intelligence
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| triggeringEventId | String | ActivityEvent.id that triggered this |
| inputHash | String | SHA-256 of canonical input fields |
| headline | String? | 8–12 word one-liner (added migration 20260614) |
| narration | String | 3–4 sentence plain-English narration — **never dropped**; exec summary route + dashboard card read this directly |
| stage | String? | early / mid / hardening / blocked |
| riskLevel | String @default("LOW") | LOW / MEDIUM / HIGH |
| riskFocus | String? | short phrase describing risk (null if LOW) |
| modelUsed | String | "llama-3.3-70b-versatile" |
| inputTokens | Int @default(0) | |
| outputTokens | Int @default(0) | |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| generatedAt | DateTime @default(now()) | |

@@unique([projectId, inputHash])

#### IntelligenceHighlight
One row per highlight bullet. Structurally enforced: only `sourceEventId` values from the narration input window can be persisted (`filterHighlights` in `src/lib/narrate.ts` validates pre-insert). Added in migration `20260614000002_add_intelligence_highlights`.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| intelligenceId | String | FK → Intelligence (onDelete: Cascade) |
| text | String | one plain-English highlight sentence |
| sourceEventId | String | validated against input event set — hallucinated IDs never reach DB |
| sourceEventKind | String | EventKind of the source event (CLAUDE_HOOK / MANUAL_STATUS) |
| sourceCommitSha | String? | gitCommitSha of source event, or null |
| organisationId | String | FK → Organisation |
| createdAt | DateTime @default(now()) | |

@@index([intelligenceId])
@@index([organisationId])

#### ReadinessSnapshot
One row per scan invocation. Stores the output of `scanMarkersInDir` + `readCoveragePct`. Up to 90 rows per project are loaded to build the OLS forecast. Added in migration `20260614000003_add_readiness_snapshot`.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| organisationId | String | FK → Organisation |
| markerCount | Int | sumMarkerDetail() result |
| markerDetail | Json | `{ todo, fixme, skippedTests, stubbed, testFileCount }` — `testFileCount` added in R2; old rows have no key, widget uses `?? 0` |
| coveragePct | Float? | total.lines.pct from coverage-summary.json; null = not yet measured |
| scannedAt | DateTime @default(now()) | |

@@index([projectId, scannedAt])
@@index([organisationId])

#### SecurityScanRun
One row per security scan invocation. Stores metadata about a completed Semgrep CE / gitleaks / osv-scanner run. Added in migration `20260615000002_add_security_findings`.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| organisationId | String | FK → Organisation |
| scannedAt | DateTime @default(now()) | |
| scanSource | ScanSource @default(CENTRAL) | reuses existing enum |
| toolsRun | Json | array of tool names that were executed |
| findingCount | Int @default(0) | total findings across all tools |

@@index([projectId, scannedAt])
@@index([organisationId])

#### SecurityFinding
One finding row per issue discovered during a security scan. Added in migration `20260615000002_add_security_findings`.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| scanRunId | String | FK → SecurityScanRun (onDelete: Cascade) |
| projectId | String | FK → Project (onDelete: Cascade) |
| organisationId | String | FK → Organisation |
| tool | String | "semgrep" / "gitleaks" / "osv-scanner" |
| ruleId | String? | Semgrep/gitleaks rule ID; null for osv-scanner |
| severity | SecuritySeverity | CRITICAL / HIGH / MEDIUM / LOW / INFO |
| message | String | human-readable finding description |
| file | String? | relative file path, if applicable |
| line | Int? | line number in file, if applicable |

@@index([projectId, organisationId])

#### ContextDriftAssessment
One row per drift assessment trigger per project. Stores the outcome of comparing committed code against the last baseline SHA using the GitHub Compare API and Groq AI analysis.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| organisationId | String | FK → Organisation |
| tenantKey | String? | |
| status | DriftAssessmentStatus @default(PENDING) | PENDING / RUNNING / COMPLETE / ERROR |
| triggeredBy | DriftTriggerSource | ON_DEMAND / VOLUME / MAJOR_EVENT / SYSTEM |
| contextSource | String | "context_builds" / "docs_on_default" / "none" |
| baselineSha | String? | commit SHA used as baseline |
| headSha | String? | commit SHA at assessment time |
| changedFiles | String[] | list of files changed between baseline and head |
| diffTruncated | Boolean @default(false) | true if diff exceeded token limit |
| healthScore | Int? | 0–100 composite score; null until COMPLETE |
| riskLevel | DriftRiskLevel? | GREEN / AMBER / RED; null until COMPLETE |
| findings | Json? | array of DriftFinding objects (type, area, doc, description, severity, confidence) |
| findingsCount | Int? | total findings count |
| aiTokensUsed | Int? | total tokens consumed by the AI analysis |
| costUSD | Float? | estimated USD cost of AI analysis |
| error | String? | error message if status = ERROR |
| assessedAt | DateTime @default(now()) | |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

@@index([projectId, assessedAt])
@@index([organisationId])

### TechnicalDebtScan

One record per scan invocation. State machine: PENDING → RUNNING → COMPLETE (or ERROR).

| Field | Type | Purpose |
|---|---|---|
| `id` | `String` | CUID primary key |
| `projectId` | `String` | Parent project (CASCADE delete) |
| `organisationId` | `String` | Tenancy scope |
| `status` | `TechDebtScanStatus` | PENDING / RUNNING / COMPLETE / ERROR |
| `currentStep` | `TechDebtStep?` | Current pipeline step; null when PENDING or ERROR |
| `sonarProjectKey` | `String?` | SonarQube project key (Phase B) |
| `qualityGate` | `String?` | PASS / FAIL / N/A (Phase B) |
| `reliabilityRating` | `String?` | A–E (Phase B) |
| `securityRating` | `String?` | A–E (Phase B) |
| `maintainabilityRating` | `String?` | A–E (Phase B) |
| `techDebtMinutes` | `Int?` | SQALE technical debt in minutes (Phase B) |
| `issueCount` | `Int?` | Total SonarQube issues BLOCKER+CRITICAL+MAJOR (Phase B) |
| `findings` | `Json?` | AI synthesis findings array (Phase D) |
| `findingsCount` | `Int?` | Total findings count |
| `criticalCount` | `Int?` | SonarQube BLOCKER severity count (Phase B); UI note: "Critical" in Sonar = highCount |
| `highCount` | `Int?` | SonarQube CRITICAL severity count (Phase B); UI note: "High" in Sonar = criticalCount |
| `debtScore` | `Int?` | Composite 0–100 score (Phase D) |
| `aiTokensUsed` | `Int?` | Tokens used by AI synthesis (Phase D) |
| `costUSD` | `Float?` | AI synthesis cost (Phase D) |
| `error` | `String?` | Error message when status = ERROR |
| `scannedAt` | `DateTime` | Timestamp; set to completion time on COMPLETE |
| `createdAt` | `DateTime` | Row creation (used for stale-run detection) |
| `updatedAt` | `DateTime` | Last update |

@@index([projectId, createdAt])
@@index([organisationId])

#### Technical Debt Scan — SYNTHESISING Step Data Flow (Phase D)

After the SONAR step completes, the orchestrator enters the SYNTHESISING step:

1. **Write raw Sonar data** — `blockerCount`, `criticalCount`, `majorCount`, `issueCount`, `qualityGate`, reliability/security/maintainability ratings, `techDebtMinutes` are written to the scan row at the start of SYNTHESISING, before any AI call. This ensures raw metrics survive even if synthesis fails.
2. **Query latest SecurityScanRun** — `db.securityScanRun.findFirst({ where: { projectId, organisationId }, orderBy: { scannedAt: "desc" }, include: { findings: true } })` — org+project scoped, most recent run only.
3. **Empty evidence fast-path** — if both `sonarIssues` (from `SonarEngineResult.issues`) and `securityFindings` are empty, `synthesiseDebtFindings` returns `{ findings: [], score: 100 }` without calling the AI.
4. **Call `synthesiseDebtFindings({ organisationId, sonarIssues, securityFindings, detectedFrameworks })`** — ceiling-gated via `isCeilingExceeded` before the AI call. Builds a prompt from real Sonar issues + SecurityFindings + detected frameworks. Parses AI JSON response.
5. **Anti-hallucination guards** — every AI finding is filtered: (a) `evidence.files` must be non-empty and at least one file must match a file from real Sonar issues or SecurityFindings (realFiles Set guard); (b) `priority` must be exactly one of `P1`/`P2`/`P3`/`P4` — others are dropped.
6. **On failure** (ceiling exceeded or parse error) → scan marked ERROR; raw Sonar data written in step 1 is preserved.
7. **On success** → `computeDebtScore(findings)` produces the deterministic `debtScore` → write COMPLETE with `findings (Json)`, `findingsCount`, `debtScore`, `aiTokensUsed`, `costUSD`.

**Field distinction**: `issueCount` = total Sonar issues (written at SYNTHESISING step 1); `findingsCount` = count of AI P1–P4 findings (written at COMPLETE in step 7). These are distinct numbers.

#### CodeHealthSnapshot
One row per SonarQube scan invocation. Stores the output of `fetchSonarMetrics` after a `runSonarScanner` call. Added in migration `20260614000004_add_code_health_snapshot`; `scanSource` added in `20260615000001_add_code_health_scan_source`.

| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| organisationId | String | FK → Organisation |
| sonarProjectKey | String | `org-{orgId}-proj-{projectId}` for CENTRAL; `SONAR_PROJECT_KEY` for EDGE |
| qualityGate | String | "PASS" / "FAIL" / "N/A" |
| reliabilityRating | String | "A"–"E" or "N/A" |
| securityRating | String | "A"–"E" or "N/A" |
| maintainabilityRating | String | "A"–"E" or "N/A" |
| coveragePct | Float? | null = not measured |
| duplicationPct | Float? | null = not measured |
| scanSource | ScanSource @default(CENTRAL) | CENTRAL = server fetched repo tarball; EDGE = server scanned its own cwd |
| scannedAt | DateTime @default(now()) | |

@@index([projectId, scannedAt])
@@index([organisationId])

---

#### AuditLogEntry
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| userId | String? | FK → User (nullable, onDelete: SetNull) |
| action | String | e.g. LOGIN_FAILURE, CREATE_PROJECT, REPO_LINK |
| subjectId | String? | ID of the affected resource |
| meta | Json? | arbitrary structured context |
| ipAddress | String? | from x-forwarded-for or x-real-ip |
| organisationId | String | FK → Organisation |
| at | DateTime @default(now()) | |

#### ProjectMember
| Field | Type | Notes |
|-------|------|-------|
| projectId | String | composite PK |
| userId | String | composite PK |
| joinedAt | DateTime @default(now()) | |

@@id([projectId, userId])

#### TimeTrackingConsent
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| userId | String @unique | FK → User (onDelete: Cascade) |
| notifiedAt | DateTime @default(now()) | |
| acknowledgedAt | DateTime? | null = not yet consented |
| consentVersion | Int @default(1) | v1 = aggregate only; v2 = includes top-app names |

#### MemberDailyTime
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| userId | String | FK → User (onDelete: Cascade) |
| day | DateTime | UTC midnight of the day |
| timezone | String | member's local timezone |
| workedSeconds | Int @default(0) | total at-keyboard (not-afk) |
| productiveSeconds | Int | |
| unproductiveSeconds | Int @default(0) | |
| idleSeconds | Int @default(0) | retained for schema compat, no longer written |
| offlineSeconds | Int @default(0) | retained for schema compat, no longer written |
| topApps | Json? | top 2 productive + top 2 unproductive apps; null until v2 consent |
| lastIngestAt | DateTime @default(now()) | |
| source | String @default("activitywatch") | |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |

@@unique([userId, day])

#### ProductiveAppRule
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| pattern | String | app name pattern |
| matchType | MatchType | EXACT / GLOB / REGEX |
| category | String? | claude / ide / terminal / vcs / browser-dev / docs / design / comms |
| isProductive | Boolean @default(true) | |
| scope | RuleScope | GLOBAL / TEAM |
| teamId | String? | null for GLOBAL rules |
| isActive | Boolean @default(true) | |
| createdBy | String? | FK → User (onDelete: SetNull) |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

#### ExecutiveSummary
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| body | String | 5–8 sentence paragraph |
| confidence | Float? | 0.0–1.0 parsed from model output |
| generatedBy | String? | FK → User (onDelete: SetNull) |
| modelUsed | String | "llama-3.3-70b-versatile" |
| inputTokens | Int? | |
| outputTokens | Int? | |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| generatedAt | DateTime @default(now()) | |

#### Invitation
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| invitedEmail | String | |
| teamId | String? | nullable (org-level invite) |
| role | Role | |
| status | InvitationStatus @default(PENDING) | PENDING / ACCEPTED / DECLINED (DECLINED added in PM5 migration `20260621205617_invitation_status_declined`) |
| invitedBy | String | FK → User |
| tenantKey | String? | |
| organisationId | String | FK → Organisation |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

#### AgentToken
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| projectId | String | FK → Project (onDelete: Cascade) |
| userId | String? | null for legacy backfilled tokens |
| createdById | String? | null for legacy backfilled tokens |
| label | String @default("") | display label |
| tokenHash | String | bcrypt(AGENT_TOKEN_PEPPER + raw, 12) |
| tokenPreview | String | last 4 chars — fast lookup hint |
| createdAt | DateTime @default(now()) | |
| revokedAt | DateTime? | null = active |
| revokedById | String? | |

#### UserToken
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| userId | String @unique | FK → User (onDelete: Cascade) |
| organisationId | String | FK → Organisation |
| tokenHash | String | bcrypt(AGENT_TOKEN_PEPPER + raw, 12) |
| tokenPreview | String | last 4 chars |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |
| tenantKey | String? | |

#### GithubInstallation
| Field | Type | Notes |
|-------|------|-------|
| id | String @id @default(cuid()) | |
| organisationId | String | FK → Organisation (onDelete: Cascade) |
| installationId | String | GitHub installation ID |
| accountName | String | GitHub account login |
| status | GithubInstallationStatus @default(ACTIVE) | ACTIVE / INVALID |
| createdAt | DateTime @default(now()) | |
| updatedAt | DateTime @updatedAt | |

@@unique([organisationId, installationId])

> **Note**: The detailed ingest pipeline documentation (step-by-step with `Source:` citations) begins at [Ingest Pipeline — Claude Code Hook Events](#ingest-pipeline--claude-code-hook-events-1) below, after the Database Indexes and Enums sections. The content above line 289 in earlier versions of this file was a duplicate. The canonical version follows the Data Model section.

---

### Database Indexes

Source: [`prisma/schema.prisma`](prisma/schema.prisma)

| Model | Index / Unique | Fields |
|-------|---------------|--------|
| Organisation | @@index | [name] |
| Membership | @@unique | [userId, organisationId] |
| Membership | @@index | [userId] |
| Membership | @@index | [organisationId] |
| Membership | @@index | [userId, status] — PM5 |
| Team | @@index | [timeTrackingEnabled] |
| Team | @@index | [organisationId] |
| Project | @@index | [status] |
| Project | @@index | [teamId, status] |
| Project | @@index | [organisationId] |
| Prompt | @@unique | [organisationId, pNumber] |
| Prompt | @@index | [isActive] |
| Prompt | @@index | [organisationId] |
| ActivityEvent | @@unique | [projectId, sourceMessageUuid] |
| ActivityEvent | @@index | [projectId, ingestedAt] |
| ActivityEvent | @@index | [userId, ingestedAt] |
| ActivityEvent | @@index | [projectId, userId, ingestedAt] |
| ActivityEvent | @@index | [projectId, kind, ingestedAt] |
| ActivityEvent | @@index | [organisationId] |
| Intelligence | @@unique | [projectId, inputHash] |
| Intelligence | @@index | [projectId, generatedAt] |
| Intelligence | @@index | [organisationId] |
| AuditLogEntry | @@index | [userId, at] |
| AuditLogEntry | @@index | [subjectId, at] |
| AuditLogEntry | @@index | [action, at] |
| AuditLogEntry | @@index | [at] |
| AuditLogEntry | @@index | [organisationId] |
| ProjectMember | @@index | [userId] |
| TimeTrackingConsent | @@index | [acknowledgedAt] |
| MemberDailyTime | @@unique | [userId, day] |
| MemberDailyTime | @@index | [userId, day] |
| MemberDailyTime | @@index | [organisationId] |
| ProductiveAppRule | @@index | [scope, isActive] |
| ProductiveAppRule | @@index | [teamId, isActive] |
| ProductiveAppRule | @@index | [organisationId] |
| ExecutiveSummary | @@index | [projectId, generatedAt] |
| ExecutiveSummary | @@index | [organisationId] |
| Invitation | @@index | [invitedEmail, status] |
| Invitation | @@index | [teamId] |
| Invitation | @@index | [organisationId] |
| AgentToken | @@index | [projectId, revokedAt] |
| AgentToken | @@index | [projectId, tokenPreview] |
| AgentToken | @@index | [userId] |
| UserToken | @@index | [tokenPreview] |
| UserToken | @@index | [organisationId] |
| GithubInstallation | @@unique | [organisationId, installationId] |
| GithubInstallation | @@index | [organisationId] |
| CodeHealthSnapshot | @@index | [projectId, scannedAt] |
| CodeHealthSnapshot | @@index | [organisationId] |
| SecurityScanRun | @@index | [projectId, scannedAt] |
| SecurityScanRun | @@index | [organisationId] |
| SecurityFinding | @@index | [projectId, organisationId] |
| ContextDriftAssessment | @@index | [projectId, assessedAt] |
| ContextDriftAssessment | @@index | [organisationId] |

---

### Enums

Source: [`prisma/schema.prisma`](prisma/schema.prisma)

| Enum | Values |
|------|--------|
| Role | MANAGER, LINE_MANAGER, MEMBER |
| ProjectStatus | ACTIVE, PAUSED, ARCHIVED |
| EventKind | CLAUDE_HOOK, MANUAL_STATUS |
| MatchType | EXACT, GLOB, REGEX |
| RuleScope | GLOBAL, TEAM |
| RepoContextStatus | NONE, LINKED, REFRESHING, ERROR |
| InvitationStatus | PENDING, ACCEPTED, DECLINED (DECLINED added in PM5) |
| MembershipStatus | PENDING, ACTIVE (added in PM5 migration `20260621203926_membership_status`) |
| GithubInstallationStatus | ACTIVE, INVALID |
| SecuritySeverity | CRITICAL, HIGH, MEDIUM, LOW, INFO |
| DriftAssessmentStatus | PENDING, RUNNING, COMPLETE, ERROR |
| DriftTriggerSource | ON_DEMAND, VOLUME, MAJOR_EVENT, SYSTEM |
| DriftRiskLevel | GREEN, AMBER, RED |

---

## Ingest Pipeline — Claude Code Hook Events

### Event Body Shape

Source: [`src/app/api/ingest/event/route.ts`](src/app/api/ingest/event/route.ts:17)

Zod schema `BodySchema`:

| Field | Type | Validation |
|-------|------|------------|
| projectId | string | min(1) |
| userIdHint | string (email) | optional — used only when token carries no userId |
| kind | "CLAUDE_HOOK" \| "MANUAL_STATUS" | enum |
| hookSource | string | optional — e.g. "UserPromptSubmit", "Stop" |
| sessionExcerpt | string | optional — last ~1500 chars of session transcript |
| filesChanged | string[] | optional |
| gitSummary | string | optional — git log output |
| gitCommitSha | string | optional |
| manualText | string | optional — for MANUAL_STATUS kind |
| claudeUsage.input | number int ≥0 | optional object |
| claudeUsage.output | number int ≥0 | optional |
| claudeUsage.cacheCreate | number int ≥0 | optional |
| claudeUsage.cacheRead | number int ≥0 | optional |
| claudeUsage.model | string | optional — e.g. "claude-sonnet-4-6" |
| claudeUsage.cost | number ≥0 | optional — pre-computed USD cost |
| sourceMessageUuid | string | optional — dedup key from transcript |
| sessionDurationSeconds | number int ≥0 | optional — Claude Code session span in seconds (lastTimestamp − firstTimestamp from transcript delta); Stop events only; stored idempotently via sourceMessageUuid upsert |

Maximum body size: 256 KB (`MAX_BODY_BYTES = 256 * 1024`).

---

### Ingest Flow Step-by-Step

Source: [`src/app/api/ingest/event/route.ts`](src/app/api/ingest/event/route.ts:40)

1. **Read raw body** (`request.arrayBuffer()`). Reject with 413 if > 256 KB.
2. **Extract Bearer token** from `Authorization` header. Reject 401 if absent or malformed.
3. **Parse JSON body**. Reject 400 on parse failure.
4. **Extract `projectId`** (partial Zod parse). Reject 401 if missing.
5. **HMAC-SHA256 gate** — cheap constant-time compare before bcrypt:
   - Read `x-pulse-signature` header (must be 64 hex chars).
   - Compute `HMAC-SHA256(rawToken, rawBuffer)`.
   - `crypto.timingSafeEqual(expected, provided)`. Reject 401 on mismatch.
6. **Token verification** via [`resolveAgentToken(rawToken, projectId)`](src/lib/resolveAgentToken.ts:20):
   - Queries `AgentToken` table by `(projectId, tokenPreview, revokedAt: null)`.
   - bcrypt-verifies each candidate. On match returns `{ valid: true, userId, tokenId }`.
   - Legacy fallback: queries `Project.agentTokenHash` and calls `verifyTokenWithGrace()`.
   - Reject 401 if no match.
7. **Project lookup** (`db.project.findUnique`). Reject 401 if not found. Reject 403 if `project.status !== "ACTIVE"`.
8. **Rate limit** via [`checkIngestRateLimit(project.id)`](src/lib/ratelimit.ts:34):
   - Uses Upstash Redis sliding window: 60 req/min at 1x, 240/min at 4x.
   - Key prefix: `pulse:ingest:event`. Falls back to allowed=true if Redis not configured.
   - Reject 429 if exceeded.
9. **Full Zod body validation** (`BodySchema.safeParse`). Reject 400 on failure.
10. **Resolve `userId`**:
    - Per-developer tokens carry `userId` directly from `resolveAgentToken`.
    - Legacy tokens (userId: null): if `userIdHint` email present, call `db.user.findFirst({ email, memberships: { some: { organisationId: project.organisationId, status: "ACTIVE" } } })`. Reject 400 `{ error: "user_not_found" }` if hint doesn't match.
    - If no hint and no userId: `userId` stays null.
11. **Redaction** via [`redact()`](src/lib/redact.ts:10) applied to `sessionExcerpt`, `manualText`, `gitSummary`:
    - Strips: env-style secrets (`KEY=value`), JWTs (`eyJ...`), Anthropic keys (`sk-ant-`), OpenAI keys (`sk-` + 20+ chars), AWS keys (`AKIA`/`ASIA`), PEM private keys, URL credentials (`://user:pass@`).
    - Truncates to 1500 chars after redaction.
    - Returns `{ text, count, kinds[] }`.
12. **P-number matching**: calls `matchPNumber(matchInput, activePrompts)` against all `isActive=true` prompts. Sets `pNumberDetected` and `promptId`.
13. **Persist `ActivityEvent`**:
    - If `sourceMessageUuid` present: `db.activityEvent.upsert({ where: { projectId_sourceMessageUuid }, create: eventData, update: {} })` — first write wins.
    - If absent: `db.activityEvent.create({ data: eventData })`.
14. **Fire-and-forget narration**: fetches org Anthropic key via `getOrgAnthropicKey`, then calls `void generateNarration(event, project, traceCtx, anthropicApiKey)` — never blocks the 200 response.
15. **Fire-and-forget feed summary** (Stop events only): if `hookSource === "Stop"` and `sessionExcerpt` present, fetches org Anthropic key via `getOrgAnthropicKey`, calls [`generateFeedSummary(excerpt, files, git, anthropicApiKey)`](src/lib/gemini.ts) (Anthropic Haiku primary, free model fallback, maxOutputTokens: 64). On success writes `feedSummary` to the event via `db.activityEvent.update`.
16. **Respond 200** with `{ id: event.id }`.

---

### Idempotency

Source: [`src/app/api/ingest/event/route.ts`](src/app/api/ingest/event/route.ts:222)

- `ActivityEvent` has `@@unique([projectId, sourceMessageUuid])`.
- When `sourceMessageUuid` is present, the route uses `upsert` with `update: {}` (empty). First write wins; duplicate POSTs are no-ops returning 200.
- When `sourceMessageUuid` is absent, a plain `create` is used.
- PostgreSQL treats `NULL` as distinct in unique constraints — existing null rows never conflict.

---

### Claude Code Session Time Flow

Source: [`.pulse/transcript-delta.mjs`](.pulse/transcript-delta.mjs) · [`.pulse/pulse-send.mjs`](.pulse/pulse-send.mjs) · [`src/lib/session-time.ts`](src/lib/session-time.ts) · [`src/app/projects/[id]/_components/CompletionStatusWidget.tsx`](src/app/projects/[id]/_components/CompletionStatusWidget.tsx)

1. `computeDelta()` extracts `firstTimestamp` / `lastTimestamp` (ISO 8601) from **all** new JSONL lines in the delta (user + assistant lines). The cursor bounds the slice, so each Stop firing's timestamps cover only its own segment.
2. `pulse-send.mjs` computes `sessionDurationSeconds = Math.round((Date.parse(lastTimestamp) − Date.parse(firstTimestamp)) / 1000)` when both values are present and the difference is positive.
3. `sessionDurationSeconds` is included in the Stop POST body alongside `claudeUsage` and `sourceMessageUuid`.
4. The ingest route stores it in `ActivityEvent.sessionDurationSeconds` via the existing `sourceMessageUuid` upsert (`update: {}`). **First write wins** — re-ingesting the same transcript is a silent no-op; session time cannot double-count.
5. `getProjectSessionSeconds(projectId, organisationId, since)` (`src/lib/session-time.ts`) aggregates `SUM(sessionDurationSeconds)` over Stop events in the time window, scoped by `organisationId` (tenancy isolated).
6. Col 4 of `CompletionStatusWidget` renders the total as **"Claude Code session time"** with source label "transcript span". Visible to `LINE_MANAGER` / `MANAGER` only (same `canSeeSpend` gate as `SpendRing`). Formatted by `formatSessionTime()` from `src/lib/session-time.ts`.

**Honest label invariants:**
- Label: always "Claude Code session time" — never "dev time", "total time", or "hours on project".
- The metric is session **span** (first message → last message in the delta), not active typing time. Idle gaps within a session inflate the figure.
- `MemberDailyTime` / `workedSeconds` is **untouched**. Session time is purely additive.
- Consent: capture is implicit in hook installation (same basis as `claudeSpendUSD`). Display gated on `canSeeSpend` (LINE_MANAGER/MANAGER).

---

### User Attribution

Source: [`src/app/api/ingest/event/route.ts`](src/app/api/ingest/event/route.ts:131)

1. Per-developer `AgentToken` rows carry `userId`. When matched, `userId` is taken directly.
2. Legacy tokens carry `userId: null`. In this case:
   - If `userIdHint` (email) is present: `db.user.findFirst({ where: { email: userIdHint, organisationId } })`. Reject 400 `{ error: "user_not_found" }` if no match — event not persisted.
   - If no `userIdHint`: `userId` remains null, event stored anonymously.

---

## Ingest Pipeline — Time Tracking

### Time Event Body Shape

Source: [`src/app/api/ingest/time/route.ts`](src/app/api/ingest/time/route.ts:17)

Zod schema `BodySchema`:

| Field | Type | Validation |
|-------|------|------------|
| projectId | string | optional (absent on UserToken path) |
| userIdHint | string (email) | optional |
| day | string | ISO 8601 UTC midnight — must match `/T00:00:00(\.000)?Z$/` |
| timezone | string | min(1) |
| workedSeconds | number int ≥0 | max 86400 |
| productiveSeconds | number int ≥0 | max 86400 |
| unproductiveSeconds | number int ≥0 | max 86400 |
| topApps.productive | array max 2 | `{ app: string, seconds: int ≥0 }` |
| topApps.unproductive | array max 2 | `{ app: string, seconds: int ≥0 }` |

Invariant: `|productiveSeconds + unproductiveSeconds - workedSeconds| ≤ 2`. Reject 422 `{ reason: "bucket_mismatch" }` on violation.

Privacy gate ([`src/lib/pulse-body-shape.ts`](src/lib/pulse-body-shape.ts)): allowed keys are `projectId`, `userIdHint`, `day`, `timezone`, `workedSeconds`, `productiveSeconds`, `unproductiveSeconds`, `topApps`. `windowTitle`, `appName`, `url` are blocked.

Maximum body size: 64 KB.

---

### Time Ingest Flow

Source: [`src/app/api/ingest/time/route.ts`](src/app/api/ingest/time/route.ts:31)

1. **Read raw body**, check 64 KB limit.
2. **Extract Bearer token** from `Authorization`. Reject 401 if absent.
3. **Parse JSON**. Reject 400 on failure.
4. **HMAC-SHA256 gate** — same constant-time compare as event ingest.
5. **Try UserToken path first**: call [`resolveUserToken(rawToken)`](src/lib/userToken.ts:14):
   - On valid: `handleUserTokenPath` — rate-limit by `userId`; check `team.timeTrackingEnabled`; check `TimeTrackingConsent.acknowledgedAt`; call `upsertDailyTime`.
6. **AgentToken path** (fallback): call `resolveAgentToken(rawToken, projectId)`. Requires `projectId` in body. `handleAgentTokenPath` — check project ACTIVE; rate-limit by `project.id`; check team tracking; resolve userId; check consent; call `upsertDailyTime`.
7. **`upsertDailyTime`**:
   - Validate day format. Reject 422 if invalid.
   - Validate bucket invariant. Reject 422 on violation.
   - Fetch existing `MemberDailyTime` row.
   - MAX-merge each bucket independently: `Math.max(existing, incoming)`.
   - `topApps`: stored only if `consentVersion >= 2`. When merging, use topApps from the row with higher `workedSeconds`.
   - `db.memberDailyTime.upsert({ where: { userId_day }, create: {..., source: "activitywatch"}, update: { workedSeconds, productiveSeconds, unproductiveSeconds, topApps, lastIngestAt } })`.
   - Respond 200 `{ ok: true }`.

---

## Narration Pipeline

### Trigger Conditions

Source: [`src/lib/narrate.ts`](src/lib/narrate.ts:103)

`generateNarration(event, project, traceCtx)` is called fire-and-forget from the ingest route. Three gates run before calling the AI:

1. **Input hash gate**: Computes `SHA-256` over a canonical pipe-delimited string of `pNumberDetected`, `lastCommitSha`, sorted `filesChanged`, `sessionExcerpt`, `gitSummary`, `eventKind`, `repoContextRefreshedAt`. Queries `db.intelligence.findFirst({ where: { projectId }, orderBy: { generatedAt: "desc" }, select: { inputHash } })`. If the latest hash matches → skip (content unchanged).

2. **Cooldown gate**: Checks in-memory `Map<projectId, timestamp>`. If `Date.now() - lastAt < 90_000` ms → skip. Cooldown is set **before** the API call to prevent concurrent burst narrations.

3. **Cost ceiling gate**: `isCeilingExceeded(organisationId)` — aggregates `Intelligence.inputTokens + outputTokens` for the current UTC month, converts to USD at `$3/M input` and `$15/M output`. Blocks if spend ≥ `CLAUDE_MONTHLY_CEILING_USD` env var.

---

### AI Request Flow

Source: [`src/lib/narrate.ts`](src/lib/narrate.ts:143)

1. Fetch recent manual statuses: `db.activityEvent.findMany({ where: { projectId, kind: "MANUAL_STATUS" }, orderBy: { ingestedAt: "desc" }, take: 3, select: { manualText, ingestedAt } })`.

2. Optional time context: if `team.aiUsesTime === true` and `event.userId != null`, fetches today's `MemberDailyTime`. Appends: `"worked Xh Ym | productive Xh Ym (Z%) | unproductive Xh Ym"`. If `topApps` present: `"Apps (today): most active in: ...; time in: ..."`.

3. Optional repo context block: if `project.repoSnapshot != null`, injects `[REPOSITORY CONTEXT]` block containing detected frameworks, top-level tree paths, key config file paths.

4. Assembles user prompt: project name, detected workflow (P-number or "Free workflow"), files changed (up to 10), git summary, session excerpt, manual statuses, time context, repo context.

5. **7-day window fetch** (Phase 7+): `db.activityEvent.findMany({ where: { projectId, ingestedAt: { gte: sevenDaysAgo } }, orderBy: { ingestedAt: "desc" }, take: 20, select: { id, kind, gitCommitSha, gitSummary, sessionExcerpt, filesChanged, manualText, ingestedAt } })`. Replaces the old single `MANUAL_STATUS` fetch. `validEventIds = Set([event.id, ...windowEvents.map(e => e.id)])`. Manual status lines derived by filtering `windowEvents` by `kind === "MANUAL_STATUS"`.

6. System prompt (constant, defined at module level): instructs the model to write in plain English for a non-technical PM. Defines `stage` (`early`/`mid`/`hardening`/`blocked`), `riskLevel` (`LOW`/`MEDIUM`/`HIGH`), `riskFocus`, `headline` (8–12 words). Requires JSON output with keys: `headline`, `narration`, `stage`, `riskLevel`, `riskFocus`, `highlights` (array of `{ text, sourceEventId }` — sourceEventId must be from the events list in the user prompt).

7. **AI API call**: `generateText({ model, system, messages: [{ role: "user", content: userPrompt }], maxOutputTokens: 1024 })` where `model` comes from `getAutoCallModel(anthropicApiKey)` — Anthropic Haiku primary, free model fallback. User prompt includes an explicit events list with IDs so the model can reference valid sourceEventIds.

8. **Parse JSON**: strips markdown code fences. Calls `JSON.parse()`. On failure: logs and returns without writing (`narration` never stored, no highlights). Parse failure is a clean no-op — no crash, no empty state.

9. **Persist `Intelligence`**: `const newIntelligence = await db.intelligence.create({ data: { projectId, triggeringEventId: event.id, inputHash, headline, narration, stage, riskLevel, riskFocus, modelUsed, inputTokens, outputTokens, tenantKey, organisationId } })`. `narration` always stored (never dropped) — exec summary + dashboard card read this directly.

10. **Persist highlights** (Phase 7+): `validHighlights = filterHighlights(parsed.highlights, validEventIds)` — drops any highlight whose `sourceEventId` is not in `validEventIds`. If `validHighlights.length > 0`: `db.intelligenceHighlight.createMany({ data: validHighlights.map(...) })`. Each row records `intelligenceId`, `text`, `sourceEventId`, `sourceEventKind`, `sourceCommitSha`, `organisationId`.

11. **Record metrics**: `recordClaudeTokens(projectId, inputTokens, outputTokens)`.

---

### Data Written

- New `Intelligence` row with: `projectId`, `inputHash`, `headline`, `narration`, `stage`, `riskLevel`, `riskFocus`, `modelUsed`, `inputTokens`, `outputTokens`.
- Zero or more `IntelligenceHighlight` rows linked via `intelligenceId` — only when the AI returns valid highlights with sourceEventIds that pass `filterHighlights`.
- In-memory Prometheus counters: `_claudeInputTokens[projectId]`, `_claudeOutputTokens[projectId]`.

---

## Read Paths — Dashboard & Project Views

### Dashboard Data Queries

Source: [`src/lib/dashboard.ts`](src/lib/dashboard.ts:41)

`fetchDashboardSummary(ctx: AuthContext)` runs six concurrent queries via `Promise.all`:

| Query | Purpose | Key filters |
|-------|---------|-------------|
| `activityEvent.count` | `eventsToday` | `hookSource = "UserPromptSubmit"`, `ingestedAt ≥ todayUTC` |
| `user.findMany` | `scopedMembers` | `isActive: true`; LM adds `teamId` filter |
| `activityEvent.count` | `promptsMatchedToday` | `pNumberDetected IS NOT NULL`, `ingestedAt ≥ todayUTC` |
| `project.count` | `totalActiveProjects` | `status = "ACTIVE"`, `events.some { ingestedAt ≥ IDLE_THRESHOLD_MS ago }` |
| `$queryRaw` | event sparklines | 7-day window; `DATE_TRUNC('day', ingestedAt)`; counts `event_count`, `member_count`, `project_count` |
| `$queryRaw` | prompt match sparklines | 7-day window; `pNumberDetected IS NOT NULL`; counts by day |

After the parallel batch, a 7th query fetches **active members** (last 30 min): `activityEvent.findMany({ userId: { in: memberIds }, ingestedAt ≥ thirtyMinAgo, distinct: ["userId"], take: 50 })`. Active names capped at 8.

**Activity feed** (8th query): `activityEvent.findMany({ where: { ingestedAt ≥ thirtyMinAgo, OR: [{ hookSource: "Stop", feedSummary: { not: null } }, { kind: "MANUAL_STATUS" }] }, orderBy: { ingestedAt: "desc" }, take: 20, select: { id, ingestedAt, feedSummary, manualText, userId, user.name, project.name } })`.

`activityText` priority: `feedSummary ?? manualText ?? null`.

BigInt note: `$queryRaw` returns PostgreSQL `COUNT` as JavaScript `BigInt`. Every aggregated field is wrapped in `Number()` before use.

---

### Project Status Computation

Source: [`src/lib/project-status.ts`](src/lib/project-status.ts:4)

`deriveStatus(status, lastActivityAt)`:
- `"ARCHIVED"` → `"Archived"`
- `"PAUSED"` → `"Paused"`
- `"ACTIVE"`: `lastActivityAt` null or age > 2h → `"Idle"`; otherwise → `"Active"`

Source: [`src/lib/project-verdict.ts`](src/lib/project-verdict.ts:36)

`computeVerdict(input: VerdictInput) → VerdictResult` — priority order:
1. Non-ACTIVE project → `on_track`
2. `riskLevel === "HIGH"` → `at_risk`
3. `!hasActivityLast3Days` → `at_risk`
4. `activeMembersToday > 0 && costTodayUSD === 0` → `needs_attention`
5. `riskLevel === "MED"` → `needs_attention`
6. `!intelGeneratedAt` → `needs_attention`
7. intel age > 48h → `needs_attention`
8. Default → `on_track`

Source: [`src/lib/project-exceptions.ts`](src/lib/project-exceptions.ts:31)

`computeExceptionFlags(input)` — flags for the "Needs a look" panel:
- **High risk**: riskLevel HIGH, severity `high`
- **Cost spike**: `costTodayUSD > avg * 2` (only when ≥5 days of history with spend), severity `medium`
- **Stalled**: no activity in 3 days, severity `high`
- **No AI spend**: active members today but $0 cost, severity `medium`
- **Repo stale**: repo linked but `repoContextRefreshedAt` > 14 days old, severity `medium`

---

### Presence Computation

Source: [`src/lib/presence.ts`](src/lib/presence.ts:6)

`derivePresence(lastActivityAt)`:
- age ≤ 30 min (`ACTIVE_THRESHOLD_MS`) → `"active"`
- age ≤ 2h (`IDLE_THRESHOLD_MS`) → `"idle"`
- else → `"offline"`

---

## Authentication Data Flow

### Session Token Flow

Source: [`src/lib/auth.ts`](src/lib/auth.ts), [`src/app/api/auth/login/route.ts`](src/app/api/auth/login/route.ts:19)

**Login (`POST /api/auth/login`)**:
1. Rate-limit by IP via `checkLoginRateLimit`.
2. `db.user.findUnique({ where: { email } })`.
3. Check `user.lockedUntil` — reject 401 silently if still locked.
4. `verifyPassword(password, user.passwordHash)` (bcrypt).
5. On failure: increment `failedLogins`; if ≥ 5 → `lockedUntil = now + 10min`; write `AuditLogEntry` `LOGIN_FAILURE` if attempts ≥ 4.
6. On success: reset `failedLogins = 0, lockedUntil = null`.
7. Resolve the user's first Membership (PM3): `db.membership.findFirst({ where: { userId }, orderBy: { createdAt: "asc" }, select: { organisationId: true } })`. If none exists → opaque 401 "Invalid credentials" (never leaks that the account is present-but-orphaned).

8. Encode JWT (`@auth/core/jwt` `encode()`) with payload. **Post-PM3 the JWT is role-less**:

| JWT field | Value |
|-----------|-------|
| sub | user.id |
| name | user.name |
| email | user.email |
| activeOrganisationId | membership.organisationId (PM3 — `role`/`teamId`/`isLineManager` are NOT in the JWT; `withAuthScoped` reads them from the Membership row on every request) |
| sessionVersion | user.sessionVersion |
| iat | unix now |
| exp | now + 30 days |
| jti | crypto.randomUUID() |

9. Set `HttpOnly; SameSite=Lax; Max-Age=2592000` cookie. Cookie name: `__Secure-authjs.session-token` on HTTPS, `authjs.session-token` on HTTP.

**Session validation** ([`src/lib/withAuthScoped.ts`](src/lib/withAuthScoped.ts:37)):
1. `auth()` — NextAuth reads and verifies the JWT cookie.
2. Returns `null` if no session or no `activeOrganisationId` claim.
3. **Session version drift check**: queries `db.user.findUnique({ select: { sessionVersion } })` (cached in `_sessionVersionCache` Map with 30-second TTL). If `jwt.sessionVersion !== db.sessionVersion` → returns null (forces re-login).
4. **PM3 anti-forge guard**: `db.membership.findUnique({ where: { userId_organisationId: { userId: session.user.id, organisationId: activeOrganisationId } } })`. The `userId` is sourced from the verified `token.sub`; the `organisationId` is the untrusted JWT claim. Returns `null` if no row — a tampered `activeOrganisationId` resolves to 401.
5. Returns `AuthContext`: `{ userId, organisationId, role, teamId, isLineManager, scope: { allTeams, canSeeTimeData, viewedTeamIds } }`. `role`, `teamId`, `isLineManager`, and the authoritative `organisationId` come from the Membership row, NOT from the JWT.

---

### PM4 — Memberships List & Switch-Org Flow

Source: [`src/app/api/auth/memberships/route.ts`](src/app/api/auth/memberships/route.ts), [`src/app/api/auth/switch-org/route.ts`](src/app/api/auth/switch-org/route.ts), [`src/components/OrgBadge.tsx`](src/components/OrgBadge.tsx)

**`GET /api/auth/memberships`** — caller's memberships only:
1. `withAuthScoped()` → `ctx` (401 if null).
2. `db.membership.findMany({ where: { userId: ctx.userId, status: "ACTIVE" }, select: { organisationId, role, teamId, organisation: { select: { name } } }, orderBy: { createdAt: "asc" } })`. **PM5**: filters `status: "ACTIVE"` so PENDING memberships never appear in the org list.
3. Response: `{ memberships: [{ organisationId, organisationName, role, teamId }] }`. No `?userId=` parameter is honored — the route's `GET()` signature is parameter-less, so there is no `Request` binding in scope to read URL/headers/body from. A structural forge guard test (reads the route file from disk) pins the absence of every input idiom.

**`POST /api/auth/switch-org`** — re-issue JWT with new active org:
1. `secret = process.env.NEXTAUTH_SECRET` (500 if absent).
2. `withAuthScoped()` → `ctx` (401 if null).
3. `checkSwitchOrgRateLimit(ctx.userId)` (429 if limited; fail-open on Upstash errors).
4. Parse body JSON (400 on invalid).
5. Validate `typeof targetOrgId === "string" && targetOrgId !== ""` (400 if not).
6. **Membership composite-key lookup**: `db.membership.findUnique({ where: { userId_organisationId: { userId: ctx.userId, organisationId: targetOrgId } }, select: { organisationId: true } })`. **Null → 403, no `Set-Cookie`.**
7. Read existing session via `auth()` to preserve `sub` + `sessionVersion` (401 if absent).
8. Re-encode JWT (see PM4 invariants in `code.md`). Cookie name proto-aware; cookie parts `Path=/`, `Max-Age=2592000`, `HttpOnly`, `SameSite=Lax`, `Secure` only on `__Secure-` branch.
9. Response: `200 { ok: true, activeOrganisationId: membership.organisationId }` with `Set-Cookie` header.

**Client switching flow** (`OrgBadge.tsx`):
1. `AppShell` (server) loads `db.membership.findMany({ where: { userId: ctx.userId }, ... })` in parallel with the org-name lookup; passes `memberships` + `activeOrganisationId` as props.
2. `OrgBadge` renders the dropdown affordance only when `memberships.length > 1`.
3. On selection: `fetch("/api/auth/switch-org", { method: "POST", body: { organisationId } })`. Browser auto-includes the `authjs.csrf-token` cookie (CSRF gate stays in front — switch-org is NOT in `CSRF_BYPASS_PREFIXES`).
4. On `res.ok`: `router.refresh()` re-runs the server tree, which reads the new cookie and re-resolves `ctx.organisationId` → new active org renders. Client never mutates `activeOrganisationId` locally.
5. On `res.status === 401`: `router.push("/login")`.
6. On 403/429/other: inline error message; no state change.

---

### Agent Token Resolution

Source: [`src/lib/resolveAgentToken.ts`](src/lib/resolveAgentToken.ts:20)

`resolveAgentToken(rawToken, projectId)`:
1. `preview = rawToken.slice(-4)`.
2. `db.agentToken.findMany({ where: { projectId, tokenPreview: preview, revokedAt: null }, select: { id, tokenHash, userId } })`.
3. For each candidate: `bcrypt.compare(AGENT_TOKEN_PEPPER + raw, tokenHash)`. Return `{ valid: true, userId, tokenId }` on first match.
4. **Legacy fallback**: `db.project.findUnique({ select: { agentTokenHash, previousTokenHash, previousTokenExpiresAt } })`. Calls `verifyTokenWithGrace(raw, currentHash, prevHash, prevExpiresAt)`. Returns `{ valid: true, userId: null, tokenId: null }` if valid.
5. Returns `{ valid: false }` if nothing matches.

`resolveAgentTokenGlobal(rawToken)` — same preview-based lookup but without a `projectId` filter (searches all `AgentToken` rows); also returns `userEmail`; legacy fallback searches `Project` by `agentTokenPreview`.

Token generation ([`src/lib/token.ts`](src/lib/token.ts:6)): `crypto.randomBytes(32).toString("base64url")`. Hash: `bcrypt(AGENT_TOKEN_PEPPER + raw, 12)`. Preview: `raw.slice(-4)`.

Grace window: `verifyTokenWithGrace(raw, currentHash, prevHash, prevExpiresAt)` — checks current hash first; if fails, checks previous hash only if `prevExpiresAt > now`.

---

### User Token Resolution

Source: [`src/lib/userToken.ts`](src/lib/userToken.ts:14)

`resolveUserToken(rawToken)`:
1. `preview = rawToken.slice(-4)`.
2. `db.userToken.findMany({ where: { tokenPreview: preview }, select: { tokenHash, userId, organisationId } })`.
3. bcrypt-verify each candidate.
4. On match: `db.membership.findFirst({ where: { userId, organisationId, status: "ACTIVE" }, select: { teamId } })` — reads `teamId` from Membership (User.teamId was dropped in PM6).
5. Returns `{ valid: true, userId, organisationId, teamId }`.

Token creation (`POST /api/install/user-token`): `db.userToken.upsert({ where: { userId }, create: { tokenHash, tokenPreview, userId, organisationId }, update: { tokenHash, tokenPreview } })`. Subsequent calls rotate — old hash immediately invalid. Raw token returned once.

---

## Consent Data Flow

Source: [`src/lib/consentCheck.ts`](src/lib/consentCheck.ts), [`src/app/api/consents/acknowledge/route.ts`](src/app/api/consents/acknowledge/route.ts)

`needsConsentModal(userId, teamId)`:
1. If no `teamId` → false.
2. `db.team.findUnique({ where: { id: teamId }, select: { timeTrackingEnabled } })`. If not enabled → false.
3. `db.timeTrackingConsent.findUnique({ where: { userId }, select: { acknowledgedAt, consentVersion } })`.
4. Returns true if: `!consent.acknowledgedAt` OR `consentVersion < 2`.

`POST /api/consents/acknowledge`:
1. Session auth.
2. Check team `timeTrackingEnabled`. Reject 400 if not.
3. `db.timeTrackingConsent.upsert({ where: { userId }, create: { acknowledgedAt: now, consentVersion: 2 }, update: { acknowledgedAt: now, consentVersion: 2 } })`. Always stamps v2.
4. Write `AuditLogEntry` `ACKNOWLEDGE_TRACKING_NOTICE`.

---

## Productive Rules Data Flow

Source: [`src/lib/productive-rules.ts`](src/lib/productive-rules.ts), [`src/app/api/productive-rules/route.ts`](src/app/api/productive-rules/route.ts)

**Loading** (`GET /api/productive-rules`) — three auth paths:
1. **UserToken Bearer**: `db.productiveAppRule.findMany({ where: { isActive: true, organisationId, OR: [{ scope: "GLOBAL" }, { scope: "TEAM", teamId }] } })`.
2. **AgentToken Bearer** (requires `?projectId=`): same query scoped to project's team.
3. **Session cookie**: MANAGER sees all active rules (org-scoped); LM/MEMBER sees GLOBAL + their team's TEAM rules.

**Merge logic** (`mergeRules(globalRules, teamRules)`):
- Build set of `teamRules` patterns (lower-cased).
- Keep GLOBAL rules whose pattern is not in the team set.
- Return `[...filteredGlobal, ...teamRules]` — TEAM rules override GLOBAL on pattern collision.

**Match types**:
- `EXACT`: `appName.toLowerCase() === pattern.toLowerCase()`
- `GLOB`: `*` → `.*` regex, anchored `^…$`, case-insensitive
- `REGEX`: treats `pattern` as a regex, case-insensitive; malformed → false

**Evaluation** (`isAppProductive(appName, mergedRules)`): returns `isProductive` of first matching rule. Default (no match) = `false`.

---

## Repo Context Data Flow

Source: [`src/lib/repo-context/index.ts`](src/lib/repo-context/index.ts), [`src/lib/repo-context/client.ts`](src/lib/repo-context/client.ts), [`src/lib/repo-context/snapshot.ts`](src/lib/repo-context/snapshot.ts)

**Trigger**: `POST /api/projects/:id/repo-context/refresh` (MANAGER or LM of team). Rate-limited per project. Fires `refreshRepoContext(projectId)` as fire-and-forget; responds 202 `{ status: "refreshing" }` immediately.

**`refreshRepoContext(projectId)`**:
1. `db.project.update({ repoContextStatus: "REFRESHING", repoContextError: null })`.
2. Parallel: `fetchMetadata(installationId, fullName)` + `generateSnapshot(installationId, fullName, defaultBranch)`.
3. On success: `db.project.update({ repoMetadata, repoSnapshot, repoContextRefreshedAt, repoContextStatus: "LINKED" })`.
4. On error: `db.project.update({ repoContextStatus: "ERROR", repoContextError: errMsg.slice(0, 500) })`.

**GitHub API calls** ([`src/lib/repo-context/client.ts`](src/lib/repo-context/client.ts)):
- JWT auth: `createAppJWT()` — RS256 JWT signed with `GITHUB_APP_PRIVATE_KEY` (base64-decoded PEM), claims `{ iat: now-60, exp: now+600, iss: GITHUB_APP_ID }`.
- Installation token: `POST https://api.github.com/app/installations/:id/access_tokens` — cached in `_tokenCache` Map for ~50 minutes.
- All calls via `authedGithubFetch(url, installationId)` — enforces `api.github.com` host allowlist.

**`fetchMetadata(installationId, fullName)`**:
- `GET https://api.github.com/repos/:fullName` → `{ name, description, default_branch, html_url, visibility }`.
- `GET https://api.github.com/repos/:fullName/languages` → `Record<string, number>` (byte counts per language).
- Returns `RepoMetadata`.

**`generateSnapshot(installationId, fullName, defaultBranch)`**:
- `GET https://api.github.com/repos/:fullName/git/trees/:branch` → top-level tree (up to 20 entries).
- For each blob in `KEY_CONFIG_ALLOWLIST` (package.json, tsconfig.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml, pom.xml, build.gradle, Dockerfile, docker-compose.yml, next.config.\*, vite.config.\*, nest-cli.json, nuxt.config.\*, astro.config.\*, svelte.config.js, README.md): `GET https://api.github.com/repos/:fullName/contents/:path?ref=:branch`.
- Each file: base64-decode content, truncate to 4096 bytes, run `redact()` on excerpt, store `{ path, excerpt }`.
- `detectFrameworks(keyConfigs)`: infers framework names from package.json deps, requirements.txt, pyproject.toml, go.mod, Cargo.toml, Dockerfile first line.
- Total `repoSnapshot` JSON capped at 8 KB (trims key config excerpts if exceeded).
- Returns `RepoSnapshot`: `{ topLevelTree, keyConfigs, detectedFrameworks, generatedAt }`.

---

## Readiness Data Flow

Source: [`src/lib/readiness.ts`](src/lib/readiness.ts), [`src/app/api/projects/[id]/readiness/route.ts`](src/app/api/projects/[id]/readiness/route.ts), [`src/app/api/projects/[id]/readiness/scan/route.ts`](src/app/api/projects/[id]/readiness/scan/route.ts)

### GET /api/projects/:id/readiness

All authenticated roles (own team). Loads up to 90 `ReadinessSnapshot` rows ordered by `scannedAt desc`, builds `ReadinessSignal` via `buildReadinessSignal`.

**Response** (200):
```json
{
  "markerCount": 7,
  "markerDetail": { "todo": 3, "fixme": 2, "skippedTests": 1, "stubbed": 1, "testFileCount": 12 },
  "coveragePct": 78.5,
  "forecast": { "kind": "trend", "daysToZero": 4, "slopePerDay": -1.75 },
  "snapshotCount": 5,
  "lastScannedAt": "2026-06-14T12:00:00.000Z"
}
```
- `forecast.kind` is one of `"trend"` | `"flat"` | `"insufficient"`.
- `coveragePct` is `null` if no `coverage/coverage-summary.json` was readable at last scan time.
- `lastScannedAt` is `null` if no snapshot exists yet.

### POST /api/projects/:id/readiness/scan

MANAGER or LINE_MANAGER (own team). Rate-limited 1/60s per projectId.

**What it does**:
1. `scanMarkersInDir(process.cwd())` — recursively counts TODO/FIXME/skipped/stubbed in .ts/.tsx/.js/.jsx/.mjs files; skips node_modules, .next, dist, coverage, generated, migrations, .git.
2. `readCoveragePct(process.cwd())` — reads `coverage/coverage-summary.json → total.lines.pct`; null if absent.
3. `db.readinessSnapshot.create(...)` — persists result.
4. Fetches updated snapshot list, returns same shape as GET.

**Response** (200): same shape as GET response above.
**Response** (429): `{ "error": "Too many requests" }` — 1/60s rate limit exceeded.

---

## Code Health Data Flow

Source: [`src/lib/code-health.ts`](src/lib/code-health.ts), [`src/app/api/projects/[id]/code-health/route.ts`](src/app/api/projects/[id]/code-health/route.ts), [`src/app/api/projects/[id]/code-health/scan/route.ts`](src/app/api/projects/[id]/code-health/scan/route.ts)

### GET /api/projects/:id/code-health

All authenticated roles (own team). Reads the latest `CodeHealthSnapshot` row for the project from DB. Zero SonarQube API calls in this path.

**Response** (200):
```json
{
  "snapshot": {
    "id": "...",
    "sonarProjectKey": "axis-pulse",
    "qualityGate": "PASS",
    "reliabilityRating": "A",
    "securityRating": "A",
    "maintainabilityRating": "B",
    "coveragePct": 78.5,
    "duplicationPct": 2.1,
    "scannedAt": "2026-06-14T12:00:00.000Z"
  }
}
```
- `snapshot` is `null` if no scan has been run yet.

### POST /api/projects/:id/code-health/scan

MANAGER or LINE_MANAGER (own team). Rate-limited 1/120s per projectId; max 2 concurrent scans server-wide (in-process semaphore). Returns 503 if required env vars are missing or semaphore is full.

**CENTRAL path** (project has `githubRepoFullName` + `githubInstallationId`):
1. Rate-limit check → 429 if exceeded.
2. Check always-required env (`SONAR_HOST_URL`, `SONAR_SCANNER_HOST_URL`, `SONAR_TOKEN`) → 503 if missing.
3. Multi-tenancy proof: `db.githubInstallation.findUnique({ where: { organisationId_installationId: { organisationId: ctx.organisationId, installationId: project.githubInstallationId } } })` → 403 if null (installation does not belong to authed org).
4. Check `SONAR_ADMIN_TOKEN` → 503 if missing.
5. Derive `sonarProjectKey = org-{ctx.organisationId}-proj-{projectId}` (never client-supplied).
6. Acquire semaphore slot (`tryAcquireScanSlot()`) → 503 if at capacity.
7. `ensureSonarProject({ projectKey, projectName, hostUrl, adminToken })` — auto-provisions project in SonarQube; "already exist" is a no-op.
8. `downloadRepoTarball({ repoFullName, ref: repoMetadata.defaultBranch ?? "HEAD", installationId, tarballPath })` — streams GitHub tarball to `/tmp/pulse-scan-{projectId}-{ts}/repo.tar.gz`.
9. `extractTarball(tarballPath, srcDir)` — extracts to `/tmp/pulse-scan-{projectId}-{ts}/src/`.
10. `runSonarScanner({ projectKey, scannerHostUrl, token, sourcesPath: srcDir })` — mounts `srcDir` into sonar-scanner Docker container.
11. `fetchSonarMetrics(projectKey, hostUrl, token)` — retrieves ratings from SonarQube REST API.
12. `db.codeHealthSnapshot.create({ ..., scanSource: "CENTRAL" })` — persists row.
13. `finally`: `releaseScanSlot()` + `rmSync(tmpDir, { recursive: true, force: true })`.

**EDGE path** (no GitHub link):
1–2. Same checks.
3. Check `SONAR_PROJECT_KEY` env var → 503 if missing.
4. Acquire semaphore → 503 if full.
5. `runSonarScanner({ projectKey: SONAR_PROJECT_KEY, sourcesPath: process.cwd() })`.
6. `fetchSonarMetrics`, `db.codeHealthSnapshot.create({ ..., scanSource: "EDGE" })`.
7. `finally`: `releaseScanSlot()`.

**Response** (200): same shape as GET response above (nested `snapshot` object).
**Response** (403): `{ "error": "Forbidden" }` — wrong org installation.
**Response** (429): `{ "error": "Too many requests" }`.
**Response** (503): `{ "error": "SonarQube not configured" }` or `{ "error": "Scan capacity exceeded" }`.

---

## Security Scan Data Flow

Source: [`src/lib/security-scan.ts`](src/lib/security-scan.ts), [`src/app/api/projects/[id]/security-scan/route.ts`](src/app/api/projects/[id]/security-scan/route.ts), [`src/app/api/projects/[id]/security-findings/route.ts`](src/app/api/projects/[id]/security-findings/route.ts)

### GET /api/projects/:id/security-findings

All authenticated roles (own team). Loads the latest `SecurityScanRun` for the project including its `SecurityFinding` rows. Derives `scanState`:

- `"not_scanned"` — no `SecurityScanRun` row exists for the project
- `"scanned_clean"` — latest scan run has `findingCount = 0`
- `"has_findings"` — latest scan run has `findingCount > 0`

**Response** (200):
```json
{
  "scanState": "has_findings",
  "scanRun": { "id": "...", "scannedAt": "...", "findingCount": 3, "toolsRun": ["semgrep","gitleaks","osv-scanner"] },
  "findings": [
    { "id": "...", "tool": "gitleaks", "severity": "CRITICAL", "message": "...", "file": "...", "line": 42 }
  ]
}
```
- `scanRun` is `null` and `findings` is `[]` when `scanState = "not_scanned"`.

### POST /api/projects/:id/security-scan

MANAGER or LINE_MANAGER (own team). Rate-limited 1/120s per projectId. Reuses the Phase 9b central scan plumbing from `src/lib/code-health.ts`.

**Scan flow**:
1. Rate-limit check → 429 if exceeded.
2. Verify GithubInstallation ownership (same multi-tenancy proof as code-health CENTRAL path) → 403 if not found.
3. Acquire semaphore slot (`tryAcquireScanSlot()`) → 503 if at capacity.
4. `downloadRepoTarball(...)` — streams GitHub tarball to `/tmp/pulse-scan-{projectId}-{ts}/repo.tar.gz`.
5. `extractTarball(tarballPath, srcDir)` — extracts to `/tmp/pulse-scan-{projectId}-{ts}/src/`.
6. `runAllSecurityTools(srcDir, tmpDir)` — runs each tool in sequence, catches individual tool failures (tool not installed = 0 findings, not an error):
   - `runSemgrep(srcDir)` → parses JSON output via `parseSemgrepOutput`; severity mapping: ERROR→HIGH, WARNING→MEDIUM, else INFO.
   - `runGitleaks(srcDir)` → parses JSON output via `parseGitleaksOutput`; all findings are CRITICAL.
   - `runOsvScanner(srcDir)` → parses JSON output via `parseOsvScannerOutput`; uses `database_specific.severity` (MODERATE→MEDIUM) or CVSS vector heuristic.
7. `db.securityScanRun.create(...)` — persists the scan run row.
8. `db.securityFinding.createMany(...)` — persists all findings.
9. `finally`: `releaseScanSlot()` + `rmSync(tmpDir, { recursive: true, force: true })`.

**Response** (200): `{ scanRunId, findingCount, findings[] }`.
**Response** (429): `{ "error": "Too many requests" }`.
**Response** (503): `{ "error": "Scan capacity exceeded" }`.

### Project Page Integration

`src/app/projects/[id]/page.tsx` fetches `latestSecurityScan` (the most recent `SecurityScanRun` with its `findings`) in the `Promise.all` alongside the other project data queries. It then:
1. Computes `scanState` from the fetched run (not_scanned / scanned_clean / has_findings).
2. Calls `groupSecurityFindings(latestSecurityScan?.findings ?? [])` from `src/lib/project-exceptions.ts` to produce a `SecurityFindingGroup[]`. Groups are keyed by `ruleId` (or `tool:message[:60]` when `ruleId` is null). INFO-severity findings are excluded from groups. Within each group, identical occurrences (same file + same line) are display-collapsed into a single entry; `totalCount` tracks the honest raw count.
3. Calls `computeExceptionFlags(input)` independently to produce the operational `ExceptionFlag[]` (high-risk, cost-spike, stall, repo-stale).
4. Passes `flags` (operational only), `securityGroups` (grouped security findings), and `scanState` to `ExceptionsWhoRow` → `ExceptionsPanel`.

`ExceptionsPanel` renders the two lists separately: operational flags as flat chips, security groups as expandable `GroupRow` items sorted worst-severity-first. HIGH/CRITICAL groups are visible by default; MEDIUM/LOW groups are hidden behind a "+N more findings — view all" toggle.

---

## Budget & Cost Data Flow

### Narration Cost (Intelligence tokens)

Source: [`src/lib/cost-ceiling.ts`](src/lib/cost-ceiling.ts)

Pricing (used for ceiling enforcement):
- Input: `$3.00/M tokens` (`INPUT_COST_PER_TOKEN = 3e-6`)
- Output: `$15.00/M tokens` (`OUTPUT_COST_PER_TOKEN = 15e-6`)

`getMonthlySpendUSD(organisationId)`: `db.intelligence.aggregate({ where: { organisationId, generatedAt: { gte: monthStart } }, _sum: { inputTokens, outputTokens } })`. Computes USD.

`isCeilingExceeded(organisationId)`: returns true if spend ≥ `CLAUDE_MONTHLY_CEILING_USD` env var. When exceeded, narration pipeline returns without calling Groq.

`getProjectSpendByMonth(organisationId)`: groups `Intelligence` by `projectId` for the current month; joins with project/team names; sorts by spend descending.

### Developer Claude Code Cost (ActivityEvent tokens)

Source: [`src/lib/dev-cost.ts`](src/lib/dev-cost.ts)

Developer tokens arrive from the Stop hook via `claudeUsage` in the ingest body. `claudeSpendUSD` is pre-computed client-side (model-aware) and stored directly on `ActivityEvent`.

Model pricing tables:
- **Sonnet 4.6**: input `$3.00/M`, output `$15.00/M`, cacheCreate `$3.75/M`, cacheRead `$0.30/M`
- **Opus**: input `$5.00/M`, output `$25.00/M`, cacheCreate `$6.25/M`, cacheRead `$0.50/M`
- **Haiku**: input `$1.00/M`, output `$5.00/M`, cacheCreate `$1.25/M`, cacheRead `$0.10/M`

Key DB queries:
- `getDevDailySpendUSD(organisationId)`: `db.activityEvent.aggregate({ _sum: { claudeSpendUSD }, where: { hookSource: "Stop", claudeSpendUSD: { not: null }, ingestedAt: { gte: dayStart } } })`.
- `getDevSpendByUser(organisationId)`: groups by `userId` for today; resolves user names.
- `getDevTokensByProject(organisationId, since)`: groups by `projectId`; sums `claudeInputTokens + claudeOutputTokens` (excludes cacheRead to avoid 40× inflation).
- `getProject7DayDailySpends(projectId, organisationId)`: fetches Stop events for last 7 days before today; groups in TypeScript by UTC date string.
- `getProjectMonthlyDevSpendUSD(projectId, organisationId)`: MTD spend from 1st of current UTC month; used for the budget-overrun alarm in `computeExceptionFlags`.
- `getProjectWindowedDevSpendUSD(projectId, organisationId, since)`: spend from caller-supplied `since` date; used by `SpendRing` display (obeys global time filter).

### Budget Display

Source: [`src/lib/budget-utils.ts`](src/lib/budget-utils.ts)

`computeBudgetStatus(usedTokens, budgetTokens)`: returns `"ok"` / `"near-limit"` (≥80%) / `"over-budget"` (≥100%) / `"no-budget"` (budgetTokens null).

`computeUsagePct(usedTokens, budgetTokens)`: returns percentage or null.

`computeNotionalBudgetUSD(budgetTokens)`: uses `SONNET_INPUT_RATE = $3.00/M` for approximate USD display.

---

## Audit Log Data Flow

Source: [`src/lib/audit.ts`](src/lib/audit.ts), route handlers throughout

`writeAudit(userId, action, subjectId, meta?, ipAddress?, organisationId?)`:
- `db.auditLogEntry.create({ data: { userId, action, subjectId, meta, ipAddress, organisationId: organisationId ?? "org_system" } })`.
- IP extracted via `getIp(request)`: reads `x-forwarded-for` (first entry) then `x-real-ip`.

Actions written across route handlers:

| Action | Trigger |
|--------|---------|
| `LOGIN_FAILURE` | Failed login (at ≥4 attempts or lockout) |
| `CREATE_PROJECT` | `POST /api/projects` |
| `EDIT_PROJECT` | `PATCH /api/projects/:id` |
| `DELETE_PROJECT` | `DELETE /api/projects/:id` |
| `CREATE_AGENT_TOKEN` | `POST /api/projects/:id/agent-tokens` |
| `SUMMARY_GENERATE` | `POST /api/projects/:id/summary` |
| `EDIT_PRODUCTIVE_RULE` | `POST /api/productive-rules` and `PATCH /api/productive-rules/:id` |
| `REPO_LINK` | `linkRepoAndRefresh()` |
| `ACKNOWLEDGE_TRACKING_NOTICE` | `POST /api/consents/acknowledge` |

`GET /api/audit` (MANAGER only): paginates `AuditLogEntry` 50 per page with optional filters: `userId`, `action`, `subjectId`, `dateFrom`, `dateTo`. Includes joined `user { id, name, email }`.

---

## Metrics & Observability Data Flow

Source: [`src/lib/metrics.ts`](src/lib/metrics.ts), [`src/lib/otel.ts`](src/lib/otel.ts), [`src/app/api/metrics/route.ts`](src/app/api/metrics/route.ts)

### In-Memory Prometheus Metrics

Module-level singleton in `src/lib/metrics.ts`. Pre-registers all known routes at startup.

**`recordRequest(route, method, statusCode, durationMs)`** — called by every tracked route handler:
- Increments `stats.total`.
- Increments `stats.byStatusClass` (`"2xx"`, `"4xx"`, `"5xx"`).
- Updates cumulative histogram buckets (11 le values: 0.005s to 10s, plus +Inf).
- Pushes `{ ts, ms }` to `stats.latenciesSampled`; trims to rolling 24h window, max 5000 samples.

**`recordClaudeTokens(projectId, inputTokens, outputTokens)`** — called by `generateNarration` after each Intelligence row write.

Pre-registered routes (`KNOWN_ROUTES`):
`POST /api/auth/login`, `POST /api/ingest/event`, `POST /api/ingest/time`, `POST /api/status`, `GET /api/projects`, `POST /api/projects/:id/summary`, `GET /api/projects/:id/export`, `POST /api/projects/:id/repo-context/refresh`, `GET /api/github/installations/:id/repos`, `GET /api/users/:id/time`, `POST /api/productive-rules`, `PATCH /api/productive-rules/:id`, `PATCH /api/teams/:id`, `GET /api/admin/audit`.

**`GET /api/metrics`**: no auth; returns Prometheus text format (`text/plain; version=0.0.4`). Exposes:
- `pulse_request_latency_seconds` (histogram) — per route/method
- `pulse_request_total` (counter) — per route/method/status_class
- `pulse_claude_input_tokens_total` (counter) — per project_id
- `pulse_claude_output_tokens_total` (counter) — per project_id

**`getRouteP95s(windowMs = 24h)`**: used by the admin latency dashboard — computes p95 and p50 from `latenciesSampled` within the window.

### OpenTelemetry Span Tracing

Source: [`src/lib/otel.ts`](src/lib/otel.ts)

Minimal in-memory span tracer. Five spans per `/api/ingest/event` call: `ingest`, `redact`, `gate`, `ai`, `store`. Stores the last completed trace in `_lastTrace` (module-level singleton) for `/build-evidence` capture.

---

## State Management

### In-Memory Rate Limit Caches

Source: various `src/lib/ratelimit-*.ts` files

- **`ratelimit.ts`** — `_rl: Ratelimit | null` + `_lastTier: string` — Upstash Redis sliding window; re-initialised if `SCALE_TIER` env var changes at runtime.
- **`withAuthScoped.ts`** — `_sessionVersionCache: Map<string, { version, cachedAt }>` — TTL 30 seconds per userId.
- **`src/lib/narrate.ts`** — `cooldowns: Map<string, number>` — per-projectId narration cooldown timestamp (90s).
- **`src/lib/repo-context/client.ts`** — `_tokenCache: Map<string, { token, expiresAt }>` — GitHub installation access tokens (cached for ~50 minutes).
- **`src/lib/metrics.ts`** — `_routeStore`, `_claudeInputTokens`, `_claudeOutputTokens` — all module-level Maps, persist for the lifetime of the Node.js process.
- `status-ratelimit.ts`, `summary-ratelimit.ts`, `repo-context-ratelimit.ts` — simple in-memory Maps for per-user/per-project rate counters (no Redis).

---

## Data Validation & Sanitisation

### Zod Schemas

| Schema | Location | Key constraints |
|--------|----------|----------------|
| `BodySchema` (event ingest) | [`src/app/api/ingest/event/route.ts:17`](src/app/api/ingest/event/route.ts:17) | projectId min(1), kind enum, claudeUsage int ≥0 |
| `BodySchema` (time ingest) | [`src/app/api/ingest/time/route.ts:17`](src/app/api/ingest/time/route.ts:17) | day string, workedSeconds max 86400, topApps arrays max 2 |
| `BodySchema` (status) | [`src/app/api/status/route.ts:9`](src/app/api/status/route.ts:9) | projectId min(1), text min(1) max(2000) |
| `bodySchema` (agent token) | [`src/app/api/projects/[id]/agent-tokens/route.ts:8`](src/app/api/projects/[id]/agent-tokens/route.ts:8) | userId min(1), label string default("") |

### Redaction

Source: [`src/lib/redact.ts`](src/lib/redact.ts)

Seven rules applied in order to `sessionExcerpt`, `manualText`, `gitSummary`:

| Rule | Pattern | Kind |
|------|---------|------|
| 1 | `^KEY=value` lines (env-style) | `"env"` |
| 2 | `eyJ...` JWT (header.payload.signature, ≥20 chars each) | `"jwt"` |
| 3 | `sk-ant-` Anthropic key | `"sk-ant"` |
| 4 | `sk-` + 20+ alphanumeric | `"sk"` |
| 5 | `AKIA`/`ASIA` + 15–16 uppercase alphanumeric | `"aws-key"` |
| 6 | PEM private key block | `"pem"` |
| 7 | URL credentials `://user:pass@` | `"url-creds"` |

Truncation to 1500 chars applied **after** all redaction rules.

### Privacy Gate (pulse-time upload)

Source: [`src/lib/pulse-body-shape.ts`](src/lib/pulse-body-shape.ts)

`ALLOWED_TIME_BODY_KEYS = Set { projectId, userIdHint, day, timezone, workedSeconds, productiveSeconds, unproductiveSeconds, topApps }`. `assertBodyShape(body)` throws if any key outside this set is present. `windowTitle`, `appName`, `url` are blocked.

### Pino Logger Redaction

Source: [`src/lib/logger.ts`](src/lib/logger.ts)

Pino `redact` paths (replaced with `"[Redacted]"` at serialisation):
`password`, `passwordHash`, `agentToken`, `agentTokenHash`, `sessionExcerpt`, `manualText`, `tenantKey`, `secret`, `apiKey`, `jwt`, `bearerToken`, `req.headers.authorization`, `req.headers['x-pulse-signature']`, `req.headers['x-internal-token']`, `headers.authorization`, `headers['x-pulse-signature']`, `headers['x-internal-token']`, `Authorization`, `authorization`.

---

## External Data Flows

### GitHub API

Source: [`src/lib/repo-context/client.ts`](src/lib/repo-context/client.ts), [`src/lib/repo-context/snapshot.ts`](src/lib/repo-context/snapshot.ts), [`src/app/api/github/installations/[id]/repos/route.ts`](src/app/api/github/installations/[id]/repos/route.ts)

All calls go through `authedGithubFetch(url, installationId)` which:
- Enforces host allowlist: only `api.github.com` permitted.
- Sets headers: `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`.
- Injects `Authorization: Bearer <installation_token>`.

| Endpoint | Purpose | Data returned |
|----------|---------|---------------|
| `POST /app/installations/:id/access_tokens` | Get installation token | `{ token, expires_at }` |
| `GET /app/installations/:id` | Get account name | `{ account: { login } }` |
| `GET /repos/:fullName` | Repo metadata | `{ name, description, default_branch, html_url, visibility }` |
| `GET /repos/:fullName/languages` | Language breakdown | `Record<string, number>` (byte counts) |
| `GET /repos/:fullName/git/trees/:branch` | Top-level tree | `{ tree: [{ path, type }] }` |
| `GET /repos/:fullName/contents/:path?ref=:branch` | Key config file contents | `{ content (base64), encoding }` |
| `GET /installation/repositories?per_page=100` | List repos for installation | `{ repositories: [{ id, full_name, name, private, html_url, default_branch }] }` |

Repo snapshot is stored as JSON in `Project.repoSnapshot` (max 8 KB). Key config excerpts are redacted before storage.

### AI API (Narration)

Source: [`src/lib/narrate.ts`](src/lib/narrate.ts)

- Primary model: `claude-haiku-4-5-20251001` via `@ai-sdk/anthropic` when org Anthropic key is set.
- Fallback: free OpenRouter models (`meta-llama/llama-3.3-70b-instruct:free` etc.) → Groq `llama-3.3-70b-versatile` when no Anthropic key.
- Provider selection: `getAutoCallModel(anthropicApiKey)` from `src/lib/ai-provider.ts`.
- Call: `generateText({ model, system: SYSTEM_PROMPT, messages: [{ role: "user", content: userPrompt }], maxOutputTokens: 512 })`
- Expected response: JSON object with `headline`, `narration`, `stage`, `riskLevel`, `riskFocus`.
- Markdown code fences stripped before `JSON.parse()`.
- Usage stats (`inputTokens`, `outputTokens`) stored on the resulting `Intelligence` row.

### AI API (Feed Summary)

Source: [`src/lib/gemini.ts`](src/lib/gemini.ts)

- Primary model: `claude-haiku-4-5-20251001` via `@ai-sdk/anthropic` when org Anthropic key is set.
- Fallback: same free model chain as narration.
- Provider selection: `getAutoCallModel(anthropicApiKey)` from `src/lib/ai-provider.ts`.
- Call: `generateText({ model, system: SYSTEM_PREFIX, messages: [{ role: "user", content }], maxOutputTokens: 64, temperature: 0.3 })`
- System prefix: "Write a 5-8 word action phrase describing what a developer accomplished. Be specific and concrete — always name the subsystem, file, or function touched."
- Expected response: a single short phrase.
- `validateFeedSummary` applied before accepting result; returns `null` on prompt echo, over-length, or structured output.
- Result stored as `ActivityEvent.feedSummary`.
- Falls back to `firstSentence(excerpt)` (first sentence up to 80 chars) if API call fails or returns null.

### Executive Summary (Groq Streaming)

Source: [`src/app/api/projects/[id]/summary/route.ts`](src/app/api/projects/[id]/summary/route.ts)

- Model: `llama-3.3-70b-versatile`
- Call: `streamText({ model, system: SYSTEM_PROMPT, prompt: userPrompt, maxOutputTokens: 1024, onFinish: async ({ text, usage }) => { ... } })`
- Returns `result.toTextStreamResponse()` — streams to client.
- `onFinish`: parses `CONFIDENCE: <float>` from last non-empty line; strips it from body; persists `ExecutiveSummary` with `body`, `confidence`, `inputTokens`, `outputTokens`, `modelUsed`.

---

## PDF Export Data Flow

Source: [`src/app/api/projects/[id]/export/route.ts`](src/app/api/projects/[id]/export/route.ts), [`src/components/pdf/SummaryPDF.tsx`](src/components/pdf/SummaryPDF.tsx)

### GET /api/projects/:id/export

All authenticated roles (own team). Rate-limited 20/hr/project. Audited as `EXPORT_PDF`. Returns 404 if no `ExecutiveSummary` exists for the project.

MEMBER role is not 403'd. Financial data is excluded server-side: `MemberDailyTime` is never queried when `ctx.scope.canSeeSpend` is false, and `spendUSD` is passed as `null` to `SummaryPDF`.

**Data fetches (11-element Promise.all)**:

| Fetch | Purpose | Gating |
|-------|---------|--------|
| project + team | Name, description, clientName, GitHub repo, frameworks | always |
| latest `ExecutiveSummary` | Body, confidence, generatedAt, modelUsed | always — 404 if absent |
| `MemberDailyTime` (last 7 days) | Per-member worked/productive seconds | only when `canSeeSpend` is true |
| recent `ActivityEvent` (Stop, last 24h) | Up to 6 deduplicated work items (feedSummary / extractSubjectLine) | always |
| `ProjectMember` + user names | Per-member table rows | always |
| latest `SecurityScanRun` + `SecurityFinding` rows | Security posture section | always |
| active `Prompt` (most recent matched) | Prompt context section | always |
| `ActivityEvent.count` (last 3 days) | `hasActivityLast3Days` signal for verdict | always |
| `ReadinessSnapshot` rows (up to 90, desc) | Readiness markers section | always |
| latest `CodeHealthSnapshot` | Code health SonarQube section | always |
| dev spend today (`getProjectDailySpendUSD`) | Spend section | only when `canSeeSpend` is true |

**Computed values (after Promise.all resolves)**:

| Value | Source |
|-------|--------|
| `findingsForVerdict` | Security findings mapped for verdict input |
| `readinessSignal` | `buildReadinessSignal(latest, snapshots)` |
| `readinessForVerdict` | Latest `ReadinessSnapshot` or null |
| `verdict` | `computeVerdict({ riskLevel, hasActivityLast3Days, activeMembersToday, costTodayUSD, intelGeneratedAt, findings: findingsForVerdict, ... })` |
| `workTypeBuckets` | `computeWorkTypeBuckets(recentCommits)` |

**SummaryPDF props (15 total)**:

The component receives: `projectName`, `teamName`, `clientName`, `description`, `githubRepo`, `detectedFrameworks`, `summaryBody`, `confidence`, `generatedAt`, `stage`, `riskLevel`, `riskFocus`, `commitCount`, `workItems[]`, `memberRows[]` — plus Phase 12 additions: `spendUSD` (null for MEMBER / no data), `devTokenBudget`, `verdict`, `securityFindings[]`, `promptContext`, `readiness`, `codeHealth`, `workType`.

**PDF sections rendered**:

| Section | Content | Condition |
|---------|---------|-----------|
| §1.5 Project Verdict | On Track / Needs Attention / At Risk with thresholds | always |
| §1.8 Readiness Markers | TODO/FIXME counts, coverage %, OLS forecast | always |
| §1.9 Code Health SonarQube | Quality gate, reliability/security/maintainability ratings | always |
| §4.5 Work-Type Breakdown | Bug / docs / build / test / other commit distribution | always |
| §5.5 Security Findings | Top findings by severity from last scan | always |
| §7.2 Active Prompt Context | Most recently matched P-number prompt | always |
| §7.5 Developer AI Spend | Daily spend vs budget | only when `spendUSD !== null` |
