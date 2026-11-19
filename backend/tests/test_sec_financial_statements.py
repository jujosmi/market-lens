from datetime import date

from app.sec_edgar.mapping import SecFinancialFact, SecIdentity, map_company_facts
from app.sec_edgar.statements import build_statement_periods


def fact(field, value, unit, start, end, fiscal_year, fiscal_period, form, accession, *, latest=True, filed=None, tag=None):
    return SecFinancialFact(
        field=field, taxonomy="us-gaap", tag=tag or field, label=field, value=float(value),
        original_value=str(value), unit=unit, currency="USD" if unit == "USD" else None,
        period_start=date.fromisoformat(start) if start else None, period_end=date.fromisoformat(end),
        fiscal_year=fiscal_year, fiscal_period=fiscal_period, form=form,
        filed=date.fromisoformat(filed or end), accession_number=accession,
        filing_url=f"https://www.sec.gov/Archives/edgar/data/1/{accession.replace('-', '')}/filing.htm",
        latest_reported_version=latest,
    )


def test_annual_comparison_matches_fy_unit_and_duration_and_uses_absolute_denominator():
    facts = [
        fact("revenue", "100000000.25", "USD", "2025-10-01", "2026-09-30", 2026, "FY", "10-K", "a26"),
        fact("revenue", "80000000.20", "USD", "2024-10-01", "2025-09-30", 2025, "FY", "10-K", "a25"),
        fact("revenue", "100", "EUR", "2024-10-01", "2025-09-30", 2025, "FY", "10-K", "a25eur"),
    ]
    annual, quarterly, ytd = build_statement_periods(facts)
    assert len(annual) == 2 and not quarterly and not ytd
    metric = annual[0].metrics["revenue"][0]
    assert metric.comparison_percent == 25.0
    assert metric.comparison_period_end == date(2025, 9, 30)
    assert metric.original_value == "100000000.25" and metric.unit == "USD"
    assert metric.comparison_value == "80000000.20"
    assert metric.comparison_form == "10-K"
    assert metric.comparison_accession_number == "a25"


def test_comparative_facts_use_period_dates_instead_of_filing_year_metadata():
    facts = [
        fact("revenue", "100", "USD", "2025-10-01", "2026-09-30", 2026, "FY", "10-K", "annual-26"),
        # A 2026 accession's prior-year value can carry fy=2026 in SEC data.
        fact("revenue", "80", "USD", "2024-10-01", "2025-09-30", 2026, "FY", "10-K", "annual-25"),
        fact("revenue", "30", "USD", "2026-04-01", "2026-06-30", 2026, "Q3", "10-Q", "quarter-26"),
        fact("revenue", "25", "USD", "2025-04-01", "2025-06-30", 2026, "Q3", "10-Q", "quarter-25"),
    ]
    annual, quarterly, _ = build_statement_periods(facts)
    assert [period.fiscal_year for period in annual] == [2026, 2025]
    assert len(annual) == 2
    assert annual[0].metrics["revenue"][0].comparison_percent == 25.0
    assert [period.fiscal_year for period in quarterly] == [2026, 2025]
    assert quarterly[0].metrics["revenue"][0].comparison_percent == 20.0


def test_interim_quarter_labels_use_annual_boundaries_when_sec_fp_conflicts():
    facts = [
        fact("revenue", "100", "USD", "2025-09-28", "2026-09-26", 2026, "FY", "10-K", "fy26"),
        fact("revenue", "90", "USD", "2024-09-29", "2025-09-27", 2025, "FY", "10-K", "fy25"),
        fact("revenue", "80", "USD", "2023-09-30", "2024-09-28", 2024, "FY", "10-K", "fy24"),
        # The report date is Q2 by its position between annual closes even if
        # an instant fact carries stale or contradictory SEC `fp` metadata.
        fact("revenue", "25", "USD", "2026-01-01", "2026-03-28", 2026, "Q2", "10-Q", "q2-flow"),
        fact("assets", "500", "USD", None, "2026-03-28", 2026, "Q3", "10-Q", "q2-instant"),
        fact("revenue", "30", "USD", "2026-03-29", "2026-06-27", 2026, "Q3", "10-Q", "q3-flow"),
        fact("revenue", "20", "USD", "2025-01-01", "2025-03-29", 2025, "Q2", "10-Q", "q2-prior"),
    ]
    _, quarterly, ytd = build_statement_periods(facts)

    assert [(row.fiscal_year, row.fiscal_period, row.period_end) for row in quarterly] == [
        (2026, "Q3", date(2026, 6, 27)),
        (2026, "Q2", date(2026, 3, 28)),
        (2025, "Q2", date(2025, 3, 29)),
    ]
    q2 = quarterly[1]
    assert q2.metrics["revenue"][0].comparison_percent == 25.0
    assert len(q2.metrics["assets"]) == 1
    assert all("assets" not in row.metrics for row in ytd)


def test_quarterly_and_ytd_are_separate_and_yoy_compares_matching_fiscal_periods():
    facts = [
        fact("revenue", "30", "USD", "2026-07-01", "2026-09-30", 2026, "Q3", "10-Q", "q26"),
        fact("revenue", "25", "USD", "2025-07-01", "2025-09-30", 2025, "Q3", "10-Q", "q25"),
        fact("operating_cash_flow", "90", "USD", "2026-01-01", "2026-09-30", 2026, "Q3", "10-Q", "y26"),
        fact("operating_cash_flow", "75", "USD", "2025-01-01", "2025-09-30", 2025, "Q3", "10-Q", "y25"),
        fact("revenue", "120", "USD", "2025-10-01", "2026-09-30", 2026, "FY", "10-K", "fy26"),
    ]
    _, quarterly, ytd = build_statement_periods(facts)
    assert [row.metrics["revenue"][0].original_value for row in quarterly] == ["30", "25"]
    assert quarterly[0].metrics["revenue"][0].comparison_percent == 20.0
    assert [row.metrics["operating_cash_flow"][0].original_value for row in ytd] == ["90", "75"]
    assert ytd[0].metrics["operating_cash_flow"][0].comparison_percent == 20.0
    assert all(row.period_type == "ytd" for row in ytd)


def test_zero_denominator_is_unavailable_and_nonlatest_versions_are_excluded():
    facts = [
        fact("net_income", "5", "USD", "2025-01-01", "2025-03-31", 2025, "Q1", "10-Q", "now"),
        fact("net_income", "0", "USD", "2024-01-01", "2024-03-31", 2024, "Q1", "10-Q", "before"),
        fact("net_income", "4", "USD", "2025-01-01", "2025-03-31", 2025, "Q1", "10-Q", "older", latest=False),
    ]
    _, quarterly, _ = build_statement_periods(facts)
    assert quarterly[0].metrics["net_income"][0].original_value == "5"
    assert quarterly[0].metrics["net_income"][0].comparison_percent is None
    assert quarterly[0].metrics["net_income"][0].comparison_period_end is None


def test_instant_balance_sheet_facts_are_kept_separate_by_reported_unit():
    facts = [
        fact("assets", "1000", "USD", None, "2026-09-30", 2026, "Q3", "10-Q", "instant-usd"),
        fact("assets", "1000", "CAD", None, "2026-09-30", 2026, "Q3", "10-Q", "instant-cad"),
    ]
    _, quarterly, _ = build_statement_periods(facts)
    assert len(quarterly) == 1
    assert {item.unit for item in quarterly[0].metrics["assets"]} == {"USD", "CAD"}
    assert all(item.duration_days is None for item in quarterly[0].metrics["assets"])


def test_mapping_supports_operating_cash_flow_equity_and_amendments_deterministically():
    identity = SecIdentity(cik="0000000001", ticker="EXMP", name="Example Inc", identity_source="approved_fixture")
    submissions = {"cik": 1, "name": "Example Inc", "filings": {"recent": {
        "accessionNumber": ["0000000001-26-000002", "0000000001-26-000001"],
        "form": ["10-Q/A", "10-Q"], "filingDate": ["2026-11-02", "2026-10-20"],
        "reportDate": ["2026-09-30", "2026-09-30"],
        "primaryDocument": ["amended.htm", "original.htm"],
    }}}
    def observation(value, accession, filed, start=None):
        row = {"val": value, "accn": accession, "fy": 2026, "fp": "Q3", "form": "10-Q/A" if accession.endswith("000002") else "10-Q", "filed": filed, "end": "2026-09-30"}
        if start:
            row["start"] = start
        return row
    company_facts = {"cik": 1, "entityName": "Example Inc", "facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"label": "Preferred revenue tag with no observations", "units": {"USD": []}},
        "Revenues": {"label": "Revenue", "units": {"USD": [
            observation(250, "0000000001-26-000002", "2026-11-02", "2026-07-01"),
        ]}},
        "NetCashProvidedByUsedInOperatingActivities": {"label": "Net cash from operating activities", "units": {"USD": [
            observation(120, "0000000001-26-000002", "2026-11-02", "2026-07-01"),
            observation(110, "0000000001-26-000001", "2026-10-20", "2026-07-01"),
        ]}},
        "StockholdersEquity": {"label": "Stockholders’ equity", "units": {"USD": [
            observation(800, "0000000001-26-000002", "2026-11-02"),
        ]}},
    }}}
    report = map_company_facts(identity=identity, requested_ticker="EXMP", company_facts=company_facts, submissions=submissions)
    cashflow = [row for row in report.facts if row.field == "operating_cash_flow"]
    assert len(cashflow) == 2
    assert sum(row.latest_reported_version for row in cashflow) == 1
    assert next(row for row in cashflow if row.latest_reported_version).form == "10-Q/A"
    assert {row.field for row in report.facts} == {"revenue", "operating_cash_flow", "stockholders_equity"}
    assert next(row for row in report.facts if row.field == "revenue").tag == "Revenues"
    assert set(report.missing_fields) == {"operating_income", "net_income", "diluted_eps", "assets", "liabilities", "cash_and_equivalents", "capital_expenditures", "long_term_debt_current", "long_term_debt_noncurrent"}
    assert report.quarterly_periods[0].metrics["operating_cash_flow"][0].original_value == "120"


def test_mapping_exposes_reported_capex_and_debt_components_for_transparent_summary():
    identity = SecIdentity(cik="0000000001", ticker="EXMP", name="Example Inc", identity_source="approved_fixture")
    accession = "0000000001-26-000010"
    submissions = {"cik": 1, "name": "Example Inc", "filings": {"recent": {
        "accessionNumber": [accession], "form": ["10-K"], "filingDate": ["2026-02-01"],
        "reportDate": ["2025-12-31"], "primaryDocument": ["annual.htm"],
    }}}
    def observation(value, *, start=None):
        row = {"val": value, "accn": accession, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-02-01", "end": "2025-12-31"}
        if start:
            row["start"] = start
        return row
    payload = {"cik": 1, "entityName": "Example Inc", "facts": {"us-gaap": {
        "PaymentsToAcquirePropertyPlantAndEquipment": {"label": "Payments to acquire property, plant and equipment", "units": {"USD": [observation(50, start="2025-01-01")]}},
        "LongTermDebtCurrent": {"label": "Long-term debt current", "units": {"USD": [observation(20)]}},
        "LongTermDebtNoncurrent": {"label": "Long-term debt noncurrent", "units": {"USD": [observation(300)]}},
    }}}
    report = map_company_facts(identity=identity, requested_ticker="EXMP", company_facts=payload, submissions=submissions)
    assert {fact.field for fact in report.facts} == {"capital_expenditures", "long_term_debt_current", "long_term_debt_noncurrent"}
    annual = report.annual_periods[0]
    assert annual.metrics["capital_expenditures"][0].original_value == "50"
    assert annual.metrics["long_term_debt_current"][0].original_value == "20"
    assert annual.metrics["long_term_debt_noncurrent"][0].accession_number == accession


def test_conflicting_duplicates_in_latest_accession_are_retained_but_excluded_from_summaries():
    identity = SecIdentity(cik="0000000001", ticker="EXMP", name="Example Inc", identity_source="approved_fixture")
    accession = "0000000001-26-000001"
    submissions = {"cik": 1, "name": "Example Inc", "filings": {"recent": {
        "accessionNumber": [accession], "form": ["10-K"], "filingDate": ["2026-02-01"],
        "reportDate": ["2025-12-31"], "primaryDocument": ["annual.htm"],
    }}}
    fact_rows = [{"val": amount, "accn": accession, "fy": 2025, "fp": "FY", "form": "10-K",
                  "filed": "2026-02-01", "start": "2025-01-01", "end": "2025-12-31"}
                 for amount in (100, 101)]
    payload = {"cik": 1, "entityName": "Example Inc", "facts": {"us-gaap": {
        "Revenues": {"label": "Revenue", "units": {"USD": fact_rows}},
    }}}
    report = map_company_facts(identity=identity, requested_ticker="EXMP", company_facts=payload, submissions=submissions)
    assert len(report.facts) == 2 and not any(row.latest_reported_version for row in report.facts)
    assert report.annual_periods == []
    assert report.status == "partial"
    assert any("Conflicting duplicate SEC observations" in warning for warning in report.warnings)
