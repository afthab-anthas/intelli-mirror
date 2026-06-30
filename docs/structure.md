# Structure

## Project Root Layout

| File / Dir | Purpose |
|---|---|
| `package.json` | npm manifest; name `axis-pulse-scaffold`, version `0.1.0`; defines `dev`, `build`, `start`, `lint`, `test`, `test:watch`, and three seed scripts |
| `next.config.mjs` | Next.js config wrapped by `withSentryConfig`; defines a `/api/__test/:path*` → `/api/internal-test/:path*` rewrite so test routes bypass App Router's `_`-folder exclusion; Sentry options: `silent: !process.env.SENTRY_DEBUG` (verbose when `SENTRY_DEBUG` is set), `widenClientFileUpload: false`, `hideSourceMaps: true`, `disableLogger: true`, `automaticVercelMonitors: false` |
| `prisma.config.ts` | Prisma config file (uses `defineConfig` from `prisma/config`); sets schema path `prisma/schema.prisma`, migrations path `prisma/migrations`, and datasource URL from `process.env.DATABASE_URL`; uses `dotenv/config` for local `.env` loading |
| `postcss.config.mjs` | PostCSS config; single plugin: `tailwindcss` |
| `components.json` | shadcn/ui config; style `base-nova`, RSC enabled, icon library `lucide`, path aliases `@/components`, `@/lib/utils`, `@/components/ui` |
| `.eslintrc.json` | ESLint config; extends `next/core-web-vitals` and `next/typescript` |
| `.gitignore` | Excludes `.env`, `.next/`, `node_modules/`, `prisma/generated/`, `coverage/`, `.playwright-mcp/`, `.pulse/config.json`, `.pulse/log`, `.pulse/rules.json`, `.pulse/transcript-cursors.json`, `/src/generated/prisma`, `dev-server.log`, `.claude/skills/`, `.claude/scheduled_tasks.lock`, `memory/` |
| `next-env.d.ts` | Auto-generated Next.js TypeScript reference file |
| `instrumentation.ts` | Next.js server/edge instrumentation hook; initialises Sentry on both `nodejs` and `edge` runtimes; enforces that `CLAUDE_MONTHLY_CEILING_USD` is set in production or throws at startup |
| `instrumentation-client.ts` | Client-side Sentry init; uses `NEXT_PUBLIC_SENTRY_DSN`; disables session/error replay sampling |
| `.env.example` | Template for all required environment variables (see §Environment Variables) |
| `.mcp.json` | MCP server config (not read in detail) |
| `CLAUDE.md` | Agent context index; links to all seven `docs/*.md` files |
| `prisma/` | Database schema, seeds, migrations |
| `scripts/` | Operational and CI helper scripts |
| `src/` | All application source code |
| `lib/` | Root-level JS-only utility (redact.mjs — used by the pulse-send agent hook) |
| `features/` | Feature planning documents (not deployed code) |
| `docs/` | Architecture and context documentation |
| `.github/` | GitHub Actions CI/CD workflows |
| `notes/` | Design specifications and personal notes |
| `build-evidence/` | Phase-by-phase build artefacts (screenshots, logs, manifests) |
| `all-prompts-library/` | Stored agent prompt templates |
| `feature-build-prompts/` | Per-phase build prompt scripts |
| `feature-build-tests/` | Per-phase acceptance test scripts |
| `backup/` | Project zip backup |

---

## Source Directory (`src/`)

### `src/app/` — Next.js App Router

#### Root pages

| Path | Description |
|---|---|
| `app/page.tsx` | Root route; immediately redirects to `/dashboard` |
| `app/layout.tsx` | Root layout; loads `Plus_Jakarta_Sans` and `IBM_Plex_Mono` fonts; wraps children in `ThemeProvider` (dark default); checks monthly cost ceiling via `getMonthlyCeilingUSD` / `getMonthlySpendUSD` and renders a sticky warning banner when exceeded |
| `app/globals.css` | Global Tailwind CSS entry point |
| `app/loading.tsx` | Root-level Suspense loading boundary |
| `app/error.tsx` | Root-level error boundary |
| `app/global-error.tsx` | Global error boundary (wraps the entire app) |
| `app/not-found.tsx` | 404 page |
| `app/privacy/page.tsx` | Privacy policy static page |
| `app/terms/page.tsx` | Terms of service static page |

#### Auth routes — `(auth)` route group

| Path | Description |
|---|---|
| `app/(auth)/login/page.tsx` | Client component; posts credentials to `/api/auth/login`; handles 423 account-lock response; uses `AuthLeftPanel` |
| `app/(auth)/signup/page.tsx` | Client component; posts to `/api/auth/signup`; includes password-strength meter; uses `AuthLeftPanel` |

#### Dashboard

| Path | Description |
|---|---|
| `app/dashboard/page.tsx` | Server component; calls `withAuthScoped()`, fetches projects scoped by role (MANAGER sees org-wide, others see own team), fetches `fetchDashboardSummary`, renders `ProjectCard` grid + `DashboardStatsClient` + `ActivityFeedClient` + optional `TrackingConsentModal` |
| `app/dashboard/_components/ProjectCard.tsx` | Renders a single project card with status, sparkline, last-activity timestamp |
| `app/dashboard/_components/SparkBars.tsx` | 7-day sparkline bar chart component |
| `app/dashboard/_components/DashboardStatsClient.tsx` | Client component; renders KPI stat cards |
| `app/dashboard/_components/StatCard.tsx` | Individual KPI card with label, value, sparkline |
| `app/dashboard/_components/ActivityFeed.tsx` | Server component wrapper for activity feed |
| `app/dashboard/_components/ActivityFeedClient.tsx` | Client component rendering activity feed items |
| `app/dashboard/_components/SignOutButton.tsx` | Client component; sign-out button |

#### Project detail

| Path | Description |
|---|---|
| `app/projects/[id]/page.tsx` | Server component; fetches project (with latest `intelligence` and `executiveSummaries`), 3-day activity window, `computeVerdict`, `computeExceptionFlags`, daily cost; enforces team-scoped access for non-MANAGERs |
| `app/projects/[id]/_components/VerdictBanner.tsx` | Renders on-track/needs-attention/at-risk verdict |
| `app/projects/[id]/_components/AISummaryPanel.tsx` | Shows latest AI narration from `Intelligence` |
| `app/projects/[id]/_components/ExceptionsPanel.tsx` | Client component. Renders operational `ExceptionFlag[]` (flat chips) and grouped security findings (`SecurityFindingGroup[]`). HIGH/CRITICAL security groups expanded by default; MEDIUM/LOW behind "+N more findings — view all" toggle. Each `GroupRow` expands to show rawMessage + repo-relative file:line list. `scanState` prop controls honest empty states ("No security scan has been run yet." / "Nothing needs attention right now."). |
| `app/projects/[id]/_components/ExceptionsWhoRow.tsx` | Shows which members are active/idle; passes `flags`, `securityGroups`, and `scanState` through to `ExceptionsPanel`. |
| `app/projects/[id]/_components/MomentumStrip.tsx` | Momentum / velocity indicator strip |
| `app/projects/[id]/_components/RepoContextPanel.tsx` | Shows linked GitHub repo snapshot and status. Phase 5: `data-tour="project-repo-context"` on all 4 return-path `<div>`s. |
| `app/projects/[id]/_components/RecentCommitsAccordion.tsx` | Expandable list of recent commits from git activity |
| `app/projects/[id]/_components/StatusBox.tsx` | Manual status entry box for members |
| `app/projects/[id]/_components/MemberStateCard.tsx` | Per-member current-state card |
| `app/projects/[id]/_components/GitActivityRail.tsx` | Visual git activity rail |
| `app/projects/[id]/_components/ProjectVitalSigns.tsx` | Cost, token usage, timing vitals |
| `app/projects/[id]/_components/ProjectActionsBar.tsx` | Rotate token, export PDF, other project actions |
| `app/projects/[id]/_components/ExecSummaryButton.tsx` | Triggers `/api/projects/[id]/summary` streaming |
| `app/projects/[id]/_components/ExecutiveSummaryPanel.tsx` | Renders the streamed executive summary with confidence score |
| `app/projects/[id]/_components/WorkTypeBar.tsx` | Vertical bar chart of files-changed per commit-type bucket (bug/docs/build/test/other), windowed by global time filter |
| `app/projects/[id]/_components/SpendRing.tsx` | Windowed dev spend amount card (obeys global time filter, no ceiling ring); MANAGER/LINE_MANAGER only |
| `app/projects/[id]/_components/SessionTimeChip.tsx` | Legacy chip — session time is now rendered as Col 4 of `CompletionStatusWidget`; file retained for reference |
| `app/projects/[id]/_components/TimeFilterBar.tsx` | Client pill component for Today/7d/30d global time filter |
| `app/projects/[id]/_components/FeatureAreaTrack.tsx` | Feature/area · Phase · Latest worker table (Server Component); phase is categorical badge only. Phase 5: `data-tour="project-feature-progress"` on both `<div>` paths. |
| `app/projects/[id]/_components/RecentActivityAccordion.tsx` | Collapsible list of Claude-hook activity events with real text (feedSummary or manualText); mirrors RecentCommitsAccordion |
| `PromptAdoptionStrip` | `src/app/projects/[id]/_components/PromptAdoptionStrip.tsx` | Chip row: windowed library-prompt match count + "In context: P[N] · [Title]" recency chip; empty state "No library prompts matched today." |
| `CompletionStatusWidget` | `src/app/projects/[id]/_components/CompletionStatusWidget.tsx` | Client component; 4-cell "Completion Status" panel (A4 plain-English unfinished markers · A3 test-file count · A2 OLS burn-down forecast · Col4 Claude Code session time). "Run Scan" button visible to MANAGER/LINE_MANAGER only. No completion %, no single rolled-up score. |
| `CodeHealthRing` | `src/app/projects/[id]/_components/CodeHealthRing.tsx` | Client component; SVG ring showing worst-of reliability/security/maintainability grade; quality gate badge; coverage/duplication pcts; "Run Scan" button (MANAGER/LINE_MANAGER). "Not scanned yet — run a scan" empty state. Phase 5: `data-tour="project-code-health"` on both `<section>` paths. |

#### Teams

| Path | Description |
|---|---|
| `app/teams/page.tsx` | Server component; shows all teams (MANAGER: all, others: own team only); renders `TeamsTable` and `NewTeamDialog` |
| `app/teams/_components/TeamsTable.tsx` | Table of teams with member/project counts |
| `app/teams/_components/NewTeamDialog.tsx` | Dialog for creating a new team (MANAGER only). Phase 5: `data-tour="teams-modal"` on inner card; removed `data-tour="teams-create-btn"`. |
| `app/teams/[id]/page.tsx` | Team detail; fetches team, members, recent activity, GitHub installations; enforces team-scoped access |
| `app/teams/[id]/_components/TeamDetailClient.tsx` | Client component for team detail interactivity |
| `app/teams/[id]/_components/NewProjectDialog.tsx` | Dialog for creating a new project within the team. Phase 5: `data-tour="project-create-modal"` on form card. |
| `app/teams/[id]/_components/TimeTrackingToggle.tsx` | Toggle for enabling/disabling time tracking on a team |

#### Admin

| Path | Description |
|---|---|
| `app/admin/audit/page.tsx` | Audit log viewer; MANAGER-only; supports filtering by userId, action, subjectId, date range; paginated at 50 per page |
| `app/admin/budget/page.tsx` | Developer token budget dashboard; fetches per-project token usage and `devTokenBudget`; MANAGER-only |
| `app/admin/budget/_components/BudgetClient.tsx` | Client component for budget editing |
| `app/admin/members/page.tsx` | Member management; MANAGER sees all users, LINE_MANAGER sees own team + unassigned |
| `app/admin/members/_components/MembersClient.tsx` | Client component for member CRUD actions; includes "View" button per row that opens MemberDetailCard |
| `app/admin/members/_components/MemberDetailCard.tsx` | Portal-mounted member detail card (Header + Spend + Time + Projects + Sessions + Commits); fetches via fetchMemberCard; rendered via createPortal to document.body |
| `app/admin/members/_components/member-card-fetch.ts` | Pure async fetch utility: `fetchMemberCard(memberId)` → `MemberCardResult`; wraps GET /api/admin/members/:id/card |
| `app/admin/tokens/page.tsx` | Agent token management; MANAGER sees all projects, LINE_MANAGER sees own team |
| `app/admin/tokens/_components/TokensClient.tsx` | Client component for token revoke/restore/rotate |
| `app/admin/cost-dashboard/page.tsx` | Monthly cost dashboard; shows ceiling, spend, per-project breakdown; uses `getMonthlyCeilingUSD`, `getDevDailySpendUSD`, `getDevSpendByUser`, `getDevSpendByDay` |
| `app/admin/cost-dashboard/_components/CostDashboardRefreshButton.tsx` | Client refresh button for cost dashboard |
| `app/admin/github/page.tsx` | GitHub App installation management; lists `GithubInstallation` records; MANAGER and LINE_MANAGER |
| `app/admin/github/_components/GitHubClient.tsx` | Client component for GitHub connect/disconnect flow |
| `app/admin/consents/page.tsx` | Consent status viewer; MANAGER-only; shows per-user `TimeTrackingConsent` records |
| `app/admin/productive-rules/page.tsx` | Productive app rules editor; MANAGER sees GLOBAL + all TEAM rules; LINE_MANAGER sees GLOBAL (read-only) + own team's TEAM rules |
| `app/admin/productive-rules/_components/ProductiveRulesClient.tsx` | Client component for rule CRUD |

#### Other pages

| Path | Description |
|---|---|
| `app/install/page.tsx` | Installation guide; fetches existing `UserToken`; renders `InstallClient`, `MachineSetupSection`, and (MANAGER-only) `AnthropicKeySection` |
| `app/install/_components/InstallClient.tsx` | Client component displaying install instructions and token generation |
| `app/install/_components/MachineSetupSection.tsx` | Machine-level setup instructions (`.pulse` config) |
| `app/install/_components/CopyableCode.tsx` | Copyable code snippet component |
| `app/install/_components/AnthropicKeySection.tsx` | MANAGER-only client component; shows key status chip (hint when set, "not configured" badge otherwise); password input with `sk-ant-` format validation; save/update button with verifying spinner; calls `POST /api/admin/org/anthropic-key` |
| `app/install/install.module.css` | CSS module for install page header |
| `app/prompts/page.tsx` | Prompt library viewer; fetches all `Prompt` records for the org sorted by `pNumber`; MEMBER can view, MANAGER/LINE_MANAGER can edit |
| `app/prompts/_components/PromptsClient.tsx` | Client component for prompt CRUD |
| `app/profile/page.tsx` | User profile page; shows time stats, role badge, `ChangePasswordForm`, `PersonalInfoForm` |
| `app/profile/_components/ChangePasswordForm.tsx` | Change password form |
| `app/profile/_components/PersonalInfoForm.tsx` | Edit name/bio/job title/location |
| `app/profile/_components/RetakeTourButton.tsx` | "Take the tour again →" button; PATCHes `hasOnboarded: false`, clears tour cookie, redirects to `/dashboard` |
| `app/invite/[id]/page.tsx` | Invite acceptance page; looks up `Invitation` by ID; passes to `InviteAcceptClient` |
| `app/invite/[id]/_components/InviteAcceptClient.tsx` | Client component handling invite accept/reject flow |
| `app/debt-analyzer/page.tsx` | Server component; MANAGER+LINE_MANAGER only (MEMBER → /dashboard); lists all projects with latest `TechnicalDebtScan` status |
| `app/debt-analyzer/[id]/page.tsx` | Per-project debt scan page; fetches latest scan; passes to `DebtScanClient` |
| `app/debt-analyzer/[id]/_components/DebtScanClient.tsx` | Client component; trigger button, 5s poll loop, 15min timeout, state UI (no-scan/PENDING/RUNNING/COMPLETE/ERROR) |

#### API routes

**Authentication**

| Route | Method | Description |
|---|---|---|
| `api/auth/[...nextauth]/route.ts` | GET/POST | NextAuth v5 catch-all handler; JWT session strategy, custom sign-in page at `/login` |
| `api/auth/login/route.ts` | POST | Custom credential login; bcrypt verify, account lockout after failed attempts, issues NextAuth JWT session |
| `api/auth/signup/route.ts` | POST | User registration; validates password policy, hashes with bcrypt cost 12, creates user + organisation |
| `api/auth/memberships/route.ts` | GET | PM4: Lists the caller's memberships only. Parameter-less `GET()` — structurally cannot read URL/headers/body; the only `userId` source is `ctx.userId` from `withAuthScoped`. A structural forge-guard test (`memberships-api.test.ts`) reads the route source from disk and pins the absence of every input idiom. |
| `api/auth/switch-org/route.ts` | POST | PM4: Re-issues the JWT with a new `activeOrganisationId`. Gates: session (via `withAuthScoped`) → rate limit (`checkSwitchOrgRateLimit`) → body JSON → org-id type guard → Membership composite-key lookup → session read → encode → cookie. JWT carries only `sub`/`name`/`email`/`activeOrganisationId`/`sessionVersion`/`iat`/`exp`/`jti` (no `role`/`teamId`/`isLineManager`). Same cookie semantics as `login` (proto-aware Secure prefix, `Max-Age=2592000`). |
| `api/auth/pending-invitations/route.ts` | GET | PM5: Returns the caller's PENDING memberships with `invitationId`. Parameter-less `GET()`. Used by `AppShell` to compute `pendingInviteCount` for the `OrgBadge` amber dot. Response: `{ memberships: [{ organisationId, organisationName, invitationId }] }`. |

**Agent ingestion (Bearer token auth)**

| Route | Method | Description |
|---|---|---|
| `api/ingest/event/route.ts` | POST | Main agent event ingestion; validates body with Zod; resolves `AgentToken`; runs redaction pipeline; matches p-number via Jaccard; delta-gates narration; calls `generateNarration` (Groq Llama); records OTel trace spans; records Prometheus metrics |
| `api/ingest/time/route.ts` | POST | Time tracking ingestion; accepts `workedSeconds`, `productiveSeconds`, `unproductiveSeconds`, `topApps`; resolves via `AgentToken` or `UserToken`; checks v2 consent before persisting `topApps`; upserts `MemberDailyTime` |

**Projects**

| Route | Method | Description |
|---|---|---|
| `api/projects/route.ts` | GET | List projects scoped by auth context |
| `api/projects/[id]/route.ts` | GET/PATCH/DELETE | Project CRUD |
| `api/projects/[id]/summary/route.ts` | POST | Streaming executive summary via Groq Llama `llama-3.3-70b-versatile`; rate-limited at 10/hr/project (1x); records audit log |
| `api/projects/[id]/ai-summary/route.ts` | GET | Fetch latest cached AI narration |
| `api/projects/[id]/export/route.ts` | GET | PDF export of executive summary via `@react-pdf/renderer`; rate-limited at 20/hr |
| `api/projects/[id]/agent-tokens/route.ts` | GET/POST | List or create per-developer agent tokens for a project |
| `api/projects/[id]/rotate-token/route.ts` | POST | Rotate project-level legacy agent token |
| `api/projects/[id]/repo-context/refresh/route.ts` | POST | Trigger GitHub repo context refresh (fetch metadata + snapshot) |
| `api/projects/[id]/readiness/route.ts` | GET | Retrieve latest readiness signal (all roles); builds `ReadinessSignal` from up to 90 recent snapshots |
| `api/projects/[id]/readiness/scan/route.ts` | POST | Run marker scan + coverage read (MANAGER/LINE_MANAGER); persist `ReadinessSnapshot`; rate-limited 1/60s/project |
| `api/projects/[id]/code-health/route.ts` | GET | Latest `CodeHealthSnapshot` for a project (DB read only) |
| `api/projects/[id]/code-health/scan/route.ts` | POST | Trigger sonar-scanner, fetch SonarQube metrics, store `CodeHealthSnapshot`; MANAGER/LINE_MANAGER only; rate-limited 1/120s/project |
| `api/projects/[id]/security-scan/route.ts` | POST | Download repo tarball, run Semgrep CE + gitleaks + osv-scanner, persist `SecurityScanRun` + `SecurityFinding` rows; MANAGER/LINE_MANAGER only; rate-limited 1/120s/project |
| `api/projects/[id]/security-findings/route.ts` | GET | Latest `SecurityScanRun` with findings; returns `scanState` (not_scanned/scanned_clean/has_findings); all roles, own team |
| `api/projects/[id]/drift/route.ts` | POST/GET | POST triggers a new `ContextDriftAssessment`; rate-limited 3/hr/project; writes CONTEXT_ASSESS audit; returns `{ assessmentId, status: "PENDING" }` 202. GET lists last 10 assessments for the project scoped to organisationId |
| `api/projects/[id]/drift/baseline/route.ts` | POST | Resolves context source, stores `contextBranchBaselineSha` on the Project, writes CONTEXT_BASELINE_SET audit; MANAGER/LINE_MANAGER only |
| `api/projects/[id]/drift/[assessmentId]/route.ts` | GET | Triple-scoped fetch (assessmentId + projectId + organisationId); calls `resetStaleRunningAssessments()` before read |
| `api/projects/[id]/debt-scan/route.ts` | POST trigger debt scan (MANAGER/in-team LINE_MANAGER, rate-limited 1/30min); GET list latest 10 scans |
| `api/projects/[id]/debt-scan/[scanId]/route.ts` | GET poll single scan; triple-scope guard (scanId + projectId + organisationId) |
| `api/projects/[id]/members/route.ts` | GET/POST | Manage project membership |
| `api/projects/[id]/members/[userId]/events/route.ts` | GET | Fetch events for a specific member on a project |

**Agent tokens**

| Route | Method | Description |
|---|---|---|
| `api/agent-tokens/[tokenId]/route.ts` | GET | Fetch token metadata |
| `api/agent-tokens/[tokenId]/revoke/route.ts` | POST | Revoke a per-developer agent token |
| `api/agent-tokens/[tokenId]/restore/route.ts` | POST | Restore a revoked agent token |

**Teams**

| Route | Method | Description |
|---|---|---|
| `api/teams/route.ts` | GET/POST | List or create teams |
| `api/teams/[id]/route.ts` | GET/PATCH/DELETE | Team CRUD; PATCH rate-limited |

**Admin members**

| Route | Method | Description |
|---|---|---|
| `api/admin/members/route.ts` | GET | List members |
| `api/admin/members/[id]/route.ts` | GET/PATCH/DELETE | Member detail |
| `api/admin/members/[id]/activate/route.ts` | POST | Activate user account |
| `api/admin/members/[id]/deactivate/route.ts` | POST | Deactivate user account |
| `api/admin/members/[id]/promote/route.ts` | POST | Promote to LINE_MANAGER |
| `api/admin/members/[id]/demote/route.ts` | POST | Demote from LINE_MANAGER |
| `api/admin/members/[id]/role/route.ts` | PATCH | Change role |
| `api/admin/members/[id]/assign-to-team/route.ts` | POST | Assign member to a team |
| `api/admin/members/[id]/remove-from-team/route.ts` | POST | Remove member from their team |
| `api/admin/members/[id]/card/route.ts` | GET | Per-member detail card data (MANAGER any org member; LINE_MANAGER own-team only; MEMBER blocked) |

**Admin — other**

| Route | Method | Description |
|---|---|---|
| `api/admin/invitations/route.ts` | GET/POST | List or create invitations |
| `api/admin/budget/route.ts` | GET | Budget summary |
| `api/admin/budget/[id]/route.ts` | PATCH | Update per-project `devTokenBudget` |
| `api/admin/cleanup/route.ts` | POST | Data lifecycle cleanup; Bearer-token auth via `INTERNAL_CLEANUP_TOKEN`; nulls content on `ActivityEvent` rows >90 days, deletes `AuditLogEntry` >12 months, deletes `MemberDailyTime` >13 months |
| `api/admin/org/anthropic-key/route.ts` | POST | MANAGER-only; validates, test-calls, encrypts and stores org Anthropic API key; returns `{ hint }` |

**GitHub**

| Route | Method | Description |
|---|---|---|
| `api/github/connect/route.ts` | GET | Initiates GitHub App OAuth flow |
| `api/github/callback/route.ts` | GET | OAuth callback; creates `GithubInstallation` record |
| `api/github/installations/[id]/route.ts` | GET/DELETE | Installation detail or delete |
| `api/github/installations/[id]/repos/route.ts` | GET | List repos for an installation; rate-limited at 30/min/user |
| `api/github/installations/refresh/route.ts` | POST | Refresh all installations status |

**Observability & utilities**

| Route | Method | Description |
|---|---|---|
| `api/health/route.ts` | GET | Health check; pings DB with `SELECT 1`; returns `{ db, lastEventAgeSeconds, claudeBudgetRemaining }` |
| `api/metrics/route.ts` | GET | Prometheus text-format metrics; public endpoint (no auth) |
| `api/status/route.ts` | POST | Manual status submission by authenticated members; redacts text; matches p-number; rate-limited at 30/min/user |
| `api/audit/route.ts` | GET | Audit log API |
| `api/dashboard/summary/route.ts` | GET | Dashboard summary data endpoint |

**Users & profile**

| Route | Method | Description |
|---|---|---|
| `api/users/[id]/time/route.ts` | GET | Fetch time data for a user (role-gated: MEMBER sees own only) |
| `api/me/time/route.ts` | GET | Authenticated user's own time data |
| `api/profile/change-password/route.ts` | POST | Change own password |
| `api/profile/update/route.ts` | PATCH | Update own profile fields (name, bio, jobTitle, location) |

**Prompts & events**

| Route | Method | Description |
|---|---|---|
| `api/prompts/route.ts` | GET/POST | List or create prompts |
| `api/prompts/[id]/route.ts` | PATCH/DELETE | Prompt CRUD |
| `api/events/[id]/p-number/route.ts` | PATCH | Override p-number on an activity event |

**Consents & invites**

| Route | Method | Description |
|---|---|---|
| `api/consents/acknowledge/route.ts` | POST | Acknowledge time-tracking consent (sets `acknowledgedAt`, upgrades to `consentVersion: 2`) |
| `api/invite/accept/route.ts` | POST | Accept an invitation; creates/updates user and sets team membership. PM5: for existing-user invites, atomically flips PENDING→ACTIVE Membership and bumps `User.sessionVersion`. |
| `api/invite/decline/route.ts` | POST | PM5: Idempotent decline — deletes the PENDING Membership row for the caller and marks `Invitation.status = DECLINED`. Uses session cookie auth (not on CSRF bypass list). |

**Install scripts**

| Route | Method | Description |
|---|---|---|
| `api/install/script/route.ts` | GET | Returns the `pulse-send.mjs` install shell script |
| `api/install/machine-script/route.ts` | GET | Returns the machine-level install script |
| `api/install/user-token/route.ts` | GET/POST | Fetch or generate a per-user `UserToken` |

**Productive rules**

| Route | Method | Description |
|---|---|---|
| `api/productive-rules/route.ts` | GET/POST | List or create productive app rules |
| `api/productive-rules/[id]/route.ts` | PATCH/DELETE | Update or delete a productive app rule |

**Test utilities**

| Route | Method | Description |
|---|---|---|
| `api/internal-test/throw-error/route.ts` | GET | Throws a test error for Sentry verification (reachable via `/api/__test/throw-error` rewrite) |

---

### `src/lib/` — Shared Library Modules

| Module | Exports / Purpose |
|---|---|
| [`auth.ts`](src/lib/auth.ts) | NextAuth v5 config; exports `handlers`, `auth`, `signIn`, `signOut`; JWT strategy; no providers (custom login route); session callback stamps `role`, `teamId`, `isLineManager`, `organisationId`, `sessionVersion` |
| [`db.ts`](src/lib/db.ts) | Singleton Prisma client using `@prisma/adapter-pg` (connection pool); fixes `TIMESTAMP` parsing to UTC; exported as `db` |
| [`withAuthScoped.ts`](src/lib/withAuthScoped.ts) | Exports `withAuthScoped()` returning `AuthContext | null`; validates `sessionVersion` against DB (30s cache) to detect forced re-login; builds `AuthScope` (allTeams, canSeeTimeData, viewedTeamIds); exports `invalidateSessionVersionCache()` |
| [`audit.ts`](src/lib/audit.ts) | Exports `writeAudit()` (creates `AuditLogEntry`) and `getIp()` (extracts IP from `x-forwarded-for` / `x-real-ip`) |
| [`token.ts`](src/lib/token.ts) | Agent token utilities: `generateRawToken()` (32 random bytes base64url), `hashToken()` (bcrypt cost 12 + pepper), `verifyToken()`, `tokenPreview()` (last 4 chars), `verifyTokenWithGrace()` (current hash + previous hash within expiry) |
| [`resolveAgentToken.ts`](src/lib/resolveAgentToken.ts) | `resolveAgentToken(rawToken, projectId)`: looks up per-developer `AgentToken` rows by preview → bcrypt verify; falls back to `Project.agentTokenHash` via `verifyTokenWithGrace` for legacy migration |
| [`resolveAgentTokenGlobal.ts`](src/lib/resolveAgentTokenGlobal.ts) | `resolveAgentTokenGlobal(rawToken)`: cross-project token resolution without known `projectId`; same two-step strategy; returns `projectId`, `userId`, `tokenId`, `userEmail` |
| [`userToken.ts`](src/lib/userToken.ts) | `resolveUserToken(rawToken)`: resolves per-user `UserToken` by preview → bcrypt verify; returns `userId`, `organisationId`, `teamId` |
| [`password.ts`](src/lib/password.ts) | `validatePassword()` (min 12 chars, requires letter + digit + symbol), `hashPassword()` (bcrypt cost 12), `verifyPassword()` |
| [`redact.ts`](src/lib/redact.ts) | `redact(input)` → `{ text, count, kinds }`; strips env-style secrets, JWTs, `sk-ant-` / `sk-` API keys, AWS key IDs, PEM private keys, URL credentials, bcrypt hashes; truncates to 1500 chars |
| [`anthropic-key.ts`](src/lib/anthropic-key.ts) | `encryptApiKey(raw)` / `decryptApiKey(enc)`: AES-256-GCM symmetric crypto using `ANTHROPIC_KEY_ENCRYPTION_SECRET`. `obscureKey(raw)`: returns `sk-ant-api0...abcd` hint. `getOrgAnthropicKey(organisationId)`: DB fetch + decrypt, returns `string \| null` |
| [`narrate.ts`](src/lib/narrate.ts) | `generateNarration(event, project, traceCtx, anthropicApiKey?)`: calls Anthropic Haiku (primary) or free models (fallback) via `getAutoCallModel`; uses 90s in-memory cooldown per project; delta-gates on `inputHash`; returns structured JSON (headline, narration, stage, riskLevel, riskFocus); records OTel spans; exports `resetCooldowns()` |
| [`gemini.ts`](src/lib/gemini.ts) | `generateFeedSummary(excerpt, filesChanged, gitSummary, anthropicApiKey?)`: calls Anthropic Haiku (primary) or free models (fallback) for 5–8 word one-liner feed summaries; `validateFeedSummary(text)`: prompt-echo/length validator; `firstSentence(text)` helper |
| [`otel.ts`](src/lib/otel.ts) | Minimal OTel-compatible in-process span tracing; exports `startTrace()`, `startSpan()`, `endSpan()`, `commitTrace()`, `getLastTrace()`; stores last completed trace in memory |
| [`metrics.ts`](src/lib/metrics.ts) | In-memory Prometheus-compatible metrics store; tracks request counts by status class, latency histograms per route; exports `recordRequest()`, `recordClaudeTokens()`, `generatePrometheusText()` |
| [`logger.ts`](src/lib/logger.ts) | Pino logger singleton; redacts sensitive fields (`password`, `passwordHash`, `agentToken`, `sessionExcerpt`, `manualText`, `tenantKey`, `jwt`, `bearerToken`, authorization headers); log level from `LOG_LEVEL` env var |
| [`cost-ceiling.ts`](src/lib/cost-ceiling.ts) | Monthly Claude cost ceiling enforcement; `getMonthlyCeilingUSD()` reads `CLAUDE_MONTHLY_CEILING_USD`; `getMonthlySpendUSD(orgId)` aggregates `Intelligence.inputTokens/outputTokens`; `isCeilingExceeded()`; `getProjectSpendByMonth()` |
| [`member-card.ts`](src/lib/member-card.ts) | `getMemberCard(targetId, organisationId, canSeeSpend, rawWindow?, viewerTodayMs?)` — assembles per-member card data; Phase 1: user + consent + latestTz in parallel; Phase 2: spend, time (member-tz windowed), projects, sessions, commits in parallel. `rawWindow` drives event/spend boundaries (viewer tz); `viewerTodayMs` is viewer's local midnight ms. Exports `MemberCardData`, `MemberIdentity`, `MemberSpend`, `MemberTimeData`, `TimeDataV2`, `TimeDataNotConsented`, `MemberProject`, `MemberSession`, `MemberCommit`, `TopApps` |
| [`ratelimit-member-card.ts`](src/lib/ratelimit-member-card.ts) | `checkMemberCardRateLimit(userId)` — Upstash sliding-window 30/min per caller userId; prefix `pulse:admin:member-card`; fail-open on Upstash errors |
| [`ratelimit-switch-org.ts`](src/lib/ratelimit-switch-org.ts) | `checkSwitchOrgRateLimit(userId)` — Upstash sliding-window 10/min AND 60/hour per `ctx.userId`; prefixes `pulse:switchorg:min`/`pulse:switchorg:hour`; fail-open on Upstash errors; bypasses in `NODE_ENV=test`; exports `_checkSwitchOrgMemRateLimit` and `_resetSwitchOrgRateLimitStore` for the rate-limits conformance suite. |
| [`dev-cost.ts`](src/lib/dev-cost.ts) | Developer Claude Code token cost tracking; defines pricing constants (`SONNET_PRICING`, `OPUS_PRICING`, `HAIKU_PRICING`) and `computeDevCostUSD()`; exports `getProjectDailySpendUSD()`, `getProject7DayDailySpends()`, `getProjectMonthlyTokens()`, `getProjectMonthlyDevSpendUSD()`, `getProjectWindowedDevSpendUSD()`, `getProjectWindowedSpendAndTokens()`, `getDevDailySpendUSD()`, `getDevSpendByUser()`, `getDevSpendByDay()`, `getDevTokensByProject()`; re-exports budget utils |
| [`project-time-window.ts`](src/lib/project-time-window.ts) | `TimeWindow = "today" \| "7d" \| "30d"` type; `resolveTimeWindow(raw, todayCutoffMs?)` — resolves window string into `ResolvedTimeWindow` with concrete Date boundaries; `parseTodayCutoff(raw)` — parses browser-side epoch-ms param to viewer's local midnight; used across project pages and member card |
| [`completion-cells.ts`](src/lib/completion-cells.ts) | `CompletionCellId = "test_files" \| "session_time"`; `getCompletionCells(canSeeSession)` — returns ordered list of cell IDs for CompletionStatusWidget; filters out `session_time` for MEMBER role |
| [`code-health-poller.ts`](src/lib/code-health-poller.ts) | `pollForNewerSnapshot(opts: PollOptions)` — client-only polling loop for code-health scan completion; polls `GET /api/projects/[id]/code-health` every 5s; resolves when `snapshot.scannedAt > triggerTime`; times out after 10 min |
| [`session-time.ts`](src/lib/session-time.ts) | `getProjectSessionSeconds(projectId, organisationId, since)` — aggregates `SUM(sessionDurationSeconds)` from Stop `ActivityEvent` rows in the time window; `formatSessionTime(seconds)` — formats seconds as "Xs" / "Xm" / "Xh Ym" |
| [`budget-utils.ts`](src/lib/budget-utils.ts) | Pure, client-safe budget display utilities; `computeBudgetStatus()`, `computeUsagePct()`, `computeNotionalBudgetUSD()`; no DB imports |
| [`dashboard.ts`](src/lib/dashboard.ts) | `fetchDashboardSummary(ctx)`: parallel DB queries for events-today, active-members, prompts-matched, sparklines (7-day), activity feed; returns `DashboardSummary` |
| [`pnumber-matcher.ts`](src/lib/pnumber-matcher.ts) | `matchPNumber(inputText, candidates)`: Jaccard (primary ≥ 0.6) + Dice bigram secondary (≥ 0.7 when Jaccard ∈ [0.4, 0.6)) — handles character-level drift; `buildFingerprint()`, `tokenize()`, `diceSimilarity()`, `normalizeForDice()`; threshold constants `JACCARD_THRESHOLD`, `DICE_SECONDARY_GATE`, `DICE_SECONDARY_THRESHOLD` |
| [`project-status.ts`](src/lib/project-status.ts) | `deriveStatus(status, lastActivityAt)`: maps DB `ProjectStatus` + last-activity age to display state (`Active` / `Idle` / `Paused` / `Archived`); `IDLE_THRESHOLD_MS = 2h` |
| [`project-verdict.ts`](src/lib/project-verdict.ts) | `computeVerdict(input)`: pure function returning `VerdictResult` (`on_track` / `needs_attention` / `at_risk` / `not_enough_signal`) based on activity (stall), security findings (critical/high/medium), and readiness snapshot state |
| [`project-exceptions.ts`](src/lib/project-exceptions.ts) | `computeExceptionFlags(input)`: pure function returning operational `ExceptionFlag[]` (high risk, cost spike >2× 7-day avg, stall, repo stale >14 days). `groupSecurityFindings(findings)`: groups raw `SecurityFinding` rows by ruleId into `SecurityFindingGroup[]` — each group has a plain-English `label` (from `RULE_LABELS` map or title-cased last dotted segment), de-duped `occurrences[]` (same file+line collapsed), `totalCount` (honest raw count), and highest-severity-wins promotion. INFO findings excluded. Sorted worst-first. `SecurityFindingGroup` type defined here. `securityFindingToExceptionFlag()` still exported for compatibility. |
| [`work-type-bar.ts`](src/lib/work-type-bar.ts) | `computeWorkTypeBuckets(commits)`: aggregates deduplicated commits into bug/docs/build/test/other file-changed counts; heuristic fallback for un-prefixed commits |
| [`feature-area-track.ts`](src/lib/feature-area-track.ts) | `deriveAreaKey`, `computeAreaPhase`, `computeAreaRows`: deterministic area grouping + phase classification (building/stabilising/maturing) from commit-type mix; floor at 3 commits |
| [`activity-rows.ts`](src/lib/activity-rows.ts) | `computeActivityRows(events, limit?)`: filters windowEvents to non-git events with real text (feedSummary ?? manualText), serialises to `ActivityRow[]`; default limit 20 |
| [`prompt-adoption.ts`](src/lib/prompt-adoption.ts) | `computePromptAdoptionSignal(events, todayEvents)`: pure function over DESC-ordered window events — returns `PromptAdoptionSignal` (`matchCount`, `mostRecentTitle`, `mostRecentPNumber`, `windowDistinctCount`, `todayDistinctCount`, `todayMostRecentTitle`); `formatPromptContextPhrase(title)` helper; `WindowEventWithPrompt`, `PromptAdoptionSignal` types |
| [`consentCheck.ts`](src/lib/consentCheck.ts) | `needsConsentModal(userId, teamId)`: returns `true` if team has `timeTrackingEnabled` and user has not acknowledged v2 consent |
| [`presence.ts`](src/lib/presence.ts) | `derivePresence(lastActivityAt)`: returns `"active"` (≤30 min), `"idle"` (≤2h), or `"offline"` |
| [`productive-rules.ts`](src/lib/productive-rules.ts) | Rule evaluation engine; `isProductiveApp(appName, rules)`: evaluates EXACT / GLOB / REGEX patterns against `ProductiveAppRule` records; TEAM rules override GLOBAL |
| [`pulse-body-shape.ts`](src/lib/pulse-body-shape.ts) | `ALLOWED_TIME_BODY_KEYS` allowlist and `assertBodyShape(body)`: CI gate that rejects any time-upload body containing privacy-sensitive keys (window titles, full app lists, URLs) |
| [`sort-project-cards.ts`](src/lib/sort-project-cards.ts) | `sortProjectCards(cards)`: sorts by `lastActivityAt` desc, then name asc for nulls |
| [`pdf-utils.ts`](src/lib/pdf-utils.ts) | `extractSubjectLine(gitSummary)`: strips SHA/metadata lines and returns first commit message subject; `shortPhrase()`, `cleanBodyForPDF()` |
| [`ratelimit.ts`](src/lib/ratelimit.ts) | Upstash Redis sliding-window rate limiter for `/api/ingest/event`; `60/min` at `1x`, `240/min` at `4x`; `getScaleTierMultiplier()` reads `SCALE_TIER` env |
| [`ratelimit-login.ts`](src/lib/ratelimit-login.ts) | Dual-window login rate limiter: `5/min/IP` + `20/hr/IP`; falls back to in-memory when Upstash is not configured |
| [`ratelimit-time.ts`](src/lib/ratelimit-time.ts) | Upstash rate limiter for `/api/ingest/time`: `30/min` per token key |
| [`ratelimit-github.ts`](src/lib/ratelimit-github.ts) | Upstash rate limiter for GitHub repos endpoint: `30/min/user` |
| [`ratelimit-readiness.ts`](src/lib/ratelimit-readiness.ts) | Upstash rate limiter for `POST /api/projects/[id]/readiness/scan`: `1/60s` per projectId |
| [`ratelimit-code-health.ts`](src/lib/ratelimit-code-health.ts) | `checkCodeHealthScanRateLimit(projectId)` — Upstash sliding-window 1/120s per projectId; prefix `pulse:code-health:scan` |
| [`ratelimit-security-scan.ts`](src/lib/ratelimit-security-scan.ts) | `checkSecurityScanRateLimit(projectId)` — Upstash sliding-window 1/120s per projectId; prefix `pulse:security:scan`. Fail-open on Upstash errors. |
| [`ratelimit-drift.ts`](src/lib/ratelimit-drift.ts) | `checkDriftRateLimit(projectId)` — in-memory sliding-window 3/hr per projectId; Upstash-upgradeable; `_resetDriftRateLimitStore()` for tests |
| [`ratelimit-debt-scan.ts`](src/lib/ratelimit-debt-scan.ts) | `checkDebtScanRateLimit(projectId)` — Upstash sliding-window 1/30min per projectId; prefix `pulse:debt-scan`; fail-open on Upstash errors |
| [`ratelimit-admin-key.ts`](src/lib/ratelimit-admin-key.ts) | `checkAdminKeyRateLimit(userId)` — Upstash sliding-window 5/min per userId; prefix `pulse:admin:org-key`; fail-open on Upstash errors; bypasses in `NODE_ENV=test` |
| [`drift/orchestrate.ts`](src/lib/drift/orchestrate.ts) | Drift orchestrator. `triggerAssessment(projectId, orgId, triggeredBy)` — creates PENDING record, runs pipeline async. `runAssessmentPipeline()` — full pipeline. `incrementVolumeCounter` / `resetVolumeCounter` — per-project ingest event counter (VOLUME_THRESHOLD=50 → auto-trigger). `resetStaleRunningAssessments()` — sets RUNNING→ERROR for assessments stuck >STALE_RUNNING_MS (5 min). `_resetDriftGuards()` for tests. DRIFT_COOLDOWN_MS=30 min in-process per projectId. |
| [`debt/orchestrate.ts`](src/lib/debt/orchestrate.ts) | `triggerDebtScan(projectId, orgId)` — creates PENDING record + fires async pipeline; duplicate guard blocks if PENDING/RUNNING exists. `runDebtScanPipeline(scanId)` — real Phase B engine: project lookup → GitHub guard → cross-tenant installation guard → concurrency slot → DOWNLOADING → download+extract → SONAR → SonarQube scan → SYNTHESISING (stores sonar fields, findings/debtScore stay null until Phase D) → COMPLETE; finally: releaseScanSlot + deleteTmpdir. `resetStaleRunningDebtScans()` — sets RUNNING→ERROR for scans stuck >15 min. |
| [`debt/engines.ts`](src/lib/debt/engines.ts) | `downloadAndExtract(project)` — creates tmp dir, downloads GitHub tarball via `downloadRepoTarball`, extracts; returns `{ tmpDir, srcDir }`. `runSonarEngine(srcDir, project)` — provisions SonarQube project (`debt-{orgId}-proj-{projId}` key), runs scanner, waits for CE, fetches metrics + issues, returns `SonarEngineResult` with ratings/techDebtMinutes/issueCount/criticalCount(BLOCKER)/highCount(CRITICAL). `deleteTmpdir(tmpDir)` — `rmSync` recursive+force. |
| [`drift/assess-diff.ts`](src/lib/drift/assess-diff.ts) | `assessDiff(projectId, organisationId, triggeredBy)` — resolves context source, compares GitHub commits against baseline SHA, creates `ContextDriftAssessment` record. BASELINE_INVALID: writes ERROR record; never auto-resets baseline. |
| [`drift/analyse-ai.ts`](src/lib/drift/analyse-ai.ts) | AI analysis via Groq (ai-provider.ts). `analyseAiDrift(projectId, orgId, assessmentId, diff)` — sends diff to LLM, returns structured `DriftFinding[]`. Type: `DriftFinding { type: ACCURACY\|COVERAGE, area, doc, description, severity: LOW\|MEDIUM\|HIGH, confidence }` |
| [`drift/compute-risk.ts`](src/lib/drift/compute-risk.ts) | `computeRiskLevel(findings)` → `{ riskLevel: DriftRiskLevel, counts, total }`. RED: any HIGH or ≥4 MEDIUM. AMBER: 1–3 MEDIUM. GREEN: no HIGH or MEDIUM. |
| [`drift/capture-baseline.ts`](src/lib/drift/capture-baseline.ts) | `captureBaseline(projectId, organisationId)` — resolves context source via `drift-github.ts` and writes `contextBranchBaselineSha` to `Project`. |
| [`drift/context-status.ts`](src/lib/drift/context-status.ts) | `deriveDisplaySource(lastCompleteContextSource, hasGithubRepo)` — resolves effective source for display. `contextSourceLabel(source)` — human-readable label for `ContextSource` value. |
| [`drift/baseline-handler.ts`](src/lib/drift/baseline-handler.ts) | Client-side response handlers. `processBaselineResponse(status, body)` — maps HTTP status/body to banner + shouldRefresh. `isMarkRefreshedDisabled(submitting, source)` — disable guard for the "Mark Refreshed" button. |
| [`code-health.ts`](src/lib/code-health.ts) | Pure: `numericRatingToLetter`, `parseQualityGate`, `worstRating`. I/O: `fetchSonarMetrics`, `runSonarScanner`, `downloadRepoTarball`, `extractTarball`, `ensureSonarProject`. Semaphore: `tryAcquireScanSlot`, `releaseScanSlot` (max 2 concurrent). Boot-time cleanup IIFE removes stale `/tmp/pulse-scan-*` and `/tmp/pulse-sec-scan-*` dirs older than 30 minutes. Types: `RatingLetter`, `QualityGate`, `SonarMetrics` |
| [`security-scan.ts`](src/lib/security-scan.ts) | Pure parsers: `parseSemgrepOutput`, `parseGitleaksOutput`, `parseOsvScannerOutput`. CLI runners: `runSemgrep(srcDir)`, `runGitleaks(srcDir)`, `runOsvScanner(srcDir)`. Orchestrator: `runAllSecurityTools(srcDir, tempDir)` — runs all three tools, catches individual tool failures (missing CLI = 0 findings), then strips the temp-dir prefix from all `file` fields via `stripSrcPrefix(filePath, srcDir)` so the DB stores repo-relative paths only. Types: `SecuritySeverity` (CRITICAL/HIGH/MEDIUM/LOW/INFO), `SecurityFindingData`, `SEVERITY_WEIGHT` map (critical:5, high:4, medium:3, low:2, info:1). |
| [`readiness.ts`](src/lib/readiness.ts) | Pure types + OLS forecast + I/O scanner. Exports: `countMarkersInContent`, `sumMarkerDetail`, `computeForecast`, `buildReadinessSignal`, `scanMarkersInDir`, `readCoveragePct`, `FORECAST_MIN_SNAPSHOTS`. Types: `MarkerDetail`, `SnapshotForForecast`, `ForecastResult`, `ReadinessSignal` |
| [`status-ratelimit.ts`](src/lib/status-ratelimit.ts) | In-memory rate limiter for `POST /api/status`: `30/min/user` |
| [`summary-ratelimit.ts`](src/lib/summary-ratelimit.ts) | In-memory rate limiters for summary (`10/hr/project` × scale tier) and export (`20/hr` × scale tier) |
| [`ratelimit-teams-patch.ts`](src/lib/ratelimit-teams-patch.ts) | Rate limiter for `PATCH /api/teams/:id` |
| [`ratelimit-productive-rules.ts`](src/lib/ratelimit-productive-rules.ts) | Rate limiter for productive rules API |
| [`ratelimit-users-time.ts`](src/lib/ratelimit-users-time.ts) | Rate limiter for user time data endpoints |
| [`repo-context-ratelimit.ts`](src/lib/repo-context-ratelimit.ts) | Rate limiter for repo context refresh |
| [`repo-context/index.ts`](src/lib/repo-context/index.ts) | `refreshRepoContext(projectId)`: orchestrates GitHub metadata fetch + snapshot generation; marks project `REFRESHING` → `LINKED` or `ERROR` |
| [`repo-context/snapshot.ts`](src/lib/repo-context/snapshot.ts) | `generateSnapshot()`: fetches repo file tree + contents of `KEY_CONFIG_ALLOWLIST` files (package.json, tsconfig.json, Dockerfile, etc.) via GitHub API; redacts secrets; returns `RepoSnapshot` |
| [`repo-context/client.ts`](src/lib/repo-context/client.ts) | GitHub App authentication; `createAppJWT()` (RS256 signed), `getInstallationToken()` (cached 60 min), `authedGithubFetch()` |
| [`repo-context/drift-github.ts`](src/lib/repo-context/drift-github.ts) | GitHub diff helpers for drift detection. `ContextSource = "context_builds" \| "docs_on_default" \| "none"`. `resolveContextSource(installationId, fullName, defaultBranch)` — checks if `context_builds` branch exists. `compareCommits(installationId, fullName, base, head)` — GitHub Compare API. `branchExists()`, `getRecursiveTree()`, `getLatestCommitSha()`. |
| [`utils.ts`](src/lib/utils.ts) | `cn(...inputs)`: `clsx` + `tailwind-merge` className utility |
| [`withAuthScoped.ts`](src/lib/withAuthScoped.ts) | (listed above) |
| [`src/lib/tour/types.ts`](src/lib/tour/types.ts) | `TourRole`, `TourStep`, `TourAdvanceMode`, `EngineState`, `EngineAction` — all types for the onboarding tour engine |
| [`src/lib/tour/cookie.ts`](src/lib/tour/cookie.ts) | `readTourCookie()`, `writeTourCookie(id)`, `clearTourCookie()` — step persistence for `pulse-tour-step` cookie. `readTourKindCookie()`, `writeTourKindCookie(kind)`, `clearTourKindCookie()` — tour-mode persistence for `pulse-tour-kind` cookie (`"first-run"` \| `"feature"`). |
| [`src/lib/tour/filter.ts`](src/lib/tour/filter.ts) | `filterSteps(steps, role, tourMode, ctx)` — filters on role, `availableIn` (first-run / feature / both), and `skipIf(ctx)` predicate |
| [`src/lib/tour/reducer.ts`](src/lib/tour/reducer.ts) | `tourReducer(state, action)` — pure state machine for tour engine transitions |
| [`src/lib/tour/steps.ts`](src/lib/tour/steps.ts) | `TOUR_STEPS` — 21-step dual-tour inventory (Phase 5). 9 first-run-only steps (welcome → project-open creation flow), 2 feature-only steps (feature-welcome, feature-nav-project), 10 shared steps (nav-prompts → done). Steps carry `roles`, `availableIn`, `routePrefix`, `pollTimeout`, optional `stub`, and optional `skipIf(ctx)` predicate. |

---

### `src/components/` — UI Components

| Component | Description |
|---|---|
| [`AppShell.tsx`](src/components/AppShell.tsx) | Server component; fetches org name AND caller's memberships in parallel (`Promise.all`); exports `MembershipOption` shared type; passes `orgName`, `activeOrganisationId`, `memberships` to `AppShellClient`. PM4. |
| [`AppShellClient.tsx`](src/components/AppShellClient.tsx) | Client component; full sidebar navigation (210px width); role-aware nav links (Dashboard, Teams, Prompts, Install, Admin sections for MANAGER/LINE_MANAGER); theme toggle; avatar with initials and role label; renders `<OrgBadge>` for the org chip. Wraps children in `<TourProvider>` for the onboarding tour engine. Teams NavLink wrapped in `data-tour="nav-teams"` div (Phase 5). |
| [`tour/TourContext.ts`](src/components/tour/TourContext.ts) | `TourContext`, `useTour()` — React context for tour engine |
| [`tour/TourOverlay.tsx`](src/components/tour/TourOverlay.tsx) | 4-sided dim overlay with spotlight cutout and teal ring; `pointer-events: none` on spotlight so real target stays clickable |
| [`tour/TourTooltip.tsx`](src/components/tour/TourTooltip.tsx) | Tooltip card: step counter (IBM Plex Mono), instruction, Skip / Next buttons; positioned below/above target, clamped to viewport |
| [`tour/TourProvider.tsx`](src/components/tour/TourProvider.tsx) | Full tour engine: `useReducer` state machine, DOM polling (200 ms / 3 s timeout), advance detection, `PATCH /api/me/onboarding` on complete/skip, portal rendering. Phase 5: reads `pulse-tour-kind` cookie to determine first-run vs feature mode; passes `(steps, role, tourMode, ctx)` to `filterSteps`; handles `element-appears` advance mode via DOM polling; clears `pulse-tour-kind` cookie on exit. |
| [`OrgBadge.tsx`](src/components/OrgBadge.tsx) | PM4. Client component. Single-membership users render the bare org chip (no affordance). Multi-membership users get a chevron + dropdown listbox with active row marker, Escape/click-outside dismissal. Selecting POSTs `/api/auth/switch-org` and on `res.ok` calls `router.refresh()` — never optimistic local state (cookie is the only source of truth). 401 → `router.push("/login")`; 403 → "Not a member"; other → "Switch failed". |
| [`AppShellSignOut.tsx`](src/components/AppShellSignOut.tsx) | Client component; sign-out button that calls NextAuth `signOut` |
| [`TrackingConsentModal.tsx`](src/components/TrackingConsentModal.tsx) | Client component; modal shown when `needsConsentModal()` returns true; posts to `/api/consents/acknowledge`; explains time tracking data collection scope |
| [`pdf/SummaryPDF.tsx`](src/components/pdf/SummaryPDF.tsx) | `@react-pdf/renderer` document component; renders executive summary PDF with stage labels, member time stats, git activity |
| [`ui/auth-left-panel.tsx`](src/components/ui/auth-left-panel.tsx) | Left panel used on login/signup pages (branding, animated elements) |
| [`ui/auth-dot-wave.tsx`](src/components/ui/auth-dot-wave.tsx) | Animated dot-wave used in the auth left panel |
| [`ui/blur-text-animation.tsx`](src/components/ui/blur-text-animation.tsx) | Text blur-in animation component |
| [`ui/button.tsx`](src/components/ui/button.tsx) | shadcn/ui button primitive with `class-variance-authority` variants |
| [`ui/card.tsx`](src/components/ui/card.tsx) | shadcn/ui card primitive |
| [`ui/form.tsx`](src/components/ui/form.tsx) | shadcn/ui form primitives (react-hook-form integration) |
| [`ui/input.tsx`](src/components/ui/input.tsx) | shadcn/ui input primitive |
| [`ui/label.tsx`](src/components/ui/label.tsx) | shadcn/ui label primitive (`@radix-ui/react-label`) |
| [`ui/EmptyState.tsx`](src/components/ui/EmptyState.tsx) | Empty state placeholder component |
| [`ui/LoadingSkeleton.tsx`](src/components/ui/LoadingSkeleton.tsx) | Loading skeleton placeholder |
| [`ui/risk-badge.tsx`](src/components/ui/risk-badge.tsx) | `RiskBadge` component; renders MED/HIGH risk chips with colour-coded border/background; returns null for LOW |

---

### `src/tests/` — Test Suite

All tests use **Vitest** with module mocking (`vi.mock`). Tests run against the API route handlers directly without a live server.

| Test file | What it covers |
|---|---|
| `admin-budget.test.ts` | Per-project developer token budget CRUD (`/api/admin/budget`) |
| `agent-token.test.ts` | Per-developer agent token lifecycle: create, revoke, restore, cross-project isolation |
| `audit-actions.test.ts` | `writeAudit()` writes correct records for each action type |
| `audit-route.test.ts` | `GET /api/admin/audit` filtering, pagination, RBAC gating |
| `cleanup.test.ts` | `POST /api/admin/cleanup` nulls/deletes correct rows by age cutoff |
| `consent.test.ts` | `needsConsentModal()` logic, `POST /api/consents/acknowledge` |
| `dashboard-summary.test.ts` | `fetchDashboardSummary()` query structure and data shaping |
| `dev-cost.test.ts` | `getProjectDailySpendUSD()`, token aggregation, multi-model pricing |
| `events-pnumber.test.ts` | `PATCH /api/events/[id]/p-number` override |
| `executive-summary-api.test.ts` | `POST /api/projects/[id]/summary` streaming, audit log, RBAC |
| `executive-summary-ratelimit.test.ts` | Summary and export rate limiter enforcement |
| `feed-summary.test.ts` | `generateFeedSummary()` Groq call and fallback |
| `framework-detector.test.ts` | `generateSnapshot()` framework detection from repo file tree |
| `git-rail.test.ts` | Git activity rail data shaping |
| `github-multi-installation.test.ts` | Multiple GitHub App installations per org |
| `ingest-idempotency.test.ts` | `sourceMessageUuid` dedup on `POST /api/ingest/event` |
| `ingest-narration.test.ts` | Narration trigger logic in the ingest pipeline |
| `ingest-time-user-token.test.ts` | Time ingestion with `UserToken` auth path |
| `ingest-user-attribution.test.ts` | `userIdHint` email attribution on ingest |
| `install-script.test.ts` | `GET /api/install/script` returns valid shell script |
| `invite-accept.test.ts` | Invitation acceptance: new user, existing user, expired invite |
| `logger-pii.test.ts` | Logger PII redaction field list |
| `login.test.ts` | `POST /api/auth/login`: valid creds, wrong password, lockout. PM4: HTTPS branch emits `__Secure-` prefix + `Secure` attribute (prod path behind Coolify HTTPS). |
| `memberships-api.test.ts` | PM4. `GET /api/auth/memberships`: 401 no session, caller-only 200, enumeration-guard (`?userId=u-bob` ignored), structural forge guard (reads route source from disk; pins absence of `new URL(`, `searchParams`, `nextUrl`, `next/headers` import, `headers()/cookies()/draftMode()` calls, any GET parameter, request-scoped `headers/json/text/formData`). Sanity-checked by injecting bypasses — test fails on each. |
| `switch-org.test.ts` | PM4. `POST /api/auth/switch-org`: 401 no session, 400 invalid JSON, 400 missing org, 429 rate-limited, 200 happy (Set-Cookie + Max-Age=2592000 + HttpOnly + SameSite=Lax + no Secure on HTTP), JWT decode pins `sub`/`activeOrganisationId`/`sessionVersion` and asserts `role`/`teamId`/`isLineManager` are `undefined`, HTTPS branch emits `__Secure-` prefix + `Secure` attribute. |
| `pm4-forge-switch-cross-org.test.ts` | PM4 FORGE TEST. Caller member of org-A only; POSTs `{ organisationId: "org-Z" }` → 403, no Set-Cookie. Composite-key assertion verifies `userId: ctx.userId` (not from body). Sanity-checked: with `auth()` mocked (so session is present), stripping `if (!membership) return 403` lets the route reach `encode()` and emit a Set-Cookie for the forged org — assertion catches `expected 200 to be 403`. Same forge bar as PM3. |
| `pm5-invite-creates-pending-membership.test.ts` | PM5: Inviting an existing user creates a PENDING Membership + Invitation atomically; duplicate invite returns 409 with `reason: "already_a_member"` or `reason: "invitation_already_pending"`. |
| `pm5-forge-pending-no-access.test.ts` | PM5 FORGE TEST. User with PENDING membership → `withAuthScoped` returns null → 401 on any protected route. Empirically verified to fail when the status gate is removed from `withAuthScoped`. |
| `pm5-forge-pending-no-switch.test.ts` | PM5 FORGE TEST. `POST /api/auth/switch-org` with a PENDING membership → 403, no Set-Cookie. Verified to fail when the status gate is bypassed. |
| `pm5-members-route-invite.test.ts` | PM5 fix. `POST /api/admin/members`: inviting an existing user creates PENDING Membership + Invitation atomically via `$transaction`; ACTIVE Membership → 409 `already_a_member`; PENDING Membership → 409 `invitation_already_pending`; new-email path skips the transaction and calls `invitation.create` directly. LINE_MANAGER path verified (teamId comes from `ctx.teamId`, not body). 5 tests. |
| `machine-script.test.ts` | `GET /api/install/machine-script` returns valid script |
| `member-commits.test.ts` | Member commit history in project detail |
| `member-events-api.test.ts` | `GET /api/projects/[id]/members/[userId]/events` |
| `member-card.test.ts` | `getMemberCard()` lib — identity, spend (with/without), time (v2/v1/v0), projects, sessions, commits, empty-state |
| `membership-backfill.test.ts` | PM2 backfill assertions against real local DB: `Membership.count() === User.count()`, field parity on `(organisationId, role, teamId, isLineManager)`, exactly one Membership per User for current org — 3 tests |
| `membership-cascade.test.ts` | PM2 cascade — deleting a `User` removes their `Membership` rows; runs inside a rolled-back transaction so no real data is mutated — 1 test |
| `pm3-forge-tampered-jwt.test.ts` | PM3 forge test (c) — JWT tampered to claim membership in an org the user is NOT a member of → `withAuthScoped` returns null → 401. Empirically verified to fail when the membership gate is bypassed — 2 tests |
| `pm3-forge-cross-org-resource.test.ts` | PM3 forge test (a) — user is a member of orgs A+B, active=B, requests an A resource → 404 because the route filters by `ctx.organisationId`. Empirically verified to fail when the org filter is dropped — 2 tests |
| `pm3-forge-header-ignored.test.ts` | PM3 forge test (b) — defensive trip-wire: recursive grep over src/ + `request.headers.get` scan over API routes. Empirically verified to fail when `x-active-org` is added anywhere — 2 tests |
| `pm3-forge-revoked-mid-session.test.ts` | PM3 forge test (d) — mid-session revocation via sessionVersion bump OR Membership deletion. Empirically verified to fail when the drift gate is disabled — 3 tests |
| `pm3-data-plane-listing.test.ts` | PM3 Phase 2. `GET /api/admin/members` reads from `Membership(status=ACTIVE)`, not `User.organisationId`. Asserts `membership.findMany` is called with `status:"ACTIVE"` and that `role` in the response comes from the Membership row, not the User row. LINE_MANAGER path additionally asserts `teamId` filter. MEMBER role → 403. 3 tests. |
| `pm3-last-manager-guard.test.ts` | PM3 Q21 forge test. Mock intentionally omits `db.user.count` — any call to it throws. Proves that the Q21 last-manager guard in `PATCH /role` and `POST /demote` calls `membership.count({ where: { role:"MANAGER", status:"ACTIVE", NOT:{userId} } })`, not `user.count`. 4 tests. |
| `pm3-member-management-membership.test.ts` | PM3 Phase 3. Asserts that `role/promote/demote/assign-to-team/remove-from-team/PATCH[id]` write `role`/`teamId`/`isLineManager` to `Membership` only — none of those fields are passed to `db.user.update`. `User.sessionVersion` increment is still allowed. Covers all 5 management routes + `PATCH [id]` teamId path. Q21 guard also verified for `role` and `demote`. 8 tests. |
| `member-card-route.test.ts` | `GET /api/admin/members/[id]/card` — tenancy proofs: cross-org 404, LINE_MANAGER cross-team 403, canSeeSpend server-derived, no-spend passthrough |
| `members-admin.test.ts` | Member management CRUD routes, role enforcement |
| `multi-tenant-fuzz.test.ts` | Cross-tenant isolation: org-ID scoping on all queries |
| `narrate-repo-context.test.ts` | Narration with repo snapshot enrichment |
| `narrate-time-enrichment.test.ts` | Narration with time-tracking data enrichment |
| `narrate.test.ts` | `generateNarration()` cooldown, delta gating, structured output |
| `password.test.ts` | `validatePassword()` rules, `hashPassword()` / `verifyPassword()` |
| `pdf-utils.test.ts` | `extractSubjectLine()`, `shortPhrase()`, `cleanBodyForPDF()` |
| `phase7-hardening.test.ts` | P7 hardening: cross-tenant block, redaction on manual status |
| `pnumber-matcher.test.ts` | Jaccard similarity matching, `buildFingerprint()`, `tokenize()` |
| `prompt-adoption.test.ts` | `computePromptAdoptionSignal` — match count, recency-based most-recent title, null-prompt-relation (deleted prompt) edge case |
| `presence.test.ts` | `derivePresence()` threshold boundaries |
| `productive-rules-api.test.ts` | `POST /api/productive-rules`, `PATCH /api/productive-rules/[id]` |
| `productive-rules.test.ts` | `isProductiveApp()`: EXACT, GLOB, REGEX patterns, scope precedence |
| `profile-change-password.test.ts` | `POST /api/profile/change-password` |
| `profile-update.test.ts` | `PATCH /api/profile/update` |
| `project-card-status.test.ts` | `deriveStatus()` logic |
| `project-daily-cost.test.ts` | `getProjectDailySpendUSD()` aggregation |
| `project-edit-preservation.test.ts` | Project PATCH preserves unmodified fields |
| `project-exceptions.test.ts` | `computeExceptionFlags()` all flag conditions |
| `project-verdict.test.ts` | `computeVerdict()` all verdict conditions |
| `prompts.test.ts` | Prompt CRUD, fingerprint dedup |
| `pulse-time-body-shape.test.ts` | `assertBodyShape()` allowlist enforcement |
| `pulse-time.test.ts` | Full `POST /api/ingest/time` pipeline |
| `rate-limits.test.ts` | Ingest event rate limiter |
| `ratelimit-refresh.test.ts` | Rate limiter store reset utilities |
| `rbac.test.ts` | Role-based access control across multiple routes |
| `redact-parity.test.ts` | TypeScript `redact.ts` and ESM `lib/redact.mjs` produce identical output |
| `redact.test.ts` | `redact()` all pattern types (env, JWT, sk-ant, sk, aws-key, PEM, url-creds) |
| `repo-context-api.test.ts` | `POST /api/projects/[id]/repo-context/refresh` |
| `readiness.test.ts` | `countMarkersInContent`, `computeForecast` (all edge cases), `buildReadinessSignal`, `scanMarkersInDir` and `readCoveragePct` (mocked fs) — 46 tests |
| `readiness-api.test.ts` | `GET /api/projects/[id]/readiness` and `POST /api/projects/[id]/readiness/scan` — auth, RBAC, rate limit, happy-path — 14 tests |
| `code-health.test.ts` | Pure function + `fetchSonarMetrics` + central scan lib (`downloadRepoTarball`, `extractTarball`, `ensureSonarProject`, semaphore) — 52 tests |
| `code-health-api.test.ts` | GET + POST route (EDGE + CENTRAL path, multi-tenancy proof, semaphore, role gate) — 25 tests |
| `security-scan.test.ts` | Parsers (`parseSemgrepOutput`, `parseGitleaksOutput`, `parseOsvScannerOutput`) + CLI runners + orchestrator (`runAllSecurityTools`) including `stripSrcPrefix` path-normalisation tests — 43 tests |
| `security-findings-display.test.ts` | `groupSecurityFindings()` — 15 tests covering empty input, INFO filtering, ruleId grouping, de-dup (same file+line), highest-severity promotion, worst-first sort, known rule labels (pickle, generic-api-key, urllib, missing-integrity), osv-scanner label, unknown rule title-casing, null-ruleId fallback key |
| `security-scan-api.test.ts` | `POST /api/projects/[id]/security-scan` and `GET /api/projects/[id]/security-findings` (auth, RBAC, rate limit, happy-path, scanState logic) — 21 tests |
| `repo-context-ratelimit.test.ts` | Repo context refresh rate limiting |
| `session-version.test.ts` | `withAuthScoped()` session version drift detection |
| `signup.test.ts` | `POST /api/auth/signup` password policy, email uniqueness |
| `sort-project-cards.test.ts` | `sortProjectCards()` ordering |
| `status.test.ts` | `POST /api/status` manual status: redaction, p-number match, rate limit |
| `team-project-crud.test.ts` | Team and project CRUD routes |
| `test-routes-gated.test.ts` | `/api/__test/throw-error` → `/api/internal-test/throw-error` rewrite |
| `time-api-top-apps.test.ts` | `topApps` storage on `POST /api/ingest/time` (v2 consent gate) |
| `time-ingest.test.ts` | Full `POST /api/ingest/time` pipeline end-to-end |
| `token-grace.test.ts` | `verifyTokenWithGrace()` — grace-window agent token rotation |
| `transcript-delta-read.test.ts` | Transcript delta reading in the ingest flow; includes 4 session timestamp extraction tests (cursor-scoped, 3-firing no-double-span) |
| `session-duration-ingest.test.ts` | `sessionDurationSeconds` stored correctly; re-ingest same `sourceMessageUuid` is no-op (session time does NOT double); `MemberDailyTime` never touched |
| `session-time.test.ts` | `getProjectSessionSeconds` aggregate query; tenancy isolation; null-sum returns 0 |
| `user-token.test.ts` | `UserToken` generation, rotation, and `resolveUserToken()` |
| `drift-compute-risk.test.ts` | `computeRiskLevel()` thresholds — GREEN/AMBER/RED boundaries (empty, LOW-only, MEDIUM 1/3/4+, HIGH); AC5: zero findings always GREEN |
| `drift-orchestrate.test.ts` | `triggerAssessment()` + `incrementVolumeCounter()` + `resetStaleRunningAssessments()` + DRIFT_COOLDOWN_MS + VOLUME_THRESHOLD |
| `drift-analyse-ai.test.ts` | `analyseAiDrift()` — Groq call, structured output parsing, cost ceiling gate, token cost tracking |
| `drift-assess-diff.test.ts` | `assessDiff()` — source resolution, commit comparison, BASELINE_INVALID path, creates ContextDriftAssessment |
| `drift-capture-baseline.test.ts` | `captureBaseline()` — source resolution, `contextBranchBaselineSha` write, no-repo-link path |
| `drift-github.test.ts` | `resolveContextSource()`, `branchExists()`, `compareCommits()`, `getLatestCommitSha()` — GitHub API mocks |
| `drift-context-status.test.ts` | `deriveDisplaySource()` and `contextSourceLabel()` — all source variants and no-GitHub fallback |
| `drift-baseline-handler.test.ts` | `processBaselineResponse()` and `isMarkRefreshedDisabled()` — all HTTP status/reason combinations |
| `drift-ratelimit.test.ts` | `checkDriftRateLimit()` — in-memory window: 3/hr per project; cross-project isolation |
| `drift-trigger-routes.test.ts` | `POST /api/projects/[id]/drift` (trigger, rate-limit, CONTEXT_ASSESS audit, RBAC) and `GET` (list assessments) — all roles |
| `drift-baseline-route.test.ts` | `POST /api/projects/[id]/drift/baseline` — source resolution, SHA write, CONTEXT_BASELINE_SET audit, RBAC; LINE_MANAGER path |
| `drift-assessment-get.test.ts` | `GET /api/projects/[id]/drift/[assessmentId]` — triple-scope (project + org + assessmentId), stale-reset side-effect, 404 cross-org |
| `drift-phase6-audit-reset.test.ts` | Phase 6 integration: baseline reset (manual + auto), CONTEXT_BASELINE_SET audit writes, stale-RUNNING→ERROR transitions |
| `debt-engines.test.ts` | `downloadAndExtract` (tmpDir creation, tarball path, HEAD fallback, error propagation) + `runSonarEngine` (env guard, per-project key, CE outcome handling, BLOCKER/CRITICAL severity mapping, null techDebtMinutes) + `deleteTmpdir` — 24 tests |
| `debt-orchestrate.test.ts` | `triggerDebtScan` + `resetStaleRunningDebtScans` + `runDebtScanPipeline` (early-exit guards: scan-not-found, project-not-found, github_not_configured, github_installation_not_found, scan_capacity_exceeded; cross-tenant guard uses scan.organisationId; engine error paths; happy-path step transitions; findings/debtScore NOT stored; finally always releases slot + deletes tmpDir) — 24 tests |
| `activity-rows.test.ts` | `computeActivityRows()` — maps ActivityEvent array to display rows; hookSource, feedSummary/manualText precedence, null user |
| `ai-provider.test.ts` | `getAutoCallModel()` and `OPENROUTER_MODELS` — OpenRouter chain selection, Groq fallback when key absent |
| `budget-today-cutoff.test.ts` | `parseTodayCutoff()` — timezone-aware "today" window from budget page searchParams; Dubai/UTC boundary tests |
| `code-health-poller.test.ts` | `pollForNewerSnapshot()` — client-side polling loop; fetch mocking; snapshot freshness checks |
| `completion-status-widget.test.ts` | `formatSessionTime()` and `getCompletionCells()` — session time formatting and completion cell computation |
| `feature-area-track.test.ts` | `deriveAreaKey()`, `computeAreaPhase()`, `computeAreaRows()` — commit-based feature area tracking |
| `member-card-fetch.test.ts` | `fetchMemberCard()` client-side fetch helper — HTTP status handling, 401/403/404 paths |
| `narrate-highlights.test.ts` | `filterHighlights()` — validates sourceEventId presence, rejects non-array input, deduplicates |
| `project-time-window.test.ts` | `resolveTimeWindow()` — timezone-aware time window resolution; Dubai/UTC boundary |
| `work-type-bar.test.ts` | `computeWorkTypeBuckets()` — classifies commits into bug/docs/build/test/feature buckets |
| `tour-engine.test.ts` | Cookie utilities, `filterSteps`, `tourReducer` transitions, `TOUR_STEPS` structure — all pure lib layer; 28 tests |
| `tour-steps.test.ts` | `TOUR_STEPS` inventory (25 steps, unique IDs, sentinel selectors), `filterSteps` per role/mode (first-run MANAGER 19, first-run LINE_MANAGER 16, feature MANAGER with-data 13, feature MANAGER no-data 20, feature LINE_MANAGER with-data 13, feature LINE_MANAGER no-data 17, MEMBER 0), `availableIn` classification, `skipIf` predicate evaluation, stub conditions, `routePrefix` coverage, `project-open` navigate-advance, `pollTimeout` values, `element-appears` advance mode |

---

## `prisma/` — Database Layer

### `schema.prisma`

Prisma client generated to `../src/generated/prisma`; datasource is PostgreSQL.

**Enums**: `Role` (MANAGER / LINE_MANAGER / MEMBER), `ProjectStatus` (ACTIVE / PAUSED / ARCHIVED), `EventKind` (CLAUDE_HOOK / MANUAL_STATUS), `MatchType` (EXACT / GLOB / REGEX), `RuleScope` (GLOBAL / TEAM), `RepoContextStatus` (NONE / LINKED / REFRESHING / ERROR), `InvitationStatus` (PENDING / ACCEPTED / DECLINED — DECLINED added in PM5), `MembershipStatus` (PENDING / ACTIVE — added in PM5), `GithubInstallationStatus` (ACTIVE / INVALID), `SecuritySeverity` (CRITICAL / HIGH / MEDIUM / LOW / INFO), `ScanSource` (CENTRAL / EDGE), `DriftAssessmentStatus` (PENDING / RUNNING / COMPLETE / ERROR), `DriftTriggerSource` (ON_DEMAND / VOLUME / MAJOR_EVENT / SYSTEM), `DriftRiskLevel` (GREEN / AMBER / RED)

**Models**:

| Model | Key fields |
|---|---|
| `Organisation` | id, name; root tenant entity |
| `User` | id, email (unique), name, passwordHash, role, teamId?, isLineManager, isActive, failedLogins, lockedUntil, sessionVersion, bio, jobTitle, location, tenantKey, organisationId |
| `Team` | id, name, description, timeTrackingEnabled, aiUsesTime, tenantKey, organisationId |
| `Project` | id, name, status, teamId, agentTokenHash/Preview (legacy), devTokenBudget, githubRepoFullName, githubInstallationId, repoMetadata/Snapshot (JSON), repoContextStatus/Error, contextBranchBaselineSha (baseline SHA for drift), tenantKey, organisationId |
| `Prompt` | id, pNumber (unique per org), title, category, body, fingerprint, isActive, createdBy, organisationId |
| `ActivityEvent` | id, projectId, userId?, kind, pNumberDetected?, sessionExcerpt, filesChanged[], gitSummary, gitCommitSha, manualText, feedSummary, redactionCount, claudeInputTokens, claudeOutputTokens, claudeCacheCreateTokens, claudeCacheReadTokens, claudeModel, claudeSpendUSD, sourceMessageUuid (dedup key), organisationId, ingestedAt |
| `Intelligence` | id, projectId, triggeringEventId, inputHash (dedup), headline, narration, stage, riskLevel, riskFocus, modelUsed, inputTokens, outputTokens, organisationId, generatedAt |
| `AuditLogEntry` | id, userId?, action, subjectId?, meta (JSON), ipAddress, organisationId, at |
| `ProjectMember` | composite PK (projectId, userId) |
| `TimeTrackingConsent` | id, userId (unique), notifiedAt, acknowledgedAt?, consentVersion (1=seconds only, 2=includes top-app names) |
| `MemberDailyTime` | id, userId, day, timezone, workedSeconds, productiveSeconds, unproductiveSeconds, idleSeconds, offlineSeconds, topApps (JSON), source, organisationId; unique (userId, day) |
| `ProductiveAppRule` | id, pattern, matchType, category, isProductive, scope, teamId?, isActive, createdBy, organisationId |
| `ExecutiveSummary` | id, projectId, body, confidence?, generatedBy?, modelUsed, inputTokens, outputTokens, organisationId, generatedAt |
| `Membership` | id, userId, organisationId, role, teamId?, isLineManager, status (MembershipStatus @default(ACTIVE) — PM5), createdAt, updatedAt; unique (userId, organisationId) |
| `Invitation` | id, invitedEmail, teamId?, role, status (InvitationStatus — includes DECLINED since PM5), invitedBy, organisationId |
| `AgentToken` | id, projectId, userId? (null = legacy), createdById?, label, tokenHash (bcrypt), tokenPreview (last 4), revokedAt? |
| `UserToken` | id, userId (unique), organisationId, tokenHash, tokenPreview, tenantKey |
| `GithubInstallation` | id, organisationId, installationId, accountName, status; unique (organisationId, installationId) |
| `SecurityScanRun` | id, projectId, organisationId, scannedAt, scanSource (ScanSource), toolsRun (JSON), findingCount |
| `SecurityFinding` | id, scanRunId, projectId, organisationId, tool, ruleId?, severity (SecuritySeverity), message, file?, line? |
| `ContextDriftAssessment` | id, projectId, organisationId, tenantKey, status (DriftAssessmentStatus), triggeredBy (DriftTriggerSource), contextSource, baselineSha?, headSha?, changedFiles[], diffTruncated, healthScore?, riskLevel (DriftRiskLevel)?, findings (Json)?, findingsCount?, aiTokensUsed?, costUSD?, error?, assessedAt, createdAt, updatedAt |
| `IntelligenceHighlight` | id, intelligenceId, text, sourceEventId, sourceEventKind, sourceCommitSha?, organisationId, createdAt |
| `ReadinessSnapshot` | id, projectId, organisationId, markerCount, markerDetail (JSON: todo/fixme/skippedTests/stubbed/testFileCount), coveragePct?, scannedAt |
| `CodeHealthSnapshot` | id, projectId, organisationId, sonarProjectKey, qualityGate, reliabilityRating, securityRating, maintainabilityRating, coveragePct?, duplicationPct?, scanSource (ScanSource), scannedAt |

### Seed files

| File | Description |
|---|---|
| `prisma/seed.ts` | `seed:0.5x` — minimal seed (half-scale); creates 1 org, ~8 teams, ~48 projects, sample users/prompts/tokens |
| `prisma/seed1x.ts` | `seed:1x` — standard scale; `manager@axis-pulse.dev` / `Manager1234!` as top MANAGER |
| `prisma/seed4x.ts` | `seed:4x` — load-test scale; 17 teams, 192 projects, 55 users |

### Migrations

49 migrations from `20260531111114_init` to `20260615000002_add_security_findings`, covering: initial schema, teams/projects, agent tokens, activity events, prompt library, intelligence, project members, time tracking consent, productive rules, executive summary, repo context, scale indexes, invitations, organisations, session versioning, token grace window, GitHub installations, feed summary, user profile fields, per-developer agent tokens, user tokens, four-bucket time, three-bucket time + top apps, active-seconds default, backfill worked-seconds, risk level focus, intelligence headline, readiness snapshot, code health snapshot, code health scan source, security findings.

| Migration | Purpose |
|---|---|
| `20260621173803_add_membership_table/migration.sql` | PM2 — creates `Membership` table + indexes + FKs; backfills one row per existing `User` from `User.(organisationId, role, teamId, isLineManager)` atomically. Additive-only; no `ALTER`/`DROP`/`UPDATE`/`DELETE` on existing tables. |
| `20260621203926_membership_status/migration.sql` | PM5 — adds `MembershipStatus` enum (`PENDING`, `ACTIVE`) and `status` column to `Membership` with `@default(ACTIVE)`. Adds `@@index([userId, status])`. Backward-compatible; all existing rows default to `ACTIVE`. |
| `20260621205617_invitation_status_declined/migration.sql` | PM5 — adds `DECLINED` value to `InvitationStatus` enum. Allows distinguishing explicit decline from "not yet responded." |

---

## `scripts/` — Operational Scripts

| Script | Description |
|---|---|
| [`sonarqube-start.sh`](scripts/sonarqube-start.sh) | Bash; starts `axis-pulse-sonarqube` Docker container with JVM caps (web/CE 256 MB, ES 512 MB); polls `/api/system/status` until UP |
| [`onboard-new-fleet.sh`](scripts/onboard-new-fleet.sh) | Bash; bootstraps a new agent fleet for any phase (1–19); reads `build-evidence/P<N>/agent-wave-manifest.json`, installs deps, runs migrations, seeds to scale tier, runs full Vitest suite, checks acceptance tests |
| [`run-all-tests.ps1`](scripts/run-all-tests.ps1) | PowerShell; regression sweep; runs `npm test` + build-evidence path checks for a phase range (default `1..18`); exits 0 (PASS) or 1 (FAIL) |
| [`load-test-4x.mjs`](scripts/load-test-4x.mjs) | Node.js; P18 load test; measures real latency against running dev server; concurrency 5, 300 warmup + 300 measurement requests; outputs `build-evidence/P18/4x-load-test-report.json` |
| [`generate-evidence.mjs`](scripts/generate-evidence.mjs) | Node.js; P18 build-evidence generator; produces cost-projection, prompt-cache-rate, scale-down-rehearsal log in `build-evidence/P18/` |
| [`check-db-p18.mjs`](scripts/check-db-p18.mjs) | Node.js; P18 DB verification; checks row counts after scale-down, detects orphaned `ProjectMember` rows, cross-tenant isolation |
| [`explain-audit.mjs`](scripts/explain-audit.mjs) | Node.js; P18 index audit; runs `EXPLAIN ANALYZE` on hot queries to document before/after for two new indexes; outputs `build-evidence/P18/index-audit-before-after.txt` |
| [`print-cleanup-target-counts.js`](scripts/print-cleanup-target-counts.js) | Node.js; P16 cleanup verification; prints before/after row counts for `ActivityEvent`, `AuditLogEntry`, `MemberDailyTime` at their retention cutoffs |
| [`seed-old-rows.js`](scripts/seed-old-rows.js) | Node.js; P16 cleanup testing; seeds `ActivityEvent`, `AuditLogEntry`, `MemberDailyTime` rows with timestamps beyond retention windows |
| [`ui-tour.mjs`](scripts/ui-tour.mjs) | Node.js + Playwright; interactive guided UI tour covering P1–P19 features; opens a real browser and prints terminal instructions; uses seed credentials `manager@axis-pulse.dev` / `Manager1234!` |

---

## `lib/` — Root-level Library

| File | Description |
|---|---|
| [`lib/redact.mjs`](lib/redact.mjs) | ESM version of the redaction logic (mirrors `src/lib/redact.ts`); used by the `pulse-send.mjs` agent-side hook script so it can redact session excerpts before transmission without a TypeScript compiler; patterns cover env vars, JWTs, `sk-ant-`/`sk-` API keys, AWS key IDs, PEM private keys, URL credentials, bcrypt hashes |

---

## `features/` — Feature Work

| Path | Description |
|---|---|
| [`features/context-drift-analyser/context-drift-user-story.md`](features/context-drift-analyser/context-drift-user-story.md) | User story for the proposed Context Drift Analyser feature (planned, not yet implemented) |
| [`features/DASHBOARD-REDESIGN/Build.md`](features/DASHBOARD-REDESIGN/Build.md) | Implementation build plan for dashboard redesign — **implemented** (`src/lib/dashboard.ts`, `DashboardStatsClient.tsx`, `StatCard.tsx`, `GET /api/dashboard/summary`) |
| [`features/DASHBOARD-REDESIGN/Dashboard-Redesign-Plan.md`](features/DASHBOARD-REDESIGN/Dashboard-Redesign-Plan.md) | Design spec for dashboard redesign — **implemented** |
| [`features/DASHBOARD-SPARKLINES/Build.md`](features/DASHBOARD-SPARKLINES/Build.md) | Implementation build plan for 7-day sparklines + activity feed — **implemented** (`SparklineWeek` type, `SparkBars.tsx`, `ActivityFeedClient.tsx`) |
| [`features/member-detail-card/brainstorm.md`](features/member-detail-card/brainstorm.md) | Brainstorm document for the member detail card feature (Phase 01 data layer, Phase 02 UI, Phase 03 window + sessions) |
| [`features/member-detail-card/window-and-sessions-brainstorm.md`](features/member-detail-card/window-and-sessions-brainstorm.md) | Brainstorm for dual-timezone windowing and session rendering in the member card |
| [`features/member-page-animations/audit.md`](features/member-page-animations/audit.md) | Animation audit comparing the cost dashboard animations with the members page; identifies `.stagger` wrapper as the only missing entrance animation — applied in commit `b7e94cbe` |
| [`features/project-redesign/revision-bugs-investigation.md`](features/project-redesign/revision-bugs-investigation.md) | Investigation notes for revision/bugs found during the project page redesign phase |

Note: The Dashboard Redesign and Sparklines features are fully implemented in the codebase. The Context Drift Analyser is planned but not yet implemented. Member detail card Phase 01 data layer is implemented; Phase 02 UI and Phase 03 window/sessions are in progress.

---

## Configuration Files

| File | Configures |
|---|---|
| `package.json` | npm scripts, dependencies (Next.js 14.2.35, Prisma 7.8, NextAuth 5.0-beta.31, Groq AI SDK, Sentry, Upstash, react-hook-form, Zod, Tailwind, Three.js, pino, bcryptjs, react-pdf), devDependencies (Vitest 4, Playwright 1.60, tsx 4, TypeScript 5) |
| `next.config.mjs` | Wraps config with `withSentryConfig`; URL rewrite for `/api/__test/*` → `/api/internal-test/*`; Sentry options: `silent: !process.env.SENTRY_DEBUG`, `widenClientFileUpload: false`, `hideSourceMaps: true`, `disableLogger: true`, `automaticVercelMonitors: false` |
| `prisma.config.ts` | Prisma config; sets schema path, migrations path, datasource URL from `DATABASE_URL`; uses `dotenv/config` |
| `postcss.config.mjs` | Single plugin: `tailwindcss` |
| `components.json` | shadcn/ui: style `base-nova`, RSC=true, baseColor `neutral`, cssVariables enabled, icon library `lucide` |
| `.eslintrc.json` | Extends `next/core-web-vitals` and `next/typescript` |
| `.gitignore` | Excludes env files (except `.env.example`), `.next/`, `node_modules/`, `prisma/generated/`, `coverage/`, `.playwright-mcp/`, `.pulse/` runtime files, `dev-server.log`, `.claude/` plugin cache |
| `instrumentation.ts` | Next.js server Sentry init (nodejs runtime) and edge Sentry init (edge runtime); production startup gate in nodejs runtime only: throws if `CLAUDE_MONTHLY_CEILING_USD` is unset in `NODE_ENV === "production"` |
| `instrumentation-client.ts` | Client Sentry init; `tracesSampleRate: 0.1`; replays disabled (`replaysSessionSampleRate: 0`, `replaysOnErrorSampleRate: 0`) |
| `.mcp.json` | MCP server configuration |

> **Note**: `sentry.server.config.ts`, `sentry.edge.config.ts`, and `sentry.client.config.ts` do **not** exist in the repo. Sentry is initialised entirely via `instrumentation.ts` and `instrumentation-client.ts`.

---

## Environment Variables

From [`.env.example`](.env.example):

| Variable | In `.env.example` | Purpose |
|---|---|---|
| `DATABASE_URL` | ✓ | PostgreSQL connection string (`postgresql://user:password@host:5432/axis_pulse`) |
| `NEXTAUTH_SECRET` | ✓ | NextAuth JWT signing secret (min 64 random bytes base64) |
| `NEXTAUTH_URL` | ✓ | Public app URL for NextAuth redirects |
| `AGENT_TOKEN_PEPPER` | ✓ | HMAC pepper prepended before bcrypt hashing agent tokens (min 32 chars) |
| `UPSTASH_REDIS_REST_URL` | ✓ | Upstash Redis REST URL for rate limiting |
| `UPSTASH_REDIS_REST_TOKEN` | ✓ | Upstash Redis REST token |
| `GITHUB_APP_ID` | ✓ | GitHub App numeric ID for repo context integration |
| `GITHUB_APP_PRIVATE_KEY` | ✓ | Base64-encoded PEM private key for GitHub App JWT signing |
| `GITHUB_APP_WEBHOOK_SECRET` | ✓ | Reserved for future webhook support; unused in v1 |
| `GITHUB_INSTALLATION_ID` | ✓ | GitHub App installation ID for the org (legacy single-installation) |
| `INTERNAL_CLEANUP_TOKEN` | ✓ | Bearer token for `POST /api/admin/cleanup` (min 32 chars) |
| `SENTRY_DSN` | ✓ | Sentry DSN for server-side error reporting |
| `NEXT_PUBLIC_SENTRY_DSN` | ✓ | Sentry DSN for client-side error reporting |
| `COOLIFY_BACKUP_BUCKET` | ✓ | S3 bucket name for Coolify backups |
| `LOG_LEVEL` | ✓ | Pino log level (default: `info`) |
| `GEMINI_API_KEY` | ✓ (stale) | **Stale entry** — `.env.example:22` shows this key under a P20 comment but the runtime code uses `GROQ_API_KEY`. Setting `GEMINI_API_KEY` has no effect. |
| `CLAUDE_MONTHLY_CEILING_USD` | ✓ | Monthly narration cost ceiling in USD (e.g. `"50.00"`); enforced at startup in production (nodejs runtime only); when narration spend ≥ ceiling, new narrations are blocked. Required in production. |
| `GROQ_API_KEY` | **✗ missing** | Groq API key for narration (`llama-3.3-70b-versatile`), feed summary, and streaming executive summary. **Required for all AI features.** Must be added manually — not in `.env.example`. |
| `SCALE_TIER` | **✗ missing** | Rate limit multiplier — `"0.5x"`, `"1x"` (default), or `"4x"`. 4x multiplies ingest/summary/export/repo-context rate limits by 4. Must be added manually — not in `.env.example`. |
| `CLAUDE_DAILY_BUDGET` | **✗ missing** | Daily token budget for health-check display (default: `100000`). Read by `GET /api/health` as `process.env.CLAUDE_DAILY_BUDGET ?? 100000`. Not enforced — display only. Must be added manually — not in `.env.example`. |
| `SENTRY_DEBUG` | **✗ missing** | Controls Sentry upload verbosity via `next.config.mjs`: `silent: !process.env.SENTRY_DEBUG`. Set to any truthy value to enable verbose Sentry build output. Not in `.env.example`. |
| `SONAR_HOST_URL` | ✓ | SonarQube REST API base URL (Node.js process → SonarQube). e.g. `http://localhost:9000`. |
| `SONAR_SCANNER_HOST_URL` | ✓ | URL used by the sonar-scanner Docker container to reach SonarQube. e.g. `http://host.docker.internal:9000` locally, `http://sonarqube:9000` on Coolify. |
| `SONAR_TOKEN` | ✓ | SonarQube user token for REST API authentication and scanner authentication. |
| `SONAR_PROJECT_KEY` | ✓ | SonarQube project key. Must match the key defined in `sonar-project.properties`. |

---

## Build & CI

### GitHub Actions — [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

Two jobs triggered on `push` to `main` and all pull requests:

**`ci` job** (ubuntu-latest, Node 20):
1. Checkout + setup Node 20 with npm cache
2. `npm ci` — install dependencies
3. `npm run lint` — ESLint
4. `npx tsc --noEmit` — TypeScript typecheck
5. `npx prisma migrate deploy` — apply migrations against a postgres:16 service container (`axis_pulse_ci` DB)
6. `npm test` — Vitest suite
7. `npx prisma migrate diff` — schema drift detection
8. `npm run build` — production build (`prisma generate && next build`)

**`deploy` job** (runs after `ci`, only on push to `main`):
- Triggers Coolify deployment via webhook (`COOLIFY_WEBHOOK_URL` / `COOLIFY_WEBHOOK_TOKEN` secrets)

### npm scripts (from `package.json`)

| Script | Command |
|---|---|
| `dev` | `next dev` |
| `build` | `prisma generate && next build` |
| `start` | `next start` |
| `lint` | `next lint` |
| `test` | `vitest run` |
| `test:watch` | `vitest` |
| `seed:0.5x` | `node --env-file .env --import tsx/esm prisma/seed.ts` |
| `seed:1x` | `node --env-file .env --import tsx/esm prisma/seed1x.ts` |
| `seed:4x` | `node --env-file .env --import tsx/esm prisma/seed4x.ts` |

---

## Entry Points

| Entry point | How to reach it |
|---|---|
| **Dev server** | `npm run dev` → `next dev` on `http://localhost:3000`; redirects `/` → `/dashboard` |
| **Production server** | `npm run build && npm start` → `next start` |
| **Agent event ingestion** | `POST /api/ingest/event` — Bearer token auth via `AgentToken`; called by `pulse-send.mjs` hook on developer machines |
| **Agent time ingestion** | `POST /api/ingest/time` — Bearer token auth via `AgentToken` or `UserToken`; called by `pulse-time.mjs` hook |
| **Manual status** | `POST /api/status` — session auth; browser form on project detail page |
| **Health check** | `GET /api/health` — public; returns `{ db, lastEventAgeSeconds, claudeBudgetRemaining }` |
| **Metrics scrape** | `GET /api/metrics` — public; Prometheus text format |
| **Data cleanup** | `POST /api/admin/cleanup` — Bearer token auth via `INTERNAL_CLEANUP_TOKEN`; designed for cron job invocation |
| **Install flow** | `/install` page → `GET /api/install/script` (returns `pulse-send.mjs`) and `POST /api/install/user-token` (generates `UserToken`) |

---

## Module Dependency Map

Derived from actual import statements read across `src/lib/`:

```
withAuthScoped.ts
  → auth.ts
  → db.ts

dashboard.ts
  → db.ts
  → withAuthScoped.ts   (type AuthContext)
  → project-status.ts   (IDLE_THRESHOLD_MS)

cost-ceiling.ts
  → db.ts

dev-cost.ts
  → db.ts
  → budget-utils.ts     (re-exports)

budget-utils.ts
  (no internal deps — safe for client import)

narrate.ts
  → db.ts
  → metrics.ts          (recordClaudeTokens)
  → otel.ts             (startSpan, endSpan, commitTrace)

gemini.ts
  (no internal deps beyond ai SDK)

resolveAgentToken.ts
  → db.ts
  → token.ts

resolveAgentTokenGlobal.ts
  → db.ts
  → token.ts

userToken.ts
  → db.ts
  → token.ts

consentCheck.ts
  → db.ts

repo-context/index.ts
  → db.ts
  → repo-context/snapshot.ts
  → audit.ts

repo-context/snapshot.ts
  → repo-context/client.ts
  → redact.ts

pnumber-matcher.ts
  (no internal deps)

project-exceptions.ts
  → dev-cost.ts   (type DaySpendRow)

project-verdict.ts
  (no internal deps)

project-status.ts
  (no internal deps)

productive-rules.ts
  (no internal deps)

sort-project-cards.ts
  (no internal deps)

presence.ts
  (no internal deps)

pulse-body-shape.ts
  (no internal deps)

pdf-utils.ts
  (no internal deps)

audit.ts
  → db.ts

logger.ts
  (no internal deps)

utils.ts
  (no internal deps)

ratelimit.ts
  (Upstash only — no internal deps)

ratelimit-login.ts
  (Upstash + in-memory — no internal deps)

ratelimit-time.ts
  (Upstash only — no internal deps)

ratelimit-github.ts
  (Upstash + in-memory — no internal deps)

status-ratelimit.ts
  (in-memory — no internal deps)

summary-ratelimit.ts
  → ratelimit.ts   (getScaleTierMultiplier)

otel.ts
  (no internal deps)

metrics.ts
  (no internal deps)
```
