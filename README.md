# Jujosmi Trade UI 2.0

An isolated React + TypeScript frontend and FastAPI demonstration backend for four research workspaces: Market Overview, Discovery, Company Research, and Watchlist. The backend uses a pinned snapshot of selected Python research functions and deterministic synthetic fixtures. The optional SEC adapter reads official SEC filings only when configured with an identifying User-Agent. Optional Supabase Auth and account watchlists are implemented in the frontend but require a separately configured project and an applied database migration.

This is a local development export. It is not a production-ready financial data service, does not execute trades, and does not provide licensed live market quotes. Do not deploy it or redistribute provider information until the relevant use rights and security controls are approved.

## Repository layout

- `frontend/` — React 19, TypeScript, Vite UI, tests, TradingView chart embed, SEC research presentation, optional Supabase Auth/watchlist client, and SQL migration.
- `backend/` — FastAPI contracts, synthetic provider, SEC EDGAR adapter, and pinned `engine_snapshot/` with integrity manifest.
- `scripts/` — loopback-only PowerShell start/stop scripts adapted for this folder layout.
- `docs/` — P4A security and SEC status reports, prior integration reports, and source-hash inventory.

No `.git` metadata, `.env.local`, secrets, virtual environments, node modules, distribution output, Python caches, or runtime logs are included.

## Requirements

- Node.js 20.19+ and npm.
- Python 3.14.10 (the tested runtime) and PowerShell on Windows.

## Install dependencies

From this directory in PowerShell:

```powershell
python -3.14 -m venv backend/.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock-py314.txt
npm --prefix frontend ci
```

If the `py` launcher does not register Python 3.14, create the venv using the full path to the installed Python 3.14 interpreter. No dependencies are installed globally.

## Start and stop locally

```powershell
.\scripts\start-local.ps1
```

Open `http://127.0.0.1:5173/`. The API is bound to loopback at `http://127.0.0.1:8000`; its OpenAPI page is `/docs`. The start script refuses ports already in use and records its own process IDs, executable paths, and start times under the system temporary directory. Stop only those matching processes with:

```powershell
.\scripts\stop-local.ps1
```

Logs remain under `%TEMP%\jujosmi-trade-ui2-full-app`. Do not expose the demo API to a network. To run services separately, see `docs/LOCAL_DEVELOPMENT.md`.

## Data and provider boundaries

- **TradingView:** Market Overview uses the official embedded chart, with TradingView controls and attribution. Its chart data stays inside the embed; Jujosmi does not extract it or use it in proprietary calculations. The React demo has no chart-data API.
- **Synthetic mode:** fixture and FastAPI demonstration responses are labeled synthetic and are not actual financial information.
- **SEC EDGAR:** the backend's server-side route returns supported reported facts and filing links with source fields. It is not a real-time quote source. Standard concepts may be absent, and the adapter must not invent missing values.
- **Other analyst/news/market-data research:** unavailable for public use until a suitable source and redistribution rights are established.
- The Python engine snapshot's SHA-256 values are recorded in `backend/engine_snapshot/snapshot-manifest.json`. The engine parity tests use the included snapshot by default and optionally compare it to an external source repository when `JUJOSMI_TRADE_SOURCE_ROOT` is explicitly set to that repository root.

## Optional SEC configuration

Set `SEC_EDGAR_USER_AGENT` only in the backend process environment, using the application name/version and a real owner-configured contact address. Do not commit that value, paste it into chat, or log it. Example format only:

```powershell
$env:SEC_EDGAR_USER_AGENT = "Jujosmi Trade/2.0 <real monitored contact>"
.\scripts\start-local.ps1
```

Do not use the placeholder literally. Without this value, SEC requests stay unavailable. Respect the adapter's request pacing and stop on SEC access-policy responses. No SEC request is needed for synthetic demo mode.

## Optional Supabase development configuration

Guest research does not require an account. Guests have a temporary browser-session watchlist. To test account sync, use only an explicitly approved disposable development project:

1. Copy `frontend/.env.example` to `frontend/.env.local` and enter the development project's URL and **publishable** key.
2. Never place a service-role, secret, or database-admin credential in a browser `VITE_` variable.
3. Add the exact localhost origin used by the app (for example `http://127.0.0.1:5173`) to that project's Auth redirect allowlist.
4. Review `frontend/supabase/migrations/202611150001_watchlist_items.sql` and apply it manually to the intended development database only.
5. Complete the two-user and anonymous RLS checks in `docs/p4a/SPRINT_P4A_RLS_SECURITY_TESTS.md` before enabling account sync.

The migration is not automatically applied. It grants authenticated SELECT/INSERT/DELETE and omits UPDATE because the client does not edit saved rows; RLS policies bind each granted operation to `auth.uid()`. Live Supabase RLS and email-link session behavior have not been verified in this export. Guest symbols are never uploaded until the user explicitly selects **Import guest watchlist**.

## Tests and checks

```powershell
Push-Location frontend
npm test
npm run build
npm audit --audit-level=low
Pop-Location

& .\backend\.venv\Scripts\python.exe -m pytest -q backend/tests
& .\backend\.venv\Scripts\python.exe -m pip check
```

The engine snapshot comparison is standalone by default. For comparison with the original repository, set `JUJOSMI_TRADE_SOURCE_ROOT` before running Python tests. This variable is optional and is not required to run the application.

## Limitations and release blockers

- Hosted Supabase Auth, email delivery, session refresh, and real PostgreSQL RLS are not verified; the SQL is a prepared migration only.
- A bounded local SEC acceptance verified live AAPL Company Facts, submissions, and a 10-K source link on 2026-11-18. The export contains no SEC contact value; configure `SEC_EDGAR_USER_AGENT` in the backend process environment before SEC research will work. This verification does not establish public display/redistribution rights or production readiness.
- TradingView commercial-use authorization for the intended public product remains outstanding. Embedding the widget is not an authorization to redistribute its data.
- No Yahoo Finance or Alpaca integration, no trading/order execution, no persistent watchlist API in FastAPI, and no production hosting setup are included.
- Public product launch is blocked until data-use rights, live SEC behavior, account/RLS security, and hosting are reviewed independently.

See `docs/EXPORT_INVENTORY.md` and `docs/EXPORT_HASH_MANIFEST.csv` for what was exported and its hash comparison. `docs/EXPORT_VERIFICATION.md` records the test/build/startup results and remaining limits.
Review `docs/THIRD_PARTY_NOTICES.md` before distributing the product or activating it publicly.
