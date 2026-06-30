# Architecture

> **Source**: Every fact below was derived from reading actual source files. No assumptions were made.

---

## System Overview

Axis Pulse is an AI workflow intelligence platform for Axis Consulting. It does four things:

1. **Captures** engineering activity from two sources: Claude Code hook events (via a `pulse-send.mjs` script wired into `.claude/settings.json`) and manual status entries typed by team members in the browser.
2. **Stores** activity as `ActivityEvent` rows in PostgreSQL, scoped to a project and organisation.
3. **Narrates** activity using Groq's `llama-3.3-70b-versatile` model — producing per-project 3–4 sentence briefs (`Intelligence` rows), headline summaries, risk levels, and on-demand streaming executive summaries.
4. **Presents** everything through a Next.js dashboard: project cards on the top level, per-project AI summary + member activity on drilldown, and a PDF export for client delivery.

Activity from the Claude Code hook also carries developer token usage (input/output/cache tokens + pre-computed USD cost), enabling real-time cost visibility per developer and per project.

A time-tracking subsystem collects daily productive/unproductive seconds and top-app data from a machine-level ActivityWatch agent, gated by per-user consent.

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | 14.2.35 |
| Language | TypeScript | ^5 |
| UI runtime | React / React DOM | ^18.3.1 |
| ORM | Prisma Client (`@prisma/client`) | ^7.8.0 |
| DB driver | `@prisma/adapter-pg` + `pg` | ^7.8.0 / ^8.21.0 |
| Auth | `next-auth` (v5 beta) | ^5.0.0-beta.31 |
| Auth adapter | `@auth/prisma-adapter` | ^2.11.2 |
| Auth core | `@auth/core` | ^0.41.2 |
| AI SDK | `ai` (Vercel AI SDK) | ^6.0.194 |
| AI provider | `@ai-sdk/groq` | ^3.0.39 |
| Password hashing | `bcryptjs` | ^3.0.3 |
| Rate limiting | `@upstash/ratelimit` + `@upstash/redis` | ^2.0.8 / ^1.38.0 |
| Error monitoring | `@sentry/nextjs` | ^10.56.0 |
| Structured logging | `pino` | ^10.3.1 |
| Schema validation | `zod` | ^4.4.3 |
| PDF generation | `@react-pdf/renderer` | ^4.5.1 |
| UI components | `shadcn`, `@radix-ui/react-label`, `@base-ui/react` | ^4.8.3 / ^2.1.8 / ^1.5.0 |
| UI utilities | `lucide-react`, `clsx`, `class-variance-authority`, `tailwind-merge` | various |
| Forms | `react-hook-form` + `@hookform/resolvers` | ^7.76.1 / ^5.4.0 |
| Theme | `next-themes` | ^0.4.6 |
| 3D / animation | `three` | ^0.184.0 |
| Test runner | `vitest` + `@vitest/coverage-v8` | ^4.1.7 |
| E2E testing | `@playwright/test` | ^1.60.0 |
| CSS | `tailwindcss`, `postcss`, `tw-animate-css` | ^3.4.1 |
| Fonts | Plus Jakarta Sans, IBM Plex Mono (Google Fonts via `next/font`) | — |
| Hosting target | Coolify (self-hosted) | — |
| Database | PostgreSQL | — |
| Cache / rate-limit store | Upstash Redis (REST) | — |

---

## Application Structure

All pages use the Next.js App Router. The root layout (`src/app/layout.tsx`) applies Plus Jakarta Sans and IBM Plex Mono fonts, wraps the app in `ThemeProvider` (dark mode), and renders a cost-ceiling banner when monthly spend ≥ `CLAUDE_MONTHLY_CEILING_USD`.

### Page Routes

| Route | File | Description |
|---|---|---|
| `/login` | `src/app/(auth)/login/page.tsx` | Credential login form |
| `/signup` | `src/app/(auth)/signup/page.tsx` | Account registration |
| `/dashboard` | `src/app/dashboard/page.tsx` | Project card grid + stats + activity feed |
| `/projects/[id]` | `src/app/projects/[id]/page.tsx` | Project detail: AI summary, vital signs, commits, repo context, verdict |
| `/teams` | `src/app/teams/page.tsx` | Teams list with create dialog |
| `/teams/[id]` | `src/app/teams/[id]/page.tsx` | Team detail: member list, time tracking toggle, project list |
| `/prompts` | `src/app/prompts/page.tsx` | P-number prompt library management |
| `/install` | `src/app/install/page.tsx` | Two-step install guide: machine setup + repo hook setup |
| `/invite/[id]` | `src/app/invite/[id]/page.tsx` | Invitation acceptance (creates or links user account) |
| `/profile` | `src/app/profile/page.tsx` | Personal info + change password |
| `/admin/audit` | `src/app/admin/audit/page.tsx` | Audit log viewer (MANAGER-only); filter by userId, action, subjectId, date range |
| `/admin/budget` | `src/app/admin/budget/page.tsx` | Developer token budget per project (MANAGER-only) |
| `/admin/consents` | `src/app/admin/consents/page.tsx` | Per-user `TimeTrackingConsent` status viewer (MANAGER-only) |
| `/admin/cost-dashboard` | `src/app/admin/cost-dashboard/page.tsx` | Monthly AI narration spend: ceiling, per-day totals, per-project breakdown |
| `/admin/github` | `src/app/admin/github/page.tsx` | GitHub App installation management (MANAGER + LINE_MANAGER) |
| `/admin/members` | `src/app/admin/members/page.tsx` | Member provisioning: invite, re-assign, deactivate (MANAGER sees all; LINE_MANAGER sees own team + Unassigned) |
| `/admin/productive-rules` | `src/app/admin/productive-rules/page.tsx` | Manage global + team app productivity rules |
| `/admin/tokens` | `src/app/admin/tokens/page.tsx` | View, revoke, and restore agent tokens |
| `/privacy` | `src/app/privacy/page.tsx` | Privacy policy (static) |
| `/terms` | `src/app/terms/page.tsx` | Terms of service (static) |
| `/debt-analyzer` | `src/app/debt-analyzer/page.tsx` | Debt scan list: all projects + latest scan status; MANAGER+LINE_MANAGER only; MEMBER → redirect `/dashboard` |
| `/debt-analyzer/[id]` | `src/app/debt-analyzer/[id]/page.tsx` | Per-project debt scan detail: trigger, progress, results; MEMBER → redirect |

### Shell Components

The `AppShell` server component (`src/components/AppShell.tsx`) fetches the organisation name and delegates to `AppShellClient` (`src/components/AppShellClient.tsx`), which renders the side navigation and header. `AppShellSignOut.tsx` provides the sign-out button.

---

## Key Components and Their Roles

| Component | Path | Role |
|---|---|---|
| `AppShell` | `src/components/AppShell.tsx` | Server wrapper that resolves org name, delegates to `AppShellClient` |
| `AppShellClient` | `src/components/AppShellClient.tsx` | Client nav shell: sidebar, header, role-aware links |
| `AppShellSignOut` | `src/components/AppShellSignOut.tsx` | Sign-out button (client component, calls NextAuth signOut) |
| `TrackingConsentModal` | `src/components/TrackingConsentModal.tsx` | Modal shown when time-tracking is enabled but user hasn't acknowledged v2 consent |
| `SummaryPDF` | `src/components/pdf/SummaryPDF.tsx` | React PDF renderer for project executive summary export |
| `ProjectCard` | `src/app/dashboard/_components/ProjectCard.tsx` | Dashboard card: last activity, AI headline, team, status badge |
| `DashboardStatsClient` | `src/app/dashboard/_components/DashboardStatsClient.tsx` | Client stat cards: events today, active members, prompts matched, active projects |
| `ActivityFeedClient` | `src/app/dashboard/_components/ActivityFeedClient.tsx` | Live activity feed (narration / Groq one-liner / manual text) |
| `SparkBars` | `src/app/dashboard/_components/SparkBars.tsx` | 7-day sparkline bar chart |
| `StatCard` | `src/app/dashboard/_components/StatCard.tsx` | Stat card with sparkline |
| `ProjectVitalSigns` | `src/app/projects/[id]/_components/ProjectVitalSigns.tsx` | Per-project: active members, cost today, exception flags |
| `VerdictBanner` | `src/app/projects/[id]/_components/VerdictBanner.tsx` | On Track / Needs Attention / At Risk verdict with explanation |
| `ExecSummaryButton` | `src/app/projects/[id]/_components/ExecSummaryButton.tsx` | Four-state header button cluster: "View report" (all users with a summary), "Export PDF" (all users with a summary), "Regenerate" (canGenerate && hasSummary), "Generate report" (canGenerate && !hasSummary) |
| `RepoContextPanel` | `src/app/projects/[id]/_components/RepoContextPanel.tsx` | Linked GitHub repo metadata + snapshot status |
| `RecentCommitsAccordion` | `src/app/projects/[id]/_components/RecentCommitsAccordion.tsx` | Expandable list of recent commit events |
| `StatusBox` | `src/app/projects/[id]/_components/StatusBox.tsx` | Member manual status entry box |
| `PromptsClient` | `src/app/prompts/_components/PromptsClient.tsx` | Prompt library table with create/edit/deactivate |
| `ProductiveRulesClient` | `src/app/admin/productive-rules/_components/ProductiveRulesClient.tsx` | Rule management UI |
| `TokensClient` | `src/app/admin/tokens/_components/TokensClient.tsx` | Token list with revoke/delete actions |
| `InstallClient` | `src/app/install/_components/InstallClient.tsx` | Repo install step: shows agent token, curl command, settings.json snippet |
| `MachineSetupSection` | `src/app/install/_components/MachineSetupSection.tsx` | Machine install step: user token generation, machine-script curl command |
| `InviteAcceptClient` | `src/app/invite/[id]/_components/InviteAcceptClient.tsx` | Invite acceptance form |
| UI primitives | `src/components/ui/` | Button, Card, Input, Label, Form, EmptyState, LoadingSkeleton, RiskBadge, AuthDotWave, BlurTextAnimation, AuthLeftPanel |
| `CodeHealthRing` | `src/app/projects/[id]/_components/CodeHealthRing.tsx` | Client component; SVG ring showing worst-of reliability/security/maintainability grade (A-E); quality gate badge; coverage/duplication pcts; "Run Scan" button (MANAGER/LINE_MANAGER only); "Not scanned yet — run a scan" empty state. |

---

## Authentication & Authorization

### Session Authentication

`src/lib/auth.ts` configures NextAuth v5 with:
- **No OAuth providers** — login is handled entirely by `POST /api/auth/login` (custom credential route)
- **JWT session strategy** — session data lives in a signed JWT cookie
- **Custom sign-in page** — `/login`
- **Session payload** — `userId`, `activeOrganisationId`, `sessionVersion`. Role-less since PM3: `role`/`teamId`/`isLineManager` are resolved per-request from the `Membership` row by `withAuthScoped`, never stored in the JWT.

`src/lib/withAuthScoped.ts` is the central auth + scope resolver for all session-protected API routes and server components. It:
1. Calls `auth()` to retrieve the session
2. **Session version drift check**: compares `session.user.sessionVersion` (from JWT) against `User.sessionVersion` in the DB (cached 30 s). If they differ, the session is invalidated — forcing re-login after role changes, team reassignments, or password changes
3. Returns an `AuthContext` with `userId`, `organisationId`, `role`, `teamId`, `isLineManager`, and an `AuthScope` (derived visibility flags)

### Bearer Token Authentication (Ingest)

Two bearer token types are used by machine-side agents:

**`AgentToken`** (per-developer, per-project) — used by `POST /api/ingest/event` and `POST /api/ingest/time`:
- Resolved by `src/lib/resolveAgentToken.ts`: looks up `AgentToken` rows by `(projectId, tokenPreview, revokedAt: null)`, then bcrypt-verifies each candidate. Falls back to legacy `Project.agentTokenHash` via `verifyTokenWithGrace()` (supports a grace window for rotated tokens)
- `src/lib/resolveAgentTokenGlobal.ts` resolves without knowing `projectId` (used by the install script endpoint)

**`UserToken`** (per-user, machine-wide) — used by `POST /api/ingest/time`:
- Resolved by `src/lib/userToken.ts`: looks up `UserToken` rows by `tokenPreview`, then bcrypt-verifies. Returns `userId`, `organisationId`, `teamId`

Both token types use `bcrypt(AGENT_TOKEN_PEPPER + rawToken, 12)` and store only the last 4 characters (`tokenPreview`) for fast candidate narrowing.

All ingest routes also verify a **HMAC-SHA256 signature** (`x-pulse-signature` header) using the raw token as the key and the raw request body as the message, using `crypto.timingSafeEqual`. This is a cheap gate applied before the bcrypt comparison.

### Role-Based Access Control (RBAC)

Three roles enforced at the API layer in every route handler:

| Role | Team | Visibility | Write capabilities |
|---|---|---|---|
| `MANAGER` | None (org-level, `teamId IS NULL`) | All teams, all projects, all members' time | Full: team CRUD, role changes, global rules, all tokens, exec summaries, audit log, budget |
| `LINE_MANAGER` | One team | Own team's projects, own team members' time | Per-team: create/edit projects on own team, assign members, rotate that team's project tokens, exec summaries for own team's projects, team-scoped rules |
| `MEMBER` | One team | Own team's projects + teammates' activity | Post own manual statuses, view own time data only |

### Password Security

`src/lib/password.ts`: minimum 12 characters, must contain letter + digit + symbol. Bcrypt cost 12. Account lockout via `User.failedLogins` + `User.lockedUntil`.

---

## Database Layer

**ORM**: Prisma 7.8.0  
**Driver**: `@prisma/adapter-pg` (connection pool via `pg.Pool`)  
**Database**: PostgreSQL  
**Client output**: `src/generated/prisma`  
**Connection**: `DATABASE_URL` env var

The singleton `db` client is created in `src/lib/db.ts`, which also sets the `pg` TIMESTAMP type parser to treat all timestamps as UTC.

### Models

#### `Organisation`
Top-level tenant entity. All other models carry `organisationId`. Currently one organisation per deployment in v1.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `name` | `String` | Indexed |
| `anthropicApiKeyEnc` | `String?` | AES-256-GCM encrypted Anthropic API key; IV+authTag+ciphertext as base64. Set by MANAGER via `POST /api/admin/org/anthropic-key`. |
| `anthropicKeyHint` | `String?` | Obscured hint (e.g. `sk-ant-api0...abcd`) shown to MANAGER on install page; never the raw key. |
| Relations | — | users, teams, projects, prompts, activityEvents, intelligence, intelligenceHighlights, auditEntries, memberDailyTime, productiveRules, executiveSummaries, invitations, githubInstallations, userTokens, readinessSnapshots, codeHealthSnapshots |

#### `User`
Identity and authentication record only. Organisation membership, role, and team assignment live exclusively in `Membership` (dropped from `User` in PM6 migration `20260622000001_drop_user_legacy_cols`).

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id` | |
| `email` | `String @unique` | |
| `name`, `bio`, `jobTitle`, `location` | `String` / `String?` | |
| `passwordHash` | `String` | bcrypt, never exposed |
| `isActive` | `Boolean` | login lockout; checked by `POST /api/auth/login` |
| `failedLogins` | `Int` | account lockout counter |
| `lockedUntil` | `DateTime?` | |
| `sessionVersion` | `Int @default(0)` | incremented on role/team changes; JWT drift detection |
| `tenantKey` | `String?` | reserved for multi-tenant |

#### `Membership` — sole source of truth for role/team/org
**The tenancy boundary and RBAC authority.** One row per `(user, organisation)` pair. `withAuthScoped` performs a single composite-indexed `findUnique` on `(userId, organisationId)` for every authenticated request; the row IS the proof that the user belongs to the active org and is the authoritative source of `role`, `teamId`, and `isLineManager`. The JWT carries `activeOrganisationId` only as a hint — a tampered claim resolves to no row → 401. The legacy `User.organisationId/role/teamId/isLineManager` columns were dropped in PM6 (migration `20260622000001_drop_user_legacy_cols`); they no longer exist on the `User` table.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `userId` | `String` | FK → User, onDelete: Cascade |
| `organisationId` | `String` | FK → Organisation, onDelete: Cascade |
| `role` | `Role @default(MEMBER)` | source of `ctx.role` post-PM3 |
| `teamId` | `String?` | FK → Team, onDelete: SetNull; source of `ctx.teamId` post-PM3 |
| `isLineManager` | `Boolean @default(false)` | source of `ctx.isLineManager` post-PM3 |
| `status` | `MembershipStatus @default(ACTIVE)` | PM5: `ACTIVE` (full access) or `PENDING` (invite sent, no access yet). Added in migration `20260621203926_membership_status`. |
| `createdAt` | `DateTime @default(now())` | login picks the user's first Membership by `createdAt ASC` |
| `updatedAt` | `DateTime @updatedAt` | |
| Unique | — | `[userId, organisationId]` — both the de-dup constraint and the `findUnique` lookup key |
| Indexes | — | `[userId]`, `[organisationId]`, `[userId, status]` (PM5) |

**PM3 authentication flow:** login resolves the user's first **ACTIVE** Membership and stamps its `organisationId` into the JWT as `activeOrganisationId`. The JWT no longer carries `role`/`teamId`/`isLineManager`. Every authenticated request goes through `withAuthScoped`, which: (1) decodes the JWT via NextAuth's signature-verifying `auth()`, (2) reads `session.user.activeOrganisationId` (the hint), (3) reads `session.user.id` (verified `token.sub`), (4) calls `db.membership.findUnique({ where: { userId_organisationId: { userId, organisationId: activeOrganisationId } } })`, **(5) PM5: returns `null` (→ 401) if `membership.status !== "ACTIVE"`**, (6) returns `null` (→ 401) if no row, (7) returns an `AuthContext` populated from the row otherwise. Four forge tests (`src/tests/pm3-forge-*.test.ts`) prove the boundary against cross-org access, header forging, JWT-claim tampering, and mid-session revocation. Three additional PM5 forge tests prove that a PENDING membership grants no access, no org switching, and that invitation accept atomically flips PENDING→ACTIVE.

#### `Team`
| Column | Type | Notes |
|---|---|---|
| `timeTrackingEnabled` | `Boolean @default(false)` | toggle per team by MANAGER |
| `aiUsesTime` | `Boolean @default(false)` | controls whether time data is fed to narration |
| `tenantKey` | `String?` | |
| `organisationId` | `String` | |
| Indexes | — | `[timeTrackingEnabled]`, `[organisationId]` |

#### `Project`
| Column | Type | Notes |
|---|---|---|
| `status` | `ProjectStatus` | ACTIVE / PAUSED / ARCHIVED |
| `teamId` | `String` | NOT NULL — every project owned by exactly one team |
| `agentTokenHash` | `String?` | legacy project-level token hash |
| `agentTokenPreview` | `String?` | legacy preview |
| `previousTokenHash` | `String?` | grace window for token rotation |
| `previousTokenExpiresAt` | `DateTime?` | grace window expiry |
| `devTokenBudget` | `Int?` | visibility-only dev Claude Code token budget |
| `githubRepoFullName` | `String?` | e.g. `axis-org/marlin-api` |
| `githubInstallationId` | `String?` | GitHub App installation ID |
| `repoMetadata` | `Json?` | name, description, defaultBranch, languages, htmlUrl, visibility |
| `repoSnapshot` | `Json?` | topLevelTree, keyConfigs, detectedFrameworks, generatedAt |
| `repoContextRefreshedAt` | `DateTime?` | |
| `repoContextStatus` | `RepoContextStatus @default(NONE)` | NONE / LINKED / REFRESHING / ERROR |
| `repoContextError` | `String?` | truncated error, no secrets |
| `contextBranchBaselineSha` | `String?` | baseline commit SHA used for drift comparison; set by `POST /drift/baseline` |
| `tenantKey` | `String?` | |
| `organisationId` | `String` | |
| Indexes | — | `[status]`, `[teamId, status]`, `[organisationId]` |
| Relations | — | agentTokens, activityEvents, intelligence, executiveSummaries, members, readinessSnapshots, codeHealthSnapshots, securityScanRuns, contextDriftAssessments |

#### `Prompt`
P-number prompt library entry.

| Column | Type | Notes |
|---|---|---|
| `pNumber` | `Int` | unique per organisation |
| `fingerprint` | `String` | normalized first ~200 chars for Jaccard matching |
| `isActive` | `Boolean @default(true)` | |
| `tenantKey` | `String?` | |
| `organisationId` | `String` | |
| Unique | — | `[organisationId, pNumber]` |
| Indexes | — | `[isActive]`, `[organisationId]` |

#### `ActivityEvent`
Central activity record. Every ingest call lands here.

| Column | Type | Notes |
|---|---|---|
| `kind` | `EventKind` | CLAUDE_HOOK / MANUAL_STATUS |
| `pNumberDetected` | `Int?` | matched P-number from Jaccard |
| `promptId` | `String?` | FK → Prompt |
| `sessionExcerpt` | `String?` | redacted, ≤1500 chars |
| `filesChanged` | `String[]` | |
| `gitSummary` | `String?` | commit message / diff stat summary |
| `gitCommitSha` | `String?` | |
| `manualText` | `String?` | MANUAL_STATUS text |
| `hookSource` | `String?` | PostToolUse / Stop / UserPromptSubmit |
| `feedSummary` | `String?` | Groq-generated one-liner (5–8 words) |
| `redactionCount` | `Int @default(0)` | secrets redacted count |
| `claudeInputTokens`, `claudeOutputTokens`, `claudeCacheCreateTokens`, `claudeCacheReadTokens` | `Int?` | developer token usage (Stop hook) |
| `claudeModel` | `String?` | e.g. `claude-sonnet-4-6` |
| `claudeSpendUSD` | `Float?` | pre-computed cost from hook |
| `sourceMessageUuid` | `String?` | dedup key — last transcript message UUID; `[projectId, sourceMessageUuid]` unique |
| `sessionDurationSeconds` | `Int?` | Claude Code session span (seconds) from transcript timestamps; Stop events only; idempotent via `sourceMessageUuid` upsert |
| `tenantKey`, `organisationId` | `String?` / `String` | |
| Indexes | — | `[projectId, ingestedAt]`, `[userId, ingestedAt]`, `[projectId, userId, ingestedAt]`, `[projectId, kind, ingestedAt]`, `[organisationId]` |

#### `Intelligence`
AI-generated narration per project. One row per unique `inputHash`.

| Column | Type | Notes |
|---|---|---|
| `triggeringEventId` | `String` | event that triggered generation |
| `inputHash` | `String` | SHA-256 of normalised inputs (delta gate) |
| `headline` | `String?` | 8–12 word plain English sentence |
| `narration` | `String` | 3–4 sentence manager brief (kept for backward compat — exec summary, dashboard card still read this directly) |
| `stage` | `String?` | early / mid / hardening / blocked |
| `riskLevel` | `String @default("LOW")` | LOW / MEDIUM / HIGH |
| `riskFocus` | `String?` | plain-English risk description |
| `modelUsed` | `String` | `llama-3.3-70b-versatile` |
| `inputTokens`, `outputTokens` | `Int @default(0)` | |
| Unique | — | `[projectId, inputHash]` |
| Indexes | — | `[projectId, generatedAt]`, `[organisationId]` |
| Relations | — | `highlights IntelligenceHighlight[]` |

#### `IntelligenceHighlight`
One highlight bullet per AI narration row. Each highlight is structurally tied to a real `ActivityEvent` that was in the narration input window — `filterHighlights` in `src/lib/narrate.ts` drops any `sourceEventId` not in the provided event set before insert. Added in migration `20260614000002_add_intelligence_highlights`.

| Column | Type | Notes |
|---|---|---|
| `intelligenceId` | `String` | FK → Intelligence (onDelete: Cascade) |
| `text` | `String` | one plain-English highlight sentence |
| `sourceEventId` | `String` | validated against input set — never hallucinated |
| `sourceEventKind` | `String` | EventKind of the source event |
| `sourceCommitSha` | `String?` | gitCommitSha of source event if present |
| `organisationId` | `String` | FK → Organisation (tenancy) |
| Indexes | — | `[intelligenceId]`, `[organisationId]` |

#### `ReadinessSnapshot`
One marker-scan result per project per invocation. Stores the output of `scanMarkersInDir` + `readCoveragePct`. Used to build a rolling OLS forecast of marker burn-down velocity. Added in migration `20260614000003_add_readiness_snapshot`.

| Column | Type | Notes |
|---|---|---|
| `projectId` | `String` | FK → Project (onDelete: Cascade) |
| `organisationId` | `String` | FK → Organisation (tenancy) |
| `markerCount` | `Int` | sum of all marker types (TODO + FIXME + skippedTests + stubbed) |
| `markerDetail` | `Json` | `{ todo, fixme, skippedTests, stubbed, testFileCount }` breakdown; `testFileCount` added in R2 (old rows have no key — widget uses `?? 0`) |
| `coveragePct` | `Float?` | lines coverage % from coverage-summary.json; null = not measured |
| `scannedAt` | `DateTime` | default now() |
| Indexes | — | `[projectId, scannedAt]`, `[organisationId]` |

#### `SecurityScanRun`
One security scan invocation record per project. Stores metadata about a completed Semgrep CE / gitleaks / osv-scanner run. Added in migration `20260615000002_add_security_findings`.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `projectId` | `String` | FK → Project (onDelete: Cascade) |
| `organisationId` | `String` | FK → Organisation |
| `scannedAt` | `DateTime @default(now())` | |
| `scanSource` | `ScanSource @default(CENTRAL)` | reuses existing enum |
| `toolsRun` | `Json` | names of tools actually executed |
| `findingCount` | `Int @default(0)` | total findings across all tools |
| Indexes | — | `[projectId, scannedAt]`, `[organisationId]` |
| Relations | — | `project Project`, `findings SecurityFinding[]` |

#### `SecurityFinding`
One finding row per issue discovered during a security scan. Added in migration `20260615000002_add_security_findings`.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `scanRunId` | `String` | FK → SecurityScanRun (onDelete: Cascade) |
| `projectId` | `String` | FK → Project (onDelete: Cascade) |
| `organisationId` | `String` | FK → Organisation |
| `tool` | `String` | "semgrep" / "gitleaks" / "osv-scanner" |
| `ruleId` | `String?` | Semgrep rule ID or gitleaks rule ID; null for osv-scanner |
| `severity` | `SecuritySeverity` | CRITICAL / HIGH / MEDIUM / LOW / INFO |
| `message` | `String` | human-readable finding description |
| `file` | `String?` | relative file path, if applicable |
| `line` | `Int?` | line number in file, if applicable |
| Indexes | — | `[projectId, organisationId]` |
| Relations | — | `scanRun SecurityScanRun` |

#### `ContextDriftAssessment`
One context drift assessment per trigger event per project. Stores the result of comparing committed code against the last baseline SHA.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `projectId` | `String` | FK → Project (onDelete: Cascade) |
| `organisationId` | `String` | FK → Organisation |
| `tenantKey` | `String?` | |
| `status` | `DriftAssessmentStatus @default(PENDING)` | PENDING / RUNNING / COMPLETE / ERROR |
| `triggeredBy` | `DriftTriggerSource` | ON_DEMAND / VOLUME / MAJOR_EVENT / SYSTEM |
| `contextSource` | `String` | "context_builds" / "docs_on_default" / "none" |
| `baselineSha` | `String?` | commit SHA used as baseline |
| `headSha` | `String?` | commit SHA at assessment time |
| `changedFiles` | `String[]` | list of files changed between baseline and head |
| `diffTruncated` | `Boolean @default(false)` | true if diff exceeded token limit |
| `healthScore` | `Int?` | 0–100 composite score; null until COMPLETE |
| `riskLevel` | `DriftRiskLevel?` | GREEN / AMBER / RED; null until COMPLETE |
| `findings` | `Json?` | array of `DriftFinding` objects |
| `findingsCount` | `Int?` | total findings count |
| `aiTokensUsed` | `Int?` | total tokens consumed by the AI analysis |
| `costUSD` | `Float?` | estimated USD cost of the AI analysis |
| `error` | `String?` | error message if status = ERROR |
| `assessedAt` | `DateTime @default(now())` | |
| `createdAt` | `DateTime @default(now())` | |
| `updatedAt` | `DateTime @updatedAt` | |
| Indexes | — | `[projectId, assessedAt]`, `[organisationId]` |

#### `TechnicalDebtScan`
One technical debt scan invocation per project. Stores state machine progress and SonarQube results (Phase B) plus AI synthesis findings (Phase D). Added in migration `20260626072627_add_technical_debt_scan`.

##### Phase D — AI Synthesis Pipeline

Phase D adds AI synthesis as the final SYNTHESISING step, executed inside `src/lib/debt/orchestrate.ts` after the SONAR step writes raw metrics:

- **`synthesise.ts`** — `synthesiseDebtFindings({ organisationId, sonarIssues, securityFindings, detectedFrameworks })` calls the AI provider via Vercel AI SDK `generateText` (using `getAutoCallModel()`). Ceiling-gated via `isCeilingExceeded` before every call. Empty evidence fast-path: when both `sonarIssues` and `securityFindings` are empty, the AI is never called and `{ findings: [], score: 100 }` is returned immediately.
- **`compute-score.ts`** — `computeDebtScore(findings): number` deterministically computes the 0–100 `debtScore` from P1–P4 finding counts: `100 − (P1×20 + P2×10 + P3×4 + P4×1)`, floored at 0. The score is never AI-emitted — prevents model inflation or deflation.
- **`SonarEngineResult` now returns `issues: SonarIssue[]`** — the already-fetched Sonar issues array is passed through to the orchestrator at no additional API cost (no duplicate call).
- **Two anti-hallucination guards** applied before storage: (1) *realFiles Set* — every finding's `evidence.files` must contain at least one file from actual Sonar issues or SecurityFindings; (2) *priority guard* — `priority` must be exactly one of `P1`/`P2`/`P3`/`P4`; any other string is dropped.
- **Synthesis failure → ERROR**: if `isCeilingExceeded` is true or AI JSON parse fails, the scan is marked ERROR. Raw Sonar data written at the SYNTHESISING step is preserved either way.
- **No GRAPH source in Phase D**: only `SONAR` and `SECURITY_SCAN` evidence sources are used; Graphify integration is deferred.
- **DB fields populated on COMPLETE**: `findings (Json)` — array of `TechDebtFinding` objects; `findingsCount` — count of P1–P4 AI findings (distinct from `issueCount` = total Sonar issues); `debtScore` — 0–100 deterministic score; `aiTokensUsed`; `costUSD`.
- **`DebtScanClient.tsx`** renders `debtScore` as a colour-coded `MetricCell` (≥80 green / 50–79 amber / <50 red) and a `FindingCard` list per finding with priority pill, category, title, description, evidence, and recommendation. Clean repos with no findings show an honest empty state.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `projectId` | `String` | FK → Project (onDelete: Cascade) |
| `organisationId` | `String` | FK → Organisation |
| `status` | `TechDebtScanStatus @default(PENDING)` | PENDING / RUNNING / COMPLETE / ERROR |
| `currentStep` | `TechDebtStep?` | DOWNLOADING / EXTRACTING / SONAR / SYNTHESISING / DONE; null when PENDING/ERROR |
| `sonarProjectKey` | `String?` | SonarQube project key used (Phase B) |
| `qualityGate` | `String?` | "PASS" / "FAIL" / "N/A" (Phase B) |
| `reliabilityRating` | `String?` | "A"–"E" / "N/A" (Phase B) |
| `securityRating` | `String?` | "A"–"E" / "N/A" (Phase B) |
| `maintainabilityRating` | `String?` | "A"–"E" / "N/A" (Phase B) |
| `techDebtMinutes` | `Int?` | SonarQube SQALE debt in minutes (Phase B) |
| `issueCount` | `Int?` | Total SonarQube issues BLOCKER+CRITICAL+MAJOR (Phase B) |
| `findings` | `Json?` | AI synthesis findings array (Phase D) |
| `findingsCount` | `Int?` | Total findings count |
| `criticalCount` | `Int?` | SonarQube BLOCKER severity issue count (Phase B) |
| `highCount` | `Int?` | SonarQube CRITICAL severity issue count (Phase B) |
| `debtScore` | `Int?` | 0–100 composite debt score (Phase D) |
| `aiTokensUsed` | `Int?` | Tokens used for AI synthesis (Phase D) |
| `costUSD` | `Float?` | AI synthesis cost (Phase D) |
| `error` | `String?` | Error message if status = ERROR |
| `scannedAt` | `DateTime @default(now())` | |
| Indexes | — | `[projectId, createdAt]`, `[organisationId]` |

#### `CodeHealthSnapshot`
One SonarQube scan result per project per invocation. Stores the ratings returned by the SonarQube REST API after a sonar-scanner run. Added in migration `20260614000004_add_code_health_snapshot`; `scanSource` added in `20260615000001_add_code_health_scan_source`.

| Column | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `projectId` | `String` | FK → Project (onDelete: Cascade) |
| `organisationId` | `String` | FK → Organisation |
| `sonarProjectKey` | `String` | `org-{orgId}-proj-{projectId}` for CENTRAL; `SONAR_PROJECT_KEY` for EDGE |
| `qualityGate` | `String` | "PASS" / "FAIL" / "N/A" |
| `reliabilityRating` | `String` | "A"–"E" or "N/A" |
| `securityRating` | `String` | "A"–"E" or "N/A" |
| `maintainabilityRating` | `String` | "A"–"E" or "N/A" |
| `coveragePct` | `Float?` | null = not measured |
| `duplicationPct` | `Float?` | null = not measured |
| `scanSource` | `ScanSource @default(CENTRAL)` | `CENTRAL` = server fetched tarball; `EDGE` = server scanned its own cwd |
| `scannedAt` | `DateTime @default(now())` | |
| Indexes | — | `[projectId, scannedAt]`, `[organisationId]` |

---

#### `AuditLogEntry`
Immutable audit trail.

| Column | Type | Notes |
|---|---|---|
| `action` | `String` | e.g. SUMMARY_GENERATE, EDIT_PROJECT, REVOKE_AGENT_TOKEN, INVITE_ACCEPTED, REPO_LINK, etc. |
| `subjectId` | `String?` | ID of the affected resource |
| `meta` | `Json?` | action-specific context |
| `ipAddress` | `String?` | from x-forwarded-for |
| Indexes | — | `[userId, at]`, `[subjectId, at]`, `[action, at]`, `[at]`, `[organisationId]` |

#### `ProjectMember`
Join table — which users are members of which projects.

| Columns | `@@id([projectId, userId])` | Indexes: `[userId]` |

#### `TimeTrackingConsent`
One row per user. Records when and at which version the user acknowledged time tracking.

| Column | Type | Notes |
|---|---|---|
| `acknowledgedAt` | `DateTime?` | null = not yet acknowledged |
| `consentVersion` | `Int @default(1)` | v1 = seconds only; v2 = includes top-app names. v1 rows are stale for v2 scope |
| Indexes | — | `[acknowledgedAt]` |

#### `MemberDailyTime`
Daily time buckets per user from the time-tracking agent.

| Column | Type | Notes |
|---|---|---|
| `day` | `DateTime` | UTC midnight |
| `timezone` | `String` | user's local timezone |
| `workedSeconds` | `Int @default(0)` | total at-keyboard (not AFK) time |
| `productiveSeconds` | `Int` | |
| `unproductiveSeconds` | `Int @default(0)` | workedSeconds = productiveSeconds + unproductiveSeconds |
| `topApps` | `Json?` | top 2 productive + top 2 unproductive apps. Null until v2 consent |
| `source` | `String @default("activitywatch")` | |
| Unique | — | `[userId, day]` |
| Indexes | — | `[userId, day]`, `[organisationId]` |

#### `ProductiveAppRule`
Rules for classifying apps/URLs as productive or unproductive.

| Column | Type | Notes |
|---|---|---|
| `pattern` | `String` | app name pattern |
| `matchType` | `MatchType` | EXACT / GLOB / REGEX |
| `category` | `String?` | |
| `isProductive` | `Boolean @default(true)` | |
| `scope` | `RuleScope` | GLOBAL / TEAM |
| `teamId` | `String?` | null for global rules |
| Indexes | — | `[scope, isActive]`, `[teamId, isActive]`, `[organisationId]` |

Rule evaluation (`src/lib/productive-rules.ts`): TEAM rules override GLOBAL rules when patterns match (case-insensitive); first-match wins within a merged list.

#### `ExecutiveSummary`
On-demand streaming executive summary, stored after generation.

| Column | Type | Notes |
|---|---|---|
| `body` | `String` | single paragraph, 5–8 sentences |
| `confidence` | `Float?` | 0.0–1.0 model-reported data richness score |
| `modelUsed` | `String` | `llama-3.3-70b-versatile` |
| Indexes | — | `[projectId, generatedAt]`, `[organisationId]` |

#### `Invitation`
| Column | Type | Notes |
|---|---|---|
| `invitedEmail` | `String` | |
| `teamId` | `String?` | |
| `role` | `Role` | |
| `status` | `InvitationStatus @default(PENDING)` | PENDING / ACCEPTED / DECLINED (DECLINED added in PM5 migration `20260621205617_invitation_status_declined`) |
| Indexes | — | `[invitedEmail, status]`, `[teamId]`, `[organisationId]` |

#### `AgentToken`
Per-developer, per-project agent tokens. Multiple per project (one per developer).

| Column | Type | Notes |
|---|---|---|
| `userId` | `String?` | null for legacy backfilled rows |
| `createdById` | `String?` | |
| `label` | `String @default("")` | display label |
| `tokenHash` | `String` | `bcrypt(AGENT_TOKEN_PEPPER + raw, 12)` — never exposed |
| `tokenPreview` | `String` | last 4 chars — fast lookup |
| `revokedAt` | `DateTime?` | null = active |
| `revokedById` | `String?` | |
| Indexes | — | `[projectId, revokedAt]`, `[projectId, tokenPreview]`, `[userId]` |

#### `UserToken`
Per-user machine-wide token (one per user). Used by the time-tracking ingest path.

| Column | Type | Notes |
|---|---|---|
| `userId` | `String @unique` | |
| `tokenHash` | `String` | same bcrypt scheme as AgentToken |
| `tokenPreview` | `String` | last 4 chars |
| Indexes | — | `[tokenPreview]`, `[organisationId]` |

#### `GithubInstallation`
Records GitHub App installations for an organisation.

| Column | Type | Notes |
|---|---|---|
| `installationId` | `String` | GitHub installation ID |
| `accountName` | `String` | GitHub account/org name |
| `status` | `GithubInstallationStatus` | ACTIVE / INVALID |
| Unique | — | `[organisationId, installationId]` |
| Indexes | — | `[organisationId]` |

---

## API Routes

All routes under `src/app/api/`. Session-authenticated routes use `withAuthScoped()`. Ingest routes use Bearer token + HMAC.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET/POST` | `/api/auth/[...nextauth]` | — | NextAuth JWT handlers (session management, CSRF-protected sign-out) |
| `POST` | `/api/auth/login` | public | Credential login: verifies password, checks account lock, creates JWT session |
| `POST` | `/api/auth/signup` | public | New user registration |
| `GET` | `/api/auth/memberships` | Session | Lists the caller's memberships only. `userId` derived from the verified session via `withAuthScoped`; the route handler accepts no parameters (`GET()` is parameter-less, blocking any URL/header/body input route). Response: `{ memberships: [{ organisationId, organisationName, role, teamId }] }`. |
| `POST` | `/api/auth/switch-org` | Session + CSRF | Re-issues the JWT with a new `activeOrganisationId` after verifying `(ctx.userId, organisationId) ∈ Membership` (same composite-key check as `withAuthScoped`). Member → 200 + `Set-Cookie`. Non-member → 403, no Set-Cookie. Goes through the CSRF middleware gate (not in `CSRF_BYPASS_PREFIXES`). |
| `GET` | `/api/auth/pending-invitations` | Session | PM5: Returns the caller's PENDING memberships with associated `invitationId`. Used by `AppShell` to compute `pendingInviteCount` for the `OrgBadge` amber dot. Response: `{ memberships: [{ organisationId, organisationName, invitationId }] }`. |

### Ingest

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/ingest/event` | Bearer AgentToken + HMAC | Claude Code hook event ingest. Pipeline: size check → HMAC verify → Zod validate → token resolve → project status check → rate limit → redact → P-number match → persist ActivityEvent → fire-and-forget narration + Groq feed summary |
| `POST` | `/api/ingest/time` | Bearer UserToken or AgentToken + HMAC | Daily time bucket upsert. Accepts three-bucket model (worked/productive/unproductive seconds) + optional topApps (v2 consent required). Supports both UserToken (machine-wide) and AgentToken (project-scoped) paths |

### Projects

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/projects` | Session | List projects scoped to org/team |
| `POST` | `/api/projects` | Session (MANAGER or LINE_MANAGER of own team) | Create project; LINE_MANAGER scoped to `ctx.teamId` (Membership-verified, not JWT); returns 201 with one-time `agentToken`; audited |
| `GET` | `/api/projects/[id]` | Session | Get project (strips `agentTokenHash`) |
| `PATCH` | `/api/projects/[id]` | Session (MANAGER or LINE_MANAGER of team) | Edit project; can trigger `linkRepoAndRefresh` |
| `DELETE` | `/api/projects/[id]` | Session (MANAGER) | Delete project |
| `POST` | `/api/projects/[id]/summary` | Session (MANAGER or LINE_MANAGER) | Streaming executive summary via Groq llama-3.3-70b-versatile; rate limited 10/hr/project; audited |
| `GET` | `/api/projects/[id]/ai-summary` | Session | Retrieve stored executive summary |
| `GET` | `/api/projects/[id]/export` | Session (all roles, own team) | PDF export; rate limited 20/hr/project. MEMBER role receives a spend-free PDF (`spendUSD: null`); `MemberDailyTime` is fetched only when `canSeeSpend` is true. |
| `GET/POST` | `/api/projects/[id]/agent-tokens` | Session | List/create per-developer tokens for project |
| `POST` | `/api/projects/[id]/rotate-token` | Session (MANAGER or LINE_MANAGER) | Rotate project-level legacy token (grace window) |
| `GET/POST` | `/api/projects/[id]/members` | Session | List/add project members |
| `GET` | `/api/projects/[id]/members/[userId]/events` | Session | Member's events on project |
| `POST` | `/api/projects/[id]/repo-context/refresh` | Session | Trigger GitHub repo snapshot refresh; rate limited 6/hr/project |
| `GET` | `/api/projects/[id]/readiness` | Session (all roles, own team) | Retrieve latest readiness signal: marker counts, coverage %, OLS forecast |
| `POST` | `/api/projects/[id]/readiness/scan` | Session (MANAGER or LINE_MANAGER) | Run a local marker scan + coverage read, persist snapshot; rate limited 1/60s/project |
| `GET` | `/api/projects/[id]/code-health` | Session (all roles, own team) | Retrieve latest stored SonarQube scan result. Returns `{snapshot: CodeHealthSnapshot|null}`. Zero SonarQube calls in the request path. |
| `POST` | `/api/projects/[id]/code-health/scan` | Session (MANAGER or LINE_MANAGER) | **CENTRAL path** (connected repo): verify GithubInstallation ownership, auto-provision SonarQube project, download repo tarball, scan in temp dir, clean up. **EDGE path** (no GitHub link): scan server's own cwd. Rate limited 1/120s/project; max 2 concurrent scans. Returns 503 if env vars missing or semaphore full. |
| `POST` | `/api/projects/[id]/security-scan` | Session (MANAGER or in-team LINE_MANAGER) | Reuses Phase 9b tarball plumbing; downloads repo tarball, runs Semgrep CE + gitleaks + osv-scanner, persists `SecurityScanRun` + `SecurityFinding` rows. Rate limited 1/120s/project. Returns `{ scanRunId, findingCount, findings[] }`. |
| `GET` | `/api/projects/[id]/security-findings` | Session (all roles, own team) | Returns `{ scanState: "not_scanned"\|"scanned_clean"\|"has_findings", scanRun, findings[] }`. Zero CLI calls in the request path. |
| `POST` | `/api/projects/[id]/drift` | Session (MANAGER or LINE_MANAGER) | Triggers a new `ContextDriftAssessment`; rate-limited 3/hr/project; writes CONTEXT_ASSESS audit; returns `{ assessmentId, status: "PENDING" }` 202 |
| `GET` | `/api/projects/[id]/drift` | Session (all roles, own team) | Lists last 10 drift assessments for the project scoped to organisationId |
| `POST` | `/api/projects/[id]/drift/baseline` | Session (MANAGER or LINE_MANAGER) | Resolves context source, stores `contextBranchBaselineSha` on the Project, writes CONTEXT_BASELINE_SET audit |
| `GET` | `/api/projects/[id]/drift/[assessmentId]` | Session (all roles, own team) | Triple-scoped fetch (assessmentId + projectId + organisationId); calls `resetStaleRunningAssessments()` before read |
| `POST` | `/api/projects/[id]/debt-scan` | Session (MANAGER or in-team LINE_MANAGER) | Trigger a technical debt scan; duplicate guard returns 409; rate-limited 1/30min/project; returns `{ scanId, status: "PENDING" }` 202 |
| `GET` | `/api/projects/[id]/debt-scan` | Session (MANAGER or in-team LINE_MANAGER) | List latest 10 `TechnicalDebtScan` records for the project |
| `GET` | `/api/projects/[id]/debt-scan/[scanId]` | Session (MANAGER or in-team LINE_MANAGER) | Poll a single scan; calls `resetStaleRunningDebtScans()` before read |

### Agent Tokens

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/agent-tokens/[tokenId]/revoke` | Session (MANAGER or LINE_MANAGER) | Set `revokedAt`; audited |
| `DELETE` | `/api/agent-tokens/[tokenId]` | Session (MANAGER or LINE_MANAGER) | Hard-delete (only if already revoked); audited |
| `POST` | `/api/agent-tokens/[tokenId]/restore` | Session | Restore a revoked token |

### GitHub

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/github/installations/[id]/repos` | Session (MANAGER or LINE_MANAGER); rate limited 30/min | List repos accessible to a GitHub App installation; cross-tenant guarded |
| `DELETE` | `/api/github/installations/[id]` | Session (MANAGER or LINE_MANAGER) | Remove installation record |
| `POST` | `/api/github/installations/refresh` | Session (MANAGER or LINE_MANAGER); rate limited 5/min | Re-validate all org installations, update ACTIVE/INVALID status |
| `GET` | `/api/github/callback` | — | GitHub App OAuth callback |
| `GET` | `/api/github/connect` | Session | Initiate GitHub App installation |

### Teams

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET/POST` | `/api/teams` | Session | List teams / create team (MANAGER only) |
| `GET/PATCH` | `/api/teams/[id]` | Session | Get / edit team; rate limited 30/hr/user |

### Prompts

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET/POST` | `/api/prompts` | Session (POST: MANAGER or LINE_MANAGER) | List all prompts / create new prompt with Jaccard fingerprint |
| `PATCH/DELETE` | `/api/prompts/[id]` | Session (MANAGER or LINE_MANAGER) | Edit or deactivate prompt |

### Admin

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET/POST` | `/api/admin/members` | Session (MANAGER or LINE_MANAGER) | **GET (PM3 Phase 2):** queries `Membership(status=ACTIVE)` filtered by `organisationId`; LINE_MANAGER additionally filters by `teamId`. Merges `m.role`/`m.isLineManager` from Membership into the User fields — role is never read from `User`. **POST (PM5 fix):** when the invited email matches an existing user, creates PENDING `Membership` + `Invitation` atomically in a `$transaction`; returns 409 `already_a_member` (ACTIVE) or `invitation_already_pending` (PENDING) on duplicates. New-email path creates `Invitation` only (Membership created on accept). LINE_MANAGER can only invite to own team with MEMBER role. |
| `GET/PATCH/DELETE` | `/api/admin/members/[id]` | Session (MANAGER) | **GET:** existence check via `Membership` composite-key lookup; returns merged User+Membership fields. **PATCH (PM3 Phase 3):** `teamId` change writes to `Membership.teamId` (never `User.teamId`); name change writes to `User.name`. **DELETE:** deactivate member. |
| `POST` | `/api/admin/members/[id]/activate` | Session (MANAGER or LINE_MANAGER own-team) | **PM3 Phase 3b:** existence check via `Membership` composite-key lookup (`userId_organisationId`). LINE_MANAGER team boundary reads `membership.teamId`. Writes `isActive: true` + `sessionVersion++` to `User`. Emits `ACTIVATE_MEMBER` audit action. Response merges `membership.user` fields with `role`/`isLineManager`/`teamId` from Membership. |
| `POST` | `/api/admin/members/[id]/deactivate` | Session (MANAGER or LINE_MANAGER own-team) | PM3 Phase 3b: same Membership existence check pattern as activate. Writes `isActive: false` + `sessionVersion++` to `User`. |
| `POST` | `/api/admin/members/[id]/promote` | Session (MANAGER) | **PM3 Phase 3:** writes `{ role: "LINE_MANAGER", isLineManager: true }` to `Membership` (not `User`). `User.sessionVersion` is still incremented for JWT invalidation. Calls `invalidateSessionVersionCache`. |
| `POST` | `/api/admin/members/[id]/demote` | Session (MANAGER) | **PM3 Phase 3:** writes `{ role: "MEMBER", isLineManager: false }` to `Membership` (not `User`). **Q21 guard:** `membership.count({ where: { status:"ACTIVE", role:"MANAGER", NOT:{userId} } })` — blocks demoting the last active MANAGER in the org; returns 409 `last_manager_cannot_demote`. |
| `POST` | `/api/admin/members/[id]/assign-to-team` | Session (MANAGER) | **PM3 Phase 3:** writes `teamId` to `Membership` (not `User`). |
| `POST` | `/api/admin/members/[id]/remove-from-team` | Session (MANAGER) | **PM3 Phase 3:** nulls `teamId` in `Membership` (not `User`). |
| `POST` | `/api/admin/members/[id]/role` | Session (MANAGER) | **PM3 Phase 3:** writes `role`/`isLineManager` to `Membership` (not `User`). **Q21 guard:** same `membership.count` last-manager check as demote route. |
| `GET` | `/api/admin/members/[id]/card` | Session (MANAGER or LINE_MANAGER own-team; MEMBER blocked) | **PM3 Phase 3b:** existence check via `Membership` composite-key lookup. Per-member detail card: identity, AI spend, time, projects, sessions, commits. Query: `?window=today\|7d\|30d` (default `7d`), `?todayCutoff=<epochMs>` (viewer's local midnight). Dual-tz windowing: time section uses member's IANA tz; event sections use viewer tz. `lastSeenAt` is all-time. |
| `GET` | `/api/admin/budget` | Session (MANAGER) | Monthly AI spend breakdown by project |
| `PATCH` | `/api/admin/budget/[id]` | Session (MANAGER) | Edit per-project dev token budget |
| `GET/POST` | `/api/admin/invitations` | Session (MANAGER) | List / create invitations |
| `POST` | `/api/admin/cleanup` | Bearer `INTERNAL_CLEANUP_TOKEN` | Data lifecycle cleanup |

### Productive Rules

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET/POST` | `/api/productive-rules` | Session (POST: MANAGER or LINE_MANAGER); POST rate limited 30/hr | List all rules / create rule |
| `PATCH` | `/api/productive-rules/[id]` | Session (MANAGER or LINE_MANAGER); rate limited 30/hr | Update rule |

### Consent / Profile / Misc

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/consents/acknowledge` | Session | Acknowledge time-tracking consent (sets `acknowledgedAt`, `consentVersion = 2`) |
| `GET` | `/api/me/time` | Session | Own time data (7-day week + today); topApps gated by v2 consent |
| `GET` | `/api/users/[id]/time` | Session; rate limited 60/min | Another user's time data; MEMBER can only see self |
| `POST` | `/api/status` | Session; rate limited 30/min/userId | Post manual status update (creates `ActivityEvent` with `kind=MANUAL_STATUS`) |
| `PATCH` | `/api/events/[id]/p-number` | Session | Override P-number on an event |
| `POST` | `/api/profile/change-password` | Session | Change own password; increments `sessionVersion` |
| `PATCH` | `/api/profile/update` | Session | Update name/bio/jobTitle/location |
| `GET` | `/api/dashboard/summary` | Session | Dashboard stats (events, active members, prompts matched, sparklines, feed) |
| `GET` | `/api/audit` | Session (MANAGER) | Paginated audit log |

### Install

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/install/script` | Bearer AgentToken (global resolve) | Returns a self-contained bash install script with embedded `pulse-send.mjs`, `transcript-delta.mjs`, `redact.mjs`, agent token, and project ID |
| `GET` | `/api/install/machine-script` | Bearer UserToken | Returns a machine-level setup bash script |
| `POST` | `/api/install/user-token` | Session | Generate or rotate a `UserToken` for the current user |

### Infrastructure

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | public | Health check: DB ping (`SELECT 1`), returns `{ db, lastEventAgeSeconds, claudeBudgetRemaining }` |
| `GET` | `/api/metrics` | public | Prometheus text format metrics (`pulse_request_latency_seconds`, `pulse_request_total`, `pulse_claude_tokens_total`) |
| `POST` | `/api/invite/accept` | public | Accept invitation: creates new user (with name + password) or migrates existing user to new org/team |
| `POST` | `/api/invite/decline` | Session | PM5: Idempotent decline — deletes the PENDING Membership row for the caller and marks the Invitation as DECLINED. No CSRF bypass (uses session cookie). |

---

## Observability & Monitoring

### Sentry (`@sentry/nextjs` 10.56.0)

Initialised in two places (both in Next.js instrumentation hooks):

| File | Runtime | Config |
|---|---|---|
| `instrumentation.ts` | nodejs (`NEXT_RUNTIME === "nodejs"`) + edge (`NEXT_RUNTIME === "edge"`) | `dsn: SENTRY_DSN`, `sendDefaultPii: false`, `tracesSampleRate: 0.1`, `environment: NODE_ENV` |
| `instrumentation-client.ts` | browser (client bootstrap) | `dsn: NEXT_PUBLIC_SENTRY_DSN`, `sendDefaultPii: false`, `tracesSampleRate: 0.1`, replays disabled (`replaysSessionSampleRate: 0`, `replaysOnErrorSampleRate: 0`) |

> **Note**: `sentry.server.config.ts`, `sentry.edge.config.ts`, and `sentry.client.config.ts` are NOT present in the repository. All Sentry initialisation happens via the two instrumentation hook files above.

Session replay is explicitly disabled in `instrumentation-client.ts`.

**Production startup gate** (`instrumentation.ts`): the check is inside `if (process.env.NEXT_RUNTIME === "nodejs")` — it only runs in the Node.js server runtime. If `NODE_ENV === "production"` and `CLAUDE_MONTHLY_CEILING_USD` is not set, the server throws at startup (`[startup] CLAUDE_MONTHLY_CEILING_USD must be set in production`). The edge runtime does NOT enforce this guard.

### Pino Logger (`pino` 10.3.1)

`src/lib/logger.ts`: structured JSON logger with 20+ redacted paths:

```
password, passwordHash, agentToken, agentTokenHash, sessionExcerpt, manualText,
tenantKey, secret, apiKey, jwt, bearerToken,
req.headers.authorization, req.headers['x-pulse-signature'],
req.headers['x-internal-token'], headers.authorization,
headers['x-pulse-signature'], headers['x-internal-token'],
Authorization, authorization
```

Log level configured via `LOG_LEVEL` env var (default: `info`).

### Prometheus Metrics (`src/lib/metrics.ts`)

In-memory, module-level singleton (single-process, promoted to Redis at 4x scale). Exported at `GET /api/metrics` as Prometheus text format (content-type `text/plain; version=0.0.4`).

**Metrics**:
- `pulse_request_latency_seconds` — histogram with 11 buckets (0.005 s → 10 s) per route+method
- `pulse_request_total` — counter by route+method+status_class (2xx/4xx/5xx)
- `pulse_claude_tokens_total_input` / `pulse_claude_tokens_total_output` — per-project narration token counters

14 known routes are pre-registered so they appear with zero traffic.

### In-memory OTel Tracing (`src/lib/otel.ts`)

Custom OpenTelemetry-compatible span tracing for the ingest pipeline. Stores only the **last completed trace** in memory. Each `POST /api/ingest/event` call produces 5 named spans: `ingest`, `redact`, `gate`, `ai`, `store`. Used for build-evidence capture via `/api/metrics`.

### Cost Ceiling Banner

`src/app/layout.tsx` reads `CLAUDE_MONTHLY_CEILING_USD` and the current month's narration spend from `Intelligence` aggregates. If spend ≥ ceiling, a red fixed banner is rendered at the top of every page.

---

## Rate Limiting

All limiters use `@upstash/ratelimit` (sliding window) when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are configured, falling back to in-memory sliding windows for dev/test. Upstash failures are fail-open (`allowed: true`).

| Module | Endpoint protected | Limit | Window | Key |
|---|---|---|---|---|
| `src/lib/ratelimit.ts` | `POST /api/ingest/event` | 60/min × `SCALE_TIER` multiplier (4x = 240/min) | 60 s | per token (project ID) |
| `src/lib/ratelimit-login.ts` | `POST /api/auth/login` | 5/min AND 20/hour (dual window, both must pass) | 60 s + 3600 s | per IP |
| `src/lib/ratelimit-switch-org.ts` | `POST /api/auth/switch-org` | 10/min AND 60/hour (dual window) | 60 s + 3600 s | per userId |
| `src/lib/ratelimit-time.ts` | `POST /api/ingest/time` | 30/min | 60 s | per token/userId |
| `src/lib/ratelimit-github.ts` | `GET /api/github/installations/[id]/repos` | 30/min | 60 s | per userId |
| `src/lib/ratelimit-github.ts` | `POST /api/github/installations/refresh` | 5/min | 60 s | per userId |
| `src/lib/ratelimit-users-time.ts` | `GET /api/users/[id]/time` | 60/min | 60 s | per caller userId |
| `src/lib/ratelimit-productive-rules.ts` | `POST/PATCH /api/productive-rules` | 30/hour | 3600 s | per userId |
| `src/lib/ratelimit-teams-patch.ts` | `PATCH /api/teams/[id]` | 30/hour | 3600 s | per userId |
| `src/lib/summary-ratelimit.ts` | `POST /api/projects/[id]/summary` | 10/hour × `SCALE_TIER` | 3600 s | per projectId |
| `src/lib/summary-ratelimit.ts` | `GET /api/projects/[id]/export` | 20/hour × `SCALE_TIER` | 3600 s | per projectId |
| `src/lib/status-ratelimit.ts` | `POST /api/status` | 30/min | 60 s | per userId |
| `src/lib/repo-context-ratelimit.ts` | `POST /api/projects/[id]/repo-context/refresh` | 6/hour × `SCALE_TIER` | 3600 s | per projectId |
| `src/lib/ratelimit-code-health.ts` | `POST /api/projects/[id]/code-health/scan` | 1/120s | 120 s | per projectId |
| `src/lib/ratelimit-security-scan.ts` | `POST /api/projects/[id]/security-scan` | 1/120s | 120 s | per projectId |
| `src/lib/ratelimit-member-card.ts` | `GET /api/admin/members/[id]/card` | 30/min | 60 s | per caller userId |
| `src/lib/ratelimit-debt-scan.ts` | `POST /api/projects/[id]/debt-scan` | 1/30min | 30 min | per projectId |

**`SCALE_TIER`** env var (values: `0.5x`, `1x`, `4x`) multiplies limits for `ingest/event`, `summary`, `export`, and `repo-context/refresh`. Default is `1x`.

---

## External Integrations

### Groq API (`@ai-sdk/groq`, model `llama-3.3-70b-versatile`)

Used for three AI functions, all via the Vercel AI SDK:

1. **Narration** (`src/lib/narrate.ts`): `generateText()` with a structured JSON prompt. Returns `{ headline, narration, stage, riskLevel, riskFocus }`. Fired asynchronously (fire-and-forget) from `POST /api/ingest/event` after persisting the event. Auth: `GROQ_API_KEY` env var.

2. **Feed summary** (`src/lib/gemini.ts`): `generateText()` with a short action-phrase prompt. Produces a 5–8 word one-liner for the activity feed. Max 64 output tokens, temperature 0.3. Auth: `GROQ_API_KEY`. (Note: file named `gemini.ts` historically; `GEMINI_API_KEY` in `.env.example` is not used by this code path.)

3. **Executive summary** (`src/app/api/projects/[id]/summary/route.ts`): `streamText()` returning a Server-Sent Events stream. Writes `ExecutiveSummary` row on completion, including parsed `confidence` score. Auth: `GROQ_API_KEY`.

**Delta gating** (narration only, `src/lib/narrate.ts`):
- `inputHash = SHA-256(pNumberDetected | lastCommitSha | filesChangedBucket | sessionExcerpt | gitSummary | eventKind | repoContextRefreshedAt)` — skips narration if hash matches latest `Intelligence.inputHash`
- 90-second in-memory cooldown per project (prevents concurrent burst)
- Monthly cost ceiling check via `src/lib/cost-ceiling.ts` (pricing: Sonnet $3/M input, $15/M output)

### GitHub App (REST API)

`src/lib/repo-context/client.ts` authenticates using RS256-signed JWTs (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY` as base64 PEM). Installation access tokens are fetched and cached for 50 minutes (expire at 60 min).

Outbound fetch is gated to `api.github.com` only (`githubFetch` enforces a hostname allowlist).

**Repo snapshot** (`src/lib/repo-context/snapshot.ts`): fetches top-level git tree (up to 20 entries), reads up to 8 key config files from an allowlist (`package.json`, `Dockerfile`, `next.config.mjs`, `README.md`, etc., 21 total), extracts up to 4096 bytes per file, runs the redactor over all content, and stores `repoMetadata` + `repoSnapshot` JSON on the `Project`.

Multiple GitHub App installations are supported per organisation via the `GithubInstallation` table.

### SonarQube Community Build (Docker)

External static analysis engine used for code health scoring. Runs as a Docker container (`sonarqube:community`, LGPL-3.0) on the same host as the application.

- **Metrics API**: accessed via `SONAR_HOST_URL` (Node.js process → SonarQube REST API). Endpoint: `/api/measures/component`. Fetches `reliability_rating`, `security_rating`, `sqale_rating`, `alert_status`, `coverage`, `duplicated_lines_density`.
- **Scanner**: invoked via `docker run sonarsource/sonar-scanner-cli:latest` using `child_process.execSync` inside the POST scan route. The container communicates with SonarQube at `SONAR_SCANNER_HOST_URL` (typically `http://host.docker.internal:9000` locally; `http://sonarqube:9000` on Coolify service network).
- **Authentication**: SonarQube user token stored in `SONAR_TOKEN`. Admin token (`SONAR_ADMIN_TOKEN`) used only for `ensureSonarProject` provisioning call (separate from scan token).
- **Central scan flow**: server fetches GitHub repo tarball via `authedGithubFetch` → extracts to `/tmp/pulse-scan-{projectId}-{ts}/src/` → mounts into sonar-scanner container → deletes temp dir in `finally`.
- **Project key scheme**: `org-{orgId}-proj-{projectId}` for connected repos (CENTRAL); `SONAR_PROJECT_KEY` env var for EDGE path.
- **Project key**: configured via `SONAR_PROJECT_KEY` env var and `sonar-project.properties` at project root.
- **Startup script**: `scripts/sonarqube-start.sh` starts the `axis-pulse-sonarqube` Docker container with JVM caps (web/CE 256 MB, Elasticsearch 512 MB) and polls `/api/system/status` until UP.

---

### Local CLI Security Scanners

Three CLI tools are invoked by `src/lib/security-scan.ts` during a security scan:

- **Semgrep CE** (`semgrep`): SAST tool that runs OWASP and security ruleset patterns against the extracted source tree. Exit code 0 = no findings, 1 = findings found (both treated as success). Severity mapping: `ERROR`→HIGH, `WARNING`→MEDIUM, anything else→INFO.
- **gitleaks** (`gitleaks`): Secret detection scanner. Searches for hard-coded credentials, API keys, and tokens. Every finding is mapped to severity CRITICAL.
- **osv-scanner** (`osv-scanner`): Open-source vulnerability scanner that checks package manifests against the OSV database. Severity derived from `database_specific.severity` field (`MODERATE`→MEDIUM) or CVSS vector heuristic.

All three tools must be installed on the host running the Next.js server. Missing tools produce 0 findings (catch-and-continue); they do not cause the route to return an error. The scan reuses the same tarball lifecycle as Phase 9b central code-health scans: `downloadRepoTarball` → `extractTarball` → run tools → `rmSync(tmpDir)` in `finally`.

After all tools have run, `runAllSecurityTools` applies `stripSrcPrefix(filePath, srcDir)` to every finding's `file` field. This converts absolute temp-dir paths (e.g. `C:\...\pulse-sec-scan-...\src\module\file.py`) to repo-relative paths (e.g. `module/file.py`) before the findings are persisted to the DB.

### Upstash Redis

Used for distributed rate limiting when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set. Sliding window algorithm via `@upstash/ratelimit`. All limiters degrade gracefully to in-memory equivalents when Upstash is unavailable.

### Sentry (see Observability section)

### Redaction Pipeline (`src/lib/redact.ts`)

Applied to `sessionExcerpt` before storage. Strips:
- Env-file values (`KEY=VALUE` style)
- JWT tokens (`eyJ...`)
- Anthropic API keys (`sk-ant-…`)
- OpenAI-style keys (`sk-` + 20+ alphanum)
- AWS access keys (`AKIA`/`ASIA` prefix)
- PEM private key blocks
- URL-embedded credentials (`scheme://user:pass@host`)

Output truncated to 1500 characters after redaction.

---

## Middleware

`src/middleware.ts` wraps every request (matcher: all paths except `_next/static`, `_next/image`, `favicon.ico`).

### CSRF Gate

All `POST`, `PATCH`, `DELETE` requests must carry either `authjs.csrf-token` or `__Host-authjs.csrf-token` cookie. Missing cookie → `403 { error: "CSRF token required" }`.

**Bypass list** (Bearer-authenticated or public endpoints that don't use session cookies):
```
/api/auth/signup, /api/auth/login, /api/ingest, /api/invite, /api/status,
/api/admin/cleanup, /api/__test, /api/internal-test, /api/install/script,
/api/install/machine-script, /api/projects/:id/summary (regex match)
```

`/api/auth/signout` is **intentionally not** in the bypass list — a POST to signout without the CSRF cookie returns 403.

### Authentication Guard

Public path prefixes (no auth required):
```
/login, /signup, /invite, /api/auth, /api/health, /api/ingest, /api/invite,
/api/metrics, /api/admin/cleanup, /api/__test, /api/internal-test,
/api/productive-rules, /api/install/script, /api/install/machine-script
```

Non-public routes without a session:
- API routes → `401 { error: "Unauthorized" }`
- Page routes → redirect to `/login`

### Security Headers

Applied to **every response** (including 401/403 responses) by `applySecurityHeaders()` in `src/middleware.ts`:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | Per-request nonce (see below) |

> **Note**: `X-Frame-Options` and `Permissions-Policy` headers are **not** set by the middleware (verified: `src/middleware.ts:29-35`). This is documented as a security gap in `docs/risk.md §1.4`.

### CSP Nonce

A per-request nonce is generated via `btoa(crypto.randomUUID())` and:
1. Set in the `Content-Security-Policy` header as `'nonce-<value>'` with `'strict-dynamic'`
2. Forwarded to the Next.js runtime as the `x-nonce` request header (so Next.js stamps its generated inline scripts)

Development mode adds `'unsafe-eval'` for webpack source maps. The SHA-256 hash `sha256-h/a3dzouJnjzmkHHjG4hModJ0q40LLSvkVgy5i5MrN8=` is also trusted (Anthropic API).

---

## Multi-tenancy

The system runs as a **single-organisation deployment** in v1. Multi-tenancy is architected but not activated:

- The `Organisation` model exists as the top-level tenant entity
- Every table carries `organisationId` (non-nullable FK to `Organisation`) used for **all query scoping**
- `withAuthScoped()` always adds `organisationId: ctx.organisationId` to every DB where clause via `orgWhere(ctx)`
- A nullable `tenantKey` column is reserved on `User`, `Team`, `Project`, `Prompt`, `ActivityEvent`, `Intelligence`, `ExecutiveSummary`, `MemberDailyTime`, `ProductiveAppRule`, `Invitation`, `UserToken` — allowing a future multi-tenant migration without breaking schema changes. Note: `Organisation`, `AgentToken`, and `GithubInstallation` do **not** have `tenantKey` columns (verified: `prisma/schema.prisma`).
- Cross-tenant access is prevented at the API layer: all resource lookups include `organisationId: ctx.organisationId` in the where clause; GitHub installation lookups verify `organisationId` before returning data
- The `GithubInstallation` unique constraint `[organisationId, installationId]` prevents cross-org installation sharing

To activate true multi-tenancy, a future phase would promote `tenantKey` from a reserved nullable column to an enforced discriminator and add a tenant resolution layer at the middleware boundary.

---

## Onboarding Tour Engine

A first-time onboarding tour for new users. The engine mounts inside `AppShellClient` and activates when `User.hasOnboarded = false`. When `hasOnboarded = true` it is a zero-cost passthrough — no renders, no listeners, no polling. On tour completion or skip, it calls `PATCH /api/me/onboarding` to set `hasOnboarded = true` permanently.

### Persistence
Step position is stored in the `pulse-tour-step` first-party cookie (24-hour expiry, SameSite=Lax, non-httpOnly, JS-readable). The cookie survives hard reloads and cross-route navigations without a DB write per step.

### State Machine (`src/lib/tour/reducer.ts`)
```
inactive  ──[INIT, on route]──────► polling
inactive  ──[INIT, off route]─────► waiting
polling   ──[TARGET_FOUND]────────► active
polling   ──[TARGET_MISSING]──────► missing  (3 s timeout)
waiting   ──[ARRIVED_ON_ROUTE]────► polling
active    ──[ADVANCE, on route]───► polling
active    ──[ADVANCE, off route]──► waiting
active/missing ──[EXIT]───────────► inactive
```

### Advance Modes
- `{ on: "click" }` — `addEventListener("click", handler, { once: true })` on the spotlight target
- `{ on: "navigate"; to }` — `usePathname()` change watcher triggers advance when `to` matches. If `to` ends with `/` (e.g. `"/projects/"`), prefix matching is used so any `/projects/[id]` route triggers the advance.
- `{ on: "next" }` — button in `TourTooltip` calls `onNext` directly. The button label is `step.buttonText ?? "Next →"` (e.g. "Start" on the welcome step, "Go to dashboard" on the done step).

### Route Matching (`routePrefix`)
Steps on dynamic routes (e.g. `/teams/[id]`, `/projects/[id]`) set `routePrefix: "/teams/"` or `"/projects/"`. `matchesRoute(step, path)` returns `true` if `path === step.route` OR `path.startsWith(step.routePrefix)`. This is used in `activateStep`, `advance`, and the route-change effect. Steps without `routePrefix` still use exact matching.

### Per-step Poll Timeout (`pollTimeout`)
Steps whose target appears only after a user action (e.g. submitting a create-project form to reveal the token) set `step.pollTimeout` in milliseconds. The default is 3 000 ms. `project-token-copy` sets 120 000 ms so the user has 2 minutes to fill the form before the engine falls back to `missing` state.

### Role Filtering and Render Context
`filterSteps(steps, role)` applied at provider mount. Steps with a `roles` array are shown only to matching roles; steps without `roles` show to all. `TourProvider` accepts a `renderCtx: TourRenderContext` prop (`{ role, hasTeam, hasProject, firstProjectId? }`) from `AppShell`, which is forwarded through `AppShellClient`. Stub conditions evaluate `renderCtx` to swap copy when a condition is true (e.g. LINE_MANAGER with no project sees "once a project exists…" copy on project-detail steps). `firstProjectId` is used by `navigateTo` functions on feature-only steps (e.g. `project-ai-narration`) to auto-navigate to the first available project. `TourStep` supports an optional `navigateTo?: string | ((ctx: TourRenderContext) => string)` field; when present, `TourProvider` calls `router.push(navigateTo)` when activating the step.

### Completion vs. Skip
`advance()` past the last step calls `doExit().then(() => router.push("/dashboard"))`. `skip()` calls `doExit()` only — no redirect. This keeps the "Go to dashboard" final step meaningful.

### Retake Tour (`/profile`)
`RetakeTourButton` on the profile page calls `PATCH /api/me/onboarding { hasOnboarded: false }`, clears the `pulse-tour-step` cookie via `clearTourCookie()`, then `router.push("/dashboard")` to re-trigger the engine.

### Never-Trap Guarantee
The overlay is 4 separate `position: fixed` divs surrounding (but not covering) the spotlight target. The spotlight ring div has `pointer-events: none` so clicks pass through to the real element. In `missing` state (target not found within poll timeout), the overlay is skipped entirely — only the tooltip and Skip button render. Esc key always calls `skip()`.

### Dual-Tour Architecture (Phase 5)

Phase 5 introduces two distinct tour modes, selected by the `pulse-tour-kind` cookie:

- **first-run tour** (`pulse-tour-kind` absent or `"first-run"`): activates when `User.hasOnboarded = false`. Includes creation steps (creating a team, creating a project, copying the project token). Intended for new users who have no data yet.
- **feature tour** (`pulse-tour-kind = "feature"`): activates when the user clicks "Take the tour again" on `/profile`. `RetakeTourButton` writes the `pulse-tour-kind=feature` cookie before pushing to `/dashboard`. Skips all creation steps; educational only. Allows existing users to revisit the tour without being required to create another team or project.

`filterSteps(steps, role, tourMode, ctx)` applies three filters: role membership, `availableIn` field (`"first-run"` | `"feature"` | absent = both), and `skipIf(ctx)` predicate (evaluated at mount time, not per step).

### Advance Modes
- `{ on: "click" }` — `addEventListener("click", handler, { once: true })` on the spotlight target
- `{ on: "navigate"; to }` — `usePathname()` change watcher triggers advance when `to` matches. If `to` ends with `/` (e.g. `"/projects/"`), prefix matching is used so any `/projects/[id]` route triggers the advance.
- `{ on: "next" }` — button in `TourTooltip` calls `onNext` directly. The button label is `step.buttonText ?? "Next →"` (e.g. "Start" on the welcome step, "Go to dashboard" on the done step).
- `{ on: "element-appears"; target }` — `TourProvider` polls the DOM at 200 ms intervals and advances automatically when `document.querySelector(target)` becomes non-null. Used by `project-create-modal` to advance only after the project-creation form is actually submitted and the token copy element appears. The polling is started in `activateStep` (early-exit path) and driven by a `useEffect` that starts/stops the interval based on engine state.

### Cookies

| Cookie | Purpose | Notes |
|---|---|---|
| `pulse-tour-step` | Current step ID (resume on reload) | 24-hour expiry, SameSite=Lax, non-httpOnly |
| `pulse-tour-kind` | Tour mode: `"first-run"` (default) or `"feature"` | Written by `RetakeTourButton`; cleared by `TourProvider` on exit |

### Step Inventory (Phase 6 — 25 steps)

**First-run only (9 steps):**
| id | roles | advance | notes |
|---|---|---|---|
| `welcome` | M+LM | next ("Start") | Centered, no spotlight; sentinel selector |
| `dashboard-cta` | MANAGER | click | Links to team creation |
| `teams-new-team` | MANAGER | click | Opens new-team modal |
| `teams-modal` | MANAGER | navigate `/teams/` | Spotlights entire dialog card; advance on navigate to `/teams/[id]`; replaced `teams-create-btn` |
| `project-new-project` | M+LM | click | routePrefix `/teams/`; live-DOM poll crosses page navigation |
| `project-create-modal` | M+LM | element-appears `[data-tour='project-token-copy']` | Spotlights entire form card; advances only after project is created and token element appears |
| `project-token-copy` | M+LM | click | pollTimeout 120 000 ms |
| `project-token-saved` | M+LM | click | Both token elements appear simultaneously |
| `project-open` | M+LM | navigate `/projects/` | routePrefix `/teams/`; drives user to project detail; stubbed for LM !hasProject |

**Feature only (7 steps):**
| id | roles | advance | notes |
|---|---|---|---|
| `feature-welcome` | M+LM | next | Centered; replaces `welcome` in feature mode |
| `project-ai-narration` | M+LM | next | `skipIf: !hasProject`; auto-navigates to first project via `navigateTo`; spotlights `AISummaryPanel` |
| `nav-prompts-feature` | M+LM | next | Auto-navigates to `/prompts` via `navigateTo` |
| `context-analyser-main` | M+LM | next | Auto-navigates to `/context-analyser` via `navigateTo` |
| `nav-cost-dashboard-feature` | M+LM | next | Auto-navigates to `/admin/cost-dashboard` via `navigateTo` |
| `nav-install-feature` | M+LM | click | Auto-navigates to `/install` via `navigateTo`; buttonText "Finish tour" |
| `done` | M+LM | next ("Go to dashboard") | Centered, no spotlight; fires router.push("/dashboard") |

**First-run only — navigation steps (3 steps, moved from shared in Phase 6):**
| id | roles | advance | notes |
|---|---|---|---|
| `nav-prompts` | M+LM | next | Sidebar; routePrefix `/`; `availableIn: "first-run"` |
| `nav-cost-dashboard` | M+LM | next | Sidebar; `availableIn: "first-run"` |
| `nav-install` | M+LM | click | Sidebar → /install; `availableIn: "first-run"` |

**Shared — both tour modes (6 steps):**
| id | roles | advance | notes |
|---|---|---|---|
| `project-verdict` | M+LM | next | routePrefix `/projects/`; stubbed for LM !hasProject |
| `project-exceptions` | M+LM | next | stubbed for LM !hasProject |
| `project-spend-ring` | M+LM | next | stubbed for LM !hasProject |
| `project-code-health` | M+LM | next | routePrefix `/projects/`; `data-tour="project-code-health"` on `CodeHealthRing` |
| `project-feature-progress` | M+LM | next | routePrefix `/projects/`; `data-tour="project-feature-progress"` on `FeatureAreaTrack` |
| `project-repo-context` | M+LM | next | routePrefix `/projects/`; `data-tour="project-repo-context"` on `RepoContextPanel` |

### Step Counts by Role and Mode
| Tour mode | Role | Data state | Steps shown |
|---|---|---|---|
| first-run | MANAGER | no data | 19 |
| first-run | LINE_MANAGER | no project | 16 |
| feature | MANAGER | with data | 13 |
| feature | MANAGER | no data | 20 |
| feature | LINE_MANAGER | with data | 13 |
| feature | LINE_MANAGER | no data | 17 |
| either | MEMBER | — | 0 |

### New `data-tour` Attributes (Phase 5)
| Value | Component | Notes |
|---|---|---|
| `teams-modal` | `NewTeamDialog.tsx` | Inner card; replaced `teams-create-btn` target |
| `project-create-modal` | `NewProjectDialog.tsx` | Form card |
| `project-code-health` | `CodeHealthRing.tsx` | On both section paths |
| `project-feature-progress` | `FeatureAreaTrack.tsx` | On both div paths |
| `project-repo-context` | `RepoContextPanel.tsx` | On all 4 return-path divs |
| `nav-teams` | `AppShellClient.tsx` | Wrapper div around Teams NavLink |
