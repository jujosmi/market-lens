# MarketLens Sprint 3A — Proposed Design System

**Status:** Proposal for independent review. No product styles or application code have been changed. Tokens below are proposed starting values, grounded in the existing `.streamlit/config.toml` palette and inline CSS. Validate contrast and rendered colors in Sprint 3B before treating them as final.

## 1. Design philosophy

**Professional Intelligence. Simplified.** Keep a calm, readable surface for standard workflows and reveal additional market detail in clearly named research panels. Let data hierarchy, spacing, alignment, and labels carry emphasis. Use color to reinforce a meaning already expressed in text; do not encode a Buy/Sell state or data quality only by hue.

Avoid decorative gradients, animated price decoration, excess pills, and large unexplained numbers. Keep market information dense when it supports comparison, but place definitions and source/freshness details nearby.

## 2. Proposed color tokens

The palette starts from the current MarketLens dark and light palette. Semantic values are restrained and should be checked against WCAG 2.2 AA for normal text (4.5:1) and large text (3:1) before implementation. Market directions should also include a label/icon or sign.

| Token | Light | Dark | Intended use |
|---|---|---|---|
| `--ml-bg` | `#F3F7F5` | `#0B1417` | Page background |
| `--ml-surface` | `#FFFFFF` | `#111D20` | Cards, panels, menus |
| `--ml-surface-raised` | `#F8FBF9` | `#172427` | Nested panel, selected row |
| `--ml-sidebar` | `#EAF1EE` | `#0E191C` | Persistent navigation surface |
| `--ml-text` | `#17312B` | `#EDF4F2` | Main text |
| `--ml-muted` | `#61756F` | `#A5B7B3` | Secondary labels and help text |
| `--ml-border` | `#DCE7E2` | `#26383A` | Dividers, outlines, table rules |
| `--ml-accent` | `#087F63` | `#76E0B2` | Selected controls, links, focus |
| `--ml-positive` | `#08734F` | `#8EE6B6` | Positive return/state |
| `--ml-negative` | `#B42335` | `#FF9999` | Negative return/state |
| `--ml-caution` | `#8A5B00` | `#FFD27D` | Warnings, risk, incomplete coverage |
| `--ml-info` | `#245B83` | `#91C7F4` | Informational notes |

Implementation should define one canonical set of CSS variables, then map both theme modes to it. Keep `.streamlit/config.toml`, Streamlit's runtime theme and the HTML assistant palette in sync. Confirm behavior in Dark, Light and System modes; avoid a second, conflicting color authority in component-specific styles.

## 3. Typography and number formatting

- **UI/body:** Manrope where available, with `system-ui`, `Segoe UI`, Arial and sans-serif fallbacks. Do not make content dependent on loading an external font.
- **Financial numbers:** DM Mono where available, with `ui-monospace`, Cascadia Mono and monospace fallbacks. Use tabular numerals so prices and percentages align.
- **Scale:** page title 30–36 px; workspace title 24–28 px; panel heading 18–22 px; body 14–16 px; table/body secondary 12–14 px; eyebrow/metadata 11–12 px. Keep minimum interactive labels readable at 13–14 px.
- **Hierarchy:** ticker and company name are prominent; exchange/sector are supporting context; price and change form the strongest numeric pair; source/as-of/status remain visible but subordinate.
- Use consistent currency, percentage, and unavailable formatting. Missing values should read “Unavailable” or “—” with a reason where useful, never `0` by default.

## 4. Spacing, grid, and surfaces

Use a 4 px base spacing scale: `4, 8, 12, 16, 24, 32, 40, 48`. Standard card padding is 16–20 px; larger desktop research panels can use 20–24 px. Keep vertical gaps predictable and avoid nested borders around every widget.

Use a responsive 12-column conceptual grid on desktop: page content max width around 1440 px with balanced outer margins; two-column areas favor roughly 7/5 or 6/6; four snapshot metrics use equal widths and wrap naturally. Do not hard-code a page width that prevents wide tables/chart interactions. On small screens, collapse multi-column metrics and research panes to one column.

### Cards and panels

- One outer frame per meaningful task group; use internal headings and dividers instead of nested cards for each individual table.
- Standard surface has a subtle 1 px border and 12–16 px radius. Avoid large shadows on every section.
- Selected cards and controls use a low-opacity accent tint plus a visible outline.
- Focus state uses a 2 px accent outline with at least 2 px offset; preserve visible keyboard focus.

### Tables

- Use descriptive, concise column names and one unit in headers (for example, “Revenue ($B)”).
- Right-align financial values; left-align labels; use tabular numerals and consistent precision.
- Make dates and source/status explicit. Keep null/missing values distinct from zero.
- Use restrained row separators and a subtle selected/hover row. Avoid relying on alternating color alone.
- Give narrow screens a deliberate horizontal scroll area and keep ticker/company identification visible where Streamlit permits. Do not hide financial columns silently.
- Prefer explicit column widths/formatters for the important user-facing tables, but do not truncate identifiers or statuses without an accessible alternative.

### Chart styling

- Preserve readable OHLC candles, volume, selected moving averages and fullscreen controls.
- Use consistent semantic up/down colors plus numeric change/sign. Ensure the selected average's line color is distinguishable and documented in a legend.
- Keep gridlines low contrast, price axis right-aligned, volume axis labeled, and crosshair/hover details legible in both themes.
- Use concise tooltips and do not draw inferred targets or predicted paths. Make interval, range, style, and average controls keyboard-accessible and plainly labeled.

## 5. Navigation treatments

- **Primary workspace navigation:** persistent sidebar with four concise destinations: Market Overview, Discovery, Company Research, Watchlist. Proposed names and exact grouping are detailed in the workspace blueprint.
- **Selected ticker:** persistent context control in the sidebar, with ticker and company identity visible in the Company Research workspace header. Search should remain distinct from current selection and explain whether choosing a result adds it, focuses it, or both.
- **Subnavigation:** short horizontal tabs or segmented controls within the active workspace. Company Research subnavigation groups existing Technical, Business & Valuation, and Estimates/Events/Filings content; each stays lazily loaded.
- **Active state:** use accent fill/left rail and a text or icon cue. Maintain the selection across reruns and show keyboard focus separately.
- **Breadcrumbs:** unnecessary on a shallow four-workspace hierarchy. Use a location label only if nested routes are introduced later.
- **Keyboard:** tab order follows visual order; nav choices, ticker search, industry buttons, chart controls and dialog close are operable by keyboard. Do not invent custom keyboard shortcuts until documented and conflict-checked.

## 6. Status, loading, empty, and error states

- **Loading:** local spinner or skeleton only around the requested data block. The rest of the workspace remains usable. Label the request in plain terms (e.g., “Loading quarterly statement”). Avoid blocking the full page for deferred research.
- **Available:** show value, unit, as-of date and provider where they help interpretation.
- **Partial:** say which part is incomplete and retain valid rows/metrics.
- **Missing:** explain that the provider returned no value; do not imply a provider outage.
- **Error:** concise user-facing message, retry/refresh path where appropriate; technical exception details go to logs, not the screen.
- **Empty search:** state that nothing matched and invite a changed query; do not present an empty table as a successful listing.
- **Informational:** neutral surface/icon, concise wording and no alarm color.
- **Warning:** text plus icon/label and caution color; never color alone.

## 7. Responsive behavior proposal

Breakpoints are initial design targets, not claims of current tested behavior. Validate actual Streamlit column stacking and generated DOM in supported browsers.

| Width | Proposed behavior |
|---|---|
| `>= 1200 px` | Expanded sidebar by default; 4-up snapshot metrics; chart/read-through two columns; Discovery selector can use a three-column button grid; tables use available width. |
| `768–1199 px` | Sidebar may collapse; snapshot metrics 2-up; chart controls wrap to two rows; market read follows chart if columns become cramped; Discovery buttons two columns; horizontal table scrolling stays inside its panel. |
| `< 768 px` | Sidebar collapsed until requested; one-column metric cards and research panels; touch controls at least 44 px target where practical; chart controls stack; avoid multi-column button grids; data tables scroll horizontally without shrinking text; floating assistant defaults to a compact, viewport-bounded bottom panel and must not obscure navigation or primary values. |

Do not reduce desktop data density solely to make mobile layouts simpler. Mobile can prioritize ticker lookup, snapshot, chart, key market read and access to each research section while keeping all current data reachable.

## 8. Accessibility and implementation notes

- Keep heading levels in order; label controls explicitly; ensure icon-only actions have accessible names.
- Check foreground/background contrast in both themes. Verify focus, hover, selected, disabled, warning and positive/negative states.
- Provide text labels or signs for sentiment/rating/returns, not color alone.
- Ensure chart interaction has a meaningful title and supporting data table or adjacent summarized values.
- Audit custom HTML assistant drag/minimize controls for keyboard and touch use; draggable movement must not be the only way to open/close it.
- Prefer native Streamlit controls and components. Keep custom CSS limited to stable, documented selectors when possible; isolate any unavoidable Streamlit DOM selectors and add upgrade regression checks.
- Keep shared token definitions in one theme module or stylesheet during Sprint 3B; derive widget styling and assistant theme from those tokens rather than duplicating literals.
