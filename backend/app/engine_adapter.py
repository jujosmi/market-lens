"""Adapters that call the commit-pinned, request-independent Jujosmi Trade functions."""

from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pandas as pd

from engine_snapshot import analytics, discovery, news, research
from . import engine_fixtures, fixtures

ENGINE_COMMIT = "91768e574576349466e95faba40ed6440eda921b"
ENGINE_SOURCE = "market_lens pure-function snapshot"


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _company(symbol: str):
    return next((item for item in fixtures.TICKERS if item.symbol == symbol), None)


def search_tickers(query: str):
    terms = query.strip().casefold()
    return [item for item in fixtures.TICKERS
            if terms in f"{item.symbol} {item.name} {item.sector} {item.industry}".casefold()][:12]


def technical_analysis(symbol: str) -> dict:
    company = _company(symbol)
    if company is None:
        raise KeyError(symbol)
    history = engine_fixtures.price_history(symbol)
    benchmark = engine_fixtures.benchmark_history()
    result = analytics.analyze(
        history,
        info=engine_fixtures.profile(symbol),
        benchmark=benchmark,
        recommendations=engine_fixtures.recommendations(symbol),
    )
    returns = {
        period: {key: (_finite(value) if key != "observations" else int(value)) for key, value in values.items()}
        for period, values in result["returns"].items()
    }
    indicators = {
        key: _finite(result[key]) for key in (
            "last", "change", "move", "hist_vol", "sma20", "sma50", "sma200", "rsi",
            "macd", "macd_signal", "drawdown", "current_drawdown", "high52", "low52",
            "relative_volume", "beta",
        )
    }
    return {
        "symbol": symbol, "name": company.name, "indicators": indicators,
        "move_source": result["move_source"], "trend_state": result["state"],
        "rating": result["rating"], "rating_source": result["rating_source"],
        "technical_rating": result["technical_rating"], "analyst_rating": result["analyst_rating"],
        "analyst_count": int(result["analyst_count"]), "analyst_score": _finite(result["analyst_score"]),
        "analyst_period": result["analyst_period"], "constructive_checks": int(result["constructive_checks"]),
        "caution_checks": int(result["caution_checks"]), "rating_checks_complete": bool(result["rating_checks_complete"]),
        "rating_checks": result["rating_check_details"], "returns": returns,
        "observations": int(result["observations"]), "hist_vol_observations": int(result["hist_vol_observations"]),
        "drawdown_observations": int(result["drawdown_observations"]), "beta_observations": int(result["beta_observations"]),
        "as_of": engine_fixtures.AS_OF, "disclosure": engine_fixtures.DISCLOSURE,
    }


def chart_data(symbol: str, period: str, interval: str = "1d") -> list[dict]:
    """Normalize synthetic history through the existing close_series function.

    Subdaily bars are deterministic interpolation of the synthetic close path;
    they are display fixtures, not provider history or exchange-session data.
    """
    history = engine_fixtures.price_history(symbol)
    close = analytics.close_series(history)
    sessions = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "1Y": 252, "ALL": len(close)}[period]
    bars_per_session = {"15m": 26, "30m": 13, "1h": 7, "2h": 4, "12h": 1, "1d": 1}[interval]
    count = min(500, sessions * bars_per_session)
    daily_values = close.tail(min(sessions, len(close))).tolist()
    if interval != "1d" or period == "1D":
        # Expand deterministic daily values by interpolation, retaining bounded output.
        if not daily_values:
            return []
        values = [
            daily_values[min(int(index * len(daily_values) / count), len(daily_values) - 1)]
            for index in range(count)
        ]
        # Add a smooth, symbol-seeded intraday perturbation so samples are not flat.
        seed = sum(map(ord, symbol))
        values = [value * (1 + 0.0016 * math.sin((i + seed) / 2.7) + 0.0005 * math.cos((i + seed) / 1.8))
                  for i, value in enumerate(values)]
    else:
        values = daily_values
    bars = []
    previous = values[0]
    for idx, value in enumerate(values):
        spread = max(value * 0.004, 0.01)
        open_value = previous + math.sin(idx + len(symbol)) * spread * 0.25
        stamp = f"SAMPLE+{idx + 1:03d} · {interval}" if interval != "1d" or period == "1D" else close.tail(count).index[idx].strftime("%Y-%m-%d")
        bars.append({"time": stamp, "open": round(open_value, 4), "high": round(max(open_value, value) + spread, 4),
                     "low": round(min(open_value, value) - spread, 4), "close": round(value, 4),
                     "volume": 700_000 + ((idx * 7919 + sum(map(ord, symbol)) * 137) % 1_100_000)})
        previous = value
    return bars


def normalized_research(symbol: str) -> tuple[dict, list[str]]:
    company = _company(symbol)
    if company is None:
        raise KeyError(symbol)
    profile = engine_fixtures.profile(symbol)
    metric_table = research.fundamentals_metric_table(profile)
    fundamentals = []
    missing = []
    for _, row in metric_table.iterrows():
        label = str(row["Metric"])
        display = str(row["Latest value"])
        fundamentals.append({"label": label, "display_value": display,
                             "raw_value": None if display == "—" else _raw_metric(label, profile),
                             "context": "synthetic provider-shaped input; normalized by market_lens.research"})
        if display == "—":
            missing.append(label)

    statement = research.quarterly_statement_table(engine_fixtures.quarterly_statement(symbol))
    quarterly_fields = {
        "Revenue ($B)": "revenue", "Operating income ($B)": "operating_income",
        "Net income ($B)": "net_income", "Diluted EPS": "diluted_eps",
    }
    quarterly = []
    for period, row in statement.iterrows():
        quarterly.append({"period": str(period), **{quarterly_fields[str(name)]: _finite(value) for name, value in row.items() if str(name) in quarterly_fields}})
    targets = research.analyst_target_summary(engine_fixtures.analyst_targets(symbol), engine_fixtures.profile(symbol)["sampleBase"])
    recommendations = research.recommendation_distribution(engine_fixtures.recommendations(symbol))
    revisions = research.eps_revision_table(engine_fixtures.eps_revisions(symbol))
    consensus = analytics.analyst_consensus(engine_fixtures.recommendations(symbol))
    recommendation_rows = [] if recommendations is None else [
        {"rating": str(row["Rating"]), "count": int(row["Analyst count"])} for _, row in recommendations.iterrows()
    ]
    revision_fields = {
        "Up last 7 days": "up_last_7days", "Up last 30 days": "up_last_30days",
        "Down last 7 days": "down_last_7_days", "Down last 30 days": "down_last_30days",
    }
    revision_rows = [] if revisions is None else [
        {"period": str(index), **{revision_fields[str(key)]: _finite(value) for key, value in row.items() if str(key) in revision_fields}}
        for index, row in revisions.iterrows()
    ]
    result = {
        "symbol": symbol, "name": company.name, "exchange": company.exchange,
        "sector": company.sector, "industry": company.industry,
        "fundamentals": fundamentals, "quarterly_financials": quarterly,
        "analyst_targets": targets,
        "analyst_consensus": {"rating": consensus["rating"], "count": int(consensus["count"]),
                              "score": _finite(consensus["score"]), "period": consensus["period"]},
        "recommendation_distribution": recommendation_rows, "eps_revisions": revision_rows,
        "events": engine_fixtures.event_items(symbol), "disclosure": engine_fixtures.DISCLOSURE,
        "as_of": engine_fixtures.AS_OF,
    }
    return result, missing


def _raw_metric(label: str, profile: dict):
    key_by_label = {label: key for label, key, _ in research.FUNDAMENTAL_FIELDS}
    return _finite(profile.get(key_by_label.get(label, "")))


def classified_news(symbol: str) -> dict:
    company = _company(symbol)
    if company is None:
        raise KeyError(symbol)
    headlines = []
    for item in engine_fixtures.news_items(symbol):
        classification = news.classify_headline(item["title"], symbol=symbol, company_name=company.name)
        headlines.append({
            **item, "sentiment": classification["label"], "confidence": classification["confidence"],
            "reason": classification["reason"], "issuer_relevant": bool(classification["issuer_relevant"]),
            "bull_score": float(classification["bull_score"]), "bear_score": float(classification["bear_score"]),
            "topic": news.classify_news_topic(item["title"]),
        })
    return {"symbol": symbol, "headlines": headlines, "events": engine_fixtures.event_items(symbol),
            "disclosure": engine_fixtures.DISCLOSURE, "as_of": engine_fixtures.AS_OF}


def validated_discovery(sector: str | None, industry: str | None, query: str) -> tuple[list[dict], list[dict], list[str], str | None]:
    """Exercise the original identity gate with offline fake provider objects."""
    directory = engine_fixtures.company_rows()
    sectors = list(dict.fromkeys(row["sector"] for row in directory))
    if sector and not any(discovery.industry_identity(sector) == discovery.industry_identity(value) for value in sectors):
        return [], [], sectors, "The requested sector does not exist in the synthetic directory."
    sector_value = next((value for value in sectors if sector and discovery.industry_identity(value) == discovery.industry_identity(sector)), None)
    available_industries = list(dict.fromkeys(row["industry"] for row in directory if not sector_value or row["sector"] == sector_value))
    if industry and not any(discovery.industry_identity(industry) == discovery.industry_identity(value) for value in available_industries):
        return [], [], sectors, "The requested industry is not listed under the selected synthetic sector."
    industry_value = next((value for value in available_industries if industry and discovery.industry_identity(value) == discovery.industry_identity(industry)), None)
    industry_keys = {name: name.casefold().replace("& ", "").replace("- ", "").replace(", ", " ").replace(" ", "-") for name in available_industries}
    if industry_value:
        key = discovery.canonical_key_for_industry_name(industry_value, tuple(industry_keys.values()))
        if key is None:
            return [], [], sectors, "The selected synthetic industry has no canonical key; no listings were returned."
        selected_rows = [row for row in directory if row["industry"] == industry_value and (not sector_value or row["sector"] == sector_value)]

        class IndustryFixture:
            name = industry_value
            sector_key = _sector_key(sector_value or selected_rows[0]["sector"])
            top_companies = _company_frame(selected_rows)
            top_performing_companies = _company_frame(selected_rows)
            top_growth_companies = _company_frame(selected_rows)

        def industry_factory(_: str):
            return IndustryFixture()

        def sector_factory(sector_key: str):
            selected_sector = next((name for name in sectors if _sector_key(name) == sector_key), "")
            return SimpleNamespace(top_companies=_company_frame([row for row in directory if row["sector"] == selected_sector]))

        def ticker_factory(symbol: str):
            row = next((row for row in directory if row["symbol"] == symbol), {})
            return SimpleNamespace(get_info=lambda: {"industryKey": industry_keys.get(row.get("industry", "")), "industry": row.get("industry"), "sector": row.get("sector")})

        result, warning = discovery.fetch_industry_companies(
            industry_key=key, industry_source="Built-in yfinance directory", sector_key=_sector_key(sector_value or selected_rows[0]["sector"]),
            industry_name=industry_value, sector_name=sector_value or selected_rows[0]["sector"],
            industry_factory=industry_factory, sector_factory=sector_factory, ticker_factory=ticker_factory,
            canonical_keys=tuple(industry_keys.values()), valid_sector_keys=tuple(_sector_key(value) for value in sectors),
        )
        symbols = list(result.index.astype(str)) if not result.empty else []
        selected_rows = [row for row in selected_rows if row["symbol"] in symbols]
        if warning:
            return selected_rows, [{"name": value, "sector": sector_value or "", "company_count": 0} for value in available_industries], sectors, warning
    else:
        selected_rows = [row for row in directory if not sector_value or row["sector"] == sector_value]
    filtered = [row for row in selected_rows if not query or query.casefold() in f"{row['symbol']} {row['name']} {row['industry']}".casefold()]
    industries = [{"name": name, "sector": next(row["sector"] for row in directory if row["industry"] == name),
                   "company_count": sum(row["industry"] == name and (not sector_value or row["sector"] == sector_value) for row in directory)} for name in available_industries]
    return filtered, industries, sectors, None


def _sector_key(label: str) -> str:
    return label.casefold().replace(" & ", "-").replace(" ", "-")


def _company_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    return frame.set_index("symbol") if not frame.empty else pd.DataFrame()
