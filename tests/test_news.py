import unittest

from market_lens.news import classify_headline


class HeadlineClassificationTests(unittest.TestCase):
    def test_directional_financial_phrases(self):
        result = classify_headline("Company beats estimates")
        self.assertEqual(result["label"], "Bullish")
        self.assertEqual(result["bull_score"], 2.4)
        self.assertEqual(classify_headline("Company cuts guidance after revenue miss")["label"], "Bearish")

    def test_negation_flips_phrase_polarity(self):
        result = classify_headline("Company does not beat estimates")
        self.assertEqual(result["label"], "Bearish")

    def test_clause_boundary_does_not_leak_negation(self):
        result = classify_headline("No warning. Shares surge after results")
        self.assertEqual(result["label"], "Bullish")

    def test_ambiguous_headline_is_neutral_low_signal(self):
        result = classify_headline("Company announces quarterly results")
        self.assertEqual(result["label"], "Neutral")
        self.assertEqual(result["confidence"], "Low")


if __name__ == "__main__":
    unittest.main()
