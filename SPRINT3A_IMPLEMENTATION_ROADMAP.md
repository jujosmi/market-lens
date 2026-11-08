# MarketLens Sprint 3A — Implementation Roadmap

**Status:** Planning proposal only. This roadmap is not authorization to start Sprint 3B. Each phase requires independent review and explicit go-ahead before implementation.

## Guardrails across all phases

- Preserve the existing market formulas, MarketLens rating checks, analyst recommendation use, expected-move interpretation, sentiment rules, and statement normalization.
- Preserve active-tab/active-workspace-only requests, cache TTLs and arguments, selected-ticker cache invalidation, recommendation-cache sharing, Discovery cache behavior and bounded parallel work.
- Keep valid partial data visible and distinguish missing values from request failures.
- Do not add a framework, provider, financial product feature, or dependency without separate review.
- Capture the Phase 2 baseline before UI work: optimized two-run means were approximately 16.8 seconds / 73 requests for cold initial load and 6.0 seconds / 32 requests for an industry switch; warm rerun was about 0.18 seconds / 0. Sprint 2B's later single live sample had slower elapsed time but the same request counts. Compare multiple runs under matched conditions and report request counts as well as time.

## Sprint 3B — Navigation & Design Foundation

**Goal:** Establish shared UI tokens and a persistent, stateful workspace shell while keeping the existing content and calculations.

**Likely files:**

- `app.py` — workspace state, sidebar navigation, active-workspace rendering boundary.
- New `market_lens/ui/theme.py` or `market_lens/ui/tokens.py` — shared palette and semantic tokens.
- New `market_lens/ui/styles.py` or a static stylesheet under `static/` — small centralized CSS layer.
- `.streamlit/config.toml` — keep Streamlit's light/dark palettes aligned with tokens.
- `market_lens/chat_component/index.html` — only if needed to keep its colors synchronized; keep component event contract.
- `tests/test_navigation.py`, `tests/test_ui_tokens.py` (new) — proposed tests.

**Tasks:**

1. Add four workspace destinations: Market Overview, Discovery, Company Research, Watchlist.
2. Keep selected ticker, watchlist, search, chart settings, industry/event selection and theme across workspace changes.
3. Introduce one source for light/dark semantic tokens and map them to Streamlit and the assistant.
4. Extract or consolidate styling without changing layout or calculations beyond what navigation needs.
5. Keep inactive workspace provider loaders out of execution; reuse the existing cached core data when multiple views need the same calculations.
6. Retain an accessible in-page location cue and keyboard-operable native navigation.

**Dependencies:** Approved workspace blueprint and token palette; review of Streamlit version and state behavior.

**Risks:** Streamlit reruns may reset or unexpectedly persist selected tabs; multiple `st.tabs` may still instantiate UI branches; CSS targets can change with Streamlit upgrades; routing may accidentally cause an inactive page to fetch data. Theme state may be influenced by both Streamlit's menu and custom assistant messages.

**Regression checks:** Existing full unit suite; AppTest navigation through all four workspaces; verify selected ticker/watchlist/industry and theme state persists; assert optional loader call counts for inactive workspaces; assert ticker refresh still clears only selected-symbol caches; verify assistant theme and message event handling.

**Acceptance criteria:** Workspace selection has an obvious active state; selection survives reruns; all existing content is reachable; no extra provider requests occur solely from visiting an unrelated workspace; both themes have legible surfaces; all previous tests pass.

**Relative complexity:** Medium.

## Sprint 3C — Dashboard & Research Workspace

**Goal:** Organize the existing first-view snapshot/chart/Market Pulse and detailed company research into a clearer information hierarchy.

**Likely files:**

- `app.py` — Market Overview and Company Research composition, shared company header, responsive column ordering.
- `market_lens/charts.py` — only presentation parameters/legend behavior if needed; preserve data and interval logic.
- `market_lens/ui/components.py` or `market_lens/ui/` modules — reusable headers, metric cards, status blocks and tables if Sprint 3B justifies this extraction.
- `tests/test_ui_rendering.py`, AppTest cases (new) — content and lazy loading.

**Tasks:**

1. Place the existing selected-ticker snapshot/chart and broad market context in Market Overview.
2. Keep the ticker/company header consistent and visible in Company Research.
3. Group current Technical, Business/Valuation, Analyst/Events/Filings, and Headlines content under Company Research subnavigation.
4. Use shared presentation components for repeated status/source/metric treatment; pass already calculated or normalized data into them.
5. Tune chart-control order, panel hierarchy and narrow-screen stacking using current chart capabilities.
6. Preserve the same provider and data dependencies when a view is moved.

**Dependencies:** Sprint 3B shell and tokens. No additional backend research is needed for the proposed content.

**Risks:** Moving a loader across a workspace boundary can make it run by default; duplicating the snapshot in Overview and Research can create confusion; recreating calculations in a card helper risks inconsistent ratings; chart configuration can lose persisted range/style state.

**Regression checks:** AppTest asserts key metrics and section labels render for selected tickers; existing financial/research presentation tests; verify active research view loads the expected optional source and inactive views do not; test ticker changes and chart preferences; test light/dark chart configuration.

**Acceptance criteria:** Standard ticker workflow reaches company identity, price/change, expected move, trend, rating and chart without requiring knowledge of advanced terms; detailed current analysis remains accessible; calculations and source statuses are unchanged; no repeated provider requests are introduced by the new header/components.

**Relative complexity:** Medium to high.

## Sprint 3D — Advanced Research & Discovery

**Goal:** Make existing detailed data easier to find, compare visually and interpret without changing rating/data logic.

**Likely files:**

- `app.py` — Discovery subnavigation, directory layout, event tables, research subview labels and data-status placement.
- `market_lens/research.py` — only presentation-normalization additions required by evidenced fields; not new financial formulas.
- `market_lens/discovery.py` — only if needed to expose existing validated listings cleanly; preserve keys/fallback validation.
- `market_lens/ui/components.py` — reusable table/status/empty-state presentation.
- `tests/test_discovery_ui.py`, `tests/test_research_views.py` (new or expanded).

**Tasks:**

1. Keep Discovery's industry search visibly separate from the industry choice list and make selection feedback clear.
2. Separate event-calendar subnavigation from the directory and show the selected date window/source coverage.
3. Make existing rating/source distinctions explicit (MarketLens technical rating versus analyst consensus).
4. Align quarterly data, valuation metrics, targets, revisions, filings, and headlines with the shared table and status patterns.
5. Review row density and horizontal overflow on company listings, sector tables and watchlist.
6. Keep unavailable classifications and missing provider fields explicitly unfilled.

**Dependencies:** Approved Sprint 3C research groupings; existing Sprint 2B normalized research APIs.

**Risks:** Reordering tabs may change Streamlit state keys; adding extra table transformations may obscure provider values; over-compressing tables can hide source/quality context; Discovery new-category navigation must preserve verified industry lookup and rating-cache boundaries.

**Regression checks:** Discovery search/filter/select and active company listing tests; valid/empty/error response fixtures; missing cells remain missing; ratings/analyst consensus labels remain distinct; calendar tabs load only their own categories; compare request counts for first visit and return to a cached industry.

**Acceptance criteria:** Users can identify their current Discovery or research subsection; company identity and data status remain visible; current researched fields and operations stay reachable; no invented values or extra rating path appears; lazy-load and cache tests pass.

**Relative complexity:** Medium.

## Sprint 3E — Responsive Polish & Regression Testing

**Goal:** Validate the full navigation/design system across themes, viewport sizes and common user journeys.

**Likely files:**

- `app.py`, `market_lens/ui/` styles/components, `.streamlit/config.toml` — targeted presentation fixes only.
- `market_lens/chat_component/index.html` — assistant touch/keyboard/viewport bounds if issues are found.
- `tests/test_responsive_contracts.py` (structural checks) and documented manual QA checklist; visual/browser test tooling only if already available or separately approved.
- `SPRINT3_IMPLEMENTATION_REPORT.md` (new) — final implementation evidence after authorized phases.

**Tasks:**

1. Review desktop, laptop, tablet and mobile layouts at the proposed ranges.
2. Test keyboard navigation, focus order, screen-reader labels, dialogs, tables, chart controls, and assistant controls.
3. Verify both theme modes and semantic state contrast; test with external font unavailable.
4. Test current-user journeys: change ticker, add from search, industry discovery/add-to-watchlist, view events, open each research section, filter headlines, refresh selected ticker and refresh market pulse.
5. Run full tests and compare multiple performance runs against the recorded baseline; isolate network timing from request counts.
6. Document remaining limitations instead of obscuring features or dropping data.

**Dependencies:** Sprint 3B–3D changes and acceptance; availability of browser/device validation or an agreed screenshot/browser test setup.

**Risks:** Responsive CSS can break Streamlit's generated layout; custom drag behavior can escape the viewport; a theme contrast fix can be insufficient in the alternate theme; test snapshots can vary due to provider state; network latency can be misread as UI regression.

**Regression checks:** Full unit and AppTest suites; 2+ comparable timing samples per performance workflow; explicit Yahoo request counts and cache observations; browser review at representative widths; keyboard-only and light/dark checks.

**Acceptance criteria:** No critical content/control is inaccessible at supported widths; all core tasks work with keyboard; dark/light themes have clear semantic states; data and calculations match pre-Sprint-3 behavior; optional providers stay deferred; performance changes are explained with comparable request counts and timings.

**Relative complexity:** Medium to high, mostly due to breadth of validation.

## 5. Approval gates and design decisions

Before Sprint 3B, request architectural review and approval for:

1. The four workspace names and proposed grouping.
2. Whether Market Overview remains the first landing view and contains the current selected-ticker chart and snapshot.
3. Whether Headlines belongs as a Company Research subview (recommended) or remains a dashboard section.
4. The initial token palette and responsive breakpoints after contrast review.
5. The specific Streamlit navigation control and state strategy after a small AppTest proof.

Do not start Sprint 3B until those decisions receive approval. Do not treat this planning document as approval to change code, dependencies, data loading, calculation behavior, production deployment, or GitHub state.
