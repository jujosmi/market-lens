# Jujosmi Trade UI 2.0 — Sprint P2B Report

**Result:** Offline Python-engine integration demonstrated. No production code, provider, credential, hosting configuration, or database was changed.

## Source audit and boundary

The source repository was read at `main`, commit `91768e574576349466e95faba40ed6440eda921b`; its working tree remained clean. Its pure functions were suitable for an API adapter:

- `analytics.py`: `close_series`, `analyze`, and `analyst_consensus` use passed-in data and pandas/numpy.
- `research.py`: fundamentals, quarterly statements, analyst target/distribution, and EPS-revision presentation normalizers.
- `news.py`: headline relevance/sentiment and topic classification.
- `discovery.py`: canonical industry identity/key logic and `fetch_industry_companies`, with factories injected for offline testing.

`providers.py` contains network-backed Yahoo Finance access and was not imported or called by the adapter. `app.py`, `cache_policy.py`, and `storage.py` depend on Streamlit session/cache or local user storage and were not exposed through these API routes. The frontend watchlist therefore remains local, session-only state.

The backend carries byte-identical snapshots of the four pure modules from the approved commit. SHA-256 values for each original and copy match in `engine_snapshot/snapshot-manifest.json`. Runtime requests call these functions with deterministic synthetic fixtures dated 2025-12-31. A parity test reads the protected source checkout for comparison; its path can be overridden with `JUJOSMI_TRADE_SOURCE_ROOT`. The production Streamlit repository itself was not modified.

## Implemented integration

- Added `GET /api/v1/tickers/{symbol}/analysis` for the existing Python analysis and rating checks.
- Wired React FastAPI mode to ticker search, chart bars, technical analysis, validated Discovery, normalized company research, and Python-classified synthetic news/events.
- Research data loads by active tab: fundamentals/statements, analyst/events, headlines, and technical analysis are requested only when that section is selected.
- The API chart now plots the Python endpoint's returned closes directly. The quote summary uses the Python analysis close and daily change in API mode, avoiding the former mismatch with the static React ticker fixture. An empty or failed chart response no longer falls back to static ticker points; it shows an unavailable/error state.
- Responses label provenance, simulated freshness, static as-of time, partial/missing fields, and safe warnings. No financial rules were recreated in React.
- CORS defaults now explicitly allow only loopback Vite ports 5173 and 5174. Browser smoke testing found that Vite selected 5174 while the original default only allowed 5173; that made otherwise successful API requests fail in-browser. The allowed-port fallback and regression assertion are now included.

The existing Market Pulse cards, Discovery earnings/IPO calendar fixtures, and session Watchlist are not backed by the Python research engine. These limitations remain identified as illustrative. There is no authentication, persistent watchlist storage, live news, current market data, or trading functionality.

## Files changed

**React prototype**

- `src/App.tsx`
- `src/components/PriceChart.tsx`
- `src/components/PriceChart.test.tsx`
- `src/data/apiClient.ts`
- `src/components/WorkspaceViews.tsx`
- `src/App.test.tsx`
- `README.md`

**Isolated FastAPI service**

- `app/main.py`
- `app/contracts.py`
- `app/fixtures.py`
- `app/engine_adapter.py`
- `app/engine_fixtures.py`
- `requirements.txt`
- `engine_snapshot/analytics.py`
- `engine_snapshot/research.py`
- `engine_snapshot/news.py`
- `engine_snapshot/discovery.py`
- `engine_snapshot/__init__.py`
- `engine_snapshot/snapshot-manifest.json`
- `tests/test_api.py`
- `tests/test_engine_parity.py`
- `README.md`

## Verification

| Check | Result |
|---|---|
| React/Vitest regression suite | 31 passed, 0 failed across 4 test files |
| TypeScript + production build | Passed; Vite 7.3.8 |
| `npm audit --audit-level=moderate` | 0 vulnerabilities reported |
| FastAPI/Python suite | 19 passed, 0 failed on Python 3.14.10 |
| Python source compilation | 13 backend Python files parsed successfully |
| Backend/package imports | Passed |
| `pip check` | No broken requirements |
| Engine numerical/normalization parity | Passed, including exact module-copy hashes and 1e-12 numeric comparisons where applicable |
| Local API browser workflow | Overview/analysis/chart, Discovery sector+industry filtering, company research tabs, and session Watchlist exercised at localhost |
| Responsive widths | All four workspaces sampled at 390×844, 768×1024, and 1280×900; document width stayed within the viewport |

Discovery and Watchlist tables use their own horizontal overflow region for dense columns. The page itself did not gain horizontal overflow. The 390px research tabs are horizontally scrollable. Browser theme behavior was not assessed because this prototype has no theme switch. The source has no `MutationObserver` reference; the earlier development-console report could not be confirmed with this browser surface, so its origin remains unverified.

No screenshot files were saved. Browser observations were made in a separate localhost tab; the existing OAuth and production-site tabs were not used.

## Startup

The two-terminal PowerShell procedure, explicit localhost CORS allowlist, health/docs URLs, test commands, endpoint inventory, engine snapshot details, and boundaries are in the updated prototype and backend `README.md` files. The API binds to `127.0.0.1` only; do not expose this demonstration API to a network.

## Recommendation

**GO** for review of the isolated, synthetic Python-engine demonstration. It proves that the existing pure Python functions can be wrapped in typed FastAPI responses and rendered through the React client. It does not establish live-data correctness, provider availability, public redistribution rights, or production parity.

**Sprint P2C: CONDITIONAL GO.** Before live-source integration, approve the provider and data-use rights, define secret handling/rate limits/cache policy, and agree on explicit freshness and failure states. Keep calculations server-side and repeat parity tests. No live provider integration or production migration is authorized by this report.
