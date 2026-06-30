# Risk

> **Scope**: Every finding in this document is grounded in a specific source file.  
> No invented risks, no generic advice.  
> **Last updated**: 2026-06-26  
> **Covers**: P1–P19 + Phase 10 Security Scan + Phase 5 Onboarding Tour + Technical Debt Analyzer Phase B + Technical Debt Analyzer Phase D (phases completed as of this writing)

---

## Table of Contents

1. [Security Risks](#1-security-risks)  
   1.1 [Authentication & Token Security](#11-authentication--token-security)  
   1.2 [API Security & Rate Limiting](#12-api-security--rate-limiting)  
   1.3 [PII & Data Handling](#13-pii--data-handling)  
   1.4 [HTTP Headers & CSP](#14-http-headers--csp)  
   1.5 [Multi-tenancy Isolation](#15-multi-tenancy-isolation)  
   1.6 [GitHub Integration](#16-github-integration)  
2. [Performance Risks](#2-performance-risks)  
3. [Scalability Risks](#3-scalability-risks)  
4. [Technical Debt](#4-technical-debt)  
5. [Compliance & Privacy Risks](#5-compliance--privacy-risks)  
6. [Recommended Mitigations](#6-recommended-mitigations)

---

## 1 Security Risks

### 1.1 Authentication & Token Security

#### Session cookie configuration

**Source**: `src/app/api/auth/login/route.ts`

Sessions are issued as 30-day JWTs (`SESSION_MAX_AGE = 30 * 24 * 60 * 60`). The cookie is set `HttpOnly; SameSite=Lax`. On HTTPS the `__Secure-` prefix is applied, adding the `Secure` flag. No MFA is implemented; this is explicitly scoped out in the archdoc §10 ("No MFA in v1 — documented as v1 scope-out").

**Risk**: 30-day session lifetime means a stolen cookie has a long window of opportunity. SameSite=Lax does not protect against cross-site POST from the same registrable domain (e.g. a subdomain).

#### Session version invalidation cache in-memory

**Source**: `src/lib/withAuthScoped.ts`

`_sessionVersionCache` is a module-level `Map<string, { version: number; cachedAt: number }>` with a 30-second TTL. This cache lives entirely in the Node.js process heap. On any process restart (deploy, crash, scale event) all cached session versions are lost, forcing a DB lookup on the next request. In a multi-process deployment each process maintains its own independent cache — a role change applied in one process will not be visible in another for up to 30 seconds.

**Risk**: Role changes may take up to 30 seconds to propagate in single-process deployments; potentially longer in multi-process. An attacker who has compromised a session cookie retains the old role for the TTL window after the role is changed.

#### bcrypt cost and missing pepper

**Source**: `src/lib/token.ts`

Agent tokens use bcrypt at cost 12 with a server-side pepper (`AGENT_TOKEN_PEPPER`). The fallback is `const pepper = process.env.AGENT_TOKEN_PEPPER ?? ""`, silently removing the pepper if the env var is absent. This is not checked at startup.

**Risk**: A missing pepper reduces token hashing to plain bcrypt(raw, 12) with no server-side secret component. If the database is breached, tokens lacking a pepper are more susceptible to offline brute-force. There is no startup assertion that fails if the pepper is absent.

#### Legacy agent token fallback

**Source**: `src/lib/resolveAgentToken.ts`

`resolveAgentToken()` first checks the new per-developer `AgentToken` table; on miss it falls back to `Project.agentTokenHash` (the old single-token-per-project model). The code comment reads: *"This fallback is intentional migration tech-debt and should be retired once all projects have ≥1 AgentToken row."* Until retired, projects that have not yet been migrated accept tokens via the legacy path, which does not return a `userId` and cannot attribute events to a specific developer.

**Risk**: Legacy tokens bypass per-developer attribution. An organisation that has not yet migrated all projects has a mixed security model where some ingest events are unattributed.

#### No rate limit on signup

**Source**: `src/app/api/auth/signup/route.ts`

The login endpoint is rate-limited (5/min + 20/hr per IP via `src/lib/ratelimit-login.ts`). The signup endpoint performs a password hash, a DB lookup, and multiple DB writes, but has **no rate limiting**.

**Risk**: An attacker can enumerate valid email addresses by POST-ing to `/api/auth/signup` at arbitrary volume. The bcrypt operation at cost 12 also makes this a CPU-amplification vector.

#### HMAC request signing on ingest routes

**Source**: `src/app/api/ingest/event/route.ts`, `src/app/api/ingest/time/route.ts`

All ingest routes perform HMAC-SHA256 signature verification using `crypto.timingSafeEqual` to prevent timing attacks. The signing key is the **raw agent token itself** (`rawToken` extracted from the Bearer header), not a separate env var. The HMAC is computed as `HMAC_SHA256(rawBody, rawToken)` and compared against the `x-pulse-signature` header. If the Bearer token is absent, the route returns 401 before the HMAC check is even reached.

**Risk**: The HMAC provides body integrity (prevents body tampering if a token leaks via logs) but not a separate server-side secret. There is no additional `INGEST_HMAC_SECRET` env var — the security relies entirely on the agent token remaining secret. Token rotation invalidates the signing key immediately.

#### Account lockout implementation

**Source**: `src/app/api/auth/login/route.ts`

Lockout triggers after 5 failed attempts within 10 minutes (`LOCKOUT_THRESHOLD = 5`, `LOCKOUT_DURATION_MS = 10 * 60 * 1000`). The lockout state is stored in `User.lockedUntil` in Postgres — it survives restarts. The error response for a locked account is deliberately identical to an invalid-credentials response to avoid leaking lockout state.

**Risk**: Low — design is sound. The lockout itself can be used as a DoS vector against legitimate users if an attacker knows their email. No CAPTCHA or progressive delay mitigates automated lockout attacks.

---

### 1.2 API Security & Rate Limiting

#### Fail-open rate limiters (Upstash unavailable)

**Sources**: `src/lib/ratelimit.ts`, `src/lib/ratelimit-time.ts`, `src/lib/ratelimit-login.ts`, `src/lib/ratelimit-github.ts`, `src/lib/ratelimit-teams-patch.ts`, `src/lib/ratelimit-productive-rules.ts`, `src/lib/ratelimit-users-time.ts`

Every Upstash-backed rate limiter follows the same pattern: if `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` are absent, or if the Redis call throws, the function returns `{ allowed: true }`. This is explicitly acknowledged in `notes/pending-work.txt`: *"Redis not provisioned in production — rate limits are currently fail-open."*

**Risk**: In the current production deployment rate limiting is entirely disabled for all ingest, summary, export, repo-context, and GitHub endpoints. Any client can send unlimited requests. This is a known blocker, not an unknown issue, but it remains unresolved.

#### Public metrics endpoint

**Source**: `src/app/api/metrics/route.ts`, `src/middleware.ts`

`GET /api/metrics` is listed in `PUBLIC_PREFIXES` in the middleware and performs no authentication. The response exposes per-project Claude token counters, per-route request counts, error counts, and latency histograms (p50/p75/p95/p99) in Prometheus text format.

**Risk**: Project token consumption and API latency data is visible to any unauthenticated caller. This leaks billing-sensitive information and reveals internal route structure. An attacker can use the latency data to fingerprint application behaviour.

#### Public productive-rules read endpoint

**Source**: `src/middleware.ts` (`PUBLIC_PREFIXES` includes `/api/productive-rules`)

`GET /api/productive-rules` is listed as public, bypassing the session check for read operations.

**Risk**: Productive rules (which describe what constitutes productive vs unproductive behaviour per team) are readable without authentication. For most deployments this is low-sensitivity data, but it may leak team names and workflow expectations to unauthenticated callers.

#### In-memory fallback rate limiters (process-scoped)

**Sources**: `src/lib/status-ratelimit.ts`, `src/lib/summary-ratelimit.ts`, `src/lib/repo-context-ratelimit.ts`, `src/lib/ratelimit-login.ts`

Several rate limiters (status: 30/min/user, summary: 10/hr/project, export: 20/hr/project, repo-context: 6/hr/project, login: 5/min/IP) use pure in-memory sliding-window stores. These stores are module-level `Map` objects that are reset on every process restart.

**Risk**: A process restart clears all rate limit counters. An attacker who can trigger a restart (e.g. via OOM or crash loop) can reset rate limits. In multi-worker deployments each worker maintains its own counter, so effective limits are multiplied by worker count.

#### CSRF protection scope

**Source**: `src/middleware.ts`

CSRF token validation bypasses `/api/status`, which is in `CSRF_BYPASS_PREFIXES`. All state-mutating routes (login, signup, ingest) that are not in the bypass list require a CSRF token.

**Risk**: `/api/status` accepts POST requests without CSRF protection. The endpoint writes `MemberStatus` records. While it requires a valid agent/user token, the missing CSRF check means a cross-site request could update status if the cookie is available.

---

### 1.3 PII & Data Handling

#### PII redaction pipeline

**Sources**: `src/lib/redact.ts`, `lib/redact.mjs`

Two copies of the redaction pipeline exist: `src/lib/redact.ts` (TypeScript, server-side) and `lib/redact.mjs` (ESM, used by scripts). The pipeline applies exactly 7 rules in order: (1) env-style assignments `KEY=VALUE`, (2) JWTs `eyJ...`, (3) Anthropic API keys `sk-ant-…`, (4) OpenAI-style keys `sk-[20+ alphanum]`, (5) AWS access keys `AKIA`/`ASIA` prefix, (6) PEM private key blocks, (7) URL-embedded credentials `scheme://user:pass@host`. The test suite (`src/tests/redact-parity.test.ts`) verifies both copies produce identical output for all corpus entries.

**Risk**: Two copies means any fix must be applied in two places. A future rule added to only one copy will create a divergence not caught until a parity test fails. Email addresses, credit card PANs, and IPv4 addresses are **not** redacted by the current pipeline — these would appear in stored `sessionExcerpt` if present.

#### Logger PII redaction paths

**Source**: `src/lib/logger.ts` (pino `redact` config, verified by `src/tests/logger-pii.test.ts`)

The pino logger has explicit `redact` paths covering: `password`, `passwordHash`, `agentToken`, `agentTokenHash`, `sessionExcerpt`, `manualText`, `tenantKey`, `secret`, `apiKey`, `jwt`, `bearerToken`, `req.headers.authorization`, `req.headers['x-pulse-signature']`, `req.headers['x-internal-token']`, `headers.authorization`, `headers['x-pulse-signature']`, `headers['x-internal-token']`, `Authorization`, `authorization`. Tests verify that sensitive values never appear in logger output.

**Risk**: Low — the redaction config is explicitly tested. Risk is that new sensitive fields added to log calls are not automatically redacted unless the path is added to the list. There is no runtime assertion that catches un-redacted sensitive field names.

#### App names collected with consent v2

**Sources**: `src/lib/pulse-body-shape.ts`, `src/lib/consentCheck.ts`

`topApps` (application names from the developer's workstation) was added to `ALLOWED_TIME_BODY_KEYS` in the ingest body shape. This field is only accepted when the user has provided consent v2. Users with consent v1 must re-acknowledge before `topApps` is stored.

**Risk**: If the consent gate is bypassed (e.g. a bug in `needsConsentModal()`), app names could be stored without explicit v2 consent. App names may qualify as personal data under GDPR (e.g. revealing medical or legal software usage).

#### `idleSeconds` / `offlineSeconds` retained in schema

**Source**: `prisma/schema.prisma` (`MemberDailyTime` model)

The `idleSeconds` and `offlineSeconds` columns exist in the `MemberDailyTime` table but are **no longer written** by any ingest route as of P12. They were retained for schema backwards compatibility.

**Risk**: The columns store zeros for all new rows, but old rows may contain real data. Any analytics query that reads these columns will silently mix real historical data with zeroed new data. Documentation does not flag this transition point.

---

### 1.4 HTTP Headers & CSP

**Source**: `src/middleware.ts` (verified line-by-line)

The middleware generates a per-request nonce via `btoa(crypto.randomUUID())` and applies a Content Security Policy with `strict-dynamic`. Security headers actually set by `applySecurityHeaders()`:

- `Strict-Transport-Security: max-age=63072000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: <nonce-based CSP>` (see CSP section in `docs/architecture.md`)

> **Correction**: `X-DNS-Prefetch-Control` is **not** set by this middleware — previously listed here in error. Verified directly from `src/middleware.ts:29-35`.

**Missing headers** (verified absent from `src/middleware.ts`):
- No `X-Frame-Options` header — the app can be embedded in `<iframe>` by any origin.
- No `Permissions-Policy` header — browser features (camera, microphone, geolocation) are not restricted.

**`style-src 'unsafe-inline'`**:
The CSP includes `style-src 'self' 'unsafe-inline'`. This allows any inline `style` attribute or `<style>` block, which weakens XSS protections for style-based attacks (e.g. CSS exfiltration via attribute selectors).

**Risk**: Absence of `X-Frame-Options` enables clickjacking attacks. Absence of `Permissions-Policy` is a defence-in-depth gap. `unsafe-inline` in `style-src` is a known CSP weakening; it cannot be tightened without auditing all inline style usage in the Next.js components.

---

### 1.5 Multi-tenancy Isolation

**Sources**: `src/lib/withAuthScoped.ts`, `src/tests/multi-tenant-fuzz.test.ts`, `src/tests/pm3-forge-*.test.ts`, `prisma/schema.prisma`

**PM3 update — JWT-trust gap closed.** Before PM3, `withAuthScoped` populated `ctx.organisationId` directly from the JWT's `organisationId` claim. A leaked `NEXTAUTH_SECRET` (or, in the multi-org future, a deliberate claim swap) could have driven cross-org access. PM3 moves the boundary into a per-request `db.membership.findUnique({ where: { userId_organisationId: { userId, organisationId } } })`. The `userId` is sourced from the verified `token.sub` (signature-checked by NextAuth); the `organisationId` is the (untrusted) JWT claim. A tampered claim → no row → null ctx → 401. Four forge tests (`pm3-forge-*.test.ts`) prove the boundary against cross-org access, header forging, JWT-claim tampering, and mid-session revocation — each empirically demonstrated to fail when the corresponding guard is removed (see ADR-024 for the verification table).

Prisma queries still include `organisationId` in their `where` clauses (the data-layer half of the boundary). The multi-tenant fuzz test suite (29 test cases) verifies:
- Unauthenticated requests return 401 (fuzz-01 through fuzz-07)
- Cross-team URL-id guessing returns 403, not 404 (fuzz-08 through fuzz-12)
- Role escalation attempts return 403 (fuzz-13 through fuzz-21)
- Cross-org project ID guessing returns 404 on scoped endpoints (fuzz-22 through fuzz-25)
- **PM3 two-membership fixture**: user member of orgs A+B, active=B, requesting an A resource → 404 (fuzz-pm3-01, fuzz-pm3-02)

**Reserved `tenantKey` columns**: The Prisma schema includes `tenantKey` columns on several models, reserved for a future multi-tenant migration (currently always `null`).

**Residual risks (post-PM3)**:
- The data-layer `organisationId` filter is still enforced by convention. A developer who forgets to scope a new query will not be caught at compile time — only by a fuzz test if one is written for that route. The fuzz test suite does not cover every route.
- Ingest paths (`/api/ingest/event`, `/api/ingest/time`) do not use `withAuthScoped` — they bind to an org at AgentToken issuance time. This is intentional and out of PM3 scope, but the org-binding security of those paths sits in `src/lib/token.ts` / `src/lib/hmac.ts`, not in the Membership boundary.
- **PM6 resolved**: `User.organisationId/role/teamId/isLineManager` columns have been dropped (migration `20260622000001_drop_user_legacy_cols`). Any future code that tries to read or write these fields will produce a compile error, not a silent runtime divergence.

**PM5 — PENDING Membership access gate.** PENDING memberships must not grant authenticated access. This is enforced by `withAuthScoped` checking `membership.status !== "ACTIVE"` → return null → 401, immediately after the Membership row is found. Three PM5 forge tests (`pm5-forge-pending-no-access.test.ts`, `pm5-forge-pending-no-switch.test.ts`, `pm5-invite-creates-pending-membership.test.ts`) empirically prove the gate. The **residual risk** is that any future route that queries `Membership` directly (bypassing `withAuthScoped`) would also need to filter `status: "ACTIVE"` — this is enforced by convention, not by the type system. The PM5 status gate is a single-point chokepoint in `withAuthScoped`; all 158+ `ctx.role === "..."` sites downstream are automatically covered without per-route changes.

#### Admin cleanup endpoint authorisation

**Source**: `src/app/api/admin/cleanup/route.ts`

The cleanup endpoint (`POST /api/admin/cleanup`) uses a simple `ADMIN_SECRET` header check (`function authorized(req: NextRequest): boolean`). It does not use the session-based RBAC system. This means it bypasses `organisationId` scoping entirely — it operates on the entire database.

**Risk**: The `ADMIN_SECRET` is a single shared secret. If leaked it grants full cleanup capability across all organisations. It is not scoped per-organisation.

---

### 1.6 GitHub Integration

**Source**: `src/lib/repo-context/client.ts`

`getInstallationToken()` caches GitHub installation access tokens in a module-level `_tokenCache` Map with a 50-minute TTL. This cache is in-memory only — it is lost on process restart.

**Risk**: After a restart, the first repo-context request for each installation will incur a GitHub API call to fetch a new token. This is functionally correct but means the cache provides no benefit immediately after restart. In multi-worker deployments each worker maintains its own token cache, multiplying GitHub API calls by worker count.

#### GitHub App private key in environment

**Source**: `src/lib/repo-context/client.ts` (`getPrivateKeyPem()`)

The GitHub App RSA private key is stored in `GITHUB_APP_PRIVATE_KEY` environment variable (PEM format). `createAppJWT()` uses this key to sign JWTs for GitHub App authentication.

**Risk**: If the private key is leaked (e.g. via an environment variable exposure), an attacker can impersonate the GitHub App for all installations. The key has no rotation mechanism in the application code. Key rotation requires updating the env var and redeploying.

#### Central scan: temp directory residue on process crash

**Source**: `src/app/api/projects/[id]/code-health/scan/route.ts`, `src/lib/code-health.ts`

During a CENTRAL scan, repo source is written to `/tmp/pulse-scan-{projectId}-{ts}/` (code health) or `/tmp/pulse-sec-scan-{projectId}-{ts}/` (security). The `finally` block in both routes calls `rmSync(tmpDir, { recursive: true, force: true })` to hard-delete it. If the Node.js process crashes (SIGKILL, OOM) between tarball extraction and the `finally` block, the source tree remains on disk until the next process start.

**Mitigation**: The boot-time IIFE in `code-health.ts` removes any `/tmp/pulse-scan-*` or `/tmp/pulse-sec-scan-*` dir older than 30 minutes on module load, so residue is cleaned up on the next restart. The dir contains only source code (no secrets, no credentials). Logs above DEBUG level do not include the temp path.

**Residual risk**: a narrow window between process crash and restart where source code sits on the host's `/tmp`. Acceptable for single-host self-hosted deployment; for shared or cloud host, ensure `/tmp` is ephemeral (e.g. `tmpfs`).

---

## 2 Performance Risks

### 2.1 In-memory metrics store

**Source**: `src/lib/metrics.ts`

The metrics store is a module-level in-memory object (`const store: MetricsStore = {}`). It accumulates per-route request counts, error counts, and latency samples for a 24-hour rolling window. The store is never persisted to disk or external storage.

**Risk**: On process restart all accumulated metrics are lost — the 24-hour window resets to zero. In a multi-worker deployment each worker maintains its own store; the `/api/metrics` endpoint only reflects the state of the single worker that handles the request. Metrics aggregation across workers is not implemented.

### 2.2 In-memory OTEL trace store

**Source**: `src/lib/otel.ts`

OTEL traces are collected in-memory within each request via `startTrace()` / `commitTrace()`. Completed traces are stored in a module-level array. There is no export to an OTEL collector or persistent backend.

**Risk**: Trace data is lost on restart. In production, without an OTEL backend, distributed tracing provides no persistent observability. The in-memory accumulation may grow without bound if `commitTrace()` is not called (e.g. on thrown errors), though each request creates a new `TraceContext`.

### 2.3 AI provider not live-tested in production

**Source**: `notes/pending-work.txt`, `src/lib/narrate.ts`

The narration and summary features use Groq Llama 3.3 70B (`createGroq` + `llama-3.3-70b-versatile`). The pending-work note states: *"ANTHROPIC_API_KEY not set — narration/summary not live-tested in production."* Note: the `.env.example` references `GEMINI_API_KEY` and the archdoc specifies `claude-sonnet-4-6`, but the actual code uses `GROQ_API_KEY`. The env example is stale.

**Risk**: The AI integration is untested end-to-end in the current production environment. Any call to `generateNarration()` or `generateFeedSummary()` that hits the Groq API will fail unless `GROQ_API_KEY` is set. The error handling falls back gracefully (returns `null` / empty string), so failures are silent from the user's perspective.

### 2.4 Narration cooldown is in-memory

**Source**: `src/lib/narrate.ts`

`generateNarration()` uses a module-level `cooldowns` Map to prevent re-generating a narration for the same input hash within a cooldown window. This map is in-memory only.

**Risk**: On process restart all cooldowns are cleared. If a burst of ingest events triggers narration before the cooldown re-establishes, duplicate narrations may be generated for the same content, incurring unnecessary AI API cost.

### 2.5 Synchronous sonar-scanner blocks the Node.js process (Code Health, Phase 9)

**Source**: `src/app/api/projects/[id]/code-health/scan/route.ts`, `src/lib/code-health.ts`

`POST /api/projects/[id]/code-health/scan` calls `runSonarScanner()` which uses `child_process.execSync` with a default 5-minute timeout. During this call the Node.js event loop is blocked — no other requests can be processed by this worker.

**Risk**: In a single-process deployment a scan request freezes all concurrent users for up to 5 minutes. The 1/120s rate limiter reduces frequency but does not eliminate the blocking window.

**Mitigation**: Acceptable for the current single-user self-hosted deployment. A future scale-up would require async execution via a job queue (e.g. BullMQ + Redis).

### 2.6 SonarQube RAM requirement

**Source**: `scripts/sonarqube-start.sh`

SonarQube CB requires approximately 1.8 GB RAM under the JVM caps applied in `sonarqube-start.sh` (web/CE 256 MB, Elasticsearch 512 MB each). The host WSL2 environment has ~6 GB available.

**Risk**: If the host machine has less than 2 GB free, SonarQube will fail to start or the OOM killer may terminate it. No health-check gate exists in the app — `SONAR_HOST_URL` availability is not validated at startup. The POST scan route returns 503 if env vars are missing, but not if SonarQube is running but unresponsive.

### 2.7 Bcrypt at cost 12 on signup

**Source**: `src/app/api/auth/signup/route.ts`

Password hashing uses bcrypt at cost 12. On a typical server this takes ~300–500 ms per hash. With no signup rate limiting (see §1.1), an attacker can issue concurrent signup requests to saturate CPU.

**Risk**: CPU-bound bcrypt exhaustion is possible without signup rate limiting. This is a compounding risk with the missing rate limit documented in §1.1.

### 2.8 Debt scan shares the code-health concurrency semaphore (Phase B)

**Source**: `src/lib/debt/orchestrate.ts`, `src/lib/code-health.ts`

`runDebtScanPipeline` calls `tryAcquireScanSlot()` / `releaseScanSlot()` from `code-health.ts`. `MAX_CONCURRENT_SCANS = 2` is a shared limit between code-health scans and debt scans. A debt scan in progress can block a code-health scan (and vice-versa).

**Risk**: In practice, a debt scan holds the slot for the full SonarQube CE duration (up to 3 min CE timeout + 5 min scanner timeout = ~8 min worst case). During this window a concurrent code-health scan POST would return `scan_capacity_exceeded`. Acceptable for current single-org deployment; would need a separate semaphore if both feature sets scale simultaneously.

### 2.9 Debt scan issues API uses ps=500 hard limit (Phase B)

**Source**: `src/lib/code-health.ts` — `fetchSonarIssues`

The `/api/issues/search` call uses `&ps=500` (SonarQube's maximum page size). For repositories with more than 500 BLOCKER+CRITICAL+MAJOR issues, only the first 500 are fetched; `issueCount`, `criticalCount`, and `highCount` will be under-reported.

**Risk**: Counts silently truncated for very large or very old codebases. Mitigation for Phase D: implement cursor pagination using SonarQube's `&p=` parameter if `paging.total > 500`.

---

## 3 Scalability Risks

### 3.1 All rate limiters fail open without Redis

**Source**: `src/lib/ratelimit.ts` and all sibling files; `notes/pending-work.txt`

As documented in §1.2, all Upstash-backed rate limiters return `{ allowed: true }` when Redis is unreachable. The pending-work note confirms Redis is not provisioned in the current production deployment.

**Risk**: Without Redis, there are no effective per-token or per-user rate limits on ingest, summary, export, or GitHub endpoints. A single misbehaving client can exhaust database connections or incur unbounded AI API costs.

### 3.2 Scale tier multiplier is a single env var

**Source**: `src/lib/ratelimit.ts` (`getScaleTierMultiplier()`)

`SCALE_TIER` is an integer env var (1–4) that multiplies rate limit ceilings by its value (e.g. `SCALE_TIER=4` gives 4× the base limits). This is tested in `src/tests/rate-limits.test.ts` for tiers 1 and 4.

**Risk**: Scaling up rate limits requires a redeploy to change the env var. There is no runtime API to adjust limits per-organisation or per-project. A single large customer cannot be given higher limits without raising limits for all customers.

### 3.3 Cost ceiling is per-organisation, not per-project

**Source**: `src/lib/cost-ceiling.ts`

`isCeilingExceeded()` checks monthly spend against `CLAUDE_MONTHLY_CEILING_USD` at the organisation level. Individual projects within an organisation can consume the entire budget before other projects get a chance.

**Risk**: A high-activity project can exhaust the organisation's monthly AI budget, blocking all other projects from generating narrations and summaries. There is no per-project sub-ceiling.

### 3.4 Instrumentation boot guard

**Source**: `instrumentation.ts`

`register()` throws at startup in production (`NODE_ENV === "production"`) if `CLAUDE_MONTHLY_CEILING_USD` is not set. This prevents deployments without a cost ceiling.

**Risk**: Low — the guard is intentional and tested. However, it means any production deployment missing this env var will fail to start, which is a hard dependency on a configuration value that may not be obviously required.

---

## 4 Technical Debt

### 4.1 AI provider mismatch across documentation and code

**Sources**: `notes/axis-pulse-archdoc.md`, `src/lib/narrate.ts`, `src/lib/gemini.ts`, `.env.example`

| Layer | States |
|-------|--------|
| archdoc §7 | `claude-sonnet-4-6` (Anthropic) |
| `.env.example` | `GEMINI_API_KEY` (Google) |
| `src/lib/narrate.ts` (actual) | `createGroq` + `llama-3.3-70b-versatile` (Groq) |
| `src/lib/gemini.ts` (actual) | also uses `createGroq` despite the filename |

The file `src/lib/gemini.ts` is named after Google Gemini but imports `@ai-sdk/groq` and calls the Groq provider. The env example shows `GEMINI_API_KEY` but the code reads `GROQ_API_KEY`.

**Risk**: Any developer reading the archdoc or `.env.example` will provision the wrong credentials. The mismatch creates confusion about which AI provider is actually in use and which API key must be set for narration to function.

### 4.2 Legacy agent token fallback not yet retired

**Source**: `src/lib/resolveAgentToken.ts`, `prisma/schema.prisma`

`Project.agentTokenHash` is nullable in the schema (for projects that have been migrated to per-developer `AgentToken` rows). The fallback path in `resolveAgentToken()` is acknowledged as tech debt with a TODO comment. No migration script exists to backfill `AgentToken` rows for all existing projects.

**Risk**: The legacy path will remain in production indefinitely unless a migration is written and run. Events ingested via the legacy path cannot be attributed to a specific developer.

### 4.3 Coolify deployment not wired

**Source**: `notes/pending-work.txt`

The pending-work note states: *"Coolify deploy not wired — production deployment is manual."* No CI/CD pipeline exists.

**Risk**: Manual deployments are error-prone. Environment variables may be set inconsistently between deployments. There is no automated rollback on failed deployments.

### 4.4 `idleSeconds` / `offlineSeconds` columns retained but not written

**Source**: `prisma/schema.prisma`, `src/app/api/ingest/time/route.ts`

`MemberDailyTime.idleSeconds` and `MemberDailyTime.offlineSeconds` were removed from ingest writes in P12 but the columns were not dropped. Old rows contain real data; new rows contain zero. No migration marks the transition point in the data.

**Risk**: Analytics queries that read these columns will silently mix real historical idle/offline seconds with zeroed values, producing incorrect averages. The schema retains dead columns indefinitely.

### 4.5 Duplicate redaction implementations

**Source**: `src/lib/redact.ts`, `lib/redact.mjs`

Two copies of the same redaction pipeline are maintained. The parity test (`src/tests/redact-parity.test.ts`) catches divergence but requires both files to be updated simultaneously for every rule change.

**Risk**: A developer who updates only one file will create a parity failure. The parity test is the only guardrail; there is no shared source of truth (e.g. a single ESM module imported by both environments).

### 4.6 Three unresolved production blockers

**Source**: `notes/pending-work.txt`

Three items are explicitly documented as unresolved:
1. **Redis not provisioned** — all Upstash rate limiters fail open.
2. **`GROQ_API_KEY` not set** — narration and summary are not live-tested.
3. **Coolify deploy not wired** — deployment is manual.

**Risk**: The application is running in production with known gaps in rate limiting, AI integration, and deployment automation.

---

## 5 Compliance & Privacy Risks

### 5.1 Consent versioning and re-acknowledgement

**Sources**: `src/lib/consentCheck.ts`, `src/lib/pulse-body-shape.ts`

Consent v2 adds collection of `topApps` (application names from the developer's workstation). Users with consent v1 are required to re-acknowledge before `topApps` data is accepted. `needsConsentModal()` checks the stored consent version against the required version.

**Risk**: If a client submits `topApps` data without re-acknowledgement (e.g. by posting directly to `/api/ingest/time`), the server must correctly reject or strip the field. The `assertBodyShape()` function in `src/lib/pulse-body-shape.ts` validates the ingest body shape but does not itself check consent status — the consent check is performed in the route handler. A route that forgets to call the consent check will accept `topApps` without v2 consent.

### 5.2 App names as personal data

**Source**: `src/lib/pulse-body-shape.ts` (`topApps` field)

Application names (e.g. "Signal", "ProtonMail", "Grindr") may qualify as sensitive personal data under GDPR Article 9 (health, sexual orientation, religion) depending on the software installed.

**Risk**: `topApps` is stored in the `MemberDailyTime` record without any sensitivity classification or retention limit distinct from other time data. There is no mechanism to selectively delete only `topApps` data for a specific user without deleting their entire time record.

### 5.3 Audit log coverage

**Source**: `src/lib/audit.ts`, `src/app/api/admin/cleanup/route.ts`

`writeAudit()` records administrative and RBAC-sensitive actions (project PATCH, team changes, cleanup runs). The audit log is a Postgres table (`AuditLog`). The cleanup endpoint writes an audit entry only for non-dry-run executions (verified by `src/tests/phase7-hardening.test.ts`).

**Risk**: Audit log coverage is event-driven (developers must call `writeAudit()`). There is no database-level trigger that captures all changes. New routes that modify sensitive data may omit audit writes. The audit log has no defined retention policy or export mechanism beyond the admin UI.

### 5.4 Session token in logs

**Source**: `src/lib/auth.ts`, pino redact config

The pino redact config includes `sessionExcerpt` as a redacted path. However, if any new log call includes the raw session cookie value under a field name not in the redact list, it will appear in logs unredacted.

**Risk**: Low — the existing redact config is comprehensive and tested. The risk is residual: future log additions not audited against the redact list.

### 5.5 Sentry error reporting

**Sources**: `sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`

Sentry is configured for error reporting. By default Sentry may capture request bodies, user identifiers, and stack frames that contain local variable values.

**Risk**: If Sentry captures a request body containing a password or token before the redaction pipeline runs, PII may be sent to Sentry's servers. The Sentry SDK's `beforeSend` hook is not configured in the source files to strip sensitive data. This should be verified against the actual Sentry dashboard configuration.

---

## 6 Recommended Mitigations

Ordered by estimated impact × ease. Each item references the finding above.

| # | Finding | Mitigation | Priority |
|---|---------|-----------|----------|
| M1 | §1.2 — fail-open rate limiters | Provision Upstash Redis. All Upstash limiters activate automatically once `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set. | **P0 — blockers** |
| M2 | §4.1 — AI provider mismatch | Update `.env.example` to replace `GEMINI_API_KEY` with `GROQ_API_KEY`. Rename `src/lib/gemini.ts` to `src/lib/feed-summary.ts`. Update archdoc §7 to reflect Groq. | **P0 — correctness** |
| M3 | §1.1 — no signup rate limit | Add the same dual-window in-memory + Upstash rate limiter used by login to the signup route. Limit: 3/min/IP + 10/hr/IP. | **P1 — security** |
| M4 | §1.4 — missing security headers | Add `X-Frame-Options: DENY` and `Permissions-Policy: camera=(), microphone=(), geolocation=()` to `applySecurityHeaders()` in `src/middleware.ts`. | **P1 — security** |
| M5 | §1.1 — missing pepper assertion | Add a startup check in `instrumentation.ts`: throw if `AGENT_TOKEN_PEPPER` is absent in production (same pattern as `CLAUDE_MONTHLY_CEILING_USD` guard). | **P1 — security** |
| M6 | §1.2 — public metrics endpoint | Add session-based auth to `GET /api/metrics` restricted to `MANAGER` role. Remove `/api/metrics` from `PUBLIC_PREFIXES` in `src/middleware.ts`. | **P1 — security** |
| M7 | §4.2 — legacy agent token fallback | Write a one-time migration script that creates an `AgentToken` row for every project that still has a `Project.agentTokenHash`. Remove the fallback path from `resolveAgentToken()` once confirmed all projects have ≥1 row. | **P2 — tech debt** |
| M8 | §3.1 — in-memory rate limiters reset on restart | For the login rate limiter specifically, consider persisting the IP block list to Redis. For other in-memory limiters the restart-reset risk is acceptable given the short windows. | **P2 — scalability** |
| M9 | §4.5 — duplicate redaction | Consolidate `src/lib/redact.ts` and `lib/redact.mjs` into a single ESM file importable by both the Next.js server and Node.js scripts. | **P2 — maintainability** |
| M10 | §5.2 — app names as sensitive data | Add a retention policy for `topApps` data (e.g. purge after 90 days via the cleanup job). Add a note to the consent modal identifying app names as a distinct data category. | **P2 — compliance** |
| M11 | §1.4 — `style-src 'unsafe-inline'` | Audit all inline `style` usage in Next.js components. Replace inline styles with CSS classes to enable removal of `'unsafe-inline'` from the CSP. | **P3 — hardening** |
| M12 | §5.5 — Sentry PII | Add a `beforeSend` hook in `sentry.server.config.ts` that strips request body fields matching the pino redact path list before events are transmitted. | **P3 — compliance** |
| M13 | §3.2 — scale tier is a single env var | Implement per-organisation rate limit overrides stored in the database. Allow MANAGERs to view their organisation's current tier without a redeploy. | **P3 — scalability** |
| M14 | §4.4 — dead schema columns | Write a Prisma migration to drop `MemberDailyTime.idleSeconds` and `MemberDailyTime.offlineSeconds` after verifying no production analytics query reads them. | **P3 — maintainability** |
| M15 | §4.3 — no CI/CD | Wire Coolify deployment. Add a GitHub Actions workflow that runs `pnpm test` on PR and triggers a Coolify deploy on merge to `main`. | **P3 — operations** |

| P20 | `process.cwd()` as scan root may not be the project codebase root on a non-standard deployment | In a containerised or multi-service deployment, `process.cwd()` is the application working directory, which may be `/app` or the Next.js root — not the developer's project directory. The readiness scan would scan the Axis Pulse source code itself, not the project being measured. | Source: [`src/app/api/projects/[id]/readiness/scan/route.ts`](src/app/api/projects/[id]/readiness/scan/route.ts) — `scanMarkersInDir(process.cwd())`. Mitigation: ADR-readiness-003 acknowledges this as Phase 8 LOCAL ONLY scope. Phase 9 should allow a configurable scan path or a separate agent-side scan CLI. |
| P21 | `ReadinessSnapshot` rows are never pruned — unbounded growth | There is no retention/cleanup job for `ReadinessSnapshot`. A project that scans daily for a year accumulates 365+ rows. The GET route caps the OLS window at 90, so accuracy is unaffected, but DB storage will grow without bound. | Source: [`src/app/api/projects/[id]/readiness/route.ts`](src/app/api/projects/[id]/readiness/route.ts) — `take: 90`. Mitigation: Add `ReadinessSnapshot` to the cleanup job in `POST /api/admin/cleanup`, pruning rows older than 90 days per project. |
| P22 | Security CLI tools (Semgrep CE, gitleaks, osv-scanner) not installed on the server silently produce 0 findings | `runAllSecurityTools` in `src/lib/security-scan.ts` catches individual tool failures and returns 0 findings per missing tool. The catch-and-continue design is intentional (ADR-security-scan-001), but operators have no visibility into which tools actually ran unless they inspect `SecurityScanRun.toolsRun`. A deployment missing all three tools will always show `scanned_clean` even though no scan occurred. | Source: `src/lib/security-scan.ts` (catch blocks in `runSemgrep`, `runGitleaks`, `runOsvScanner`). Mitigation: `toolsRun` JSON on `SecurityScanRun` records which tools actually executed. A future health-check or admin panel could warn when `toolsRun` is empty. |
| P23 | Semgrep CE scan on large repositories may timeout and produce partial results | `runSemgrep` uses the default `--config=auto` ruleset. On a repository with hundreds of files, Semgrep may take more than 120 seconds, which is the default timeout used in the scan route's semaphore window. If the process is killed mid-scan, the output JSON will be incomplete and `parseSemgrepOutput` may return an empty array. | Source: `src/lib/security-scan.ts` — `runSemgrep`. Mitigation: Add an explicit `--timeout` flag to the semgrep invocation (e.g. `--timeout 90`) and catch JSON parse errors gracefully. |
| P24 | gitleaks may flag `.env.example` as a secret-containing file (false positive) | `.env.example` contains placeholder values like `your_token_here` and example connection strings. gitleaks pattern matching on entropy or regex may trigger false positives on example values. | Source: `src/lib/security-scan.ts` — `runGitleaks`. Mitigation: Add a `.gitleaksignore` or `gitleaks.toml` config file to the repository root specifying `.env.example` as an allowed file. |
| P25 | `ANTHROPIC_KEY_ENCRYPTION_SECRET` rotation requires a one-time re-encrypt of all stored org keys | `Organisation.anthropicApiKeyEnc` is encrypted using AES-256-GCM keyed on `ANTHROPIC_KEY_ENCRYPTION_SECRET`. If the secret is rotated without a migration script, all stored keys become unreadable — AI calls silently fall back to free models with no explicit error surfaced to MANAGERs. | Source: `src/lib/anthropic-key.ts` — `decryptApiKey`. Mitigation: Document the re-encrypt procedure in runbooks; `decryptApiKey` logs an error and returns `null` on failure so fallback behaviour is safe (never crashes). |

| P25 | ~~Admin management routes must write `role`/`teamId`/`isLineManager` to `Membership`, never to `User` — enforced by convention and tests only, not by the type system~~ **CLOSED — PM6 shipped** | The `User.role`, `User.teamId`, `User.isLineManager`, and `User.organisationId` columns have been dropped (migration `20260622000001_drop_user_legacy_cols`, 2026-06-22). Any code that attempts `db.user.update({ data: { role: ... } })` now produces a Prisma client compile error. The convention risk is a compile-time guarantee. | Source: `prisma/migrations/20260622000001_drop_user_legacy_cols/migration.sql`. Closed by ADR-028. |

| P26 | Drift cooldown, volume counter, and rate-limit store are in-process memory — reset on every process restart | `DRIFT_COOLDOWN_MS` (30 min) and `VOLUME_THRESHOLD` (50 ingest events) are tracked in module-level Maps in `src/lib/drift/orchestrate.ts`. `checkDriftRateLimit()` in `src/lib/ratelimit-drift.ts` uses an in-memory store. A process restart resets all three: (1) the cooldown guard — allowing an immediate re-trigger; (2) the volume counter — losing accumulated progress toward the 50-event threshold; (3) the rate-limit window — resetting the 3/hr per-project limit. This is the same pattern as the narration cooldown (§2.4) and the status/summary in-memory rate limiters. Acceptable for single-process 1x deployment; does not introduce data loss or security risk. | Source: `src/lib/drift/orchestrate.ts` (cooldowns Map, volumeCounters Map), `src/lib/ratelimit-drift.ts` (rateLimitStore Map). Mitigation: For high-availability or multi-process deployments, migrate all three to Upstash Redis sliding-window rate limiters. `ratelimit-drift.ts` is explicitly designed for Upstash-upgradability. |

---

| P27 | AI synthesis ceiling gate may leave debt scans in ERROR state | When `CLAUDE_MONTHLY_CEILING_USD` is hit, `isCeilingExceeded` returns true and `synthesiseDebtFindings` exits without calling the AI. The scan is marked ERROR. Raw Sonar data written at the start of the SYNTHESISING step is preserved in the DB — `blockerCount`, `criticalCount`, `majorCount`, `issueCount`, `qualityGate`, and ratings remain available even in ERROR state. Users must re-trigger the scan after the next billing cycle resets spend. Mitigation: the ceiling is configurable — raising `CLAUDE_MONTHLY_CEILING_USD` or unsetting it removes the gate. Source: `src/lib/debt/synthesise.ts` (`isCeilingExceeded` call), `src/lib/debt/orchestrate.ts` (ERROR path). |

| P28 | Anti-hallucination guard reduces but does not eliminate AI fabrication in debt findings | The `realFiles` guard drops TechDebtFindings whose `evidence.files` contain no file from the actual Sonar issue list or SecurityFinding list. However, the model could hallucinate a realistic-looking file name that happens to already exist in the evidence set (file attribution error, not file invention). The finding's `description` and `recommendation` fields are AI-generated and are not verified beyond the file-match guard. The priority guard ensures only valid P1–P4 strings are stored, but does not validate whether the assigned priority is accurate. Mitigation: the synthesis prompt instructs "only reference files and lines from the provided lists" and "no code excerpts". The guard is a defence-in-depth layer, not a formal proof of accuracy. Source: `src/lib/debt/synthesise.ts` (realFiles guard, priority guard, prompt instructions). |

---

| P29 | Feed summary prompt-echo puts raw instructions in the "Active Now" line | Free-tier OpenRouter/Groq models occasionally echo the system prompt instead of completing it. Before this fix, the echoed text was stored verbatim in `ActivityEvent.feedSummary` and surfaced in the dashboard "Active Now" line. The validator in `validateFeedSummary()` (`src/lib/gemini.ts`) now rejects known prompt-echo patterns and falls back to `firstSentence(excerpt)`. **Mitigated** — the validator is the hard guarantee; the `firstSentence` fallback always produces a usable value. Residual risk: new echo patterns not covered by the current `REJECT_PHRASES` / `REJECT_PREFIXES` lists could still slip through. To address, extend the lists in `validateFeedSummary()` as new patterns are observed. Source: `src/lib/gemini.ts` (`validateFeedSummary`), `src/app/api/ingest/event/route.ts` (Stop-event block). |

| P30 | Context Drift Analyser false-positive "no drift" verdict when diff contains no comparable docs/code | Before this fix, an assessment where the diff included no context docs and no source files (e.g. only binary files or files that GitHub 404'd) returned an empty findings array, which the UI displayed as "No drift detected — All context docs match the current code." This was a false positive: the AI had no evidence to compare against, so zero findings was not a signal of alignment. The fix adds an `inconclusive` path: when `docs.length === 0 && allCode.length === 0`, the assessment is stored as `COMPLETE` with `error: "inconclusive"` and the UI shows "Inconclusive — no comparable changes in this diff". The `auditDocsAgainstRepoSnapshot()` function provides a diff-independent structural check (framework mismatch detection against `repoSnapshot.detectedFrameworks`) that runs before the inconclusive fallback and can catch "wrong project's docs" scenarios. **Mitigated** — the inconclusive guard is tested in `src/tests/drift-inconclusive.test.ts`. Residual risk: the snapshot audit only detects framework mismatches for the ~30 known framework names in `KNOWN_STACK_TERMS`. A doc describing a bespoke or uncommon framework absent from the list will not be caught by the snapshot audit. Source: `src/lib/drift/analyse-ai.ts` (`auditDocsAgainstRepoSnapshot`, inconclusive guard), `src/lib/drift/orchestrate.ts` (COMPLETE+inconclusive handling), `src/app/context-analyser/[id]/_components/DriftDetailClient.tsx` (`InconclusiveState`). |

---

*End of risk document. All findings above are derived from direct inspection of the source files listed. No risks have been invented or extrapolated beyond what the code demonstrates.*
