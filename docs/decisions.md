# Architectural Decisions

> **Rule:** Every ADR below is grounded in evidence found in actual source files, configuration, migration SQL, or project documentation. No decision is recorded without a citation.

---

## ADR-001: AI Provider — Groq Llama 3.3 70B (not Claude / Anthropic)

**Status:** Accepted (supersedes original Anthropic design in `notes/axis-pulse-archdoc.md`)

**Context:** The architecture document (`notes/axis-pulse-archdoc.md`) specifies `claude-sonnet-4-6` as the AI model for narration. However the actual implementation diverges from this.

**Decision:** Narration (`src/lib/narrate.ts`) and feed-summary generation (`src/lib/gemini.ts`) both use **Groq** (`@ai-sdk/groq`, model `llama-3.3-70b-versatile`) rather than Anthropic Claude. The `package.json` lists `@ai-sdk/groq` as a production dependency. `GROQ_API_KEY` is the operative API key.

**Rationale (inferred from code):** The file `src/lib/gemini.ts` — named for Gemini — also calls Groq, suggesting the provider was switched mid-build. The `.env.example` references `GEMINI_API_KEY` as a "free tier" option added in P20, while `GROQ_API_KEY` is used in the running code. Groq's free tier and low-latency inference are the likely practical drivers.

**Consequences:** The cost ceiling in `src/lib/cost-ceiling.ts` still references Sonnet 4.6 pricing (`$3/1M input, $15/1M output`) but the actual model is Groq's Llama. The `/admin/budget` display is therefore an approximation. `Intelligence.modelUsed` records `"llama-3.3-70b-versatile"` not `"claude-sonnet-4-6"`.

**Evidence:** [`src/lib/narrate.ts:1-15`](src/lib/narrate.ts:15) — `const MODEL = "llama-3.3-70b-versatile"`, `createGroq({ apiKey: process.env.GROQ_API_KEY })`. [`src/lib/gemini.ts:1-47`](src/lib/gemini.ts:1) — same pattern. [`package.json:17`](package.json:17) — `"@ai-sdk/groq": "^3.0.39"`.

---

## ADR-002: Delta Gating — SHA-256 Hash of Inputs Before Every AI Call

**Status:** Accepted

**Context:** AI narration is expensive and should not fire on identical inputs. A 90-second cooldown alone is insufficient because a project with frequent identical events would still accumulate calls after the cooldown expires.

**Decision:** Before every narration call, compute `inputHash = sha256(pNumberDetected | lastCommitSha | filesChangedBucket | sessionExcerpt | gitSummary | eventKind | repoContextRefreshedAt)`. If the latest `Intelligence.inputHash` for the project equals the new hash, skip the AI call entirely. A separate 90-second in-memory cooldown is applied regardless of delta.

**Rationale:** Deterministic deduplication at zero cost. The `@@unique([projectId, inputHash])` Prisma constraint on `Intelligence` provides a database-level guard against concurrent double-writes with the same hash.

**Consequences:** The cooldown map (`cooldowns: Map<string, number>`) is in-process memory — intentionally acceptable for single-process 0.5x/1x deployments. A comment in the source (`// Acceptable for single-process 0.5x deployment; promoted to Redis in P17`) marks this as known deferred work. Snapshot refreshes invalidate the gate because `repoContextRefreshedAt` is part of the hash.

**Evidence:** [`src/lib/narrate.ts:76-97`](src/lib/narrate.ts:86) — `computeInputHash()`. [`src/lib/narrate.ts:18-25`](src/lib/narrate.ts:18) — in-memory cooldowns map with comment. [`notes/axis-pulse-archdoc.md:93-99`](notes/axis-pulse-archdoc.md:93) — delta gating specification.

---

## ADR-003: Agent Token Auth — bcrypt + Pepper + Preview Index

**Status:** Accepted (evolved from single-hash to per-developer table in P-post-3)

**Context:** Claude Code hook scripts must authenticate to `/api/ingest/event` without storing a plaintext token anywhere. The token is shown once on creation/rotation and must be irrecoverable after that.

**Decision:** Agent tokens are 32-byte `crypto.randomBytes` encoded as `base64url`. They are stored as `bcrypt(pepper + raw, cost=12)`. A 4-character `tokenPreview` (last 4 chars) is stored in plaintext for fast pre-filter lookup. A dedicated `AgentToken` table (added in migration `20260607080000_per_developer_agent_tokens`) supports per-developer tokens. Legacy `Project.agentTokenHash` is retained as a fallback with a grace-window for old installs.

**Rationale:** bcrypt at cost 12 is standard for secret storage. Pepper (`AGENT_TOKEN_PEPPER` env) adds a server-side secret that makes offline dictionary attacks against a leaked DB useless. The preview-based pre-filter avoids full-table bcrypt scans on every ingest request. Grace-window support (`verifyTokenWithGrace`) prevents service interruption when tokens are rotated.

**Consequences:** Token rotation involves two hashes in the `previousTokenHash`/`previousTokenExpiresAt` fields during the grace window. The `AgentToken` table's legacy migration comment explicitly marks `Project.agentTokenHash` as intentional tech-debt: "should be retired once all projects have ≥1 AgentToken row."

**Evidence:** [`src/lib/token.ts:1-35`](src/lib/token.ts:1) — full implementation. [`src/lib/resolveAgentToken.ts:1-63`](src/lib/resolveAgentToken.ts:1) — lookup strategy with fallback. [`prisma/migrations/20260607080000_per_developer_agent_tokens/migration.sql:1-8`](prisma/migrations/20260607080000_per_developer_agent_tokens/migration.sql:1) — migration comment documenting the intentional tech-debt.

---

## ADR-004: Three-Tier RBAC — MANAGER / LINE_MANAGER / MEMBER

**Status:** Accepted

**Context:** A single admin/user binary is insufficient for a multi-team consulting org. Managers need org-wide visibility; line managers need team-scoped visibility; members need self-only time data.

**Decision:** Three roles enforced at the application layer via `withAuthScoped()`. MANAGER has `teamId IS NULL` and sees all teams. LINE_MANAGER has `teamId IS NOT NULL` and one team. MEMBER has `teamId IS NOT NULL`. Exactly one LINE_MANAGER per team is enforced by application code (409 on second promotion attempt). Scope derivation happens in `withAuthScoped()` and produces `{ allTeams, canSeeTimeData, viewedTeamIds }` consumed by every route handler.

**Rationale:** The archdoc's role visibility matrix (`notes/axis-pulse-archdoc.md:725-738`) drove the three-tier design. The invariant "one LM per team" is app-enforced rather than DB-enforced because Postgres partial unique indexes across nullable boolean columns are complex; the app-level 409 is simpler and equally effective for a single-process deployment.

**Consequences:** Every API route must call `withAuthScoped()` before any DB query — there is no automatic middleware injection. The response serialiser must strip the `time` block from member cards when `scope.canSeeTimeData === false`. Field omission happens server-side before the response leaves the process (defence in depth).

**Evidence:** [`src/lib/withAuthScoped.ts:1-76`](src/lib/withAuthScoped.ts:22) — full implementation with `orgWhere()`, `teamWhere()` helpers. [`notes/axis-pulse-archdoc.md:65-82`](notes/axis-pulse-archdoc.md:65) — role table definition. [`notes/user-story.md:429-459`](notes/user-story.md:429) — P9 RBAC phase spec.

---

## ADR-005: Session Strategy — NextAuth v5 JWT (No Database Sessions)

**Status:** Accepted

**Context:** The app needs stateless sessions that survive process restarts and do not require a sessions table. Role and teamId must be readable from the session without a DB round-trip on every request.

**Decision:** NextAuth v5 with `session: { strategy: "jwt" }`. No credentials provider — authentication is handled by the custom `/api/auth/login` route. Role, teamId, isLineManager, organisationId, and sessionVersion are embedded in the JWT payload via the `jwt` callback.

**Rationale:** JWT sessions are cheaper (no DB query per request) and survive horizontal scale-out. The `sessionVersion` field (an integer on the `User` row, checked in `withAuthScoped`) provides a server-side invalidation mechanism: bumping the DB version forces a re-login even though the JWT is still cryptographically valid.

**Consequences:** The `_sessionVersionCache` in `withAuthScoped.ts` caches the DB version for 30 seconds to avoid a DB hit on every request. If role or team assignments change, there is up to a 30-second propagation delay before the session reflects the change — acceptable for this use case.

**Evidence:** [`src/lib/auth.ts:1-30`](src/lib/auth.ts:5) — NextAuth config with `strategy: "jwt"`, no providers. [`src/lib/withAuthScoped.ts:4-16`](src/lib/withAuthScoped.ts:4) — session version cache with 30 s TTL. [`notes/axis-pulse-archdoc.md:803-809`](notes/axis-pulse-archdoc.md:803) — authentication design spec.

---

## ADR-006: Redaction Pipeline — Dual-Layer (Client + Server), Byte-Identical

**Status:** Accepted

**Context:** Claude Code hook scripts send session excerpts (prompts, tool outputs) that may contain API keys, JWTs, AWS credentials, PEM blocks, and URL-embedded passwords. These must never reach the database or logs.

**Decision:** A 7-rule regex redaction pipeline runs on **both** the client script (`lib/redact.mjs`) and the server ingest route (`src/lib/redact.ts`). The two files implement byte-identical logic (same regex patterns, same placeholder `[REDACTED]`, same 1500-char truncation). A shared test suite (`src/tests/redact-parity.test.ts`) asserts both produce identical output on every corpus case. Rules cover: env-style assignments, JWTs, Anthropic/OpenAI keys, AWS access keys, PEM blocks, URL credentials.

**Rationale:** Defence in depth. If the client script is compromised or buggy, the server catches what was missed. The archdoc explicitly states: "raw `sessionExcerpt` never logged on any path." Redaction count and kinds are emitted to `ActivityEvent.redactionCount` and an `AUDIT` row — but the content of removed values is never recorded.

**Consequences:** The `.mjs` and `.ts` files must be kept in sync manually — there is no automatic code-sharing mechanism since one is ESM for Node scripts and one is TypeScript for the Next.js server. The parity test is the CI gate. `sessionExcerpt` in DB is guaranteed ≤ 1500 chars.

**Evidence:** [`src/lib/redact.ts:1-75`](src/lib/redact.ts:1) — server implementation. [`lib/redact.mjs:1-55`](lib/redact.mjs:1) — client implementation (byte-identical rules). [`notes/axis-pulse-archdoc.md:849-861`](notes/axis-pulse-archdoc.md:849) — redaction pipeline specification.

---

## ADR-007: Rate Limiting — Upstash Redis Sliding Window, Fail-Open

**Status:** Accepted

**Context:** The ingest endpoint and all AI-triggering routes must be protected from abuse and runaway cost. Rate limiting must work across restarts without in-process state.

**Decision:** Upstash Redis (`@upstash/ratelimit`, `@upstash/redis`) with sliding window algorithm. Each route has its own limiter instance with documented limits (e.g. ingest: 60/min/token; login: 5/min/IP; summary: 10/hr/project). When `UPSTASH_REDIS_REST_URL` or `UPSTASH_REDIS_REST_TOKEN` env vars are absent, all limiters **fail-open** (allow all requests). Rate limits scale with `SCALE_TIER` env var: 4x tier multiplies the ingest limit by 4.

**Rationale:** Fail-open is an explicit choice: blocking all requests when Redis is unavailable would stop ingest and harm the demo. The risk of a brief unprotected window during a Redis outage is acceptable for v1. Upstash's HTTP-based Redis client works from Next.js Edge and serverless contexts where a TCP Redis connection is not available.

**Consequences:** Rate limit enforcement is a deferred dependency on production Redis provisioning — recorded in `notes/pending-work.txt` as "[P4] Production Redis for Rate Limiting — PENDING." In local dev, a Docker bridge workaround is documented in the same file.

**Evidence:** [`src/lib/ratelimit.ts:1-45`](src/lib/ratelimit.ts:15) — fail-open logic and scale-tier multiplier. [`notes/pending-work.txt:8-37`](notes/pending-work.txt:8) — pending production Redis wiring. [`build-evidence/P17/agent-wave-manifest.json:13`](build-evidence/P17/agent-wave-manifest.json:13) — conformance test verifying all 12 documented route limits.

---

## ADR-008: HMAC Request Signing on Ingest Endpoint

**Status:** Accepted

**Context:** Bearer token authentication alone does not prevent replay attacks or body tampering if a token leaks via logs. The ingest endpoint receives sensitive hook payloads from developer machines.

**Decision:** Every POST to `/api/ingest/event` and `/api/ingest/time` must carry `X-Pulse-Signature: HMAC_SHA256(rawBody, agentToken)`. The server recomputes the HMAC and performs a constant-time comparison. Bearer token + HMAC must both pass; either alone is rejected.

**Rationale:** Two-factor ingest authentication: token proves identity, HMAC proves body integrity. The archdoc explicitly states this "protects against replay if the bearer token leaks via logs and against a body-only tamper attack on the transport."

**Consequences:** The client script (`pulse-send.mjs`) must HMAC-sign every payload before sending. The raw token must be available on the client machine. The HMAC secret and the bearer token are the same value — if the token is rotated, the signing key changes immediately.

**Evidence:** [`notes/axis-pulse-archdoc.md:820-823`](notes/axis-pulse-archdoc.md:820) — request signing specification. [`build-evidence/P4/agent-wave-manifest.json`](build-evidence/P3/agent-wave-manifest.json) — HMAC failure-mode evidence in P4 artifacts.

---

## ADR-009: Multi-Tenancy — organisationId Column Promotion (Not a Full Rewrite)

**Status:** Accepted

**Context:** The v1 archdoc specified a single-org deployment with a nullable `tenantKey` reserved for future multi-tenancy. During implementation, the `Organisation` entity was introduced as a concrete entity.

**Decision:** An `Organisation` model was added post-P3 via migration `20260604000001_add_organisations`. All major tables (`User`, `Team`, `Project`, `ActivityEvent`, `Intelligence`, `AuditLogEntry`, `MemberDailyTime`, `ProductiveAppRule`, `ExecutiveSummary`, `Invitation`) received an `organisationId NOT NULL` column backfilled to a seeded `org_axis_seed` row. All `withAuthScoped()` helpers inject `organisationId` into every DB query automatically via `orgWhere(ctx)`.

**Rationale:** The column-promotion approach allows multi-tenancy to be enabled by provisioning a new `Organisation` row and assigning users/teams to it — no schema migrations required. The archdoc noted: "future multi-tenant migration is a non-breaking column promotion."

**Consequences:** The `tenantKey` nullable column remains on many tables from the original design but is superseded by `organisationId` as the operative scoping field. Both exist in the schema simultaneously.

**Evidence:** [`prisma/migrations/20260604000001_add_organisations/migration.sql:1-80`](prisma/migrations/20260604000001_add_organisations/migration.sql:1) — full promotion migration with backfill. [`src/lib/withAuthScoped.ts:68-76`](src/lib/withAuthScoped.ts:68) — `orgWhere()` helper. [`notes/axis-pulse-archdoc.md:61-63`](notes/axis-pulse-archdoc.md:61) — tenantKey reservation rationale.

---

## ADR-010: PDF Export — @react-pdf/renderer (Not Playwright Headless)

**Status:** Accepted

**Context:** The archdoc listed PDF generation as an open question: "Playwright headless vs `@react-pdf/renderer` — decision in Week 4 based on Coolify image size constraints."

**Decision:** `@react-pdf/renderer` was chosen, as evidenced by its presence in `package.json` (`"@react-pdf/renderer": "^4.5.1"`). Playwright is listed only as a devDependency (`"@playwright/test": "^1.60.0"`), not used for PDF generation.

**Rationale (inferred from package.json):** `@react-pdf/renderer` runs in the Node.js process without a headless browser binary, which avoids the large Chromium bundle size and container complexity on Coolify. Playwright remains as a test dependency only.

**Consequences:** PDF styling is limited to `@react-pdf/renderer`'s PDF primitives (no arbitrary CSS). The PDF is rendered server-side in the Next.js route handler at `GET /api/projects/:id/export`.

**Evidence:** [`package.json:23`](package.json:23) — `"@react-pdf/renderer": "^4.5.1"`. [`notes/axis-pulse-archdoc.md:1001`](notes/axis-pulse-archdoc.md:1001) — PDF library decision deferred. [`notes/user-story.md:670-698`](notes/user-story.md:670) — P14 executive summary & PDF spec.

---

### ADR-010-ext: PDF Export — MEMBER Role Ungated, Financial Data Excluded Server-Side (Phase 12)

**Status:** Accepted (extends ADR-010)

**Context:** The original export route (Phase 14) restricted `GET /api/projects/[id]/export` to MANAGER and LINE_MANAGER, returning 403 for MEMBER. Phase 12 removed this restriction.

**Decision:** MEMBER role users can now request a PDF export. Financial data (`spendUSD`, `MemberDailyTime`) is conditionally excluded server-side based on the authenticated user's `canSeeSpend` flag (derived from `withAuthScoped`). When `canSeeSpend` is false, `spendUSD: null` is passed to `SummaryPDF` and the Developer AI Spend section (§7.5) is omitted from the rendered PDF. `MemberDailyTime` is not fetched at all when `canSeeSpend` is false.

**Rationale:** MEMBER users have legitimate need to view and share project intelligence. Financial data exclusion is enforced at the DB-query level (the fetch is never made), not by client-side hiding — preserving the Rule 5 invariant that MEMBER users cannot access teammates' time data or spend figures. The `SummaryPDF` component receives `spendUSD: null` as a genuine signal, not a default; it branches on this to omit the spend section entirely.

**Consequences:** The RBAC table in ADR-004 remains consistent — MEMBER still cannot see financial data; the route change only removes the blanket 403. The rate limiter at 20/hr/project applies equally to all roles. `ExecSummaryButton` now shows "View report" and "Export PDF" buttons to all users who have a stored summary, regardless of role.

**Evidence:** `src/app/api/projects/[id]/export/route.ts` — `canSeeSpend` conditional fetch; `SummaryPDFProps.spendUSD?: number | null`. `src/app/projects/[id]/_components/ExecSummaryButton.tsx` — four-button cluster visible to all roles.

---

## ADR-011: GitHub Integration — GitHub App (Not PATs)

**Status:** Accepted

**Context:** The Repository Context Layer needs read access to private GitHub repos. The alternatives were Personal Access Tokens (PATs) tied to individual users, or a GitHub App installation.

**Decision:** A GitHub App named "Axis Pulse" with `contents: read` + `metadata: read` permissions only. Installation tokens are minted per-installation using the App's private key (RS256 JWT), cached in-process for 50 minutes (tokens expire in 60 minutes). The host allowlist in `githubFetch()` restricts all calls to `api.github.com` only.

**Rationale:** The archdoc documents the decision explicitly: "private repos work out of the box; 5000+ req/hour rate budget; no human-tied credential; centralised revocation." PATs would require a team member to own the token and would expire or become invalid when that person leaves.

**Consequences:** Requires one-time setup by an org admin to register the GitHub App and add `GITHUB_APP_ID` + `GITHUB_APP_PRIVATE_KEY` (base64-PEM) to Coolify env. The `GITHUB_APP_WEBHOOK_SECRET` env var is reserved but unused in v1. Installation token caching is in-process memory (not Redis) — acceptable for single-process deployment.

**Evidence:** [`src/lib/repo-context/client.ts:1-107`](src/lib/repo-context/client.ts:62) — host allowlist enforcement, JWT minting, token cache. [`notes/axis-pulse-archdoc.md:474-481`](notes/axis-pulse-archdoc.md:474) — GitHub App rationale. [`.env.example:8-13`](.env.example:8) — GitHub App env vars.

---

## ADR-012: Repository Context — Summarised Snapshot Only (No Full Indexing)

**Status:** Accepted

**Context:** Narration quality improves when the AI knows the project's tech stack and structure, but sending full source files on every narration call would be expensive and risk leaking code.

**Decision:** A bounded JSON snapshot (≤ 8 KB) is generated at link time and stored in `Project.repoSnapshot`. It contains: top-level directory tree (≤ 20 entries), excerpts from a curated allowlist of key config files (≤ 8 files, ≤ 4 KB each, redacted), and a deterministic framework detector result. On each narration call, only the framework list, top-level paths, and config file paths are appended to the prompt — never raw config bodies.

**Rationale:** The archdoc constraint: "No full repo indexing, no embeddings, no vector search. Lightweight contextual enhancement only." Config excerpt bodies are stored in the DB for dashboard display but are explicitly excluded from per-narration prompts. Total tokens added per narration: ~150–300.

**Consequences:** The `KEY_CONFIG_ALLOWLIST` is a fixed set — extending it requires a code change. The snapshot becomes stale as the repo evolves; a 14-day staleness hint is shown in the UI. The `repoContextRefreshedAt` field is part of the `inputHash` so a manual refresh forces a fresh narration.

**Evidence:** [`src/lib/repo-context/snapshot.ts:1-31`](src/lib/repo-context/snapshot.ts:8) — `KEY_CONFIG_ALLOWLIST` and 8 KB enforcement. [`src/lib/narrate.ts:209-219`](src/lib/narrate.ts:209) — only paths/frameworks sent to AI, not raw excerpts. [`notes/axis-pulse-archdoc.md:463-467`](notes/axis-pulse-archdoc.md:463) — "not index code, no vector search" constraint.

---

## ADR-013: Time Tracking — ActivityWatch Integration, Three Integers Only

**Status:** Accepted

**Context:** Axis wanted Insightful-style activity tracking without the privacy risks of screenshot capture or window-title collection. A lightweight, privacy-first alternative was required.

**Decision:** ActivityWatch (open-source, MIT, runs locally on each team member's machine) is used as the data source. The `pulse-time.mjs` script runs every 5 minutes, reads today's window/AFK events from the local ActivityWatch REST API at `localhost:5600`, applies `ProductiveAppRule` matching **locally on the machine**, and posts only three integers (`workedSeconds`, `productiveSeconds`, `unproductiveSeconds`) plus IANA timezone to `/api/ingest/time`. The `pulse-body-shape.ts` allowlist is a CI gate: any upload body key outside the allowlist fails the test suite.

**Rationale:** "Privacy by construction" — the script has no code path that uploads window titles, URLs, or app names. The compile-time invariant is asserted by a unit test. The only data that leaves the machine is an aggregate summary of seconds.

**Consequences:** ActivityWatch must be installed separately on each team member's machine (not bundled by Axis Pulse). Time tracking is opt-in per team via `Team.timeTrackingEnabled` toggle. Members must acknowledge a non-dismissable consent modal before using the dashboard when tracking is enabled. `MemberDailyTime` stores one row per (user, day) — bounded storage of 18,250 rows/year for 50 members.

**Evidence:** [`src/lib/pulse-body-shape.ts:1-25`](src/lib/pulse-body-shape.ts:3) — upload body allowlist and CI gate. [`src/lib/consentCheck.ts:1-13`](src/lib/consentCheck.ts:1) — consent enforcement. [`notes/axis-pulse-archdoc.md:567-651`](notes/axis-pulse-archdoc.md:567) — ActivityWatch integration design.

---

## ADR-014: Productive App Rules — Client-Side Matching, Global + Team Scopes

**Status:** Accepted

**Context:** Determining whether a focused window/URL is "productive work" requires matching app names against a rule library. The matching must happen without raw app/URL data leaving the developer's machine.

**Decision:** The rule library has two scopes: `GLOBAL` (org-wide, editable by MANAGER) and `TEAM` (per-team overrides, editable by LINE_MANAGER). The merged rule list is cached at `.pulse/rules.json` on each member's machine (24-hour TTL, `If-None-Match`-driven refresh). Matching runs locally in `pulse-time.mjs` — Pulse server never sees the app names. Match types are `EXACT`, `GLOB` (simple `*` wildcard), and `REGEX`. TEAM rules override GLOBAL rules by pattern.

**Rationale:** Local matching is the privacy guarantee. The server-side `productive-rules.ts` module implements the same matching logic for tests and for any server-side use, but the operative runtime execution is on the client machine.

**Consequences:** A rule change on the server takes up to 24 hours to propagate to client machines unless the member manually refreshes. The glob implementation uses a simple `*`→`.*` regex transformation without `minimatch` — noted in a source comment: "`minimatch` is NOT in package.json, so GLOB matching is implemented as a simple regex transformation."

**Evidence:** [`src/lib/productive-rules.ts:1-136`](src/lib/productive-rules.ts:9) — match types, merge precedence, comment on minimatch absence. [`notes/axis-pulse-archdoc.md:629-643`](notes/axis-pulse-archdoc.md:629) — rule scopes and client-side matching design.

---

## ADR-015: Monthly Cost Ceiling — Hard Gate, Startup Enforcement

**Status:** Accepted

**Context:** AI narration calls must be bounded to prevent runaway spend. The archdoc required a manager-visible cost ceiling that blocks new calls when exceeded.

**Decision:** `CLAUDE_MONTHLY_CEILING_USD` env var (e.g. `"50.00"`) sets a monthly spending ceiling. `isCeilingExceeded()` sums `Intelligence.inputTokens * $3/1M + outputTokens * $15/1M` for the current calendar month and compares to the ceiling. When exceeded, narration calls short-circuit with `cost_ceiling_exceeded`. A global banner appears on every authed page. **In production, the app refuses to start if `CLAUDE_MONTHLY_CEILING_USD` is unset** — enforced by a startup check in `instrumentation.ts`.

**Rationale:** The archdoc states: "over-budget routes fail closed with a visible banner, never silently." The startup guard (`instrumentation.ts:6-8`) makes the ceiling mandatory in production — an operator cannot accidentally deploy without it.

**Consequences:** Spend tracking uses Sonnet 4.6 pricing constants even though the actual model is Groq Llama 3.3 70B — making the ceiling display an approximation. The ceiling resets at the start of each calendar month (UTC-based window).

**Evidence:** [`src/lib/cost-ceiling.ts:1-37`](src/lib/cost-ceiling.ts:7) — pricing constants and ceiling enforcement. [`instrumentation.ts:5-8`](instrumentation.ts:5) — startup guard refusing production start without ceiling. [`build-evidence/P17/agent-wave-manifest.json:12`](build-evidence/P17/agent-wave-manifest.json:12) — ceiling enforcement listed as delivered capability.

---

## ADR-016: Observability — In-Process Prometheus Metrics + Lightweight OTel Spans

**Status:** Accepted

**Context:** A manager-visible latency and cost dashboard is required, but integrating a full observability stack (Prometheus server, Jaeger, etc.) would be disproportionate for v1.

**Decision:** Metrics are stored as module-level in-process maps (`_routeStore`, `_claudeInputTokens`, `_claudeOutputTokens`) in `src/lib/metrics.ts`. Prometheus text format is generated on demand at `GET /api/metrics`. OTel spans are stored in a single `_lastTrace` in-process variable in `src/lib/otel.ts` — only one trace is retained (for build-evidence capture). All known routes are pre-registered so they appear in metrics even with zero traffic.

**Rationale:** Comment in `src/lib/metrics.ts:3`: "Module-level singleton — persists across requests in a single Node.js process (1x deployment). Promoted to Redis-backed store at 4x if needed." This matches the incremental scaling philosophy: use the simplest working solution at the current scale tier.

**Consequences:** Metrics reset on every process restart. P95 latency is computed from a rolling 24-hour in-memory sample capped at 5,000 samples. This is not suitable for multi-instance deployments. The OTel trace store only keeps the most recent trace — adequate for build-evidence capture but not for production tracing at scale.

**Evidence:** [`src/lib/metrics.ts:1-4`](src/lib/metrics.ts:1) — in-process store with scale comment. [`src/lib/otel.ts:1-5`](src/lib/otel.ts:1) — "Stores the last completed trace in memory for /build-evidence capture." [`build-evidence/P17/agent-wave-manifest.json`](build-evidence/P17/agent-wave-manifest.json) — OTel trace sample artifact.

---

## ADR-017: Structured Logging — pino with Redacted Field List

**Status:** Accepted

**Context:** Application logs must be structured for Coolify's log viewer but must never contain PII, session content, tokens, or authorization headers.

**Decision:** `pino` structured logger with a static `REDACTED_PATHS` list that replaces sensitive fields with `"[Redacted]"` at serialization time. Redacted paths include: `password`, `passwordHash`, `agentToken`, `agentTokenHash`, `sessionExcerpt`, `manualText`, `tenantKey`, `secret`, `apiKey`, `jwt`, `bearerToken`, `req.headers.authorization`, `req.headers['x-pulse-signature']`, `req.headers['x-internal-token']`.

**Rationale:** Pino's built-in `redact` option operates at serialization time — field values are never touched by string formatting. This is more reliable than post-hoc log scrubbing. The archdoc requires: "PII / session-content fields are explicitly redacted in the logger config."

**Consequences:** Fields on nested objects are only redacted if their path is explicitly listed. Developers must add new sensitive paths to `REDACTED_PATHS` when introducing new fields that carry secrets. Log level is configurable via `LOG_LEVEL` env var (default `"info"`).

**Evidence:** [`src/lib/logger.ts:1-37`](src/lib/logger.ts:5) — full REDACTED_PATHS list and pino config. [`notes/axis-pulse-archdoc.md:897`](notes/axis-pulse-archdoc.md:897) — "pino structured logger to stdout; PII / session-content fields are explicitly redacted."

---

## ADR-018: Security Headers — Per-Request CSP Nonce via Middleware

**Status:** Accepted

**Context:** Next.js 14 App Router injects inline bootstrap scripts for hydration. A static `script-src 'self'` CSP would block these scripts. But `'unsafe-inline'` would defeat CSP entirely.

**Decision:** The middleware generates a per-request nonce (`btoa(crypto.randomUUID())`) and passes it as `x-nonce` header. The CSP uses `'nonce-${nonce}'` plus `'strict-dynamic'` so Next.js's generated scripts are stamped automatically. In development, `'unsafe-eval'` is appended for webpack source maps; in production it is omitted.

**Rationale:** Comment in `src/middleware.ts:14-17` documents this explicitly: "Next.js 14 App Router injects inline bootstrap scripts for hydration, so a static 'self'-only script-src blocks them. A per-request nonce passed via x-nonce lets Next.js stamp its own generated scripts automatically."

**Consequences:** The CSP includes `https://api.anthropic.com` in `script-src` — a holdover from the original Anthropic Claude design that may no longer be necessary given the switch to Groq.

**Evidence:** [`src/middleware.ts:14-35`](src/middleware.ts:14) — nonce generation and CSP construction. [`notes/axis-pulse-archdoc.md:826-829`](notes/axis-pulse-archdoc.md:826) — transport and headers spec.

---

## ADR-019: P-Number Detection — Jaccard Similarity (No Embeddings)

**Status:** Accepted

**Context:** The system must auto-classify which numbered prompt workflow a Claude Code session is running. The alternatives were embedding-based similarity or deterministic text matching.

**Decision:** Jaccard similarity on the first 200 tokenized, lowercased, punctuation-stripped characters of each event's session text against each active `Prompt.fingerprint`. Highest similarity ≥ 0.6 wins. Below threshold → `pNumberDetected = null` → dashboard shows "Free workflow." Managers can manually override per event.

**Rationale:** The archdoc states: "Free, deterministic, fast. No embeddings, no vector store." Jaccard avoids embedding API costs and operational complexity. The 0.6 threshold and manager override provide graceful fallback for mismatches.

**Consequences:** Fingerprint quality depends on the first 200 characters of each prompt being distinctive. The 0.6 threshold is hardcoded in the matcher. Similar prompts in the same category could produce false positives.

**Evidence:** [`notes/axis-pulse-archdoc.md:450-459`](notes/axis-pulse-archdoc.md:450) — Jaccard specification and rationale. [`notes/user-story.md:300-326`](notes/user-story.md:300) — P6 prompt library phase spec with acceptance criteria.

---

## ADR-020: Consent Model — Versioned, Non-Dismissable, Re-Consent on Schema Change

**Status:** Accepted

**Context:** Time tracking collects behavioural data. Informed consent is required. The initial design used a simple `acknowledgedAt` timestamp.

**Decision:** `TimeTrackingConsent` has a `consentVersion` integer (added in migration `20260612000001_three_bucket_time_top_apps`). `consentCheck.ts` requires `acknowledgedAt` to be set AND `consentVersion >= 2`. Members who consented under v1 (aggregate-only) must re-consent when v2 (which adds `topApps` app-name collection) is deployed. The consent modal blocks the entire dashboard until clicked.

**Rationale:** Migration comment: "v1=aggregate-only, v2=includes app names." The version bump was triggered by the `topApps` JSONB field addition to `MemberDailyTime` — a material change to what data is collected that warrants fresh consent.

**Consequences:** All previously-consented users see the modal again on upgrade to v2. Demo seed accounts must have `consentVersion = 2` to avoid blocking the demo.

**Evidence:** [`src/lib/consentCheck.ts:10-12`](src/lib/consentCheck.ts:10) — version gate `(consent.consentVersion ?? 1) < 2`. [`prisma/migrations/20260612000001_three_bucket_time_top_apps/migration.sql:7-9`](prisma/migrations/20260612000001_three_bucket_time_top_apps/migration.sql:7) — consentVersion column with v1/v2 comment.

---

## ADR-021: Hook-Based Event Capture (Not a Polling Daemon)

**Status:** Accepted

**Context:** Capturing Claude Code activity requires either a persistent polling daemon or Claude Code's native hook extension points.

**Decision:** Claude Code's `PostToolUse`, `Stop`, and `UserPromptSubmit` hooks invoke `pulse-send.mjs` as a subprocess on each event. The script exits 0 silently on success and logs to `.pulse/log` on failure — never blocking the Claude session. No persistent daemon is installed.

**Rationale:** The archdoc documents explicitly: "Event-driven: zero polling cost when idle. No daemon to install, monitor, or keep running. Cross-platform free (Claude Code abstracts OS). Strongest 'fully agentic' narrative for judges."

**Consequences:** Events only land when Claude Code is active. A network failure causes the event to be dropped (logged locally, not queued for retry). Install footprint is six JSON lines in `.claude/settings.json` plus `.pulse/pulse-send.mjs`.

**Evidence:** [`notes/axis-pulse-archdoc.md:756-796`](notes/axis-pulse-archdoc.md:756) — hook vs daemon rationale. [`build-evidence/P5`](build-evidence/) — P5 evidence confirming E2E hook installation and event flow.

---

## ADR-022: Risk Schema — Three-Level riskLevel Replaces Boolean hasRisk

**Status:** Accepted (supersedes original boolean design)

**Context:** The original `Intelligence` schema used `hasRisk: Boolean` and `riskLabel: String?`. A boolean cannot distinguish HIGH from MEDIUM risk.

**Decision:** Migration `20260613000001_risk_level_focus` dropped `hasRisk` and `riskLabel`, replacing them with `riskLevel TEXT NOT NULL DEFAULT 'LOW'` (LOW / MEDIUM / HIGH) and `riskFocus TEXT?`. Existing rows backfilled: `hasRisk=true → MEDIUM`. The narration system prompt was updated to output the new fields.

**Rationale:** Migration comment: "hasRisk=true → MEDIUM (conservative default; no HIGH signal available from boolean)." Three levels allow the UI to distinguish shared-area changes (MEDIUM) from core-infrastructure changes (HIGH).

**Consequences:** Historical `Intelligence` rows with `hasRisk=true` now show as MEDIUM even if they were genuinely HIGH. The `<RiskBadge />` component now branches on three values.

**Evidence:** [`prisma/migrations/20260613000001_risk_level_focus/migration.sql:1-10`](prisma/migrations/20260613000001_risk_level_focus/migration.sql:1) — migration with backfill logic. [`src/lib/narrate.ts:53-70`](src/lib/narrate.ts:53) — updated system prompt with riskLevel/riskFocus output schema.

---

## Technology Choices

| Technology | Role | Evidence |
|---|---|---|
| **Next.js 14 (App Router)** | Full-stack framework — server components for data, route handlers for API, streaming for exec summary | [`package.json:33`](package.json:33) `"next": "14.2.35"` |
| **PostgreSQL + Prisma** | Primary data store with typed query builder; migrations in `prisma/migrations/` | [`prisma.config.ts`](prisma.config.ts), 50+ migration files |
| **Prisma PG Adapter** | Driver adapter connecting Prisma to the `pg` connection pool (not the default Prisma connection) | [`src/lib/db.ts:1-23`](src/lib/db.ts:1) — `PrismaPg` adapter with connection pool |
| **NextAuth v5** | JWT session management and CSRF protection; no database sessions | [`src/lib/auth.ts`](src/lib/auth.ts) |
| **bcryptjs** | Password hashing (cost 12) and agent token hashing (cost 12 + pepper) | [`src/lib/password.ts`](src/lib/password.ts), [`src/lib/token.ts`](src/lib/token.ts) |
| **Upstash Redis** | HTTP-based Redis for rate limiting; works from Edge and serverless | [`src/lib/ratelimit.ts`](src/lib/ratelimit.ts) |
| **@ai-sdk/groq** | Groq Llama 3.3 70B for narration and feed summaries | [`src/lib/narrate.ts:1`](src/lib/narrate.ts:1), [`src/lib/gemini.ts:1`](src/lib/gemini.ts:1) |
| **ai (Vercel AI SDK)** | `generateText` and `streamText` abstraction layer over AI providers | [`package.json:25`](package.json:25) `"ai": "^6.0.194"` |
| **@react-pdf/renderer** | Server-side PDF generation for executive summary export | [`package.json:23`](package.json:23) |
| **shadcn/ui + Tailwind CSS** | Component library and utility CSS; radix-ui primitives | [`package.json:37`](package.json:37), [`components.json`](components.json) |
| **pino** | Structured JSON logging to stdout with field-level redaction | [`src/lib/logger.ts`](src/lib/logger.ts) |
| **Sentry** | Unhandled exception reporting; `sendDefaultPii: false` across all configs | [`sentry.client.config.ts`](sentry.client.config.ts), [`sentry.server.config.ts`](sentry.server.config.ts) |
| **vitest** | Unit and integration test runner | [`package.json:54`](package.json:54) `"vitest": "^4.1.7"` |
| **Playwright** | End-to-end test infrastructure (devDependency only; not used for PDF generation) | [`package.json:50`](package.json:50) |
| **Coolify** | Self-hosted deployment platform (Caddy reverse proxy, Docker containers, scheduled tasks for cron) | [`notes/axis-pulse-archdoc.md:905-917`](notes/axis-pulse-archdoc.md:905) |
| **ActivityWatch** | Open-source local time-tracking client (not bundled; installed separately by members) | [`notes/axis-pulse-archdoc.md:573`](notes/axis-pulse-archdoc.md:573) |
| **zod** | Runtime schema validation | [`package.json:46`](package.json:46) |

---

## Trade-offs Documented

### Fail-Open Rate Limiting
When `UPSTASH_REDIS_REST_URL` is absent, all rate limiters allow all requests rather than blocking everything. This means a misconfigured production deployment has no rate limiting. The trade-off is documented in [`notes/pending-work.txt:14-18`](notes/pending-work.txt:14): "If either env var is missing OR Redis is unreachable → fail-open (all requests pass)."

### In-Process Metrics and Cooldown State
Narration cooldowns (`cooldowns: Map<string, number>`) and Prometheus metrics (`_routeStore`) are in-process module-level state. They reset on every process restart and do not survive multi-instance scale-out. Source comments acknowledge this: "Acceptable for single-process 0.5x deployment; promoted to Redis in P17." The trade-off accepts operational simplicity over correctness at scale.

### Dual .ts/.mjs Redaction Files
The server (`src/lib/redact.ts`) and client (`lib/redact.mjs`) implement the same 7-rule redaction pipeline in two separate files — one TypeScript, one ESM JavaScript — with no automatic code-sharing. The parity test (`src/tests/redact-parity.test.ts`) is the only safety net. The trade-off accepts sync risk for architectural simplicity: keeping the client script free of TypeScript compilation.

### Cost Ceiling Pricing Mismatch
`src/lib/cost-ceiling.ts` uses Anthropic Claude Sonnet 4.6 pricing (`$3/1M input, $15/1M output`) but the actual model is Groq Llama 3.3 70B (which has different pricing). The `/admin/budget` dashboard is therefore an approximation. This is an implicit trade-off created by the provider switch mid-build.

### Jaccard P-Number Matching at 0.6 Threshold
The similarity threshold is hardcoded at 0.6 and is not tunable via config. The archdoc describes it as "tunable" but the code does not expose it as an env var or config field. A false match shows the wrong P-number; the manager override flow provides the escape hatch.

### Session Version Propagation Delay
Role changes take up to 30 seconds to propagate to live sessions because `_sessionVersionCache` in `withAuthScoped.ts` has a 30-second TTL. A promoted LINE_MANAGER may see stale permissions for up to 30 seconds.

### Snapshot Generation in Request Handler
The GitHub repo snapshot (`lib/repo-context/`) is generated synchronously inside the Next.js request handler — ~9 GitHub API calls, ~2 seconds typical. The archdoc acknowledges: "On timeout → ERROR state + retry button; never blocks event ingestion." This avoids a background worker but means snapshot requests have higher latency than typical API calls.

---

## Technical Debt

The following items are evidenced by source comments, pending-work.txt entries, or migration SQL comments:

1. **Production Redis not provisioned** — Rate limiting is fail-open until `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set in Coolify. Documented in [`notes/pending-work.txt:8-37`](notes/pending-work.txt:8).

2. **Coolify deploy not yet wired** — CI/CD webhook to Coolify is pending manual setup. Documented in [`notes/pending-work.txt:89-124`](notes/pending-work.txt:89).

3. **Live GROQ_API_KEY not configured in production** — P13 and P14 acceptance criteria requiring live AI calls (streaming exec summary, time-enriched narration) are marked PENDING because no AI API key is set. Documented in [`notes/pending-work.txt:41-85`](notes/pending-work.txt:41). **Note**: `notes/pending-work.txt:44` still reads "ANTHROPIC_API_KEY not configured in .env" — this is a stale reference to the original provider. The actual runtime uses `GROQ_API_KEY` per `src/lib/narrate.ts:233` and `src/app/api/projects/[id]/summary/route.ts`. The pending-work notes themselves need updating.

4. **Legacy Project.agentTokenHash fallback** — The `AgentToken` table supersedes per-project hashes but `Project.agentTokenHash` columns are intentionally retained. Migration comment: "intentional migration tech-debt, should be retired once all projects have ≥1 AgentToken row." See [`prisma/migrations/20260607080000_per_developer_agent_tokens/migration.sql:7-8`](prisma/migrations/20260607080000_per_developer_agent_tokens/migration.sql:7).

5. **Narration cooldown not Redis-backed** — The `cooldowns: Map<string, number>` in `src/lib/narrate.ts` is in-process. Comment: "Acceptable for single-process 0.5x deployment; promoted to Redis in P17." However P17 was implemented without this promotion — the cooldown remains in-process.

6. **GitHub App webhook secret unused** — `GITHUB_APP_WEBHOOK_SECRET` is provisioned in `.env.example` and the archdoc secrets table, but the archdoc notes "Reserved for future webhook support; not used in v1."

7. **CSP includes api.anthropic.com** — The `script-src` directive in `src/middleware.ts` includes `https://api.anthropic.com` — a holdover from the original Anthropic design. This is unnecessary given the switch to Groq and is a minor CSP scope over-grant.

8. **tenantKey columns superseded by organisationId** — Many tables have both `tenantKey TEXT?` (from the original design) and `organisationId TEXT NOT NULL` (from migration `20260604000001`). The `tenantKey` columns are effectively dead but remain in the schema.

9. **OTel trace store keeps only one trace** — `_lastTrace` in `src/lib/otel.ts` is a single in-memory slot. This was intentionally designed "for /build-evidence capture" and is not a production-grade tracing solution.

10. **Consent version check hardcoded at 2** — [`src/lib/consentCheck.ts:12`](src/lib/consentCheck.ts:12) checks `(consent.consentVersion ?? 1) < 2`. Future consent changes would require a code change to bump this constant.

---

## Future Considerations

The following planned changes, migration paths, or scaling considerations are found in the documentation:

### Multi-Tenancy (Planned, Not Built)
The `Organisation` model and `organisationId` columns on every table form the foundation for multi-tenant SaaS. The archdoc states: "A nullable `tenantKey` column is reserved so a future multi-tenant migration is non-breaking." The actual migration (`20260604000001_add_organisations`) implements this as a non-breaking column promotion — new tenants require only a new `Organisation` row.
**Evidence:** [`prisma/migrations/20260604000001_add_organisations/migration.sql`](prisma/migrations/20260604000001_add_organisations/migration.sql), [`notes/axis-pulse-archdoc.md:29-31`](notes/axis-pulse-archdoc.md:29).

### Redis-Backed Cooldowns and Metrics at 4x
Both the narration cooldown map and the Prometheus metrics store are documented as candidates for Redis promotion at 4x scale. The metrics file comment explicitly says "Promoted to Redis-backed store at 4x if needed."
**Evidence:** [`src/lib/metrics.ts:3`](src/lib/metrics.ts:3), [`src/lib/narrate.ts:19`](src/lib/narrate.ts:19).

### Context Drift Analyser (Implemented)
The Context Drift Analyser monitors whether a project's committed code has drifted from its context documentation. It is fully implemented across API routes, lib modules, a Prisma model, and 13 test files.

**Architecture decisions:**
- **Async pipeline**: `POST /api/projects/[id]/drift` returns 202 immediately with `{ assessmentId, status: "PENDING" }`. The pipeline runs async: PENDING → RUNNING → COMPLETE/ERROR. `GET /api/projects/[id]/drift/[assessmentId]` polls for result. Stale RUNNING assessments (>5 min = STALE_RUNNING_MS) auto-transition to ERROR on the next GET.
- **Baseline SHA model**: `Project.contextBranchBaselineSha` stores the commit SHA of the last known-good context state. `POST /drift/baseline` captures it. BASELINE_INVALID (force-push erased the baseline) surfaces as ERROR without auto-reset — requires a manual baseline refresh.
- **Context source priority**: `resolveContextSource()` checks for a `context_builds` branch first (higher signal quality); falls back to `/docs` on the default branch; reports "none" if neither exists.
- **Risk thresholds**: RED = any HIGH finding or ≥4 MEDIUM. AMBER = 1–3 MEDIUM. GREEN = no HIGH or MEDIUM. Defined in `src/lib/drift/compute-risk.ts`.
- **Volume trigger**: `incrementVolumeCounter()` increments a per-project in-process counter after every ingest event. When it reaches VOLUME_THRESHOLD (50), an automatic ON_DEMAND assessment fires. Counter resets to 0. Mirrors narration cooldown pattern.
- **In-process cooldown**: DRIFT_COOLDOWN_MS = 30 min per projectId. Prevents spam from ON_DEMAND triggers without a database round-trip.
- **Rate limit**: 3 assessments per hour per project (in-memory; Upstash-upgradeable). `src/lib/ratelimit-drift.ts`.
- **AI analysis**: `analyseAiDrift()` in `src/lib/drift/analyse-ai.ts` uses Groq via `ai-provider.ts`. Cost ceiling checked before every call. `DriftFinding` type carries `type` (ACCURACY/COVERAGE), `area`, `doc`, `description`, `severity` (LOW/MEDIUM/HIGH), `confidence`.
- **Audit actions**: CONTEXT_ASSESS written by `POST /drift`; CONTEXT_BASELINE_SET written by `POST /drift/baseline`.

**Evidence:** [`src/app/api/projects/[id]/drift/route.ts`](src/app/api/projects/[id]/drift/route.ts), [`src/lib/drift/orchestrate.ts`](src/lib/drift/orchestrate.ts), [`src/lib/drift/compute-risk.ts`](src/lib/drift/compute-risk.ts), [`src/lib/drift/analyse-ai.ts`](src/lib/drift/analyse-ai.ts), [`src/lib/repo-context/drift-github.ts`](src/lib/repo-context/drift-github.ts), `src/tests/drift-*.test.ts` (13 test files).

### Dashboard Sparklines and Activity Feed (Implemented)
`features/DASHBOARD-SPARKLINES/Build.md` planned 7-day sparkline bars on each dashboard stat card and a live activity feed. These ARE implemented: `src/lib/dashboard.ts` defines `SparklineWeek` type and runs two `$queryRaw` sparkline queries; `src/app/dashboard/_components/SparkBars.tsx` renders the bars; `ActivityFeedClient.tsx` renders the live feed. The `DashboardSummary` type includes `sparklines` and `activityFeed` fields.
**Evidence:** [`src/lib/dashboard.ts`](src/lib/dashboard.ts), [`src/app/dashboard/_components/SparkBars.tsx`](src/app/dashboard/_components/SparkBars.tsx).

### Dashboard Redesign (Implemented)
`features/DASHBOARD-REDESIGN/Build.md` planned a `/api/dashboard/summary` endpoint and redesigned stat cards. These ARE implemented: `GET /api/dashboard/summary` exists at `src/app/api/dashboard/summary/route.ts`; `DashboardStatsClient.tsx` renders four KPI cards (Events Today, Active Members, Prompts Matched Today, Active Projects) with sparklines; `StatCard.tsx` is the reusable card component. 30-second polling is active.
**Evidence:** [`src/app/api/dashboard/summary/route.ts`](src/app/api/dashboard/summary/route.ts), [`src/app/dashboard/_components/DashboardStatsClient.tsx`](src/app/dashboard/_components/DashboardStatsClient.tsx).

### Per-Project Daily Token Budget Removal
Migration `20260609000002_remove_daily_token_budget` removed `Project.dailyTokenBudget` (which was `100,000 tokens/day` per the archdoc design). This was superseded by the monthly ceiling approach in P17. A per-developer token budget was added separately (`20260609000003_add_dev_token_budget`).
**Evidence:** Migration files `20260609000002` and `20260609000003`.

### GitHub Webhooks (Reserved, Not Implemented)
`GITHUB_APP_WEBHOOK_SECRET` is in `.env.example` and provisioned in the archdoc secrets table. The archdoc says "Reserved for future webhook support; not used in v1." Webhooks would allow push-triggered snapshot refreshes without polling.
**Evidence:** [`.env.example:12`](.env.example:12), [`notes/axis-pulse-archdoc.md:843`](notes/axis-pulse-archdoc.md:843).

### MFA (Scoped Out)
No MFA is implemented. The archdoc's risk register documents this explicitly: "MFA not implemented — medium likelihood, low impact — mitigated by lockout + rate limit + strong password policy." Documented as v1 scope-out.
**Evidence:** [`notes/axis-pulse-archdoc.md:809`](notes/axis-pulse-archdoc.md:809), [`notes/axis-pulse-archdoc.md:1029`](notes/axis-pulse-archdoc.md:1029).

### 4x Scale Graduation (Partially Complete)
The archdoc specifies a P18 scale graduation to 12–20 teams / 8 managers / ~96–480 projects with index audits, load testing, and Redis tier increases. Migration `20260603110000_p18_scale_indexes` adds indexes for the hot query paths. The full 4x load test and scale-down rehearsal are still pending.
**Evidence:** [`prisma/migrations/20260603110000_p18_scale_indexes/migration.sql`](prisma/migrations/20260603110000_p18_scale_indexes/migration.sql), [`notes/user-story.md:856-889`](notes/user-story.md:856).

### ADR-code-health-001: Code Health — SonarQube CB + Synchronous execSync Scan

**Status:** Accepted

**Context:** Phase 9 adds code health scoring (reliability, security, maintainability ratings, quality gate, coverage, duplication) to the project detail page. The feature must work on a self-hosted Coolify deployment with no serverless function limits.

**Decision:**
1. Use **SonarQube Community Build** (LGPL-3.0 Docker image `sonarqube:community`) as the static analysis engine. Configured via `SONAR_HOST_URL`, `SONAR_SCANNER_HOST_URL`, `SONAR_TOKEN`, `SONAR_PROJECT_KEY` env vars.
2. Scans run **synchronously** via `child_process.execSync` inside the POST scan route. The `sonarsource/sonar-scanner-cli:latest` Docker image is invoked, which mounts the project root and communicates with SonarQube.
3. Scan results are stored in `CodeHealthSnapshot` and the project page **reads from DB only** — zero SonarQube calls in the render path.
4. The Refresh button triggers `POST /api/projects/[id]/code-health/scan`. Rate-limited to 1/120s per project (Upstash sliding window).

**Rationale:** SonarQube CB is LGPL-3.0 and runs entirely on-premise — no data leaves the self-hosted environment. `execSync` is acceptable for a single-process self-hosted deployment with no Vercel 10s limit. Async via a job queue would be over-engineering for the current deployment model.

**Consequences:** A slow scan (up to 5 minutes) blocks the Node.js process during `execSync`. This is acceptable in the current single-project self-hosted context. A future scale-up to many parallel scans would require migrating to an async job queue. The 120-second rate limit prevents concurrent scan accumulation.

**Evidence:** `src/lib/code-health.ts` — `execSync(cmd, { timeout: timeoutMs, stdio: "pipe" })`. `src/app/api/projects/[id]/code-health/scan/route.ts` — synchronous POST handler. `src/lib/ratelimit-code-health.ts` — 1/120s sliding window.

---

### ADR-code-health-002: Central Scan — Model D (server fetches tarball, scans, hard-deletes source)

**Status:** Accepted

**Context:** Phase 9b extends code health to any project with a connected GitHub repo, not just the local axis-pulse codebase. The server must fetch the repo source, scan it with SonarQube, and never retain the source after the scan.

**Decision:**
1. **Server fetches tarball** via `downloadRepoTarball()` using the existing GitHub App installation token (`authedGithubFetch`). The tarball is streamed directly to `/tmp/pulse-scan-{projectId}-{ts}/repo.tar.gz`.
2. **Per-project SonarQube key**: `org-{orgId}-proj-{projectId}`. The `orgId` comes from the authed session context (`ctx.organisationId`), never from the client request.
3. **Auto-provisioning**: `ensureSonarProject()` creates the SonarQube project before first scan using a separate `SONAR_ADMIN_TOKEN`. Idempotent — "already exist" is treated as success.
4. **Hard-delete in `finally`**: `rmSync(tmpDir, { recursive: true, force: true })` runs in a `finally` block so source is always deleted, even on scanner failure.
5. **Multi-tenancy proof**: route verifies `db.githubInstallation.findUnique({ where: { organisationId_installationId: { organisationId: ctx.organisationId, installationId: project.githubInstallationId } } })` → 403 if null. The installation ID comes from a project already fetched with `organisationId: ctx.organisationId`, so no org can claim another org's installation.
6. **Semaphore**: `MAX_CONCURRENT_SCANS = 2` (in-process). Returns 503 if full. Protects the host's Docker daemon from unbounded concurrent container launches.
7. **EDGE path retained**: projects without a GitHub link still use `process.cwd()` + `SONAR_PROJECT_KEY`; `scanSource = "EDGE"`.

**Rejected alternatives:**
- *Model A* (developer runs scanner, pushes results): requires developer-side tooling; no way to verify the scan ran against the declared commit.
- *Model B* (CI/CD pipeline pushes results): requires CI changes in every connected repo.
- *Model C* (clone via git): requires git binary, SSH keys, or PAT; tarball is simpler and avoids git history overhead.

**Evidence:** `src/lib/code-health.ts`, `src/app/api/projects/[id]/code-health/scan/route.ts`, `prisma/migrations/20260615000001_add_code_health_scan_source/migration.sql`.

---

### ADR-security-scan-001: Security Scanning — Local CLI Tools (Not a Cloud SAST Service)

**Status:** Accepted

**Context:** Phase 10 adds a "Needs a Look" security panel to the project detail page, surfacing findings from SAST, secret detection, and dependency vulnerability scanning. The options were: (a) a hosted SAST cloud service (Snyk, SonarCloud), (b) a Docker-based scanner, or (c) locally installed CLI tools invoked directly by the application server.

**Decision:**
1. **Three local CLI tools**: Semgrep CE (`semgrep`), gitleaks (`gitleaks`), and osv-scanner (`osv-scanner`) are invoked directly via `child_process` in `src/lib/security-scan.ts`. No Docker containers are required for the security scan path (unlike the SonarQube code-health scan).
2. **Reuse Phase 9b tarball plumbing entirely**: `downloadRepoTarball`, `extractTarball`, and `tryAcquireScanSlot`/`releaseScanSlot` from `src/lib/code-health.ts` are reused verbatim. The tarball lifecycle (download → extract → scan → `rmSync` in finally) is identical.
3. **Catch-and-continue per tool**: If any tool is not installed or exits with an error, that tool returns 0 findings and the others continue. A missing CLI is not a hard failure.
4. **Severity mapping is tool-specific**: Semgrep ERROR→HIGH, WARNING→MEDIUM, else INFO; gitleaks always CRITICAL; osv-scanner uses `database_specific.severity` (MODERATE→MEDIUM) or CVSS vector heuristic.
5. **`scanState` distinguishes "not scanned yet" from "scanned clean"**: The `ExceptionsPanel` shows different empty states for `"not_scanned"` vs `"scanned_clean"` — honest about whether a scan has ever run (§5.9 honest empty states principle).

**Rationale:** Local CLI tools run entirely on the self-hosted Coolify instance — no data leaves the private infrastructure. No SaaS API keys or per-scan billing. The three selected tools cover complementary attack surfaces: Semgrep (code patterns), gitleaks (secrets in source), osv-scanner (known CVEs in dependencies). Docker was not chosen because the existing SonarQube scan already uses Docker; adding a second Docker invocation path for security was not warranted when the CLI tools provide equivalent coverage.

**Rejected alternatives:**
- *Cloud SAST service*: requires external data transmission and per-scan billing.
- *Docker-based scanner*: would duplicate the existing Docker-in-scan infrastructure from Phase 9b without benefit.
- *Single tool only*: Semgrep alone would miss secrets and dependency CVEs; gitleaks alone would miss code patterns.

**Consequences:** CLI tools must be installed on the server where the Next.js process runs. Missing tools silently produce 0 findings with no error surfaced to the user — a known operational risk (see `docs/risk.md` P22). The semaphore from `src/lib/code-health.ts` is shared with SonarQube scans (`MAX_CONCURRENT_SCANS = 2`), so a simultaneous code-health scan and security scan will contend for slots.

**Evidence:** `src/lib/security-scan.ts`, `src/app/api/projects/[id]/security-scan/route.ts`, `src/lib/ratelimit-security-scan.ts`.

---

### ADR-security-scan-002: Security Findings Merged With Operational Exception Flags, Sorted Worst-First

**Status:** Accepted

**Context:** The project detail page already shows operational exception flags (high risk, cost spike, stall, repo stale) in the "Needs a Look" panel via `ExceptionsPanel`. Security findings from the new scan pipeline need to appear in the same panel without a separate UI section.

**Decision:** Security findings are converted to `ExceptionFlag` objects via `securityFindingToExceptionFlag()` in `src/lib/project-exceptions.ts`, merged with operational flags in `src/app/projects/[id]/page.tsx`, and sorted worst-first by the unified `SEVERITY_WEIGHT` map (CRITICAL:5, HIGH:4, MEDIUM:3, LOW:2, INFO:1). `ExceptionFlag.severity` was extended from `"high" | "medium"` to `"critical" | "high" | "medium" | "low" | "info"` to accommodate the 5-level security severity scale. An optional `source` field identifies the originating tool.

**Rationale:** A single merged and sorted list presents a coherent "things that need attention" view regardless of whether the finding is AI-detected (narration risk) or statically scanned (security tool). The project page server component bears the responsibility for merging and sorting — the panel component remains a pure display layer.

**Evidence:** `src/lib/project-exceptions.ts` (`securityFindingToExceptionFlag`), `src/app/projects/[id]/page.tsx`, `src/app/projects/[id]/_components/ExceptionsPanel.tsx`.

---

### ADR-readiness-001: Readiness signals are per-tool, never aggregated into a single %
**Decision:** The ReadinessWidget shows each signal (markers, coverage, CI, forecast) in its own labelled cell. There is no aggregated "X% ready to ship" or "completion %" of any kind.
**Rationale:** An aggregated readiness % requires a denominator of total scope, which is not measurable from code metrics alone. Any such number would be misleading — a project could have 0 markers but still be missing critical requirements. Each signal is honest about its source and its own limits.
**Evidence:** [`src/app/projects/[id]/_components/ReadinessWidget.tsx`](src/app/projects/[id]/_components/ReadinessWidget.tsx).

### ADR-readiness-002: Forecast requires ≥ 3 snapshots (FORECAST_MIN_SNAPSHOTS = 3)
**Decision:** `computeForecast` returns `{ kind: "insufficient" }` when fewer than 3 snapshots exist. The forecast is never extrapolated from 1 or 2 data points.
**Rationale:** Two points trivially define any line — a "trend" from two points is not a trend, it's the definition of the line through those points. Three points is the minimum for the OLS residual to be non-trivially informative. Any fewer is noise.
**Evidence:** [`src/lib/readiness.ts`](src/lib/readiness.ts) — `FORECAST_MIN_SNAPSHOTS = 3`.

### ADR-readiness-003: Scan root is process.cwd() (LOCAL ONLY, no CI integration in Phase 8)
**Decision:** `scanMarkersInDir` and `readCoveragePct` both use `process.cwd()` as the scan root. CI status (GitHub Actions) and SonarQube quality gate are shown as "not measured yet" in Phase 8.
**Rationale:** This is a single-project self-hosted Coolify deployment. `process.cwd()` is the application root, which is also the codebase root on this deployment. External CI and SonarQube integration are deferred to Phase 9 to avoid scope creep.
**Known risk:** On a container or non-root-mounted deployment, `process.cwd()` may not be the project codebase root — see risk register. Evidence: [`src/app/api/projects/[id]/readiness/scan/route.ts`](src/app/api/projects/[id]/readiness/scan/route.ts).

---

### ADR-security-scan-003: Security Finding Path Normalization (stripSrcPrefix)

**Status:** Accepted

**Context:** When the security scan pipeline extracts a repo tarball to a temp directory, tool output contains absolute paths rooted at that temp dir. Storing these absolute paths in `SecurityFinding.file` would make findings meaningless after the temp dir is deleted and would leak internal server path structure.

**Decision:** After all three tools complete, `runAllSecurityTools` calls `stripSrcPrefix(filePath, srcDir)` on every finding's `file` field. This converts absolute temp-dir paths to repo-relative paths (e.g. `safeai-intelli/security_pwa/index.html`) before the findings are written to the DB. `stripSrcPrefix` removes the leading `srcDir` prefix (normalised to forward slashes) and any leading slash from the result. If the file path does not start with `srcDir`, it is left unchanged.

**Rationale:** Repo-relative paths are stable across re-scans and deployments, match what developers see in their editor, and do not reveal server directory structure. The conversion is lossy (absolute path is gone) but intentionally so — the temp dir is deleted immediately after the scan anyway.

**Evidence:** `src/lib/security-scan.ts` (stripSrcPrefix, runAllSecurityTools), `src/app/api/projects/[id]/security-scan/route.ts`.

---

### ADR-security-scan-004: GNU tar Windows Compatibility (try-with-fallback extraction)

**Status:** Accepted

**Context:** The tarball extraction step uses `child_process.execSync("tar ...")` on Windows. Two tar implementations are in use depending on how the server process was started: (1) GNU tar 1.35 (from Git Bash / MinGW in PATH), which requires `--force-local` to prevent drive letters (C:) being interpreted as remote hostnames; (2) Windows built-in bsdtar (`C:\Windows\System32\tar.exe`), which does NOT support `--force-local` but handles Windows drive-letter paths natively. Statically detecting which tar is present at module load time is unreliable because Next.js HMR does not reinitialize module-level IIFEs on hot reload.

**Decision:** Both paths are normalised to forward slashes (C:\path → C:/path) before being passed to tar. The extraction first attempts `tar --force-local -xf ...`; if that throws an error containing "--force-local is not supported" (bsdtar's exact message), it retries with `tar -xf ...`. All other errors are re-thrown. Tested: GNU tar path PASS, bsdtar path PASS (bsdtar 3.8.4 libarchive).

**Rationale:** A try-with-fallback avoids module-level state (which has HMR caching issues in Next.js dev mode) and works correctly regardless of which tar binary is in the server process's PATH. The one extra execSync call on bsdtar is negligible — it runs only on the first failure, and tarball extraction is fast compared to the GitHub download that precedes it.

**Evidence:** `src/lib/code-health.ts` (extractTarball).

---

## ADR-spend-lm: LINE_MANAGER Spend Visibility in Member Detail Card

**Status:** Accepted  
**Date:** 2026-06-16

**Full ADR:** `features/member-detail-card/adr-spend-visibility.md`

**Decision:** LINE_MANAGER can see spend (USD + tokens) for their own team members via `GET /api/admin/members/[id]/card`. This widens spend visibility beyond the previous MANAGER-only access on the cost-dashboard. Spend is omitted server-side (key absent from response) when `canSeeSpend=false`; this flag is computed from `ctx.role` on the server and never read from the request.

**Evidence:** `src/lib/member-card.ts` (`getMemberCard`, `canSeeSpend` param); `src/app/api/admin/members/[id]/card/route.ts` (role gate); `src/tests/member-card.test.ts` (`"spend" in result!` assertion); `src/tests/member-card-route.test.ts` (cross-org + cross-team 403/404 proofs).

---

## ADR-member-card-dual-tz: Dual-Timezone Windowing in Member Detail Card

**Status:** Accepted  
**Date:** 2026-06-16

**Context:** The member detail card has two logically distinct data categories that require different timezone references for windowing:
1. **Time-at-keyboard (MemberDailyTime):** rows represent the member's local calendar day, stored as UTC midnight. A member in Asia/Dubai working on "June 17 locally" stores `day = 2026-06-17T00:00:00Z`. Filtering by viewer UTC would return the wrong day.
2. **Event-based data (spend, sessions, commits, projects):** these are `ingestedAt` timestamps. The viewer wants to see "what happened today from my perspective," matching the existing `resolveTimeWindow` pattern on the project page.

**Decision:** Two separate windowing mechanisms are applied and must not be cross-applied:

- **Time section:** `computeMemberTimeRange(window, memberTz)` uses `Intl.DateTimeFormat("en-CA", { timeZone: memberTz })` to derive the member's local calendar date as UTC midnight. `memberTz` is read from `MemberDailyTime.findFirst({ orderBy: { day: "desc" } })` — the most recent row's timezone. Falls back to UTC if no rows exist. This is DAY-ROW SUMMING, not an event cutoff.

- **Event sections:** `resolveTimeWindow(rawWindow, viewerTodayMs).start` produces a `since` Date in the viewer's timezone. Applied as `ingestedAt: { gte: since }` on spend, sessions, commits, and projects queries. This is an EVENT CUTOFF, not day-row summing.

- **lastSeenAt:** NOT windowed. The `_max: { ingestedAt }` aggregate for identity has no `ingestedAt` filter — it answers "last seen ever."

**Security invariant:** The `window` and `viewerTodayMs` params are time-narrowing only. They are applied as additive `where` clause filters on top of the existing `organisationId + userId + role/team` gate. A malicious or forged `window` param can only reduce the data returned, never expose data from another user, team, or org.

**Evidence:** `src/lib/member-card.ts` (`computeMemberTimeRange`, `resolveTimeWindow` import, Phase 1 `latestTzRow` lookup); `src/tests/member-card.test.ts` (tz-windowing describe block with Dubai/NY fake-timer edge cases); `src/tests/member-card-route.test.ts` (window param forwarding tests).

---

## ADR-023: PM2 — Membership table as read-shadow for multi-org migration

**Status:** Accepted
**Date:** 2026-06-21

**Context:** PM1 completed `withAuthScoped` routing for all 12 pages. PM2 is the next step toward multi-org: a `Membership` table that mirrors `User.(organisationId, role, teamId, isLineManager)` as one row per `(user, organisation)` pair. Doing the full cutover in a single phase — table + backfill + read switch in `withAuthScoped` + JWT plumbing + every route + runtime write hooks — would touch the auth boundary, every read path, and the migration simultaneously. That is the wrong shape for a multi-tenancy change where a single missed call site is a cross-tenant leak.

**Decision:** Split the change into phases.
- **PM2 (this ADR):** Introduce the `Membership` table + atomic in-migration backfill as a pure **read-shadow**. No production code reads from it. `User.organisationId/role/teamId/isLineManager` remain authoritative.
- **PM3:** Switch reads from `User.*` to `Membership.*` in `withAuthScoped` (and any other read sites), behind a feature flag if necessary.
- **PM4+:** Add runtime write paths (user creation, role change, team move, multi-org assignment) and eventually drop the old `User.*` columns.

**Consequences:**
- Old `User.organisationId/role/teamId/isLineManager` columns remain authoritative through PM2; PM3 is the cutover.
- Storage cost is negligible — one row per user, single-digit kilobytes at current scale.
- New invariant: `Membership.count() === User.count()` post-PM2 migration. Enforced by `src/tests/membership-backfill.test.ts` (3 assertions: count parity, field parity on the four mirrored columns, exactly one Membership per User in their current org).
- Cascade invariant: deleting a `User` removes their `Membership` rows via `ON DELETE CASCADE`. Enforced by `src/tests/membership-cascade.test.ts` inside a rolled-back transaction.
- The composite `@@unique([userId, organisationId])` makes duplicate memberships impossible at the DB level.

**Reversibility / Live-DB safety:**
- Migration is **additive-only**. It only creates the `Membership` table, its indexes, its three FKs, and reads from `User` for the backfill. **Zero** `ALTER`/`DROP`/`UPDATE`/`DELETE` on existing tables.
- Lock posture: `INSERT INTO "Membership" SELECT FROM "User"` takes `ACCESS SHARE` on `User` — read-only, compatible with concurrent reads and writes against `User`. Creating the new `Membership` table itself acquires no lock on any existing table. There is no `ALTER TABLE "User"` at any point.
- Reversible by `DROP TABLE "Membership" CASCADE`. Because no production code reads from `Membership` in PM2, a drop has no behavioural impact — the system continues reading from `User.*` exactly as it does today.
- Prod-apply gate: the generated `migration.sql` was reviewed by the user against the local-generated file before any `prisma migrate deploy` against production.

**Verification:**
- Local-generated migration SQL reviewed and approved by the user before any prod apply.
- Three real-DB assertion tests pass against local data (`membership-backfill.test.ts`).
- One real-DB cascade test passes inside a rolled-back transaction (`membership-cascade.test.ts`).
- `npx prisma migrate diff --from-config-datasource --to-schema prisma/schema.prisma --exit-code` returns 0 (schema and migrations agree, no drift).

**Evidence:** `prisma/migrations/20260621173803_add_membership_table/migration.sql`; `prisma/schema.prisma` (`Membership` model + back-relations on `User`, `Organisation`, `Team`); `src/tests/membership-backfill.test.ts`; `src/tests/membership-cascade.test.ts`.

---

## ADR-024: PM3 — Tenancy boundary moves into `withAuthScoped` via Membership lookup

**Status:** Accepted (PM3 shipped 2026-06-21)

**Context:** Before PM3, the JWT carried `organisationId`, `role`, `teamId`, and `isLineManager` as trusted claims. `withAuthScoped` extracted them and returned an `AuthContext` directly — the JWT signature was the only thing standing between an attacker and an arbitrary org claim. Two concrete weaknesses in that posture:

1. A leaked `NEXTAUTH_SECRET` would allow a forged JWT claiming membership in any org, with no second check.
2. In the multi-org future (PM4+), a user with memberships in orgs A and B would have nothing stopping them — at the JWT layer — from setting `activeOrganisationId="C"` and accessing org C's data. The JWT itself would be the only authority.

PM2 introduced `Membership` as a read-shadow (one row per `(user, organisation)` pair, populated by the migration backfill). PM3 makes that table the authoritative source.

**Decision:** The JWT becomes role-less. It carries `sub`, `activeOrganisationId`, and `sessionVersion` only. On every authenticated request, `withAuthScoped` performs a single `findUnique` against `Membership(userId, organisationId)` (the composite unique index from PM2). Missing row → `null` ctx → caller returns 401. The `ctx.role`/`teamId`/`isLineManager`/`organisationId` fields are populated from the Membership row.

**The asymmetry that makes this work:** `userId` is sourced from `session.user.id`, which NextAuth writes from `token.sub` — verified by the JWT signature. An attacker without `NEXTAUTH_SECRET` cannot change `sub` without invalidating the signature, in which case `auth()` returns null and we never enter the membership lookup. `activeOrganisationId` is the only field treated as untrusted. So the composite lookup `(verifiedUserId, possiblyForgedOrg)` either finds the user's real row or finds nothing.

**Login flow change:** the route now calls `db.membership.findFirst({ where: { userId }, orderBy: { createdAt: "asc" } })` and stamps `membership.organisationId` into the JWT as `activeOrganisationId`. Returns an opaque `"Invalid credentials"` 401 if no Membership exists — never leaks that the account is present-but-orphaned.

**Signup flow change:** `User.create` and `Membership.create` happen in a single `$transaction`. Self-signup creates a `Membership(role: MANAGER)`; invitation acceptance creates one with the invite's role/team/org. The existing-user invitation-link path also updates `Membership.teamId` and `Membership.role` to keep them in sync with the legacy `User.teamId` column. The old `User.organisationId/role/teamId/isLineManager` columns are still written on signup — they are dropped in PM6.

**Forge tests** (the proof, all four green and empirically verified to fail when the corresponding guard is bypassed):

| Test | File | Scenario | Empirical-regression check performed |
|---|---|---|---|
| (a) | `pm3-forge-cross-org-resource.test.ts` | User member of orgs A+B, active=B, GET an org-A project → 404 | Dropping `organisationId: ctx.organisationId` from the route's `where` clause → test fails |
| (b) | `pm3-forge-header-ignored.test.ts` | `X-Active-Org` header is never read; grep + `headers.get` scan over src/ | Adding `request.headers.get("x-active-org")` anywhere in a route → test fails |
| (c) | `pm3-forge-tampered-jwt.test.ts` | JWT claims membership in org-C, no Membership(u1, org-C) exists → null ctx → 401 | Removing `if (!membership) return null` from `withAuthScoped` → test fails |
| (d) | `pm3-forge-revoked-mid-session.test.ts` | sessionVersion bumped OR Membership deleted mid-session → null ctx → 401 | Disabling the sessionVersion drift gate → test (d.1) fails |

**Consequences:**
- One extra indexed read per authenticated request (the `@@unique([userId, organisationId])` composite from PM2). Accepted.
- The ~158 `ctx.role === "..."` sites across route handlers are **unchanged** — `AuthContext` keeps its shape; only the source of its fields changes.
- Four direct-`session.user.*` callsites outside `withAuthScoped` (`github/connect`, `install/page`, `layout.tsx`, `AppShell.tsx`) were migrated to call `withAuthScoped` and read `ctx.role`/`ctx.organisationId`. After PM3, the JWT's active-org claim is read in exactly one place: `withAuthScoped` itself.
- Old `User.organisationId/role/teamId/isLineManager` columns kept as PM6 fallback; no read path consults them.
- Ingest paths (`/api/ingest/event`, `/api/ingest/time`) confirmed unaffected — they use AgentToken + HMAC, never `withAuthScoped` (verified by grep).

**Out of scope (PM3):** UI to switch active org (PM4); org-list endpoint that lists a user's memberships (PM4); removing the legacy `User.*` columns (PM6); changing the ingest path's AgentToken→org binding (separate stream).

**Verification:**
- Four forge tests pass; each empirically demonstrated to fail when the corresponding guard is removed (see table above).
- Full Vitest suite: 1788 passed, 4 skipped.
- `tsc --noEmit` baseline: zero new errors in `src/`; the +12 in `src/tests/` is the same `vi.mocked()` + Prisma overload pattern as the existing baseline (see `feedback_tsc_baseline_drift` memory note).
- Exhaustive grep audit: exactly 5 callers of `auth()` in `src/`, zero JWT-decode-outside-NextAuth, zero request-side org reads.

**Evidence:** `src/lib/withAuthScoped.ts` (the membership lookup); `src/lib/auth.ts` (slimmed session callback); `src/types/next-auth.d.ts` (role-less JWT shape); `src/app/api/auth/login/route.ts` (Membership-resolves-activeOrganisationId); `src/app/api/auth/signup/route.ts` (User+Membership in `$transaction`); `src/tests/pm3-forge-*.test.ts` (the four forge tests); `src/tests/multi-tenant-fuzz.test.ts` Group 4b (two-membership fixture); the four Task-3 migrations of bypass sites.

## ADR-025: PM4 — Multi-org switching via JWT re-issue, gated by Membership composite-key

**Status:** Accepted (PM4 shipped 2026-06-21)

**Context:** PM3 made the `Membership(userId, organisationId)` row the proof of belonging — the JWT's `activeOrganisationId` claim is treated as a hint, and every authenticated request resolves it through `withAuthScoped`. With that boundary in place, PM4 adds the user-visible piece: a memberships list endpoint, a switch-org endpoint that moves the active org, and a sidebar dropdown UI.

The threat surface PM4 must NOT introduce:
1. **Enumeration** — a logged-in user must never be able to query "what orgs is user X in?" via any code path.
2. **Cross-org JWT forgery** — switching to an org you are not a member of must be impossible regardless of body tampering.
3. **Stale-role smuggling** — the JWT must remain role-less; a re-issue must not re-introduce `role`/`teamId`/`isLineManager` claims that would bypass PM3's per-request Membership lookup.
4. **Client-side forgery** — the UI must never optimistically render an active-org change that the server has not actually confirmed via cookie re-issue.

**Decision — three primitives, all gated by the same Membership composite-key check that PM3 made authoritative:**

1. **`GET /api/auth/memberships`** — caller-only enumeration. The route handler is declared `export async function GET()` with **no `Request` parameter** — no URL, header, or body can be read because there is no binding in scope. The only `userId` source is `ctx.userId` from `withAuthScoped`. A structural forge-guard test (`src/tests/memberships-api.test.ts`) reads the route source from disk and pins the absence of every input idiom (`new URL(`, `searchParams`, `nextUrl`, `next/headers` imports, `headers()/cookies()/draftMode()` calls, any GET parameter, request-scoped `headers/json/text/formData`). Sanity-checked by injecting each bypass — test fails on every one.

2. **`POST /api/auth/switch-org`** — re-issues the session JWT with a new `activeOrganisationId` after verifying `(ctx.userId, targetOrgId) ∈ Membership` via the same composite-key `findUnique` as `withAuthScoped`. The forge asymmetry is the same as PM3: `userId` from the verified session, `targetOrgId` is the only request input. The re-issued JWT carries only `sub`/`name`/`email`/`activeOrganisationId`/`sessionVersion`/`iat`/`exp`/`jti` — `role`/`teamId`/`isLineManager` are not keys in the token object literal (structural protection, not just an absent value). Cookie semantics are byte-for-byte parity with login: proto-aware `__Secure-` prefix, `Path=/`, `Max-Age=2592000`, `HttpOnly`, `SameSite=Lax`. `iat`/`exp` are refreshed on each switch (parity with a fresh login, not lifetime extension). The route is rate-limited per `ctx.userId` (10/min AND 60/hr, dual-window; `src/lib/ratelimit-switch-org.ts`) and goes through the CSRF middleware gate (not in `CSRF_BYPASS_PREFIXES`).

3. **`OrgBadge` dropdown** — never-optimistic. The component renders the dropdown affordance only when `memberships.length > 1`; single-membership users see the bare chip exactly as before. On selection, `fetch` POSTs to switch-org; on `res.ok`, `router.refresh()` re-runs the server tree (which reads the new cookie). The client **never** mutates an "active org" state; `activeOrganisationId` is a read-only prop. On `res.status === 401`, the dropdown redirects to `/login`. On 403/429/other, it surfaces an inline error and does not move the active org. This closes the client-side forgery surface — an attacker who could forge a 200 response (e.g., compromised edge) cannot shift the UI's view of the active org without also producing a real server-issued cookie.

**Forge test (the proof, empirically demonstrated to fail when the guard is removed):**

| Test | File | Scenario | Empirical-regression check performed |
|---|---|---|---|
| (e) | `src/tests/pm4-forge-switch-cross-org.test.ts` | Caller member of org-A only; POSTs `{ organisationId: "org-Z" }` → 403, no Set-Cookie | With `auth()` mocked (so a session is present and the rate limit allows), removing `if (!membership) return 403` lets the route reach `encode()` and emit `Set-Cookie` + 200. The assertion `expected 200 to be 403` catches it directly — the actual cookie-issuance attack, not an incidental 401 from upstream unmocking. |

Plus the structural forge guard (`memberships-api.test.ts`): reads the memberships route source from disk; sanity-checked by injecting `new URL(request.url)`, `import { headers } from "next/headers"`, and a named `GET(req: Request)` parameter — test fails on each.

**Cookie / production-path coverage:** added HTTPS Secure-cookie assertions to BOTH `src/tests/switch-org.test.ts` and `src/tests/login.test.ts`. The `x-forwarded-proto=https` branch is the one that runs behind Coolify's HTTPS termination in production — previously untested for either route.

**Consequences:**
- One extra `findMany` per AppShell render (the memberships list for the dropdown), parallelized with the org-name lookup via `Promise.all`.
- One extra `findUnique` per switch-org POST (the membership check). Rate-limited per user.
- JWT shape unchanged from PM3 — the switch-org route does not reintroduce role claims.
- Mid-page session loss now redirects to `/login` from the dropdown (was: silent "Switch failed" stuck state).
- The `--error-fg` design token was added to `globals.css` so the dropdown's inline error message has adequate contrast in light mode (~5.6:1 on `--sidebar-surface = #dde2f0`).
- Multi-tab semantics: each browser tab has its own session cookie. Switching in one tab does not move the others until they `router.refresh()`. This is acceptable for a security-first design — each tab is its own session window.

**Out of scope (PM4):** A "favorite org" / persisted last-active-org server-side (the cookie IS the active-org state); per-org branding/theming; the membership management UI (PM5+); removing the legacy `User.organisationId/role/teamId/isLineManager` columns (PM6).

**Verification:**
- Forge test (e) passes; empirically demonstrated to fail when the membership guard is removed.
- Structural forge guard on `memberships-api.test.ts` passes; sanity-checked against three injected bypasses.
- HTTPS branch coverage added to both `switch-org.test.ts` and `login.test.ts`.
- CSRF gate confirmed unchanged: `grep switch-org src/middleware.ts` returns empty; `CSRF_BYPASS_PREFIXES` still excludes the route.
- Full Vitest suite: 1801 passed, 4 skipped.
- tsc baseline: 1130 errors (unchanged from PM3 tip; all in `src/tests/`, none in `src/`).

## ADR-027: PM3-COMPLETE — Membership as data-plane source of truth for admin member management

**Status:** Accepted (PM3-COMPLETE shipped 2026-06-22)

**Context:** ADR-024 (PM3) made `Membership` the **auth-plane** source of truth — `withAuthScoped` looks up the Membership row to determine `role`, `teamId`, and `isLineManager` for every request. However, the admin management routes (GET listing, promote, demote, role, assign-to-team, remove-from-team, PATCH, activate, deactivate, card) still read from and wrote to `User.role`/`User.teamId`/`User.isLineManager` — the old fields. This created a split state: `withAuthScoped` read from `Membership` but the management UI wrote to `User`, requiring both tables to stay in sync manually.

**Decision (Phase 2):** `GET /api/admin/members` reads only from `Membership(status=ACTIVE)`, not `User.organisationId`. The `role` and `isLineManager` fields in the response are always taken from the Membership row. LINE_MANAGER queries additionally filter by `Membership.teamId`. This completes the listing data-plane migration.

**Decision (Phase 3):** All management write routes (promote, demote, role, assign-to-team, remove-from-team, PATCH `[id]` for teamId) write `role`, `teamId`, and `isLineManager` exclusively to `Membership`. They no longer touch `User.role`, `User.teamId`, or `User.isLineManager`. `User.sessionVersion` is still incremented on any role change — the JWT reads `User.sessionVersion` for cache-invalidation; this field was never on Membership.

**Decision (Phase 3b):** The activate, deactivate, and card routes adopt the Membership composite-key lookup (`findUnique({ where: { userId_organisationId: { userId, organisationId } } })`) for their existence check and LINE_MANAGER team boundary. `User.isActive` remains the field that actually controls account access (login lockout checks `User.isActive`); the Membership lookup is used for tenancy-scoped existence confirmation and role/teamId retrieval only.

**Q21 last-manager guard:** `PATCH /role` and `POST /demote` must prevent demoting the last active MANAGER in an org. The guard counts `db.membership.count({ where: { organisationId, status: "ACTIVE", role: "MANAGER", NOT: { userId: targetId } } })`. Using `membership.count` (not `user.count`) is deliberate: PENDING or non-member rows are excluded by `status: "ACTIVE"`, so only seated, active managers count toward the threshold. Returns 409 `last_manager_cannot_demote` when the count is 0.

**PM5 fix (POST /api/admin/members):** `POST /api/admin/members` received the same PM5 fix applied earlier to `/api/admin/invitations`. When the invited email matches an existing user, the route now creates both the `Invitation` and a `PENDING Membership` atomically in a `$transaction`. Previously, only an `Invitation` was created, leaving a window of inconsistency between the Invitation and the Membership states. Duplicate-invite guards (`already_a_member` / `invitation_already_pending`) operate on the Membership status, consistent with ADR-026.

**Invariants maintained:**
- `User.role`, `User.teamId`, `User.isLineManager` remain in the schema for legacy compatibility but are no longer the source of truth for org membership data — `Membership` fields are authoritative.
- `User.isActive` remains authoritative for account lockout/activation (login checks `User.isActive`, not `Membership.status`).
- `User.sessionVersion` remains on `User` (JWT must be invalidatable even when Membership is PENDING or deleted).
- All management routes continue to enforce `organisationId` scoping via composite-key lookups — no cross-tenant risk from the migration.

**Consequences:**
- The `User` table's `role`/`teamId`/`isLineManager` fields are now effectively stale for all rows — any code that reads them directly (outside of `withAuthScoped`) will see the pre-PM3 state. This is acceptable in the current single-org deployment; PM6 will drop these columns.
- The Q21 guard is now resilient to invited-but-not-yet-accepted manager counts: PENDING managers do not contribute to the active-manager count.
- Listing performance: one `Membership.findMany` with `status=ACTIVE` replaces the old `User.findMany` — equivalent complexity; indexed on `organisationId`.

**Forge tests** (empirically verified to fail when the corresponding guard is removed):

| Test | File | Scenario |
|---|---|---|
| Phase 2 | `pm3-data-plane-listing.test.ts` | `GET /api/admin/members` calls `membership.findMany` with `status:"ACTIVE"`; role in response from Membership |
| Phase 3 | `pm3-member-management-membership.test.ts` | All management routes write to Membership; `User.update` never receives `role`/`teamId`/`isLineManager` |
| Q21 | `pm3-last-manager-guard.test.ts` | Mock omits `user.count` — any call throws; proves guard uses `membership.count` |
| PM5 fix | `pm5-members-route-invite.test.ts` | `POST /api/admin/members` creates PENDING Membership+Invitation atomically for existing users |

**Out of scope (PM3-COMPLETE):** Dropping `User.role`/`User.teamId`/`User.isLineManager` columns (PM6); migrating the invite-accept flow to read teamId from Invitation rather than User (already correct via PM5 Membership).

**Evidence:** `src/app/api/admin/members/route.ts`; `src/app/api/admin/members/[id]/route.ts`; `src/app/api/admin/members/[id]/{promote,demote,role,assign-to-team,remove-from-team,activate,deactivate,card}/route.ts`; `src/tests/pm3-data-plane-listing.test.ts`; `src/tests/pm3-last-manager-guard.test.ts`; `src/tests/pm3-member-management-membership.test.ts`; `src/tests/pm5-members-route-invite.test.ts`.

---

## ADR-026: PM5 — PENDING Membership for safe existing-user invitation

**Status:** Accepted (PM5 shipped 2026-06-22)

**Context:** Before PM5, inviting a user who already had an account required either (a) instantly granting them ACTIVE Membership and access to the org before they had a chance to accept, or (b) creating only an `Invitation` row with no Membership counterpart and leaving the accept flow to create the Membership lazily. Option (a) is a security violation — access must not be granted until acceptance. Option (b) means there is a window where the `withAuthScoped` lookup returns null for a user who has theoretically been invited but not yet set up a Membership, creating an inconsistency between the Invitation state and the auth state.

**Decision:** When an existing user is invited to an org, the `POST /api/admin/invitations` handler creates both the `Invitation` row and a `PENDING Membership` row in a single `$transaction`. The PENDING Membership:
1. Exists in the DB immediately (consistent state — Invitation always has a counterpart Membership).
2. Grants **no authenticated access** — `withAuthScoped` checks `membership.status !== "ACTIVE"` after finding the row and returns `null` (→ 401) for any PENDING row.
3. Is flipped to `ACTIVE` atomically when the user accepts (`POST /api/invite/accept`), which also bumps `User.sessionVersion` to invalidate any cached sessions.
4. Is deleted atomically when the user declines (`POST /api/invite/decline`), and the `Invitation.status` is set to `DECLINED`.

**New `MembershipStatus` enum** (`PENDING | ACTIVE`): added in migration `20260621203926_membership_status`. Existing rows default to `ACTIVE` — backward-compatible. A new `@@index([userId, status])` supports efficient queries for pending invitations.

**New `InvitationStatus.DECLINED`**: added in migration `20260621205617_invitation_status_declined`. Allows distinguishing "never responded" from "explicitly declined" in invitation history.

**Duplicate invite guard**: `POST /api/admin/invitations` returns 409 with `{ reason: "already_a_member" }` if an ACTIVE Membership already exists, or `{ reason: "invitation_already_pending" }` if a PENDING Invitation + Membership already exists. This prevents double-invite races.

**`GET /api/auth/pending-invitations`**: returns the caller's PENDING memberships with `invitationId`. Used by `AppShell` to compute `pendingInviteCount`; non-zero renders an amber indicator dot on `OrgBadge`.

**The status gate is the single chokepoint**: `withAuthScoped` is the only entry point for authenticated routes. Adding the `status !== "ACTIVE"` check there means all 158+ `ctx.role === "..."` sites across the codebase automatically respect the gate — no per-route changes were needed.

**Forge tests** (empirically verified to fail when the corresponding guard is removed):

| Test | File | Scenario |
|---|---|---|
| (f) | `pm5-invite-creates-pending-membership.test.ts` | Inviting existing user creates PENDING Membership + Invitation atomically; duplicate invite → 409 |
| (g) | `pm5-forge-pending-no-access.test.ts` | User with PENDING membership → `withAuthScoped` returns null → 401 on any protected route |
| (h) | `pm5-forge-pending-no-switch.test.ts` | `POST /api/auth/switch-org` with PENDING membership → 403, no Set-Cookie |

**Out of scope (PM5):** UI in `AppShell` to display and act on pending invitations (post-PM5 UI work); removing the legacy `User.organisationId/role/teamId/isLineManager` columns (PM6); the decline affordance from the badge dropdown (follow-on UI).

**Evidence:** `prisma/migrations/20260621203926_membership_status/migration.sql`; `prisma/migrations/20260621205617_invitation_status_declined/migration.sql`; `src/lib/withAuthScoped.ts` (status gate); `src/app/api/auth/pending-invitations/route.ts`; `src/app/api/invite/accept/route.ts` (PENDING→ACTIVE flip + sessionVersion bump); `src/app/api/invite/decline/route.ts`; `src/app/api/admin/invitations/route.ts` (atomic Invitation+PENDING Membership creation + 409 guards); `src/tests/pm5-*.test.ts`.

---

## ADR-028: PM6 — Drop legacy User columns (role, teamId, isLineManager, organisationId)

**Status:** Accepted (PM6 shipped 2026-06-22)

**Context:** From PM2 through PM5, the `User` table carried four columns that duplicated data now authoritative in `Membership`: `role`, `teamId`, `isLineManager`, and `organisationId`. These were kept as a rollback fallback through the PM2–PM5 migration series:
- PM2 (ADR-023): `Membership` created; columns still read and written.
- PM3 (ADR-024): `withAuthScoped` reads from `Membership`; legacy columns no longer consulted at runtime but still written on signup.
- PM3-COMPLETE (ADR-027): all management write routes (promote/demote/role/assign-team) write exclusively to `Membership`; legacy columns become stale.
- PM5 (ADR-026): PENDING membership flow — no new reads of legacy `User.*` fields introduced.

By the time PM3-COMPLETE shipped, every read path was sourcing role/team/org data from `Membership`. The legacy columns were dead weight: stale data that no code read, yet which could confuse future developers or be accidentally written by a regression.

**Pre-flight verification (commit `07c06cad`):** A grep audit confirmed zero `select: { role/teamId/isLineManager/organisationId }` reads outside of `withAuthScoped` (which already used `Membership`); zero `update: { role/teamId/isLineManager/organisationId }` writes in any route. The only remaining writes were in `src/app/api/auth/signup/route.ts` and `src/app/api/invite/accept/route.ts` — both were removed in the same commit. All three tests that referenced `User.role` in their fixtures (`membership-cascade.test.ts`) were updated to remove the stale field from `user.create()` calls.

**Decision:** Drop `User.role`, `User.teamId`, `User.isLineManager`, and `User.organisationId` from the schema and database. Migration `20260622000001_drop_user_legacy_cols`:
- `ALTER TABLE "User" DROP CONSTRAINT "User_organisationId_fkey"`
- `ALTER TABLE "User" DROP CONSTRAINT "User_teamId_fkey"`
- `DROP INDEX "User_organisationId_idx"`, `"User_role_idx"`, `"User_teamId_idx"`
- `ALTER TABLE "User" DROP COLUMN "isLineManager"`, `"organisationId"`, `"role"`, `"teamId"`

No `CREATE`, `INSERT`, or `UPDATE` statements — pure structural cleanup. A pg_dump snapshot was taken before the prod deploy as the sole rollback path (the migration is irreversible without a restore).

**Consequences:**
- `User` is now a pure identity + authentication record: `email`, `passwordHash`, `isActive`, `failedLogins`, `lockedUntil`, `sessionVersion`, `tenantKey`. Org membership and RBAC are 100% in `Membership`.
- The schema compiler (`tsc`) now catches any future attempt to read `user.role`/`user.teamId`/`user.isLineManager`/`user.organisationId` at build time — what was a convention risk becomes a compile error.
- Three test files updated: `membership-cascade.test.ts` (removed `role` from `tx.user.create()` fixture), `membership-backfill.test.ts` (replaced cross-column parity assertions with referential-integrity + exactly-one-Membership checks, since the source columns no longer exist).
- `src/lib/userToken.ts` — `resolveUserToken` now reads `teamId` from `Membership.findFirst` instead of `User.findUnique`. `organisationId` comes from `UserToken` (stored at token creation time).

**Multi-org membership model** (consolidating ADR-023/024/027/028): The final authoritative shape is: one `User` row holds credentials; one or more `Membership` rows bind that user to organisations with a role, team, and status. Every authenticated boundary (`withAuthScoped`, login, switch-org, pending-invitations) operates on `Membership` only. No auth-plane data lives on `User` except `sessionVersion` (needed for drift detection regardless of membership state) and `isActive` (needed for lockout, which must function even for users with no active Membership).

**RBAC three-tier per Membership** (consolidating ADR-004/024/027/028): The three-tier `MANAGER`/`LINE_MANAGER`/`MEMBER` role hierarchy is stored exclusively in `Membership.role`. A user's effective role for a given request is determined by the `Membership(userId, activeOrganisationId)` row resolved in `withAuthScoped`. There is no fallback to `User.role` — the column does not exist. A user may have different roles in different organisations (one `Membership` row per org per user).

**Per-request Membership verification boundary** (consolidating ADR-024/028): Every session-authenticated request passes through `withAuthScoped`, which performs a single `db.membership.findUnique({ where: { userId_organisationId: { userId, organisationId: activeOrganisationId } } })`. The composite unique index `@@unique([userId, organisationId])` makes this a constant-time lookup. The result is the sole source of truth for the request's `role`, `teamId`, `isLineManager`, and `organisationId`. No request caches these values between calls (except `sessionVersion`, which is cached for 30 s in `_sessionVersionCache`).

**Verification:**
- `npx prisma migrate diff --from-config-datasource --to-schema prisma/schema.prisma --exit-code` returns 0 (schema and DB agree, no drift).
- `npx tsc --noEmit` exits 0 for `src/` (zero new errors in application code).
- Full Vitest suite: 1811 tests passed (same count as PM5 tip; no regressions from column-drop or test-fixture fixes).
- CI GREEN on commit `98430fde` (post test-fixture fix for cascade test).
- Prod deployed to Coolify; `withAuthScoped` confirmed functional in production.

**Evidence:** `prisma/migrations/20260622000001_drop_user_legacy_cols/migration.sql`; `prisma/schema.prisma` (`User` model without legacy fields); `src/lib/withAuthScoped.ts` (Membership-only lookup); `src/lib/userToken.ts` (Membership.findFirst for teamId); `src/app/api/auth/signup/route.ts` (no User.role/teamId writes); `src/tests/membership-cascade.test.ts` (updated fixture); `src/tests/membership-backfill.test.ts` (updated assertions).

---

## ADR-phase-r: LINE_MANAGER Scoped Project Creation (Phase R)

**Status:** Accepted

**Context:** `POST /api/projects` blocked all non-MANAGER roles with a blanket `role !== "MANAGER" → 403`. `TeamDetailClient` showed the "New Project" button for `role !== "MEMBER"` callers, so LINE_MANAGERs saw the button but received a silent 403 when they clicked it. The page-level route guard (`teams/[id]/page.tsx`) already redirects a LINE_MANAGER away from any team detail page that is not their own team, making the silent failure visible only on their own team's page — the one case where the action should actually succeed.

**Decision:** Allow LINE_MANAGERs to create projects scoped to the team recorded on their `Membership` row. The API uses a two-step check in `POST /api/projects`:

1. Early MEMBER block: `ctx.role === "MEMBER" → 403`. Fast path, unchanged semantics for MEMBERs.
2. After body parsing, before any DB call: `ctx.role === "LINE_MANAGER" && ctx.teamId !== teamId → 403`. `ctx.teamId` is set by `withAuthScoped()` from the `Membership` DB row — it is not read from the JWT and cannot be forged (see ADR-024).

MANAGERs retain unrestricted creation across all teams in their org. The existing `db.team.findFirst({ where: { id: teamId, organisationId: ctx.organisationId } })` call provides the cross-org tenancy boundary independently of the role check (proven by forge-5).

The `ProjectsTab` UI button condition is tightened to `role === "MANAGER" || (role === "LINE_MANAGER" && callerTeamId === teamId)` via a new `callerTeamId: string | null` prop (sourced from `ctx.teamId` in the server component). This removes any implicit reliance on the page-level redirect for UI correctness — the button is now only rendered where the API will actually accept the request.

**Proof:** Five forge tests in `src/tests/pr-projects-create-rbac.test.ts`:
- forge-1: LM own team → 201 (fails if blanket `role !== "MANAGER"` guard is restored)
- forge-2: LM other team → 403, `db.team.findFirst` not called (fails if scoped check is removed)
- forge-3: MANAGER any team → 201 (pre-existing behaviour verified)
- forge-4: MEMBER → 403 (pre-existing behaviour verified)
- forge-5: LM own `teamId` but team absent from their org → 422 (org tenancy intact)

Pre-fix failures confirmed: forge-1 and forge-5 failed for the stated reasons before the guard was applied.

**Consequences:** LINE_MANAGERs gain project creation on their own team. No other route's RBAC is modified. `withAuthScoped` is unchanged. Pre-existing `multi-tenant-fuzz.test.ts` fuzz-14 corrected: it was asserting that LM creating on `team-1` (their own team) returns 403 — this was accidentally correct under the old blanket guard, not a true cross-team escalation test. Updated to send `teamId: "team-2"` (a team the LM does not manage), which now tests the real boundary.

**Evidence:** `src/app/api/projects/route.ts`; `src/tests/pr-projects-create-rbac.test.ts`; `src/app/teams/[id]/_components/TeamDetailClient.tsx` (`callerTeamId` prop, `canCreateProject` condition); `src/app/teams/[id]/page.tsx` (`callerTeamId={ctx.teamId}`).

---

### ADR-tour-cookie: Cookie-based tour step persistence (not localStorage, not DB column per step)

**Decision:** Store the current tour step ID in a first-party `pulse-tour-step` cookie (SameSite=Lax, 24-hour max-age, non-httpOnly).

**Rationale:**
- **Not localStorage:** localStorage is per-origin but not per-user. A shared browser profile would have one user's tour state leak into another's session. Cookies are sent with the request and can be scoped more reliably to a login session.
- **Not a DB column per step:** A DB write on every step transition adds latency and up to 20+ writes for a full tour. `User.hasOnboarded` (written once on complete or skip) already covers the durable "has this user finished the tour" state. Transient step progress doesn't need DB durability — if the cookie is lost, the tour restarts from step 0, which is an acceptable degradation.
- **Cookie:** Survives hard reloads and SSR-to-client hydration without an API round-trip. Readable from `document.cookie` on the client. Not accessible to the server (non-httpOnly) — the server never needs to read step progress. The 24-hour expiry is a reasonable boundary; if a user doesn't finish the tour within a day, restarting from step 0 is fine.

---

### ADR-tour-routePrefix: Dynamic route matching via `routePrefix` on `TourStep`

**Decision:** Add `routePrefix?: string` to `TourStep`. Route checks use `matchesRoute(step, path)`: exact match on `step.route` OR `path.startsWith(step.routePrefix)` when prefix is set. The NAVIGATE ADVANCE effect additionally uses trailing-slash prefix logic (`to.endsWith("/") && to.length > 1`).

**Context:** The tour engine used exact `pathname === step.route` comparisons. Steps on dynamic routes (`/teams/[id]`, `/projects/[id]`) cannot be represented as exact strings at step-definition time. Options considered: (a) regex `routePattern`; (b) wildcard sentinel; (c) rely on live-DOM polling across navigation (works for `click`-advance steps but fails for `waiting` → `ARRIVED_ON_ROUTE` transitions); (d) `routePrefix` startsWith.

**Rationale:** `routePrefix` is the simplest, most legible option. It covers all Phase 3 cases. All existing steps use exact routes (none end with `/`), so the new code path is unreachable for existing steps — the change is backwards-compatible. `matchesRoute` is a pure helper with no side effects, tested indirectly via tour-steps.test.ts.

**Consequences:** Steps on dynamic segments set `routePrefix` and a fallback `route` (the static prefix, used for the `isOnRoute` check at `advance()` time when the user is still on the prior page). The `NAVIGATE ADVANCE` effect uses an analogous rule: `to.endsWith("/") → startsWith`; otherwise exact match. No state-machine logic changed.

**Evidence:** `src/lib/tour/types.ts` (`routePrefix?: string`); `src/components/tour/TourProvider.tsx` (`matchesRoute`, NAVIGATE ADVANCE effect); `src/lib/tour/steps.ts` (steps 5–14 with routePrefix).

---

### ADR-tour-dual-split: Two distinct tours (first-run vs feature) instead of one unified tour

**Decision (Phase 5, revised Phase 5-fix):** Replace the single 15-step tour with two logically separate tours — a **first-run tour** (activated when `hasOnboarded === false`) and a **feature tour** (activated by writing `pulse-tour-kind=feature` cookie in `RetakeTourButton`). A `TourStep.availableIn` field (`"first-run"` | `"feature"` | absent = both) gates which steps appear in which mode. `filterSteps` now takes a 4th argument `tourMode` and applies the `availableIn` gate in addition to the existing `roles` gate.

**Adaptive creation path (Phase 5-fix):** Creation steps (`dashboard-cta` → `project-open`) carry **no `availableIn`** — they appear in both tours, gated only by `skipIf` predicates (`skipIf: ctx => ctx.hasTeam` or `skipIf: ctx => ctx.hasProject`). This makes the feature tour self-adapting: a user retaking the tour with no existing data sees the creation flow first; a user who already has data has those steps removed by `skipIf`. `feature-nav-project` (navigate into an existing project) has the inverse guard (`skipIf: ctx => !ctx.hasProject`) so it only appears when a project already exists — the two navigation paths are mutually exclusive.

**Context:** The original Phase 5 design made creation steps `availableIn: "first-run"` only, which caused the feature tour to dead-end for users with no data: `feature-nav-project` assumed a project existed, leaving a no-data user stuck with no spotlight target. The fix replaces the per-step `availableIn` guard with runtime `skipIf` predicates, making both tours data-aware.

**Options considered:**
- (a) `skipIf(ctx)` predicates on creation steps — works but makes the single step list hard to reason about; the set of visible steps varies unpredictably based on current user state.
- (b) Two separate `TOUR_STEPS` arrays — clean separation but duplicates shared steps and creates a sync risk.
- (c) `availableIn` field on each step, combined with a `tourMode` runtime parameter — one canonical list, explicit per-step membership, no duplication.

**Rationale:** `availableIn` (option c) for tour-exclusive steps (`welcome`, `feature-welcome`, `feature-nav-project`); `skipIf` (option a) for creation steps that depend on runtime data state. The two mechanisms compose cleanly: `availableIn` is a static membership gate, `skipIf` is a dynamic data gate. Shared steps (feature exploration: `nav-prompts` → `done`) carry neither field and always appear in both tours.

**Consequences:**
- `filterSteps` signature changed from `(steps, role)` to `(steps, role, tourMode, ctx)`.
- `TourStep` gained `availableIn?: "first-run" | "feature"` and `skipIf?: (ctx: TourFilterCtx) => boolean`.
- `TourAdvanceMode` gained `"element-appears"` to support the `project-create-modal` step (spotlights the modal card, then polls for `[data-tour='project-token-copy']` to appear before advancing — avoids advancing before the token is rendered after form submission).
- Step count: 21 total — 1 first-run-only (`welcome`), 2 feature-only (`feature-welcome`, `feature-nav-project`), 8 adaptive/creation (`dashboard-cta` → `project-open`, skipIf-gated), 10 shared (`nav-prompts` → `done`).
- `RetakeTourButton` writes `pulse-tour-kind=feature` before `router.push("/dashboard")`.
- Feature tour with data: 12 steps (creation steps skipped by skipIf). Feature tour without data (LINE_MANAGER): 16 steps (creation steps included, feature-nav-project skipped). First-run with data: 11 steps (MANAGER). First-run without data: up to 19 steps (MANAGER).

**Evidence:** `src/lib/tour/types.ts` (`availableIn`, `skipIf`, `element-appears`); `src/lib/tour/filter.ts` (4-arg `filterSteps`); `src/lib/tour/cookie.ts` (`readTourKindCookie`, `writeTourKindCookie`, `clearTourKindCookie`); `src/lib/tour/steps.ts` (21-step inventory); `src/components/tour/TourProvider.tsx` (tourMode read, `element-appears` polling, cookie clear on exit); `src/app/profile/_components/RetakeTourButton.tsx` (writes `pulse-tour-kind=feature`).

---

### ADR-tour-stale-rsc: Read tour cookie before `hasOnboarded` prop in TourProvider mount guard

**Decision (Phase 5-fix):** In `TourProvider`'s mount `useEffect`, call `readTourCookie()` before checking the `hasOnboarded` prop. The guard is `if ((hasOnboarded && !savedId) || steps.length === 0) return` — the tour is skipped only when `hasOnboarded` is true **and** no step cookie is present.

**Context:** AppShell is a Server Component embedded in each individual page.tsx — it remounts on every Next.js navigation. The `hasOnboarded` value is the RSC prop fresh from the DB on full navigations, but Next.js's router cache can replay a stale RSC payload (with `hasOnboarded=true` from a prior response) when the user navigates during a retake tour. The cookie (`pulse-tour-step`) is always client-side-fresh; if it is present, a tour is actively in progress regardless of what the server prop says.

**Rationale:** The cookie is the source of truth for "tour is actively in progress". The server prop is the source of truth for "has the user ever completed the tour". Trusting the cookie over a potentially stale server prop prevents the tour from silently dropping mid-session on intermediate-page navigations.

**Consequences:** A user who has `hasOnboarded=true` but also has a live `pulse-tour-step` cookie (e.g., browser reloaded mid-retake-tour) resumes the tour instead of silently stopping. Without the cookie, `hasOnboarded=true` still prevents the tour from auto-starting (correct first-time-load behaviour).

**Evidence:** `src/components/tour/TourProvider.tsx` (mount `useEffect`, `readTourCookie()` call before hasOnboarded guard).

---

## ADR-debt-phase-d: Technical Debt AI Synthesis Design

**Status:** Accepted (Phase D shipped 2026-06-26)

**Context:** Phase B built the SonarQube scanning pipeline and stored raw metrics (`issueCount`, ratings, `techDebtMinutes`). Phase D adds the final SYNTHESISING step: AI synthesis of findings, a deterministic debt score, and a UI that renders findings per priority.

**Key decisions:**

### Synthesis failure → ERROR (not COMPLETE-without-findings)
A `COMPLETE` scan with no findings means "clean repo — the AI found nothing significant." A synthesis failure (ceiling exceeded or JSON parse error) is a different condition — it means the AI analysis did not run. Marking failure as ERROR preserves the semantic distinction and prevents a failed scan from appearing as a passing one. Raw Sonar data written at the start of the SYNTHESISING step is preserved in the DB regardless of whether synthesis succeeds or fails.

### `debtScore` computed in code, not AI-emitted
`computeDebtScore(findings)` in `src/lib/debt/compute-score.ts` applies a deterministic formula: `100 − (P1×20 + P2×10 + P3×4 + P4×1)`, floored at 0. The AI never emits the score. This prevents the model from inflating or deflating the score, and makes the number fully reproducible from the findings list alone.

### Evidence-grounding is mandatory (anti-hallucination guard)
Every AI finding passes two guards before storage: (1) `evidence.files` must be non-empty and at least one listed file must exist in the `realFiles` Set constructed from actual Sonar issue files and SecurityFinding files; (2) `priority` must be exactly one of the strings `P1`, `P2`, `P3`, or `P4`. Findings that fail either condition are dropped silently. This is a defence-in-depth measure — the prompt also instructs the model to only reference files from the provided lists.

### No GRAPH source in Phase D
`FindingSource` type supports `"SONAR"` and `"SECURITY_SCAN"` only. Graphify code-graph integration as a third evidence source is deferred to a future phase.

### Empty evidence fast-path — AI never called for clean repos
When both `sonarIssues` and `securityFindings` are empty (nothing to synthesise), `synthesiseDebtFindings` returns `{ findings: [], score: 100 }` immediately without calling the AI. This avoids unnecessary ceiling consumption and correctly represents a project with no detected issues.

**Evidence:** `src/lib/debt/types.ts` (Priority, FindingSource, Evidence, TechDebtFinding, SynthesisResult); `src/lib/debt/compute-score.ts` (computeDebtScore); `src/lib/debt/synthesise.ts` (synthesiseDebtFindings, realFiles guard, priority guard, empty fast-path); `src/lib/debt/orchestrate.ts` (SYNTHESISING step, SecurityScanRun query, failure→ERROR path); `src/app/debt-analyzer/[id]/_components/DebtScanClient.tsx` (debtScore MetricCell, FindingCard list).

---

## ADR-feed-summary-validator: Output validation in generateFeedSummary() — prompt-echo guard

**Status:** Accepted
**Date:** 2026-06-29

**Context:** The feed summary one-liner (5–8 word action phrase stored in `ActivityEvent.feedSummary` and shown in the dashboard "Active Now" feed) was occasionally showing raw system-prompt text such as "We need to produce a 5-8 word action phrase describing what a developer accomplished. Must start with past-tense action verb…" This happened because free-tier OpenRouter models sometimes echo or paraphrase the system prompt instead of completing it. The raw echoed text was passed verbatim to `ActivityEvent.feedSummary` with no validation.

**Decision:** Add a `validateFeedSummary(text)` function in `src/lib/gemini.ts` that rejects model outputs matching known prompt-echo patterns before storing them. The validator is the hard guarantee; prompt engineering (added explicit "Respond with ONLY" instruction) is a soft hint. The ingest route's existing `firstSentence(excerpt)` fallback is preserved when the validator rejects the output.

**Validator rejection criteria:**
- Contains any of: `"action phrase"`, `"past-tense"`, `"passive voice"`, `"trailing punctuation"`, `"5-8 word"`, `"subsystem"` (case-insensitive)
- Starts with: `"we need to"`, `"write a"`, `"here is"`, `"here's"`, `"sure,"`, `"certainly"`, `"of course"`, `"note:"` (case-insensitive)
- Contains newlines or JSON braces
- Exceeds 12 words or 90 characters

**Accepted output** is clamped: trimmed, trailing punctuation stripped.

**Consequences:** A small number of valid outputs that happen to contain the rejected keywords will be falsely rejected (e.g. a summary mentioning "subsystem"). In practice these are rare. The fallback to `firstSentence(excerpt)` always produces a usable value. The validator is unit-tested in `src/tests/feed-summary.test.ts`.

**Evidence:** `src/lib/gemini.ts` (`validateFeedSummary`, `generateFeedSummary`); `src/tests/feed-summary.test.ts` (unit tests for prompt-echo → null, valid phrase → pass, over-length → null).

---

## ADR-drift-inconclusive: Context Drift Analyser — inconclusive verdict and repoSnapshot full-audit

**Status:** Accepted
**Date:** 2026-06-29

**Context:** The Context Drift Analyser previously returned a false-positive "no drift detected" (GREEN) verdict when the diff between baseline and head contained no documentation files and no comparable source files. This happened because `analyseAiDrift()` is diff-scoped: it only shows docs that `filterRelevantDocPaths()` links to changed files. When docs from a different project were placed in the docs folder and no corresponding code diff was present, the model had nothing to compare, `parseDriftFindings` returned `[]`, and the UI showed "No drift detected — All context docs match the current code."

**Decision (minimum fix — Bug 2a):** When `docs.length === 0 && allCode.length === 0` (no relevant docs and no comparable code after full assembly), `analyseAiDrift` returns `{ ok: false, error: "inconclusive" }` instead of calling the AI with empty inputs. `orchestrate.ts` intercepts this specific error and stores the assessment as `status: COMPLETE, riskLevel: "GREEN", error: "inconclusive"` so it is distinguishable from a real clean result. The UI (`DriftDetailClient`) renders an amber "Inconclusive — no comparable changes in this diff" panel instead of the green "No drift detected" panel.

**Decision (preferred fix — Bug 2b — full-audit path):** Before returning inconclusive, `analyseAiDrift` runs `auditDocsAgainstRepoSnapshot()`, a diff-independent structural check. This function compares all fetched doc content against `project.repoSnapshot.detectedFrameworks`. When docs describe a framework that does NOT appear in the repo snapshot (e.g. docs mention Django but the repo only detects Next.js), a HIGH-severity `ACCURACY` finding is returned via `ok: true`. This catches the "wrong project's docs" scenario even when there is no code diff. The finding bypasses the AI entirely (no token cost, `modelId: "snapshot-audit"`).

**Contract change:** `AnalyseAiFailure.error` now includes `"inconclusive"` as a new union member. `orchestrate.ts` handles it specially (COMPLETE + `error` field) rather than as an ERROR status.

**Consequences:**
- False-positive "Context is perfect" verdict eliminated for diff-less assessments.
- The UI now shows three states for COMPLETE assessments: (1) real findings present → FindingsList, (2) zero findings + no `error` field → "No drift detected" (genuine clean), (3) zero findings + `error: "inconclusive"` → "Inconclusive" panel.
- `auditDocsAgainstRepoSnapshot` returns findings only when `repoSnapshot.detectedFrameworks` is non-empty; it is a no-op when the project has no linked repo or no snapshot. This prevents false positives on unlinked projects.
- All GitHub calls in the audit path still go through `authedGithubFetch()`. The AI cost ceiling is still checked before any AI call. The snapshot audit itself makes no AI calls and has zero token cost.

**Evidence:** `src/lib/drift/analyse-ai.ts` (`auditDocsAgainstRepoSnapshot`, inconclusive guard in `analyseAiDrift`); `src/lib/drift/orchestrate.ts` (inconclusive handling); `src/app/context-analyser/[id]/_components/DriftDetailClient.tsx` (`InconclusiveState` component, `assessment.error` check); `src/tests/drift-inconclusive.test.ts` (13 tests covering all scenarios).

---

## ADR-029: Anthropic Haiku as Primary Org-Level AI Provider

**Status:** Accepted (supersedes ADR-001 primary-provider designation for org-configured deployments)
**Date:** 2026-06-30

**Context:** ADR-001 established Groq (`llama-3.3-70b-versatile`) as the operative AI provider, replacing the original Anthropic design, citing free-tier availability and low latency. In practice, free-tier models served via Groq and OpenRouter produce unreliable structured output: observed failure modes include JSON hallucination (model emits free-prose instead of the required JSON schema), prompt-echo (feed summary returning raw system-prompt text — addressed by ADR-feed-summary-validator), and inconsistent schema adherence under load. These failure modes degrade narration quality and require defensive validation layers that add complexity without fixing the root cause.

**Decision:** Add Anthropic Claude Haiku as the primary AI provider at the org level. A MANAGER can set an Anthropic API key for the organisation via a MANAGER-only API route. When an org key is set, all narration and feed-summary calls route to Haiku. When no org key is set, the system falls back to the existing OpenRouter/Groq path with a server-side warning logged. `getAutoCallModel(anthropicApiKey?)` in `src/lib/ai-provider.ts` owns all routing logic.

**Rationale:**
- Haiku is fast (comparable to Groq Llama latency in practice) and cheap at $0.80/$4.00 per 1M input/output tokens — comparable to or cheaper than OpenRouter free-tier at production volumes.
- Haiku reliably follows structured prompts and JSON output schemas, eliminating the prompt-echo and hallucination failure modes that required the `validateFeedSummary` defensive guard.
- One API key per org set by MANAGER provides a clean operational model: no developer-level credential management, and the key is scoped to the org boundary already established by ADR-009.
- The fallback chain to OpenRouter/Groq is preserved for orgs that have not yet configured a key, maintaining zero-friction onboarding for the demo and evaluation deployments.

**Implementation:**
- `anthropicApiKeyEnc String?` and `anthropicKeyHint String?` fields added to the `Organisation` model.
- The API key is encrypted at rest using AES-256-GCM with `ANTHROPIC_KEY_ENCRYPTION_SECRET` (a 32-byte / 64 hex-char server secret set by the operator). `anthropicKeyHint` stores the last 4 characters of the raw key for display only (same preview pattern as AgentToken per ADR-003).
- `@ai-sdk/anthropic` added as a production dependency.
- A MANAGER-only API route (`PUT /api/admin/org/anthropic-key`) accepts and encrypts the key; a corresponding `DELETE` route clears it.
- `getAutoCallModel(anthropicApiKey?)` returns `{ model, provider }`: when `anthropicApiKey` is present, returns `anthropic("claude-haiku-4-5")`; otherwise returns the existing Groq/OpenRouter model.

**Consequences:**
- ADR-001's fallback chain (OpenRouter → Groq) is preserved and remains the operative path for orgs without a configured key. ADR-001 is not reversed; Haiku is an additive primary path, not a replacement of the fallback.
- The `@ai-sdk/anthropic` package is added to `package.json`.
- `ANTHROPIC_KEY_ENCRYPTION_SECRET` is added to `.env.example` as a required operator secret when the Haiku path is used.
- The cost-ceiling pricing constants in `src/lib/cost-ceiling.ts` (currently approximating Sonnet 4.6 pricing) should be updated in a follow-on to reflect Haiku pricing for orgs using the Haiku path. This is deferred as a known trade-off consistent with the existing ceiling mismatch documented in ADR-015.
- MANAGER-only key management follows the same RBAC pattern as all other MANAGER-only routes (ADR-004).

**Evidence:** `prisma/schema.prisma` (`Organisation.anthropicApiKeyEnc`, `Organisation.anthropicKeyHint`); `src/lib/ai-provider.ts` (`getAutoCallModel`); `src/app/api/admin/org/anthropic-key/route.ts`; `package.json` (`@ai-sdk/anthropic`); `.env.example` (`ANTHROPIC_KEY_ENCRYPTION_SECRET`).
