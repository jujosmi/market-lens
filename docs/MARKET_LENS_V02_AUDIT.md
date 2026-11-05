# Market Lens v0.2 baseline audit

**Audit date:** 2026-11-04  
**Scope:** Existing repository before v0.2 changes  
**Product boundary:** Market Lens is a standalone viewing and research app. It does not connect to a brokerage or place trades and must remain separate from Kestrel.

## Repository inventory

The repository contains three product files: `app.py` (827 lines), `README.md`, and `requirements.txt`. There were no application packages, test suite, database, or docs directory at the start of this audit. `.venv` is an environment directory and is not application source.

The application is one Streamlit script. It contains page styling, sentiment dictionaries, Yahoo Finance provider calls, caching, financial calculations, chart creation, session-state callbacks, and all page rendering in the same file.

## Existing strengths

- The app has a coherent dark dashboard and a useful breadth of observation features: watchlists, price charts, technical indicators, sector ETFs, company facts, research headlines, an industry directory, and event calendars.
- Market data retrieval is cached with different TTLs for prices, search, profile, industry, and event data.
- Most optional Yahoo Finance endpoints fail independently so missing analyst, filing, or calendar details need not block the company history.
- The headline section exposes evidence and a low-signal marker. The Buy / Hold / Sell label shows its simple component checks and disclaims personalization.
- `README.md` explains data limitations and provides local run commands.
- The yfinance dependency is constrained to major version 1, which provides the calendar and industry APIs currently used.

## Main weaknesses and technical debt

### Financial calculations

- **RSI zero-loss handling is incorrect.** The rolling average loss is replaced with `NaN` when it equals zero. A monotonic rise therefore produces `NaN` RSI instead of the conventional limiting value of 100. A flat series produces `NaN`; a monotonic fall should produce 0. The current fallback of 50 is only used when total history has 14 or fewer closes, not when the rolling averages are undefined.
- **The 200-day average is represented with too little history.** The branch accepts 100 observations and then averages up to 200; with 100–199 observations it displays a partial mean as the 200-day average. With fewer than 100 it averages the entire history. This is not a 200-day indicator.
- **20- and 50-day averages silently use partial windows** when fewer than 20 or 50 closes are present.
- **Performance horizon indexing is off by one.** For `n=21`, the current expression compares the last close to row `-21`, which spans 20 return intervals. The same issue affects all horizons. When history is short, the code silently substitutes the oldest available close and still labels the result as a full 1m / 3m / 6m / 1y period.
- **Stock and benchmark horizons are not date-aligned.** Both series use the same number of trailing rows, but holiday calendars, listings, and data gaps can differ. Beta strips timezones and joins by date, but it can silently drop dates and does not report the effective observation count.
- **Historical volatility silently changes its sample size.** Any 10–29 observations are treated as a 30-observation window. Below 10 observations, the code inserts 30% volatility. Neither the partial window nor the 30% fallback is identified as missing or approximated in the output.
- **Expected-move inputs are approximate and under-described.** The options estimate takes a median of up to six near-the-money call/put IV values from one nearest expiry and scales that IV to 30 calendar days. This is not a constant-maturity surface calculation. The realized-volatility fallback inherits the sample-size/fixed-value issue above.
- **Maximum drawdown uses the available trailing history, not necessarily a full year.** The value is still labeled “Largest 1 year drawdown.” Likewise the 52-week high/low use whatever observations are available, without showing coverage.
- **The Buy / Hold / Sell rule can operate on missing checks.** An unavailable 3-month excess return becomes `False` for both positive and negative checks, while other indicators may be partial. The rating does not expose a valid-input count.

### Market and sector analysis

- The market regime calls the S&P trend “rising” when `last > SMA50 > SMA200`; the code does not calculate whether either average is itself rising. The `risk-on` wording therefore overstates what those inequalities establish.
- Breadth counts how many of the 11 sector ETFs have positive 1-month returns. This is sector breadth, not the percentage of constituent stocks above a moving average; the nearby copy partly explains this distinction.
- The sector loop allows frames longer than 50 rows but then indexes row `-63` for the quarterly figure. Histories of 51–62 rows can raise `IndexError` and stop the page. The S&P benchmark guard is 64 rows, but the sector guard is not.
- Market performance labels depend on returned row counts, not explicit date windows. Market regimes and the Treasury proxy do not show source observation dates or staleness.

### Data retrieval and freshness

- Yahoo Finance through yfinance is the only operational data provider. It is an unofficial interface and may be delayed, rate-limited, incomplete, or changed upstream.
- Cached return values contain raw DataFrames/dicts without provider, retrieval timestamp, last observation, interval, freshness state, or warnings. A valid cached response, an empty response, a stale response, and a provider failure often look similar in the UI.
- Several provider failures are swallowed with `except Exception: pass`, so the app cannot explain why an analyst figure, filing, or event is absent.
- `load_market_context` can return partial data after an all-symbol request fails. This is useful resilience, but no per-symbol status is retained.
- Search, fundamentals, analyst estimates, options, earnings, industry listings, IPOs, economic events, and splits all rely on Yahoo/yfinance. There is no provider interface, source registry, or normalized response type.
- `load_benchmark` is defined but unused. Market data, profile, and company information use different functions and caches without a shared metadata contract.

### Application structure and UX

- The monolithic script makes calculations hard to unit test without importing Streamlit and executing UI code.
- The editable comma-separated watchlist and selected ticker live only in Streamlit session state; symbols do not persist across browser sessions.
- The dashboard retrieves a wide set of event and industry data on each rerun (subject to cache), and renders all tabs in one long page. This can make first load and navigation heavy.
- Errors in the selected symbol stop the page; many optional failures show only “Unavailable” or no data. There is no common status language for delayed, stale, partial, missing, or failed data.
- Styling and layout are desktop-oriented and rely on custom CSS and HTML. Charts have a fixed height and only price / 20-day average in the main view.
- The binary headline classifier is a transparent hand-built phrase/word heuristic, not a trained finance model. Its bearish tie-break is explicitly low signal, but the heuristic is unvalidated and should not be presented as stock-return prediction.

## Recommended v0.2 sequence

1. Extract pure calculations into an import-safe analytics module; add fixed synthetic-input tests before changing the UI.
2. Correct RSI edge cases, require full windows for rolling averages, define calendar/trading-session return horizons, align benchmark dates, and return missing values when sample coverage is insufficient.
3. Fix sector guard conditions and make regime wording match the tested calculation. Make breadth labels precise.
4. Introduce a small provider interface and a result/status envelope carrying provider, retrieval time, last observation, interval, freshness, missing-data state, and warning. Keep yfinance as the only provider for this release.
5. Update the UI to display data freshness and distinguish stale, partial, missing, and failed data.
6. Add documented tests for financial calculations and provider-error paths, runnable offline.
7. Defer persistent multi-user storage and broader market screening until the corrected foundation is in place.

## Calculation assumptions to document in the application

- RSI: 14 periods, arithmetic rolling averages as currently implemented; decide and document flat-window convention (50) and zero-loss / zero-gain limits (100 / 0).
- Moving averages: require exactly 20, 50, or 200 valid closing prices; otherwise display unavailable.
- Performance: define horizons explicitly in trading sessions (21 / 63 / 126 / 252) and require the close immediately before the requested interval, i.e. `n+1` valid closes.
- Relative return: calculate each series over common start/end observation dates, then subtract benchmark return. Do not use mismatched trailing row counts.
- Beta: covariance of aligned daily simple returns divided by benchmark-return variance, with minimum sample count reported.
- Realized volatility: sample standard deviation of the explicitly stated daily-return window, annualized by `sqrt(252)`; no fixed substitute when data is missing.
- Drawdown: make period explicit and require enough history for that period.
- Sector return: require at least the horizon plus one close; label sector ETF performance as sector proxy performance, not constituent breadth.
- Expected move: separate option-IV and realized-volatility methods, disclose source/expiry/coverage, and never silently substitute a made-up volatility value.

## Baseline tests

No tests existed at audit time. No code was changed before this audit was written.
