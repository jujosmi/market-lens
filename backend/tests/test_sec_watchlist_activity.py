from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.sec_edgar.client import SecRateLimited
from app.sec_edgar.discovery import SecDiscoveryService, WATCHLIST_ACTIVITY_FORMS
from app.sec_edgar.mapping import SecIdentity


def submissions(cik: int, name: str) -> dict:
    return {
        "cik": cik,
        "name": name,
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0000320193-26-000004",
                    "0000320193-26-000003",
                    "0000320193-26-000002",
                    "0000320193-26-000001",
                    "0000320193-26-000001",
                ],
                "form": ["10-K/A", "10-K", "8-K", "S-1", "10-K"],
                "filingDate": ["2026-11-18", "2026-11-18", "2026-11-17", "2026-11-16", "2026-11-18"],
                "reportDate": ["2026-09-26", "2026-09-26", "", "", "2026-09-26"],
                "primaryDocument": ["a.htm", "k.htm", "current.htm", "s1.htm", "duplicate.htm"],
                "primaryDocDescription": ["Amended annual report", "Annual report", "Current report", "Registration", "Duplicate"],
                "acceptanceDateTime": [
                    "2026-11-18T16:00:00.000Z",
                    "2026-11-18T15:00:00.000Z",
                    "2026-11-17T13:30:00Z",
                    "2026-11-16T13:00:00Z",
                    "2026-11-18T16:00:00.000Z",
                ],
                "items": ["", "", "2.02, 9.01", "", ""],
            }
        },
    }


class Gateway:
    report_cached = False

    def __init__(self, rate_limit_msft: bool = False):
        self.rate_limit_msft = rate_limit_msft
        self.submission_calls: list[str] = []

    def resolve_ticker(self, ticker: str, exchange: str | None = None):
        companies = {
            "AAPL": ("0000320193", "Apple Inc.", "Nasdaq"),
            "MSFT": ("0000789019", "Microsoft Corporation", "Nasdaq"),
        }
        row = companies.get(ticker)
        if row is None or (exchange and exchange.casefold() != row[2].casefold()):
            return None
        return SecIdentity(cik=row[0], ticker=ticker, name=row[1], exchange=row[2], identity_source="sec_company_tickers")

    def get_submissions(self, cik: str):
        self.submission_calls.append(cik)
        if cik == "0000789019" and self.rate_limit_msft:
            raise SecRateLimited("SEC request limit reached.")
        name = "Apple Inc." if cik == "0000320193" else "Microsoft Corporation"
        return submissions(int(cik), name)


class CacheMarker:
    report_cached = False

    def begin_report(self):
        pass


def test_watchlist_forms_keep_amendment_identity_dedupe_accessions_and_sort_by_acceptance():
    gateway = Gateway()
    data, warnings = SecDiscoveryService(gateway).recent_filings(
        "AAPL",
        limit=20,
        allowed_forms=WATCHLIST_ACTIVITY_FORMS,
    )
    assert [filing.form for filing in data.filings] == ["10-K/A", "10-K", "8-K"]
    assert [filing.accession_number for filing in data.filings] == [
        "0000320193-26-000004",
        "0000320193-26-000003",
        "0000320193-26-000002",
    ]
    assert data.filings[0].primary_doc_description == "Amended annual report"
    assert data.filings[0].acceptance_datetime == "2026-11-18T16:00:00Z"
    assert data.filings[2].items == "2.02, 9.01"
    assert data.filings[2].filing_url == "https://www.sec.gov/Archives/edgar/data/320193/000032019326000002/current.htm"
    assert any("Duplicate" in warning for warning in warnings)


def test_watchlist_batch_keeps_success_when_another_company_is_rate_limited(monkeypatch):
    from app import main

    gateway = Gateway(rate_limit_msft=True)
    client = CacheMarker()
    monkeypatch.setattr(main, "_get_sec_client", lambda: client)
    monkeypatch.setattr(main, "_sec_discovery_service", SecDiscoveryService(gateway))

    response = TestClient(app).post(
        "/api/v1/discovery/filings/watchlist",
        json={"companies": [{"ticker": "AAPL", "exchange": "Nasdaq"}, {"ticker": "MSFT", "exchange": "Nasdaq"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "sec-edgar"
    assert body["status"] == "partial"
    entries = body["data"]["entries"]
    assert [entry["status"] for entry in entries] == ["partial", "rate_limited"]
    assert entries[0]["data"]["filings"][0]["accession_number"] == "0000320193-26-000004"
    assert entries[1]["data"] is None and "limit" in entries[1]["error"].lower()
    assert gateway.submission_calls == ["0000320193", "0000789019"]


def test_watchlist_batch_rejects_invalid_duplicate_and_over_limit_companies():
    client = TestClient(app)
    invalid = client.post("/api/v1/discovery/filings/watchlist", json={"companies": [{"ticker": "../bad", "exchange": None}]})
    duplicate = client.post("/api/v1/discovery/filings/watchlist", json={"companies": [{"ticker": "AAPL", "exchange": "Nasdaq"}, {"ticker": "aapl", "exchange": "NASDAQ"}]})
    over_limit = client.post("/api/v1/discovery/filings/watchlist", json={"companies": [{"ticker": "A" + str(index), "exchange": None} for index in range(6)]})
    assert invalid.status_code == 422
    assert duplicate.status_code == 422
    assert over_limit.status_code == 422
