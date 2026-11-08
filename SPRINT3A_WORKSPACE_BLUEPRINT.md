# MarketLens Sprint 3A — Workspace Blueprint

**Status:** Proposed architecture for independent review. The four top-level workspaces below are recommendations; current source is a single dashboard page and does not yet have these routes. No new analysis or data provider is proposed.

## 1. Navigation decision

Use a persistent sidebar for **four** top-level workspaces:

1. **Market Overview** — selected-ticker snapshot and chart plus broad Market Pulse.
2. **Discovery** — Industry Directory, Earnings Soon, IPOs Soon and Other Events.
3. **Company Research** — detailed Technical & Relative Strength, Business & Valuation, Estimates/Events/Filings, and Headlines & Sentiment views for the selected ticker.
4. **Watchlist** — the existing multi-ticker snapshot table and industry filter, with the existing ticker edit/add/search controls kept in persistent sidebar context.

This proposal gives the existing features useful destinations without creating empty workspaces. Do **not** add a separate Advanced Analytics top-level destination: the current technical and detailed financial analysis already belongs within Company Research. Do **not** add Settings at this stage: theme selection is available from Streamlit's app menu, and no other settings surface exists.

Use the sidebar for stable workspace selection and ticker context. Use horizontal subnavigation inside Discovery and Company Research. Avoid a second top navigation row that repeats the workspace names. Breadcrumbs are not needed for a flat four-workspace hierarchy. Preserve the current quick links as optional in-page anchors only where a workspace still contains long content.

## 2. Proposed state model

Keep one selected ticker shared across the application. Proposed session-state keys:

- `market_lens_workspace`: one of Overview, Discovery, Company Research, Watchlist.
- `focus_ticker`: current selected symbol (existing key).
- `research_desk_tabs`: active Company Research subview (existing key, with name retained if feasible).
- `discovery_index_tabs`: active Discovery subsection (existing key).
- Existing watchlist/search/theme/chart keys remain stable through the first migration unless there is a tested reason to change them.

Changing workspace must not reset ticker, watchlist, chart preferences, industry selection, date window, or user theme. Selecting a new ticker should update the selected company header and all ticker-specific views on the next rerun. A Discovery company action should reuse the existing add-to-watchlist-and-focus behavior.

Do not include selected ticker, watchlist, or research tab defaults in a URL unless privacy, shareability and state-reset behavior are deliberately reviewed. Session state is sufficient for the first increment.

## 3. Proposed navigation and data boundaries

| Workspace | Existing content mapped here | Data-loading boundary |
|---|---|---|
| Market Overview | Selected ticker snapshot, expected move/trend/rating, price chart, market read and Market Pulse | Load core selected-ticker data and cached market context because existing rating/relative-return calculations consume them. Load chart-specific history only for a selected interval/range that needs a separate provider fetch. |
| Discovery | Searchable industry buttons and listings/ratings; earnings, IPO, split and economic-event calendars | Load the industry index/listing only while the directory subsection is active. Load only the selected calendar subsection. Keep company rating cache and bounded workers. |
| Company Research | Technical and relative performance tables; company profile/quarterly rows; targets/distribution/EPS revisions/analyst changes/earnings/filings; headlines | Load technical values from already cached core inputs. Fetch quarterly statements, catalyst fields, and headlines only for the selected subview/section. Preserve independent partial results and current five-minute research cache policy. |
| Watchlist | Current watchlist snapshot table, company/sector/industry, price/change/move/trend/rating/date/status and industry filter | Reuse selected snapshot and existing per-symbol caches. Do not fetch catalyst, quarterly, news, or unselected chart data. |

The selected ticker calculation currently also consumes broad market context. If the new workspace layout changes which page loads that context, preserve the current calculation inputs and reuse its existing cache; do not recompute ratings with a reduced data set to make navigation appear faster.

## 4. Proposed information hierarchy

### Market Overview

1. Compact page header: “Market Overview”, selected company/ticker, sector/industry and source/as-of status.
2. Four primary metrics: last close/change, 30-day expected move (clearly non-directional), trend read, and MarketLens rating with explanation.
3. Price chart with current interval/range/style/average controls and fullscreen action.
4. Concise Market Read adjacent to chart on wide screens, below chart on narrow screens.
5. Market Pulse: major indexes, VIX regime, 10-year Treasury proxy, S&P trend and collapsible sector rotation.

This groups the existing first-view market information. It does not add forecast cards or new indicators.

### Discovery

1. Header and event-window selector.
2. Subnavigation: Industry Directory, Earnings Soon, IPOs Soon, Other Events.
3. Directory: separate search field, selected industry label, keyboard-operable industry choices, and company/rating table.
4. Calendars: clear date range and provider coverage note, then a compact, labeled table.
5. Add/focus action on listed company results where the current source already supports it.

Do not display unavailable provider rows as confirmed empty classifications. Keep current Yahoo key validation and explicit error/missing states.

### Company Research

Persistent compact company header: ticker, company name, exchange if supplied, sector/industry, last close and daily change. Keep MarketLens rating and analyst consensus separately labeled because they use different inputs.

Subnavigation groups the existing views:

- **Technical & relative strength:** current signal checks, technical indicators, benchmark returns, and read-through.
- **Business & valuation:** profile metrics and quarterly income statement.
- **Analyst & company events:** target range/mean, recommendation distribution, EPS revisions, rating changes, earnings dates, and filings.
- **Headlines:** sentiment summary/filter, publisher/date, reason and story link.

This is a proposed clearer grouping of the current Research Desk and Headlines section. It does not change rating logic, add unsupported valuation ratios, or manufacture comparative analysis.

### Watchlist

1. Header with number of tickers and existing limit.
2. Existing company snapshot table with industry filter, clear status and as-of fields.
3. Sidebar remains the place to edit the comma-separated list, search/add a symbol, choose focus ticker and refresh selected-ticker data.

No portfolio, transactions, P&L, alerts, or cloud syncing is implied by the Watchlist name.

## 5. Wireframes

### Desktop — proposed

```text
┌──────────────────────┬────────────────────────────────────────────────────────────┐
│ MARKET LENS          │ Market Overview                                             │
│                      │ [Selected company / ticker / industry / source status]       │
│ ▸ Market Overview    │ [Last close] [Expected move] [Trend] [MarketLens rating]    │
│   Discovery          │ ┌──────────────────────────────┐ ┌───────────────────────┐ │
│   Company Research   │ │ Price chart + controls      │ │ Market Read           │ │
│   Watchlist          │ │                              │ │                       │ │
│                      │ └──────────────────────────────┘ └───────────────────────┘ │
│ Selected ticker      │ Market Pulse · indexes · VIX · rates · sector rotation       │
│ [search/select]      │ [index table] [regime panel]                                  │
│ Watchlist [edit]     │                                                              │
│ [refresh selected]   │                                                              │
└──────────────────────┴────────────────────────────────────────────────────────────┘
```

```text
Company Research · AMZN — Amazon.com, Inc. · Consumer Cyclical / Internet Retail
[Technical & relative strength] [Business & valuation] [Analyst & company events] [Headlines]
┌─────────────────────────────────────────┐ ┌─────────────────────────────────────┐
│ Active research view                    │ │ Context / related sourced data       │
│ indicators, table, analyst data, etc.    │ │ partial-data and as-of explanations  │
└─────────────────────────────────────────┘ └─────────────────────────────────────┘
```

### Mobile — proposed

```text
┌────────────────────────────────┐
│ ☰ Market Lens     [ticker ▾]   │  Sidebar/workspaces open on request
├────────────────────────────────┤
│ Market Overview                │
│ AMZN · company · as-of/status   │
│ Last close / daily change       │
│ Expected move                  │
│ Trend read                      │
│ MarketLens rating               │
│ [chart controls, stacked]       │
│ [price chart]                   │
│ [Market Read]                   │
│ [Market Pulse →]                │
└────────────────────────────────┘
```

On mobile, the four workspaces remain reachable from a compact menu; subviews can become horizontally scrollable tabs with visible focus and a clear selected label, or a labeled native select control if Streamlit tab widths prove unsuitable. Do not hide detailed rows or force chart controls below an unreachable fold.

## 6. Common user journeys

### Check a ticker already in the watchlist

1. Use the persistent ticker select/search in the sidebar.
2. Review company identity, price/date status, snapshot metrics and chart on Market Overview.
3. Open Company Research and choose Technical, Business, Analyst/Events, or Headlines.
4. Advanced data loads only when its subview is active; missing fields remain visibly missing.

### Find and add a company by industry

1. Open Discovery → Industry Directory.
2. Search by industry/sector, choose a button, and review the sourced company list with MarketLens ratings.
3. Choose the existing add/focus action on a company.
4. Market Overview updates to that company; Company Research uses the same selected ticker.

### Check upcoming earnings or IPOs

1. Open Discovery and choose the specific calendar subsection.
2. Choose the 30/60/90 day window.
3. Review returned dates and the source/coverage notice. Failed retrieval is distinct from no returned rows.

### Review the watchlist

1. Open Watchlist.
2. Filter by a known industry and compare existing snapshot columns.
3. Select a ticker in the sidebar to focus the overview and detailed research.

## 7. Streamlit implementation feasibility

The proposed four-workspace shell is feasible without changing frameworks. A sidebar `st.radio`/segmented control or equivalent keyed native selector can drive a session-state workspace key. Conditional rendering in the existing app entry point can preserve shared ticker state and avoid running inactive UI branches. A full multi-page `st.navigation` conversion is possible but not necessary for a shallow four-workspace hierarchy and would require extra review of shared state, entry-point behavior and caches.

Within Company Research and Discovery, either retain keyed `st.tabs(on_change="rerun")` with `load_tab_data_if_active()` or use a single active-subview control that renders only one content branch. The latter can make active state and keyboard navigation clearer, but must be tested to ensure Streamlit reruns do not reset user choices. Avoid wrapping each view in a separate `st.tabs` and then doing all expensive loads before checking selection.

Native Streamlit handles layout, controls, tables, metrics, dialogs and spinners. A small CSS layer may be needed for design tokens, active-nav treatment, chart/panel spacing and responsive adjustments. Keep `components.html` limited to existing assistant functionality; do not introduce custom JavaScript navigation unless a native control cannot meet an identified need.

## 8. Proposed vs existing feature labels

**Existing:** all content/data in the audit's confirmed-capability section.  
**Proposed:** the four persistent workspace destinations, compact shared ticker header, the Market Overview grouping, Company Research grouping of Headlines with research, and responsive rearrangement shown in the wireframes.  
**Not proposed:** new research metrics, account settings, trade actions, portfolio tracking, company comparisons, or provider/data-layer changes.
