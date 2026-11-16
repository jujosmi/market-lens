"""Offline-only implementation of the typed provider interface."""

from __future__ import annotations

from datetime import datetime, timezone

from app import engine_adapter, engine_fixtures, fixtures
from app.contracts import (
    ChartData, DiscoveryCalendarData, DiscoveryData,
    IndustryItem, NewsEventsData, OverviewData, ResearchData, TechnicalAnalysis,
    TickerSearchData, WatchlistSummary, WatchlistSummaryData,
)
from .contracts import ProviderProvenance, ProviderResult, ProviderState
from .contracts import PriceBar, TickerIdentity


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class SyntheticOfflineProvider:
    """Deterministic adapter; this class contains no HTTP client or provider SDK."""

    provider_id = "synthetic-offline"

    def _provenance(self, product: str, *, source: str = "synthetic-fixtures", calculation: str | None = None) -> ProviderProvenance:
        stamp = _date(engine_fixtures.AS_OF)
        return ProviderProvenance(
            provider_id=self.provider_id,
            product=product,
            feed_kind="synthetic",
            retrieved_at=stamp,
            as_of=stamp,
            permitted_use="prototype_only",
            source_revision=engine_adapter.ENGINE_COMMIT if source == "python-engine-snapshot" else None,
            calculation=calculation,
            notes=["Deterministic offline fixture; not current provider data."],
        )

    @staticmethod
    def _result(data, product: str, *, status: ProviderState = "ok", warnings: list[str] | None = None,
                missing_fields: list[str] | None = None, source: str = "synthetic-fixtures",
                calculation: str | None = None):
        provider = SyntheticOfflineProvider()
        return ProviderResult(data=data, status=status, provenance=provider._provenance(product, source=source, calculation=calculation),
                              warnings=warnings or [], missing_fields=missing_fields or [])

    async def overview(self) -> ProviderResult[OverviewData]:
        data = OverviewData(markets=fixtures.MARKETS, sector_activity=fixtures.SECTOR_ACTIVITY, disclosure=fixtures.DISCLOSURE)
        return self._result(data, "market overview", source="synthetic-fixtures")

    async def ticker_search(self, query: str) -> ProviderResult[TickerSearchData]:
        query = query.strip()
        rows = engine_adapter.search_tickers(query.casefold())
        # Validate identity at the provider boundary; synthetic identities remain
        # explicitly tagged as fixtures and are not asserted as real-world facts.
        for row in rows:
            TickerIdentity(**row.model_dump(), identity_status="fixture_only")
        data = TickerSearchData(query=query, results=rows)
        status: ProviderState = "ok" if rows else "unavailable"
        warnings = [] if rows else ["No synthetic ticker fixtures matched the query."]
        return self._result(data, "ticker search", status=status, warnings=warnings, source="python-engine-snapshot",
                            calculation=f"market_lens.discovery.industry_identity@{engine_adapter.ENGINE_COMMIT}")

    async def history(self, symbol: str, period: str, interval: str) -> ProviderResult[ChartData]:
        if not any(item.symbol == symbol for item in fixtures.TICKERS):
            return self._result(None, "historical prices", status="unavailable",
                                warnings=["No synthetic chart fixture is available for this ticker."], source="python-engine-snapshot")
        bars = [PriceBar(**bar).model_dump() for bar in engine_adapter.chart_data(symbol, period, interval)]
        label = "Python engine sample series · synthetic interpolation, not historical market data"
        return self._result(ChartData(symbol=symbol, range=period, interval=interval, bars=bars, label=label),
                            "historical prices", source="python-engine-snapshot",
                            calculation=f"market_lens.analytics.close_series@{engine_adapter.ENGINE_COMMIT}")

    async def technical_analysis(self, symbol: str) -> ProviderResult[TechnicalAnalysis]:
        try:
            data = TechnicalAnalysis(**engine_adapter.technical_analysis(symbol))
        except KeyError:
            return self._result(None, "technical analysis", status="unavailable",
                                warnings=["No Python engine fixture is available for this ticker."], source="python-engine-snapshot")
        return self._result(data, "technical analysis", source="python-engine-snapshot",
                            calculation=f"market_lens.analytics.analyze@{engine_adapter.ENGINE_COMMIT}")

    async def directory(self, sector: str | None, industry: str | None, query: str) -> ProviderResult[DiscoveryData]:
        rows, industries, sectors, warning = engine_adapter.validated_discovery(sector, industry, query)
        if warning and (warning.startswith("The requested") or "canonical key" in warning):
            return self._result(None, "company directory", status="invalid",
                                warnings=["Selected filters are not available in the synthetic directory."], source="python-engine-snapshot")
        symbols = {row["symbol"] for row in rows}
        companies = [item for item in fixtures.COMPANIES if item.symbol in symbols]
        industry_items = [IndustryItem(**item) for item in industries]
        status: ProviderState = "partial" if warning and companies else "unavailable" if not companies else "ok"
        warnings = [warning] if warning else ["No synthetic company fixtures matched the validated filters."] if not companies else []
        data = DiscoveryData(sectors=sectors, industries=industry_items, companies=companies,
                             selected_sector=sector, selected_industry=industry, query=query,
                             disclosure=engine_fixtures.DISCLOSURE)
        return self._result(data, "company directory", status=status, warnings=warnings, source="python-engine-snapshot",
                            calculation=f"market_lens.discovery.fetch_industry_companies@{engine_adapter.ENGINE_COMMIT}; injected local fixtures only")

    async def calendar(self, kind: str, window_days: int) -> ProviderResult[DiscoveryCalendarData]:
        items = fixtures.EARNINGS_CALENDAR if kind == "earnings" else fixtures.IPO_CALENDAR
        data = DiscoveryCalendarData(kind=kind, window_days=window_days, items=items,
                                     disclosure=fixtures.CALENDAR_DISCLOSURE)
        return self._result(data, "corporate calendar", warnings=[fixtures.CALENDAR_DISCLOSURE], source="synthetic-fixtures")

    async def company_research(self, symbol: str) -> ProviderResult[ResearchData]:
        try:
            result, missing = engine_adapter.normalized_research(symbol)
            data = ResearchData(**result)
        except KeyError:
            return self._result(None, "company research", status="unavailable",
                                warnings=["No synthetic research fixture is available for this ticker."], source="python-engine-snapshot")
        warnings = [f"Unavailable fixture fields: {', '.join(missing)}"] if missing else []
        return self._result(data, "company research", status="partial" if missing else "ok",
                            warnings=warnings, missing_fields=missing, source="python-engine-snapshot",
                            calculation=f"market_lens.research and market_lens.analytics.analyst_consensus@{engine_adapter.ENGINE_COMMIT}")

    async def news_events(self, symbol: str) -> ProviderResult[NewsEventsData]:
        try:
            data = NewsEventsData(**engine_adapter.classified_news(symbol))
        except KeyError:
            return self._result(None, "company news and events", status="unavailable",
                                warnings=["No synthetic news or event fixture is available for this ticker."], source="python-engine-snapshot")
        return self._result(data, "company news and events", source="python-engine-snapshot",
                            calculation=f"market_lens.news.classify_headline and classify_news_topic@{engine_adapter.ENGINE_COMMIT}")

    async def watchlist_summaries(self, symbols: str) -> ProviderResult[WatchlistSummaryData]:
        requested = list(dict.fromkeys(part.strip().upper() for part in symbols.split(",") if part.strip()))
        known = {item.symbol: item for item in fixtures.TICKERS}
        summaries = []
        missing = []
        for symbol in requested:
            ticker = known.get(symbol)
            try:
                analysis = engine_adapter.technical_analysis(symbol) if ticker else None
            except KeyError:
                analysis = None
            if not ticker or analysis is None:
                missing.append(symbol)
                continue
            indicators = analysis["indicators"]
            summaries.append(WatchlistSummary(
                symbol=symbol, name=ticker.name, sector=ticker.sector, industry=ticker.industry,
                sample_close=indicators.get("last"), sample_change_percent=indicators.get("change"),
                technical_rating=analysis["technical_rating"], trend_state=analysis["trend_state"],
            ))
        if not summaries:
            return self._result(None, "watchlist summaries", status="unavailable",
                                warnings=["No supported synthetic watchlist summaries were found."], source="python-engine-snapshot")
        data = WatchlistSummaryData(symbols=requested, summaries=summaries, disclosure=engine_fixtures.DISCLOSURE)
        return self._result(data, "watchlist summaries", status="partial" if missing else "ok",
                            warnings=[f"No synthetic summary is available for: {', '.join(missing)}."] if missing else [],
                            source="python-engine-snapshot",
                            calculation=f"market_lens.analytics.analyze@{engine_adapter.ENGINE_COMMIT}")
