"""Pure mapping from SEC-shaped submissions/companyfacts JSON to app records.

This module deliberately has no HTTP client. Callers must supply reviewed
identity mapping and provider payloads; fixtures are labelled as fixtures.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
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


class SecCompanyReport(ProviderModel):
    identity: SecIdentity
    facts: list[SecFinancialFact]
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
}
ALLOWED_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A", "6-K", "6-K/A"}


def _date(value: str | None, *, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise SecMappingError(f"Invalid SEC {field} date.") from exc


def _filing_url(cik: str, accession_number: str, document: str | None) -> str | None:
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
    the latest reported version; earlier filings remain in the output.
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
                           filing_url=_filing_url(identity.cik, accession, document))
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
        chosen_tag = next((tag for tag in candidate_tags if tag in taxonomy), None)
        if chosen_tag is None:
            missing.append(field)
            continue
        concept = taxonomy[chosen_tag]
        if not isinstance(concept, dict):
            missing.append(field)
            continue
        units = concept.get("units", {})
        if not isinstance(units, dict):
            missing.append(field)
            continue
        for unit, observations in units.items():
            if not isinstance(observations, list):
                continue
            for observation in observations:
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
                normalized.append({
                    "field": field, "taxonomy": "us-gaap", "tag": chosen_tag,
                    "label": concept.get("label", chosen_tag), "value": float(value), "original_value": str(value), "unit": unit,
                    "currency": unit.split("/")[0] if unit.startswith(("USD", "EUR", "GBP", "CAD")) else None,
                    "period_start": start, "period_end": end,
                    "fiscal_year": observation.get("fy"), "fiscal_period": observation.get("fp"),
                    "form": form, "filed": filed, "accession_number": accession,
                    "filing_url": filing.filing_url,
                })

    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for item in normalized:
        key = (item["field"], item["unit"], item["period_start"], item["period_end"], item["form"])
        groups[key].append(item)
    latest_by_accession: set[tuple] = set()
    for key, versions in groups.items():
        winner = max(versions, key=lambda item: (item["filed"], item["accession_number"]))
        latest_by_accession.add((key, winner["accession_number"]))
    output = []
    for item in normalized:
        key = (item["field"], item["unit"], item["period_start"], item["period_end"], item["form"])
        output.append(SecFinancialFact(**item, latest_reported_version=(key, item["accession_number"]) in latest_by_accession))
    output.sort(key=lambda item: (item.period_end, item.field, item.unit, item.filed, item.accession_number))
    filings = sorted(filings_by_accession.values(), key=lambda item: (item.filing_date, item.accession_number), reverse=True)
    return SecCompanyReport(identity=identity, facts=output, filings=filings, missing_fields=missing,
                            status="partial" if missing else "ok")
