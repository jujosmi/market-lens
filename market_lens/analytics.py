"""Pure financial calculations. All horizons use trading observations."""

from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252
HORIZONS = {"1d":1, "1w":5, "1m":21, "3m":63, "6m":126, "1y":252}


def close_series(prices: pd.Series | pd.DataFrame) -> pd.Series:
    """Get valid positive closes, with one observation per normalized date."""
    if isinstance(prices, pd.DataFrame):
        if "Close" not in prices:
            return pd.Series(dtype="float64", name="Close")
        series = prices["Close"]
    else:
        series = prices
    series = pd.to_numeric(series, errors="coerce").dropna().astype("float64")
    if isinstance(series.index, pd.DatetimeIndex):
        index = series.index
        if index.tz is not None:
            index = index.tz_localize(None)
        series.index = index.normalize()
        series = series[~series.index.duplicated(keep="last")]
    return series[series > 0].sort_index()


def moving_average(prices: pd.Series | pd.DataFrame, window: int) -> float:
    """Return a full-window simple moving average, or NaN if history is short."""
    if window <= 0:
        raise ValueError("window must be positive")
    close = close_series(prices)
    if len(close) < window:
        return float("nan")
    return float(close.rolling(window=window, min_periods=window).mean().iloc[-1])


def relative_strength_index(prices: pd.Series | pd.DataFrame, period: int = 14) -> float:
    """Wilder RSI; return NaN until a complete seed period is available.

    Edge conventions: no losses => 100; no gains => 0; no gains and no losses
    (flat closes) => 50.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    close = close_series(prices)
    if len(close) < period + 1:
        return float("nan")
    change = close.diff().dropna()
    if len(change) < period:
        return float("nan")
    gains = change.clip(lower=0).to_numpy()
    losses = (-change.clip(upper=0)).to_numpy()
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0
    return float(100 - 100 / (1 + avg_gain / avg_loss))


def period_return(prices: pd.Series | pd.DataFrame, sessions: int) -> float:
    """Simple return over exactly `sessions` intervals; NaN without n+1 closes."""
    if sessions <= 0:
        raise ValueError("sessions must be positive")
    close = close_series(prices)
    if len(close) < sessions + 1:
        return float("nan")
    return float(close.iloc[-1] / close.iloc[-sessions - 1] - 1)


def _aligned_closes(asset: pd.Series | pd.DataFrame, benchmark: pd.Series | pd.DataFrame) -> pd.DataFrame:
    left = close_series(asset).rename("asset")
    right = close_series(benchmark).rename("benchmark")
    return pd.concat([left, right], axis=1, join="inner").dropna().sort_index()


def relative_return(asset: pd.Series | pd.DataFrame, benchmark: pd.Series | pd.DataFrame, sessions: int) -> dict[str, float]:
    """Calculate asset and SPY returns over the same common trading dates."""
    if sessions <= 0:
        raise ValueError("sessions must be positive")
    aligned = _aligned_closes(asset, benchmark)
    if len(aligned) < sessions + 1:
        return {"asset":float("nan"), "benchmark":float("nan"), "excess":float("nan"), "observations":len(aligned)}
    period = aligned.iloc[-sessions - 1:]
    asset_return = float(period["asset"].iloc[-1] / period["asset"].iloc[0] - 1)
    benchmark_return = float(period["benchmark"].iloc[-1] / period["benchmark"].iloc[0] - 1)
    return {"asset":asset_return, "benchmark":benchmark_return,
            "excess":asset_return-benchmark_return, "observations":len(period)}


def beta(asset: pd.Series | pd.DataFrame, benchmark: pd.Series | pd.DataFrame,
         window: int = 120, minimum_observations: int = 60) -> tuple[float, int]:
    """OLS-style beta from aligned daily simple returns; report paired sample size."""
    if window <= 1 or minimum_observations <= 1:
        raise ValueError("window and minimum_observations must exceed one")
    asset_returns = close_series(asset).pct_change(fill_method=None).rename("asset")
    benchmark_returns = close_series(benchmark).pct_change(fill_method=None).rename("benchmark")
    aligned = pd.concat([asset_returns, benchmark_returns], axis=1, join="inner").dropna().tail(window)
    count = len(aligned)
    if count < minimum_observations or aligned["benchmark"].var(ddof=1) == 0:
        return float("nan"), count
    value = aligned["asset"].cov(aligned["benchmark"]) / aligned["benchmark"].var(ddof=1)
    return float(value), count


def realized_volatility(prices: pd.Series | pd.DataFrame, window: int = 30,
                        minimum_observations: int | None = None) -> tuple[float, int]:
    """Annualized sample standard deviation of daily returns; no fixed fallback."""
    if window <= 1:
        raise ValueError("window must exceed one")
    required = window if minimum_observations is None else minimum_observations
    if required <= 1:
        raise ValueError("minimum_observations must exceed one")
    returns = close_series(prices).pct_change(fill_method=None).dropna().tail(window)
    if len(returns) < required:
        return float("nan"), len(returns)
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)), len(returns)


def maximum_drawdown(prices: pd.Series | pd.DataFrame, observations: int = 252) -> tuple[float, int]:
    """Maximum peak-to-trough drawdown over a full observation window."""
    if observations <= 1:
        raise ValueError("observations must exceed one")
    close = close_series(prices)
    if len(close) < observations:
        return float("nan"), len(close)
    period = close.tail(observations)
    drawdowns = period / period.cummax() - 1
    return float(drawdowns.min()), len(period)


def _macd(prices: pd.Series, minimum_observations: int = 35) -> tuple[float, float]:
    if len(prices) < minimum_observations:
        return float("nan"), float("nan")
    fast = prices.ewm(span=12, adjust=False, min_periods=12).mean()
    slow = prices.ewm(span=26, adjust=False, min_periods=26).mean()
    line = fast - slow
    signal = line.ewm(span=9, adjust=False, min_periods=9).mean()
    return float(line.iloc[-1]), float(signal.iloc[-1])


def analyze(history: pd.DataFrame, info: dict | None = None,
            options_move: float | None = None,
            benchmark: pd.DataFrame | None = None) -> dict:
    """Build indicator values and an explainable rating from valid history only."""
    info = info or {}
    close = close_series(history)
    if close.empty:
        raise ValueError("No valid closing prices")
    last = float(close.iloc[-1])
    day_return = period_return(close, 1)
    sma20 = moving_average(close, 20)
    sma50 = moving_average(close, 50)
    sma200 = moving_average(close, 200)
    rsi = relative_strength_index(close, 14)
    macd, macd_signal = _macd(close)
    hist_vol, hist_vol_observations = realized_volatility(close, 30)
    drawdown, drawdown_observations = maximum_drawdown(close, 252)
    current_drawdown = float(close.iloc[-1] / close.tail(252).max() - 1) if len(close) >= 252 else float("nan")
    high52 = float(close.tail(252).max()) if len(close) >= 252 else float("nan")
    low52 = float(close.tail(252).min()) if len(close) >= 252 else float("nan")
    returns = {}
    for label, sessions in HORIZONS.items():
        if label == "1d":
            base = period_return(close, sessions)
            returns[label] = {"asset":base, "benchmark":float("nan"), "excess":float("nan"), "observations":len(close)}
        elif benchmark is not None and not benchmark.empty:
            returns[label] = relative_return(close, benchmark, sessions)
        else:
            own = period_return(close, sessions)
            returns[label] = {"asset":own, "benchmark":float("nan"), "excess":float("nan"), "observations":len(close)}
    beta_value, beta_observations = (beta(close, benchmark) if benchmark is not None and not benchmark.empty
                                     else (float("nan"), 0))
    move = float(options_move) if options_move is not None and np.isfinite(options_move) and options_move > 0 else float("nan")
    move_source = "Options implied volatility" if np.isfinite(move) else "Unavailable: insufficient realized-volatility history"
    if not np.isfinite(move) and np.isfinite(hist_vol):
        move = float(hist_vol * np.sqrt(21 / TRADING_DAYS_PER_YEAR))
        move_source = "30-session realized volatility estimate"

    above50 = last > sma50 if np.isfinite(sma50) else None
    stack50_200 = sma50 > sma200 if np.isfinite(sma50) and np.isfinite(sma200) else None
    macd_positive = macd > macd_signal if np.isfinite(macd) and np.isfinite(macd_signal) else None
    excess3m = returns["3m"]["excess"]
    excess_positive = excess3m > 0 if np.isfinite(excess3m) else None
    rsi_constructive = 50 <= rsi < 70 if np.isfinite(rsi) else None
    below200 = last < sma200 if np.isfinite(sma200) else None
    macd_negative = macd < macd_signal if np.isfinite(macd) and np.isfinite(macd_signal) else None
    excess_negative = excess3m < 0 if np.isfinite(excess3m) else None
    rsi_elevated = rsi >= 70 if np.isfinite(rsi) else None
    deep_drawdown = current_drawdown <= -0.20 if np.isfinite(current_drawdown) else None
    constructive_values = [above50, stack50_200, macd_positive, excess_positive, rsi_constructive]
    caution_values = [below200, macd_negative, excess_negative, rsi_elevated, deep_drawdown]
    rating_checks = [
        {"side":"Constructive", "label":"Price above 50-day average", "passed":above50},
        {"side":"Constructive", "label":"50-day average above 200-day average", "passed":stack50_200},
        {"side":"Constructive", "label":"MACD above signal line", "passed":macd_positive},
        {"side":"Constructive", "label":"3-month excess return vs SPY is positive", "passed":excess_positive},
        {"side":"Constructive", "label":"RSI between 50 and 70", "passed":rsi_constructive},
        {"side":"Caution", "label":"Price below 200-day average", "passed":below200},
        {"side":"Caution", "label":"MACD below signal line", "passed":macd_negative},
        {"side":"Caution", "label":"3-month excess return vs SPY is negative", "passed":excess_negative},
        {"side":"Caution", "label":"RSI at or above 70", "passed":rsi_elevated},
        {"side":"Caution", "label":"Drawdown is at least 20% from the 52-week high", "passed":deep_drawdown},
    ]
    constructive_count = sum(value is True for value in constructive_values)
    caution_count = sum(value is True for value in caution_values)
    checks_complete = all(value is not None for value in constructive_values + caution_values)
    balance = constructive_count - caution_count
    rating = ("Buy" if balance >= 2 else "Sell" if balance <= -2 else "Hold") if checks_complete else "Unavailable"

    if np.isfinite(sma200):
        above50_200 = last > sma50 > sma200 if np.isfinite(sma50) else False
        below50_200 = last < sma50 < sma200 if np.isfinite(sma50) else False
        state = "Upward 50d / 200d alignment" if above50_200 else "Downward 50d / 200d alignment" if below50_200 else "Mixed moving-average alignment"
    else:
        state = "Insufficient history for a 200-day trend"

    relative_volume = float("nan")
    if "Volume" in history:
        volume = pd.to_numeric(history["Volume"], errors="coerce").dropna()
        if len(volume) >= 20:
            median = float(volume.tail(20).median())
            if median > 0:
                relative_volume = float(volume.iloc[-1] / median)
    return {
        "last":last, "change":day_return * 100 if np.isfinite(day_return) else float("nan"),
        "move":move, "move_source":move_source, "hist_vol":hist_vol,
        "hist_vol_observations":hist_vol_observations, "sma20":sma20, "sma50":sma50,
        "sma200":sma200, "rsi":rsi, "state":state, "market_cap":info.get("marketCap"),
        "name":info.get("shortName") or info.get("longName"), "macd":macd,
        "macd_signal":macd_signal, "drawdown":drawdown * 100 if np.isfinite(drawdown) else drawdown,
        "drawdown_observations":drawdown_observations,
        "current_drawdown":current_drawdown * 100 if np.isfinite(current_drawdown) else current_drawdown,
        "high52":high52, "low52":low52, "relative_volume":relative_volume,
        "returns":returns, "beta":beta_value, "beta_observations":beta_observations,
        "rating":rating, "constructive_checks":constructive_count,
        "caution_checks":caution_count, "rating_checks_complete":checks_complete,
        "rating_check_details":rating_checks, "observations":len(close),
    }
