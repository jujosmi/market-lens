# Market Lens v0.2 Release Report

**Completed:** 2026-11-04  
**Scope:** Incremental reliability and maintainability work from the baseline audit in [MARKET_LENS_V02_AUDIT.md](MARKET_LENS_V02_AUDIT.md).

## Features improved

- The original Streamlit dashboard remains the application. It still includes ticker discovery, industry browsing and watchlist filtering, market pulse, sector rotation, fundamentals, analyst information, events, filing links, headline sentiment, and a Buy / Hold / Sell screen.
- The main dashboard areas are grouped into labeled bordered sections, and selected tabs have a distinct highlight to make the current research area easier to spot.
- Snapshot cards reveal short explanations on hover/focus. The signal-rating explanation uses the same named checks and threshold as the actual rating; the trend explanation shows the averages and history window behind the label.
- Added a draggable corner terminology assistant. It uses a curated offline glossary without a key and can use the OpenAI Responses API for broader educational questions when `OPENAI_API_KEY` is set server-side. API keys never enter the browser component. The panel discloses that chat is sent to OpenAI and may incur API charges.
- Added a Cloudflare Pages integration folder with a responsive iframe example and deployment notes. Hosted mode (`MARKET_LENS_HOSTED=true`) isolates each visitor's watchlist to that Streamlit session rather than writing a shared server-side JSON file.
- The sidebar watchlist now saves locally to `.market_lens_watchlist.json` and normalizes symbols to uppercase, removes duplicates, and caps the list at eight.
- Market history and the benchmark tables expose provider source, retrieval time, interval, latest observation, and a freshness/status label. Broad-market and sector rows include their observation date and status. Yahoo quote delay is explicitly marked unknown because the provider does not establish that information here.
- A provider interface separates history retrieval from analytics. The existing Yahoo Finance source remains in place; other providers can implement the same boundary later.
- Missing/short histories no longer silently create partial 20-, 50-, 200-day, 30-session volatility, 52-week, or one-year drawdown values. The interface gives a reason when an indicator or rating cannot be calculated.
- The sector table requires 64 closes before showing a 63-interval quarterly comparison, avoiding the prior 51–62 row indexing error. Market-regime language describes the moving-average alignment actually measured.

## Financial calculation corrections

- **RSI:** Wilder's RSI uses the first 14 daily changes as a seed and then applies Wilder smoothing. It returns 100 with zero average loss, 0 with zero average gain, 50 on a flat series, and unavailable without 15 closes.
- **Moving averages:** Each average uses its full labeled window. There is no partial 200-day or all-history substitute.
- **Returns:** An `n`-session return uses `n + 1` closes. The app now includes one-day, one-week, one-month, three-month, six-month and one-year periods. Missing horizons remain unavailable.
- **Relative performance:** The stock and SPY closes are joined on common dates before the same-period returns are calculated. The 3-month Buy/Hold/Sell check compares excess return on those shared dates.
- **Beta:** Beta is computed from individually calculated daily returns joined by the same date. It uses up to 120 paired observations and requires at least 60; the calculation returns the observation count.
- **Volatility:** Realized volatility requires all 30 trailing daily returns and annualizes sample standard deviation with `sqrt(252)`. The 30-day expected range can use available near-the-money option IV, otherwise the full 30-session realized estimate. There is no fixed 30% fallback.
- **Drawdown and 52-week levels:** The one-year high/low and maximum drawdown use exactly 252 closes. Current drawdown is measured from the trailing 252-close high.
- **Ratings:** The five constructive and five caution checks still have equal weight. Buy/Hold/Sell is withheld if any required input is unavailable, rather than treating missing checks as negative or neutral.
- **Sector returns:** One month uses 21 return intervals (22 closes), and three months uses 63 intervals (64 closes). Sector returns are compared with SPY over the same label horizon, using ETF proxy closes.

The expanded formulas and beginner notes are in the repository [README](../README.md). The UI and docs explain that these are descriptive calculations and simple screening rules, not validated forecasts.

## Architecture and data flow

`app.py` still owns the Streamlit page, user interaction and rendering. Its work is supported by smaller modules:

- `market_lens/providers.py` defines `MarketDataProvider`, the Yahoo Finance adapter, and `DataEnvelope` metadata for status, source, interval, timestamps and warnings.
- `market_lens/analytics.py` contains pure calculations that can be tested without Streamlit or live quotes.
- `market_lens/news.py` contains the inspectable finance-specific phrase/term sentiment rules and topic grouping.
- `market_lens/charts.py` builds the Plotly price chart.
- `market_lens/storage.py` loads and atomically saves the single-user local watchlist JSON.
- `market_lens/config.py` contains shared symbols, sectors and list limits.
- `tests/` contains offline `unittest` coverage with synthetic histories and a fake provider.

The UI requests a two-year daily history so that the 200-day and 252-close measures can be calculated when observations exist. The provider metadata wraps price history; profile, analyst, calendar, news and filing endpoints remain optional direct Yahoo Finance calls and may have separate freshness/coverage behavior.

## Headline research and method

The classifier now avoids counting a matched financial phrase again as individual sentiment words, uses phrase boundaries, and applies clause-local negation. It always shows Bullish or Bearish as requested; an uninformative tie is shown Bearish · Low signal and documented as a forced display choice rather than evidence.

Financial text needs domain-specific vocabulary. The [Loughran–McDonald dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/) was built for financial filings, while the FinBERT paper reports improvements over earlier methods on two financial sentiment datasets ([Araci, 2019](https://arxiv.org/abs/1908.10063)). Research has also evaluated negation-scope detection specifically on financial news ([Pröllochs et al., 2016](https://www.sciencedirect.com/science/article/pii/S0167923616300823)). Those findings motivate domain terms, phrase matching and negation handling, but do not validate this app's hand-built weights. The current implementation is not FinBERT, does not estimate probabilities, and has not been benchmarked against a human-labeled Market Lens headline set. It can still miss context, source credibility, company-specific effects and actual market reaction. Headline tone must not be interpreted as expected stock return.

## Tests executed

Command: `.venv\Scripts\python.exe -m unittest discover -s tests -v`

Final result: **35 tests passed** in 0.215 seconds. Coverage includes Wilder RSI edge cases, full-window and short-history calculations, missing values, exact horizon indexing, aligned returns across different time zones, beta sample counts and missing dates, realized volatility and drawdown coverage, full-year measure availability, recent/missing/stale/partial/failed provider states, local watchlist persistence, phrase scoring, negation and clause boundaries, offline glossary and mocked AI API handling, and legacy-safe rating explanations.

A separate mocked `streamlit.testing.v1.AppTest` render completed with no app exceptions. It exercises the full dashboard script with synthetic price data and no live provider requests.

Syntax check: `.venv\Scripts\python.exe -m py_compile app.py market_lens\analytics.py market_lens\charts.py market_lens\config.py market_lens\news.py market_lens\providers.py market_lens\storage.py` completed successfully.

Syntax compilation completed successfully.

## Known limitations

- Yahoo Finance/yfinance remains the only price source. Quote delay cannot be verified; missing, delayed, stale, rate-limited or changed endpoints remain possible.
- The detailed provenance envelope currently applies to primary stock price history and the market/sector price histories. Company profile, fundamentals, analyst, news, event and filing calls are still independent provider endpoints; some fail silently or do not carry per-response timestamps. The UI gives general source and coverage caveats, but these are not yet wrapped in equivalent per-endpoint envelopes.
- The watchlist is local, single-user JSON with no synchronization, account separation or encryption.
- For a public Cloudflare/Streamlit embed, set `MARKET_LENS_HOSTED=true` so watchlists remain session-local. This is not user authentication; the embedded market dashboard itself is publicly accessible when deployed as a public Streamlit Community Cloud app.
- The website embed is a prepared snippet only. It needs a deployed HTTPS Streamlit app URL and must be copied into the actual Cloudflare Pages site; the website source was not present in this project folder.
- The industry listing is a provider-curated directory, not a complete exchange security master. IPO, earnings and economic calendars may be preliminary or incomplete.
- Sector ETF breadth is not the fraction of all listed stocks advancing or trading above trend. There is no exchange advance/decline, equal-weight participation, credit-spread or market internals feed yet.
- Buy/Hold/Sell thresholds are transparent but unvalidated and equally weighted. They can lag, whipsaw and disagree with fundamental or portfolio considerations.
- Headline sentiment has no labeled evaluation set or calibrated confidence. Low/Medium/High are rule-based signal-strength labels, not probabilities or evidence that a stock will rise or fall.
- No live-provider UI session was run as part of the offline checks; provider behavior outside the fake fixtures depends on current Yahoo Finance availability.

## Recommended next version

1. Add primary-source SEC filing enrichment and endpoint-level freshness/error envelopes for fundamentals, events, analyst data and news.
2. Build an opt-in labeled headline evaluation set, measure precision/recall by event type, and compare the current rule engine with FinBERT before adopting a model.
3. Add true market breadth series (advance/decline, equal-weight participation and new highs/lows) and document their sources and sampling.
4. Add source links and observation counts beside each screening check, plus filters for market cap, liquidity, volatility and technical conditions in discovery.
5. Expand local preferences to multiple named watchlists only if useful; keep the app read-only and separate from Kestrel.
