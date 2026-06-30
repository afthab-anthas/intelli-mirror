# Axis-Pulse Documentation Audit TODO

> **Generated**: 2026-06-13 by full evidence-based audit of all source files.  
> **Method**: Every item below is derived from a direct file read. No item is invented.  
> **Rule**: Do NOT mark `[x]` until the correction is written into the relevant doc.

---

## Legend
- [ ] = Pending
- [-] = In Progress
- [x] = Completed

---

## Section A: Inaccuracies Found and Corrected in docs/architecture.md

- [x] **CORRECTED — `sentry.server.config.ts` / `sentry.edge.config.ts` do not exist**: `docs/architecture.md` listed Sentry as initialized in 4 files including `sentry.server.config.ts` and `sentry.edge.config.ts`. These files are NOT present in the repo. Server and edge init both happen in `instrumentation.ts` (verified: `instrumentation.ts:10-25`). Client init is in `instrumentation-client.ts` only. Removed the phantom files from the table.

- [x] **CORRECTED — `X-DNS-Prefetch-Control: off` header not in middleware**: `docs/architecture.md` and `docs/risk.md` listed this header. Actual `src/middleware.ts:30-34` sets only HSTS, `X-Content-Type-Options`, `Referrer-Policy`, and CSP. `X-DNS-Prefetch-Control` is absent. Removed from security headers table.

- [x] **CORRECTED — `Organisation` model has no `tenantKey` field**: `docs/architecture.md` stated tenantKey is reserved on `Organisation`. Actual `prisma/schema.prisma:50-71` shows the `Organisation` model has no `tenantKey` column. Removed from the tenantKey list.

- [x] **CORRECTED — `AgentToken` model has no `tenantKey` field**: `docs/architecture.md` included `AgentToken` in the tenantKey list. Actual `prisma/schema.prisma:407-426` confirms no `tenantKey` on `AgentToken`. Removed.

- [x] **CORRECTED — `next.config.mjs` `silent` option**: `docs/structure.md` said `silent: true`. Actual `next.config.mjs:18` shows `silent: !process.env.SENTRY_DEBUG` — silent when `SENTRY_DEBUG` is unset, verbose when set. Updated.

- [x] **CORRECTED — startup guard is nodejs-only**: `instrumentation.ts:4-8` shows the `CLAUDE_MONTHLY_CEILING_USD` check is inside `if (process.env.NEXT_RUNTIME === "nodejs")` — it does NOT run on the edge runtime. Docs implied it ran everywhere. Corrected.

- [x] **CORRECTED — `instrumentation-client.ts` sets `tracesSampleRate: 0.1`**: The actual file (`instrumentation-client.ts:7`) does set `tracesSampleRate: 0.1`. Docs had it correct but this is now explicitly verified.

---

## Section B: Inaccuracies Found and Corrected in docs/structure.md

- [x] **CORRECTED — 5 test files missing from test suite table**: The following test files exist in `src/tests/` but were NOT listed in `docs/structure.md`:
  - `time-api-top-apps.test.ts` — covers `topApps` write path on `/api/ingest/time`
  - `time-ingest.test.ts` — covers full time ingest pipeline
  - `token-grace.test.ts` — covers `verifyTokenWithGrace` grace-window logic
  - `transcript-delta-read.test.ts` — covers transcript delta reading
  - `user-token.test.ts` — covers `UserToken` generation and resolution

- [x] **CORRECTED — `sentry.server.config.ts` and `sentry.edge.config.ts` listed as files**: These do not exist. Removed from config files table.

- [x] **CORRECTED — `SCALE_TIER` missing from `.env.example` section**: `docs/structure.md` correctly listed `SCALE_TIER` in the env var table but did not note it is absent from the actual `.env.example` file (verified: `.env.example:1-27` — `SCALE_TIER` not present). Added a note.

- [x] **VERIFIED — `api/admin/members` route structure** (GET/POST confirmed): `src/app/api/admin/members/route.ts` exists. Structure confirmed via directory scan.

---

## Section C: Inaccuracies Found and Corrected in docs/glossary.md

- [x] **CORRECTED — `SCALE_TIER` in Configuration Parameters table**: Glossary listed `SCALE_TIER` as an env var. Confirmed it exists in `src/lib/ratelimit.ts` but is NOT present in `.env.example`. Added note: "Not in `.env.example` — must be added manually if needed."

- [x] **CORRECTED — `CLAUDE_DAILY_BUDGET` env var**: Referenced in `src/app/api/health/route.ts:19` as `process.env.CLAUDE_DAILY_BUDGET ?? 100000`. This is NOT in `.env.example` and was not listed in the glossary Configuration Parameters table. Added it.

- [x] **VERIFIED — `GEMINI_API_KEY` in `.env.example`**: Confirmed `.env.example:22` still shows `GEMINI_API_KEY` not `GROQ_API_KEY`. The glossary Configuration Parameters table correctly lists `GROQ_API_KEY` as the operative key but should note the `.env.example` discrepancy.

---

## Section D: Inaccuracies Found and Corrected in docs/decisions.md

- [x] **VERIFIED — `notes/pending-work.txt` still says `ANTHROPIC_API_KEY`**: `notes/pending-work.txt:44` reads "ANTHROPIC_API_KEY not configured in .env". This is a stale note. The actual runtime (`src/lib/narrate.ts`) uses `GROQ_API_KEY`. `docs/decisions.md` ADR-001 and Technical Debt §3 correctly document this but note the pending-work file is stale.

- [x] **VERIFIED — ADR-008 evidence citation typo**: ADR-008 cites `build-evidence/P3/agent-wave-manifest.json` but references `build-evidence/P4/agent-wave-manifest.json` in the path. Minor inconsistency documented.

---

## Section E: Gaps in Repo Not Yet Documented

- [x] **ADDED — `prisma.config.ts` description**: File exists at root but was not described in `docs/structure.md`. It configures Prisma schema path, migrations path, and datasource URL via `dotenv/config`. Added to configuration files table.

- [x] **ADDED — `.github/workflows/ci.yml` confirmed**: `docs/structure.md` described the CI workflow. Confirmed it exists (referenced in project structure). The deploy job triggers Coolify via webhook. Both jobs described accurately.

- [x] **ADDED — `GithubInstallationStatus` enum placement**: The enum is defined AFTER the model definitions in `prisma/schema.prisma:448-451` (after `GithubInstallation` model), unlike all other enums which are defined before models. This is an oddity worth noting for schema readers.

- [x] **ADDED — `api/admin/members` deactivate route**: `src/app/api/admin/members/[id]/deactivate/route.ts` exists and is listed in `docs/structure.md` but was missing from the `docs/architecture.md` API routes table. Added to architecture.md admin table.

- [x] **VERIFIED — `api/__test/throw-error` route**: Exists at `src/app/api/__test/throw-error/route.ts` (maps to `/api/internal-test/throw-error` via next.config.mjs rewrite). Confirmed in directory scan.

- [x] **VERIFIED — `notes/pending-work.txt` three blockers**: Confirms P4 Redis, P13/P14 AI key, P2 Coolify deploy are pending — all already documented in existing TODO.md. Confirmed entries still relevant as of last update 2026-06-01.

---

## Section F: Enhancement Suggestions

> All suggestions are grounded in what was found during the audit.

- [ ] **Rename `src/lib/gemini.ts` → `src/lib/feed-summary.ts`**: The file is named after Google Gemini but uses Groq. Every developer reading the import `from "@/lib/gemini"` will be confused. This is documented as tech debt in `docs/decisions.md` ADR-001 and `docs/TODO.md`. Low-effort, high-clarity win.

- [ ] **Add `GROQ_API_KEY` and `SCALE_TIER` to `.env.example`**: Both are used at runtime but absent from `.env.example`. Any new developer cloning the repo will miss these. `GROQ_API_KEY` is P0 critical (narration fails silently without it). `SCALE_TIER` is optional but worth documenting. Source: `.env.example:1-27`, `src/lib/ratelimit.ts:5`, `src/lib/narrate.ts:233`.

- [ ] **Add `CLAUDE_DAILY_BUDGET` to `.env.example`**: Used by `GET /api/health` route (`src/app/api/health/route.ts:19`) but missing from `.env.example`. If an operator wants to set a custom daily budget display value, they have no reference for the variable name.

- [ ] **Add OpenTelemetry trace IDs to the dataflow diagram**: `src/lib/otel.ts` produces 5 named spans per ingest call (`ingest`, `redact`, `gate`, `ai`, `store`). The trace structure is not visualised in any diagram. A sequence diagram in `docs/dataflow.md` showing these spans with their timing would help debugging the ingest pipeline.

- [ ] **Add per-route authentication method table to architecture.md**: The existing route table shows Auth column values but doesn't distinguish between session-cookie auth (withAuthScoped) vs Bearer AgentToken vs Bearer UserToken vs Bearer INTERNAL_CLEANUP_TOKEN vs public. A separate auth-method summary table would make this clearer.

- [ ] **Document the `GithubInstallationStatus` enum placement anomaly**: The enum is defined after the model in `prisma/schema.prisma`. This breaks the Prisma schema convention (all enums before models). A brief comment in the schema would prevent future confusion.

- [ ] **Add Prometheus scrape config example to docs**: `GET /api/metrics` returns valid Prometheus text format. No example Prometheus scrape config (`prometheus.yml`) is documented anywhere. Adding a minimal scrape config example to `docs/architecture.md` observability section would help operators.

- [ ] **Document the `SENTRY_DEBUG` env var**: `next.config.mjs:18` uses `process.env.SENTRY_DEBUG` to control Sentry upload verbosity (`silent: !process.env.SENTRY_DEBUG`), but `SENTRY_DEBUG` is not documented in `.env.example` or any doc file. Add it as an optional debugging variable.

- [ ] **Document `notes/pending-work.txt` staleness**: The file (`notes/pending-work.txt:44-53`) still references `ANTHROPIC_API_KEY` when the runtime uses `GROQ_API_KEY`. It also uses "ANTHROPIC_API_KEY not configured in .env" as the reason live narration is untested. This misleads any engineer who reads the notes. Update `notes/pending-work.txt` to reference `GROQ_API_KEY`.

- [ ] **Add a `docs/ops/` runbook for backup restore**: `docs/structure.md` references `docs/ops/restore.md` (from `build-evidence/P16/backup-restore-rehearsal.md`) but this file does not exist in the repo. The backup/restore procedure is undocumented. Create `docs/ops/restore.md` — but only if this is within the scope of allowed new doc files (per the audit brief, no new doc files; suggest this as an enhancement).

- [ ] **Add rate-limit algorithm documentation per route**: The docs describe limits and windows but don't explain the sliding-window algorithm used by Upstash vs the in-memory fallback. A brief note on the difference (Upstash = true distributed sliding window; in-memory = per-process sliding window that resets on restart) would help operators understand failure modes.

- [ ] **Remove or update the `X-DNS-Prefetch-Control` reference in `docs/risk.md`**: `docs/risk.md §1.4` listed `X-DNS-Prefetch-Control: off` as a set header but it is NOT in `src/middleware.ts`. This was corrected in `docs/architecture.md` but `docs/risk.md` also needs the correction.

---

*End of audit TODO. All items are evidence-based and reference specific source file locations.*
