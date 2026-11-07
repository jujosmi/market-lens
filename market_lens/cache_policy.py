"""Targeted cache invalidation policy for the dashboard's refresh controls."""

from __future__ import annotations


CHART_INTERVALS = ("15 minute", "30 minute", "1 hour", "2 hours", "12 hours", "1 day")


def selected_ticker_cache_entries(symbol: str) -> tuple[tuple[str, tuple], ...]:
    """Return only cache keys owned by one ticker's snapshot, research, and chart."""
    ticker = str(symbol).strip().upper()
    if not ticker:
        return ()
    entries = [
        ("load_market_data", (ticker,)),
        ("load_ticker_news", (ticker,)),
        ("load_company_fundamentals", (ticker,)),
        ("load_company_catalysts", (ticker,)),
        ("load_snapshot", (ticker,)),
        ("load_profile", (ticker,)),
        ("load_analyst_recommendations", (ticker,)),
        ("load_analyst_recommendation_result", (ticker,)),
    ]
    entries.extend(("load_chart_history", (ticker, interval)) for interval in CHART_INTERVALS)
    return tuple(entries)


def clear_selected_ticker_caches(symbol: str, cached_functions: dict) -> None:
    """Invalidate only the selected ticker's entries using CachedFunc.clear."""
    for function_name, args in selected_ticker_cache_entries(symbol):
        cached_functions[function_name].clear(*args)
