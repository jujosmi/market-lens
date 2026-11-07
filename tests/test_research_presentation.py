from __future__ import annotations

import unittest
from textwrap import dedent
from unittest.mock import Mock, patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import app
from market_lens.research import (
    analyst_target_summary, eps_revision_table, fundamentals_metric_table,
    quarterly_statement_table, recommendation_distribution,
)
from tests.fixtures.research_responses import RESEARCH_RESPONSES


class ResearchPresentationTests(unittest.TestCase):
    def test_live_shape_fixtures_render_financials_for_amzn_msft_and_nvda(self):
        expected_latest_revenue_billions = {"AMZN":201.944, "MSFT":92.279, "NVDA":96.221}
        expected_market_caps = {"AMZN":"$2.80T", "MSFT":"$3.94T", "NVDA":"$4.51T"}
        for symbol, fixture in RESEARCH_RESPONSES.items():
            with self.subTest(symbol=symbol):
                metric_table = fundamentals_metric_table(fixture["info"])
                self.assertEqual(
                    metric_table.loc[metric_table["Metric"] == "Market cap", "Latest value"].iloc[0],
                    expected_market_caps[symbol],
                )
                self.assertIn("Trailing P/E", metric_table["Metric"].tolist())

                quarterly = quarterly_statement_table(fixture["quarterly_income_stmt"])
                self.assertIn("Revenue ($B)", quarterly.columns)
                self.assertAlmostEqual(
                    quarterly.iloc[0]["Revenue ($B)"],
                    expected_latest_revenue_billions[symbol],
                )
                self.assertIn("Diluted EPS", quarterly.columns)

                target = analyst_target_summary(fixture["analyst_price_targets"],
                                                fixture["analyst_price_targets"]["current"])
                self.assertEqual(target["mean"], fixture["analyst_price_targets"]["mean"])
                self.assertIsNotNone(target["upside_percent"])

                distribution = recommendation_distribution(fixture["recommendations_summary"])
                self.assertEqual(distribution["Analyst count"].sum(),
                                 sum(fixture["recommendations_summary"].iloc[0][key]
                                     for key in ("strongBuy", "buy", "hold", "sell", "strongSell")))
                self.assertEqual(distribution.iloc[0]["Rating"], "Strong buy")

                revisions = eps_revision_table(fixture["eps_revisions"])
                self.assertIn("Up last 7 days", revisions.columns)
                self.assertEqual(revisions.index[0], "Current quarter")
                self.assertEqual(revisions.iloc[0]["Currency"], "USD")

    def test_quarterly_presentation_keeps_missing_provider_values_empty(self):
        frame = RESEARCH_RESPONSES["AMZN"]["quarterly_income_stmt"]
        presentation = quarterly_statement_table(frame)
        self.assertTrue(pd.isna(presentation.iloc[1]["Revenue ($B)"]))
        self.assertEqual(presentation.iloc[0]["Revenue ($B)"], 201.944)

    def test_quarterly_presentation_supports_provider_row_alias_and_bad_shapes(self):
        statement = pd.DataFrame(
            [[10_000_000_000], [2_500_000_000]],
            index=["Total Revenue", "Total Operating Income As Reported"],
            columns=[pd.Timestamp("2026-09-30")],
        )
        presentation = quarterly_statement_table(statement)
        self.assertEqual(presentation.iloc[0]["Revenue ($B)"], 10.0)
        self.assertEqual(presentation.iloc[0]["Operating income ($B)"], 2.5)
        self.assertTrue(quarterly_statement_table(None).empty)
        self.assertTrue(quarterly_statement_table(pd.DataFrame()).empty)
        self.assertTrue(quarterly_statement_table(pd.DataFrame([[1]], columns=["unknown"])).empty)

    def test_malformed_analyst_data_is_not_presented_as_zero_coverage(self):
        self.assertIsNone(analyst_target_summary([1, 2, 3]))
        self.assertIsNone(analyst_target_summary({"mean":"not a number"}))
        self.assertIsNone(recommendation_distribution(pd.DataFrame({"buy":[3]})))
        malformed = RESEARCH_RESPONSES["AMZN"]["recommendations_summary"].astype({"buy":"float64"}).copy()
        malformed.loc[0, "buy"] = 1.5
        self.assertIsNone(recommendation_distribution(malformed))
        self.assertIsNone(eps_revision_table(pd.DataFrame()))

    def test_fundamentals_loader_distinguishes_provider_error_from_missing(self):
        class FailedTicker:
            @property
            def quarterly_income_stmt(self):
                raise TimeoutError("network detail")

        ticker = FailedTicker()
        with patch.object(app.yf, "Ticker", return_value=ticker):
            failed = app.load_company_fundamentals.__wrapped__("AMZN")
        self.assertEqual(failed["status"], "error")
        self.assertIn("could not be retrieved", failed["message"])
        self.assertNotIn("network detail", failed["message"])

        ticker = Mock()
        ticker.quarterly_income_stmt = None
        with patch.object(app.yf, "Ticker", return_value=ticker):
            missing = app.load_company_fundamentals.__wrapped__("AMZN")
        self.assertEqual(missing["status"], "missing")
        self.assertIsNone(missing["message"])

    def test_catalyst_partial_failure_preserves_available_provider_fields(self):
        ticker = Mock()
        targets = RESEARCH_RESPONSES["AMZN"]["analyst_price_targets"]
        revisions = RESEARCH_RESPONSES["AMZN"]["eps_revisions"]
        upgrades = pd.DataFrame([{"Firm":"Example", "ToGrade":"Buy"}])
        ticker.get_earnings_dates.side_effect = TimeoutError("provider detail")
        ticker.analyst_price_targets = targets
        ticker.get_eps_revisions.return_value = revisions
        ticker.get_sec_filings.side_effect = TypeError("provider parser detail")
        ticker.get_upgrades_downgrades.return_value = upgrades
        with patch.object(app.yf, "Ticker", return_value=ticker):
            result = app.load_company_catalysts.__wrapped__("AMZN")

        self.assertIs(result["analyst_targets"], targets)
        self.assertIs(result["eps_revisions"], revisions)
        self.assertIs(result["upgrades"], upgrades)
        self.assertIn("earnings_dates", result["_errors"])
        self.assertIn("sec_filings", result["_errors"])
        self.assertNotIn("provider parser detail", str(result["_errors"]))

    def test_recommendation_result_distinguishes_missing_error_and_valid_rows(self):
        valid = RESEARCH_RESPONSES["AMZN"]["recommendations_summary"]
        with patch.object(app.yf, "Ticker") as ticker_factory:
            ticker_factory.return_value.get_recommendations_summary.return_value = valid
            result = app.load_analyst_recommendation_result.__wrapped__("AMZN")
        self.assertEqual(result["status"], "available")
        self.assertEqual(recommendation_distribution(result["data"]).iloc[1]["Analyst count"], 44)

        with patch.object(app.yf, "Ticker") as ticker_factory:
            ticker_factory.return_value.get_recommendations_summary.return_value = pd.DataFrame()
            missing = app.load_analyst_recommendation_result.__wrapped__("AMZN")
        self.assertEqual(missing["status"], "missing")

        with patch.object(app.yf, "Ticker") as ticker_factory:
            ticker_factory.return_value.get_recommendations_summary.side_effect = TimeoutError("private detail")
            failed = app.load_analyst_recommendation_result.__wrapped__("AMZN")
        self.assertEqual(failed["status"], "error")
        self.assertNotIn("private detail", failed["message"])

    def test_active_research_tab_renders_data_and_inactive_tab_stays_deferred(self):
        script = dedent("""
            import streamlit as st
            from app import load_tab_data_if_active
            business, analyst = st.tabs(
                ["Business & valuation", "Estimates, events & filings"],
                key="research_fixture_tabs", on_change="rerun",
            )
            with business:
                result = load_tab_data_if_active(
                    business, lambda: "Quarterly revenue: $201.94B", "Business data deferred",
                )
                st.metric("Business presentation", result)
            with analyst:
                result = load_tab_data_if_active(
                    analyst, lambda: "Analyst target: $326.99", "Analyst data deferred",
                )
                st.metric("Analyst presentation", result)
        """)
        at = AppTest.from_string(script).run()
        rendered = {element.label:element.value for element in at.metric}
        self.assertEqual(rendered["Business presentation"], "Quarterly revenue: $201.94B")
        self.assertEqual(rendered["Analyst presentation"], "Analyst data deferred")
        at.session_state["research_fixture_tabs"] = "Estimates, events & filings"
        at.run()
        rendered = {element.label:element.value for element in at.metric}
        self.assertEqual(rendered["Business presentation"], "Business data deferred")
        self.assertEqual(rendered["Analyst presentation"], "Analyst target: $326.99")


if __name__ == "__main__":
    unittest.main()
