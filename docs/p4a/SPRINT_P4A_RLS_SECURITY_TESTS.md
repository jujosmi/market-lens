# Sprint P4A — RLS Security Test Plan and Results

## Results performed

The offline Vitest model covers normalized symbols/exchanges, duplicate-safe writes, reads scoped to two mock identities, rejection of a spoofed owner write, protection against deleting another user's row, and refusing to construct a repository without an owner. These are client/repository regression tests only.

The SQL migration was reviewed locally for RLS enablement, authenticated grants, revocation from `PUBLIC` and `anon`, and explicit `auth.uid() = user_id` policies for SELECT, INSERT, and DELETE. UPDATE is intentionally not granted because the client does not edit rows. The migration was not applied. No Supabase project or database was accessed; real RLS enforcement is **unverified**.

## Live development verification checklist

Run only against an explicitly approved disposable development project after reviewing and applying `SPRINT_P4A_WATCHLIST_SCHEMA.sql` there. Create two disposable accounts, A and B, through the project's own Auth flow. Use the normal publishable client and user sessions; never use a service-role key.

| Check | Action | Expected result |
|---|---|---|
| Guest access | Open public workspaces without signing in | Public research remains accessible; guest list stays temporary |
| Anonymous database access | Attempt watchlist SELECT/INSERT/UPDATE/DELETE without a user session | No rows; writes denied by table grants/RLS |
| A owns a row | As A, add `AAPL` with an exchange | Insert succeeds; A can read it |
| B isolation | As B, list rows | A's row is invisible |
| Spoofed owner insert | As A, directly attempt insert with B's `user_id` | Rejected by INSERT `WITH CHECK` policy |
| Update denied | As A, attempt to update even A's own row through the Data API | Denied because the authenticated role has no UPDATE grant |
| Cross-owner update | As A, attempt to update B's row or transfer A's row to B | Denied; no row is updated |
| Cross-owner delete | As A, attempt delete of B's row ID | No row is deleted |
| Own delete | As A, delete A's own row | Permitted |
| Duplicate | Add same normalized symbol/exchange twice as A | Only one row exists |
| Account switch | Sign out A, then sign in as B in same browser | A's rows disappear from UI; only B's rows render |
| Session expiry/refresh | Allow access token to expire while refresh session remains valid; then test expired refresh session | SDK refreshes safely, or UI fails closed and requests reauthentication; no cross-user data shown |
| Guest import | Add guest symbols, then sign in | No upload until user selects “Import guest watchlist”; import is idempotent |
| Persistence | Refresh after successful sign-in and save | Session restores and same user's saved list reloads |

Capture only pass/fail and sanitized error categories. Do not record email addresses, tokens, key values, or user data. If any unauthorized read/write succeeds, stop and do not enable account sync.

## Limits

Mock tests cannot establish Postgres role grants, JWT claim correctness, RLS policy behavior, Auth callback settings, or refresh-token lifecycle. Complete the table against the intended development project before any beta activation. No production project should be modified as part of this test plan.
