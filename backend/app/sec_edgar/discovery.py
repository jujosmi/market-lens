"""Read-only SEC directory search and demand-driven filing enrichment."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Protocol

from app.contracts import SecDirectoryCompany, SecDirectoryData, SecFilingActivity, SecFilingsData, SecIndustryCompany, SecIndustryData
from app.sec_edgar.mapping import SecIdentity, SecMappingError, sec_filing_url
from app.sec_edgar.client import SecAccessBlocked, SecClientError, SecRateLimited
from app.sec_edgar.sic_classification import sic_sector


DIRECTORY_DISCLOSURE = (
    "Source: SEC EDGAR company_tickers_exchange.json. SEC says ticker/CIK/exchange "
    "associations may not be accurate or complete. This is not a complete or authoritative "
    "inventory of currently tradable securities. The source provides no GICS sector or "
    "industry classification."
)
FILINGS_DISCLOSURE = (
    "Source: SEC EDGAR issuer submissions. These are filed documents, not scheduled events "
    "or earnings announcements. An 8-K is not characterized as earnings-related without "
    "reviewing the filing. An S-1 does not establish an IPO trading date."
)
INDUSTRY_DISCLOSURE = (
    "Industry source: official SEC issuer submissions (SIC and SIC description). Broad browse groups follow U.S. SIC major divisions; they are not GICS or another commercial taxonomy. "
    "Only the current search page, up to 10 SEC directory matches, is classified on demand. This is partial coverage, not a complete market industry directory. Issuers without a valid SEC SIC are excluded from industry matches."
)
DISCOVERY_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A", "S-1", "S-1/A"}
WATCHLIST_ACTIVITY_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"}


class SecDiscoveryGateway(Protocol):
    report_cached: bool

    def get_ticker_directory(self) -> list[dict[str, Any]]: ...
    def resolve_ticker(self, ticker: str, exchange: str | None = None) -> SecIdentity | None: ...
    def get_submissions(self, cik: str) -> dict[str, Any]: ...


class SecDiscoveryService:
    def __init__(self, gateway: SecDiscoveryGateway):
        self._gateway = gateway

    def list_companies(self, *, query: str = "", exchange: str | None = None,
                       limit: int = 25, offset: int = 0) -> SecDirectoryData:
        rows = self._gateway.get_ticker_directory()
        companies: list[SecDirectoryCompany] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ticker = row.get("ticker")
            name = row.get("name")
            cik_value = row.get("cik")
            exchange_value = row.get("exchange")
            if not isinstance(ticker, str) or not ticker.strip() or not isinstance(name, str) or not name.strip():
                continue
            try:
                cik = str(int(cik_value)).zfill(10)
            except (TypeError, ValueError, OverflowError):
                continue
            exchange_name = exchange_value.strip() if isinstance(exchange_value, str) and exchange_value.strip() else None
            companies.append(SecDirectoryCompany(ticker=ticker.strip().upper(), name=name.strip(), cik=cik, exchange=exchange_name))

        available_exchanges = sorted({item.exchange for item in companies if item.exchange}, key=str.casefold)
        normalized_query = " ".join(query.split()).casefold()
        normalized_exchange = exchange.strip().casefold() if exchange else ""
        filtered = [item for item in companies
                    if (not normalized_exchange or (item.exchange or "").casefold() == normalized_exchange)
                    and (not normalized_query or normalized_query in item.ticker.casefold() or normalized_query in item.name.casefold())]
        filtered.sort(key=lambda item: (item.name.casefold(), item.ticker, item.exchange or ""))
        total = len(filtered)
        return SecDirectoryData(
            companies=filtered[offset:offset + limit], total=total, limit=limit, offset=offset,
            query=query, exchange=exchange, available_exchanges=available_exchanges,
            disclosure=DIRECTORY_DISCLOSURE,
        )

    def industry_companies(self, *, query: str, exchange: str | None = None,
                           limit: int = 10, offset: int = 0) -> tuple[SecIndustryData, list[str]]:
        """Enrich only a bounded page of explicit SEC directory search results."""
        if len(" ".join(query.split())) < 2:
            raise SecMappingError("Enter at least two letters to classify SEC directory matches.")
        if not 1 <= limit <= 10:
            raise SecMappingError("Industry lookup is limited to ten directory matches per request.")
        directory = self.list_companies(query=query, exchange=exchange, limit=limit, offset=offset)
        companies: list[SecIndustryCompany] = []
        warnings: list[str] = []
        unclassified = 0
        for index, row in enumerate(directory.companies):
            try:
                submissions = self._gateway.get_submissions(row.cik)
            except (SecClientError, SecMappingError) as exc:
                # An SEC-wide access block or rate limit must stop immediately.
                if isinstance(exc, (SecAccessBlocked, SecRateLimited)):
                    raise
                warnings.append("SEC classification could not be retrieved for one or more search results; available verified results are shown.")
                # Do not repeatedly hit an unavailable provider for the rest of the page.
                unclassified += len(directory.companies) - index
                break
            try:
                returned_cik = str(int(submissions.get("cik"))).zfill(10)
            except (TypeError, ValueError, OverflowError):
                returned_cik = ""
            if returned_cik != row.cik:
                warnings.append("An issuer classification was omitted because its SEC CIK did not match the selected directory record.")
                unclassified += 1
                continue
            raw_sic = submissions.get("sic")
            sic = str(raw_sic).strip() if raw_sic is not None else ""
            description = submissions.get("sicDescription")
            description = description.strip() if isinstance(description, str) else ""
            broad_group = sic_sector(sic)
            if broad_group is None or not description:
                unclassified += 1
                continue
            companies.append(SecIndustryCompany(
                ticker=row.ticker, name=row.name, cik=row.cik, exchange=row.exchange,
                sic=sic, sic_description=description, sic_sector=broad_group,
            ))
        data = SecIndustryData(
            companies=companies, total_matches=directory.total, total_candidates=len(directory.companies), limit=limit,
            offset=offset, query=query, exchange=exchange,
            available_exchanges=directory.available_exchanges,
            classified_count=len(companies), unclassified_count=unclassified,
            disclosure=INDUSTRY_DISCLOSURE,
        )
        return data, warnings

    def recent_filings(self, ticker: str, *, exchange: str | None = None,
                       limit: int = 20, allowed_forms: set[str] | None = None) -> tuple[SecFilingsData, list[str]]:
        identity = self._gateway.resolve_ticker(ticker, exchange)
        if identity is None:
            raise SecMappingError("No unique SEC company matched this ticker and exchange. Search the SEC directory and select an exchange-qualified company.")
        submissions = self._gateway.get_submissions(identity.cik)
        if str(submissions.get("cik", "")).zfill(10) != identity.cik:
            raise SecMappingError("SEC submissions CIK does not match the selected issuer.")
        issuer_name = submissions.get("name")
        if issuer_name and str(issuer_name).strip().casefold() != identity.name.strip().casefold():
            raise SecMappingError("SEC submissions issuer name does not match the selected issuer.")
        recent = submissions.get("filings", {}).get("recent", {})
        if not isinstance(recent, dict):
            raise SecMappingError("SEC recent filings response has an unsupported shape.")
        required = ("accessionNumber", "form", "filingDate")
        if any(not isinstance(recent.get(field), list) for field in required):
            raise SecMappingError("SEC recent filings response has an unsupported shape.")
        columns = {key: recent.get(key) for key in (
            *required, "reportDate", "primaryDocument", "primaryDocDescription",
            "acceptanceDateTime", "items",
        )}
        row_count = min(len(columns[key]) for key in required)
        activities: list[SecFilingActivity] = []
        warnings: list[str] = []
        seen_accessions: set[str] = set()
        forms = DISCOVERY_FORMS if allowed_forms is None else allowed_forms
        sic = submissions.get("sic")
        sic = str(sic).strip() if sic is not None and str(sic).strip() else None
        sic_description = submissions.get("sicDescription")
        sic_description = str(sic_description).strip() if isinstance(sic_description, str) and sic_description.strip() else None
        for index in range(row_count):
            accession = columns["accessionNumber"][index]
            filed = columns["filingDate"][index]
            if not isinstance(accession, str) or not isinstance(filed, str):
                warnings.append("Some SEC filing rows were incomplete and omitted.")
                continue
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
                warnings.append("Some SEC filing rows had invalid accession identifiers and were omitted.")
                continue
            if accession in seen_accessions:
                warnings.append("Duplicate SEC accession rows were omitted.")
                continue
            seen_accessions.add(accession)
            form = columns["form"][index]
            if form not in forms:
                continue
            try:
                filed_date = date.fromisoformat(filed)
            except ValueError:
                warnings.append("Some SEC filing rows had invalid dates and were omitted.")
                continue
            report_date_value = columns["reportDate"][index] if isinstance(columns["reportDate"], list) and index < len(columns["reportDate"]) else None
            report_date = None
            if isinstance(report_date_value, str) and report_date_value:
                try:
                    report_date = date.fromisoformat(report_date_value).isoformat()
                except ValueError:
                    warnings.append("A filing report period was not provided in a valid date format.")
            primary = columns["primaryDocument"][index] if isinstance(columns["primaryDocument"], list) and index < len(columns["primaryDocument"]) else None
            if not isinstance(primary, str):
                primary = None
            description_value = columns["primaryDocDescription"][index] if isinstance(columns["primaryDocDescription"], list) and index < len(columns["primaryDocDescription"]) else None
            description = description_value.strip()[:300] if isinstance(description_value, str) and description_value.strip() else None
            acceptance_value = columns["acceptanceDateTime"][index] if isinstance(columns["acceptanceDateTime"], list) and index < len(columns["acceptanceDateTime"]) else None
            acceptance_datetime = None
            if isinstance(acceptance_value, str) and acceptance_value.strip():
                try:
                    parsed_acceptance = datetime.fromisoformat(acceptance_value.strip().replace("Z", "+00:00"))
                    if parsed_acceptance.tzinfo is None:
                        raise ValueError("timezone missing")
                    acceptance_datetime = parsed_acceptance.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                except ValueError:
                    warnings.append("A filing acceptance timestamp was invalid and omitted.")
            items_value = columns["items"][index] if isinstance(columns["items"], list) and index < len(columns["items"]) else None
            # SEC submissions expose 8-K item identifiers as a comma-separated
            # string. Preserve the provider value; never infer it from a title.
            items = items_value.strip() if isinstance(items_value, str) and items_value.strip() else None
            activities.append(SecFilingActivity(
                cik=identity.cik, ticker=identity.ticker, company_name=identity.name,
                exchange=identity.exchange, sic=sic, sic_description=sic_description, form=form,
                filing_date=filed_date.isoformat(), report_date=report_date,
                accession_number=accession, primary_document=primary,
                filing_url=sec_filing_url(identity.cik, accession, primary), items=items,
                acceptance_datetime=acceptance_datetime, primary_doc_description=description,
            ))
        activities.sort(
            key=lambda item: (
                item.acceptance_datetime or item.filing_date + "T00:00:00Z",
                item.filing_date,
                item.accession_number,
            ),
            reverse=True,
        )
        data = SecFilingsData(
            ticker=identity.ticker, company_name=identity.name, cik=identity.cik,
            exchange=identity.exchange, sic=sic, sic_description=sic_description,
            filings=activities[:limit], forms=["10-K", "10-Q", "8-K", "S-1"],
            disclosure=FILINGS_DISCLOSURE,
        )
        return data, list(dict.fromkeys(warnings))
