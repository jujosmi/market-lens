# FULL_APP Export Verification

Verification was run against the assembled `FULL_APP_EXPORT_P4A1` copy before it was transferred to the upload destination. The copied files were used for installs, tests, build, and local startup; the original development folders were not used as the tested source tree.

## Results

- `npm ci` from the copied frontend lockfile: completed; npm reported 0 vulnerabilities during install.
- React/Vitest: **57 passed across 8 test files**.
- Frontend TypeScript validation and production build: passed (Vite transformed 2,209 modules).
- `npm audit --audit-level=low`: **0 vulnerabilities**.
- Python backend suite from the copied `backend/` tree in the existing isolated Python 3.14.10 environment: **57 passed**, with one Starlette/httpx `TestClient` deprecation warning.
- All **28** installed Python package versions matched `backend/requirements-lock-py314.txt`. In-memory syntax compilation: **25 backend Python files compiled**. FastAPI and SEC adapter imports passed. `pip check`: no broken requirements.
- Snapshot integrity/parity tests passed against the included manifest. External repository source is now optional via `JUJOSMI_TRADE_SOURCE_ROOT`; tests no longer require a developer-specific checkout path.
- PowerShell start/stop scripts parsed successfully. The startup script correctly refused occupied default port 8000; after selecting unused loopback ports 54630 and 54631, it returned a successful API health response and HTTP 200 frontend page. The two recorded processes were stopped using the exported stop script. No unrelated process was terminated.
- Credential-pattern scan: no high-confidence credential match. Only `frontend/.env.example` is present; no real credentials, `.env.local`, service key, SEC contact value, or environment-specific runtime file is included.
- Root `.gitignore` behavior was checked with Git in a disposable temporary repo: secret files, virtual environments, package installs, build output, caches, and logs were ignored; `.env.example`, source, dependency lock, and logo remained trackable.
- After transfer to the designated upload folder, all **95 files** were compared to the verified staging copy by relative path and SHA-256: no missing, extra, or mismatched files.
- The export includes the SQL migration but does not apply it. Static migration tests verify RLS, owner-bound SELECT/INSERT/DELETE policies, duplicate constraint, and absence of an unused UPDATE grant. These are not live database tests.

## Limitations

- No hosted Supabase project was connected. Email Auth, callback allowlisting, session renewal, and database RLS remain unverified.
- SEC access was not attempted: the local backend had no `SEC_EDGAR_USER_AGENT`. Live company facts and the populated SEC responsive UI remain unverified.
- This check is a local build/startup test, not browser visual acceptance or a production deployment test.
- TradingView commercial-use authorization remains outstanding. The widget's existing attribution and isolation are preserved; see `THIRD_PARTY_NOTICES.md`.

## Render CORS startup correction (2026-11-16)

- The backend now separates explicit localhost development origins from exact HTTPS origins configured for Render staging and validates the Render API host with `RENDER_EXTERNAL_HOSTNAME`.
- Python 3.14.10 backend suite: **75 passed**; in-memory compilation: **26 Python files**; application/SEC imports passed; `pip check` reported no broken requirements.
- A simulated Render-mode Uvicorn process started on loopback. `/health` returned HTTP 200, the exact configured frontend origin passed preflight, and an unapproved origin received HTTP 400 without CORS authorization.
- CORS remains non-credentialed and limited to GET/OPTIONS and Accept/Content-Type. OpenAPI data endpoints remain read-only; no account mutation or trading routes were enabled.
- The export package was refreshed with the backend correction, regression tests, and `docs/RENDER_CORS_STARTUP_FIX_REPORT.md`. This was not a Render deployment. See the fix report for the required Render environment configuration and test warning.

## P4C functional controls verification (2026-11-17)

- React/Vitest: **66 passed across 10 test files**.
- TypeScript validation and Vite production build: passed. Vite reports the main JavaScript bundle at approximately 508 kB minified, slightly above its 500 kB advisory threshold; the build succeeds.
- `npm audit --audit-level=low`: **0 vulnerabilities**.
- FastAPI backend: **75 passed**, with one existing Starlette/httpx TestClient deprecation warning. No backend source files changed.
- Local browser smoke at `http://127.0.0.1:5190`: confirmed workspace navigation, Public Charts from Company Research, Ctrl/Command+K from Company Research to the public chart search, sector filtering to the matching company, Research navigation for the filtered company, and Preferences/Help opening and closing. The local FastAPI service was not running; the SEC panel showed its expected unavailable state.
- The browser smoke was desktop-sized. The browser automation surface did not expose viewport overrides, so 390×844 and 768×1024 visual acceptance remain owner checks. No screenshot was saved into this package.
- The React source was refreshed from its authoritative project. Backend source remains unchanged. The package contains 103 files, including the safe `frontend/.env.example`; no `.env.local`, credentials, node_modules, dist output, Python environments/caches, or Git metadata are included.

These checks are local development verification only, not production deployment or license approval.

## P4D SEC-powered Discovery verification (2026-11-17)

- React/Vitest: **71 passed across 10 test files**. TypeScript validation and Vite production build passed; the main JavaScript chunk is approximately 518 kB minified, above the 500 kB advisory threshold.
- Production dependency audit (`npm audit --omit=dev --audit-level=low`): **0 vulnerabilities**. Full development dependency audit previously reported 8 high findings in transitive `picomatch` via Vite tooling; npm advisory output offered no fix.
- Python backend suite: **85 passed**, with one existing Starlette/httpx TestClient deprecation warning. In-memory syntax compilation covered 23 Python files; FastAPI and SEC Discovery imports passed; `pip check` reported no broken requirements.
- The latest backend failure was a fixture defect: duplicate ticker entries omitted exchange values while asserting exchange-specific identity. The fixture now supplies distinct NYSE and Nasdaq exchanges; the adapter correctly refuses an unqualified ambiguous ticker and resolves only the explicitly matching exchange.
- SEC adapter tests use official-shape fixtures and mock transports. Live SEC access was not attempted because the process environment does not contain `SEC_EDGAR_USER_AGENT`; no issuer data or live HTTP metrics are claimed.
- Local browser smoke at `http://127.0.0.1:5177/discovery` confirmed the SEC Discovery workspace renders, labels the SEC directory source, and shows a safe API-unavailable state without synthetic fallback. It did not verify populated SEC data or mobile visual acceptance.
- The SEC directory provides symbol/name/exchange search and local pagination over the cached official association file. Exchange qualification is retained when opening Company Research to avoid guessing between duplicate symbols. Issuer filings are loaded only on demand.
- Future earnings/IPO schedules remain explicitly unavailable. SEC SIC is presented as SIC, not GICS; the SEC ticker association file may be incomplete or inaccurate and is not a full tradable-security or industry directory.
- Export inventory and SHA-256 manifest were regenerated after syncing 6 frontend and 4 backend source files. The authorized FULL_APP destination was rechecked by relative path and SHA-256: 105 files, zero missing, zero extra, and zero mismatched files.
- No production Render, Supabase, Cloudflare, GitHub, or protected Streamlit settings were changed.

These checks are local development verification only, not production deployment, live SEC verification, or licensing approval.

