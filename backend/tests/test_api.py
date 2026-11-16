import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app

class ApiTestClient:
    def get(self, url: str, **kwargs):
        async def request():
            async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://testserver") as client:
                return await client.get(url, **kwargs)
        return asyncio.run(request())


client = ApiTestClient()


def test_health_marks_demo_mode():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "synthetic-fixtures"}


def test_overview_contract_is_synthetic_and_typed():
    body = client.get("/api/v1/overview").json()
    assert body["status"] == "ok"
    assert body["source"] == "synthetic-fixtures"
    assert body["freshness"] == "simulated"
    assert len(body["data"]["markets"]) == 4
    assert all(len(row["series"]) >= 2 for row in body["data"]["markets"])
    assert "not live" in body["data"]["disclosure"]


def test_search_is_bounded_and_returns_no_match_state():
    body = client.get("/api/v1/tickers/search", params={"q": "NVDA"}).json()
    assert body["data"]["results"][0]["symbol"] == "NVDA"
    empty = client.get("/api/v1/tickers/search", params={"q": "ZZZZ"})
    assert empty.status_code == 200
    assert empty.json()["status"] == "unavailable"


def test_invalid_search_is_distinct_and_does_not_echo_input():
    response = client.get("/api/v1/tickers/search", params={"q": "<script>alert(1)</script>"})
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "invalid"
    assert body["data"] is None
    assert "script" not in str(body).casefold()


def test_chart_returns_deterministic_bounded_synthetic_bars():
    first = client.get("/api/v1/tickers/NVDA/chart?range=1D&interval=15m").json()
    second = client.get("/api/v1/tickers/NVDA/chart?range=1D&interval=15m").json()
    assert first == second
    assert first["data"]["interval"] == "15m"
    assert len(first["data"]["bars"]) == 26
    assert "not historical" in first["data"]["label"]


def test_chart_resolution_is_returned_and_history_is_bounded():
    body = client.get("/api/v1/tickers/NVDA/chart?range=1Y&interval=30m").json()
    assert body["status"] == "ok"
    assert body["data"]["interval"] == "30m"
    assert len(body["data"]["bars"]) == 500
    assert "interpolation" in body["data"]["label"]


def test_invalid_chart_resolution_is_classified_as_invalid():
    response = client.get("/api/v1/tickers/NVDA/chart?interval=5m")
    assert response.status_code == 422
    assert response.json()["status"] == "invalid"


def test_discovery_filters_companies_and_industries():
    body = client.get("/api/v1/discovery", params={"sector": "Technology", "industry": "Semiconductors"}).json()
    assert [item["symbol"] for item in body["data"]["companies"]] == ["NVDA"]
    assert body["data"]["companies"][0]["classification_label"] == "simulated classification"


def test_earnings_and_ipo_calendar_are_explicit_synthetic_fixture_responses():
    earnings = client.get("/api/v1/discovery/calendar?kind=earnings&window_days=30").json()
    ipos = client.get("/api/v1/discovery/calendar?kind=ipos&window_days=60").json()
    assert earnings["source"] == ipos["source"] == "synthetic-fixtures"
    assert earnings["data"]["kind"] == "earnings"
    assert ipos["data"]["kind"] == "ipos"
    assert earnings["data"]["items"][0]["symbol"] == "NVDA"
    assert "not actual upcoming" in earnings["data"]["disclosure"]


def test_watchlist_summary_uses_python_engine_and_partial_for_unsupported_symbols():
    body = client.get("/api/v1/watchlist/summaries?symbols=NVDA,ZZZZ,AAPL").json()
    assert body["status"] == "partial"
    assert body["source"] == "python-engine-snapshot"
    summaries = body["data"]["summaries"]
    assert [row["symbol"] for row in summaries] == ["NVDA", "AAPL"]
    assert all(row["sample_close"] is not None and row["technical_rating"] for row in summaries)
    assert "ZZZZ" in body["warnings"][0]


def test_watchlist_summary_rejects_more_than_ten_requested_symbols():
    response = client.get("/api/v1/watchlist/summaries?symbols=" + ",".join(["NVDA"] * 11))
    assert response.status_code == 422
    assert response.json()["status"] == "invalid"


def test_research_and_news_events_are_separate_contracts():
    research = client.get("/api/v1/companies/AMZN/research").json()
    news = client.get("/api/v1/companies/AMZN/news-events").json()
    assert research["data"]["symbol"] == "AMZN"
    assert research["data"]["fundamentals"]
    assert news["data"]["headlines"][0]["sentiment"] == "Bullish"
    assert news["data"]["headlines"][0]["issuer_relevant"] is True
    assert news["data"]["events"]


def test_unknown_ticker_is_unavailable_not_invalid():
    response = client.get("/api/v1/companies/ZZZZ/research")
    assert response.status_code == 404
    assert response.json()["status"] == "unavailable"


def test_unknown_host_is_rejected():
    response = client.get("/api/v1/overview", headers={"host": "example.com"})
    assert response.status_code == 400


def test_cors_is_explicit_for_the_local_vite_frontend():
    allowed = client.get("/api/v1/overview", headers={"origin": "http://127.0.0.1:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    fallback_port = client.get("/api/v1/overview", headers={"origin": "http://127.0.0.1:5174"})
    assert fallback_port.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"
    assert "access-control-allow-credentials" not in allowed.headers
    rejected = client.get("/api/v1/overview", headers={"origin": "https://example.com"})
    assert "access-control-allow-origin" not in rejected.headers


def test_unexpected_fixture_failure_returns_safe_failed_contract(monkeypatch):
    from app import fixtures
    from app.main import provider_cache

    provider_cache.invalidate("synthetic-offline", "overview", {})
    monkeypatch.setattr(fixtures, "MARKETS", ["malformed fixture"])
    response = client.get("/api/v1/overview")
    provider_cache.invalidate("synthetic-offline", "overview", {})
    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "failed"
    assert body["data"] is None
    assert body["warnings"] == ["The demonstration API could not complete this request."]
    assert "malformed fixture" not in response.text
