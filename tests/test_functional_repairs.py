from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import app
import pandas as pd


class FunctionalRepairTests(unittest.TestCase):
    def test_profile_provider_error_is_visible_and_safe(self):
        with patch.object(app.yf, "Ticker", side_effect=TimeoutError("private provider detail")):
            result = app.load_profile.__wrapped__("AMZN")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["name"], "AMZN")
        self.assertEqual(result["sector"], "Unavailable")
        self.assertIn("could not be retrieved", result["warning"])
        self.assertNotIn("private provider detail", result["warning"])

    def test_profile_provider_shape_and_true_missing_data_are_distinct(self):
        with patch.object(app.yf, "Ticker", return_value=Mock(get_info=Mock(return_value="unexpected"))):
            malformed = app.load_profile.__wrapped__("AMZN")
        self.assertEqual(malformed["status"], "malformed")
        self.assertEqual(malformed["industry"], "Unavailable")

        with patch.object(app.yf, "Ticker", return_value=Mock(get_info=Mock(return_value=pd.DataFrame({"unexpected": [1]})))):
            malformed_frame = app.load_profile.__wrapped__("AMZN")
        self.assertEqual(malformed_frame["status"], "malformed")

        with patch.object(app.yf, "Ticker", return_value=Mock(get_info=Mock(return_value=None))):
            missing = app.load_profile.__wrapped__("AMZN")
        self.assertEqual(missing["status"], "missing")
        self.assertEqual(missing["industry"], "Unclassified")

    def test_profile_mapping_keeps_yahoo_company_identity(self):
        info = {"shortName":"Amazon.com, Inc.", "sector":"Consumer Cyclical", "industry":"Internet Retail"}
        with patch.object(app.yf, "Ticker", return_value=Mock(get_info=Mock(return_value=info))):
            result = app.load_profile.__wrapped__("AMZN")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["name"], "Amazon.com, Inc.")
        self.assertEqual(result["industry"], "Internet Retail")

    def test_ticker_search_distinguishes_provider_failure_from_empty_search(self):
        with patch.object(app.yf, "Search", side_effect=RuntimeError("private detail")):
            failed = app._search_tickers_result.__wrapped__("Example")
        self.assertEqual(failed["matches"], [])
        self.assertIn("temporarily unavailable", failed["warning"])
        self.assertNotIn("private detail", failed["warning"])

        with patch.object(app.yf, "Search", return_value=Mock(quotes=[])):
            empty = app._search_tickers_result.__wrapped__("No Such Listing")
        self.assertEqual(empty, {"matches":[], "warning":None})

        with patch.object(app.yf, "Search", return_value=Mock(quotes={"unexpected":"mapping"})):
            malformed = app._search_tickers_result.__wrapped__("Malformed")
        self.assertEqual(malformed["matches"], [])
        self.assertIn("unsupported format", malformed["warning"])

    def test_search_api_raises_typed_error_instead_of_returning_no_matches(self):
        with patch.object(app, "_search_tickers_result", return_value={
            "matches":[], "warning":"Ticker suggestions are temporarily unavailable.",
        }):
            with self.assertRaises(app.TickerSearchUnavailable):
                app.search_tickers("Example")

    def test_news_normalizer_accepts_legacy_and_nested_yfinance_shapes(self):
        legacy = app.normalize_news_item({
            "title":"Example earnings beat expectations", "publisher":"Wire",
            "link":"https://example.test/story", "providerPublishTime":1_798_000_000,
        })
        self.assertEqual(legacy["publisher"], "Wire")
        self.assertEqual(legacy["link"], "https://example.test/story")
        self.assertTrue(legacy["published_at"])

        nested = app.normalize_news_item({"content":{
            "title":"Example raises outlook", "provider":{"displayName":"Provider"},
            "canonicalUrl":{"url":"https://example.test/nested"}, "pubDate":"2026-11-12T10:00:00Z",
        }})
        self.assertEqual(nested["publisher"], "Provider")
        self.assertEqual(nested["link"], "https://example.test/nested")

    def test_news_normalizer_skips_malformed_items_without_raising(self):
        for item in (None, "not a story", {"content":"unexpected"}, {"content":{"title":None}}):
            with self.subTest(item=item):
                self.assertIsNone(app.normalize_news_item(item))

    def test_news_normalizer_handles_out_of_range_provider_timestamps(self):
        result = app.normalize_news_item({"title":"Example report", "providerPublishTime":1e100})
        self.assertEqual(result["published_at"], "Date unavailable")


if __name__ == "__main__":
    unittest.main()
