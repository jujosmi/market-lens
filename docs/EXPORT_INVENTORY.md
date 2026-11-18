# FULL_APP Export Inventory

Updated for Sprint P4D SEC-powered Discovery.

## Directory summary

- `frontend/` — React application, tests, assets, dependency lock, TradingView embed, Supabase foundation, and SQL migration.
- `backend/` — FastAPI app, official SEC adapter, SEC Discovery directory/filings routes, provider contracts, tests, and research snapshot.
- `scripts/` — local loopback startup/stop scripts.
- `docs/` — export integrity and existing project documentation.

Included file count: 
105

The package excludes Git metadata, real credentials, `.env.local`, virtual environments, node modules, build output, Python caches, and runtime logs. Only safe `.env.example` placeholders are included.

## Complete file list

- `.gitignore`
- `backend/.gitignore`
- `backend/app/__init__.py`
- `backend/app/contracts.py`
- `backend/app/engine_adapter.py`
- `backend/app/engine_fixtures.py`
- `backend/app/fixtures.py`
- `backend/app/main.py`
- `backend/app/providers/__init__.py`
- `backend/app/providers/cache.py`
- `backend/app/providers/contracts.py`
- `backend/app/providers/licensing.py`
- `backend/app/providers/synthetic.py`
- `backend/app/sec_edgar/__init__.py`
- `backend/app/sec_edgar/client.py`
- `backend/app/sec_edgar/discovery.py`
- `backend/app/sec_edgar/mapping.py`
- `backend/app/sec_edgar/service.py`
- `backend/engine_snapshot/__init__.py`
- `backend/engine_snapshot/analytics.py`
- `backend/engine_snapshot/discovery.py`
- `backend/engine_snapshot/news.py`
- `backend/engine_snapshot/research.py`
- `backend/engine_snapshot/snapshot-manifest.json`
- `backend/README.md`
- `backend/requirements-lock-py314.txt`
- `backend/requirements.txt`
- `backend/tests/test_api.py`
- `backend/tests/test_cors_config.py`
- `backend/tests/test_engine_parity.py`
- `backend/tests/test_licensing_and_sec_mapping.py`
- `backend/tests/test_providers.py`
- `backend/tests/test_sec_discovery.py`
- `backend/tests/test_sec_edgar_http.py`
- `docs/EXPORT_HASH_MANIFEST.csv`
- `docs/EXPORT_INVENTORY.md`
- `docs/EXPORT_VERIFICATION.md`
- `docs/history/SPRINT_P2A_AND_ACETERNITY_IMPLEMENTATION_REPORT.md`
- `docs/history/SPRINT_P2B_ENGINE_INTEGRATION/SPRINT_P2B_ENGINE_INTEGRATION_REPORT.md`
- `docs/LOCAL_DEVELOPMENT.md`
- `docs/p4a/SPRINT_P4A_AUTH_FLOW_TEST_RESULTS.md`
- `docs/p4a/SPRINT_P4A_AUTH_IMPLEMENTATION_REPORT.md`
- `docs/p4a/SPRINT_P4A_RLS_SECURITY_TESTS.md`
- `docs/p4a/SPRINT_P4A_SEC_ACCEPTANCE_STATUS.md`
- `docs/p4a/SPRINT_P4A_WATCHLIST_SCHEMA.sql`
- `docs/RENDER_CORS_STARTUP_FIX_REPORT.md`
- `docs/SOURCE_HASH_COMPARISON.md`
- `docs/THIRD_PARTY_NOTICES.md`
- `frontend/.env.example`
- `frontend/.gitignore`
- `frontend/components.json`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/public/jujosmi-logo.png`
- `frontend/README.md`
- `frontend/responsive-review.html`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/auth/AuthAccountMenu.tsx`
- `frontend/src/auth/AuthContext.tsx`
- `frontend/src/auth/database.types.ts`
- `frontend/src/auth/supabaseClient.test.ts`
- `frontend/src/auth/supabaseClient.ts`
- `frontend/src/auth/watchlistMigration.test.ts`
- `frontend/src/auth/watchlistRepository.test.ts`
- `frontend/src/auth/watchlistRepository.ts`
- `frontend/src/components/ExpandableResearchCard.test.tsx`
- `frontend/src/components/ExpandableResearchCard.tsx`
- `frontend/src/components/HelpGlossaryDialog.test.tsx`
- `frontend/src/components/HelpGlossaryDialog.tsx`
- `frontend/src/components/LandingPage.tsx`
- `frontend/src/components/ModalPanel.tsx`
- `frontend/src/components/PreferencesDialog.tsx`
- `frontend/src/components/PriceChart.test.tsx`
- `frontend/src/components/PriceChart.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/SpotlightCard.tsx`
- `frontend/src/components/TradingViewAdvancedChart.test.tsx`
- `frontend/src/components/TradingViewAdvancedChart.tsx`
- `frontend/src/components/ui/background-gradient-animation.tsx`
- `frontend/src/components/ui/hover-border-gradient.tsx`
- `frontend/src/components/WorkspaceTabs.tsx`
- `frontend/src/components/WorkspaceViews.tsx`
- `frontend/src/data/apiClient.test.ts`
- `frontend/src/data/apiClient.ts`
- `frontend/src/data/fixtures.ts`
- `frontend/src/data/tradingViewSymbols.ts`
- `frontend/src/data/workspaceFixtures.ts`
- `frontend/src/lib/utils.ts`
- `frontend/src/main.tsx`
- `frontend/src/preferences.test.ts`
- `frontend/src/preferences.ts`
- `frontend/src/styles.css`
- `frontend/src/test-setup.ts`
- `frontend/src/types.ts`
- `frontend/src/vite-env.d.ts`
- `frontend/supabase/migrations/202611150001_watchlist_items.sql`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `README.md`
- `scripts/start-local.ps1`
- `scripts/stop-local.ps1`
