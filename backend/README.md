# Jujosmi Trade UI 2.0 — local FastAPI demonstration

This isolated Python service demonstrates typed frontend/backend contracts using deterministic local fixtures and a commit-pinned snapshot of selected pure Jujosmi Trade Python research functions. It does not import or modify the Streamlit source tree at runtime and does not contact market-data providers. The read-only SEC EDGAR Company Research route is a separate official SEC source; fixture and engine responses remain marked simulated.

## Start locally (PowerShell)

Use Python 3.14 and run the backend in its own terminal. If the Python launcher does not resolve version 3.14, replace the $pythonExe example below with the exact installed interpreter path:

```powershell
# Run from the backend project directory.
$pythonExe = "C:\Path\To\Python314\python.exe"
& $pythonExe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock-py314.txt
$env:TRADE_UI_ALLOWED_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174"
# Optional SEC Company Research: replace with the product/version and a real monitored contact address.
$env:SEC_EDGAR_USER_AGENT = "Jujosmi Trade/2.0 contact@your-domain.com"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The SEC route stays unavailable until `SEC_EDGAR_USER_AGENT` contains an identifying product/version and real contact address; do not use the example placeholder literally. The value is sent only in server-side HTTP headers and is never returned or logged. The adapter allows one request per 0.5 seconds process-wide, caps retries and response size, caches successful identity/data responses, and pauses requests after an SEC 403. Browser clients call only the local FastAPI endpoint because `data.sec.gov` does not provide browser CORS access.

Health check: `http://127.0.0.1:8000/health`. OpenAPI docs: `http://127.0.0.1:8000/docs`.

Run tests with `python -m pytest -q`; verify dependencies with `python -m pip check`. The Python 3.14.10 installation and its environment are local to this workstation; neither the system PATH nor global Python packages are modified by these commands.

For a repeatable Python 3.14 demo environment, the verified exact dependency set is recorded in `requirements-lock-py314.txt`. After creating and activating the virtual environment, install those exact pins with `python -m pip install -r requirements-lock-py314.txt`. Keep `requirements.txt` as the supported version-range declaration; refresh the lock only as a reviewed dependency change.

For a one-command local startup, run `..\start-jujosmi-trade-demo.ps1` from PowerShell in the parent `misc projects` folder. It starts the API and Vite server bound to loopback, checks both services, and writes logs and process IDs under `%TEMP%\jujosmi-trade-ui2`. Stop only those recorded processes with `..\stop-jujosmi-trade-demo.ps1`. The launcher requires the backend `.venv` and frontend `node_modules` to exist first.
If you have the original Market Lens checkout, parity tests can compare the copied snapshot against it by setting JUJOSMI_TRADE_SOURCE_ROOT to the repository root. This comparison is optional and is not required for the local service.

## API inventory

All data endpoints are GET-only under `/api/v1`:

| Endpoint | Purpose |
|---|---|
| `/overview` | Synthetic market summary, sparklines, and sector participation samples |
| `/tickers/search?q=...` | Bounded fixture ticker/name/industry search |
| `/tickers/{symbol}/chart?range=...&interval=...` | Synthetic OHLCV bars at `15m`, `30m`, `1h`, `2h`, `12h`, or `1d`; subdaily bars are deterministic interpolation, not historical prices |
| `/tickers/{symbol}/analysis` | Original `analytics.analyze` and analyst-consensus functions over synthetic inputs |
| `/discovery?sector=...&industry=...&q=...` | Original Discovery identity validation exercised with offline injected factories |
| `/discovery/calendar?kind=earnings|ipos&window_days=...` | Explicitly synthetic calendar examples; the requested window is echoed and does not imply actual upcoming dates |
| `/discovery/companies?q=...&exchange=...&limit=...&offset=...` | Search and paginate the cached official SEC ticker/CIK/exchange association file; no company facts are inferred |
| `/discovery/filings/{symbol}?exchange=...&limit=...` | Demand-driven recent 10-K, 10-Q, 8-K, and S-1 issuer submissions for a selected ticker; may include SEC SIC metadata |
| `/companies/{symbol}/research` | Original fundamentals, quarterly statement, analyst-target, recommendation, and EPS revision normalizers |
| `/companies/{symbol}/news-events` | Original headline relevance/sentiment and topic classifiers over synthetic headline text |
| `/companies/{symbol}/sec-research` | Server-side SEC issuer identity, submissions, and standard Company Facts; requires identifying User-Agent configuration |
| `/watchlist/summaries?symbols=...` | Up to ten symbols summarized by the existing Python technical-analysis function; read-only and session-only |

Responses use `data`, `status`, `source`, `freshness`, `warnings`, `stale`, and, where available, `as_of`, `provenance`, and `missing_fields`. Invalid input is `invalid`, unknown fixture keys are `unavailable`, provider throttling is `rate_limited`, and unexpected service exceptions are `failed`. Public error text is deliberately generic. The endpoints do not expose user or account data and do not mutate watchlists.

## Provider boundary

`app/providers/contracts.py` defines typed response/provenance contracts and the read-only `ProviderMarketData` protocol. `SyntheticOfflineProvider` is currently the only implementation and contains no network client or market-data SDK. The HTTP routes use this provider interface rather than importing the fixtures/engine adapter directly. Provider provenance distinguishes synthetic, delayed, and real-time feed kinds and includes a permitted-use classification; all current prototype records are `prototype_only`.

`ProviderCache` namespaces keys by provider ID, operation, and normalized parameters. The local API uses a bounded process-local cache (128 entries), 300-second success TTL, 5-second failure TTL, 900-second stale-if-error window, and a 3-second request timeout. If a refresh fails while prior data remains inside the stale window, the response is `partial`, sets `stale: true`, and identifies the fallback in its warning. The React client displays stale state. This cache has no user-specific data and is not suitable for private account records.

Future adapters must supply provider-specific source/feed/timestamp/licensing metadata, obey bounded request sizes, use the cache and timeout boundary, and map provider errors to `rate_limited`, `unavailable`, `partial`, or `failed`. They must not fall back to synthetic fixtures silently. Public display and commercial redistribution remain disabled until provider agreements explicitly permit those uses.

## Engine snapshot

`engine_snapshot/` is copied byte-for-byte from `market-lens` commit `91768e574576349466e95faba40ed6440eda921b`. See `snapshot-manifest.json` for original and copied SHA-256 values. The adapter uses functions from `analytics.py`, `research.py`, `news.py`, and `discovery.py`. `providers.py`, Streamlit app/session/cache code, and storage are intentionally not loaded. After production source changes, review and refresh the snapshot explicitly, then rerun parity tests. This demo does not prove live provider coverage, data licensing, or production-grade parity.

## Security boundary

Local development binds to `127.0.0.1`; Trusted Host accepts localhost and test hosts only; CORS accepts explicit HTTP localhost origins and rejects other domains. The repository contains a Render-style hosted configuration path, but the active hosting provider, service identity, and canonical API hostname have not been verified. If the owner confirms Render, set `TRADE_UI_ALLOWED_ORIGINS` to the exact HTTPS frontend origin and verify Render's `RENDER=true` and `RENDER_EXTERNAL_HOSTNAME` runtime variables before starting the service. Do not reuse the historical example origin without owner confirmation. Do not use wildcard origins. CORS remains non-credentialed, and only `GET`/preflight plus `Accept` and `Content-Type` are allowed. Authentication, database-backed accounts, watchlist mutation, trading, and unlicensed market-data operations are not enabled. This CORS configuration does not authorize broader public use of this demonstration API or change its synthetic/SEC source boundaries.

## SEC EDGAR source boundary

`app/sec_edgar/client.py` contacts only official SEC JSON endpoints through a fixed server-side allowlist. The React app requests `/companies/{symbol}/sec-research`; it never calls SEC directly. Data is limited to the SEC ticker/CIK association file, company submissions, and standard `us-gaap` Company Facts concepts. Company-specific XBRL extensions remain unmapped. The response retains original numeric text and numeric value, units, period dates, form, filing date, accession number, CIK, and SEC archive URL. Company Facts observations whose accession does not appear in the submissions response are omitted; no estimated, TTM, valuation, or market-price values are created.

The adapter uses a process-shared 0.5-second request interval, a 7-second request timeout, at most two retries for transient gateway errors, a 15 MiB response cap, bounded success caching (ticker/exchange directory 24 hours; submissions/facts 15 minutes), and no negative caching. Directory text/exchange search and pagination are filtered locally from this cached file; they do not make additional SEC requests. Issuer submissions are fetched only when a visitor asks for that company's filings, then cached. A 403 trips a process-level circuit breaker. Provider failure remains distinguishable from a missing fact and does not fall back to synthetic data. The HTTP API reports SEC provenance and live/cached freshness. The ticker association file can be incomplete or inaccurate and does not establish a complete list of currently tradable securities. It contains no GICS sector or industry fields; the selected-issuer filings view may show SEC SIC as such. Earnings and IPO schedules remain unavailable. Analysts, news, and technical research remain unavailable in public mode; TradingView stays separate and its embedded data is not extracted or used for calculations.

## SEC financial statement views

`/api/v1/companies/{symbol}/sec-research` includes `annual_periods`, `quarterly_periods`, and `ytd_periods` built from the issuer's reported Company Facts. Annual facts remain FY; three-month interim facts remain quarterly; six-/nine-month cumulative income and cash-flow facts remain YTD; instant balance-sheet facts keep their as-of date and appear only in annual/quarterly views. The adapter does not derive Q4 or subtract YTD cash flows to manufacture quarters. When SEC fiscal-period metadata conflicts for the same date, an interim label is resolved from that date's position between consecutive annual closes; otherwise the provider label is retained. Original fact metadata is preserved.

Year-over-year values require the same metric, unit, normalized fiscal period, and duration within seven days, and use `(current - previous) / abs(previous) × 100`. Zero denominators are unavailable. The latest filed accession is selected per concept, unit, and exact period. Same-valued duplicates do not inflate summaries; conflicting duplicate values in the latest accession are retained in raw facts, excluded from summaries, and flagged. Unsupported or absent measures remain unavailable rather than zero.

Live browser acceptance retrieved AAPL Company Facts and submissions on 2026-11-18 and followed the latest 10-K link to its SEC filing page. Automated tests still use mock HTTP transports and SEC-shaped fixtures. This local check does not establish public redistribution rights or production readiness. The export includes no SEC contact value; configure a real monitored `SEC_EDGAR_USER_AGENT` only in the backend process environment. Official references: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [fair-access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), and [User-Agent FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions).

