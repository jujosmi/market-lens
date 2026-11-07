import logging
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

import app
from market_lens.discovery import (
    canonical_key_for_industry_name, canonical_local_industry_rows,
    fetch_industry_companies,
)


class DiscoveryIndustryTests(unittest.TestCase):
    def call_fetch(self, industry, sector=None, *, key="software-infrastructure", source="Yahoo Finance",
                   industry_name="Software Infrastructure", sector_name="Technology",
                   industry_factory=None, sector_factory=None, ticker_factory=None,
                   canonical_keys=("software-infrastructure",)):
        return fetch_industry_companies(
            key, source, "technology", industry_name, sector_name,
            industry_factory or (lambda requested_key:industry),
            sector_factory or (lambda requested_key:sector or SimpleNamespace(top_companies=pd.DataFrame())),
            ticker_factory or (lambda symbol:SimpleNamespace(get_info=lambda:{"industryKey":key})),
            canonical_keys=canonical_keys,
            valid_sector_keys=("technology",),
        )

    def test_success_combines_provider_company_lists(self):
        industry = SimpleNamespace(
            name="Software Infrastructure",
            top_companies=pd.DataFrame({"name":["NVIDIA"]}, index=["NVDA"]),
            top_performing_companies=pd.DataFrame({"ytd return":[0.2]}, index=["NVDA"]),
            top_growth_companies=pd.DataFrame({"growth estimate":[0.3]}, index=["MSFT"]),
        )

        companies, error = self.call_fetch(industry)

        self.assertIsNone(error)
        self.assertEqual(set(companies.index), {"NVDA", "MSFT"})
        self.assertIn("Top companies", companies.loc["NVDA", "Company list"])
        self.assertIn("Top performing", companies.loc["NVDA", "Company list"])

    def test_app_loader_passes_the_selected_provider_key_and_labels(self):
        app.load_industry_companies.clear(
            "software-infrastructure", "Yahoo Finance", "technology",
            "Software - Infrastructure", "Technology",
        )
        with patch("app.fetch_industry_companies", return_value=(pd.DataFrame(), None)) as fetch:
            app.load_industry_companies(
                "software-infrastructure", "Yahoo Finance", "technology",
                "Software - Infrastructure", "Technology",
            )

        args, kwargs = fetch.call_args
        self.assertEqual(args[:5], (
            "software-infrastructure", "Yahoo Finance", "technology",
            "Software - Infrastructure", "Technology",
        ))
        self.assertIn("industry_factory", kwargs)

    def test_empty_valid_provider_response_is_not_reported_as_error(self):
        industry = SimpleNamespace(
            name="Software Infrastructure", top_companies=None,
            top_performing_companies=None, top_growth_companies=None,
        )
        sector = SimpleNamespace(top_companies=pd.DataFrame())

        companies, error = self.call_fetch(industry, sector)

        self.assertTrue(companies.empty)
        self.assertIsNone(error)

    def test_invalid_local_key_is_rejected_before_provider_request(self):
        industry_factory = Mock()
        companies, error = self.call_fetch(
            None, source="Built-in yfinance directory", key="software_infrastructure",
            industry_factory=industry_factory,
        )

        self.assertTrue(companies.empty)
        self.assertIn("not in yfinance's canonical industry-key list", error)
        industry_factory.assert_not_called()

    def test_provider_failure_is_reported_and_logged(self):
        industry_factory = Mock(side_effect=RuntimeError("upstream unavailable"))
        sector_factory = Mock(side_effect=TimeoutError("sector timeout"))

        with self.assertLogs("market_lens.discovery", level="WARNING") as captured:
            companies, error = self.call_fetch(
                None, industry_factory=industry_factory, sector_factory=sector_factory,
            )

        self.assertTrue(companies.empty)
        self.assertIn("requests failed", error)
        self.assertTrue(any("industry object request failed" in line for line in captured.output))
        self.assertTrue(any("sector 'technology' top-companies fallback request failed" in line for line in captured.output))

    def test_sector_fallback_requires_exact_yahoo_industry_key_match(self):
        industry = SimpleNamespace(
            name="Software Infrastructure", top_companies=None,
            top_performing_companies=None, top_growth_companies=None,
        )
        sector = SimpleNamespace(top_companies=pd.DataFrame(
            {"name":["NVIDIA", "Salesforce"]}, index=["NVDA", "CRM"],
        ))

        def ticker_factory(symbol):
            key = "software-infrastructure" if symbol == "NVDA" else "software-application"
            return SimpleNamespace(get_info=lambda:{"industryKey":key})

        companies, error = self.call_fetch(industry, sector, ticker_factory=ticker_factory)

        self.assertIsNone(error)
        self.assertEqual(list(companies.index), ["NVDA"])
        self.assertIn("Yahoo industryKey verified", companies.loc["NVDA", "Company list"])

    def test_local_key_must_verify_against_live_yahoo_name_and_sector(self):
        industry = SimpleNamespace(
            name=None, sector_key=None, top_companies=None,
            top_performing_companies=None, top_growth_companies=None,
        )
        sector = SimpleNamespace(top_companies=pd.DataFrame(
            {"name":["NVIDIA", "Salesforce"]}, index=["NVDA", "CRM"],
        ))

        def ticker_factory(symbol):
            profile = {
                "NVDA":{"industry":"Software - Infrastructure", "sector":"Technology",
                        "industryKey":"software-infrastructure"},
                "CRM":{"industry":"Software - Application", "sector":"Technology",
                       "industryKey":"software-application"},
            }[symbol]
            return SimpleNamespace(get_info=lambda:profile)

        companies, warning = self.call_fetch(
            industry, sector, key="software—infrastructure",
            source="Built-in yfinance directory", industry_name="Software—Infrastructure",
            industry_factory=lambda key:industry, ticker_factory=ticker_factory,
            canonical_keys=("software—infrastructure",),
        )

        self.assertEqual(list(companies.index), ["NVDA"])
        self.assertIn("did not verify", warning)
        self.assertIn("Yahoo profile industry/sector confirmation", warning)
        self.assertIn("Yahoo profile industry and sector verified", companies.loc["NVDA", "Company list"])

    def test_local_key_matching_preserves_yahoo_em_dash_and_requires_allowlist(self):
        name = "Software—Infrastructure"
        valid_keys = ("software—infrastructure", "software—application")
        self.assertEqual(canonical_key_for_industry_name(name, valid_keys), "software—infrastructure")
        rows = canonical_local_industry_rows(
            {"Technology":{name, "Made Up Category"}},
            {"technology":valid_keys},
            {"technology":"Technology"},
        )
        self.assertEqual([row["industry_key"] for row in rows], ["software—infrastructure"])


if __name__ == "__main__":
    unittest.main()
