"""Interactive market-chart construction for the Streamlit dashboard."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


WINDOW_DAYS = {"1D":1, "5D":7, "1M":31, "2M":62, "3M":93,
               "6M":186, "1Y":366, "2Y":732, "5Y":1827}


def price_chart(
    history: pd.DataFrame,
    symbol: str,
    light_mode: bool = False,
    chart_type: str = "Candles",
    window: str = "6M",
    overlays: tuple[str, ...] | list[str] = ("20 day", "50 day"),
    interval: str = "1 day",
) -> go.Figure:
    """Build a TradingView-style price, moving-average, and volume chart."""
    data = history.sort_index().copy()
    if window in WINDOW_DAYS and not data.empty:
        data = data.loc[data.index >= data.index[-1] - pd.Timedelta(days=WINDOW_DAYS[window])]
    data = data.dropna(subset=["Close"])
    line_color = "#087f63" if light_mode else "#76e0b2"
    average_colors = {20:"#536ac7" if light_mode else "#9aa9ff",
                      50:"#c27a17" if light_mode else "#f4b860",
                      200:"#a34b9b" if light_mode else "#e58bd5"}
    label_color = "#61756f" if light_mode else "#91a6a3"
    grid_color = "#e1e9e5" if light_mode else "#203235"
    bull_color = "#087f63" if light_mode else "#26a69a"
    bear_color = "#d64555" if light_mode else "#ef5350"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.025,
        row_heights=[0.78, 0.22],
    )
    has_ohlc = all(column in data.columns for column in ("Open", "High", "Low", "Close"))
    if chart_type == "Candles" and has_ohlc:
        fig.add_trace(go.Candlestick(
            x=data.index, open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"],
            name=symbol, increasing_line_color=bull_color, decreasing_line_color=bear_color,
            increasing_fillcolor=bull_color, decreasing_fillcolor=bear_color,
            whiskerwidth=0.45,
            hovertemplate=("%{x|%b %d, %Y}<br>Open: $%{open:,.2f}<br>High: $%{high:,.2f}"
                           "<br>Low: $%{low:,.2f}<br>Close: $%{close:,.2f}<extra></extra>"),
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Close"], mode="lines", name=symbol,
            line={"color":line_color, "width":2}, fill="tozeroy",
            fillcolor="rgba(118,224,178,.07)" if not light_mode else "rgba(8,127,99,.08)",
            hovertemplate="%{x|%b %d, %Y}<br>Close: $%{y:,.2f}<extra></extra>",
        ), row=1, col=1)

    bar_unit = "day" if interval == "1 day" else "bar"
    for period in (20, 50, 200):
        if f"{period} {bar_unit}" not in overlays:
            continue
        label = f"{period} {bar_unit} average"
        fig.add_trace(go.Scatter(
            x=data.index, y=data["Close"].rolling(period, min_periods=period).mean(),
            mode="lines", name=label,
            line={"color":average_colors[period], "width":1.35},
            hovertemplate=f"%{{x|%b %d, %Y}}<br>{label}: $%{{y:,.2f}}<extra></extra>",
        ), row=1, col=1)

    if "Volume" in data.columns:
        if "Open" in data.columns:
            volume_colors = [bull_color if close >= open_ else bear_color
                             for open_, close in zip(data["Open"], data["Close"])]
        else:
            volume_colors = [bull_color if change >= 0 else bear_color
                             for change in data["Close"].diff().fillna(0)]
        fig.add_trace(go.Bar(
            x=data.index, y=data["Volume"], name="Volume", marker_color=volume_colors,
            opacity=0.72, hovertemplate="%{x|%b %d, %Y}<br>Volume: %{y:,.0f}<extra></extra>",
        ), row=2, col=1)

    fig.update_layout(
        height=390, margin={"l":4, "r":6, "t":26, "b":4},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color":label_color, "family":"Manrope"},
        legend={"orientation":"h", "y":1.08, "x":0},
        hovermode="x unified", dragmode="pan", uirevision=f"{symbol}:{interval}:{window}:{chart_type}",
    )
    fig.update_yaxes(showgrid=True, gridcolor=grid_color, zeroline=False, side="right", row=1, col=1)
    fig.update_yaxes(showgrid=False, zeroline=False, side="right", row=2, col=1,
                     tickformat="~s", title_text="Vol.", title_font={"size":10})
    fig.update_xaxes(showgrid=False, zeroline=False, showspikes=True, spikemode="across",
                     spikesnap="cursor", spikethickness=1, row=1, col=1)
    fig.update_xaxes(showgrid=False, zeroline=False, showspikes=True, spikemode="across",
                     spikesnap="cursor", spikethickness=1, row=2, col=1)
    return fig
