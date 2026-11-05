import unittest

from market_lens.explanations import rating_explanation, trend_explanation


class ReadingExplanationTests(unittest.TestCase):
    def test_rating_explains_counts_without_new_check_detail_field(self):
        text = rating_explanation({"rating":"Buy", "constructive_checks":3, "caution_checks":1})
        self.assertIn("net +2", text)
        self.assertIn("gives Buy", text)

    def test_unavailable_rating_explains_missing_inputs(self):
        text = rating_explanation({"rating":"Unavailable", "rating_checks_complete":False})
        self.assertIn("indicators are unavailable", text)

    def test_trend_explains_history_requirement(self):
        text = trend_explanation({"state":"Insufficient history for a 200-day trend", "sma200":float("nan"), "observations":100})
        self.assertIn("100 closes", text)
        self.assertIn("needs 200", text)


if __name__ == "__main__":
    unittest.main()
