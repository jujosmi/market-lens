# Market Lens

Market Lens is a local stock watchlist and research dashboard. It helps you observe market conditions, compare stocks and sectors, review company information and read recent headlines. It is a standalone viewer: it has no brokerage connection and cannot place trades.

## Light and dark appearance

Market Lens includes a coordinated light palette and dark palette for the dashboard, sidebar, cards, chart, and floating terminology chat. Use Streamlit's app menu (⋮) and choose **Light**, **Dark**, or **System**. The default is dark.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Enter up to eight ticker symbols in the sidebar. The watchlist is saved to `.market_lens_watchlist.json` in this project folder and stays local to this computer.

## Main views

- **Market pulse:** SPY, QQQ, IWM and DIA returns, VIX, a 10-year Treasury yield proxy, S&P 500 moving-average alignment and sector ETF breadth.
- **Sector rotation:** eleven sector ETF performance rankings and excess returns against SPY over one and three months.
- **Stock research:** adjusted daily prices, full-window moving averages, RSI, MACD, volatility, beta, drawdown, relative returns versus SPY, fundamentals, estimates, events, filing links and news.
- **Discovery:** searchable industry categories, company listings, ticker search suggestions, earnings and IPO calendars, splits and economic events.
- **Watchlist:** persistent symbols, industry filtering and an explainable rule-based Buy / Hold / Sell screen.
- **Hover help and terminology assistant:** snapshot cards explain their readings on hover. A draggable corner helper answers common terms offline and supports open-ended AI explanations when configured.

## Enable AI chat

The built-in glossary works without an API key. To enable open-ended AI explanations locally, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, replace the placeholder with your own OpenAI API key, and restart Streamlit:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

For a hosted app, add `OPENAI_API_KEY = "your-api-key"` in the Streamlit host's Secrets settings. Keep the real key out of GitHub and Cloudflare website files; `.gitignore` excludes the local secrets file. The key remains server-side. When AI is enabled, the user's question and recent chat are sent to OpenAI; the watchlist and market data are not attached automatically. API usage may incur charges. Answers are for terminology education, not security recommendations or live market research. The model can be changed with `MARKET_LENS_AI_MODEL` in an environment variable or Streamlit secret.

## How the calculations work

The calculations live in `market_lens/analytics.py` and operate on trading observations:

- A 20-, 50- or 200-day simple moving average uses exactly that many valid closes. It is unavailable before then.
- RSI is Wilder's 14-period calculation, seeded with the first 14 daily changes and recursively smoothed. No losses maps to 100; no gains maps to 0; a flat series maps to 50.
- An `n`-session price return uses `n + 1` closes. Relative returns first align the stock and SPY closes by shared calendar dates.
- Beta uses matched daily returns only, needs at least 60 paired observations, uses at most the latest 120, and exposes the sample count in the calculation output.
- Realized volatility is the sample standard deviation of 30 daily returns, annualized by `sqrt(252)`. It is unavailable without all 30 returns.
- 52-week range and maximum drawdown require 252 closes. Missing windows stay unavailable instead of being presented as full-year values.
- The rating uses five equally weighted constructive and five caution checks. It only emits Buy, Hold or Sell when every required input exists; otherwise it shows Unavailable. It is not a validated prediction or personalized recommendation.

## News sentiment

`market_lens/news.py` contains inspectable finance-specific phrases, weighted terms, a short negation scope and a binary Bullish / Bearish output with Low / Medium / High heuristic signal. Phrase matches are not double-counted as separate word matches. A tie is displayed as Bearish · Low signal to preserve the requested two-way display; that is a forced label, not evidence of bearish news.

Financial language benefits from domain-specific treatment: the [Loughran–McDonald dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/) was developed for financial text, and [FinBERT research](https://arxiv.org/abs/1908.10063) finds finance-trained contextual models outperform earlier approaches on financial sentiment tasks. This app uses a transparent local ruleset, not a trained or calibrated model. It can miss context, sarcasm, source quality and company-specific meaning. Headline tone does not predict stock returns. Read the linked story and verify material claims against company releases or filings.

## Data reliability and limitations

Market history is retrieved through `market_lens/providers.py`, which wraps the current Yahoo Finance / yfinance source in a small provider interface. The main stock history displays source, retrieval time, interval, last observation, freshness status and any warning. Broad-market and sector tables include each result's observation date and status. Yahoo quote delay is not verifiable through this provider, so the app says so rather than claiming real-time data. Status values distinguish recent, stale, partial, missing and failed responses.

`market_lens/charts.py` holds chart construction; `market_lens/config.py` holds shared settings; `market_lens/storage.py` stores the local watchlist; and `market_lens/news.py` handles headline scoring. The Streamlit UI remains in `app.py`. The watchlist is a single-user local JSON file, not synced or encrypted.

For a shared hosted deployment, set `MARKET_LENS_HOSTED = "true"` in Streamlit secrets. That keeps each watchlist in its visitor's session instead of using a server-wide file. Hosted session watchlists reset when the browser session ends; this setting is not an authentication system.

## Put it on a Cloudflare website

Cloudflare Pages hosts website files; it does not run this Streamlit/Python app as a static page. Host Market Lens separately (for example, deploy it from GitHub to Streamlit Community Cloud), then copy the responsive iframe snippet in [`website_embed/market-lens-iframe.html`](website_embed/market-lens-iframe.html) into the Cloudflare Pages site and replace its placeholder URL. Streamlit Community Cloud supports embedding public apps; private app embeds are not officially supported. The `?embed=true` view hides Streamlit's toolbar and surrounding padding. Read [`website_embed/README.md`](website_embed/README.md) for setup and hosted watchlist isolation instructions.

The VIX is an options-implied measure of expected S&P 500 volatility over about 30 days; it does not indicate direction. See [Cboe's VIX FAQ](https://www.cboe.com/tradable_products/vix/faqs). Expected move is a volatility range, not a directional target or probability. The options fallback uses a small sample of near-the-money implied volatility quotes; it is not a constant-maturity volatility surface. Sector ETF returns are proxies and sector breadth is not the same as the share of all listed stocks above a trend threshold.

Company, analyst, news, industry and event coverage comes mainly from Yahoo Finance via the community-maintained [`yfinance`](https://ranaroussi.github.io/yfinance/) package. It may be delayed, incomplete, rate limited or unavailable, and Yahoo may change access. IPO and earnings dates can change; an earnings release date is not necessarily an earnings-call time. SEC filing links are third-party links when returned; [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) is the primary record for U.S. filings. Confirm important details with original sources.

## Tests

The offline unit tests use synthetic or fixed data and do not need live market access:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

This dashboard is informational and is not financial advice.
