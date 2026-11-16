"""Typed provider boundary shared by offline and future authorized adapters.

Provider values are data with provenance and an explicit permitted-use label;
they are not implicitly suitable for public display or redistribution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.contracts import (
    ChartData,
    DiscoveryCalendarData,
    DiscoveryData,
    NewsEventsData,
    OverviewData,
    ResearchData,
    TechnicalAnalysis,
    TickerSearchData,
    WatchlistSummaryData,
)

ProviderState = Literal["ok", "partial", "unavailable", "rate_limited", "failed", "invalid"]
FeedKind = Literal["synthetic", "delayed", "real_time"]
PermittedUse = Literal["prototype_only", "personal_only", "public_display", "commercial_display", "unknown"]


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProviderProvenance(ProviderModel):
    provider_id: str = Field(min_length=1, max_length=80)
    product: str = Field(min_length=1, max_length=120)
    feed_kind: FeedKind
    retrieved_at: datetime
    as_of: datetime | None = None
    permitted_use: PermittedUse = "unknown"
    license_reference: str | None = None
    source_revision: str | None = None
    calculation: str | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("retrieved_at", "as_of")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime | None):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Provider timestamps must include a timezone.")
        return value


T = TypeVar("T")


class ProviderResult(ProviderModel, Generic[T]):
    data: T | None
    status: ProviderState
    provenance: ProviderProvenance
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    stale: bool = False


class ProviderRequest(ProviderModel):
    timeout_seconds: float = Field(default=3.0, gt=0, le=15)


class TickerIdentity(ProviderModel):
    symbol: str = Field(min_length=1, max_length=10, pattern=r"^[A-Z][A-Z0-9.-]{0,9}$")
    name: str = Field(min_length=1, max_length=160)
    exchange: str = Field(min_length=1, max_length=80)
    sector: str | None = None
    industry: str | None = None
    identity_status: Literal["provider_asserted", "fixture_only", "unverified"] = "unverified"


class PriceBar(ProviderModel):
    time: str = Field(min_length=1, max_length=64)
    open: float = Field(allow_inf_nan=False)
    high: float = Field(allow_inf_nan=False)
    low: float = Field(allow_inf_nan=False)
    close: float = Field(allow_inf_nan=False)
    volume: int = Field(ge=0)

    @model_validator(mode="after")
    def high_low_contain_open_and_close(self):
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close) or self.low > self.high:
            raise ValueError("OHLC values are internally inconsistent.")
        return self


class ProviderMarketData(Protocol):
    """Read-only contract; implementations must not mutate user/account data."""

    provider_id: str

    async def overview(self) -> ProviderResult[OverviewData]: ...
    async def ticker_search(self, query: str) -> ProviderResult[TickerSearchData]: ...
    async def history(self, symbol: str, period: str, interval: str) -> ProviderResult[ChartData]: ...
    async def technical_analysis(self, symbol: str) -> ProviderResult[TechnicalAnalysis]: ...
    async def directory(self, sector: str | None, industry: str | None, query: str) -> ProviderResult[DiscoveryData]: ...
    async def calendar(self, kind: str, window_days: int) -> ProviderResult[DiscoveryCalendarData]: ...
    async def company_research(self, symbol: str) -> ProviderResult[ResearchData]: ...
    async def news_events(self, symbol: str) -> ProviderResult[NewsEventsData]: ...
    async def watchlist_summaries(self, symbols: str) -> ProviderResult[WatchlistSummaryData]: ...
