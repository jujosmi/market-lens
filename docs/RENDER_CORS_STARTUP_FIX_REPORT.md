# Render CORS Startup Fix

Date: 2026-11-16

## Root cause and correction

`backend/app/main.py` treated every configured CORS origin as a development origin and accepted only `http://` loopback hosts. Render serves the approved frontend over HTTPS, so application import raised before FastAPI could start. `TrustedHostMiddleware` also allowed only loopback and test hosts, which would reject requests addressed to the Render API service.

The configuration now separates local and Render modes. Local mode keeps explicit HTTP origins restricted to `localhost`, `127.0.0.1`, or `::1`, including explicitly selected non-default development ports. Render mode requires `TRADE_UI_ALLOWED_ORIGINS`, accepts only canonical explicit HTTPS DNS origins, rejects HTTP and loopback origins, and restricts trusted hosts to Render's validated `RENDER_EXTERNAL_HOSTNAME`. Wildcards, credentials, paths, query strings, fragments, malformed hosts, and non-canonical default ports remain rejected. Methods remain limited to GET and OPTIONS; headers remain limited to Accept and Content-Type; credentialed CORS remains disabled.

Localhost API startup remains unchanged in the desktop start script. The backend README now documents Render's runtime variables and the exact-origin configuration. No frontend origin, API hostname, credential, or secret is hardcoded in application configuration.

## Verification

- Python: 3.14.10, isolated backend environment.
- Backend tests: 75 passed, 0 failed (the prior reported baseline was 57).
- In-memory compilation: 26 backend Python files, including the engine snapshot and tests.
- FastAPI and SEC adapter imports: passed.
- `pip check`: no broken requirements.
- Simulated Render Uvicorn process bound only to loopback: startup succeeded with `RENDER=true`, a validated `RENDER_EXTERNAL_HOSTNAME`, and the explicit approved frontend origin.
- `/health`: HTTP 200.
- Approved frontend CORS preflight: HTTP 200 with the exact `Access-Control-Allow-Origin` value.
- Unapproved origin preflight: HTTP 400 and no allow-origin response header.
- Automated route-surface assertion: data routes are GET-only; POST and Authorization-header preflights are rejected.
- A Starlette/httpx TestClient deprecation warning remains; it does not fail the suite.
- No live Render deployment, SEC request, or production configuration change was performed.

## Render configuration action

In the backend Render service environment, set `TRADE_UI_ALLOWED_ORIGINS` to exactly:

`https://jujosmi-trade-v2.onrender.com`

Render supplies `RENDER` and `RENDER_EXTERNAL_HOSTNAME` for a Render web service. Confirm these service variables are present in the deployed runtime before restarting. This local fix does not itself update the deployed service.
