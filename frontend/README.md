# Jujosmi Trade UI 2.0 — isolated prototype

This is a standalone React/TypeScript prototype. It does not import, replace, or write into the Streamlit application. Public mode embeds TradingView's official Advanced Chart widget; its chart and any market display are supplied directly by TradingView and are never read into Jujosmi calculations. Public Company Research retrieves reported SEC filings and Company Facts through the sibling server-side FastAPI adapter; analyst, news, and technical research remain unavailable until a suitable source and usage rights are established. Offline fixtures and the FastAPI demo's other endpoints contain synthetic examples only.

## Start the React client

Requires Node.js 20.19+ (or a compatible newer LTS) and npm.

```powershell
# Run from the frontend project directory.
npm ci
npm run dev
```

Open the Vite localhost URL (normally `http://127.0.0.1:5173/`). Local development displays the TradingView embed by default; a production build hides it unless `VITE_TRADINGVIEW_WIDGET_ENABLED=true` is explicitly set after licensing review. `/welcome` is the optional landing page; `/`, `/market-overview`, `/discovery`, `/research`, and `/watchlist` remain direct terminal routes. In the terminal header, `Offline fixtures (dev)` enables explicitly simulated React fixtures, while `FastAPI demo (synthetic)` uses the sibling local service for synthetic responses. Public Discovery remains unavailable because no verified public directory is connected. Public Company Research shows SEC-reported facts only when the backend has an identifying SEC User-Agent configured; otherwise the panel explains that SEC data is unavailable. Guests keep a temporary session watchlist; authenticated users can synchronize symbols only after the account gate, project, and RLS migration are separately approved and verified.

## Supabase development configuration

Account functionality is disabled unless `VITE_SUPABASE_AUTH_ENABLED=true`. To connect an explicitly approved disposable/development project, copy `.env.example` to `.env.local`, fill `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` from that project, set the gate to `true`, and restart Vite. `VITE_SUPABASE_PUBLIC_SIGNUP` must remain `false`; public account creation is not approved. The browser client rejects recognized service-role/secret keys; never place such keys in any `VITE_` variable. `.env.local` is ignored by Git. The client uses PKCE email magic links, session persistence and refresh through Supabase Auth. The redirect is the exact current app origin, which must be explicitly approved in the intended Supabase project before enabling sign-in. Do not use wildcard redirect URLs. Public-release builds keep this gate off until live authentication and RLS controls are verified.

## Production build configuration

Production builds have no localhost API fallback. Set `VITE_TRADE_API_BASE_URL` to the owner-confirmed backend API base (including `/api/v1`) before building; if it is blank, API-backed research reports a clear unavailable state and sends no request. `.env.production.example` keeps account access and the TradingView widget disabled. The widget is off by default in production and should remain off until the exact public display use is cleared. To create the static bundle, run `npm ci`, `npm test`, and `npm run build`; output is written to `dist/`. `VITE_` values are compiled into public browser code and must never contain secrets.

The callback verifies the one-time `token_hash` query parameter at the app root (`/`) through Supabase `verifyOtp`. The Supabase Magic Link email template must therefore link to `{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=email`; the default template may instead return a `code` callback and will not match this handler. Configure this template only after reviewing it in the intended development project. PKCE's verifier is stored by the browser client, so the link must be opened in the same browser profile where sign-in was requested. Sign-in success is shown only after Supabase returns an authenticated session.

Before enabling saved watchlists, review and apply `supabase/migrations/202611150001_watchlist_items.sql` only to the intended development database. It enables RLS, revokes anonymous table privileges, grants the required authenticated operations, and enforces `auth.uid() = user_id` for each operation. The migration is not applied by the app. The frontend must use only the publishable key; database service-role credentials are never required by normal watchlist operations. Do not treat static SQL assertions or mocked two-user client tests as RLS verification; complete the two-user real-PostgreSQL steps in the P4B security report before enabling accounts.

To review viewport presets, open `/responsive-review.html`. The local harness provides 390×844, 768×1024, and 1280×900 app frames. Its narrow Discovery and Watchlist tables remain dense and may require horizontal scrolling.

## Start the Python API demonstration

Use a separate PowerShell terminal. The Python service runs independently from the React dev server. To create the backend environment on this workstation, where `py -3.14` is not registered, use the installed interpreter path:

```powershell
# Run from the backend project directory.
$pythonExe = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
& $pythonExe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock-py314.txt
$env:TRADE_UI_ALLOWED_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check: `http://127.0.0.1:8000/health`. OpenAPI docs: `http://127.0.0.1:8000/docs`. The API allows only the listed loopback origins. If Vite selects another port, add only that exact localhost origin to `TRADE_UI_ALLOWED_ORIGINS` before starting the API. Do not expose this demo API to a network.

After both environments are installed, the parent `misc projects` folder includes `start-jujosmi-trade-demo.ps1` and `stop-jujosmi-trade-demo.ps1` to launch and stop just the local API/Vite processes. The launcher binds both services to loopback and keeps logs under `%TEMP%\jujosmi-trade-ui2`. It does not expose a network interface or add machine-wide environment settings.

Run verification from each package directory:

```powershell
# React
npm test
npm run build
npm audit --audit-level=moderate

# FastAPI
python -m pytest -q
python -m pip check
```

## API contracts

All data operations are GET-only under `/api/v1` and return a typed envelope with `data`, `status`, `source`, `freshness`, and `warnings`.

| Endpoint | Purpose |
|---|---|
| `/overview` | Synthetic market summary, sparklines, and sector participation samples |
| `/tickers/search?q=...` | Bounded fixture ticker/name/industry search |
| `/tickers/{symbol}/chart?range=...&interval=...` | Deterministic synthetic OHLCV bars at `15m`, `30m`, `1h`, `2h`, `12h`, or `1d`; subdaily bars are interpolation, not historical prices |
| `/tickers/{symbol}/analysis` | Existing Python technical analysis and rating checks on synthetic history |
| `/discovery?sector=...&industry=...&q=...` | Simulated directory and classifications |
| `/discovery/calendar?kind=earnings|ipos&window_days=...` | Synthetic calendar fixtures; window metadata does not promise an actual event within those dates |
| `/companies/{symbol}/research` | Example fundamentals, analyst fields, events, and technical context |
| `/companies/{symbol}/news-events` | Generic headline and event examples |
| `/companies/{symbol}/sec-research` | Official SEC issuer identity, standard reported facts, and recent filing links; separate from TradingView and available only through the backend |
| `/watchlist/summaries?symbols=...` | Read-only Python sample close, move, trend and technical rating for up to ten symbols |

The backend routes share a typed provider contract and currently use only `SyntheticOfflineProvider`. Every result carries synthetic feed provenance and `prototype_only` permitted use. A bounded provider-scoped cache separates successful and failed TTLs, times out requests, preserves stale results only with an explicit stale warning, and classifies rate limiting. Future real-provider modes require separate approval, provider-specific licensing review, and must not silently substitute synthetic values.

Responses distinguish synthetic fixture endpoints (`source: synthetic-fixtures`) from commit-pinned Python calculations (`source: python-engine-snapshot`), identify freshness as simulated, and can include `as_of`, provenance, missing fields, and warnings. Invalid input, unavailable fixtures, and failed requests have distinct response statuses and safe user-facing messages. The browser client uses a 5-second timeout and validates response shapes at runtime.

## Sprint P2B Python-engine integration

FastAPI mode connects the read-only parts of all four workspaces to the backend: ticker search; interval-aware synthetic OHLCV bars; technical analysis; market summary, sparklines, and sector participation; validated Discovery directory; synthetic earnings/IPO calendar examples; normalized fundamentals and quarterly statements; analyst expectations; EPS revisions/events; Python-classified synthetic headlines; and bounded Watchlist summaries. Company Research fetches only the active research tab. Overview and Watchlist summaries each request the bounded ticker list in one request only while their workspace is active. Guest watchlists remain browser-session state. When Supabase is configured, authenticated watchlists are kept separate from guest state and loaded per signed-in user. API errors do not trigger silent fixture fallback.

The backend's `engine_snapshot` directory contains byte-for-byte copies of the pure `market_lens` functions from approved Streamlit commit `91768e574576349466e95faba40ed6440eda921b`; its manifest records source and snapshot hashes. This makes the demo reproducible without importing Streamlit, providers, credentials, or protected-repository files at runtime. Updating the snapshot requires an explicit source review and parity tests. Synthetic inputs are static and deterministic, dated `2025-12-31`, and never represent present-day prices or verified research.

## Workspace interactions

- **Market Overview:** fixture ticker search or Python API search; chart range, interval, style, and fullscreen controls; API-mode synthetic OHLCV chart, market summary, and technical analysis; session watchlist toggle; expandable market context and strength details.
- **Discovery:** sector and industry filters; search; Python-engine identity validation over synthetic fixtures; API-served synthetic earnings and IPO calendar examples; expandable company details and navigation to Company Research.
- **Company Research:** Overview, Financials, Analysts & Events, News, and Technical tabs; active-tab Python normalizers and classifiers over synthetic inputs; reusable detail cards.
- **Watchlist:** add/remove, sort, select tickers, request Python-engine summaries in FastAPI mode, expand details, and open Company Research. Guests use a temporary session list; an authenticated account list syncs only after Supabase and the RLS migration are configured.
- **Landing:** `/welcome` presents Jujosmi branding and an Enter button. The terminal stays directly accessible at its existing routes, with a return path to `/welcome`.

## Design system and component inventory

| Component | Purpose |
|---|---|
| `Sidebar`, `WorkspaceTabs` | Responsive four-workspace navigation and accessible tabs |
| `SpotlightCard`, `PriceChart`, `TradingViewAdvancedChart` | Bento surfaces, an explicitly synthetic offline SVG, and the isolated official TradingView embed |
| `LandingPage` | Original Jujosmi landing composition using animated gradient and gradient-border action |
| `ExpandableResearchCard` | Local accessible modal pattern for fixture-backed research details; Escape, outside click, focus trap/restoration, internal scrolling, reduced-motion handling |
| Aceternity `BackgroundGradientAnimation` | Official free registry component, scoped to the landing background |
| Aceternity `HoverBorderGradient` | Official free registry component adapted as the landing action |
| Expandable Card Standard | Official demo was installed and reviewed; the reusable app component adapts its expansion pattern without the demo's remote sample images or external content |

The project uses React 19, TypeScript, Tailwind CSS v4, Vite, and Motion. The shadcn registry configuration is in `components.json`; CSS variables and existing global tokens were preserved. No paid Pro component or new runtime dependency was added for the registry components. The component source was adapted locally; verify applicable upstream terms before distributing a shipped product. See the [Expandable Card](https://ui.aceternity.com/components/expandable-card), [Background Gradient Animation](https://ui.aceternity.com/components/background-gradient-animation), and [Hover Border Gradient](https://ui.aceternity.com/components/hover-border-gradient) pages.

## Python engine integration boundary

The isolated adapter calls the source-snapshot functions in `analytics.py`, `research.py`, `news.py`, and `discovery.py` through typed FastAPI endpoints. Parity tests compare outputs to the approved Streamlit source commit. The React app renders their outputs but does not recompute ratings or normalize financial statements. Backend `requirements-lock-py314.txt` pins the tested Python 3.14 environment; the checked-in npm `package-lock.json` pins the frontend dependency graph.

`providers.py` remains disconnected, so no articles or company information are fetched live. `cache_policy.py` contains Streamlit-specific invalidation; no user-specific or market-data service cache has been added. `storage.py` and the React Watchlist are not exposed as shared API persistence. Streamlit session state and widget loading remain in the original app, untouched. The snapshot+synthetic-fixture demonstration proves the wrapping, parity, validation, and rendering path; it does not prove provider reliability, current financial accuracy, licensing, or production readiness.

## Known verification limits

Sprint P2B localhost browser checks exercised FastAPI mode, engine-backed Market Overview, Discovery sector/industry selection and NVDA research navigation, Company Research fundamentals, analyst, news and technical tabs, plus session Watchlist. All four workspaces were checked at 390×844, 768×1024, and 1280×900; the document did not overflow horizontally. Dense Discovery/Watchlist tables retain internal horizontal scrolling. Theme behavior was not checked because this prototype has no theme switch. Application source contains no `MutationObserver` reference; the reported development-only browser-console error could not be confirmed from the browser adapter's console-log surface.

The prototype has an optional Supabase Auth/watchlist foundation but no connected hosted project, live authentication, or independently verified RLS deployment. It has no provider integration for market data, real filings/news beyond the bounded SEC adapter, verified market quotes, trading capability, or full operational/data-source parity with Streamlit. Calendar dates and IPO examples are purely synthetic. Market summary, interval-expanded chart bars, and Watchlist summaries use explicit local fixtures rather than a production data feed. Provider access, storage, Streamlit cache policy, and Streamlit session state remain intentionally unintegrated.


