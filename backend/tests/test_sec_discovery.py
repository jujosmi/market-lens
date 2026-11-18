from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sec_edgar.client import SecEdgarHttpClient, SecEdgarSettings, SharedRateLimiter
from app.sec_edgar.discovery import SecDiscoveryService
from app.sec_edgar.mapping import SecIdentity, SecMappingError


UA = "Jujosmi Trade/2.0 sec-discovery-test@jtrade.test"


class Gateway:
    report_cached = False

    def __init__(self):
        self.rows = [
            {"cik": 320193, "name": "Apple Inc.", "ticker": "AAPL", "exchange": "Nasdaq"},
            {"cik": 789019, "name": "Microsoft Corporation", "ticker": "MSFT", "exchange": "Nasdaq"},
            {"cik": 1000001, "name": "Example Holdings", "ticker": "EXM", "exchange": "NYSE"},
            {"cik": 1000002, "name": "Example Holdings Class B", "ticker": "EXM", "exchange": "Nasdaq"},
        ]
        self.submissions_calls = []

    def get_ticker_directory(self):
        return self.rows

    def resolve_ticker(self, ticker, exchange=None):
        matches=[row for row in self.rows if row["ticker"] == ticker and (not exchange or row["exchange"].casefold() == exchange.casefold())]
        if len(matches) != 1: return None
        row=matches[0]
        return SecIdentity(cik=str(row["cik"]).zfill(10),ticker=row["ticker"],name=row["name"],exchange=row["exchange"],identity_source="sec_company_tickers")

    def get_submissions(self, cik):
        self.submissions_calls.append(cik)
        name = "Example Holdings" if cik == "0001000001" else "Apple Inc."
        return {
            "cik": int(cik), "name": name, "sic": "3571", "sicDescription": "Electronic Computers",
            "filings": {"recent": {
                "accessionNumber": ["0000320193-26-000003", "0000320193-26-000002", "0000320193-26-000001", "0000320193-26-000000"],
                "form": ["8-K", "10-Q", "S-1", "4"],
                "filingDate": ["2026-11-03", "2026-10-30", "2026-10-25", "2026-10-20"],
                "reportDate": ["2026-10-31", "2026-09-27", "", "2026-09-30"],
                "primaryDocument": ["current.htm", "quarter.htm", "registration.htm", "form4.xml"],
            }}
        }


def test_directory_search_filters_company_ticker_exchange_and_paginates():
    service=SecDiscoveryService(Gateway())
    first=service.list_companies(query="apple",limit=1,offset=0)
    assert first.total == 1 and first.companies[0].ticker == "AAPL"
    assert first.companies[0].cik == "0000320193" and first.companies[0].exchange == "Nasdaq"
    page=service.list_companies(query="example",limit=1,offset=1)
    assert page.total == 2 and page.offset == 1 and page.companies[0].ticker == "EXM"
    assert page.available_exchanges == ["Nasdaq", "NYSE"]
    nyse=service.list_companies(query="EXM",exchange="NYSE")
    assert nyse.total == 1 and nyse.companies[0].name == "Example Holdings"
    assert "not a complete" in nyse.disclosure


def test_directory_does_not_invent_sector_or_financial_metrics():
    data=SecDiscoveryService(Gateway()).list_companies(query="AAPL")
    row=data.companies[0].model_dump()
    assert set(row) == {"ticker", "name", "cik", "exchange"}
    assert "GICS" in data.disclosure


def test_recent_filings_include_only_requested_actual_forms_and_sec_provenance():
    gateway=Gateway()
    data,warnings=SecDiscoveryService(gateway).recent_filings("AAPL",limit=10)
    assert [filing.form for filing in data.filings] == ["8-K", "10-Q", "S-1"]
    assert data.sic == "3571" and data.sic_description == "Electronic Computers"
    assert data.filings[0].filing_date == "2026-11-03"
    assert data.filings[0].report_date == "2026-10-31"
    assert data.filings[0].accession_number == "0000320193-26-000003"
    assert data.filings[0].filing_url == "https://www.sec.gov/Archives/edgar/data/320193/000032019326000003/current.htm"
    assert data.filings[2].report_date is None and warnings == []
    assert "not scheduled events" in data.disclosure


def test_duplicate_ticker_requires_exchange_and_issuer_identity_is_checked():
    service=SecDiscoveryService(Gateway())
    with pytest.raises(SecMappingError,match="No unique SEC company"):
        service.recent_filings("EXM")
    data,_=service.recent_filings("EXM",exchange="NYSE")
    assert data.cik == "0001000001"
    gateway=Gateway()
    gateway.get_submissions=lambda _cik: {"cik": 2,"name":"Wrong Issuer","filings":{"recent":{}}}
    with pytest.raises(SecMappingError,match="does not match"):
        SecDiscoveryService(gateway).recent_filings("AAPL")


def test_directory_http_adapter_uses_official_columnar_shape_and_cache():
    calls=[]
    payload={"fields":["cik","name","ticker","exchange"],"data":[[320193,"Apple Inc.","AAPL","Nasdaq"],[789019,"Microsoft Corporation","MSFT","Nasdaq"]]}
    def handler(request):
        calls.append(request)
        assert request.url == "https://www.sec.gov/files/company_tickers_exchange.json"
        assert request.headers["user-agent"] == UA
        return httpx.Response(200,json=payload)
    client=SecEdgarHttpClient(SecEdgarSettings(UA),transport=httpx.MockTransport(handler),limiter=SharedRateLimiter(0))
    client.begin_report(); first=client.get_ticker_directory()
    assert first[0]["cik"] == 320193
    assert client.report_cached is False
    client.begin_report(); second=client.get_ticker_directory()
    assert second == first and client.report_cached is True
    assert len(calls)==1 and client.cache_hits==1
    client.close()


def test_sec_ticker_identity_can_be_qualified_by_exchange():
    payload={"fields":["cik","name","ticker","exchange"],"data":[[1234,"First Example","EXM","NYSE"],[5678,"Second Example","EXM","Nasdaq"]]}
    client=SecEdgarHttpClient(SecEdgarSettings(UA),transport=httpx.MockTransport(lambda _request:httpx.Response(200,json=payload)),limiter=SharedRateLimiter(0))
    assert client.resolve_ticker("EXM") is None
    assert client.resolve_ticker("EXM","NYSE").cik == "0000001234"
    assert client.resolve_ticker("EXM","Nasdaq").name == "Second Example"
    client.close()


def test_discovery_directory_endpoint_uses_sec_envelope_and_bounded_parameters(monkeypatch):
    from app import main
    gateway=Gateway(); service=SecDiscoveryService(gateway)
    class CacheMarker:
        report_cached=False
        def begin_report(self): pass
    monkeypatch.setattr(main,"_get_sec_client",lambda:CacheMarker())
    monkeypatch.setattr(main,"_sec_discovery_service",service)
    response=TestClient(app).get("/api/v1/discovery/companies?q=Apple&limit=1&offset=0")
    assert response.status_code==200
    body=response.json()
    assert body["source"]=="sec-edgar" and body["freshness"]=="live"
    assert body["data"]["total"]==1 and body["data"]["companies"][0]["cik"]=="0000320193"
    assert "not a complete" in body["data"]["disclosure"]
    invalid=TestClient(app).get("/api/v1/discovery/companies?limit=500")
    assert invalid.status_code==422


def test_discovery_filings_endpoint_preserves_filing_metadata(monkeypatch):
    from app import main
    class CacheMarker:
        report_cached=True
        def begin_report(self): pass
    monkeypatch.setattr(main,"_get_sec_client",lambda:CacheMarker())
    monkeypatch.setattr(main,"_sec_discovery_service",SecDiscoveryService(Gateway()))
    response=TestClient(app).get("/api/v1/discovery/filings/AAPL")
    assert response.status_code==200
    body=response.json()
    assert body["freshness"]=="cached" and body["provenance"]=="Official SEC EDGAR issuer submissions"
    assert body["data"]["sic_description"]=="Electronic Computers"
    assert body["data"]["filings"][0]["form"]=="8-K"


def test_discovery_endpoints_fail_safely_when_sec_user_agent_is_not_configured(monkeypatch):
    from app import main
    from app.sec_edgar.client import SecConfigurationError
    monkeypatch.setattr(main,"_get_sec_client",lambda:(_ for _ in ()).throw(SecConfigurationError("SEC EDGAR is not configured with an identifying User-Agent contact.")))
    monkeypatch.setattr(main,"_sec_discovery_service",None)
    response=TestClient(app).get("/api/v1/discovery/companies")
    assert response.status_code==503
    assert response.json()["data"] is None
    assert "User-Agent contact" in response.json()["warnings"][0]


def test_public_sec_research_route_forwards_exchange_qualifier(monkeypatch):
    from app import main
    from app.sec_edgar.mapping import SecCompanyReport
    captured={}
    class Service:
        def get_company_report(self, ticker, exchange=None):
            captured.update(ticker=ticker,exchange=exchange)
            return SecCompanyReport(
                identity=SecIdentity(cik="0001000001",ticker=ticker,name="Example Holdings",exchange=exchange,identity_source="sec_company_tickers"),
                facts=[],filings=[],missing_fields=["revenue"],live_data=True,status="partial",as_of="2026-11-17T12:00:00Z",
            )
    monkeypatch.setattr(main,"_sec_service",Service())
    response=TestClient(app).get("/api/v1/companies/EXM/sec-research?exchange=NYSE")
    assert response.status_code==200
    assert captured=={"ticker":"EXM","exchange":"NYSE"}
    assert response.json()["data"]["identity"]["exchange"]=="NYSE"
