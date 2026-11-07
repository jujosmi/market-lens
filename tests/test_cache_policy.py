import unittest
from unittest.mock import Mock, call, patch

import app
from market_lens.cache_policy import (
    CHART_INTERVALS, clear_selected_ticker_caches, selected_ticker_cache_entries,
)


class CachePolicyTests(unittest.TestCase):
    def test_selected_ticker_refresh_is_scoped_to_symbol(self):
        entries = selected_ticker_cache_entries(" nvda ")
        self.assertIn(("load_market_data", ("NVDA",)), entries)
        self.assertIn(("load_ticker_news", ("NVDA",)), entries)
        self.assertIn(("load_company_fundamentals", ("NVDA",)), entries)
        self.assertIn(("load_company_catalysts", ("NVDA",)), entries)
        self.assertIn(("load_snapshot", ("NVDA",)), entries)
        self.assertIn(("load_profile", ("NVDA",)), entries)
        self.assertIn(("load_analyst_recommendations", ("NVDA",)), entries)
        self.assertIn(("load_analyst_recommendation_result", ("NVDA",)), entries)
        self.assertIn(("load_chart_history", ("NVDA", "1 day")), entries)
        self.assertEqual(
            {args[1] for name, args in entries if name == "load_chart_history"},
            set(CHART_INTERVALS),
        )

    def test_selected_ticker_refresh_never_clears_shared_caches(self):
        names = {name for name, _ in selected_ticker_cache_entries("NVDA")}
        self.assertNotIn("load_market_context", names)
        self.assertNotIn("load_benchmark", names)
        self.assertNotIn("load_industry_index", names)
        self.assertNotIn("load_upcoming_events", names)

    def test_empty_symbol_has_no_cache_entries(self):
        self.assertEqual(selected_ticker_cache_entries("  "), ())

    def test_invalidation_calls_each_cached_function_with_its_scoped_key(self):
        entries = selected_ticker_cache_entries("NVDA")
        cached_functions = {name:Mock() for name, _ in entries}

        clear_selected_ticker_caches(" nvda ", cached_functions)

        self.assertEqual(set(cached_functions), {name for name, _ in entries})
        for name, args in entries:
            cached_functions[name].clear.assert_any_call(*args)
        self.assertEqual(
            sum(function.clear.call_count for function in cached_functions.values()),
            len(entries),
        )

    def test_application_refresh_maps_to_the_ticker_cache_functions(self):
        entries = selected_ticker_cache_entries("NVDA")
        cached_functions = {name:Mock() for name, _ in entries}

        with patch.multiple(app, **cached_functions):
            app.clear_selected_ticker_data(" nvda ")

        self.assertEqual(set(cached_functions), {name for name, _ in entries})
        for name, function in cached_functions.items():
            expected_calls = [call(*args) for entry_name, args in entries if entry_name == name]
            self.assertEqual(function.clear.call_args_list, expected_calls)


if __name__ == "__main__":
    unittest.main()
