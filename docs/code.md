# Code

> **Source verification**: All function signatures and patterns below were verified against actual source files. Last audit: 2026-06-13.

## Code Conventions & Patterns

### File Organisation
- All library utilities live in `src/lib/` as flat `.ts` files; no barrel `index.ts` unless a subdirectory warrants it (e.g. `src/lib/repo-context/`).
- Next.js 14 App Router route handlers are at `src/app/api/<resource>/route.ts`; nested dynamic segments use `[id]` directory naming.
- Tests mirror their subject with `src/tests/<name>.test.ts`; no `__tests__` directories.
- Generated Prisma client is emitted to `src/generated/prisma` (not `node_modules`), configured in `prisma/schema.prisma`.

### Naming Conventions
- Functions: camelCase (`generateNarration`, `resolveAgentToken`, `computeVerdict`).
- Types / interfaces: PascalCase (`AuthContext`, `ResolvedToken`, `VerdictResult`).
- Constants: UPPER_SNAKE_CASE for primitives (`BCRYPT_COST`, `COOLDOWN_MS`, `MAX_BODY_BYTES`).
- Internal / test-only reset helpers are prefixed with underscore: `_resetStatusRateLimitStore`, `_resetMetricsStore`.
- Rate-limiter modules follow the pattern `ratelimit-<endpoint>.ts`; their Upstash prefix strings follow `pulse:<resource>:<operation>`.

### TypeScript Usage Patterns
- `satisfies` is not used; `as const` is used for string literal arrays (e.g. `VALID_MATCH_TYPES`).
- Route handler return types are always `NextResponse` (or `Response` for streaming/PDF).
- DB query results that arrive as `bigint` from `$queryRaw` are always wrapped in `Number()` before arithmetic.
- `void` is used deliberately to suppress floating promises on fire-and-forget calls (e.g. `void generateNarration(event, project, traceCtx)`).
- Discriminated unions are used for token resolution results: `{ valid: true; userId: string | null } | { valid: false }`.
- The `db` singleton is exported from `src/lib/db.ts` and re-used across all modules; never instantiated per-request.
- Pure helper modules (e.g. `budget-utils.ts`, `productive-rules.ts`, `project-verdict.ts`) carry no server/DB imports and are explicitly safe to import in both Server and Client Components.
- Prisma adapter used is `@prisma/adapter-pg` (Edge-compatible pg pool adapter), not the default connector.
- `pg.types.setTypeParser` is called at module load to parse `TIMESTAMP WITHOUT TIME ZONE` columns as UTC.

---

## Key Functions Reference

### Authentication & Token Resolution

**[`src/lib/auth.ts`](src/lib/auth.ts)**

```ts
export const { handlers, auth, signIn, signOut } = NextAuth({ ... })
```
- Configures NextAuth with `strategy: "jwt"`, no providers (login is handled by the custom `/api/auth/login` route).
- `jwt` callback passes the token through unchanged.
- `session` callback maps `token.sub` → `session.user.id`; copies `activeOrganisationId` and `sessionVersion` from JWT claims into the session object. Post-PM3, `role`/`teamId`/`isLineManager` are NOT in the JWT — `withAuthScoped` reads them from the verified Membership row on every request. `activeOrganisationId` is a *hint*; the Membership composite-key lookup is the proof.
- Custom sign-in page: `/login`.

---

**[`src/lib/withAuthScoped.ts`](src/lib/withAuthScoped.ts)**

```ts
export async function withAuthScoped(): Promise<AuthContext | null>
```
- Calls `auth()` to get the (signature-verified) session; returns `null` if no session or no `activeOrganisationId` claim.
- Performs session-version drift check: compares `token.sessionVersion` against `db.user.sessionVersion` (cached 30 s in `_sessionVersionCache`). Returns `null` if they differ, forcing re-login.
- **PM3 anti-forge guard:** performs `db.membership.findUnique({ where: { userId_organisationId: { userId: session.user.id, organisationId: activeOrganisationId } } })`. The `userId` is sourced from the verified `token.sub`; the `organisationId` is the (untrusted) JWT claim. Returns `null` if no row — this is what makes a tampered `activeOrganisationId` claim resolve to 401.
- **PM5 status gate:** after the Membership row is found, returns `null` if `membership.status !== "ACTIVE"`. A `PENDING` membership grants no authenticated access; the caller receives a 401 without any hint about the pending state.
- Returns `AuthContext`: `{ userId, organisationId, role, teamId, isLineManager, scope }`. `role`, `teamId`, `isLineManager`, and the authoritative `organisationId` come from the Membership row, **not** from the JWT.
- `scope.allTeams` is `true` only for `MANAGER`; `scope.canSeeTimeData` is `false` for `MEMBER`.

```ts
export function invalidateSessionVersionCache(userId: string): void
export function orgWhere(ctx: AuthContext): { organisationId: string }
export function teamWhere(ctx: AuthContext): object
```
- `teamWhere` returns `{ organisationId }` for MANAGER, `{ teamId, organisationId }` for LINE_MANAGER, `{ id: "__none__" }` for MEMBER.

---

**[`src/lib/token.ts`](src/lib/token.ts)**

```ts
export function generateRawToken(): string
// crypto.randomBytes(32).toString("base64url")

export async function hashToken(raw: string): Promise<string>
// bcrypt.hash(AGENT_TOKEN_PEPPER + raw, 12)

export async function verifyToken(raw: string, hash: string): Promise<boolean>
// bcrypt.compare(AGENT_TOKEN_PEPPER + raw, hash)

export function tokenPreview(raw: string): string
// raw.slice(-4) — last 4 chars used as fast lookup hint

export async function verifyTokenWithGrace(
  raw: string,
  currentHash: string | null,
  previousHash: string | null,
  previousExpiresAt: Date | null
): Promise<boolean>
// Tries currentHash first; falls back to previousHash if not expired.
```

- `BCRYPT_COST = 12` for all agent tokens.
- Pepper is read from `process.env.AGENT_TOKEN_PEPPER` (empty string if unset).

---

**[`src/lib/resolveAgentToken.ts`](src/lib/resolveAgentToken.ts)**

```ts
export async function resolveAgentToken(
  rawToken: string,
  projectId: string,
): Promise<ResolvedToken>
// ResolvedToken = { valid: true; userId: string | null; tokenId: string | null } | { valid: false }
```
- Step 1: queries `AgentToken` by `(projectId, tokenPreview, revokedAt: null)`; bcrypt-verifies each candidate. Returns `{ valid: true, userId, tokenId }` on first match.
- Step 2: Legacy fallback — queries `Project.agentTokenHash` and calls `verifyTokenWithGrace`. Returns `{ valid: true, userId: null, tokenId: null }` on match (no developer attribution).
- Preview collision safety: loops over ALL candidates; never exits on first mismatching bcrypt.

---

**[`src/lib/resolveAgentTokenGlobal.ts`](src/lib/resolveAgentTokenGlobal.ts)**

```ts
export async function resolveAgentTokenGlobal(rawToken: string): Promise<ResolvedTokenGlobal>
// ResolvedTokenGlobal = { valid: true; projectId: string; userId: string | null; tokenId: string | null; userEmail: string | null } | { valid: false }
```
- Same two-step strategy as `resolveAgentToken` but cross-project — used by `/api/install/script` where `projectId` is unknown.
- Step 2 legacy path searches `Project` by `agentTokenPreview`.

---

**[`src/lib/userToken.ts`](src/lib/userToken.ts)**

```ts
export async function resolveUserToken(rawToken: string): Promise<ResolvedUserToken>
// ResolvedUserToken = { valid: true; userId: string; organisationId: string; teamId: string | null } | { valid: false }
```
- Queries `UserToken` by `tokenPreview`; bcrypt-verifies each candidate.
- On match, fetches `user.teamId` from DB and returns full context.
- Used by `/api/ingest/time` and `/api/productive-rules` (machine-wide time-tracking path).

---

### Rate Limiting

All rate limiters follow the same pattern: prefer Upstash Redis sliding window when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set; fall back to an in-memory `Map<string, number[]>` (sliding window) otherwise. On Upstash errors, the limiter defaults to `allowed: true` (fail-open).

| Module | Endpoint protected | Limit | Window | Key | Upstash prefix |
|---|---|---|---|---|---|
| [`ratelimit.ts`](src/lib/ratelimit.ts) | `POST /api/ingest/event` | 60/min × `SCALE_TIER` multiplier | 60 s | tokenKey (projectId) | `pulse:ingest:event` |
| [`ratelimit-time.ts`](src/lib/ratelimit-time.ts) | `POST /api/ingest/time` | 30/min | 60 s | tokenKey | `pulse:ingest:time` |
| [`ratelimit-login.ts`](src/lib/ratelimit-login.ts) | `POST /api/auth/login` | 5/min AND 20/hr (dual-window) | 60 s / 3600 s | IP address | `pulse:login:min` / `pulse:login:hour` |
| [`status-ratelimit.ts`](src/lib/status-ratelimit.ts) | `POST /api/status` | 30/min | 60 s | userId | in-memory only |
| [`summary-ratelimit.ts`](src/lib/summary-ratelimit.ts) | `POST /api/projects/:id/summary` | 10/hr × multiplier | 3600 s | projectId | in-memory only |
| [`summary-ratelimit.ts`](src/lib/summary-ratelimit.ts) | `GET /api/projects/:id/export` | 20/hr × multiplier | 3600 s | projectId | in-memory only |
| [`repo-context-ratelimit.ts`](src/lib/repo-context-ratelimit.ts) | `POST /api/projects/:id/repo-context/refresh` | 6/hr × multiplier | 3600 s | projectId | in-memory only |
| [`ratelimit-github.ts`](src/lib/ratelimit-github.ts) | `GET /api/github/installations/:id/repos` | 30/min | 60 s | userId | `pulse:github:repos` |
| [`ratelimit-github.ts`](src/lib/ratelimit-github.ts) | repo context refresh (GitHub API calls) | 5/min | 60 s | userId | `pulse:github:refresh` |
| [`ratelimit-users-time.ts`](src/lib/ratelimit-users-time.ts) | `GET /api/users/:id/time` | 60/min | 60 s | userId | `pulse:users:time` |
| [`ratelimit-productive-rules.ts`](src/lib/ratelimit-productive-rules.ts) | `POST/PATCH /api/productive-rules` | 30/hr | 3600 s | userId | `pulse:productive-rules` |
| [`ratelimit-teams-patch.ts`](src/lib/ratelimit-teams-patch.ts) | `PATCH /api/teams/:id` | 30/hr | 3600 s | userId | `pulse:teams:patch` |
| [`ratelimit-code-health.ts`](src/lib/ratelimit-code-health.ts) | `POST /api/projects/:id/code-health/scan` | 1/120s | 120 s | projectId | `pulse:code-health:scan` |

**Scale tier**: `SCALE_TIER` env var (`"1x"` default, `"4x"` supported). Multiplier = 4 at 4x, 1 at 1x and 0.5x. Applied to: ingest event, summary, export, repo-context refresh.

**Test helpers**: every in-memory limiter exports `_reset<Name>RateLimitStore()` for test isolation. Login exports `_checkLoginMemRateLimit(ip)` for conformance tests (bypasses the `NODE_ENV === "test"` bypass in the public function).

---

### Redaction Pipeline

**[`src/lib/redact.ts`](src/lib/redact.ts)**

```ts
export function redact(input: string): RedactResult
// RedactResult = { text: string; count: number; kinds: string[] }
```

Rules applied in order (each increments `count` and adds to `kinds`):

| Rule | Pattern | Kind |
|---|---|---|
| 1 — env-style assignment | `/^(\s*[A-Z][A-Z0-9_]+\s*=)(\S+)/gm` | `env` (+ nested kind if value matches jwt/sk-ant/sk/aws-key) |
| 2 — JWT | `/eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/g` | `jwt` |
| 3 — Anthropic key | `/sk-ant-[A-Za-z0-9_-]+/g` | `sk-ant` |
| 4 — OpenAI-style key | `/sk-[A-Za-z0-9]{20,}/g` | `sk` |
| 5 — AWS access key | `/(?:AKIA|ASIA)[A-Z0-9]{15,16}/g` | `aws-key` |
| 6 — PEM private key | `/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g` | `pem` |
| 7 — URL credentials | `/:\/\/[^:/?#\s]+:[^@\s]+@/g` — replaces with `://<PLACEHOLDER>@` | `url-creds` |

- Placeholder string: `[REDACTED]`.
- After all rules, output is truncated to `MAX_CHARS = 1500`. Truncation happens **after** redaction.
- `kinds` is deduplicated (Set); the same kind fires only once even if multiple matches occur.
- Rule 1 also tags nested secret kinds found in the value (e.g. if the value is a JWT, `jwt` is also added to `kinds`).

---

### Narration & AI

**[`src/lib/narrate.ts`](src/lib/narrate.ts)**

```ts
export async function generateNarration(
  event: ActivityEvent,
  project: Project,
  traceCtx?: TraceContext,
  anthropicApiKey?: string | null
): Promise<void>
```
- Model: `claude-haiku-4-5-20251001` via Anthropic (primary when `anthropicApiKey` set), falling back to free OpenRouter/Groq models via `getAutoCallModel`.
- `maxOutputTokens: 512`.
- Gate 1 — delta hash dedup: computes `computeInputHash` over `(pNumberDetected, lastCommitSha, filesChangedBucket sorted, sessionExcerpt, gitSummary, eventKind, repoContextRefreshedAt)`. Skips if latest `Intelligence` row for the project has the same hash.
- Gate 2 — cooldown: in-memory `Map<projectId, lastNarratedAt>`; skips if `< COOLDOWN_MS = 90_000 ms` since last narration. Cooldown is set **before** the API call to prevent concurrent bursts.
- Fetches up to 3 recent `MANUAL_STATUS` events for context.
- Optionally enriches with `MemberDailyTime` if `team.aiUsesTime === true`.
- Optionally includes `repoSnapshot` (detected frameworks, top-level tree, key config paths) if `project.repoSnapshot != null`.
- Strips markdown code fences from AI response before `JSON.parse`.
- Persists `Intelligence` row with: `headline`, `narration`, `stage`, `riskLevel`, `riskFocus`, `modelUsed`, `inputTokens`, `outputTokens`, `inputHash`, `triggeringEventId`, `organisationId`.
- Calls `recordClaudeTokens(projectId, inputTokens, outputTokens)` after persist.
- Never throws to caller — all errors logged via `console.error` and function returns `void`.

```ts
export function computeInputHash(inputs: InputHashInputs): string
// SHA-256 hex of canonical "|"-joined string; filesChangedBucket sorted before join.

export function resetCooldowns(): void
// Exported for test isolation only.
```

**System prompt summary**: instructs model to write plain English for a non-technical manager. Output format is JSON with keys `headline` (8–12 words), `narration` (3–4 sentences), `stage` (`"early"|"mid"|"hardening"|"blocked"|null`), `riskLevel` (`"LOW"|"MEDIUM"|"HIGH"`), `riskFocus` (string or null).

---

**[`src/lib/gemini.ts`](src/lib/gemini.ts)** (named `gemini` but uses Anthropic Haiku / free model fallback)

```ts
export async function generateFeedSummary(
  excerpt: string,
  filesChanged?: string[],
  gitSummary?: string | null,
  anthropicApiKey?: string | null,
): Promise<string | null>
```
- Model: `claude-haiku-4-5-20251001` via Anthropic (primary when `anthropicApiKey` set), falling back to free OpenRouter/Groq models. `maxOutputTokens: 64`. `temperature: 0.3`.
- Produces a 5–8 word action phrase (e.g. `"Fixed null reference in cost dashboard query"`).
- Returns `null` if no Anthropic key and neither `OPENROUTER_API_KEY` nor `GROQ_API_KEY` is set.
- Includes up to 6 file names and git summary as context.
- User message explicitly instructs the model: `"Respond with ONLY the 5-8 word action phrase. No explanation, no preamble."` to reduce prompt-echo.
- **Output validator** (`validateFeedSummary`) applied before returning any result. Returns `null` when:
  - Output (case-insensitive) contains any of: `"action phrase"`, `"past-tense"`, `"passive voice"`, `"trailing punctuation"`, `"5-8 word"`, `"subsystem"` — indicates the model echoed the system prompt.
  - Output starts with: `"we need to"`, `"write a"`, `"here is"`, `"here's"`, `"sure,"`, `"certainly"`, `"of course"`, `"note:"` — indicates preamble/meta commentary rather than the phrase.
  - Output contains newlines or JSON braces — multi-line or structured output.
  - Output exceeds 12 words or 90 characters.
- Accepted output is clamped: trimmed, trailing punctuation stripped.
- When `generateFeedSummary` returns `null`, the ingest route (`POST /api/ingest/event`) falls back to `firstSentence(excerpt)`.

```ts
export function validateFeedSummary(text: string): string | null
// Hard validator applied before returning any model output.
// Returns cleaned phrase or null (caller falls back to firstSentence).

export function firstSentence(text: string): string
// Cuts at first [.!\n] or 80 chars; trims trailing partial word.
// Used as fallback when generateFeedSummary returns null or throws.
```

---

### Database Helpers

**[`src/lib/db.ts`](src/lib/db.ts)**

```ts
export const db: PrismaClient
```
- Singleton pattern: `globalForPrisma.prisma ?? createPrismaClient()`. In non-production, stored on `globalThis` to survive hot-reload.
- Uses `@prisma/adapter-pg` with `pg.Pool({ connectionString: process.env.DATABASE_URL })`.
- Logging: `["error", "warn"]` in development; `["error"]` in production.
- `pg.types.setTypeParser(builtins.TIMESTAMP, val => new Date(val + "Z"))` applied at module load.

---

**[`src/lib/dashboard.ts`](src/lib/dashboard.ts)**

```ts
export async function fetchDashboardSummary(ctx: AuthContext): Promise<DashboardSummary>
```
- Runs 6 parallel DB queries: events today count, scoped members, prompt-matched events today, active projects count, 7-day event sparkline (raw SQL), 7-day prompt-match sparkline (raw SQL).
- MANAGER scope: org-wide. LINE_MANAGER scope: team-scoped.
- Active members = users with events in last 30 minutes; up to 8 names surfaced.
- Activity feed: last 20 events in 30-minute window where `hookSource = "Stop"` with `feedSummary` set OR `kind = "MANUAL_STATUS"`.
- `$queryRaw` returns `BigInt`; all aggregated fields wrapped in `Number()`.
- `SparklineWeek` type: `[number, number, number, number, number, number, number]` (index 0 = 6 days ago, index 6 = today).

---

**[`src/lib/project-status.ts`](src/lib/project-status.ts)**

```ts
export const IDLE_THRESHOLD_MS = 2 * 60 * 60 * 1000  // 2 hours

export function deriveStatus(
  status: string,
  lastActivityAt: string | null
): "Active" | "Idle" | "Paused" | "Archived"
```
- ARCHIVED → `"Archived"`, PAUSED → `"Paused"`.
- ACTIVE: idle if `lastActivityAt` is null or older than 2 hours → `"Idle"`, else `"Active"`.

---

**[`src/lib/project-verdict.ts`](src/lib/project-verdict.ts)**

```ts
export function computeVerdict(input: VerdictInput): VerdictResult
// VerdictLevel = "on_track" | "needs_attention" | "at_risk"
```
- PAUSED/ARCHIVED projects short-circuit to `on_track` immediately.
- Worst-signal-wins priority: `HIGH risk` → `at_risk`; `no activity 3 days` → `at_risk`; `active members + $0 cost` → `needs_attention`; `MED risk` → `needs_attention`; `no intel yet` → `needs_attention`; `intel > 48h old` → `needs_attention`.
- Always returns `thresholds: string[]` (6 threshold rules) for transparent UI display.

---

**[`src/lib/project-exceptions.ts`](src/lib/project-exceptions.ts)**

```ts
export function computeExceptionFlags(input: ExceptionInput): ExceptionFlag[]
// ExceptionFlag = { id: string; label: string; detail: string; severity: "critical" | "high" | "medium" | "low" | "info"; source?: string }
```
- Flags: `"high-risk"` (riskLevel HIGH), `"cost-spike"` (today > 2× 7-day average, requires ≥5 days history), `"stall-no-activity"` (no activity last 3 days), `"stall-no-cost"` (active today but $0), `"repo-stale"` (linked repo not refreshed in >14 days), `"budget-overrun"` (MTD spend > `computeNotionalBudgetUSD(devTokenBudget)`; only fires when `devTokenBudget` is non-null).
- `ExceptionInput` requires `monthlySpendUSD: number` (MTD spend) and `devTokenBudget: number | null` for the overrun alarm.

```ts
export type SecurityFindingGroup = {
  ruleId: string          // group key (ruleId or tool:message[:60] fallback)
  label: string           // plain-English label, never blank
  rawMessage: string      // full prose from the tool (shown when expanded)
  tool: string            // "semgrep" | "gitleaks" | "osv-scanner"
  severity: ExceptionFlag["severity"]  // highest severity seen in group
  occurrences: Array<{ file: string; line: number | null }>  // de-duped distinct locations
  totalCount: number      // raw DB count including dupes
}

export function groupSecurityFindings(findings: SecurityFindingLike[]): SecurityFindingGroup[]
```
- Groups raw findings by `ruleId` (or `tool:message[:60]` when `ruleId` is null). INFO-severity findings are excluded. Identical occurrences (same `file` + same `line`) are display-collapsed — `totalCount` still reflects the raw count. Group `severity` is promoted to the highest seen within the group. Result sorted worst-severity-first.
- `label` is derived from `RULE_LABELS` lookup first (plain-English for known semgrep/gitleaks rules), then for osv-scanner uses the message directly, then for unknowns falls back to title-casing the last dotted segment of the ruleId. Never blank.
- `RULE_LABELS` covers common Semgrep Python security rules (pickle, MD5/SHA-1, subprocess, urllib, jinja2, SRI), common gitleaks secret patterns (generic-api-key, aws-access-key-id, github-pat, slack-app-token, generic-private-key), and the Semgrep detected-generic-api-key variant.

```ts
export function securityFindingToExceptionFlag(f: SecurityFinding): ExceptionFlag
```
- Legacy helper; still exported. Converts a single `SecurityFinding` to an `ExceptionFlag`. The project page now uses `groupSecurityFindings` instead.

---

**[`src/lib/work-type-bar.ts`](src/lib/work-type-bar.ts)**

```ts
export function computeWorkTypeBuckets(commits: CommitInput[]): WorkTypeBuckets
// CommitInput = { gitSummary: string | null; filesChanged: string[] }
// WorkTypeBuckets = { bug, docs, build, test, other, total, inferredCount: number }
```
- Heights = `filesChanged.length` (generated/lock files excluded) summed per bucket. CC type → bucket: `fix`→bug, `docs`→docs, `feat`/`refactor`→build, `test`→test, else→other. Un-prefixed commits classified by file-path + subject-keyword heuristic; `inferredCount` increments once per heuristic commit.

---

**[`src/lib/feature-area-track.ts`](src/lib/feature-area-track.ts)**

```ts
export function deriveAreaKey(gitSummary: string | null, filesChanged: string[]): string
// → CC scope if present and not in coarse denylist (p\d+, f\d+, diag, ci, deps?, lint)
// → else mode of pathToArea() from filesChanged; "unknown" if nothing available

export function computeAreaPhase(commits: CommitForArea[], windowStart: Date, now?: Date): AreaPhase
// → "building"    if commits.length < 3 (signal floor) or feat/refactor dominate
// → "stabilising" if fix+test >= 30% of total OR recent half has more fix/test than feat
// → "maturing"    if fix+test >= 50% AND zero feat/refactor commits
// Un-prefixed commits count toward neither featLike nor stabiliseLike

export function computeAreaRows(commits: CommitForArea[], windowStart: Date, now?: Date): AreaRow[]
// Groups by deriveAreaKey → one AreaRow per area
// AreaRow = { area: string; phase: AreaPhase; latestWorker: string | null; commitCount: number }
// latestWorker = authorName of most recent ingestedAt commit in area (null if unknown)
// Sorted by commitCount descending
```

---

**[`src/lib/activity-rows.ts`](src/lib/activity-rows.ts)**

```ts
export function computeActivityRows(events: RawEvent[], limit?: number): ActivityRow[]
// RawEvent = { id, userId, hookSource, feedSummary, manualText, gitCommitSha, ingestedAt: Date, user }
// ActivityRow = { id, userId, userName, text, hookSource, ingestedAt: string }
```
- Excludes events where `gitCommitSha !== null` (git events covered by RecentCommitsAccordion).
- Excludes events with `userId === null` (unattributed).
- Excludes events with no text (`feedSummary == null && manualText == null`).
- `text = feedSummary ?? manualText` — both fields are stored already-redacted at ingest.
- Default limit 20; `ingestedAt` serialised to ISO string.

---

**[`src/lib/pnumber-matcher.ts`](src/lib/pnumber-matcher.ts)**

```ts
export function matchPNumber(inputText: string, candidates: PromptCandidate[]): string | null
// Two-gate matching:
//   Gate 1 (primary): Jaccard similarity ≥ JACCARD_THRESHOLD (0.6) on token sets → immediate match
//   Gate 2 (secondary): Jaccard ∈ [DICE_SECONDARY_GATE (0.4), JACCARD_THRESHOLD) → Dice bigram ≥ DICE_SECONDARY_THRESHOLD (0.7) → match
// Handles character-level drift (typos, British/American spelling differences).
// Returns pNumber string of best match, or null if no candidate passes either gate.

export function buildFingerprint(text: string): string
// First 200 chars of text, lowercased, used as the matching surface.

export function tokenize(text: string): Set<string>
// Splits fingerprint into word tokens; returns a Set for Jaccard computation.

export function diceSimilarity(a: string, b: string): number
// Dice coefficient on character bigrams with multiplicity; symmetric.
// Returns 1 for identical strings, 0 if either string is empty (but 1 if both empty).

export function normalizeForDice(text: string): string
// Lowercase + strip punctuation → space, truncate to 200 chars; operates on raw string (not tokenised).

export const JACCARD_THRESHOLD: number         // 0.6 — primary match threshold
export const DICE_SECONDARY_GATE: number       // 0.4 — minimum Jaccard to attempt secondary Dice check
export const DICE_SECONDARY_THRESHOLD: number  // 0.7 — Dice threshold for secondary match
```

---

**[`src/lib/prompt-adoption.ts`](src/lib/prompt-adoption.ts)**

```ts
export function computePromptAdoptionSignal(events: WindowEventWithPrompt[]): PromptAdoptionSignal
// events: DESC-ordered windowEvents enriched with prompt relation (caller controls window)
// matchCount: count of events where pNumberDetected != null
// mostRecentTitle: prompt.title from the first matched event (most recent); null if prompt deleted
// mostRecentPNumber: pNumberDetected from the first matched event (set even if prompt was deleted)

// WindowEventWithPrompt = ActivityEvent & { prompt: { title: string } | null }
// PromptAdoptionSignal = { matchCount: number; mostRecentTitle: string | null; mostRecentPNumber: string | null }
```
- Pure function — no DB access. Caller is responsible for passing correctly windowed and ordered events.

---

**[`src/lib/readiness.ts`](src/lib/readiness.ts)**

```ts
export const FORECAST_MIN_SNAPSHOTS = 3  // minimum snapshots for a trend forecast

export function countMarkersInContent(content: string): MarkerDetail
// Counts TODO (word boundary, case-sensitive), FIXME (word boundary, case-sensitive),
// skipped tests (.skip(, .todo(, xit(, xdescribe(, xtest(), stubbed functions
// (throw new Error('not implemented') case-insensitive)

export function sumMarkerDetail(detail: MarkerDetail): number
// sum of all four fields

export function computeForecast(
  snapshots: SnapshotForForecast[],
  now?: number  // injectable for testing; defaults to Date.now()
): ForecastResult
// OLS linear regression over (scannedAt, markerCount) pairs.
// Returns "insufficient" when < FORECAST_MIN_SNAPSHOTS.
// Returns "flat" when slope >= 0 or x-variance is 0.
// Returns "trend" only for a genuine downward slope — never shows "clears in N days" otherwise.

export function buildReadinessSignal(
  latest: { markerCount: number; markerDetail: MarkerDetail; coveragePct: number | null; scannedAt: Date } | null,
  snapshots: SnapshotForForecast[],
  now?: number
): ReadinessSignal

export async function scanMarkersInDir(rootDir: string): Promise<MarkerDetail>
// Recursively walks rootDir; skips node_modules, .next, dist, coverage, generated, migrations, .git
// Reads .ts, .tsx, .js, .jsx, .mjs files only

export async function readCoveragePct(rootDir: string): Promise<number | null>
// Reads coverage/coverage-summary.json → total.lines.pct; returns null on any error or absence
```
- `MarkerDetail = { todo, fixme, skippedTests, stubbed, testFileCount }` — `testFileCount` counts `*.{test,spec}.{ts,tsx,js,jsx}` filenames; set by `scanMarkersInDir`, not `countMarkersInContent`; not included in `sumMarkerDetail`
- `ForecastResult = { kind: "trend"; daysToZero; slopePerDay } | { kind: "flat"; message } | { kind: "insufficient"; neededMore }`
- **Critical invariant**: `computeForecast` never returns `{ kind: "trend" }` for a flat or rising marker series.

---

**[`src/lib/sort-project-cards.ts`](src/lib/sort-project-cards.ts)**

```ts
export function sortProjectCards<T extends SortableCard>(cards: T[]): T[]
```
- Projects with `lastActivityAt` sort descending by recency. Null `lastActivityAt` sorts to end, then alphabetically by name.

---

**PM3 Data-Plane Patterns (admin member management)**

All six admin management routes (`promote`, `demote`, `role`, `assign-to-team`, `remove-from-team`, `PATCH [id]`) follow the same Phase 3 pattern:

```ts
// Existence check — always via Membership composite-key, never by User alone
const membership = await db.membership.findUnique({
  where: { userId_organisationId: { userId: params.id, organisationId: ctx.organisationId } },
  select: { userId: true, role: true, teamId: true, isLineManager: true },
})
if (!membership) return NextResponse.json({ reason: "not_found" }, { status: 404 })

// Role / teamId write → Membership, never User
await db.membership.update({
  where: { userId_organisationId: { userId: params.id, organisationId: ctx.organisationId } },
  data: { role: "LINE_MANAGER", isLineManager: true },  // example: promote
})

// sessionVersion bump → User (JWT reads User.sessionVersion; Membership has no sessionVersion)
await db.user.update({ where: { id: params.id }, data: { sessionVersion: { increment: 1 } } })
invalidateSessionVersionCache(params.id)
```

**Q21 last-manager guard** (used in `demote` and `role` routes):

```ts
if (membership.role === "MANAGER") {
  const otherManagerCount = await db.membership.count({
    where: {
      organisationId: ctx.organisationId,
      status: "ACTIVE",
      role: "MANAGER",
      NOT: { userId: params.id },
    },
  })
  if (otherManagerCount < 1) {
    return NextResponse.json({ reason: "last_manager_cannot_demote" }, { status: 409 })
  }
}
```
- Uses `membership.count` with `status: "ACTIVE"` filter — never `user.count`. Intentional: a PENDING or non-member Manager should not count toward the guard.

**PM3 Phase 2 listing pattern** (`GET /api/admin/members`):

```ts
const membershipWhere =
  ctx.role === "MANAGER"
    ? { organisationId: ctx.organisationId, status: "ACTIVE" as const }
    : { organisationId: ctx.organisationId, status: "ACTIVE" as const, teamId: ctx.teamId ?? "__none__" }

const memberships = await db.membership.findMany({
  where: membershipWhere,
  include: { user: { select: { id, email, name, teamId, isActive, ... } } },
})
const users = memberships.map((m) => ({ ...m.user, role: m.role, isLineManager: m.isLineManager }))
```
- `role` and `isLineManager` always come from the Membership row, never from User fields.

---

**[`src/lib/member-card.ts`](src/lib/member-card.ts)**

```ts
// Returns null when target user is not found in the given org.
// canSeeSpend=false omits the spend key entirely from the returned object (not undefined-value, key absent).
// time shape: consentVersion >= 2 → TimeDataV2 with day-row array for the member's local window;
//             consentVersion < 2  → TimeDataNotConsented { consentVersion: 0|1, reason: "not_consented" }
// Tokens = claudeInputTokens + claudeOutputTokens only (cache tokens excluded — ~40× inflation otherwise).
// sessionExcerpt / gitSummary returned as stored (redacted at ingest; no re-processing here).
//
// DUAL TIMEZONE WINDOWING:
//   rawWindow: "today"|"7d"|"30d" (default "7d"). Invalid values silently default to "7d".
//   Time section (MemberDailyTime): windows by the MEMBER'S own IANA timezone, read from their
//     most recent day row. "today" = member's local calendar day as UTC midnight. UTC fallback if no rows.
//   Event sections (spend/sessions/commits/projects): windows by the VIEWER'S timezone via
//     resolveTimeWindow(rawWindow, viewerTodayMs). lastSeenAt is NOT windowed — all-time only.
//   The window param is additive time-narrowing on top of the existing org+user+role gate.
export async function getMemberCard(
  targetId: string,
  organisationId: string,
  canSeeSpend: boolean,
  rawWindow?: string,       // "today"|"7d"|"30d"; undefined → "7d"
  viewerTodayMs?: number,   // viewer's local midnight as epoch ms (for viewer-tz "today" boundary)
): Promise<MemberCardData | null>

export type MemberCardData = {
  identity: MemberIdentity      // id, name, email, role, teamName, isActive, lastSeenAt (all-time), consentVersion
  spend?: MemberSpend           // absent when canSeeSpend=false; windowed by viewer-tz since
  time: MemberTimeData          // TimeDataV2 | TimeDataNotConsented; windowed by member-tz local days
  projects: MemberProject[]     // activity-based groupBy projectId; windowed by viewer-tz since; sorted by lastActiveAt desc
  recentSessions: MemberSession[] // last 15 CLAUDE_HOOK Stop events within viewer-tz window; feedSummary + sessionExcerpt
  recentCommits: MemberCommit[]   // last 15 events with gitCommitSha within viewer-tz window; sha truncated to 7 chars
}

export type MemberSession = {
  id: string
  feedSummary: string | null    // Groq 5-8 word phrase; null for old events or manual entries
  sessionExcerpt: string | null // raw but redacted transcript tail; use as fallback via firstSentence()
  sessionDurationSeconds: number | null
  projectName: string
  date: string
}
```

---

**[`src/app/admin/members/_components/member-card-fetch.ts`](src/app/admin/members/_components/member-card-fetch.ts)**

```ts
// Wraps GET /api/admin/members/:id/card. Returns a discriminated union so callers
// never need to handle raw Response objects. On non-OK responses, status is preserved
// for UI to show 403 (access restricted), 404 (not found), 429 (rate limited), etc.
// opts.window appended as ?window=...; opts.todayCutoff appended as ?todayCutoff=<epochMs>.
export async function fetchMemberCard(
  memberId: string,
  opts?: FetchMemberCardOpts, // { window?: TimeWindow; todayCutoff?: number }
): Promise<MemberCardResult>

export type MemberCardResult =
  | { ok: true; data: MemberCardData }
  | { ok: false; status: number }
```

---

### Password & Security

**[`src/lib/password.ts`](src/lib/password.ts)**

```ts
export function validatePassword(password: string): PasswordValidationResult
// { ok: true } | { ok: false; reason: "password_too_short" | "missing_digit_or_symbol" }
```
- `MIN_LENGTH = 12`.
- Requires at least one letter (`/[a-zA-Z]/`), one digit (`/[0-9]/`), and one symbol (`/[^a-zA-Z0-9]/`).

```ts
export async function hashPassword(plain: string): Promise<string>
// bcrypt.hash(plain, 12)

export async function verifyPassword(plain: string, hash: string): Promise<boolean>
// bcrypt.compare(plain, hash)
```
- `BCRYPT_COST = 12` (same as agent tokens).
- Test confirms hash format `$2b$12$...`.

**Login lockout** (implemented in `/api/auth/login`): `LOCKOUT_THRESHOLD = 5` failed attempts → `lockedUntil = now + 10 minutes`. Lockout state is never revealed in error messages (always returns `"Invalid credentials"`). Audit logged at ≥ 4 failed attempts and on lockout.

---

### Audit Logging

**[`src/lib/audit.ts`](src/lib/audit.ts)**

```ts
export function getIp(request: Request): string | null
// Reads x-forwarded-for (first IP) or x-real-ip

export async function writeAudit(
  userId: string | null,
  action: string,
  subjectId: string | null,
  meta?: Record<string, unknown> | null,
  ipAddress?: string | null,
  organisationId?: string
): Promise<void>
```
- `organisationId` defaults to `"org_system"` when omitted.
- `meta` is stored as Prisma `InputJsonValue`.

**Audit actions found across route handlers** (from `writeAudit` call sites):

| Action string | Triggered by |
|---|---|
| `LOGIN_FAILURE` | `/api/auth/login` on repeated/lockout failure (only at attempt ≥ 4; `reason: "repeated_failure"` at attempt 4, `"account_locked"` at attempt 5) |
| `CREATE_PROJECT` | `POST /api/projects` |
| `EDIT_PROJECT` | `PATCH /api/projects/[id]` |
| `DELETE_PROJECT` | `DELETE /api/projects/[id]` |
| `CREATE_TEAM` | `POST /api/teams` |
| `UPDATE_TEAM` | `PATCH /api/teams/[id]` |
| `DELETE_TEAM` | `DELETE /api/teams/[id]` |
| `ROTATE_TOKEN` | `POST /api/projects/[id]/rotate-token` |
| `VIEW_PROJECT` | `GET /api/projects/[id]/members` (manager reading a project's member list) |
| `ADD_PROJECT_MEMBER` | `POST /api/projects/[id]/members` |
| `SUMMARY_GENERATE` | `POST /api/projects/[id]/summary` |
| `EXPORT_PDF` | `GET /api/projects/[id]/export` |
| `CONTEXT_ASSESS` | `POST /api/projects/[id]/drift` — on-demand drift assessment triggered |
| `CONTEXT_BASELINE_SET` | `POST /api/projects/[id]/drift/baseline` (manual) or `runAssessmentPipeline` (auto — on context_builds push) |
| `EDIT_PRODUCTIVE_RULE` | `POST/PATCH/DELETE /api/productive-rules` (with `action: "create"\|"update"\|"delete"` in meta) |
| `CREATE_PROMPT` | `POST /api/prompts` |
| `UPDATE_PROMPT` | `PATCH /api/prompts/[id]` |
| `DELETE_PROMPT` | `DELETE /api/prompts/[id]` |
| `LINK_PROMPT` | `PATCH /api/events/[id]/p-number` — P-number override on an event |
| `INVITE_MEMBER` | `POST /api/admin/members` |
| `ACTIVATE_MEMBER` | `POST /api/admin/members/[id]/activate` |
| `REMOVE_MEMBER` | `POST /api/admin/members/[id]/deactivate` — account deactivated (not team removal) |
| `ASSIGN_TO_TEAM` | `POST /api/admin/members/[id]/assign-to-team` and `PATCH /api/admin/members/[id]` when teamId is non-empty |
| `REMOVE_FROM_TEAM` | `POST /api/admin/members/[id]/remove-from-team` and `PATCH /api/admin/members/[id]` when teamId is empty |
| `ASSIGN_ROLE` | `POST /api/admin/members/[id]/role` — role change with `{ from, to }` in meta |
| `PROMOTE_LINE_MANAGER` | `POST /api/admin/members/[id]/promote` |
| `DEMOTE_LINE_MANAGER` | `POST /api/admin/members/[id]/demote` |
| `INVITE_ACCEPTED` | `POST /api/invite/accept` (both new-user and existing-user paths) |
| `INVITE_DECLINED` | `POST /api/invite/decline` (only written when invitee is an existing user) |
| `CREATE_AGENT_TOKEN` | `POST /api/projects/[id]/agent-tokens` |
| `REVOKE_AGENT_TOKEN` | `POST /api/agent-tokens/[tokenId]/revoke` |
| `DELETE_AGENT_TOKEN` | `DELETE /api/agent-tokens/[tokenId]` (hard-delete of already-revoked token) |
| `RESTORE_AGENT_TOKEN` | `POST /api/agent-tokens/[tokenId]/restore` |
| `CHANGE_PASSWORD` | `POST /api/profile/change-password` |
| `RUN_CLEANUP` | `POST /api/admin/cleanup` |
| `REPO_LINK` | `linkRepoAndRefresh` in `src/lib/repo-context/index.ts` |
| `REPO_REFRESH` | Snapshot refresh completed; from `src/lib/repo-context/index.ts` |

Audit reads are paginated (`PAGE_SIZE = 50`) at `GET /api/audit`, scoped to `organisationId`, MANAGER-only.

---

### Metrics & Observability

**[`src/lib/metrics.ts`](src/lib/metrics.ts)**

```ts
export function recordRequest(route: string, method: string, statusCode: number, durationMs: number): void
export function recordClaudeTokens(projectId: string, inputTokens: number, outputTokens: number): void
export function generatePrometheusText(): string
export function getRouteP95s(windowMs?: number): RouteP95[]
export function _resetMetricsStore(): void  // test only
```

- In-memory module-level singleton. Not Redis-backed.
- Histogram buckets: `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]` seconds.
- `MAX_LATENCY_SAMPLES = 5_000`; rolling 24h window.
- Prometheus metric names emitted:
  - `pulse_request_latency_seconds` (histogram) — labels: `route`, `method`, `le`
  - `pulse_request_total` (counter) — labels: `route`, `method`, `status_class` (`2xx`/`4xx`/`5xx`)
  - `pulse_claude_input_tokens_total` (counter) — label: `project_id`
  - `pulse_claude_output_tokens_total` (counter) — label: `project_id`
- Pre-registers 14 known routes so they appear at zero even with no traffic.

---

**[`src/lib/otel.ts`](src/lib/otel.ts)**

```ts
export function startTrace(): TraceContext
export function startSpan(ctx: TraceContext, name: string, attributes?: Record<string, string|number|boolean>): Span
export function endSpan(span: Span): void
export function commitTrace(ctx: TraceContext): void
export function getLastTrace(): Trace | null
```
- Minimal in-memory OTel-compatible span store. Stores the last completed trace for `/build-evidence` capture.
- 5 spans per ingest call: `ingest`, `redact`, `gate`, `ai`, `store`.
- `startTime` uses `performance.now()`.

---

**[`src/lib/logger.ts`](src/lib/logger.ts)**

```ts
export const logger: pino.Logger
```
- Level: `process.env.LOG_LEVEL ?? "info"`.
- Base field: `env: process.env.NODE_ENV`.
- Redacted paths (replaced with `"[Redacted]"`):
  `password`, `passwordHash`, `agentToken`, `agentTokenHash`, `sessionExcerpt`, `manualText`, `tenantKey`, `secret`, `apiKey`, `jwt`, `bearerToken`, `req.headers.authorization`, `req.headers['x-pulse-signature']`, `req.headers['x-internal-token']`, `headers.authorization`, `headers['x-pulse-signature']`, `headers['x-internal-token']`, `Authorization`, `authorization`.

---

### PDF Generation

**[`src/lib/pdf-utils.ts`](src/lib/pdf-utils.ts)**

```ts
export function extractSubjectLine(gitSummary: string): string
```
- Iterates lines of `gitSummary`; skips: bare SHAs (7–40 hex chars), `commit <sha>` headers, `Author:`/`Date:`/`Merge:` metadata, diffstat columns (`| N`), `N files changed` summary lines, diff `+++`/`---` headers. Strips a leading short-SHA prefix from the returned line. Returns `""` if no subject found.

```ts
export function shortPhrase(s: string, maxWords = 8): string
// Truncates to maxWords words, appending "…" if truncated.

export function cleanBodyForPDF(body: string): string
// Removes backtick code spans: `GET /api/foo` → GET /api/foo
```

**PDF export structure** (from `GET /api/projects/[id]/export/route.ts`): rendered via `@react-pdf/renderer` using `SummaryPDF` component. All roles can request a PDF — MEMBER role receives a spend-free variant (`spendUSD: null`). The route runs an 11-element `Promise.all` fetching: project + team, executive summary, member daily time (gated by `canSeeSpend`), recent events, member list, security scan findings, prompt context, 3-day activity count, readiness snapshots, code health snapshot, and the project's own fields. Computes `findingsForVerdict` (from security findings), `readinessSignal` (via `buildReadinessSignal`), `readinessForVerdict` (latest snapshot), `computeVerdict` result, and `workTypeBuckets` (via `computeWorkTypeBuckets`). Passes 15 props to `SummaryPDF`.

`SummaryPDFProps` includes: `spendUSD` (null when MEMBER or no data), `devTokenBudget`, `verdict`, `securityFindings`, `promptContext`, `readiness`, `codeHealth`, `workType` — in addition to the original fields (project name, team name, client name, description, GitHub repo, detected frameworks, executive summary body, confidence score, generated date, stage, risk level, risk focus, 24h commit count, up to 6 deduplicated recent work items, per-member table). New PDF sections: Project Verdict (§1.5), Readiness Markers (§1.8), Code Health SonarQube (§1.9), Work-Type Breakdown (§4.5), Security Findings (§5.5), Active Prompt Context (§7.2), Developer AI Spend (§7.5, role-gated — absent when `spendUSD` is null). Requires a prior `ExecutiveSummary` row; returns 404 otherwise.

---

### Productive Rules Engine

**[`src/lib/productive-rules.ts`](src/lib/productive-rules.ts)**

```ts
export function matchRule(appName: string, rule: RulePattern): boolean
```
- `EXACT`: case-insensitive `===`.
- `GLOB`: `*` → `.*` regex (anchored `^…$`, case-insensitive). `**` not required.
- `REGEX`: uses `new RegExp(pattern, "i")`; malformed regex returns `false` without throwing.
- Unknown `matchType` returns `false`.

```ts
export function mergeRules(globalRules: RuleRecord[], teamRules: RuleRecord[]): RuleRecord[]
```
- TEAM rules override GLOBAL rules with the same pattern (case-insensitive pattern equality).
- Returns filtered globals + all team rules; order preserved.

```ts
export function isAppProductive(appName: string, mergedRules: Array<{...}>): boolean
```
- Iterates merged rules in order; returns `isProductive` of the first match.
- Default (no match): `false` (not productive).

**Isolation contract**: callers must filter team rules to the requesting user's `teamId` before calling `mergeRules`. The pure function has no DB access and cannot enforce cross-team isolation itself.

---

### Presence & Real-time

**[`src/lib/presence.ts`](src/lib/presence.ts)**

```ts
export const ACTIVE_THRESHOLD_MS = 30 * 60 * 1000   // 30 minutes
export const IDLE_THRESHOLD_MS = 2 * 60 * 60 * 1000  // 2 hours

export function derivePresence(lastActivityAt: Date | string | null | undefined): PresenceState
// PresenceState = "active" | "idle" | "offline"
```
- `null`/`undefined`/invalid date → `"offline"`.
- Age ≤ 30 min → `"active"`.
- Age ≤ 2 hr → `"idle"`.
- Otherwise → `"offline"`.

---

### Repo Context

**[`src/lib/repo-context/index.ts`](src/lib/repo-context/index.ts)**

```ts
export async function refreshRepoContext(projectId: string): Promise<RefreshResult>
// RefreshResult = { success: boolean; error?: string; durationMs?: number; redactionCount?: number }
```
- Transitions project to `repoContextStatus = "REFRESHING"` immediately.
- Fetches `RepoMetadata` (repo info + languages) and `RepoSnapshot` in parallel.
- Counts `[REDACTED]` placeholders in key config excerpts for the `redactionCount` field.
- On success: stores `repoMetadata`, `repoSnapshot`, `repoContextRefreshedAt`, sets status to `"LINKED"`.
- On error: sets `repoContextStatus = "ERROR"`, stores error message (truncated to 500 chars).

```ts
export async function linkRepoAndRefresh(
  projectId: string,
  githubRepoFullName: string,
  githubInstallationId: string,
  triggeredBy: string
): Promise<RefreshResult>
```
- Updates `project.githubRepoFullName` and `githubInstallationId`, then calls `refreshRepoContext`. Writes `REPO_LINK` audit entry.

---

**[`src/lib/repo-context/client.ts`](src/lib/repo-context/client.ts)**

```ts
export function createAppJWT(): string
// RS256 JWT for GitHub App authentication. iat-60s, exp+600s, iss=GITHUB_APP_ID.
// Private key read from GITHUB_APP_PRIVATE_KEY (base64 or PEM).

export async function getInstallationToken(installationId: string): Promise<string>
// Cached for 50 minutes (tokens expire in 60 min). Cache key = installationId.

export async function githubFetch(url: string, init?: RequestInit): Promise<Response>
// Enforces host allowlist: only api.github.com is permitted.
// Adds Accept: application/vnd.github+json and X-GitHub-Api-Version: 2022-11-28.

export async function authedGithubFetch(url: string, installationId: string, init?: RequestInit): Promise<Response>
// Gets installation token then calls githubFetch with Authorization: Bearer <token>.

export async function getInstallationAccount(installationId: string): Promise<string>
// Returns account.login from GET /app/installations/:id.
```

---

**[`src/lib/repo-context/snapshot.ts`](src/lib/repo-context/snapshot.ts)**

```ts
export async function fetchMetadata(installationId: string, fullName: string): Promise<RepoMetadata>
export async function generateSnapshot(installationId: string, fullName: string, defaultBranch: string): Promise<RepoSnapshot>
export function detectFrameworks(keyConfigs: KeyConfig[]): string[]
```
- `MAX_TREE_ENTRIES = 20` top-level items. `MAX_KEY_CONFIGS = 8`. `MAX_EXCERPT_BYTES = 4096` per config. Total snapshot capped at 8 KB.
- `KEY_CONFIG_ALLOWLIST` (21 files): `package.json`, `tsconfig.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Dockerfile`, `docker-compose.yml`, `next.config.{js,mjs,ts}`, `vite.config.{js,ts}`, `nest-cli.json`, `nuxt.config.{js,ts}`, `astro.config.{mjs,ts}`, `svelte.config.js`, `README.md`.
- Key config excerpts are passed through `redact()` before storage.
- Framework detection from `package.json` dependencies: Next.js (with major version), NestJS, Nuxt.js, SvelteKit, Astro, Vite, Express, Fastify, React. From `requirements.txt`/`pyproject.toml`: FastAPI, Django, Flask, Poetry. From `go.mod`: Gin, Fiber, Go module. From `Cargo.toml`: Actix Web, Axum, Rust crate. From `Dockerfile`: Python/Node/Go container.

---

### Code Health — `src/lib/code-health.ts`

Pure:
- `numericRatingToLetter(value: string|null|undefined): RatingLetter` — converts SonarQube numeric rating (1.0–5.0) to letter; bands A=[1,2), B=[2,3), C=[3,4), D=[4,5), E=[5,5]; null/invalid → "N/A"
- `parseQualityGate(value: string|null|undefined): QualityGate` — "OK"→"PASS", "ERROR"→"FAIL", else "N/A"
- `worstRating(...ratings: RatingLetter[]): RatingLetter` — returns the worst (highest-index) known rating; ignores N/A; all-N/A → "N/A"

I/O:
- `fetchSonarMetrics(projectKey, hostUrl, token): Promise<SonarMetrics>` — calls SonarQube REST API (`/api/measures/component`); fetches `reliability_rating`, `security_rating`, `sqale_rating`, `alert_status`, `coverage`, `duplicated_lines_density`, `sqale_index`; `SonarMetrics` includes `sqaleIndexMinutes: number | null` (tech-debt minutes); throws on non-OK HTTP
- `fetchSonarIssues(projectKey, hostUrl, token): Promise<SonarIssue[]>` — calls `/api/issues/search?componentKeys=...&types=CODE_SMELL,BUG,VULNERABILITY&severities=BLOCKER,CRITICAL,MAJOR&ps=500`; strips `{projectKey}:` prefix from `component` to yield relative file path; `SonarIssue = { file, line: number|null, message, severity, ruleId }`; throws on non-OK HTTP
- `runSonarScanner(opts: { projectKey, scannerHostUrl, token, sourcesPath, sources?, timeoutMs? }): void` — runs `sonarsource/sonar-scanner-cli:latest` Docker container via `execSync`; mounts `sourcesPath` as `/usr/src`; stdio piped; default timeout 5 minutes; throws on non-zero exit
- `downloadRepoTarball(opts: { repoFullName, ref, installationId, tarballPath }): Promise<void>` — fetches GitHub tarball via `authedGithubFetch`, streams to `tarballPath` using `pipeline(Readable.fromWeb(body), writeStream)`
- `extractTarball(tarballPath, srcDir): void` — runs `tar xf ... --strip-components=1` via `execSync` to strip GitHub's top-level directory prefix
- `ensureSonarProject(opts: { projectKey, projectName, hostUrl, adminToken }): Promise<void>` — calls `POST /api/projects/create` with `SONAR_ADMIN_TOKEN`; treats "already exist" response as success

Semaphore:
- `tryAcquireScanSlot(): boolean` — returns `true` and increments counter if `_activeScanCount < MAX_CONCURRENT_SCANS (2)`; otherwise returns `false`
- `releaseScanSlot(): void` — decrements `_activeScanCount` (floor 0); always called in `finally` blocks

Module init:
- Boot-time IIFE removes `/tmp/pulse-scan-*` dirs older than 30 minutes (crash cleanup from previous process)

Types: `RatingLetter` ("A"|"B"|"C"|"D"|"E"|"N/A"), `QualityGate` ("PASS"|"FAIL"|"N/A"), `SonarMetrics`

**[`src/lib/ratelimit-code-health.ts`](src/lib/ratelimit-code-health.ts)**

```ts
export async function checkCodeHealthScanRateLimit(projectId: string): Promise<{ allowed: boolean }>
```
- Upstash sliding-window 1 request per 120 seconds per projectId.
- Upstash prefix: `pulse:code-health:scan`.
- Fail-open on Upstash errors (standard convention).

---

### Security Scanning

**[`src/lib/security-scan.ts`](src/lib/security-scan.ts)**

```ts
export type SecuritySeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO"

export interface SecurityFindingData {
  tool: string
  ruleId?: string
  severity: SecuritySeverity
  message: string
  file?: string
  line?: number
}

export const SEVERITY_WEIGHT: Record<SecuritySeverity, number>
// { CRITICAL: 5, HIGH: 4, MEDIUM: 3, LOW: 2, INFO: 1 }
// Used to sort merged exception flags worst-first in the project page.
```

Parsers (pure, no I/O):
```ts
export function parseSemgrepOutput(rawJson: string): SecurityFindingData[]
// Parses Semgrep JSON output. Severity mapping: ERROR→HIGH, WARNING→MEDIUM, INFO→INFO, else→INFO.

export function parseGitleaksOutput(rawJson: string): SecurityFindingData[]
// Parses gitleaks JSON output. All findings are mapped to CRITICAL severity.

export function parseOsvScannerOutput(rawJson: string): SecurityFindingData[]
// Parses osv-scanner JSON output. Uses database_specific.severity (MODERATE→MEDIUM) if present;
// falls back to CVSS vector heuristic (score>=9→CRITICAL, >=7→HIGH, >=4→MEDIUM, else LOW).
```

CLI runners:
```ts
export async function runSemgrep(srcDir: string): Promise<SecurityFindingData[]>
// Invokes: semgrep scan --config=auto --json <srcDir>
// Returns [] if semgrep is not installed or returns a non-JSON error (catch-and-continue).

export async function runGitleaks(srcDir: string): Promise<SecurityFindingData[]>
// Invokes: gitleaks detect --source=<srcDir> --report-format=json --report-path=<tmpFile>
// Returns [] if gitleaks is not installed. Exit code 1 (findings found) is treated as success.

export async function runOsvScanner(srcDir: string): Promise<SecurityFindingData[]>
// Invokes: osv-scanner --format json <srcDir>
// Returns [] if osv-scanner is not installed or no manifest files found.
```

Orchestrator:
```ts
export async function runAllSecurityTools(
  srcDir: string,
  tempDir: string
): Promise<SecurityFindingData[]>
// Runs all three tools in sequence. Each tool failure is caught independently — a missing CLI
// produces 0 findings and does not abort the others. Returns deduplicated combined findings.
```

**[`src/lib/ratelimit-security-scan.ts`](src/lib/ratelimit-security-scan.ts)**

```ts
export async function checkSecurityScanRateLimit(projectId: string): Promise<{ allowed: boolean }>
```
- Upstash sliding-window 1 request per 120 seconds per projectId.
- Upstash prefix: `pulse:security:scan`.
- Fail-open on Upstash errors (standard convention).

---

**[`src/lib/ratelimit-member-card.ts`](src/lib/ratelimit-member-card.ts)**

```ts
export async function checkMemberCardRateLimit(userId: string): Promise<{ allowed: boolean }>
```
- Upstash sliding-window 30 requests per 60 seconds per caller userId.
- Upstash prefix: `pulse:admin:member-card`.
- Fail-open on Upstash errors (standard convention).

---

**[`src/lib/ratelimit-debt-scan.ts`](src/lib/ratelimit-debt-scan.ts)**

```ts
export async function checkDebtScanRateLimit(projectId: string): Promise<{ allowed: boolean }>
```
- Upstash sliding-window 1 request per 30 minutes per projectId.
- Upstash prefix: `pulse:debt-scan`.
- Fail-open on Upstash errors (standard convention).

---

**[`src/lib/debt/orchestrate.ts`](src/lib/debt/orchestrate.ts)**

```ts
// TriggerResult = { ok: true; scanId: string } | { ok: false; reason: "project_not_found" | "already_running" }

export async function triggerDebtScan(projectId: string, organisationId: string): Promise<TriggerResult>
// Creates PENDING TechnicalDebtScan record + fires runDebtScanPipeline async (fire-and-forget).
// Duplicate guard: returns { ok: false, reason: "already_running" } if a PENDING or RUNNING scan exists.

export async function runDebtScanPipeline(scanId: string): Promise<void>
// Phase B real-engine pipeline: load scan → project lookup → GitHub guard (github_not_configured) →
// cross-tenant installation guard (github_installation_not_found, queries by scan.organisationId) →
// concurrency slot (scan_capacity_exceeded, no releaseScanSlot if slot not acquired) →
// RUNNING+DOWNLOADING → downloadAndExtract → SONAR → runSonarEngine →
// SYNTHESISING (stores sonarProjectKey, ratings, techDebtMinutes, issue/critical/highCount;
//   findings/debtScore stay null — Phase D) → COMPLETE+DONE+scannedAt.
// catch: marks ERROR with err.message. finally: releaseScanSlot + deleteTmpdir (cleanup swallowed).

export async function resetStaleRunningDebtScans(): Promise<number>
// Sets RUNNING → ERROR for TechnicalDebtScan rows stuck for > STALE_RUNNING_MS (15 min).
// Returns the count of rows updated.
```

---

**[`src/lib/debt/engines.ts`](src/lib/debt/engines.ts)**

```ts
export type ProjectForScan = {
  id: string; name: string; githubRepoFullName: string;
  githubInstallationId: string; repoMetadata: unknown; organisationId: string
}

export type SonarEngineResult = {
  sonarProjectKey: string; qualityGate: string;
  reliabilityRating: string; securityRating: string; maintainabilityRating: string;
  techDebtMinutes: number | null; issueCount: number;
  criticalCount: number   // BLOCKER severity issues
  highCount: number       // CRITICAL severity issues
}

export async function downloadAndExtract(project: ProjectForScan): Promise<{ tmpDir: string; srcDir: string }>
// Creates pulse-debt-scan-{id}-{ts} tmpDir; downloads GitHub tarball; extracts to srcDir.
// repoMetadata.defaultBranch → ref; falls back to "HEAD" if absent.

export async function runSonarEngine(srcDir: string, project: ProjectForScan): Promise<SonarEngineResult>
// Reads SONAR_HOST_URL (REST), SONAR_SCANNER_HOST_URL (scanner), SONAR_ADMIN_TOKEN.
// Per-project key: "debt-{orgId}-proj-{projId}" — distinct from code-health and axis-pulse self-scan keys.
// ensureSonarProject → runSonarScannerAsync → waitForSonarCe → fetchSonarMetrics → fetchSonarIssues.
// criticalCount = BLOCKER issues; highCount = CRITICAL issues (SonarQube severity naming).

export function deleteTmpdir(tmpDir: string): void
// rmSync(tmpDir, { recursive: true, force: true })
```

---

### Budget & Cost

**[`src/lib/budget-utils.ts`](src/lib/budget-utils.ts)** — pure, no server imports

```ts
export type BudgetStatus = "ok" | "near-limit" | "over-budget" | "no-budget"
export const BUDGET_NOTIONAL_USD_PER_M = 3.00  // Sonnet 4.6 input rate $3/M

export function computeBudgetStatus(usedTokens: number, budgetTokens: number | null): BudgetStatus
// null budget → "no-budget"; ≥100% → "over-budget"; ≥80% → "near-limit"; else "ok"

export function computeUsagePct(usedTokens: number, budgetTokens: number | null): number | null
// null budget → null; budgetTokens=0 and usedTokens>0 → Infinity; else Math.round(pct)

export function computeNotionalBudgetUSD(budgetTokens: number | null): number | null
// budgetTokens / 1_000_000 * 3.00
```

---

**[`src/lib/cost-ceiling.ts`](src/lib/cost-ceiling.ts)**

```ts
export const INPUT_COST_PER_TOKEN = 3e-6    // $3/M
export const OUTPUT_COST_PER_TOKEN = 15e-6  // $15/M

export function getMonthlyCeilingUSD(): number | null
// Reads CLAUDE_MONTHLY_CEILING_USD env var. Returns null if unset.

export async function getMonthlySpendUSD(organisationId: string): Promise<number>
// Aggregates Intelligence.inputTokens + outputTokens for current UTC calendar month.

export async function isCeilingExceeded(organisationId: string): Promise<boolean>
// Returns true if monthly spend >= ceiling.

export async function getProjectSpendByMonth(organisationId: string): Promise<Array<{...}>>
// Groups Intelligence rows by projectId for current month; sorted by spendUSD descending.
```

---

**[`src/lib/dev-cost.ts`](src/lib/dev-cost.ts)** — developer Claude Code token cost tracking

```ts
export type ModelPricing = { input: number; output: number; cacheCreate: number; cacheRead: number }
export const SONNET_PRICING: ModelPricing  // $3/$15/M input/output; cache-write $3.75/M; cache-read $0.30/M
export const OPUS_PRICING: ModelPricing    // $5/$25/M; cache-write $6.25/M; cache-read $0.50/M
export const HAIKU_PRICING: ModelPricing   // $1/$5/M; cache-write $1.25/M; cache-read $0.10/M

export function pricingForModel(model: string | null | undefined): ModelPricing
// Resolves model string → pricing table. Falls back to SONNET_PRICING for unknown/null.

export type DevTokens = { input: number; output: number; cacheCreate: number; cacheRead: number }
export function computeDevCostUSD(tokens: DevTokens, model: string | null | undefined): number
// Pure cost computation: sum of (token count × per-token rate) across all four token types.

export async function getDevDailySpendUSD(organisationId: string, since?: Date): Promise<number>
// Today's total dev Claude Code spend for the org. Pass `since` (local midnight as UTC Date).

export async function getDevSpendByUser(organisationId: string, since?: Date): Promise<UserSpendRow[]>
// Today's spend grouped by developer, sorted descending. Resolves user names in one query.

export async function getDevSpendByDay(organisationId: string, days: number): Promise<DaySpendRow[]>
// Daily team spend totals for the last N days, sorted ascending by date.

export async function getDevTokensByProject(organisationId: string, since: Date): Promise<ProjectTokenRow[]>
// Today's cumulative Claude Code token usage (input + output only) per project.
// Cache-read tokens excluded: they are $0.30/M (10× cheaper than input) and would inflate raw counts.

export async function getProjectDailySpendUSD(projectId: string, organisationId: string, since?: Date): Promise<number>
// Today's total dev Claude Code spend for a single project.

export async function getProject7DayDailySpends(projectId: string, organisationId: string): Promise<DaySpendRow[]>
// Per-day spend for the 7 days before today (UTC). Used for cost-spike detection.

export async function getProjectMonthlyTokens(projectId: string, organisationId: string): Promise<number>
// Month-to-date total token usage (input + output only) for a single project (UTC calendar month).

export async function getProjectMonthlyDevSpendUSD(projectId: string, organisationId: string): Promise<number>
// Month-to-date Claude Code spend for a single project. Always from 1st of current UTC month.

export async function getProjectWindowedDevSpendUSD(projectId: string, organisationId: string, since: Date): Promise<number>
// Windowed spend (Today / 7d / 30d) for a single project via caller-supplied `since` date.

export async function getProjectWindowedSpendAndTokens(projectId: string, organisationId: string, since: Date): Promise<WindowedSpendAndTokens>
// Single aggregate: windowed spend + input/output token totals. Role-gated at call site.
```
Re-exports `BudgetStatus`, `computeBudgetStatus`, `computeUsagePct`, `computeNotionalBudgetUSD` from `budget-utils.ts`.

---

### Consent Check

**[`src/lib/consentCheck.ts`](src/lib/consentCheck.ts)**

```ts
export async function needsConsentModal(userId: string, teamId: string | null): Promise<boolean>
```
- Returns `false` immediately if `teamId` is null (MANAGER has no team, no consent needed).
- Checks `team.timeTrackingEnabled`; returns `false` if disabled.
- Checks `TimeTrackingConsent` row: returns `true` if `acknowledgedAt` is null OR `consentVersion < 2`.
- Implements the v2 re-consent requirement: users who consented at v1 (aggregate-only) must re-consent when app-name collection is added.

---

### Body Shape Validation

**[`src/lib/pulse-body-shape.ts`](src/lib/pulse-body-shape.ts)**

```ts
export const ALLOWED_TIME_BODY_KEYS = new Set([
  'projectId', 'userIdHint', 'day', 'timezone',
  'workedSeconds', 'productiveSeconds', 'unproductiveSeconds', 'topApps'
])

export function assertBodyShape(body: Record<string, unknown>): void
// Throws if any key outside ALLOWED_TIME_BODY_KEYS is present.
// Blocked: windowTitle, appName, url, full app lists.
// Allowed: topApps (top 2 productive + top 2 unproductive app names + seconds, requires v2 consent).
```

**Ingest event Zod schema** (from `/api/ingest/event/route.ts`):
```ts
z.object({
  projectId: z.string().min(1),
  userIdHint: z.string().email().optional(),
  kind: z.enum(["CLAUDE_HOOK", "MANUAL_STATUS"]),
  hookSource: z.string().optional(),
  sessionExcerpt: z.string().optional(),
  filesChanged: z.array(z.string()).optional(),
  gitSummary: z.string().optional(),
  gitCommitSha: z.string().optional(),
  manualText: z.string().optional(),
  claudeUsage: z.object({
    input: z.number().int().min(0),
    output: z.number().int().min(0),
    cacheCreate: z.number().int().min(0),
    cacheRead: z.number().int().min(0),
    model: z.string().optional(),
    cost: z.number().min(0),
  }).optional(),
  sourceMessageUuid: z.string().optional(),
})
```
`MAX_BODY_BYTES = 256 * 1024` (ingest event), `64 * 1024` (ingest time).

**Ingest time Zod schema** (from `/api/ingest/time/route.ts`):
```ts
z.object({
  projectId: z.string().min(1).optional(),
  userIdHint: z.string().email().optional(),
  day: z.string().min(1),  // must match /T00:00:00(\.000)?Z$/
  timezone: z.string().min(1),
  workedSeconds: z.number().int().nonnegative().max(86400),
  productiveSeconds: z.number().int().nonnegative().max(86400),
  unproductiveSeconds: z.number().int().nonnegative().max(86400),
  topApps: z.object({
    productive: z.array(z.object({ app: z.string(), seconds: z.number().int().nonnegative() })).max(2),
    unproductive: z.array(z.object({ app: z.string(), seconds: z.number().int().nonnegative() })).max(2),
  }).optional(),
})
```
Additional invariant enforced in code: `|productiveSeconds + unproductiveSeconds - workedSeconds| <= 2`.

---

### Time Window Utilities

**[`src/lib/project-time-window.ts`](src/lib/project-time-window.ts)**

```ts
export type TimeWindow = "today" | "7d" | "30d"

export type ResolvedTimeWindow = {
  window: TimeWindow
  label: string
  start: Date
  prevStart: Date
  prevEnd: Date
}

export function resolveTimeWindow(raw: string | undefined, todayCutoffMs?: number): ResolvedTimeWindow
// Resolves a window string into concrete Date boundaries.
// "today" — viewer's LOCAL calendar day. Pass `todayCutoffMs` (epoch ms of local midnight,
//   computed browser-side as `new Date().setHours(0,0,0,0)`) for tz-correct boundary.
//   Fallback when absent/invalid: UTC calendar midnight (never rolling 24h).
// "7d" / "30d" — rolling from now (todayCutoffMs ignored).
// prevStart / prevEnd = the equivalent prior period for delta comparisons.

export function parseTodayCutoff(raw: string | undefined): Date
// Parses a raw `todayCutoff` search-param string (epoch ms as string, injected browser-side)
// into a Date representing the viewer's local calendar midnight.
// Falls back to UTC midnight when absent, empty, non-numeric, zero, or negative.
```
Used by project pages, member card, and budget page to ensure "today" is always the viewer's local calendar day, not UTC midnight.

---

### Display & Completion Utilities

**[`src/lib/completion-cells.ts`](src/lib/completion-cells.ts)**

```ts
export type CompletionCellId = "test_files" | "session_time"

export function getCompletionCells(canSeeSession: boolean): CompletionCellId[]
// Returns the ordered list of cell IDs to render in CompletionStatusWidget.
// canSeeSession = role !== "MEMBER". When false, only ["test_files"]. When true, both cells.
```

---

**[`src/lib/code-health-poller.ts`](src/lib/code-health-poller.ts)** — client-side polling only (no server imports)

```ts
export type CodeHealthSnapshot = {
  reliabilityRating: string; securityRating: string; maintainabilityRating: string
  qualityGate: string; coveragePct: number | null; duplicationPct: number | null
  sonarProjectKey: string; scannedAt: string
}

export type PollOptions = {
  projectId: string
  triggerTime: string        // ISO string captured at click time; resolves only when snapshot.scannedAt > this
  onSnapshot: (s: CodeHealthSnapshot) => void
  onError: (msg: string) => void
  shouldAbort: () => boolean // called before each sleep; return true to stop without error
  pollIntervalMs?: number    // default 5000
  timeoutMs?: number         // default 10 * 60 * 1000
}

export async function pollForNewerSnapshot(opts: PollOptions): Promise<void>
// Polls GET /api/projects/[id]/code-health every `pollIntervalMs` until a snapshot with
// scannedAt > triggerTime arrives, `onError` fires (scan failed), or `timeoutMs` is reached.
// Never terminates on scanInProgress — only on newer snapshot, error, or timeout.
```
Used by `CodeHealthRing` to drive the post-scan polling loop without blocking the server.

---

### Onboarding Tour Engine

**[`src/lib/tour/cookie.ts`](src/lib/tour/cookie.ts)**

```ts
// Step persistence — pulse-tour-step cookie
export function readTourCookie(): string | null
// Reads document.cookie for 'pulse-tour-step'; returns the step ID string or null.

export function writeTourCookie(stepId: string): void
// Sets document.cookie 'pulse-tour-step=<stepId>; max-age=86400; SameSite=Lax; path=/'

export function clearTourCookie(): void
// Removes the 'pulse-tour-step' cookie by setting max-age=0.

// Tour-mode persistence — pulse-tour-kind cookie (Phase 5)
export function readTourKindCookie(): "first-run" | "feature" | null
// Reads document.cookie for 'pulse-tour-kind'; returns the tour mode or null (= default first-run).

export function writeTourKindCookie(kind: "first-run" | "feature"): void
// Sets document.cookie 'pulse-tour-kind=<kind>; max-age=86400; SameSite=Lax; path=/'

export function clearTourKindCookie(): void
// Removes the 'pulse-tour-kind' cookie by setting max-age=0.
```

**[`src/lib/tour/filter.ts`](src/lib/tour/filter.ts)**

```ts
export function filterSteps(
  steps: TourStep[],
  role: TourRole,
  tourMode: "first-run" | "feature",
  ctx: TourFilterCtx
): TourStep[]
// Returns steps that pass all three gates:
//   1. roles gate: step.roles includes role (or roles is absent)
//   2. availableIn gate: step.availableIn === tourMode (or availableIn is absent = both modes)
//   3. skipIf gate: step.skipIf?.(ctx) is falsy (or skipIf is absent)
```

**[`src/lib/tour/reducer.ts`](src/lib/tour/reducer.ts)**

```ts
export function tourReducer(state: EngineState, action: EngineAction): EngineState
// Pure state machine. Transitions:
//   inactive + INIT(on route)     → polling
//   inactive + INIT(off route)    → waiting
//   polling  + TARGET_FOUND       → active
//   polling  + TARGET_MISSING     → missing
//   waiting  + ARRIVED_ON_ROUTE   → polling
//   active   + ADVANCE(on route)  → polling
//   active   + ADVANCE(off route) → waiting
//   active/missing + EXIT         → inactive
```

**[`src/lib/tour/steps.ts`](src/lib/tour/steps.ts)**

```ts
export const TOUR_STEPS: TourStep[]
// 21-step dual-tour inventory (Phase 5).
// Structured as three groups:
//   first-run only (9): welcome, dashboard-cta, teams-new-team, teams-modal,
//     project-new-project, project-create-modal, project-token-copy,
//     project-token-saved, project-open
//   feature only (2): feature-welcome, feature-nav-project
//   shared / both (10): nav-prompts, project-verdict, project-exceptions,
//     project-spend-ring, project-code-health, project-feature-progress,
//     project-repo-context, nav-cost-dashboard, nav-install, done
// Step counts after filterSteps:
//   first-run MANAGER 19, first-run LINE_MANAGER 16
//   feature MANAGER 12, feature LINE_MANAGER 12
//   MEMBER 0 (all steps require MANAGER or LINE_MANAGER)
// TourStep fields:
//   id, route, routePrefix?, selector, instruction, buttonText?,
//   pollTimeout?, advance, roles?, availableIn?, stub?, skipIf?
// Notable steps:
//   project-token-copy   — pollTimeout: 120_000; advance.on = "element-appears"
//                          (polls until [data-tour='project-token-copy'] appears in DOM)
//   project-open         — advance { on: "navigate", to: "/projects/" } (prefix match)
//   teams-modal          — advance { on: "navigate", to: "/teams/" }; spotlights dialog card
//   project-create-modal — advance.on = "element-appears"; spotlights form card
//   welcome / done       — sentinel selectors; tooltip centers (no spotlight)
```

**[`src/app/profile/_components/RetakeTourButton.tsx`](src/app/profile/_components/RetakeTourButton.tsx)**

```ts
// Client component. Calls PATCH /api/me/onboarding { hasOnboarded: false },
// writes pulse-tour-kind=feature via writeTourKindCookie("feature"),
// clears the pulse-tour-step cookie via clearTourCookie(), then
// router.push("/dashboard") to launch the feature tour.
export function RetakeTourButton(): JSX.Element
```

---

## API Route Patterns

### Auth Guard Pattern
Every session-authenticated route calls `withAuthScoped()` as the first operation:
```ts
const ctx = await withAuthScoped()
if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
```

Agent-token routes read `Authorization: Bearer <token>`, extract the raw token, then call `resolveAgentToken(rawToken, projectId)` or `resolveUserToken(rawToken)`.

### HMAC Pre-authentication (ingest routes)
Before bcrypt token verification, ingest routes compute `HMAC-SHA256(rawToken, rawBody)` and compare to the `x-pulse-signature` header using `crypto.timingSafeEqual`. This is a cheap gate that blocks unsigned requests without incurring bcrypt cost.

### RBAC Check Pattern
After auth, routes check role:
```ts
if (ctx.role !== "MANAGER") return NextResponse.json({ reason: "forbidden" }, { status: 403 })
// or for cross-team access:
if (ctx.role !== "MANAGER" && project.teamId !== ctx.teamId) return NextResponse.json({ reason: "forbidden" }, { status: 403 })
```

### Tenancy Scoping
All DB queries that list resources include `organisationId: ctx.organisationId` in `where` clauses. Resource-specific queries additionally check the `id` in `where` to avoid ID-guessing attacks (404 if not found rather than leaking existence).

### Error Response Shapes
- Auth errors: `{ error: "Unauthorized" }` with status 401.
- Permission errors: `{ reason: "forbidden" }` with status 403.
- Not found: `{ reason: "not_found" }` with status 404.
- Validation: `{ reason: "<reason_code>" }` with status 422.
- Rate limit: `{ error: "Rate limit exceeded" }` with status 429.
- Conflict: `{ reason: "<reason_code>" }` with status 409.
- Server error: `{ error: "Internal server error" }` with status 500.

### Token Hash Stripping
Responses for project resources always strip `agentTokenHash` before sending:
```ts
const { agentTokenHash: _hash, ...projectData } = project
return NextResponse.json(projectData)
```

### Fire-and-Forget Pattern
Async side effects that must not block the 200 response use `void`:
```ts
void generateNarration(event, project, traceCtx)
void linkRepoAndRefresh(projectId, repoFullName, installationId, ctx.userId)
```

### PM4 — switch-org JWT re-issue invariants

`POST /api/auth/switch-org` is the only route in the codebase that re-encodes the session JWT outside of login. It must preserve identity while moving the active org:

1. `sub` is `ctx.userId` — the verified session id. Body cannot influence this field.
2. `sessionVersion` is read from the existing session (`session.user.sessionVersion`). It is NOT incremented — the user identity is unchanged.
3. `iat` is now-seconds; `exp` is `iat + SESSION_MAX_AGE` (30 days). This is **parity with login**, not a lifetime extension — every switch costs a fresh 30-day window, the same window a fresh login produces.
4. `jti` is a new `crypto.randomUUID()` — fresh per switch, supports per-token revocation.
5. `activeOrganisationId` is sourced from `membership.organisationId` (the DB read), not from the request body. The values are equal-by-construction (the lookup queried the body's id), but stamping from the verified row encodes the "trust the proof" invariant.
6. `role`, `teamId`, `isLineManager` are NOT keys in the token object literal. The structural absence prevents stale-role smuggling: a maintainer cannot accidentally include them via spread because there is no spread. Tests decode the cookie and assert `toBeUndefined()` on each.
7. Cookie semantics match login exactly: `getCookieName(req)` returns `__Secure-authjs.session-token` when `x-forwarded-proto === "https"`, plain otherwise; cookie parts are `Path=/`, `Max-Age=2592000`, `HttpOnly`, `SameSite=Lax`, with `Secure` appended only on the `__Secure-` branch.

The forge test (`pm4-forge-switch-cross-org.test.ts`) mocks `auth()` with a valid session so that removing the membership guard would let the route reach `encode()` and emit a Set-Cookie for the forged org — the test catches that as `expected 200 to be 403`. Empirically demonstrated to fail when the guard is removed.

### PM5 — Pending Invitations & Decline Routes

**[`src/app/api/auth/pending-invitations/route.ts`](src/app/api/auth/pending-invitations/route.ts)**

`GET /api/auth/pending-invitations` — returns the caller's PENDING memberships with associated `invitationId`.

```ts
export async function GET(): Promise<NextResponse>
// → { memberships: [{ organisationId, organisationName, invitationId }] }
```
- `withAuthScoped()` → `ctx` (401 if null).
- `db.membership.findMany({ where: { userId: ctx.userId, status: "PENDING" }, include: { organisation: true } })`.
- Cross-joins with `Invitation` to surface `invitationId` for each PENDING membership.
- Used by `AppShell` to compute `pendingInviteCount`; non-zero count triggers the amber dot on `OrgBadge`.
- Route `GET()` is parameter-less — no URL/body/header inputs accepted.

**[`src/app/api/invite/decline/route.ts`](src/app/api/invite/decline/route.ts)**

`POST /api/invite/decline` — idempotent decline of a pending invitation.

```ts
export async function POST(req: Request): Promise<NextResponse>
// body: { invitationId: string }
// → 200 { ok: true } | 400 | 401 | 404
```
- `withAuthScoped()` → `ctx` (401 if null).
- Parses and validates `invitationId` from request body (400 if missing/invalid).
- Verifies the `Invitation` belongs to the caller's email and is still `PENDING` (404 if not found or already processed).
- In a single `$transaction`: deletes the `PENDING Membership` row for `(ctx.userId, invitation.organisationId)` and updates `Invitation.status = "DECLINED"`.
- Idempotent: if the PENDING Membership is already gone (e.g. concurrent decline), the transaction still marks the Invitation DECLINED and returns 200.
- Uses session cookie auth — not in `CSRF_BYPASS_PREFIXES`; goes through the CSRF gate.

**Updated: `POST /api/admin/invitations`** now returns 409 for duplicate invite attempts:
- `{ reason: "already_a_member" }` — user already has an ACTIVE Membership in this org.
- `{ reason: "invitation_already_pending" }` — a PENDING Invitation (and PENDING Membership) already exists for this email + org.

### PM4 — never-optimistic OrgBadge invariant

`src/components/OrgBadge.tsx` is the only client-side code path that can move the active org. The invariant is: **client state never reflects an active-org change until the server cookie has been re-issued**. Concretely, `selectOrg`:

- On `res.ok` (200): `setOpen(false); setPending(null); router.refresh()`. The new active org appears only because the next server render reads the new cookie. There is NO `setActiveOrg(...)` or equivalent client mutation.
- On `res.status === 401`: `router.push("/login")` — session expired mid-page.
- On any other non-ok status (403, 429, 400): `setError(...); setPending(null)`. No active-org mutation.
- On fetch reject (network error): `setError("Network error"); setPending(null)`. No active-org mutation.

`activeOrganisationId` is a read-only prop. If it were mutated client-side, an attacker who could trigger a 200 response without an actual cookie re-issue (e.g., a compromised CDN edge serving a stale 200) could shift the UI's view of the active org without the server believing it. The router-refresh-only path forces the server cookie to be the authoritative source.

The dropdown affordance (chevron + button wrapper) is gated on `memberships.length > 1` — single-membership users render the bare span chip and never invoke `selectOrg`.

---

## Error Handling Patterns

- Route handlers wrap their main logic in `try/catch`; the catch block logs via `console.error` with a `[route]` tag and returns a 500 JSON response.
- Pure library functions (narration, repo context) catch internally and return gracefully; they never propagate to callers.
- Zod validation uses `.safeParse()` (never `.parse()`) so failures return `{ success: false }` without throwing.
- Database errors from update/delete operations that may fail legitimately (e.g. concurrent edits) are caught specifically in `PATCH /api/teams/[id]` with a 500 response.
- The ingest event route uses a helper `respond()` function to ensure `endSpan` and `recordRequest` are always called even on early returns.

---

## Validation Patterns

- Zod is used for API request bodies (`BodySchema.safeParse(body)`). Failure returns 400 or 422.
- Direct body casting (`body as Record<string, unknown>`) is used for simple partial fields before Zod full validation (e.g. extracting `projectId` for project lookup before full schema check).
- Field-level guards use `typeof x === "string" && x.trim()` patterns; no Zod for individual field checks in PATCH routes.
- Email validation: `z.string().email()` in Zod schemas for `userIdHint`.
- Day format validation in ingest time: `/T00:00:00(\.000)?Z$/` regex applied after Zod schema parse.
- Enum validation for `matchType`, `scope` uses explicit `const` arrays with `.includes()`.

---

## Critical Code Paths

### Ingest Pipeline (`POST /api/ingest/event`)

1. Read raw body (max 256 KB).
2. Extract `Bearer` token from `Authorization` header.
3. Parse JSON body; extract `projectId`.
4. Verify `x-pulse-signature` header (HMAC-SHA256, constant-time compare) — cheap gate.
5. Call `resolveAgentToken(rawToken, projectId)` (per-developer table + legacy fallback).
6. Fetch project; check `status === "ACTIVE"`.
7. Check rate limit via `checkIngestRateLimit(project.id)`.
8. Full Zod body validation.
9. Resolve `userId`: from token (per-developer) → `userIdHint` email lookup → null.
10. Redact `sessionExcerpt`, `manualText`, `gitSummary` through `redact()`.
11. P-number matching via `matchPNumber(sessionExcerpt, activePrompts)` (primary Jaccard ≥ 0.6; secondary Jaccard ∈ [0.4, 0.6) + Dice bigram ≥ 0.7 — handles typos, British/American spelling drift).
12. Persist `ActivityEvent` via `create` (no `sourceMessageUuid`) or `upsert` keyed on `(projectId, sourceMessageUuid)` with empty `update: {}` (first-write-wins idempotency).
13. Fire-and-forget `generateNarration(event, project, traceCtx, anthropicApiKey)` (fetches org key via `getOrgAnthropicKey` first).
14. Fire-and-forget Anthropic Haiku (or free model fallback) feed summary for `hookSource === "Stop"` events → updates `feedSummary` field.
15. Return `{ id: event.id }` with status 200.

### Narration Pipeline (`generateNarration`)

1. Compute `inputHash` from `(pNumber, commitSha, sorted filesChanged, sessionExcerpt, gitSummary, eventKind, repoContextRefreshedAt)`.
2. Fetch latest `Intelligence` row; skip if `inputHash` matches (dedup).
3. Check in-memory cooldown map; skip if last narration < 90 s ago.
4. Set cooldown timestamp **before** API call.
5. Fetch up to 3 recent manual status events.
6. Optionally fetch `MemberDailyTime` if `team.aiUsesTime === true`.
7. Build user prompt from redacted event fields + optional repo context block.
8. Call `getAutoCallModel(anthropicApiKey)` for model selection (Anthropic Haiku primary, free model fallback); `generateText`, `maxOutputTokens: 512`.
9. Strip markdown code fences from response; JSON.parse.
10. Validate `parsed.narration` exists as string; log and return on failure.
11. Persist `Intelligence` row; call `recordClaudeTokens`.

### Auth Flow (Login)

1. Check rate limit: 5/min + 20/hr per IP.
2. Parse `{ email, password }` from body.
3. Fetch `User` by email.
4. Check `lockedUntil` (silently returns `"Invalid credentials"` if locked).
5. `bcrypt.compare(password, user.passwordHash)`.
6. On failure: increment `failedLogins`; lock if ≥ 5; audit at ≥ 4.
7. On success: reset `failedLogins`, `lockedUntil`.
8. Encode JWT via `@auth/core/jwt` `encode()` with `sub`, `role`, `teamId`, `isLineManager`, `organisationId`, `sessionVersion`. `exp = now + 30 days`.
9. Set `HttpOnly; SameSite=Lax` cookie; `Secure` if HTTPS.

### Token Resolution Flow (resolveAgentToken)

1. Compute `tokenPreview = rawToken.slice(-4)`.
2. Query `AgentToken` where `(projectId, tokenPreview, revokedAt: null)`.
3. Loop all candidates: `bcrypt.compare(PEPPER + raw, candidate.tokenHash)`.
4. On match: return `{ valid: true, userId: candidate.userId, tokenId: candidate.id }`.
5. If no match, query `Project` for `(agentTokenHash, previousTokenHash, previousTokenExpiresAt)`.
6. Try `verifyTokenWithGrace(raw, currentHash, previousHash, previousExpiresAt)`.
7. On match: return `{ valid: true, userId: null, tokenId: null }` (legacy token).
8. Otherwise: return `{ valid: false }`.

---

## Testing Patterns

### Framework & Setup
- All tests use **Vitest** (`describe`, `it`, `expect`, `vi`).
- Module mocks use `vi.mock("@/lib/db", () => ({ db: { model: { method: vi.fn() } } }))` pattern.
- `vi.hoisted(() => vi.fn())` is used for mocks that must be hoisted before imports (e.g. `mockGenerateNarration` in ingest-narration tests).
- `beforeAll` sets required env vars (`NEXTAUTH_SECRET`, `GROQ_API_KEY`).
- `beforeEach` clears mocks (`vi.clearAllMocks()`) and/or resets in-memory stores.

### Test Structure
- Tests are grouped by `describe` blocks per acceptance criterion or feature area.
- Pure function tests: call directly, assert return value. No mocking.
- Route handler tests: construct `new Request(url, { method, headers, body })` directly; call exported route function; `await res.json()` for body assertions.
- Signed request helper pattern (ingest tests):
```ts
function makeSignedRequest(body: Record<string, unknown>) {
  const rawBody = JSON.stringify(body)
  const sig = crypto.createHmac("sha256", AGENT_TOKEN).update(rawBody).digest("hex")
  return new Request(url, { headers: { Authorization: `Bearer ${AGENT_TOKEN}`, "X-Pulse-Signature": sig }, body: rawBody })
}
```

### Mocking Patterns
- `db` is always mocked with `vi.mock("@/lib/db", ...)`. Only the specific methods used by the route are mocked.
- `withAuthScoped` is mocked with `AuthContext` fixture objects. Three standard fixtures: `MANAGER_CTX`, `LM_TEAM1_CTX`, `MEMBER_TEAM1_CTX`.
- Rate limiters are bypassed in tests: either via `NODE_ENV === "test"` bypass (login) or by directly using internal `_reset*` functions and `_check*` functions.
- Narrate mock: `mockGenerateNarration.mockResolvedValue(undefined)` for fire-and-forget paths; a `setTimeout(r, 0)` drain is used to let the void promise settle before asserting.

### Multi-tenant Fuzz Tests
`src/tests/multi-tenant-fuzz.test.ts` contains 25 test cases in 4 groups:
1. **Unauthenticated → 401**: 7 routes, `mockAuth.mockResolvedValue(null)`.
2. **URL-id guessing (cross-team) → 403**: LM or MEMBER accessing another team's resource.
3. **Role escalation → 403**: MEMBER/LM attempting MANAGER-only operations.
4. **Cross-org isolation → 404**: Verifies `organisationId` is in `findUnique` where clause.

### Rate Limit Conformance Tests
`src/tests/rate-limits.test.ts` exhaustively verifies every rate limiter by calling the check function in a loop. Pattern:
```ts
for (let i = 0; i < LIMIT; i++) expect(check("key").allowed).toBe(true)
expect(check("key").allowed).toBe(false)  // one over limit
```
Includes `SCALE_TIER=4x` tests that verify 4× multiplied limits.
