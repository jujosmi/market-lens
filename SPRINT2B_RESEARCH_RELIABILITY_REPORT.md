# MarketLens Sprint 2B — Research Reliability & Performance

**Review date:** 2026-11-07  
**Source:** `C:\Users\mores\Documents\GitHub\market-lens`  
**Runtime:** Python 3.13.15, Streamlit 1.66.1, yfinance 1.8.0

## Findings

The reported AMZN blank sections were not reproducible as a consistent presentation failure against live Yahoo Finance responses on this review date. The live Business & Valuation page displayed available company metrics and quarterly values; Analyst Expectations displayed targets, the recommendation distribution, EPS revisions, and filings. AppTest completed both tabs without exceptions.

The strongest reproducible cause was reliability handling: provider exceptions in several research paths were swallowed or converted to empty values, so a timeout or parser failure appeared identical to a genuine lack of data. Live SEC filing retrieval also failed transiently once with a client-side `TypeError`, then returned filings on a later request. That supports an intermittent provider/client failure explanation, rather than a stable AMZN-specific data gap.

Live response structures from yfinance 1.8.0:

- `get_info()` returned a mapping with AMZN market cap, valuation, margin, and other supplied fields.
- `quarterly_income_stmt` returned a DataFrame indexed by statement row names, with period dates in columns. The observed rows included `Total Revenue`, `Operating Income`, `Total Operating Income As Reported`, `Net Income`, and `Diluted EPS`. Some provider cells were null; the view preserves those nulls.
- `analyst_price_targets` returned a mapping with `current`, `high`, `low`, `mean`, and `median`.
- `get_recommendations_summary()` returned a DataFrame with `period`, `strongBuy`, `buy`, `hold`, `sell`, and `strongSell` columns. The current `0m` row was preferred when available.
- `get_eps_revisions()` returned a DataFrame with direction/window columns and currency/methodology metadata.

These response shapes are consistent with the [yfinance analysis API](https://ranaroussi.github.io/yfinance/reference/yfinance.analysis.html), [quarterly income statement reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.quarterly_income_stmt.html), and [Ticker API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.html). Provider fields remain optional and may vary by symbol or request.

## Changes

- Added `market_lens/research.py` to normalize company metrics, quarterly statement row aliases, analyst targets, recommendation distributions, and EPS revisions for display.
- Kept provider nulls null and omitted unavailable metrics. No estimates or classifications are synthesized.
- Changed fundamentals and catalyst loaders to return explicit `available`, `missing`, `error`, or `malformed` status where relevant. Catalyst requests fail independently, so one failed endpoint does not hide successfully returned research.
- Added concise generic UI messages for provider failures and missing data. Technical logs include ticker, endpoint, exception type, and traceback without rendering implementation details to users.
- Reduced the fundamentals and catalyst cache lifetime to five minutes so transient failures do not remain hidden for long. Analyst recommendation data remains shared with the existing rating path and retains symbol-specific cache invalidation.
- Preserved deferred quarterly statement and catalyst loading, active-tab-only retrieval, rating calculations, cache invalidation, and Discovery behavior.

## Regression coverage and validation

Added realistic response fixtures captured from live AMZN, MSFT, and NVDA structures, plus tests for financial presentation, quarterly aliases and missing cells, target normalization, recommendation counts, EPS revision labels, malformed responses, missing data, partial endpoint failure, and lazy tab activation.

- `python -m compileall -q app.py market_lens tests`: passed.
- `python -m unittest discover -s tests`: **70 tests passed**.
- Live AMZN AppTest: both requested tabs rendered without exceptions. AMZN displayed a `$2.80T` market cap; quarterly revenue values included `$201.944B`, a preserved missing quarter, `$181.519B`, and `$213.386B`; recommendation distribution displayed 14 Strong Buy, 44 Buy, 3 Hold, 0 Sell, and 0 Strong Sell; target and EPS revision data were present.
- Live MSFT and NVDA response structures were also captured and checked in fixtures; fixture presentation tests passed for both.

## Performance impact and remaining bottlenecks

The comparable headless benchmark scenario after these changes made 73 Yahoo requests for the cold initial page, 0 for an unchanged warm rerun, 9 for a ticker switch, and 32 for a Discovery industry switch. The counts match the prior Phase 2 optimized scenario (73 / 0 / 9 / 32), so this reliability repair added no measured requests to those workflows.

This single live run measured 23.86 seconds cold, 0.18 seconds warm, 4.15 seconds for the ticker switch, and 6.16 seconds for the industry switch. The prior Phase 2 comparison measured two runs at 15.92–17.68 seconds cold, 0.18 seconds warm, 1.54–1.63 seconds for ticker switching, and 6.02–6.03 seconds for industry switching. Request counts stayed flat, while elapsed times varied; a single run is not enough to attribute the slower cold/ticker timings to this change. Yahoo response latency dominates these short headless samples. The added presentation normalization is local DataFrame/mapping work and does not create provider calls.

The largest remaining contributors are still the 73-request cold page—selected ticker snapshot inputs, watchlist research, broad market context, and Discovery ratings—and the 32-request industry switch, which fetches rating inputs for newly listed companies. The current design already defers inactive Research and Discovery tabs. Further reductions would need to change provider batching, rating freshness, or shared data reuse; those can affect coverage, update timing, or financial calculations, so they are recommendations for a later measured review, not included here.

## Modified files

- `app.py`
- `market_lens/cache_policy.py`
- `market_lens/research.py` (new)
- `tests/test_cache_policy.py`
- `tests/test_performance_optimization.py`
- `tests/test_research_presentation.py` (new)
- `tests/fixtures/__init__.py` (new)
- `tests/fixtures/research_responses.py` (new)
- `SPRINT2B_RESEARCH_RELIABILITY_REPORT.md` (this report)
- `SPRINT2_PERFORMANCE_COMPARISON.md` (updated with current benchmark)

No interface redesign, major architecture change, GitHub publication, or deployment was performed.
