import tempfile
import unittest
from pathlib import Path

from market_lens.storage import load_watchlist, save_watchlist


class WatchlistStorageTests(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watchlist.json"
            save_watchlist(["aapl", "MSFT"], path)
            self.assertEqual(load_watchlist(path), ["AAPL", "MSFT"])

    def test_load_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_watchlist(Path(directory) / "missing.json"), ["NVDA", "AAPL", "TSLA"])

    def test_save_deduplicates_and_caps_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watchlist.json"
            save_watchlist(["aapl", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOG", "META", "AMZN", "INTC"], path)
            self.assertEqual(load_watchlist(path), ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GOOG", "META", "AMZN"])


if __name__ == "__main__":
    unittest.main()
