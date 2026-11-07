import unittest

from market_lens.explanations import rating_explanation, trend_explanation


class ReadingExplanationTests(unittest.TestCase):
    def test_rating_explains_screen_counts_and_threshold(self):
        text = rating_explanation({"rating":"Buy", "constructive_checks":3, "caution_checks":1})
        self.assertIn("3/5 constructive minus 1/5 caution", text)
        self.assertIn("+2 or more", text)
        self.assertIn("technical screen", text)

    def test_unavailable_rating_explains_incomplete_history(self):
        text = rating_explanation({"rating":"Unavailable", "rating_checks_complete":False})
        self.assertIn("No Market Lens signal is shown", text)
        self.assertIn("technical-history inputs are unavailable", text)

    def test_trend_explains_history_requirement(self):
        text = trend_explanation({"state":"Insufficient history for a 200-day trend", "sma200":float("nan"), "observations":100})
        self.assertIn("100 closes", text)
        self.assertIn("needs 200", text)


if __name__ == "__main__":
    unittest.main()
