"""Plotly chart construction, kept separate from Streamlit rendering."""

import plotly.graph_objects as go
import pandas as pd


def price_chart(history: pd.DataFrame, symbol: str, light_mode: bool = False) -> go.Figure:
    data = history.tail(126)
    line_color = "#087f63" if light_mode else "#76e0b2"
    average_color = "#536ac7" if light_mode else "#9aa9ff"
    label_color = "#61756f" if light_mode else "#91a6a3"
    grid_color = "#e1e9e5" if light_mode else "#203235"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data["Close"], mode="lines", name=symbol,
        line={"color":line_color, "width":2.4}, fill="tozeroy",
        fillcolor="rgba(118,224,178,.07)",
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data["Close"].rolling(20, min_periods=20).mean(),
        mode="lines", name="20 day average",
        line={"color":average_color, "width":1.4, "dash":"dot"},
    ))
    fig.update_layout(
        height=310, margin={"l":0,"r":0,"t":12,"b":0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color":label_color,"family":"Manrope"},
        legend={"orientation":"h","y":1.12,"x":0},
        xaxis={"showgrid":False,"zeroline":False},
        yaxis={"showgrid":True,"gridcolor":grid_color,"zeroline":False,"side":"right"},
        hovermode="x unified",
    )
    return fig
