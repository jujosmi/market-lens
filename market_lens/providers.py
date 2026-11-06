"""Market-data provider boundary and source/freshness metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from .config import DATA_PROVIDER_NAME


@dataclass
class DataEnvelope:
    """A provider response plus enough metadata to describe its quality."""

    data: pd.DataFrame
    source: str
    retrieved_at: datetime
    interval: str
    status: str
    last_observation: str | None = None
    provider_delay: str = "unknown"
    warning: str | None = None


class MarketDataProvider:
    """Small interface used by the UI; alternate providers can implement it."""

    def history(self, symbol: str, period: str = "2y", interval: str = "1d") -> DataEnvelope:
        raise NotImplementedError

    def histories(self, symbols: list[str], period: str = "2y", interval: str = "1d") -> dict[str, DataEnvelope]:
        raise NotImplementedError


class YahooFinanceProvider(MarketDataProvider):
    """Read-only Yahoo Finance adapter. It cannot verify quote-delivery delay."""

    @staticmethod
    def _envelope(data: pd.DataFrame, interval: str, retrieved_at: datetime,
                  warning: str | None = None) -> DataEnvelope:
        if not isinstance(data, pd.DataFrame) or data.empty or "Close" not in data.columns:
            return DataEnvelope(pd.DataFrame(), DATA_PROVIDER_NAME, retrieved_at, interval,
                                "missing", warning=warning or "Provider returned no usable price history.")
        original_rows = len(data)
        cleaned = data.dropna(subset=["Close"]).sort_index()
        if cleaned.empty:
            return DataEnvelope(pd.DataFrame(), DATA_PROVIDER_NAME, retrieved_at, interval,
                                "missing", warning="Price history contained no valid closes.")
        last = pd.Timestamp(cleaned.index[-1])
        last_observation = last.isoformat()
        if last.tzinfo is None:
            last = last.tz_localize("UTC")
        age_days = (pd.Timestamp(retrieved_at) - last.tz_convert("UTC")).total_seconds() / 86400
        status = "stale" if age_days > 5 else "partial" if original_rows != len(cleaned) else "recent"
        if status == "stale":
            warning = warning or f"Latest price observation is {age_days:.1f} days old."
        elif status == "partial":
            excluded_rows = original_rows - len(cleaned)
            warning = warning or f"{excluded_rows} of {original_rows} returned price rows had no closing price and were omitted."
        return DataEnvelope(cleaned, DATA_PROVIDER_NAME, retrieved_at, interval, status,
                            last_observation, "unknown", warning)

    def history(self, symbol: str, period: str = "2y", interval: str = "1d") -> DataEnvelope:
        retrieved_at = datetime.now(timezone.utc)
        try:
            frame = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
            warning = None if not frame.empty else f"No price history returned for {symbol}; the symbol may be invalid or not covered."
            return self._envelope(frame, interval, retrieved_at, warning)
        except Exception as exc:
            return DataEnvelope(pd.DataFrame(), DATA_PROVIDER_NAME, retrieved_at, interval, "failed",
                                warning=f"Price provider failed for {symbol}: {type(exc).__name__}: {exc}")

    def histories(self, symbols: list[str], period: str = "2y", interval: str = "1d") -> dict[str, DataEnvelope]:
        retrieved_at = datetime.now(timezone.utc)
        try:
            downloaded = yf.download(symbols, period=period, interval=interval, auto_adjust=True,
                                     group_by="ticker", progress=False, threads=True)
        except Exception as exc:
            downloaded = pd.DataFrame()
            download_warning = f"Bulk history request failed ({type(exc).__name__}); individual requests were attempted."
        else:
            download_warning = None
        results = {}
        for symbol in symbols:
            try:
                frame = downloaded[symbol] if not downloaded.empty else pd.DataFrame()
                if frame.empty or "Close" not in frame:
                    results[symbol] = self.history(symbol, period, interval)
                else:
                    results[symbol] = self._envelope(frame, interval, retrieved_at, download_warning)
            except Exception as exc:
                results[symbol] = DataEnvelope(pd.DataFrame(), DATA_PROVIDER_NAME, retrieved_at,
                                               interval, "failed",
                                               warning=f"Could not normalize {symbol} history: {type(exc).__name__}: {exc}")
        return results
