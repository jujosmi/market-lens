# MarketLens Sprint 3A — UI Architecture Audit

**Scope:** Read-only review of the current source and repository documentation. This audit documents what is present in the reviewed code, separates observations from proposals, and does not authorize implementation.

**Reviewed:** `app.py`, `.streamlit/config.toml`, `market_lens/` modules, tests, `README.md`, and `website_embed/README.md` in the MarketLens repository. The entry points are `app.py` (canonical) and `streamlit_app.py` (compatibility wrapper). No `AGENTS.md` was found in the source tree.

## 1. Application structure

MarketLens is currently a single-page Streamlit application. `app.py` owns `configure_app()`, the cached data-loading functions, UI state helpers, and `run_app()`. `run_app()` renders the sidebar and the full vertical dashboard in a fixed sequence. It imports calculations, chart construction, provider access, research normalization, cache policy, local storage, sentiment, explanations, and the chat component from `market_lens/`.

The UI is built with native Streamlit containers, columns, metrics, dataframes, buttons, select boxes, expanders, spinners, alerts, and keyed `st.tabs`. The main content sections use bordered containers. A short custom HTML quick-navigation row links to in-page anchors. The page uses `layout="wide"` and starts with the sidebar expanded.

Custom styling lives in a long inline CSS block in `configure_app()`. It defines CSS variables from an active light/dark palette, styles Streamlit's generated elements, imports Manrope and DM Mono from Google Fonts, and defines the cards, section frames, pills, quick navigation, metric help tooltips, sidebar, tabs, and floating chat position. `.streamlit/config.toml` separately defines Streamlit theme palettes and static serving. The custom movable terminology assistant is an HTML component in `market_lens/chat_component/index.html`, initialized by `market_lens/assistant.py` and hosted through `streamlit.components.v1`.

## 2. Current navigation and user workflows

### Sidebar

- Jujosmi logo links to `jujosmi.com`.
- A comma-separated text field edits the watchlist (up to eight symbols); a ticker/company search returns Yahoo Finance matches that can be added to the list.
- A select box chooses the ticker analyzed in the dashboard.
- A Signal Guide explains that the Buy/Hold/Sell screen is rule-based and that expected move is non-directional.
- **Refresh data** invalidates the selected ticker's caches. Hosted mode is described in the sidebar when enabled.
- Theme switching currently relies on Streamlit's app menu; there is no MarketLens Settings workspace or in-app theme settings panel.

### Main page order

1. Brand/hero and in-page quick navigation.
2. Selected company/provider-data metadata and the **Selected ticker snapshot**.
3. Price chart with selectable bar interval, date range, Candles/Line style, moving averages, and fullscreen dialog; adjacent trend, momentum, and volatility explanation.
4. **Discovery Index** with industry directory, earnings, IPO, and other-event tabs.
5. **Market pulse** with SPY/QQQ/IWM/DIA, VIX, a 10-year Treasury proxy, S&P 500 moving-average regime, sector ETF rotation, data dates/status, and Refresh pulse.
6. **Research desk**, whose tabs are Technical & Relative Strength, Business & Valuation, and Estimates, Events & Filings.
7. **Headlines & sentiment**, including Bullish/Bearish/Neutral filtering and a methodology expander.
8. **Watchlist snapshot** table with an industry filter.
9. Movable terminology assistant.

### Discovery Index

Industry Directory has a separate search field and a scrollable three-column button directory. Choosing an industry loads a company table that includes MarketLens ratings, and eligible rows can be added to the watchlist. The other tabs show earnings dates, upcoming IPOs, economic events, and splits. The event window is 30, 60, or 90 days. Each tab is guarded so its provider data is fetched only when selected. Industry listings use Yahoo's verified industry keys or documented validated fallback behavior.

### Company research views

- Technical & Relative Strength shows moving averages, RSI, MACD, realized volatility, beta, 52-week range, drawdown, relative volume, S&P 500 returns, a read-through, and the existing MarketLens technical rating checks.
- Business & Valuation renders profile/valuation metrics and reported quarterly income rows. It uses statement-row aliases and preserves missing provider cells.
- Estimates, Events & Filings shows analyst targets, the shared recommendation distribution, EPS revisions, analyst rating changes, earnings dates, and SEC filings where returned.
- The tab activation callback and `load_tab_data_if_active()` defer quarterly statements and catalyst research until their view is active.

### Watchlist and data state

Local watchlists are persisted as JSON by `market_lens/storage.py`. README documents session-isolated watchlists in hosted mode; that is not account syncing or authentication. Streamlit session state holds current selections and UI state. Most Yahoo-backed loaders are cached; selected-ticker refresh clears only matching ticker entries. Analyst recommendations are shared by snapshot and Discovery rating paths. These are performance and data-integrity constraints for any new navigation.

## 3. Confirmed capabilities and non-capabilities

**Present in reviewed source:** watchlist editing and filtering; symbol suggestions; selected-ticker research; industry search and selection; calendar tabs; market pulse; chart styles, ranges, intervals, averages and fullscreen view; technical, fundamentals and analyst research; headlines/sentiment; explanations; optional AI terminology chat; theme support; cache refresh controls; local/hosted watchlist storage modes.

**Not present as standalone functionality:** separate routed Overview/Discovery/Research/Watchlist pages; a persistent workspace navigation menu; a dedicated Settings workspace; account profiles or cloud-synced watchlists; trading/order entry; portfolio holdings/performance; company comparison workspace; additional analyst calculations beyond the current sourced fields. These must not be presented as existing functionality in Sprint 3 planning.

## 4. Usability weaknesses observed in source

- The vertical page is long. The quick-nav anchors help jump to sections but do not provide a persistent workspace location, clear active state, or in-section navigation after reruns.
- All primary areas are rendered in one document. Users distinguish workspace areas by scroll position and section headings rather than by a persistent location indicator.
- Discovery and Market Pulse appear between the ticker snapshot/chart and the Research Desk. A user moving among company analyses may need to cross unrelated market-wide content.
- The sidebar combines watchlist editing, search, ticker focus, guidance, and refresh controls. It is useful as a persistent ticker context but is not currently a workspace navigator.
- Multiple tab systems are nested within the page. Tabs are functional and lazy-loaded, but users can confuse Discovery calendars with company research subviews.
- The Industry Directory button set can be long; it is searchable and scrollable, but keyboard focus and narrow-screen density deserve explicit QA.
- Tables carry high information density. Long column sets, generated dataframe sizing, and Streamlit horizontal overflow can make comparison difficult on laptop/tablet widths. The company directory currently includes provider listing labels and data fields as well as ratings.
- The chart's controls are compact and the chart shares its panel with a neighboring Market Read. On narrow screens, chart-control wrapping and fullscreen-dialog sizing need validation.
- Custom CSS targets Streamlit implementation selectors such as `data-testid`, generated keys, and BaseWeb tab attributes. Streamlit upgrades can change these selectors.
- The floating assistant can obscure content and its saved x/y position is only clamped at zero in Python; it is not visibly clamped to viewport dimensions. Its HTML/JS keyboard, screen-reader, and touch behavior needs focused accessibility testing.
- Typography imports from Google Fonts at runtime; offline/restricted environments depend on browser fallback fonts.
- A provider failure in the main initial data load currently reaches a broad `st.error(str(exc))` path; implementation planning should maintain the Sprint 2B principle of user-friendly errors while keeping technical detail in logs.

## 5. Architecture constraints and preserved behavior

- Keep Streamlit and the current Python calculation/data layers; this audit found no demonstrated requirement that necessitates a framework migration.
- Navigation changes must maintain the selected ticker and watchlist when users change workspace.
- Do not call optional data loaders for inactive workspaces/tabs. In particular, preserve separate deferred chart history, statement, catalyst, calendar, and headlines paths.
- Preserve cache keys, selected-ticker invalidation, analyst cache sharing, Discovery caching, rating calculations, and normalized research output.
- Do not recompute or duplicate Buy/Hold/Sell, analyst consensus, expected-move, return, volatility, or sentiment logic in presentation components.
- Preserve source/freshness/status, missing-value, and warning presentation. Never turn an empty response into a zero or inferred classification.
- Preserve public-deployment protection and per-visitor hosted watchlist behavior.
- Since the app currently has no authentication/settings surface, do not add one in the name of navigation cleanup.

## 6. Main recommendation

Use a persistent workspace selector in the sidebar and keep selected ticker context available across workspaces. Consolidate detailed ticker views into a Company Research workspace. Keep advanced analysis as subnavigation within that workspace rather than a parallel copy of the same data. Use clear top-level sections for Market Overview, Discovery, Company Research, and Watchlist. Do not add Settings until a real user-facing setting beyond Streamlit's theme menu is in scope.

The concrete hierarchy and migration boundaries are documented in `SPRINT3A_WORKSPACE_BLUEPRINT.md`; proposed tokens and responsive states are in `SPRINT3A_DESIGN_SYSTEM.md`.
