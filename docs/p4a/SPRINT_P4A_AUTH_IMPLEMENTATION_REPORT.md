# Sprint P4A — Authentication & Persistent Watchlist Foundation

**Project:** Jujosmi Trade UI 2.0  
**Scope:** Isolated React prototype and local FastAPI regression verification  
**Status:** Local foundation implemented; hosted activation and live RLS verification remain pending.

## Completed

- Added an optional Supabase browser client configured only by `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`. It is dynamically imported, uses PKCE, restores persisted Auth sessions, and enables the SDK's refresh behavior. No Supabase project was contacted.
- Added an account menu with passwordless email-link sign-in, session status, sign-out, accessible feedback, and an explicit unconfigured state. Public workspaces remain usable without authentication; no fake account is created.
- Kept guest watchlists in browser `sessionStorage`. Authenticated watchlists use an owner-scoped repository. A guest list is offered for explicit import only; it is not uploaded automatically. Switching/signing out clears private watchlist state and async updates are guarded by user identity.
- Added ticker/exchange validation, exchange-qualified uniqueness, idempotent insert behavior, owner-filtered reads/deletes, and a versioned PostgreSQL migration with RLS and explicit grants/policies. The browser role receives SELECT, INSERT, and DELETE only; UPDATE is omitted because the client does not edit saved records.
- Updated setup documentation, `.env.example` placeholders, and ignore rules. The migration has not been applied to any database.

## Files changed in the isolated React project

- `src/App.tsx`, `src/App.test.tsx`
- `src/components/Sidebar.tsx`, `src/components/WorkspaceViews.tsx`, `src/styles.css`
- `src/auth/AuthContext.tsx`, `src/auth/AuthAccountMenu.tsx`, `src/auth/database.types.ts`, `src/auth/supabaseClient.ts`, `src/auth/watchlistRepository.ts`
- `src/auth/supabaseClient.test.ts`, `src/auth/watchlistRepository.test.ts`
- `supabase/migrations/202611150001_watchlist_items.sql`
- `package.json`, `package-lock.json`, `.gitignore`, `.env.example`, `README.md`

The report copy of the schema is [SPRINT_P4A_WATCHLIST_SCHEMA.sql](SPRINT_P4A_WATCHLIST_SCHEMA.sql). The React prototype is not a Git repository in this workspace. No staging, commit, push, or deployment was performed.

## Security and data boundaries

- The frontend accepts a publishable key only; recognizable secret/service-role keys are rejected. Pattern scanning found only the literal `service_role` rejection logic in source and its bundled copy, not a credential value. No `.env.local` or hosted project configuration was present.
- Watchlist rows contain user ID, canonical symbol, optional exchange, and timestamps only. They contain no prices or financial-provider data.
- Guest research does not require sign-in. Private database access relies on authenticated user JWTs plus database RLS; client-side filtering is defense-in-depth, not the authorization boundary.
- Static migration tests check RLS, owner policies, duplicate constraints, and least-privilege grants. The offline two-user test is a mocked RLS model. Neither proves that PostgreSQL/Supabase actually enforces the migration.

## Verification

- React: **57 tests passed** across 7 files (baseline 47), including a simulated app reload that confirms the temporary guest list restores from `sessionStorage` and static checks of the migration's least-privilege contract.
- TypeScript validation and Vite production build: passed. Supabase SDK is emitted as a separate lazy-loaded chunk; the main bundle is about 496 kB uncompressed.
- `npm audit --audit-level=low`: **0 vulnerabilities**.
- Backend Python 3.14 suite: **57 passed**, one existing Starlette/httpx deprecation warning.
- In-memory Python compilation: **25 backend Python files**; application and SEC imports passed; `pip check`: no broken requirements.
- A local credential-pattern scan did not find credential values. It did find expected `service_role` detection text in `supabaseClient.ts`, its test, and the built bundle.

The protected Streamlit repository status could not be verified: Git refused the read-only status command because the repository is owned by a different Windows SID and is not configured as a safe directory. I did not alter Git's global safe-directory configuration. No command modified that repository.

## Not live-verified

No Supabase URL or publishable key was configured, so email delivery, callback allowlisting, session persistence/refresh, account switching, hosted RLS, and cross-device synchronization were not exercised. The app correctly remains in guest mode.

`SEC_EDGAR_USER_AGENT` was absent from process, user, and machine environment. The earlier local API request returned the SEC configuration-required response before an upstream request. No SEC HTTP requests were made in this sprint. Therefore no live AAPL/NVDA SEC facts, filing links, or SEC-backed responsive screenshots were verified.

## Activation prerequisites

1. Configure an explicitly approved development Supabase URL and publishable key in local `.env.local` only; never put secrets in `VITE_` variables.
2. Add the exact local app origin to the development project's Auth redirect allowlist and verify email-link behavior.
3. Review and apply the migration to that development database only.
4. Complete the two-user, anonymous, spoofed-owner, sign-out, and token-expiry RLS checklist in `SPRINT_P4A_RLS_SECURITY_TESTS.md`.
5. Separately configure a legitimate SEC User-Agent contact in the backend process and complete bounded SEC verification before claiming actual SEC research acceptance.

**Recommendation:** Conditional go for local code review. Not ready to activate hosted account sync or claim SEC live acceptance. No production deployment is authorized or recommended by these results.
