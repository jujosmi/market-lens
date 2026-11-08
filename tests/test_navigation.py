from __future__ import annotations

import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

import app
from market_lens.providers import DataEnvelope
from market_lens.ui.navigation import (
    DEFAULT_WORKSPACE,
    RESTORE_PENDING_KEY,
    SAVED_WIDGET_STATE_KEY,
    WORKSPACES,
    WORKSPACE_KEY,
    initialize_workspace_state,
    restore_workspace_widget_state,
    save_workspace_widget_state,
    workspace_requires_ticker_data,
)
from market_lens.ui.theme import DARK_TOKENS, LIGHT_TOKENS, css_variable_declarations, get_theme_tokens


def _luminance(color: str) -> float:
    rgb = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _market_fixture() -> tuple[dict, dict, DataEnvelope]:
    index = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=300)
    close = np.linspace(70.0, 150.0, len(index)) + np.sin(np.arange(len(index)) / 5)
    history = pd.DataFrame(
        {
            "Open":close - 0.4,
            "High":close + 0.8,
            "Low":close - 0.9,
            "Close":close,
            "Volume":np.full(len(index), 1_000_000),
        },
        index=index,
    )
    envelope = DataEnvelope(
        history, "Fixture", datetime.now(timezone.utc), "1d", "recent",
        last_observation=index[-1].isoformat(), provider_delay="unknown",
    )
    recommendations = pd.DataFrame(
        [{"period":"0m", "strongBuy":14, "buy":44, "hold":3, "sell":0, "strongSell":0}]
    ).set_index("period")
    info = {
        "longName":"Example Corporation",
        "sector":"Technology",
        "industry":"Software Infrastructure",
        "marketCap":2_000_000_000_000,
        "trailingPE":30.0,
        "forwardPE":25.0,
        "numberOfAnalystOpinions":61,
    }
    payload = {
        "history":history,
        "history_result":envelope,
        "info":info,
        "optional_warnings":[],
        "options_move":0.04,
        "options_expiry":"2026-12-18",
        "recommendations":recommendations,
        "recommendation_status":"available",
        "recommendation_message":None,
        "profile_status":"available",
    }
    context = {"SPY":history, "_metadata":{"SPY":envelope}}
    return payload, context, envelope


class NavigationStateTests(unittest.TestCase):
    def test_four_workspaces_and_default_state(self):
        self.assertEqual(
            WORKSPACES,
            ("Market Overview", "Discovery", "Company Research", "Watchlist"),
        )
        state = {}
        self.assertEqual(initialize_workspace_state(state), DEFAULT_WORKSPACE)
        self.assertEqual(state[WORKSPACE_KEY], DEFAULT_WORKSPACE)
        state[WORKSPACE_KEY] = "not-a-workspace"
        self.assertEqual(initialize_workspace_state(state), DEFAULT_WORKSPACE)

    def test_only_discovery_skips_selected_ticker_core_loader(self):
        self.assertFalse(workspace_requires_ticker_data("Discovery"))
        for workspace in ("Market Overview", "Company Research", "Watchlist"):
            with self.subTest(workspace=workspace):
                self.assertTrue(workspace_requires_ticker_data(workspace))

    def test_workspace_specific_widget_state_survives_widget_pruning(self):
        original = {
            "market_chart_interval":"1 hour",
            "market_chart_range":"1D",
            "market_chart_style":"Line",
            "market_chart_averages":["20 bar"],
            "research_desk_tabs":"Business & valuation",
            "discovery_index_tabs":"IPOs soon",
        }
        state = dict(original)
        save_workspace_widget_state(state)
        saved = state[SAVED_WIDGET_STATE_KEY]
        self.assertEqual(saved["market_chart_interval"], "1 hour")
        self.assertEqual(saved["research_desk_tabs"], "Business & valuation")
        self.assertEqual(saved["discovery_index_tabs"], "IPOs soon")
        for workspace, keys in (
            ("Market Overview", ("market_chart_interval", "market_chart_range", "market_chart_style", "market_chart_averages")),
            ("Company Research", ("research_desk_tabs",)),
            ("Discovery", ("discovery_index_tabs",)),
        ):
            with self.subTest(workspace=workspace):
                restored = {SAVED_WIDGET_STATE_KEY:saved, RESTORE_PENDING_KEY:True}
                restore_workspace_widget_state(restored, workspace)
                for key in keys:
                    self.assertEqual(restored[key], original[key])
                self.assertFalse(restored[RESTORE_PENDING_KEY])

    def test_theme_tokens_include_both_modes_and_accessible_semantic_text(self):
        self.assertEqual(get_theme_tokens("light"), LIGHT_TOKENS)
        self.assertEqual(get_theme_tokens("dark"), DARK_TOKENS)
        for name, tokens in (("light", LIGHT_TOKENS), ("dark", DARK_TOKENS)):
            with self.subTest(theme=name):
                for role in ("text", "muted", "accent", "bull", "bear", "caution", "info"):
                    self.assertGreaterEqual(_contrast(tokens[role], tokens["background"]), 4.5)
                declarations = css_variable_declarations(tokens)
                self.assertIn("--market-lens-font-body:", declarations)
                self.assertIn("--market-lens-font-financial:", declarations)
                self.assertIn("--ml-space-8:48px", declarations)

    def test_headless_app_navigation_routes_and_preserves_state(self):
        payload, context, envelope = _market_fixture()
        history = payload["history"]
        earnings_result = {
            "Earnings":pd.DataFrame(), "IPOs":pd.DataFrame(),
            "Splits":pd.DataFrame(), "Economic events":pd.DataFrame(),
            "_errors":{}, "_earnings_fallback":False,
        }
        statement = pd.DataFrame(
            {pd.Timestamp("2026-09-30"): [100_000_000_000, 12_000_000_000, 8_000_000_000, 2.0]},
            index=["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"],
        )
        app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
        at = AppTest.from_file(str(app_path), default_timeout=120)
        at.session_state["watchlist_input"] = "AMZN, MSFT"
        at.session_state["focus_ticker"] = "AMZN"
        at.session_state["ticker_search_query"] = ""

        with ExitStack() as stack:
            core_loader = stack.enter_context(patch.object(app, "load_market_data", return_value=payload))
            context_loader = stack.enter_context(patch.object(app, "load_market_context", return_value=context))
            stack.enter_context(patch.object(app, "load_industry_index", return_value=pd.DataFrame()))
            calendar_loader = stack.enter_context(patch.object(app, "load_upcoming_events", return_value=earnings_result))
            fundamentals_loader = stack.enter_context(patch.object(app, "load_company_fundamentals", return_value={
                "data":statement, "status":"available", "message":None,
            }))
            catalysts_loader = stack.enter_context(patch.object(app, "load_company_catalysts", return_value={
                "earnings_dates":pd.DataFrame(), "analyst_targets":None, "eps_revisions":pd.DataFrame(),
                "sec_filings":[], "upgrades":pd.DataFrame(), "_errors":{}, "_missing":[],
            }))
            news_loader = stack.enter_context(patch.object(app, "load_ticker_news", return_value=([], None)))
            stack.enter_context(patch.object(app, "load_snapshot", return_value=envelope))
            stack.enter_context(patch.object(app, "load_profile", return_value={
                "name":"Example Corporation", "sector":"Technology", "industry":"Software Infrastructure",
            }))
            stack.enter_context(patch.object(app, "load_analyst_recommendations", return_value=payload["recommendations"]))
            stack.enter_context(patch.object(app, "load_chart_history", return_value=(history, None)))

            at.run(timeout=120)
            self.assertFalse(at.exception, [item.value for item in at.exception])
            self.assertEqual(at.session_state[WORKSPACE_KEY], "Market Overview")
            self.assertTrue(any("Selected ticker snapshot" in item.value for item in at.markdown))
            self.assertEqual(core_loader.call_count, 1)

            # The overview controls are snapshotted before their hidden widgets are pruned.
            at.get_by_key("market_chart_interval").set_value("1 hour")
            at.run(timeout=120)
            at.get_by_key("market_chart_range").set_value("1D")
            at.get_by_key("market_chart_style").set_value("Line")
            at.get_by_key("market_chart_averages").set_value(["20 bar"])
            at.run(timeout=120)
            core_calls_before_discovery = core_loader.call_count
            context_calls_before_discovery = context_loader.call_count
            at.get_by_key(WORKSPACE_KEY).set_value("Discovery")
            at.run(timeout=120)
            self.assertFalse(at.exception, [item.value for item in at.exception])
            self.assertTrue(any("Discovery index" in item.value for item in at.markdown))
            self.assertEqual(core_loader.call_count, core_calls_before_discovery)
            self.assertEqual(context_loader.call_count, context_calls_before_discovery)
            self.assertEqual(at.session_state["watchlist_input"], "AMZN, MSFT")
            self.assertEqual(at.session_state["focus_ticker"], "AMZN")

            at.session_state["discovery_index_tabs"] = "Earnings soon"
            at.run(timeout=120)
            self.assertEqual(calendar_loader.call_count, 1)
            self.assertFalse(at.exception, [item.value for item in at.exception])

            at.get_by_key(WORKSPACE_KEY).set_value("Company Research")
            at.run(timeout=120)
            self.assertFalse(at.exception, [item.value for item in at.exception])
            self.assertTrue(any("Company research" in item.value for item in at.markdown))
            self.assertEqual(news_loader.call_count, 0)
            self.assertEqual(core_loader.call_count, core_calls_before_discovery + 1)

            at.session_state["research_desk_tabs"] = "Business & valuation"
            at.run(timeout=120)
            self.assertTrue(any("Reported quarterly trend" in item.value for item in at.markdown))
            self.assertEqual(fundamentals_loader.call_count, 1)
            self.assertEqual(catalysts_loader.call_count, 0)
            at.session_state["research_desk_tabs"] = "Estimates, events & filings"
            at.run(timeout=120)
            self.assertEqual(catalysts_loader.call_count, 1)
            at.session_state["research_desk_tabs"] = "Headlines & sentiment"
            at.run(timeout=120)
            self.assertEqual(news_loader.call_count, 1)
            self.assertTrue(any("Headlines & sentiment" in item.value for item in at.markdown))

            at.get_by_key(WORKSPACE_KEY).set_value("Watchlist")
            at.run(timeout=120)
            self.assertFalse(at.exception, [item.value for item in at.exception])
            self.assertTrue(any("Watchlist snapshot" in item.value for item in at.markdown))
            self.assertEqual(at.session_state["focus_ticker"], "AMZN")

            at.get_by_key(WORKSPACE_KEY).set_value("Company Research")
            at.run(timeout=120)
            self.assertEqual(at.session_state["research_desk_tabs"], "Headlines & sentiment")
            self.assertEqual(news_loader.call_count, 2)

            at.get_by_key(WORKSPACE_KEY).set_value("Discovery")
            at.run(timeout=120)
            self.assertEqual(at.session_state["discovery_index_tabs"], "Earnings soon")

            at.get_by_key(WORKSPACE_KEY).set_value("Market Overview")
            at.run(timeout=120)
            self.assertEqual(at.session_state["market_chart_interval"], "1 hour")
            self.assertEqual(at.session_state["market_chart_range"], "1D")
            self.assertEqual(at.session_state["market_chart_style"], "Line")
            self.assertEqual(at.session_state["market_chart_averages"], ["20 bar"])
            self.assertEqual(at.session_state["watchlist_input"], "AMZN, MSFT")
            self.assertFalse(at.exception, [item.value for item in at.exception])

            at.session_state["market_lens_ui_theme"] = "light"
            at.run(timeout=120)
            self.assertTrue(any("--text-color:#17312b" in item.value for item in at.markdown))
            at.session_state["market_lens_ui_theme"] = "dark"
            at.run(timeout=120)
            self.assertTrue(any("--text-color:#edf4f2" in item.value for item in at.markdown))


if __name__ == "__main__":
    unittest.main()
