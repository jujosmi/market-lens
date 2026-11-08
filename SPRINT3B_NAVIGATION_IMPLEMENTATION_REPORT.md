# MarketLens Sprint 3B — Navigation & Design Foundation

**Date:** 2026-11-07  
**Scope:** Navigation and design foundation only  
**Review package:** `FULL_APP`  
**Deployment:** None

## Summary

Sprint 3B organizes MarketLens into four persistent workspaces: Market Overview, Discovery, Company Research, and Watchlist. The default remains Market Overview. Only the active workspace renders its primary content; Discovery also skips the selected-ticker core payload that it does not use. The original data providers, rating logic, financial calculations, cache policy, and Discovery/Research feature implementations were preserved.

Shared light and dark semantic tokens now drive the page styling. Workspace-specific widget values are saved and restored around navigation so changing workspaces does not discard chart, Discovery, research, or watchlist selections. Headlines and sentiment are part of Company Research.

## Implementation

- `app.py`: persistent workspace selector, workspace-scoped rendering, Discovery core-data gating, shared theme variables, and headlines research tab. Existing feature calculations/loaders are retained.
- `market_lens/ui/navigation.py`: supported workspace definitions, state normalization, widget-state preservation, and core-data scope.
- `market_lens/ui/theme.py`: semantic light/dark palettes, typography stacks, spacing scale, and CSS variable generation.
- `tests/test_navigation.py`: regression coverage for workspace rendering/navigation, hidden-widget state restoration, data-load boundaries, lazy research activation, and token contrast.

The complete application runtime, static assets, configuration, website embed, dependencies, previous sprint reports, and tests are included in this review package. No changes were made to the Documents GitHub repository, and nothing was published or deployed.

## Verification

- Python compile check (`compileall app.py market_lens tests`): passed.
- Full test suite (`unittest discover -s tests`): **75 tests passed** in 2.105 seconds.
- Navigation-specific tests: **5 passed**, including a headless Streamlit AppTest through all four workspaces.
- AppTest verified that Discovery does not load selected-ticker core data, research requests remain tied to active research tabs, and chart/ticker/subview selections survive workspace changes.
- Theme token tests verified text contrast against the selected background. Minimum measured WCAG contrast ratios: light theme 4.54:1 (muted text), dark theme above 7:1. Other measured light-theme semantic colors were at least 4.60:1.

The suite emits existing Streamlit and Plotly deprecation/runtime-context warnings; they did not fail tests and are outside this sprint's scope. Tests ran with Python 3.13 although repository metadata specifies Python 3.14, so a Python 3.14 run remains a compatibility check for the review environment.

## Performance assessment

The comparable Sprint 2 Phase 2 baseline documented in `SPRINT2_PERFORMANCE_COMPARISON.md` measured a cold initial run at 15.92–17.68 seconds / 73 provider requests, warm reruns at 0.18 seconds / 0 requests, ticker switches at 1.54–1.63 seconds / 9 requests, and Discovery industry changes at 6.02–6.03 seconds / 32 requests. The Sprint 2B sample retained those request counts.

Sprint 3B makes the default page render one workspace at a time and gates selected-ticker core requests out of Discovery. This preserves the existing provider-loader/caching rules; the navigation regression harness verifies the loader boundaries with fixtures. A new live-provider benchmark was not run, so there is no measured Sprint 3B wall-time or Yahoo request-count delta to claim. Live request totals and elapsed times remain provider/cache dependent. The prior baseline is retained for independent comparison.

## Review limitations

- Validation used headless Streamlit AppTest; browser screenshots, responsive layouts, and manual keyboard navigation were not reviewed.
- Existing project warning/deprecation cleanup and Python 3.14 validation are not part of Sprint 3B.
- No Sprint 3C work, provider changes, algorithm/rating changes, deployment, or publication were performed.
