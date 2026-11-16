from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sec_edgar import client as sec_client_module
from app.sec_edgar.client import SecAccessBlocked, SecClientError, SecConfigurationError, SecEdgarHttpClient, SecEdgarSettings, SharedRateLimiter
from app.sec_edgar.service import SecCompanyResearchService


UA = "Jujosmi Trade/2.0 sec-test@jtrade.test"


def ticker_directory(rows):
    """SEC company_tickers_exchange.json uses fields plus ordered data rows."""
    return {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[row["cik"], row["name"], row["ticker"], row.get("exchange")] for row in rows],
    }


def test_sec_client_requires_real_identifying_user_agent(monkeypatch):
    monkeypatch.delenv("SEC_EDGAR_USER_AGENT", raising=False)
    with pytest.raises(SecConfigurationError, match="identifying User-Agent"):
        SecEdgarSettings.from_env()
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "Jujosmi Trade/2.0 your.email@example.com")
    with pytest.raises(SecConfigurationError):
        SecEdgarSettings.from_env()
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", "Jujosmi Trade/2.0 sec-test@jtrade.test")
    assert SecEdgarSettings.from_env().user_agent.endswith("sec-test@jtrade.test")


def test_identity_and_company_data_use_only_official_fixed_endpoints_and_cache():
    calls = []
    ticker_map = ticker_directory([{"cik": 320193, "name": "Apple Inc.", "ticker": "AAPL", "exchange": "Nasdaq"}])
    def handler(request):
        calls.append(request)
        assert request.url.host in {"www.sec.gov", "data.sec.gov"}
        assert request.headers["user-agent"] == UA
        if request.url.path.endswith("company_tickers_exchange.json"):
            payload = ticker_map
        elif "/submissions/" in request.url.path:
            payload = {"cik": 320193, "filings": {"recent": {}}}
        else:
            payload = {"cik": 320193, "facts": {"us-gaap": {}}}
        return httpx.Response(200, json=payload)
    client = SecEdgarHttpClient(SecEdgarSettings(UA), transport=httpx.MockTransport(handler), limiter=SharedRateLimiter(0))
    resolved = client.resolve_ticker("aapl")
    assert resolved.cik == "0000320193" and resolved.exchange == "Nasdaq"
    client.resolve_ticker("AAPL")
    assert len(calls) == 1 and client.cache_hits == 1
    client.get_submissions("0000320193")
    client.get_company_facts("0000320193")
    client.get_submissions("0000320193")
    client.get_company_facts("0000320193")
    assert [call.url.path for call in calls] == ["/files/company_tickers_exchange.json", "/submissions/CIK0000320193.json", "/api/xbrl/companyfacts/CIK0000320193.json"]
    assert len(calls) == 3 and client.cache_hits == 3
    client.close()


def test_ambiguous_or_missing_ticker_is_not_guessed():
    def handler(_):
        return httpx.Response(200, json=ticker_directory([
            {"cik": 1, "name": "One", "ticker": "ABC"},
            {"cik": 2, "name": "Two", "ticker": "ABC"},
        ]))
    client = SecEdgarHttpClient(SecEdgarSettings(UA), transport=httpx.MockTransport(handler), limiter=SharedRateLimiter(0))
    assert client.resolve_ticker("ABC") is None
    client.close()


def test_ticker_directory_rejects_malformed_columnar_rows_without_guessing():
    malformed = [
        {"fields": ["cik", "name", "ticker"], "data": [[320193, "Apple Inc."]]},
        {"fields": ["cik", "name", "ticker", "ticker"], "data": []},
        {"fields": ["cik", "name"], "data": [[320193, "Apple Inc."]]},
        [{"cik": 320193, "name": "Apple Inc.", "ticker": "AAPL"}],
    ]
    for payload in malformed:
        client = SecEdgarHttpClient(
            SecEdgarSettings(UA),
            transport=httpx.MockTransport(lambda _, payload=payload: httpx.Response(200, json=payload)),
            limiter=SharedRateLimiter(0),
        )
        with pytest.raises(SecClientError, match="unsupported response shape"):
            client.resolve_ticker("AAPL")
        client.close()


def test_non_json_success_response_is_reported_as_unreadable_not_shape_mismatch():
    client = SecEdgarHttpClient(
        SecEdgarSettings(UA),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>unavailable</html>", headers={"content-type": "text/html"})),
        limiter=SharedRateLimiter(0),
    )
    with pytest.raises(SecClientError, match="unreadable response"):
        client.resolve_ticker("AAPL")
    client.close()


def test_sec_403_stops_following_live_requests(monkeypatch):
    sec_client_module._BLOCKED.clear()
    calls = []
    def handler(_):
        calls.append(1)
        return httpx.Response(403)
    client = SecEdgarHttpClient(SecEdgarSettings(UA), transport=httpx.MockTransport(handler), limiter=SharedRateLimiter(0))
    with pytest.raises(SecAccessBlocked):
        client.resolve_ticker("AAPL")
    with pytest.raises(SecAccessBlocked):
        client.resolve_ticker("AAPL")
    assert len(calls) == 1
    client.close(); sec_client_module._BLOCKED.clear()


def test_sec_retries_only_bounded_transient_server_errors():
    calls = []
    def handler(_):
        calls.append(1)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json=ticker_directory([]))
    client = SecEdgarHttpClient(SecEdgarSettings(UA), transport=httpx.MockTransport(handler), limiter=SharedRateLimiter(0))
    assert client.resolve_ticker("AAPL") is None
    assert len(calls) == 2
    client.close()


def test_sec_report_preserves_original_decimal_value_and_partial_fields():
    cik = "0000320193"
    identity = {"cik": cik, "name": "Apple Inc.", "ticker": "AAPL", "identity_source": "sec_company_tickers"}
    submissions = {"cik": int(cik), "filings": {"recent": {"accessionNumber": ["0000320193-26-000001"], "form": ["10-Q"], "filingDate": ["2026-10-30"], "reportDate": ["2026-09-27"], "primaryDocument": ["q.htm"]}}}
    facts = {"cik": int(cik), "facts": {"us-gaap": {"Revenues": {"label": "Revenue", "units": {"USD": [{"val": "1", "accn": "0000320193-26-000001", "form": "10-Q", "filed": "2026-10-30", "start": "2026-06-29", "end": "2026-09-27"}]}}}}}
    # json parser turns numeric JSON tokens into Decimal; this is the same payload path as the live client.
    from decimal import Decimal
    facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["val"] = Decimal("123456789.123456789")
    class Gateway:
        def resolve_ticker(self, _):
            from app.sec_edgar.mapping import SecIdentity
            return SecIdentity(**identity)
        def get_submissions(self, _): return submissions
        def get_company_facts(self, _): return facts
    report = SecCompanyResearchService(Gateway(), live_data_verified=True).get_company_report("AAPL")
    assert report.facts[0].original_value == "123456789.123456789"
    assert report.facts[0].period_end.isoformat() == "2026-09-27"
    assert report.facts[0].accession_number == "0000320193-26-000001"
    assert report.status == "partial" and "diluted_eps" in report.missing_fields


def test_partial_company_facts_failure_preserves_independent_submissions_data():
    from app.sec_edgar.mapping import SecIdentity
    cik = "0000320193"
    class Gateway:
        def resolve_ticker(self, _): return SecIdentity(cik=cik, ticker="AAPL", name="Apple Inc.", identity_source="sec_company_tickers")
        def get_submissions(self, _):
            return {"cik": int(cik), "name": "Apple Inc.", "filings": {"recent": {"accessionNumber": ["0000320193-26-000001"], "form": ["10-Q"], "filingDate": ["2026-10-30"], "reportDate": ["2026-09-27"], "primaryDocument": ["q.htm"]}}}
        def get_company_facts(self, _): raise SecClientError("SEC data is currently unavailable.")
    report = SecCompanyResearchService(Gateway(), live_data_verified=True).get_company_report("AAPL")
    assert report.status == "partial" and report.filings[0].form == "10-Q"
    assert report.facts == [] and report.warnings


def test_sec_api_fails_closed_with_clear_configuration_message(monkeypatch):
    monkeypatch.delenv("SEC_EDGAR_USER_AGENT", raising=False)
    response = TestClient(app).get("/api/v1/companies/AAPL/sec-research")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert "User-Agent contact" in response.json()["warnings"][0]


def test_sec_api_returns_typed_live_envelope_from_injected_provider(monkeypatch):
    from app import main
    from app.sec_edgar.mapping import SecIdentity
    cik = "0000320193"
    identity = SecIdentity(cik=cik, ticker="AAPL", name="Apple Inc.", identity_source="sec_company_tickers")
    submissions = {"cik": int(cik), "name": "Apple Inc.", "filings": {"recent": {}}}
    facts = {"cik": int(cik), "entityName": "Apple Inc.", "facts": {"us-gaap": {}}}
    class Gateway:
        def resolve_ticker(self, _): return identity
        def get_submissions(self, _): return submissions
        def get_company_facts(self, _): return facts
    monkeypatch.setattr(main, "_sec_service", SecCompanyResearchService(Gateway(), live_data_verified=True))
    response = TestClient(app).get("/api/v1/companies/AAPL/sec-research")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "sec-edgar" and body["freshness"] == "live"
    assert body["data"]["identity"]["cik"] == cik
    assert body["status"] == "partial"


def test_local_api_to_sec_http_adapter_integration_uses_only_mocked_sec_transport(monkeypatch):
    from app import main
    sec_client_module._BLOCKED.clear()
    calls = []
    payloads = {
        "/files/company_tickers_exchange.json": ticker_directory([{"cik": 320193, "name": "Apple Inc.", "ticker": "AAPL", "exchange": "Nasdaq"}]),
        "/submissions/CIK0000320193.json": {"cik": 320193, "name": "Apple Inc.", "filings": {"recent": {}}},
        "/api/xbrl/companyfacts/CIK0000320193.json": {"cik": 320193, "entityName": "Apple Inc.", "facts": {"us-gaap": {}}},
    }
    def handler(request):
        calls.append(request.url.path)
        assert request.headers["user-agent"] == UA
        return httpx.Response(200, json=payloads[request.url.path])
    def fake_client(settings):
        assert settings.user_agent == UA
        return SecEdgarHttpClient(settings, transport=httpx.MockTransport(handler), limiter=SharedRateLimiter(0))
    monkeypatch.setenv("SEC_EDGAR_USER_AGENT", UA)
    monkeypatch.setattr(main, "_sec_service", None)
    monkeypatch.setattr(main, "_sec_client", None)
    monkeypatch.setattr(main, "SecEdgarHttpClient", fake_client)
    response = TestClient(app).get("/api/v1/companies/AAPL/sec-research")
    assert response.status_code == 200
    assert response.json()["source"] == "sec-edgar"
    assert response.json()["data"]["identity"]["cik"] == "0000320193"
    assert len(calls) == 3

