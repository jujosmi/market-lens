"""SEC research orchestration with injectable transport and pure fact mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from .mapping import STANDARD_FACT_TAGS, SecCompanyReport, SecIdentity, SecMappingError, map_company_facts


class SecEdgarGateway(Protocol):
    """Minimal interface a separately authorized SEC client must implement."""

    def resolve_ticker(self, ticker: str, exchange: str | None = None) -> SecIdentity | None: ...
    def get_submissions(self, cik: str) -> Mapping[str, Any]: ...
    def get_company_facts(self, cik: str) -> Mapping[str, Any]: ...


class SecCompanyResearchService:
    """Map SEC payloads with provenance while keeping the gateway injectable."""

    def __init__(self, gateway: SecEdgarGateway, *, live_data_verified: bool = False) -> None:
        self._gateway = gateway
        self._live_data_verified = live_data_verified

    def get_company_report(self, ticker: str, exchange: str | None = None) -> SecCompanyReport:
        normalized = ticker.strip().upper()
        if not normalized or len(normalized) > 12:
            raise SecMappingError("Ticker must contain 1 to 12 characters.")
        begin_report = getattr(self._gateway, "begin_report", None)
        if begin_report:
            begin_report()
        identity = self._gateway.resolve_ticker(normalized, exchange) if exchange else self._gateway.resolve_ticker(normalized)
        if identity is None:
            raise SecMappingError("No SEC issuer identity is mapped for this ticker.")
        if identity.identity_source != "sec_company_tickers":
            raise SecMappingError("SEC live reports require a provider-verified ticker-to-CIK mapping.")
        warnings: list[str] = []
        try:
            submissions = self._gateway.get_submissions(identity.cik)
        except Exception as exc:
            # Provider exception details are logged by the adapter, not exposed to users.
            from .client import SecClientError
            if not isinstance(exc, SecClientError):
                raise
            return SecCompanyReport(identity=identity, facts=[], filings=[], missing_fields=list(STANDARD_FACT_TAGS),
                                    source="SEC EDGAR", live_data=True, status="partial",
                                    freshness="cached" if getattr(self._gateway, "report_cached", False) else "live",
                                    as_of=datetime.now(timezone.utc).isoformat(),
                                    warnings=[str(exc)])
        try:
            company_facts = self._gateway.get_company_facts(identity.cik)
        except Exception as exc:
            from .client import SecClientError
            if not isinstance(exc, SecClientError):
                raise
            report = map_company_facts(identity=identity, requested_ticker=normalized,
                                       submissions=submissions, company_facts={"cik": identity.cik, "facts": {}})
            return report.model_copy(update={"source": "SEC EDGAR submissions; Company Facts unavailable",
                                             "live_data": True, "status": "partial",
                                             "freshness": "cached" if getattr(self._gateway, "report_cached", False) else "live",
                                             "as_of": datetime.now(timezone.utc).isoformat(),
                                             "warnings": [str(exc)]})
        report = map_company_facts(
            identity=identity,
            requested_ticker=normalized,
            submissions=submissions,
            company_facts=company_facts,
        )
        return report.model_copy(update={
            "source": "SEC EDGAR submissions and Company Facts" if self._live_data_verified else "SEC EDGAR-shaped response via injected gateway (not live-verified)",
            "live_data": self._live_data_verified,
            "status": "partial" if report.missing_fields or not report.facts or not report.filings else "ok",
            "freshness": "cached" if getattr(self._gateway, "report_cached", False) else "live",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "warnings": (["One or more standard XBRL fields are not reported or are not present in the selected taxonomy."] if report.missing_fields else []),
        })
