import unittest

import numpy as np
import pandas as pd

from market_lens.analytics import (
    analyze,
    beta,
    maximum_drawdown,
    moving_average,
    period_return,
    relative_return,
    realized_volatility,
    relative_strength_index,
)


def prices(values, dates=None):
    if dates is None:
        dates = pd.date_range("2025-01-01", periods=len(values), freq="B", tz="America/New_York")
    return pd.Series(values, index=dates, name="Close", dtype=float)


class MovingAverageTests(unittest.TestCase):
    def test_full_window_mean(self):
        self.assertEqual(moving_average(prices([10, 20, 30]), 3), 20)

    def test_insufficient_history_is_unavailable(self):
        self.assertTrue(np.isnan(moving_average(prices([10, 20]), 3)))

    def test_missing_values_are_ignored_before_window_check(self):
        series = prices([10, np.nan, 20, 30])
        self.assertEqual(moving_average(series, 3), 20)


class RsiTests(unittest.TestCase):
    def test_zero_average_loss_returns_100(self):
        self.assertEqual(relative_strength_index(prices(list(range(100, 116))), 14), 100)

    def test_zero_average_gain_returns_zero(self):
        self.assertEqual(relative_strength_index(prices(list(range(116, 100, -1))), 14), 0)

    def test_flat_series_returns_50(self):
        self.assertEqual(relative_strength_index(prices([5.0] * 16), 14), 50)

    def test_short_series_is_unavailable(self):
        self.assertTrue(np.isnan(relative_strength_index(prices([1, 2, 3]), 14)))


class ReturnTests(unittest.TestCase):
    def test_return_uses_n_plus_one_closes(self):
        self.assertAlmostEqual(period_return(prices([100, 110, 121]), 2), 0.21)

    def test_short_horizon_is_unavailable(self):
        self.assertTrue(np.isnan(period_return(prices([100, 110]), 2)))

    def test_relative_return_uses_intersection_of_dates(self):
        asset = prices([100, 110, 121], pd.to_datetime(["2025-01-01", "2025-01-03", "2025-01-06"]))
        benchmark = prices([100, 200, 220], pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]))
        result = relative_return(asset, benchmark, 1)
        self.assertAlmostEqual(result["asset"], 0.1)
        self.assertAlmostEqual(result["benchmark"], 0.1)
        self.assertAlmostEqual(result["excess"], 0.0)
        self.assertEqual(result["observations"], 2)

    def test_relative_return_insufficient_common_dates_is_unavailable(self):
        dates = pd.date_range("2025-01-01", periods=3, freq="B")
        result = relative_return(prices([10, 11, 12], dates), prices([20, 21, 22], dates), 3)
        self.assertTrue(np.isnan(result["excess"]))


class RiskMeasureTests(unittest.TestCase):
    def test_beta_aligns_different_timezone_indexes(self):
        dates = pd.date_range("2025-01-01", periods=6, freq="B", tz="America/New_York")
        asset = prices([100, 101, 99, 104, 102, 108], dates)
        benchmark_dates = dates.tz_convert("UTC")
        benchmark = prices([100, 100.5, 99.5, 102.5, 101.5, 105], benchmark_dates)
        value, observations = beta(asset, benchmark, window=5, minimum_observations=3)
        self.assertTrue(np.isfinite(value))
        self.assertEqual(observations, 5)

    def test_beta_counts_only_same_date_daily_returns(self):
        dates = pd.date_range("2025-01-01", periods=8, freq="B")
        asset = prices([100, 102, 101, 105, 108], dates[[0, 1, 3, 5, 7]])
        benchmark = prices([100, 101, 99, 102, 104, 103, 106, 108], dates)
        value, observations = beta(asset, benchmark, window=10, minimum_observations=3)
        self.assertTrue(np.isfinite(value))
        self.assertEqual(observations, 4)

    def test_realized_volatility_does_not_invent_a_fallback(self):
        value, observations = realized_volatility(prices([100, 101, 99, 102]), window=30)
        self.assertTrue(np.isnan(value))
        self.assertEqual(observations, 3)

    def test_max_drawdown_requires_full_window(self):
        value, observations = maximum_drawdown(prices([100, 80, 110]), observations=4)
        self.assertTrue(np.isnan(value))
        self.assertEqual(observations, 3)

    def test_max_drawdown_peak_to_trough(self):
        value, observations = maximum_drawdown(prices([100, 80, 110]), observations=3)
        self.assertAlmostEqual(value, -0.2)
        self.assertEqual(observations, 3)


class CompositeAnalysisTests(unittest.TestCase):
    def test_200_day_average_is_not_fabricated_from_shorter_history(self):
        history = pd.DataFrame({"Close":np.arange(100.0, 250.0), "Volume":np.full(150, 1000)},
                               index=pd.date_range("2025-01-01", periods=150, freq="B"))
        result = analyze(history)
        self.assertTrue(np.isnan(result["sma200"]))
        self.assertEqual(result["rating"], "Unavailable")
        self.assertFalse(result["rating_checks_complete"])

    def test_full_year_measures_available_after_full_history(self):
        closes = np.linspace(100, 150, 260)
        history = pd.DataFrame({"Close":closes, "Volume":np.full(260, 1000)},
                               index=pd.date_range("2025-01-01", periods=260, freq="B"))
        result = analyze(history)
        self.assertTrue(np.isfinite(result["sma200"]))
        self.assertTrue(np.isfinite(result["high52"]))
        self.assertTrue(np.isfinite(result["drawdown"]))


if __name__ == "__main__":
    unittest.main()
