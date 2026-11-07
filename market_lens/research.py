"""Presentation normalization for optional company research data."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


FUNDAMENTAL_FIELDS = (
    ("Market cap", "marketCap", "currency"),
    ("Trailing P/E", "trailingPE", "number"),
    ("Forward P/E", "forwardPE", "number"),
    ("PEG ratio", "pegRatio", "number"),
    ("Price / sales", "priceToSalesTrailing12Months", "number"),
    ("EV / EBITDA", "enterpriseToEbitda", "number"),
    ("Revenue growth", "revenueGrowth", "percent"),
    ("Profit margin", "profitMargins", "percent"),
    ("Operating margin", "operatingMargins", "percent"),
    ("Return on equity", "returnOnEquity", "percent"),
    ("Debt / equity", "debtToEquity", "number"),
    ("Current ratio", "currentRatio", "number"),
    ("Free cash flow", "freeCashflow", "currency"),
    ("Dividend yield", "dividendYield", "percent"),
)

QUARTERLY_ROWS = (
    ("Revenue ($B)", ("Total Revenue",)),
    ("Operating income ($B)", ("Operating Income", "Total Operating Income As Reported")),
    ("Net income ($B)", ("Net Income",)),
    ("Diluted EPS", ("Diluted EPS",)),
)

RECOMMENDATION_FIELDS = (
    ("Strong buy", "strongBuy"),
    ("Buy", "buy"),
    ("Hold", "hold"),
    ("Sell", "sell"),
    ("Strong sell", "strongSell"),
)

EPS_REVISION_COLUMN_LABELS = {
    "upLast7days":"Up last 7 days",
    "upLast30days":"Up last 30 days",
    "downLast7Days":"Down last 7 days",
    "downLast30days":"Down last 30 days",
    "currency":"Currency",
    "methodology":"Methodology",
}
EPS_REVISION_PERIOD_LABELS = {
    "0q":"Current quarter", "+1q":"Next quarter",
    "0y":"Current year", "+1y":"Next year",
}


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if np.isfinite(number) else None


def fundamentals_metric_table(info: object) -> pd.DataFrame:
    """Build the Business & Valuation table from provider-supplied profile fields."""
    values = info if isinstance(info, Mapping) else {}
    rows = []
    for label, key, kind in FUNDAMENTAL_FIELDS:
        number = _finite_number(values.get(key))
        if number is None:
            display = "—"
        elif kind == "percent":
            display = f"{number * 100:.1f}%"
        elif kind == "currency":
            display = f"${number / 1e12:.2f}T" if abs(number) >= 1e12 else f"${number / 1e9:.2f}B"
        else:
            display = f"{number:,.2f}"
        rows.append({"Metric":label, "Latest value":display})
    return pd.DataFrame(rows, columns=["Metric", "Latest value"])


def quarterly_statement_table(statement: object) -> pd.DataFrame:
    """Normalize yfinance quarterly income rows without estimating missing values."""
    empty = pd.DataFrame(columns=[label for label, _ in QUARTERLY_ROWS])
    if not isinstance(statement, pd.DataFrame) or statement.empty:
        return empty

    dated_columns = []
    for column in statement.columns:
        parsed = pd.to_datetime(column, errors="coerce")
        if not pd.isna(parsed):
            dated_columns.append((parsed, column))
    if not dated_columns:
        return empty
    dated_columns.sort(key=lambda item:item[0], reverse=True)
    selected_columns = dated_columns[:4]

    available_rows = []
    for display_label, candidates in QUARTERLY_ROWS:
        row_key = next((candidate for candidate in candidates if candidate in statement.index), None)
        if row_key is None:
            continue
        row_values = []
        for _, column in selected_columns:
            number = _finite_number(statement.at[row_key, column])
            if number is not None and display_label != "Diluted EPS":
                number /= 1e9
            row_values.append(number)
        available_rows.append((display_label, row_values))

    if not available_rows:
        return empty
    periods = [parsed.strftime("%b %Y") for parsed, _ in selected_columns]
    return pd.DataFrame(
        {label:values for label, values in available_rows},
        index=pd.Index(periods, name="Quarter"),
    )


def analyst_target_summary(targets: object, last_price: object = None) -> dict[str, float | None] | None:
    """Validate the yfinance target mapping while keeping missing values explicit."""
    if not isinstance(targets, Mapping) or not targets:
        return None
    normalized = {key:_finite_number(targets.get(key)) for key in ("current", "high", "low", "mean", "median")}
    if not any(value is not None for value in normalized.values()):
        return None
    spot = _finite_number(last_price)
    mean = normalized["mean"]
    normalized["upside_percent"] = ((mean / spot - 1) * 100
                                    if mean is not None and spot is not None and spot > 0 else None)
    return normalized


def recommendation_distribution(recommendations: object) -> pd.DataFrame | None:
    """Format the current yfinance recommendation period as a labeled count table."""
    if not isinstance(recommendations, pd.DataFrame) or recommendations.empty:
        return None
    if not all(field in recommendations.columns for _, field in RECOMMENDATION_FIELDS):
        return None
    current = recommendations
    if "period" in current.columns:
        periods = current["period"].astype(str).str.casefold()
        current_period = current.loc[periods == "0m"]
        if not current_period.empty:
            current = current_period
    record = current.iloc[0]
    rows = []
    for label, field in RECOMMENDATION_FIELDS:
        count = _finite_number(record[field])
        if count is None or count < 0 or not count.is_integer():
            return None
        rows.append({"Rating":label, "Analyst count":int(count)})
    return pd.DataFrame(rows, columns=["Rating", "Analyst count"])


def eps_revision_table(revisions: object) -> pd.DataFrame | None:
    """Use readable labels while preserving all provider-supplied revision values."""
    if not isinstance(revisions, pd.DataFrame) or revisions.empty:
        return None
    result = revisions.rename(columns=EPS_REVISION_COLUMN_LABELS).copy()
    result.index = pd.Index(
        [EPS_REVISION_PERIOD_LABELS.get(str(period), str(period)) for period in result.index],
        name="Period",
    )
    return result
