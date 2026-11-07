# MarketLens Sprint 2 — Performance Baseline

**Baseline date:** 2026-11-07  
**Source tree:** `C:\Users\mores\Documents\GitHub\market-lens`  
**Environment:** Windows, Python 3.13.15, Streamlit 1.66.1, yfinance 1.8.0.  
**Scope:** Sprint 2 Phase 1 only. No application behavior or source code was changed.

## Measurement method

The page was run with Streamlit's headless `AppTest` against `streamlit_app.py`. Each baseline sequence began with a cleared `st.cache_data` cache and measured four consecutive workflows: initial cold page run, unchanged warm rerun, changing the focused ticker from NVDA to AAPL, and selecting another Discovery industry. The sequence was repeated in a second fresh Python process. `time.perf_counter()` measured Streamlit script execution. The `curl_cffi.requests.Session.request` method was wrapped to count outbound HTTP calls during each workflow; observed requests were to Yahoo Finance hosts.

A separate fresh-process loader pass measured `load_market_data`, `load_market_context`, `load_industry_index`, `load_industry_companies`, and `rate_industry_companies`, including warm cache calls. Those timings are diagnostic samples and are not mixed into the page-level measurements.

These are headless script-execution and HTTP-request measurements. They do not include real browser layout, paint, network transfer to a user browser, or perceived interaction latency. Provider response times vary, so the two page-level runs are reported as ranges rather than as a stable average. Data values were not altered for measurement.

## Page-level baseline

| Workflow | Run 1 | Run 2 | Requests observed |
|---|---:|---:|---:|
| Cold initial app run | 33.10 s | 26.33 s | 90, 83 |
| Warm unchanged rerun | 0.20 s | 0.22 s | 0, 0 |
| Switch NVDA → AAPL | 10.51 s | 5.76 s | 17, 17 |
| Switch Discovery industry | 7.15 s | 8.40 s | 43, 32 |

Both initial runs completed without AppTest exceptions. The watchlist visible in the tested session was NVDA, AAPL, and TSLA. A Yahoo 404 for UAN fundamentals was printed during the run; it did not fail the page and is consistent with optional provider data being unavailable for one symbol.

## Loader diagnostics

| Loader scenario | Time | Yahoo HTTP requests | Notes |
|---|---:|---:|---|
| Cold `load_market_data("NVDA")` | 7.75 s | 15 | Selected ticker history plus profile, news, analyst, event, filing, statement, and options calls. |
| Warm NVDA market data | <0.01 s | 0 | Cache hit. |
| Cold `load_market_data("AAPL")` | 2.19 s | 14 | A separate symbol causes a fresh request set. |
| Cold `load_market_context()` | 2.74 s | 17 | Broad-market and sector benchmark histories. |
| Warm market context | <0.01 s | 0 | Cache hit. |
| Cold `load_industry_index()` | 1.83 s | 13 | Returned 145 industry rows; asks Yahoo for each configured sector directory. |
| Warm industry index | <0.01 s | 0 | Cache hit. |
| Cold sample industry companies | 0.12 s | 1 | Returned 2 rows for Semiconductors in this provider response. |
| Cold ratings for 12 discovered companies | 6.24 s | 44 | Includes bulk price data, benchmark history, and per-company analyst recommendation retrieval. |
| Warm same ratings | <0.01 s | 0 | Cache hit. |

## Existing architecture and bottlenecks

- `load_market_data()` uses a 300-second cache, but it fetches numerous optional datasets on the initial ticker path. Its cold sample made 14–15 requests and took 2.2–7.7 seconds. Several calls are sequential and failures are mostly swallowed as optional data.
- `load_market_context()` uses a separate 300-second cache and loads 17 symbols on the initial page. The selected-ticker payload and the shared market context are both needed before the page continues rendering.
- `load_industry_index()` has a long 86,400-second cache lifetime, but a cold call still made 13 requests. `load_industry_companies()` uses a 3,600-second cache.
- Discovery ratings are cached for 1,800 seconds, but an uncached industry can still trigger price-history and analyst-recommendation requests for many companies. The measured 12-company rating call made 44 requests. `load_benchmark()` separately retrieves SPY and may repeat work already present in market context.
- Upcoming calendar data is requested at the top of the Discovery section before its four tabs are declared. The selected industry list and the earnings, IPO, and other-event views are all constructed in that same run.
- Both `st.tabs()` groups (Discovery and Technical/Business/Research) use the default behavior. Streamlit documents that all tab contents are computed on each rerun unless tab state is used for conditional rendering. Therefore switching a ticker or another widget can also execute work under inactive tabs. (See [Streamlit tabs documentation](https://docs.streamlit.io/develop/api-reference/layout/st.tabs).)
- `price_chart()` and technical `analyze()` calculations run during page rendering. The selected chart bars are cached for 900 seconds, but figure construction and other Python/pandas rendering work recur on each rerun.
- The page-level warm rerun is already fast and makes no Yahoo requests, showing that the current cache works well after data has been populated. The main latency opportunity is reducing *cold* and *new-selection* work without weakening freshness or the existing cache invalidation behavior.

## Proposed fixes for the next phase

1. Split selected-ticker loading into essential data for the snapshot and chart, then load secondary analyst, filing, statement, option, and other research datasets only when their section is activated. Preserve the same outputs and display-level error handling.
2. Make the existing expensive Discovery and research sections conditional on active navigation state, after verifying the installed Streamlit version and preserving current widget state. This should prevent inactive tabs from causing provider work on unrelated reruns.
3. Reuse benchmark history already loaded for market context in Discovery rating calculations, or share it through a cache keyed on the same source and period. Verify that this changes request duplication only, not rating inputs.
4. Batch or otherwise reduce per-company rating requests where Yahoo supports it; retain analyst-consensus thresholds and the existing technical fallback. Benchmark small and large industries and handle provider errors without labeling missing data as a rating.
5. Keep existing cache lifetimes as a baseline until freshness needs are documented. Add narrowly scoped invalidation checks so ticker refresh and market-pulse refresh retain their Sprint 1 behavior.
6. After implementation, rerun the same cold/warm/ticker/industry workflows and compare request counts and script-execution timings. Use real-browser instrumentation only for any browser-rendering claim.

No Sprint 2 implementation, UI redesign, provider migration, or production/GitHub action is included in this Phase 1 report.
