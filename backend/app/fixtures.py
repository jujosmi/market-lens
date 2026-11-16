"""Deterministic synthetic fixtures. No provider or network access occurs here."""

from __future__ import annotations

import math

from .contracts import (
    ChartBar,
    CalendarItem,
    DiscoveryCompany,
    IndustryItem,
    MarketIndex,
    SectorActivity,
    TickerSearchItem,
)

DISCLOSURE = "Synthetic demonstration data only; not live, verified, or an investment recommendation."
CALENDAR_DISCLOSURE = "Synthetic calendar fixtures only. Dates are illustrative and are not actual upcoming earnings or IPO announcements."

EARNINGS_CALENDAR = [
    CalendarItem(symbol="NVDA", name="NVIDIA Corporation", date_label="Fixture · 2025-12-31", title="Sample earnings call", detail="Synthetic event used to exercise the earnings calendar view."),
    CalendarItem(symbol="AMZN", name="Amazon.com, Inc.", date_label="Fixture · 2025-12-31", title="Sample earnings release", detail="Synthetic event; no published calendar is connected."),
    CalendarItem(symbol="AAPL", name="Apple Inc.", date_label="Unscheduled fixture", title="Sample earnings event", detail="Illustrative calendar entry only."),
]

IPO_CALENDAR = [
    CalendarItem(symbol="SAMPLE1", name="Example issuer", date_label="Fixture · 2025-12-31", title="Illustrative public listing", detail="Synthetic placeholder; no real offering or listing is represented."),
    CalendarItem(symbol="SAMPLE2", name="Demonstration company", date_label="Unscheduled fixture", title="Example technology offering", detail="No live IPO calendar is connected."),
]

MARKETS = [
    MarketIndex(name="S&P 500", symbol="SPX", value="5,842.47", change="+0.38%", tone="up", series=[18, 22, 20, 28, 25, 33, 30, 38, 36, 43, 40, 46]),
    MarketIndex(name="NASDAQ 100", symbol="NDX", value="20,271.88", change="+0.61%", tone="up", series=[16, 20, 19, 27, 25, 34, 31, 40, 38, 46, 43, 52]),
    MarketIndex(name="DOW JONES", symbol="DJI", value="42,215.80", change="−0.14%", tone="down", series=[42, 39, 44, 37, 40, 33, 36, 28, 32, 24, 27, 20]),
    MarketIndex(name="VIX", symbol="VOLATILITY", value="17.36", change="−2.1%", tone="up", series=[32, 30, 35, 29, 27, 31, 25, 23, 27, 20, 18, 16]),
]

SECTOR_ACTIVITY = [
    SectorActivity(name="Technology", value=82),
    SectorActivity(name="Industrials", value=67),
    SectorActivity(name="Healthcare", value=58),
    SectorActivity(name="Financials", value=44),
]

TICKERS = [
    TickerSearchItem(symbol="NVDA", name="NVIDIA Corporation", exchange="NASDAQ", sector="Technology", industry="Semiconductors"),
    TickerSearchItem(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", sector="Technology", industry="Consumer Electronics"),
    TickerSearchItem(symbol="MSFT", name="Microsoft Corporation", exchange="NASDAQ", sector="Technology", industry="Software Infrastructure"),
    TickerSearchItem(symbol="AMZN", name="Amazon.com, Inc.", exchange="NASDAQ", sector="Consumer Cyclical", industry="Internet Retail"),
    TickerSearchItem(symbol="GOOGL", name="Alphabet Inc.", exchange="NASDAQ", sector="Communication Services", industry="Internet Content & Information"),
    TickerSearchItem(symbol="JPM", name="JPMorgan Chase & Co.", exchange="NYSE", sector="Financial Services", industry="Credit Services"),
    TickerSearchItem(symbol="LLY", name="Eli Lilly and Company", exchange="NYSE", sector="Healthcare", industry="Drug Manufacturers"),
]

_DISCOVERY_NUMBERS = {
    "NVDA": ("142.68", "+1.84%", "up", 72, "$3.4T", "Positive", [30, 33, 29, 37, 34, 40, 38, 45, 41, 49, 45, 54, 51, 58, 55, 65, 61, 70, 67, 76, 73, 81, 77, 86]),
    "AAPL": ("231.44", "+0.62%", "up", 64, "$3.5T", "Balanced", [40, 43, 39, 42, 46, 43, 48, 45, 50, 49, 54, 51, 55, 53, 58, 57, 60, 58, 64, 61, 66, 65, 70, 73]),
    "MSFT": ("512.24", "−0.28%", "down", 48, "$3.8T", "Cautious", [70, 67, 72, 69, 64, 68, 62, 65, 59, 62, 56, 58, 53, 57, 51, 54, 49, 52, 46, 49, 44, 47, 42, 45]),
    "AMZN": ("218.90", "+1.11%", "up", 68, "$2.3T", "Positive", [32, 35, 33, 38, 36, 39, 37, 45, 42, 47, 44, 50, 47, 53, 50, 56, 53, 60, 57, 65, 62, 68, 64, 74]),
    "GOOGL": ("176.42", "+0.43%", "up", 61, "$2.1T", "Balanced", [35, 38, 36, 41, 39, 43, 40, 46, 44, 49, 47, 52, 49, 55, 53, 58, 56, 63, 60, 67, 63, 70, 68, 73]),
    "JPM": ("284.16", "−0.21%", "down", 57, "$806B", "Balanced", [68, 64, 70, 67, 63, 66, 61, 65, 59, 62, 57, 60, 55, 59, 53, 56, 51, 55, 48, 52, 45, 49, 43, 46]),
    "LLY": ("812.30", "+0.86%", "up", 74, "$771B", "Positive", [26, 29, 27, 34, 31, 38, 35, 42, 39, 46, 43, 51, 48, 55, 51, 59, 56, 63, 60, 68, 64, 71, 68, 76]),
}

COMPANIES = [
    DiscoveryCompany(symbol=t.symbol, name=t.name, exchange=t.exchange, sector=t.sector, industry=t.industry,
        price=_DISCOVERY_NUMBERS[t.symbol][0], change=_DISCOVERY_NUMBERS[t.symbol][1],
        change_tone=_DISCOVERY_NUMBERS[t.symbol][2], strength=_DISCOVERY_NUMBERS[t.symbol][3],
        market_cap=_DISCOVERY_NUMBERS[t.symbol][4], rating=_DISCOVERY_NUMBERS[t.symbol][5],
        series=_DISCOVERY_NUMBERS[t.symbol][6])
    for t in TICKERS
]

SECTORS = list(dict.fromkeys(t.sector for t in TICKERS))
INDUSTRIES = [IndustryItem(name=industry, sector=sector,
    company_count=sum(c.sector == sector and c.industry == industry for c in COMPANIES))
    for sector, industry in dict.fromkeys((t.sector, t.industry) for t in TICKERS)]

def chart_bars(symbol: str, bar_range: str) -> list[ChartBar]:
    """Build stable normalized demonstration bars, not market history."""
    count = 24 if bar_range == "1D" else 30
    seed = sum(ord(char) for char in symbol)
    center = 80.0 + seed % 190
    bars = []
    for index in range(count):
        close = center + math.sin((index + seed) * 0.7) * center * 0.035 + index * center * 0.001
        open_value = close - math.cos((index + seed) * 0.6) * center * 0.009
        spread = center * (0.004 + (index % 4) * 0.001)
        bars.append(ChartBar(time=f"T+{index + 1:02d}", open=round(open_value, 2), high=round(max(open_value, close) + spread, 2), low=round(min(open_value, close) - spread, 2), close=round(close, 2), volume=100_000 + ((seed * 137 + index * 4_321) % 900_000)))
    return bars
