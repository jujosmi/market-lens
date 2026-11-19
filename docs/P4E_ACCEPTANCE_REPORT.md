# Sprint P4E Acceptance Report

**Date:** 2026-11-18  
**Release state:** Conditional — ready for owner staging review  
**Deployment state:** NO-GO; no push, hosting change, DNS change, or deployment occurred.

## Source of truth

- Frontend: authoritative React and TypeScript project tree.
- Backend: authoritative FastAPI project tree.

The source folders have no Git metadata, so no commit or branch is claimed. The deterministic release version is the SHA-256 identifier in P4E_RELEASE_MANIFEST.json.

## Implementation and build

- Production gates are explicit: Supabase auth and signup disabled, TradingView disabled, and no production loopback API fallback when the canonical API base is blank.
- Guest watchlists and SEC Company Research remain separate from synthetic demo content. Unavailable SEC data is never replaced with synthetic financial values.
- SEC issuer identity is checked against the selected ticker. Recent filings preserve the optional SEC 8-K items field and classify an earnings-related event only when SEC Item 2.02 is present.
- SEC financial summaries provide period-matched revenue growth, operating and net margins, free cash flow, and reported cash/debt context. Derived cards show formulas, source values, accession provenance, and filing links. Calculation tests cover matching periods and units, zero bases, conflicts, non-finite values, and no annual/YTD bridging.
- Workspace and chart code are lazy-loaded. The TradingView initialization lifecycle has a focused regression test.
- Frontend: **100 tests passed** across 18 files. TypeScript project checking (tsc -b, included in npm run build) and Vite production build passed; the project defines no separate typecheck npm script.
- Frontend output: CSS 99.19 kB (20.91 kB gzip); lazy WorkspaceViews 91.52 kB (22.96 kB gzip); main JavaScript 453.22 kB (142.44 kB gzip); no Vite greater-than-500 kB chunk warning.
- Backend: **94 tests passed**; pip check reported no broken requirements. One Starlette/httpx TestClient deprecation warning remains.
- Local API smoke: /health returned ok; configured loopback origin received CORS access; an unapproved origin received no allow-origin header and its preflight was rejected with 400.
- The isolated browser verified the guest shell, unavailable-source messaging, account-disabled state, guest watchlist, and responsive preview before the latest SEC financial-summary source update. The outer browser window cropped the 1440-wide preview, console inspection was unavailable, and the latest derived SEC figures were not browser-verified against live SEC data. Treat browser verification as limited, not as a full acceptance pass.

## SEC boundary

The adapter uses fixed official SEC URLs, a shared 0.5-second request interval, a four-request concurrency cap, 7-second timeout, bounded transient retries, a 15 MiB body limit, caching, input validation, and explicit 403/429 handling. The SEC contact setting was absent locally, so Company Research showed unavailable and no SEC request was made during this release check. Staging must set SEC_EDGAR_USER_AGENT securely to an identifying product/version and monitored contact.

SEC documentation states public EDGAR content is free to reuse, but its API access rules still require a declared User-Agent and moderated request rate. This application paces at 2 requests per second.

## TradingView and licensing

The public widget remains disabled by default. In a local widget-enabled check, the frame initialized but chart pixels remained blank; available browser tooling could not expose the console details or determine whether the cause was a blocked asset, initialization, CSP, or provider behavior. Current TradingView terms limit data and content to display-only use for personal or internal business purposes and restrict broader processing. Do not enable the public widget without confirming the intended use is permitted or obtaining a separate agreement.

## Hosting, dependency, and rights blockers

- Frontend host/project identity, backend host/service identity, canonical API hostname, routing from trade.jujosmi.com, and any Cloudflare relationship remain unverified.
- The production dependency audit previously reported no production runtime vulnerabilities. The full audit reported five high findings in development/build tooling only (fdir, picomatch, tinyglobby, Vite, and Vitest), with no critical findings. Safe remediation would require major-version downgrades; no unreviewed downgrade was applied.
- Public widget use rights, monitored SEC contact, exact hosted CORS origin, and staging target remain unresolved.
- The browser could not inspect console output; the widget-enabled rendering issue is unresolved. This export is not a deployment approval.

## Outcome

**CONDITIONAL — ready for owner staging review after the explicit confirmations in P4E_STAGING_CHECKLIST.md. Deployment remains NO-GO until the owner approves actual targets, environment settings, SEC contact, and the TradingView decision.**

