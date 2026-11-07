from __future__ import annotations

import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

import app


class PerformanceOptimizationTests(unittest.TestCase):
    def test_core_ticker_load_defers_section_specific_research(self):
        ticker = Mock()
        ticker.get_info.return_value = {"longName": "Example Corp"}
        ticker.options = []
        history = pd.DataFrame({"Close": [100.0]}, index=pd.date_range("2026-01-01", periods=1))
        history_result = SimpleNamespace(data=history, warning=None)
        recommendations = pd.DataFrame({"strongBuy": [1], "buy": [2], "hold": [1], "sell": [0], "strongSell": [0]})

        with patch.object(app.yf, "Ticker", return_value=ticker), \
             patch.object(app.YahooFinanceProvider, "history", return_value=history_result), \
             patch.object(app, "load_analyst_recommendation_result", return_value={
                 "data":recommendations, "status":"available", "message":None,
             }) as load_recommendations:
            result = app.load_market_data.__wrapped__("EXM")

        self.assertEqual(result["info"]["longName"], "Example Corp")
        self.assertIs(result["recommendations"], recommendations)
        load_recommendations.assert_called_once_with("EXM")
        ticker.get_news.assert_not_called()
        ticker.get_earnings_dates.assert_not_called()
        ticker.get_eps_revisions.assert_not_called()
        ticker.get_sec_filings.assert_not_called()
        ticker.get_upgrades_downgrades.assert_not_called()
        self.assertNotIn("quarterly_income", result)
        self.assertNotIn("analyst_targets", result)

    def test_headlines_loader_is_isolated_and_reports_provider_failure(self):
        ticker = Mock()
        ticker.get_news.side_effect = RuntimeError("provider unavailable")
        with patch.object(app.yf, "Ticker", return_value=ticker):
            news, warning = app.load_ticker_news.__wrapped__("EXM")
        self.assertEqual(news, [])
        self.assertIn("Recent headlines could not be retrieved", warning)
        ticker.get_news.assert_called_once_with(count=12)

    def test_fundamentals_loader_only_requests_quarterly_statement(self):
        ticker = Mock()
        statement = pd.DataFrame({"2026-09-30": [1]}, index=["Total Revenue"])
        ticker.quarterly_income_stmt = statement
        with patch.object(app.yf, "Ticker", return_value=ticker):
            result = app.load_company_fundamentals.__wrapped__("EXM")
        self.assertEqual(result["status"], "available")
        self.assertIs(result["data"], statement)
        ticker.get_info.assert_not_called()
        ticker.get_recommendations_summary.assert_not_called()

    def test_catalyst_loader_preserves_fields_and_reuses_one_ticker_instance(self):
        ticker = Mock()
        earnings = pd.DataFrame({"Earnings Date": [date(2026, 12, 1)]})
        targets = {"mean": 123.0}
        revisions = pd.DataFrame({"upLast7days": [1]})
        filings = [{"type": "10-Q"}]
        upgrades = pd.DataFrame({"To Grade": ["Buy"]})
        ticker.get_earnings_dates.return_value = earnings
        ticker.analyst_price_targets = targets
        ticker.get_eps_revisions.return_value = revisions
        ticker.get_sec_filings.return_value = filings
        ticker.get_upgrades_downgrades.return_value = upgrades
        with patch.object(app.yf, "Ticker", return_value=ticker) as ticker_factory:
            result = app.load_company_catalysts.__wrapped__("EXM")
        ticker_factory.assert_called_once_with("EXM")
        self.assertIs(result["earnings_dates"], earnings)
        self.assertIs(result["analyst_targets"], targets)
        self.assertIs(result["eps_revisions"], revisions)
        self.assertIs(result["sec_filings"], filings)
        self.assertIs(result["upgrades"], upgrades)

    def test_upcoming_events_only_requests_selected_calendar_sections(self):
        calendar = Mock()
        calendar.get_ipo_info_calendar.return_value = pd.DataFrame({"Symbol": ["NEW"]})
        with patch.object(app.yf, "Calendars", return_value=calendar), \
             patch.object(app.yf, "Ticker") as ticker_factory:
            result = app.load_upcoming_events.__wrapped__(
                date.today(), date.today() + timedelta(days=30), (), ("IPOs",),
            )
        self.assertEqual(len(result["IPOs"]), 1)
        calendar.get_ipo_info_calendar.assert_called_once()
        calendar.get_earnings_calendar.assert_not_called()
        calendar.get_splits_calendar.assert_not_called()
        calendar.get_economic_events_calendar.assert_not_called()
        ticker_factory.assert_not_called()

    def test_inactive_tab_is_not_marked_open(self):
        self.assertTrue(app.tab_is_active(SimpleNamespace(open=True)))
        self.assertFalse(app.tab_is_active(SimpleNamespace(open=False)))
        self.assertFalse(app.tab_is_active(object()))

    def test_inactive_tab_does_not_invoke_provider_loader(self):
        loader = Mock(return_value="loaded")
        fallback = {}
        result = app.load_tab_data_if_active(SimpleNamespace(open=False), loader, fallback)
        self.assertIs(result, fallback)
        loader.assert_not_called()

    def test_active_tab_invokes_provider_loader(self):
        loader = Mock(return_value="loaded")
        result = app.load_tab_data_if_active(SimpleNamespace(open=True), loader, {})
        self.assertEqual(result, "loaded")
        loader.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
