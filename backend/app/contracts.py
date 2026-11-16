from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")
ResponseStatus = Literal["ok", "partial", "unavailable", "rate_limited", "failed", "invalid"]
ResponseSource = Literal["synthetic-fixtures", "python-engine-snapshot", "sec-edgar"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApiEnvelope(StrictModel, Generic[T]):
    data: T | None
    status: ResponseStatus
    source: ResponseSource = "synthetic-fixtures"
    freshness: Literal["simulated", "live", "cached"] = "simulated"
    as_of: str | None = None
    provenance: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stale: bool = False


class MarketIndex(StrictModel):
    name: str
    symbol: str
    value: str
    change: str
    tone: Literal["up", "down"]
    series: list[float]


class SectorActivity(StrictModel):
    name: str
    value: int = Field(ge=0, le=100)


class OverviewData(StrictModel):
    markets: list[MarketIndex]
    sector_activity: list[SectorActivity]
    disclosure: str


class TickerSearchItem(StrictModel):
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str


class TickerSearchData(StrictModel):
    query: str
    results: list[TickerSearchItem]


class ChartBar(StrictModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartData(StrictModel):
    symbol: str
    range: Literal["1D", "1W", "1M", "3M", "1Y", "ALL"]
    interval: Literal["15m", "30m", "1h", "2h", "12h", "1d"]
    bars: list[ChartBar]
    label: str


class DiscoveryCompany(StrictModel):
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    price: str
    change: str
    change_tone: Literal["up", "down"]
    series: list[float]
    strength: int = Field(ge=0, le=100)
    range: Literal["1M"] = "1M"
    market_cap: str
    rating: Literal["Positive", "Balanced", "Cautious"]
    classification_label: Literal["simulated classification"] = "simulated classification"


class IndustryItem(StrictModel):
    name: str
    sector: str
    company_count: int = Field(ge=0)


class DiscoveryData(StrictModel):
    sectors: list[str]
    industries: list[IndustryItem]
    companies: list[DiscoveryCompany]
    selected_sector: str | None = None
    selected_industry: str | None = None
    query: str
    disclosure: str


class CalendarItem(StrictModel):
    symbol: str
    name: str
    date_label: str
    title: str
    detail: str


class DiscoveryCalendarData(StrictModel):
    kind: Literal["earnings", "ipos"]
    window_days: int = Field(ge=1, le=180)
    items: list[CalendarItem]
    disclosure: str


class WatchlistSummary(StrictModel):
    symbol: str
    name: str
    sector: str
    industry: str
    sample_close: float | None
    sample_change_percent: float | None
    technical_rating: str
    trend_state: str


class WatchlistSummaryData(StrictModel):
    symbols: list[str]
    summaries: list[WatchlistSummary]
    disclosure: str


class FundamentalMetric(StrictModel):
    label: str
    display_value: str
    raw_value: float | None
    context: str


class QuarterlyFinancialPeriod(StrictModel):
    period: str
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    diluted_eps: float | None = None


class AnalystTargets(StrictModel):
    current: float | None = None
    high: float | None = None
    low: float | None = None
    mean: float | None = None
    median: float | None = None
    upside_percent: float | None = None


class AnalystConsensus(StrictModel):
    rating: str | None = None
    count: int
    score: float | None = None
    period: str | None = None


class RecommendationCount(StrictModel):
    rating: str
    count: int


class EPSRevisionPeriod(StrictModel):
    period: str
    up_last_7days: float | None = None
    up_last_30days: float | None = None
    down_last_7_days: float | None = None
    down_last_30days: float | None = None


class CompanyEvent(StrictModel):
    date_label: str
    title: str
    detail: str


class ResearchData(StrictModel):
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    fundamentals: list[FundamentalMetric]
    quarterly_financials: list[QuarterlyFinancialPeriod]
    analyst_targets: AnalystTargets | None
    analyst_consensus: AnalystConsensus
    recommendation_distribution: list[RecommendationCount]
    eps_revisions: list[EPSRevisionPeriod]
    events: list[CompanyEvent]
    disclosure: str
    as_of: str


class NewsItem(StrictModel):
    title: str
    publisher: str
    published_at: str
    sentiment: Literal["Bullish", "Bearish", "Neutral"]
    confidence: Literal["High", "Medium", "Low"]
    reason: str
    issuer_relevant: bool
    bull_score: float
    bear_score: float
    topic: str


class NewsEventsData(StrictModel):
    symbol: str
    headlines: list[NewsItem]
    events: list[CompanyEvent]
    disclosure: str
    as_of: str


class RatingCheck(StrictModel):
    side: Literal["Constructive", "Caution"]
    label: str
    passed: bool | None


class TechnicalAnalysis(StrictModel):
    symbol: str
    name: str
    indicators: dict[str, float | None]
    move_source: str
    trend_state: str
    rating: str
    rating_source: str
    technical_rating: str
    analyst_rating: str | None
    analyst_count: int
    analyst_score: float | None
    analyst_period: str | None
    constructive_checks: int
    caution_checks: int
    rating_checks_complete: bool
    rating_checks: list[RatingCheck]
    returns: dict[str, dict[str, float | int | None]]
    observations: int
    hist_vol_observations: int
    drawdown_observations: int
    beta_observations: int
    as_of: str
    disclosure: str
