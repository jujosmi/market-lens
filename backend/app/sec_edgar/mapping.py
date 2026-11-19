"""Pure mapping from SEC-shaped submissions/companyfacts JSON to app records.

This module deliberately has no HTTP client. Callers must supply reviewed
identity mapping and provider payloads; fixtures are labelled as fixtures.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import math
from typing import Any, Literal
from decimal import Decimal

from pydantic import Field, field_validator

from app.providers.contracts import ProviderModel


class SecMappingError(ValueError):
    """Raised when identity or disclosure payloads do not safely map."""


class SecIdentity(ProviderModel):
    cik: str = Field(pattern=r"^\d{10}$")
    ticker: str = Field(min_length=1, max_length=12, pattern=r"^[A-Z0-9.-]+$")
    name: str = Field(min_length=1, max_length=200)
    exchange: str | None = None
    identity_source: Literal["sec_company_tickers", "approved_fixture"]


class SecFiling(ProviderModel):
    cik: str
    accession_number: str
    form: str
    filing_date: date
    report_period: date | None = None
    primary_document: str | None = None
    filing_url: str | None = None


class SecFinancialFact(ProviderModel):
    field: str
    taxonomy: str
    tag: str
    label: str
    value: float
    original_value: str
    unit: str
    currency: str | None = None
    period_start: date | None = None
    period_end: date
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    form: str
    filed: date
    accession_number: str
    filing_url: str | None = None
    latest_reported_version: bool


class SecStatementValue(ProviderModel):
    field: str
    taxonomy: str
    tag: str
    label: str
    value: float
    original_value: str
    unit: str
    currency: str | None = None
    period_start: date | None = None
    period_end: date
    duration_days: int | None = None
    form: str
    filed: date
    accession_number: str
    filing_url: str | None = None
    comparison_percent: float | None = None
    comparison_period_end: date | None = None
    comparison_value: str | None = None
    comparison_filed: date | None = None
    comparison_form: str | None = None
    comparison_accession_number: str | None = None
    comparison_filing_url: str | None = None


class SecStatementPeriod(ProviderModel):
    fiscal_year: int | None = None
    fiscal_period: str | None = None
    period_type: Literal["annual", "quarterly", "ytd"]
    period_start: date | None = None
    period_end: date
    metrics: dict[str, list[SecStatementValue]]


class SecCompanyReport(ProviderModel):
    identity: SecIdentity
    facts: list[SecFinancialFact]
    annual_periods: list[SecStatementPeriod] = Field(default_factory=list)
    quarterly_periods: list[SecStatementPeriod] = Field(default_factory=list)
    ytd_periods: list[SecStatementPeriod] = Field(default_factory=list)
    filings: list[SecFiling]
    missing_fields: list[str]
    source: str = "SEC EDGAR Company Facts schema fixture"
    live_data: bool = False
    status: Literal["ok", "partial"] = "ok"
    freshness: Literal["live", "cached"] = "live"
    as_of: str | None = None
    warnings: list[str] = Field(default_factory=list)


# Only standard, entity-wide tags are included. Company extensions remain
# unmapped until separately reviewed, never guessed by label similarity.
STANDARD_FACT_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss",),
    "diluted_eps": ("EarningsPerShareDiluted",),
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "cash_and_equivalents": ("CashAndCashEquivalentsAtCarryingValue",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capital_expenditures": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "long_term_debt_current": ("LongTermDebtCurrent",),
    "long_term_debt_noncurrent": ("LongTermDebtNoncurrent",),
    "stockholders_equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
}
ALLOWED_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A", "6-K", "6-K/A"}


def _date(value: str | None, *, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise SecMappingError(f"Invalid SEC {field} date.") from exc


def sec_filing_url(cik: str, accession_number: str, document: str | None) -> str | None:
    if not document or "/" in document or "\\" in document or document in {".", ".."}:
        return None
    accession_path = accession_number.replace("-", "")
    if not accession_path.isdigit():
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{document}"


def map_company_facts(
    *,
    identity: SecIdentity,
    requested_ticker: str,
    company_facts: dict[str, Any],
    submissions: dict[str, Any],
) -> SecCompanyReport:
    """Normalize a provided SEC-shaped fixture, preserving filed versions.

    A selected ticker must exactly match the reviewed identity map and CIK in
    both payloads. Facts retain original unit/currency and filing provenance.
    For a same-field/unit/period group, the latest filed accession is marked as
    the latest reported version across original and amended forms; earlier
    filings remain in the output.
    """
    ticker = requested_ticker.strip().upper()
    if not isinstance(company_facts, dict) or not isinstance(submissions, dict):
        raise SecMappingError("SEC company data has an unexpected response shape.")
    if ticker != identity.ticker.upper():
        raise SecMappingError("Ticker does not match the supplied identity mapping.")
    facts_cik = str(company_facts.get("cik", "")).zfill(10)
    subs_cik = str(submissions.get("cik", "")).zfill(10)
    if facts_cik != identity.cik or subs_cik != identity.cik:
        raise SecMappingError("SEC payload CIK does not match the supplied ticker identity.")
    facts_name = company_facts.get("entityName")
    submissions_name = submissions.get("name")
    if facts_name and str(facts_name).strip().casefold() != identity.name.strip().casefold():
        raise SecMappingError("SEC Company Facts issuer name does not match the supplied ticker identity.")
    if submissions_name and str(submissions_name).strip().casefold() != identity.name.strip().casefold():
        raise SecMappingError("SEC submissions issuer name does not match the supplied ticker identity.")

    filings_block = submissions.get("filings", {})
    if not isinstance(filings_block, dict):
        raise SecMappingError("SEC submissions data has an unexpected response shape.")
    filing_rows = filings_block.get("recent", {})
    if not isinstance(filing_rows, dict):
        raise SecMappingError("SEC recent filings data has an unexpected response shape.")
    filings_by_accession: dict[str, SecFiling] = {}
    lengths = [len(v) for v in filing_rows.values() if isinstance(v, list)]
    row_count = min(lengths, default=0)
    for index in range(row_count):
        accession = filing_rows.get("accessionNumber", [])[index]
        form = filing_rows.get("form", [""] * row_count)[index]
        if form not in ALLOWED_FORMS:
            continue
        filed = _date(filing_rows.get("filingDate", [None] * row_count)[index], field="filing")
        report_period = _date(filing_rows.get("reportDate", [None] * row_count)[index], field="report")
        if filed is None:
            continue
        document = filing_rows.get("primaryDocument", [None] * row_count)[index]
        filing = SecFiling(cik=identity.cik, accession_number=accession, form=form,
                           filing_date=filed, report_period=report_period,
                           primary_document=document,
                           filing_url=sec_filing_url(identity.cik, accession, document))
        filings_by_accession[accession] = filing

    facts_block = company_facts.get("facts", {})
    if not isinstance(facts_block, dict):
        raise SecMappingError("SEC Company Facts data has an unexpected response shape.")
    taxonomy = facts_block.get("us-gaap", {})
    if not isinstance(taxonomy, dict):
        raise SecMappingError("SEC standard taxonomy data has an unexpected response shape.")
    normalized: list[dict[str, Any]] = []
    missing: list[str] = []
    for field, candidate_tags in STANDARD_FACT_TAGS.items():
        concept_rows: list[dict[str, Any]] = []
        chosen_tag = None
        for candidate_tag in candidate_tags:
            concept = taxonomy.get(candidate_tag)
            if not isinstance(concept, dict) or not isinstance(concept.get("units"), dict):
                continue
            candidate_rows: list[dict[str, Any]] = []
            for unit, observations in concept["units"].items():
                if not isinstance(observations, list):
                    continue
                for observation in observations:
                    if not isinstance(observation, dict):
                        continue
                    accession = observation.get("accn")
                    form = observation.get("form")
                    filing = filings_by_accession.get(accession)
                    if not accession or not filing or form not in ALLOWED_FORMS or filing.form != form:
                        continue
                    filed = _date(observation.get("filed"), field="fact filed")
                    end = _date(observation.get("end"), field="fact period end")
                    start = _date(observation.get("start"), field="fact period start")
                    if filed is None or end is None:
                        continue
                    value = observation.get("val")
                    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                        continue
                    numeric_value = float(value)
                    if not math.isfinite(numeric_value):
                        continue
                    candidate_rows.append({
                        "field": field, "taxonomy": "us-gaap", "tag": candidate_tag,
                        "label": concept.get("label", candidate_tag), "value": numeric_value, "original_value": str(value), "unit": unit,
                        "currency": unit.split("/")[0] if unit.startswith(("USD", "EUR", "GBP", "CAD")) else None,
                        "period_start": start, "period_end": end,
                        "fiscal_year": observation.get("fy"), "fiscal_period": observation.get("fp"),
                        "form": form, "filed": filed, "accession_number": accession,
                        "filing_url": filing.filing_url,
                    })
            if candidate_rows:
                chosen_tag = candidate_tag
                concept_rows = candidate_rows
                break
        if chosen_tag is None:
            missing.append(field)
            continue
        normalized.extend(concept_rows)

    groups: dict[tuple, list[int]] = defaultdict(list)
    for index, item in enumerate(normalized):
        key = (item["field"], item["unit"], item["period_start"], item["period_end"])
        groups[key].append(index)
    latest_indices: set[int] = set()
    duplicate_warnings: list[str] = []
    for key, version_indices in groups.items():
        latest_filed, latest_accession = max(
            (normalized[index]["filed"], normalized[index]["accession_number"])
            for index in version_indices
        )
        candidates = [index for index in version_indices
                      if (normalized[index]["filed"], normalized[index]["accession_number"]) == (latest_filed, latest_accession)]
        candidate_values = {normalized[index]["original_value"] for index in candidates}
        if len(candidate_values) == 1:
            # Exact duplicate observations from one accession are preserved in
            # raw facts, while one stable occurrence supplies the summary.
            latest_indices.add(min(candidates))
        else:
            duplicate_warnings.append(
                f"Conflicting duplicate SEC observations for {key[0]} through {key[3].isoformat()} were excluded from summaries."
            )
    output = []
    for index, item in enumerate(normalized):
        output.append(SecFinancialFact(**item, latest_reported_version=index in latest_indices))
    output.sort(key=lambda item: (item.period_end, item.field, item.unit, item.filed, item.accession_number))
    filings = sorted(filings_by_accession.values(), key=lambda item: (item.filing_date, item.accession_number), reverse=True)
    report = SecCompanyReport(identity=identity, facts=output, filings=filings, missing_fields=missing,
                              warnings=duplicate_warnings, status="partial" if missing or duplicate_warnings else "ok")
    from .statements import build_statement_periods
    annual, quarterly, ytd = build_statement_periods(output)
    return report.model_copy(update={"annual_periods": annual, "quarterly_periods": quarterly, "ytd_periods": ytd})
