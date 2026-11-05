import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from market_lens.providers import YahooFinanceProvider


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, **kwargs):
        if self.symbol == "BAD":
            raise RuntimeError("offline provider failure")
        if self.symbol == "EMPTY":
            return pd.DataFrame()
        return pd.DataFrame({"Close":[100.0, 101.0]}, index=pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=2, freq="D"))


class ProviderTests(unittest.TestCase):
    @patch("market_lens.providers.yf.Ticker", FakeTicker)
    def test_provider_returns_source_time_and_last_observation(self):
        result = YahooFinanceProvider().history("GOOD")
        self.assertEqual(result.source, "Yahoo Finance via yfinance")
        self.assertIsNotNone(result.retrieved_at)
        self.assertIsNotNone(result.last_observation)
        self.assertEqual(result.status, "recent")
        self.assertEqual(result.provider_delay, "unknown")

    @patch("market_lens.providers.yf.Ticker", FakeTicker)
    def test_empty_symbol_is_missing_not_valid(self):
        result = YahooFinanceProvider().history("EMPTY")
        self.assertEqual(result.status, "missing")
        self.assertTrue(result.data.empty)
        self.assertIsNotNone(result.warning)

    @patch("market_lens.providers.yf.Ticker", FakeTicker)
    def test_provider_exception_is_distinguished(self):
        result = YahooFinanceProvider().history("BAD")
        self.assertEqual(result.status, "failed")
        self.assertIn("offline provider failure", result.warning)

    def test_partial_and_stale_rows_are_labeled(self):
        now = datetime.now(timezone.utc)
        partial = pd.DataFrame({"Close":[100.0, None]}, index=pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=2, freq="D"))
        partial_result = YahooFinanceProvider._envelope(partial, "1d", now)
        self.assertEqual(partial_result.status, "partial")
        stale_last = pd.Timestamp.now(tz="UTC") - pd.Timedelta(8, unit="days")
        old_date = [stale_last - pd.Timedelta(1, unit="days"), stale_last]
        stale = pd.DataFrame({"Close":[100.0, 101.0]}, index=old_date)
        stale_result = YahooFinanceProvider._envelope(stale, "1d", now)
        self.assertEqual(stale_result.status, "stale")


if __name__ == "__main__":
    unittest.main()
