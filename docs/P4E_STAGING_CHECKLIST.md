# P4E Staging Checklist

**State:** Preparation only. No deployment was performed. All unverified service identities and hostnames remain OWNER_CONFIRMATION_REQUIRED.

## Owner confirmations required

- Frontend host/provider and project/service identity: OWNER_CONFIRMATION_REQUIRED.
- Backend host/provider and service identity: OWNER_CONFIRMATION_REQUIRED.
- Canonical backend API hostname and route to the frontend: OWNER_CONFIRMATION_REQUIRED.
- Confirm that trade.jujosmi.com routes to the intended latest UI 2.0 frontend: OWNER_CONFIRMATION_REQUIRED.
- Confirm the deployment platform supports the pinned Node and Python runtimes and required build/start commands.

## Configuration matrix

| Item | Evidence status | Current value |
|---|---|---|
| Public frontend domain | Owner-provided | trade.jujosmi.com |
| Frontend platform/service | Unverified | OWNER_CONFIRMATION_REQUIRED |
| Backend platform/service | Unverified | OWNER_CONFIRMATION_REQUIRED |
| Canonical API hostname | Unverified | OWNER_CONFIRMATION_REQUIRED |
| Render hosting path | Project-code/documentation only | Not proof of active Render service |
| Node/Python project runtime pins | Source/config confirmed | Node 20.19+ documented; Python 3.14 lock tested locally |
| Public auth and signup gates | Source confirmed | Disabled by default |
| Public TradingView gate | Source confirmed | Disabled by default |
| API base URL | Source behavior confirmed, deployment value unknown | Blank production config fails closed |
| Hosted CORS origin | Unverified | Must be exact confirmed HTTPS origin |
| Health endpoint | Source confirmed | GET /health |
| Cloudflare routing or embedding | Unverified | OWNER_CONFIRMATION_REQUIRED |
| SEC User-Agent contact | Local configuration absent | OWNER_CONFIRMATION_REQUIRED |
## Build and runtime configuration

Frontend build in frontend/:

1. npm ci
2. npm test
3. Set VITE_TRADE_API_BASE_URL to https://<confirmed-api-host>/api/v1 only after the backend hostname is verified.
4. Set VITE_SUPABASE_AUTH_ENABLED=false, VITE_SUPABASE_PUBLIC_SIGNUP=false, and VITE_TRADINGVIEW_WIDGET_ENABLED=false.
5. npm run build

Backend in backend/:

1. Use Python 3.14 and install requirements-lock-py314.txt.
2. Startup entry point is uvicorn app.main:app; host-specific bind address and port command are OWNER_CONFIRMATION_REQUIRED.
3. Configure SEC_EDGAR_USER_AGENT as a product/version plus a monitored contact address using the host secret settings. Do not commit this value.
4. Set TRADE_UI_ALLOWED_ORIGINS to the exact confirmed HTTPS frontend origin(s), with no wildcard. The public origin is expected to include https://trade.jujosmi.com only if the owner confirms its routing.
5. The code has a Render-specific configuration path, but Render is not a confirmed target. If Render is confirmed, verify its provided RENDER and RENDER_EXTERNAL_HOSTNAME runtime values before startup.

## Public feature decisions

- Guest access requires no account; Supabase auth and public signup remain disabled.
- TradingView widget is disabled by default, leaving SEC Company Research and guest watchlists available. Keep it disabled until the intended public/commercial display use is confirmed against applicable terms.
- No provider credentials, paid market-data sources, trading endpoints, or brokerage controls are required for the guest research MVP.

## Health and browser smoke

1. Confirm backend GET /health returns status: ok.
2. Confirm an OPTIONS preflight from the exact frontend origin succeeds and an unapproved origin does not receive Access-Control-Allow-Origin.
3. Confirm /api/v1/companies/{symbol}/sec-research reports a transparent unavailable state when SEC contact configuration is absent and returns provenance when configured.
4. In an isolated browser, test Discovery → Company Research, annual/quarterly/YTD statements, SEC filing links, company switching, guest watchlist, and mobile layout at 390 × 844.
5. Check that missing SEC values remain unavailable, account controls describe the disabled state, and the disabled TradingView notice is visible.
6. Review host logs for SEC 403/429 responses, timeout rates, backend failures, and unexpected CORS/host errors.

## Rollback

Before staging, retain the previous complete export and record the staged artifact hash. The hosting owner must confirm how to restore the prior immutable deployment or artifact; exact host rollback controls are OWNER_CONFIRMATION_REQUIRED. Do not replace DNS or production routing as part of this checklist.

## Required environment names

- Frontend build-time: VITE_TRADE_API_BASE_URL, VITE_SUPABASE_AUTH_ENABLED, VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY, VITE_SUPABASE_PUBLIC_SIGNUP, VITE_TRADINGVIEW_WIDGET_ENABLED.
- Backend runtime: SEC_EDGAR_USER_AGENT, TRADE_UI_ALLOWED_ORIGINS; Render-specific only if confirmed: RENDER, RENDER_EXTERNAL_HOSTNAME.

