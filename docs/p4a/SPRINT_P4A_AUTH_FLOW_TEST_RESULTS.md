# Sprint P4A — Auth Flow Test Results

## Offline checks actually run

- React/Vitest: **57 passed across 7 test files**. This exceeds the previous 47-test baseline.
- Added UI coverage for absent Supabase configuration: account panel shows a guest/unavailable state, public Market Overview remains available, and no fake authenticated session is presented.
- Added offline repository tests for ticker/exchange validation, duplicate-safe writes, identity-scoped reads, cross-owner spoof rejection, cross-owner delete protection, and owner-required construction.
- Added a reload simulation proving a guest symbol is restored from `sessionStorage` after remounting the app.
- Added static SQL migration assertions for RLS enablement, owner-bound read/insert/delete policies, duplicate prevention, and absence of an unused UPDATE grant.
- Supabase configuration tests cover missing configuration and rejection of recognized service-role credentials. No client request was sent to Supabase.
- TypeScript check and production build passed; `npm audit --audit-level=low` reported 0 vulnerabilities.
- Backend Python 3.14 suite: **57 passed**. In-memory compile: 25 Python files. Imports passed; `pip check` passed.

## Not exercised

No Supabase credentials or project URL were configured. These flows remain untested against a real Auth service:

- Email-link dispatch, verification, and callback return.
- Exact-origin redirect allowlist behavior.
- Persisted session restoration, access-token refresh, expiry, and recovery.
- Sign-in/sign-out with multiple actual users.
- Database persistence across refresh/devices.
- PostgreSQL RLS enforcement and anon denial.

The account layer is optional and stays in guest mode until configuration exists. `AuthContext` uses Supabase PKCE, persistent sessions, automatic refresh, URL callback detection, and local-scope sign-out, but those SDK paths were not live-validated here.

## Manual next step

Use an approved development Supabase project only. Configure `.env.local` with its project URL and publishable key, add the exact local origin to the Auth redirect allowlist, review/apply the migration, and complete the checks in `SPRINT_P4A_RLS_SECURITY_TESTS.md`. Do not place service-role keys in the browser or in any `VITE_` variable.
