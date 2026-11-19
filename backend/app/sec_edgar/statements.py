"""Deterministic, period-safe views over preserved SEC Company Facts records."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from .mapping import SecFinancialFact, SecStatementPeriod, SecStatementValue


ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
INTERIM_FORMS = {"10-Q", "10-Q/A", "6-K", "6-K/A"}
INSTANT_FIELDS = {"assets", "liabilities", "cash_and_equivalents", "stockholders_equity", "long_term_debt_current", "long_term_debt_noncurrent"}
EXPECTED_FIELDS = (
    "revenue", "operating_income", "net_income", "diluted_eps", "operating_cash_flow",
    "capital_expenditures", "assets", "liabilities", "stockholders_equity", "cash_and_equivalents",
    "long_term_debt_current", "long_term_debt_noncurrent",
)


def _duration_days(fact: SecFinancialFact) -> int | None:
    if fact.period_start is None:
        return None
    return (fact.period_end - fact.period_start).days + 1


def _period_type(fact: SecFinancialFact, days: int | None) -> str | None:
    fp = (fact.fiscal_period or "").upper()
    if fact.field in INSTANT_FIELDS and days is None:
        if fact.form in ANNUAL_FORMS and fp == "FY":
            return "annual"
        if fact.form in INTERIM_FORMS and fp in {"Q1", "Q2", "Q3"}:
            return "quarterly"
        return None
    if days is None:
        return None
    if fact.form in ANNUAL_FORMS and fp == "FY" and 300 <= days <= 400:
        return "annual"
    if fact.form in INTERIM_FORMS and fp in {"Q1", "Q2", "Q3"}:
        if 70 <= days <= 110:
            return "quarterly"
        if fp in {"Q2", "Q3"} and 120 <= days < 300:
            return "ytd"
    return None


def _reported_fiscal_year(fact: SecFinancialFact, period_type: str, annual_ends: list[date]) -> int:
    """Anchor period years to actual period dates, not filing-year metadata.

    SEC ``fy`` can describe the filing's fiscal year even when an accession
    carries prior-year comparative facts. Annual periods therefore use their
    reported end year. Interim periods map to the next reported annual close,
    which also handles fiscal years ending outside December.
    """
    if period_type == "annual":
        return fact.period_end.year
    following_annual_ends = [end for end in annual_ends if end >= fact.period_end]
    if following_annual_ends:
        nearest = min(following_annual_ends, key=lambda end: (end - fact.period_end).days)
        # The next annual close is normally at most about nine months after
        # Q1 and at most three months after Q3. A full year usually signals a
        # prior-year comparative value, not a period in the later fiscal year.
        if (nearest - fact.period_end).days <= 310:
            return nearest.year
    return fact.fiscal_year if fact.fiscal_year is not None else fact.period_end.year


def _reported_fiscal_period(fact: SecFinancialFact, period_type: str, annual_ends: list[date]) -> str | None:
    """Resolve interim quarter labels from the issuer's annual boundaries.

    SEC ``fp`` metadata can disagree across facts for the same report date.
    When consecutive annual closes bracket an interim date, use its position
    in that fiscal year to choose the nearest conventional quarter boundary.
    Keep the provider label when the dates do not support a confident match.
    """
    if period_type == "annual":
        return "FY"
    source_period = (fact.fiscal_period or "").upper()
    if period_type not in {"quarterly", "ytd"}:
        return fact.fiscal_period

    previous_ends = [end for end in annual_ends if end < fact.period_end]
    following_ends = [end for end in annual_ends if end > fact.period_end]
    if not previous_ends or not following_ends:
        return source_period or None
    previous_end = max(previous_ends)
    next_end = min(following_ends)
    fiscal_year_days = (next_end - previous_end).days
    elapsed_days = (fact.period_end - previous_end).days
    if fiscal_year_days <= 0 or elapsed_days <= 0 or elapsed_days >= fiscal_year_days:
        return source_period or None

    position = elapsed_days / fiscal_year_days
    quarter_centers = (("Q1", 0.25), ("Q2", 0.50), ("Q3", 0.75))
    nearest, center = min(quarter_centers, key=lambda item: abs(position - item[1]))
    return nearest if abs(position - center) <= 0.10 else (source_period or None)


def _metric_value(fact: SecFinancialFact, days: int | None) -> SecStatementValue:
    return SecStatementValue(
        field=fact.field, taxonomy=fact.taxonomy, tag=fact.tag, label=fact.label,
        value=fact.value, original_value=fact.original_value, unit=fact.unit,
        currency=fact.currency, period_start=fact.period_start, period_end=fact.period_end,
        duration_days=days, form=fact.form, filed=fact.filed,
        accession_number=fact.accession_number, filing_url=fact.filing_url,
    )


def _comparable_duration(current: int | None, previous: int | None) -> bool:
    if current is None or previous is None:
        return current is None and previous is None
    # Fiscal calendars can move by a day or two; large duration differences
    # (quarter vs YTD or FY) are never treated as comparable.
    return abs(current - previous) <= 7


def _percentage_change(current: str, previous: str) -> float | None:
    try:
        current_decimal = Decimal(current)
        previous_decimal = Decimal(previous)
        if not current_decimal.is_finite() or not previous_decimal.is_finite() or previous_decimal == 0:
            return None
        return float((current_decimal - previous_decimal) / abs(previous_decimal) * Decimal(100))
    except (InvalidOperation, ValueError, OverflowError):
        return None


def build_statement_periods(
    facts: list[SecFinancialFact],
) -> tuple[list[SecStatementPeriod], list[SecStatementPeriod], list[SecStatementPeriod]]:
    """Build annual, discrete-quarter and cumulative YTD statement views.

    A three-month period is eligible as a quarter only when SEC metadata marks
    Q1-Q3 and its actual start/end span is approximately one quarter. Annual
    facts are FY disclosures. Six-/nine-month cumulative facts remain YTD and
    are never differenced to manufacture quarter values or Q4.
    """
    rows: dict[str, dict[tuple, dict]] = {"annual": {}, "quarterly": {}, "ytd": {}}
    annual_ends = sorted({
        fact.period_end for fact in facts
        if fact.latest_reported_version and fact.form in ANNUAL_FORMS
        and _period_type(fact, _duration_days(fact)) == "annual"
    })
    for fact in facts:
        if not fact.latest_reported_version or fact.field not in EXPECTED_FIELDS:
            continue
        days = _duration_days(fact)
        kind = _period_type(fact, days)
        if kind is None:
            continue
        # Instant balance-sheet observations accompany the annual or quarter
        # they were reported with; they are never cumulative YTD disclosures.
        kinds = {kind}
        for view_kind in kinds:
            fiscal_year = _reported_fiscal_year(fact, view_kind, annual_ends)
            view_period = _reported_fiscal_period(fact, view_kind, annual_ends)
            key = (fiscal_year, view_period, fact.period_end)
            row = rows[view_kind].setdefault(key, {
                "fiscal_year": fiscal_year,
                "fiscal_period": view_period,
                "period_type": view_kind,
                "period_start": fact.period_start,
                "period_end": fact.period_end,
                "metrics": defaultdict(list),
            })
            row["metrics"][fact.field].append(_metric_value(fact, days))

    result: dict[str, list[SecStatementPeriod]] = {}
    for kind, grouped in rows.items():
        periods: list[SecStatementPeriod] = []
        for row in grouped.values():
            metrics = {
                field: sorted(values, key=lambda item: (item.unit, item.filed, item.accession_number))
                for field, values in row["metrics"].items()
            }
            periods.append(SecStatementPeriod(**{**row, "metrics": metrics}))
        periods.sort(key=lambda row: (row.period_end, row.fiscal_year or 0, row.fiscal_period or ""), reverse=True)
        result[kind] = periods

    for kind, periods in result.items():
        enriched: list[SecStatementPeriod] = []
        for period in periods:
            metrics: dict[str, list[SecStatementValue]] = {}
            for field, values in period.metrics.items():
                out: list[SecStatementValue] = []
                for value in values:
                    prior: list[SecStatementValue] = []
                    if period.fiscal_year is not None:
                        for other in periods:
                            if other.fiscal_year != period.fiscal_year - 1 or other.fiscal_period != period.fiscal_period:
                                continue
                            for previous in other.metrics.get(field, []):
                                if previous.unit == value.unit and _comparable_duration(value.duration_days, previous.duration_days):
                                    prior.append(previous)
                    if prior:
                        previous = max(prior, key=lambda item: (item.period_end, item.filed, item.accession_number))
                        change = _percentage_change(value.original_value, previous.original_value)
                        value = value.model_copy(update={
                            "comparison_percent": change,
                            "comparison_period_end": previous.period_end if change is not None else None,
                            "comparison_value": previous.original_value if change is not None else None,
                            "comparison_filed": previous.filed if change is not None else None,
                            "comparison_form": previous.form if change is not None else None,
                            "comparison_accession_number": previous.accession_number if change is not None else None,
                            "comparison_filing_url": previous.filing_url if change is not None else None,
                        })
                    out.append(value)
                metrics[field] = out
            enriched.append(period.model_copy(update={"metrics": metrics}))
        result[kind] = enriched

    return result["annual"], result["quarterly"], result["ytd"]
