"""Deterministic, provider-shaped inputs for exercising the source engine offline."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .fixtures import TICKERS

AS_OF = "2025-12-31T00:00:00+00:00"
DISCLOSURE = (
    "Synthetic test input processed by the existing Jujosmi Trade Python functions. "
    "This is not live market data, verified company research, or investment advice."
)

_BASE = {"NVDA": 142.68, "AAPL": 231.44, "MSFT": 512.24, "AMZN": 218.90, "GOOGL": 176.42, "JPM": 284.16, "LLY": 812.30}
_CAP = {"NVDA": 3.4e12, "AAPL": 3.5e12, "MSFT": 3.8e12, "AMZN": 2.3e12, "GOOGL": 2.1e12, "JPM": 806e9, "LLY": 771e9}


def profile(symbol: str) -> dict:
    base = _BASE[symbol]
    return {
        "marketCap": _CAP[symbol], "trailingPE": 38.4, "forwardPE": 31.8,
        "pegRatio": 1.42, "priceToSalesTrailing12Months": 14.2,
        "enterpriseToEbitda": 27.5, "revenueGrowth": 0.126,
        "profitMargins": 0.356, "operatingMargins": 0.452,
        "returnOnEquity": 0.318, "debtToEquity": 41.2,
        "currentRatio": 2.14, "freeCashflow": 72.4e9,
        "dividendYield": None, "shortName": next(item.name for item in TICKERS if item.symbol == symbol),
        "sampleBase": base,
    }


def price_history(symbol: str) -> pd.DataFrame:
    """Produce 320 deterministic daily observations with a nonconstant path."""
    index = pd.bdate_range(end="2025-12-31", periods=320, tz="UTC")
    base = _BASE[symbol]
    offset = sum(map(ord, symbol)) % 13
    closes = [base * (0.62 + 0.00115 * i + 0.027 * math.sin((i + offset) / 8.0) + 0.012 * math.cos((i + offset) / 17.0)) for i in range(len(index))]
    volumes = [850_000 + ((i * 7919 + offset * 101) % 1_400_000) for i in range(len(index))]
    return pd.DataFrame({"Close": closes, "Volume": volumes}, index=index)


def benchmark_history() -> pd.DataFrame:
    index = pd.bdate_range(end="2025-12-31", periods=320, tz="UTC")
    closes = [400.0 * (0.91 + 0.00044 * i + 0.014 * math.sin(i / 13.0) + 0.006 * math.cos(i / 29.0)) for i in range(len(index))]
    return pd.DataFrame({"Close": closes}, index=index)


def quarterly_statement(symbol: str) -> pd.DataFrame:
    scale = _CAP[symbol] / _CAP["NVDA"]
    columns = pd.to_datetime(["2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"])
    return pd.DataFrame(
        [
            [124.3e9 * scale, 118.6e9 * scale, 110.5e9 * scale, 105.2e9 * scale],
            [42.1e9 * scale, 41.6e9 * scale, 39.8e9 * scale, 36.9e9 * scale],
            [30.8e9 * scale, 26.9e9 * scale, 23.1e9 * scale, 21.4e9 * scale],
            [1.23, 1.08, 0.92, 0.84],
        ],
        index=["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"],
        columns=columns,
    )


def recommendations(symbol: str) -> pd.DataFrame:
    offsets = sum(map(ord, symbol)) % 4
    return pd.DataFrame([{"period": "0m", "strongBuy": 4 + offsets, "buy": 8, "hold": 5, "sell": 2, "strongSell": 1}])


def analyst_targets(symbol: str) -> dict[str, float]:
    base = _BASE[symbol]
    return {"current": base, "high": base * 1.35, "low": base * 0.78, "mean": base * 1.12, "median": base * 1.08}


def eps_revisions(symbol: str) -> pd.DataFrame:
    strength = sum(map(ord, symbol)) % 5
    return pd.DataFrame(
        {"upLast7days": [1 + strength, 2, 1, 3], "upLast30days": [4 + strength, 5, 2, 6],
         "downLast7Days": [0, 1, 1, 0], "downLast30days": [1, 2, 2, 1]},
        index=["0q", "+1q", "0y", "+1y"],
    )


def news_items(symbol: str) -> list[dict[str, str]]:
    company = next(item.name for item in TICKERS if item.symbol == symbol)
    return [
        {"title": f"{company} synthetic fixture beats earnings estimates and revenue grows", "publisher": "Local test fixture", "published_at": AS_OF},
        {"title": f"{company} synthetic fixture cuts guidance and misses earnings estimates", "publisher": "Local test fixture", "published_at": AS_OF},
        {"title": f"{company} synthetic company profile fixture receives a routine update", "publisher": "Local test fixture", "published_at": AS_OF},
    ]


def event_items(symbol: str) -> list[dict[str, str]]:
    return [
        {"date_label": "Fixture date · 2025-12-31", "title": "Sample earnings event", "detail": f"Synthetic event fixture for {symbol}; not a published calendar."},
        {"date_label": "Unscheduled fixture", "title": "Sample company event", "detail": "No provider calendar is connected."},
    ]


def company_rows() -> list[dict[str, str]]:
    """Return directory identities already present in the demo fixtures."""
    return [{"symbol": item.symbol, "name": item.name, "exchange": item.exchange, "sector": item.sector, "industry": item.industry} for item in TICKERS]
