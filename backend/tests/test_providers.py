from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.providers.cache import CachePolicy, ProviderCache
from app.providers.contracts import PriceBar, ProviderProvenance, ProviderResult, TickerIdentity
from app.providers.synthetic import SyntheticOfflineProvider


STAMP = datetime(2025, 12, 31, tzinfo=timezone.utc)
PROVENANCE = ProviderProvenance(
    provider_id="fixture-a", product="test", feed_kind="synthetic",
    retrieved_at=STAMP, as_of=STAMP, permitted_use="prototype_only",
)


def run(awaitable):
    return asyncio.run(awaitable)


def test_provider_contracts_require_timezone_and_consistent_ohlc():
    with pytest.raises(ValueError):
        ProviderProvenance(provider_id="test", product="test", feed_kind="delayed",
                           retrieved_at=datetime(2025, 1, 1))
    with pytest.raises(ValueError):
        PriceBar(time="sample", open=10, high=9, low=8, close=9, volume=1)
    identity = TickerIdentity(symbol="NVDA", name="Fixture", exchange="NASDAQ", identity_status="fixture_only")
    assert identity.identity_status == "fixture_only"


def test_offline_provider_returns_typed_source_and_availability_metadata():
    provider = SyntheticOfflineProvider()
    overview = run(provider.overview())
    assert overview.status == "ok"
    assert overview.provenance.provider_id == "synthetic-offline"
    assert overview.provenance.permitted_use == "prototype_only"
    assert overview.provenance.feed_kind == "synthetic"
    assert len(overview.data.markets) == 4

    search = run(provider.ticker_search("NVDA"))
    assert search.data.results[0].symbol == "NVDA"
    assert search.provenance.source_revision == "91768e574576349466e95faba40ed6440eda921b"

    chart = run(provider.history("NVDA", "1D", "15m"))
    assert chart.data.interval == "15m"
    assert len(chart.data.bars) == 26
    assert "not historical" in chart.data.label


def test_offline_provider_preserves_validation_missing_and_partial_states():
    provider = SyntheticOfflineProvider()
    directory = run(provider.directory("Technology", "Semiconductors", ""))
    assert directory.status == "ok"
    assert [company.symbol for company in directory.data.companies] == ["NVDA"]

    mismatch = run(provider.directory("Healthcare", "Semiconductors", ""))
    assert mismatch.status == "invalid"
    assert mismatch.data is None

    research = run(provider.company_research("AMZN"))
    assert research.status == "partial"
    assert research.missing_fields == ["Dividend yield"]
    assert research.data.fundamentals[-1].display_value == "—"

    news = run(provider.news_events("NVDA"))
    assert {item.sentiment for item in news.data.headlines} == {"Bullish", "Bearish", "Neutral"}


def test_cache_key_is_canonical_and_provider_scoped():
    key1 = ProviderCache.cache_key("provider-a", "history", {"symbol": "NVDA", "period": "1M"})
    key2 = ProviderCache.cache_key("provider-a", "history", {"period": "1M", "symbol": "NVDA"})
    key3 = ProviderCache.cache_key("provider-b", "history", {"symbol": "NVDA", "period": "1M"})
    assert key1 == key2
    assert key1 != key3


def test_cache_invalidation_is_provider_and_request_scoped():
    now = [0.0]
    cache = ProviderCache(CachePolicy(max_entries=5), clock=lambda: now[0])

    async def success(value, provenance=PROVENANCE):
        return ProviderResult[str](data=value, status="ok", provenance=provenance)

    run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, lambda: success("n"), PROVENANCE))
    second_provenance = PROVENANCE.model_copy(update={"provider_id": "fixture-b"})
    run(cache.get_or_load("fixture-b", "quote", {"symbol": "NVDA"}, lambda: success("b", second_provenance), second_provenance))
    assert cache.invalidate("fixture-a", "quote", {"symbol": "NVDA"})
    assert cache.invalidate_provider("fixture-b") == 1
    assert len(cache._entries) == 0


def test_cache_uses_success_and_failure_ttls_and_serves_stale_on_error():
    now = [0.0]
    cache = ProviderCache(CachePolicy(success_ttl_seconds=5, failure_ttl_seconds=2,
                                      stale_if_error_seconds=10, timeout_seconds=1), clock=lambda: now[0])
    calls = [0]

    async def success():
        calls[0] += 1
        return ProviderResult[str](data="latest", status="ok", provenance=PROVENANCE)

    async def failure():
        calls[0] += 1
        return ProviderResult[str](data=None, status="rate_limited", provenance=PROVENANCE,
                                   warnings=["Provider rate limit reached."])

    first = run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, success, PROVENANCE))
    now[0] = 4
    cached = run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, failure, PROVENANCE))
    assert cached.data == "latest" and not cached.stale
    assert calls[0] == 1

    now[0] = 6
    stale = run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, failure, PROVENANCE))
    assert stale.data == "latest" and stale.stale and stale.status == "partial"
    assert "showing the last successful result as stale" in stale.warnings[-1]
    assert calls[0] == 2


def test_cache_short_caches_failures_and_bounds_entries():
    now = [0.0]
    cache = ProviderCache(CachePolicy(success_ttl_seconds=5, failure_ttl_seconds=2,
                                      stale_if_error_seconds=0, max_entries=1, timeout_seconds=1), clock=lambda: now[0])
    calls = [0]

    async def failure():
        calls[0] += 1
        return ProviderResult[str](data=None, status="failed", provenance=PROVENANCE,
                                   warnings=["Unavailable."])

    first = run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, failure, PROVENANCE))
    now[0] = 1
    second = run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, failure, PROVENANCE))
    assert first.status == second.status == "failed"
    assert calls[0] == 1
    cache.cache_key("fixture-a", "quote", {"symbol": "AAPL"})
    # A second distinct fetch evicts the least recently used key when capacity is one.
    run(cache.get_or_load("fixture-a", "quote", {"symbol": "AAPL"}, failure, PROVENANCE))
    assert len(cache._entries) == 1


def test_cache_timeout_returns_safe_failure_result():
    cache = ProviderCache(CachePolicy(timeout_seconds=0.01))

    async def slow():
        await asyncio.sleep(0.05)
        return ProviderResult[str](data="late", status="ok", provenance=PROVENANCE)

    result = run(cache.get_or_load("fixture-a", "quote", {"symbol": "NVDA"}, slow, PROVENANCE))
    assert result.status == "failed"
    assert result.data is None
    assert result.warnings == ["Provider request timed out."]


def test_api_marks_successful_cached_response_stale_after_refresh_failure(monkeypatch):
    from app import main
    from app.providers.cache import CachePolicy, ProviderCache
    from tests.test_api import client

    now = [0.0]
    cache = ProviderCache(CachePolicy(success_ttl_seconds=1, failure_ttl_seconds=1,
                                      stale_if_error_seconds=10, timeout_seconds=1), clock=lambda: now[0])
    monkeypatch.setattr(main, "provider_cache", cache)
    first = client.get("/api/v1/overview")
    assert first.status_code == 200 and first.json()["stale"] is False

    async def fail_refresh():
        return ProviderResult[object](data=None, status="failed", provenance=main.provider._provenance("overview"),
                                      warnings=["Provider data is temporarily unavailable."])

    monkeypatch.setattr(main.provider, "overview", fail_refresh)
    now[0] = 2
    stale = client.get("/api/v1/overview")
    assert stale.status_code == 200
    assert stale.json()["status"] == "partial"
    assert stale.json()["stale"] is True
    assert stale.json()["data"]["markets"]


def test_api_exposes_rate_limit_as_429_with_safe_status(monkeypatch):
    from app import main
    from tests.test_api import client

    main.provider_cache.invalidate("synthetic-offline", "overview", {})

    async def rate_limited():
        return ProviderResult[object](data=None, status="rate_limited", provenance=main.provider._provenance("overview"),
                                      warnings=["Provider request limit reached."])

    monkeypatch.setattr(main.provider, "overview", rate_limited)
    response = client.get("/api/v1/overview")
    assert response.status_code == 429
    assert response.json()["status"] == "rate_limited"
    assert "Provider request limit" in response.json()["warnings"][0]
