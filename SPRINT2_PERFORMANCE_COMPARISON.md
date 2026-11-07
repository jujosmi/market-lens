# MarketLens Sprint 2 — Phase 2 Performance Comparison

**Date:** 2026-11-07  
**Source:** `C:\Users\mores\Documents\GitHub\market-lens`  
**Environment:** Windows, Python 3.13.15, Streamlit 1.66.1, yfinance 1.8.0.  
**Baseline reference:** [`SPRINT2_PERFORMANCE_BASELINE.md`](SPRINT2_PERFORMANCE_BASELINE.md)

## Summary

Phase 2 prioritizes less work before the user opens an optional research/calendar view. Selected-ticker analyst consensus and options-implied expected move remain on the initial path because they directly determine values shown in the snapshot; deferring either would temporarily change those visible results. The analytics and rating calculations were not changed.

The main page now runs only the selected Discovery tab and selected Research tab's provider loaders. The selected ticker still gets the profile, history, recommendation summary, options-derived expected move, and headlines. Statement data and the additional analyst, earnings, and filing data load only when their Research tab is selected. Headline loading is split into its own cached function and remains loaded when the Headlines section renders.

## Comparable page scenarios

The same headless `AppTest` procedure was used before and after. Each sequence began in a fresh Python process with Streamlit's data cache cleared, then ran the cold page, an unchanged warm rerun, NVDA → AAPL, and a Discovery industry switch. `time.perf_counter()` records script-execution time. Yahoo request counts wrap `curl_cffi.requests.Session.request`. These results exclude browser rendering and vary with provider response time.

| Workflow | Baseline run 1 | Baseline run 2 | Optimized run 1 | Optimized run 2 | Request change |
|---|---:|---:|---:|---:|---:|
| Cold initial app | 33.10 s / 90 | 26.33 s / 83 | 15.92 s / 73 | 17.68 s / 73 | 90→73 (−18.9%); 83→73 (−12.0%) |
| Warm unchanged rerun | 0.20 s / 0 | 0.22 s / 0 | 0.18 s / 0 | 0.18 s / 0 | No requests in either version |
| Switch NVDA → AAPL | 10.51 s / 17 | 5.76 s / 17 | 1.63 s / 9 | 1.54 s / 9 | 17→9 (−47.1%) in both runs |
| Switch Discovery industry | 7.15 s / 43 | 8.40 s / 32 | 6.03 s / 32 | 6.02 s / 32 | −25.6% in run 1; unchanged in run 2 |

Across the two samples, the cold initial script time improved from 29.71 s to 16.80 s (−43.4%) and average observed requests fell from 86.5 to 73 (−15.6%). Ticker-switch script time improved from 8.13 s to 1.58 s (−80.5%). Industry-switch script time improved from 7.78 s to 6.03 s (−22.5%); requests averaged 37.5 before and 32 after (−14.7%). The second baseline industry-switch run already made 32 requests, so the request reduction depends on which new symbols Yahoo returns for the selected industry. These are small live-provider samples, not fixed service-level guarantees.

## Deferred-tab verification

Headless Streamlit navigation selected each tab by its keyed session-state label. Each tab opened without script exceptions and loaded only its relevant event/research data:

| Newly selected tab | First activation requests |
|---|---:|
| Earnings soon | 1 |
| IPOs soon | 1 |
| Other events (economic calendar + splits) | 2 |
| Business & valuation (quarterly statement) | 1 |
| Estimates, events & filings | 5 |
| Technical & relative strength | 0 |

Initial cold page requests fell from 83–90 to 73, and none of the event calendars or Research-only datasets were requested until their tab was activated. Re-running the unchanged page continued to make zero requests. The existing 900-second event cache, 3,600-second statement cache, 1,800-second catalyst cache, 300-second core/news caches, and 1,800-second analyst-recommendation cache remain scoped by their arguments.

## Changes made

- `app.py`: reduced `load_market_data()` to snapshot inputs plus the analyst recommendations and options move required by its visible rating and expected-move metrics. Added separate cached loaders for news, quarterly statements, and catalyst research. The selected-ticker recommendation loader is shared with Discovery so a ticker already loaded for the snapshot can reuse its recommendation cache. Discovery and Research tabs now use Streamlit state-tracked selection (`on_change="rerun"`) and only call the active tab's data loaders. Calendar requests accept selected sections, so Earnings, IPOs, and Other events no longer request one another's data.
- `market_lens/cache_policy.py`: added the new per-ticker data caches to selected-ticker refresh invalidation.
- `tests/test_cache_policy.py`: asserts the new caches are invalidated for the selected ticker.
- `tests/test_performance_optimization.py`: regression coverage for deferred loader boundaries, provider failure handling, one ticker object per catalyst request group, section-specific calendar requests, and active/inactive tab dispatch.

## Rating consistency and decisions

- `market_lens/analytics.py` was not changed. Snapshot signal inputs (history, analyst recommendation summary, options move, and SPY context) and rating thresholds remain as before.
- Discovery retains the existing bulk price-history request, analyst consensus threshold, technical fallback, and bounded `ThreadPoolExecutor` limit of eight workers. Individual analyst recommendation results remain cached per symbol, and the complete rating result remains cached for its symbol tuple. Switching back to an already visited industry therefore uses its existing cache entry.
- A possible SPY-request reuse was measured but not applied: the 6-month `Ticker.history()` benchmark and the matching slice of the 2-year bulk market-context series had the same dates but slightly different adjusted closes (maximum difference about $0.000061). Reusing the context series could alter beta/relative-return inputs, so the separate benchmark path was retained to preserve numerical consistency.
- No unbounded concurrency, interface redesign, provider change, deployment, or publication was performed.

## Verification

- `python -m compileall -q app.py market_lens tests`: passed.
- `python -m unittest discover -s tests`: **62 tests passed**.
- Headless page and tab-navigation runs: no AppTest exceptions.
- Browser rendering and live user interaction have not been measured; they still need manual browser review.

## Independent review package

The existing `FULL_APP` folder did not contain the runtime modules imported by `app.py` (including analytics, charts, providers, and news), and its existing test files were one-byte placeholders. To make the handoff runnable, the current `market_lens` Python modules, chat component HTML, static logos, and complete test files were copied there alongside the changed files and reports. The full 62-test suite passes from that review folder. The source repository's tracked changes remain limited to `app.py`, `market_lens/cache_policy.py`, and `tests/test_cache_policy.py`; the new performance test and comparison report are added files.

## Sprint 2B reliability-fix spot check (2026-11-07)

Using the same headless AppTest scenario, one additional live run measured cold initial at **23.86 s / 73 Yahoo requests**, warm rerun at **0.18 s / 0**, ticker switch at **4.15 s / 9**, and Discovery industry switch at **6.16 s / 32**. Request counts match the Phase 2 optimized counts exactly. Cold and ticker elapsed times were above the prior two-run ranges, while industry switching was close; with one live sample and unchanged request counts, this is treated as Yahoo latency variation rather than a demonstrated regression. See [`SPRINT2B_RESEARCH_RELIABILITY_REPORT.md`](SPRINT2B_RESEARCH_RELIABILITY_REPORT.md) for the AMZN findings, test coverage, and details.
