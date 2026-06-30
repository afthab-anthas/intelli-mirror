# Known Issues — Post-Launch Backlog

Audit conducted 2026-06-29. Three HIGH severity findings were fixed before
launch (see commits c23b12b9, 33644be4, 9e45ca0d, 6f3c048f). The items below
are deferred as post-launch work; none blocks the competition deadline.

---

## MEDIUM severity

### M-3 — Privacy Policy and Terms of Service are placeholder pages
**Routes:** `/privacy`, `/terms`  
Both pages display a "Coming soon" placeholder. The signup form asks users to
tick "I agree to the Terms of Service and Privacy Policy" before these
documents exist.  
**Why deferred:** Legal copy is an external dependency; the technical wiring
(routes, links) is already in place. Acceptable for an internal competition
demo; must be resolved before any public launch.

### M-4 — "Forgot password?" link goes nowhere
**Location:** `/login` page — `href="#"`  
No password reset flow exists. Users who lose their password cannot self-serve.  
**Why deferred:** Requires email delivery infrastructure (SMTP/SES) and a
password-reset token flow. Scope exceeds the competition deadline. Severity
is acceptable for a controlled demo with known credentials.

### M-5 — `unsafe-eval` in `script-src` CSP
**Location:** `src/middleware.ts` — `buildCsp()`  
`unsafe-eval` is currently gated to `NODE_ENV === "development"` only, so it
is absent from production builds. The finding was correct for the dev server
but does not affect the production CSP.  
**Status:** No action needed in production; monitoring only.

### M-6 — `https://api.anthropic.com` in `script-src`
**Location:** `src/middleware.ts` — `buildCsp()`  
The Anthropic domain appears in `script-src` (should be `connect-src` at
most, and the AI provider is Groq per ADR-001). This is a stale entry from an
earlier development iteration.  
**Why deferred:** Removing or moving it requires verifying no runtime
dependency on it loading scripts. Low risk but warrants a dedicated cleanup
pass.

### M-7 — Unauthorised admin access silently redirects; no access-denied page
**Location:** All admin pages — middleware redirect on role check failure  
MEMBER users navigating directly to `/admin/*` are silently redirected to
`/dashboard` with no toast or error message.  
**Why deferred:** UX polish; security is intact (redirect blocks access). An
explicit `/access-denied` page is the right fix but is non-critical.

### M-8 — Signup flow only exercisable via invite
**Route:** `/signup`  
The full 4-step flow is gated behind an invite token. Step 1 renders
correctly; beyond that requires a live invite link.  
**Why deferred:** By design — the product is invite-only. Document the invite
flow in the admin runbook and confirm the invite-create path works end-to-end.

### M-9 — 320px viewport: filter tabs overflow and login link clips
**Breakpoint:** 320×568px (smallest Android / iPhone SE)  
Filter tabs on `/admin/members` overflow their container. "Forgot password?"
clips off the right edge on `/login`.  
**Why deferred:** 320px is below the supported minimum width for this product.
Fix involves `flex-wrap` on the tab row and constraining the login footer link.

---

## LOW severity

### L-1 — No `Retry-After` header on 429 responses
Rate-limited responses (e.g., login brute-force) return 429 with no
`Retry-After` header. RFC 6585 requires it.  
**Why deferred:** One-liner fix; no functional impact for human users.

### L-2 — `X-Powered-By: Next.js` header exposed
Reveals the application framework. Suppress with `poweredByHeader: false` in
`next.config.mjs`.  
**Why deferred:** Information disclosure only; no direct exploitability.

### L-3 — Missing `Permissions-Policy` header
No `Permissions-Policy` header restricts camera/microphone/geolocation access.  
**Why deferred:** Low risk for a B2B internal tool; add before any public
consumer launch.

### L-4 — Page `<title>` is "Axis Pulse" on every route
No page-specific titles. Affects browser history, tab management, and screen
readers.  
**Why deferred:** Polish item; use Next.js `generateMetadata()` per route in
the next sprint.

### L-5 — No Open Graph / Twitter Card / canonical URL meta tags
Social sharing and search indexing are impaired.  
**Why deferred:** Not relevant for an internal tool; revisit if a public
marketing site is added.

### L-6 — Mobile sidebar (375px) has no dismiss overlay
Drawer opens without a semi-transparent backdrop; no tap-outside-to-close.  
**Why deferred:** UX polish only; the close button is present.

### L-7 — 768px tablet: project cards drop to single-column
2-column layout at 768px would better use tablet space (desktop is 3-column).  
**Why deferred:** Minor responsive gap; fix with a CSS `grid-template-columns`
breakpoint.

### L-8 — `/api/projects` returns all records with no pagination (~138KB at 4x)
200 projects returned in a single response at the 4x seed scale.  
**Why deferred:** Functional at competition scale; must be addressed before
any enterprise deployment. Add cursor-based pagination.

### L-9 — Sentry double-init warning on client startup
`Sentry.init()` called twice — once from `sentry.client.config.ts` and once
during instrumentation. Causes duplicate events and deprecation warnings.  
**Why deferred:** Follow Sentry's migration guide to consolidate into
`instrumentation-client.ts` only (see startup warnings for the exact
recommended action).

---

## ACCESSIBILITY

### A-1 — No skip-to-main-content link (WCAG 2.4.1, Level A)
All pages lack a skip nav link. Keyboard-only users must tab through the full
sidebar on every page load.  
**Why deferred:** Add a visually-hidden `<a href="#main-content">Skip to
content</a>` as the first focusable element in the AppShell layout.

### A-2 — 2 unlabeled inputs on `/admin/members` (WCAG 1.3.1 + 4.1.2, Level A)
Two filter inputs have no associated `<label>`. Screen readers cannot announce
their purpose.  
**Why deferred:** One-line fix per input; low user impact for an internal tool
with a small, sighted user base.

### A-3 — Page `<title>` identical across all routes (WCAG 2.4.2, Level A)
Covered by L-4 above; same fix resolves both.

### A-4 — Light mode wordmark contrast (WCAG 1.4.3, Level AA)
**Fixed in commit 9e45ca0d.** The `rgba(237,240,250,0.75)` hardcode is now
`var(--text-primary)`, resolving the white-on-white failure in light mode.

### A-5 — Mobile sidebar lacks dismissal affordance (WCAG 2.5.3)
Covered by L-6 above.

### A-6 — Filter tabs overflow at 320px (WCAG 1.4.10 Reflow, Level AA)
Covered by M-9 above.

---

## RESOLVED (fixed pre-launch)

| Issue | Commit |
|-------|--------|
| H-1: `/api/metrics` unauthenticated | c23b12b9 |
| H-2: No clickjacking protection | 33644be4 |
| M-2: Wordmark "axis" invisible in light mode | 9e45ca0d |
| M-1: BlurTextAnimation React hydration mismatch | 6f3c048f |

---

## NON-ISSUES (investigated and closed)

**H-3 — `/api/admin/audit` returning 404:** The `/admin/audit` page is a
React Server Component that queries Prisma directly — no separate API route
exists or is needed. The 404s in audit logs were from external browser calls
to a non-existent URL during testing. The page displays live audit data
correctly.

**L-10 — GitHub callback URL hardcoded to localhost:** All `localhost:3000`
occurrences in `src/` are either Vitest test fixtures (correct) or
`process.env.NEXTAUTH_URL ?? "http://localhost:3000"` fallbacks. Env-driven
in all production paths.
