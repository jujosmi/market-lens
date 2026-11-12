from __future__ import annotations

import html
import logging
import os
import re
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
try:
    # yfinance ships this mapping locally, so the industry directory can still
    # render and be searched when Yahoo's sector endpoint is temporarily down.
    from yfinance.const import SECTOR_INDUSTY_MAPPING, SECTOR_INDUSTY_MAPPING_LC
except Exception:
    SECTOR_INDUSTY_MAPPING = {}
    SECTOR_INDUSTY_MAPPING_LC = {}
from market_lens.analytics import analyze
from market_lens.assistant import ask_ai, floating_chat, get_api_key
from market_lens.charts import price_chart
from market_lens.config import (
    DEFAULT_WATCHLIST, MAX_WATCHLIST_SIZE, SECTORS, SECTOR_KEYS,
    hosted_watchlist_mode, public_watchlist_guard,
)
from market_lens.cache_policy import clear_selected_ticker_caches as invalidate_ticker_caches
from market_lens.discovery import (
    canonical_local_industry_rows, fetch_industry_companies, industry_identity, provider_text,
)
from market_lens.explanations import rating_explanation, trend_explanation
from market_lens.news import classify_headline as sentiment, classify_news_topic as news_topic
from market_lens.providers import YahooFinanceProvider
from market_lens.research import (
    analyst_target_summary, eps_revision_table, fundamentals_metric_table,
    quarterly_statement_table, recommendation_distribution,
)
from market_lens.storage import load_watchlist, save_watchlist
from market_lens.ui.components import (
    render_company_header, render_financial_table, render_headline_card, render_metric_card, render_section_heading, render_workspace_heading,
)
from market_lens.ui.navigation import (
    WORKSPACES, WORKSPACE_KEY, initialize_workspace_state,
    restore_workspace_widget_state, save_workspace_widget_state,
    workspace_requires_ticker_data,
)
from market_lens.ui.theme import app_background_css, css_variable_declarations, get_theme_tokens, resolve_active_theme

LOGGER = logging.getLogger("market_lens.app")

def configure_app() -> None:
    global ACTIVE_THEME, LIGHT_THEME, THEME_COLORS, HOSTED_MODE
    st.set_page_config(page_title="Jujosmi Trade", page_icon="◉", layout="wide", initial_sidebar_state="expanded")


    try:
        ACTIVE_THEME = resolve_active_theme(st.session_state.get("market_lens_ui_theme"), st.context.theme.type)
    except Exception:
        ACTIVE_THEME = "dark"
    LIGHT_THEME = ACTIVE_THEME == "light"
    THEME_COLORS = get_theme_tokens(ACTIVE_THEME)
    st.markdown(
        "<style>:root{" + css_variable_declarations(THEME_COLORS) + "}</style>",
        unsafe_allow_html=True,
    )


    def _secret_setting(name: str) -> str:
        try:
            return str(st.secrets.get(name, ""))
        except Exception:
            return ""


    HOSTED_MODE = hosted_watchlist_mode(os.environ.get("MARKET_LENS_HOSTED", ""), _secret_setting("MARKET_LENS_HOSTED"))
    PUBLIC_DEPLOYMENT_ERROR = public_watchlist_guard(
        os.environ.get("MARKET_LENS_PUBLIC", ""), _secret_setting("MARKET_LENS_PUBLIC"),
        os.environ.get("MARKET_LENS_HOSTED", ""), _secret_setting("MARKET_LENS_HOSTED"),
    )
    if PUBLIC_DEPLOYMENT_ERROR:
        st.error(PUBLIC_DEPLOYMENT_ERROR)
        st.stop()

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {
      --ink:var(--market-lens-text,#edf4f2);
      --muted:var(--market-lens-muted,color-mix(in srgb,var(--ink) 62%,transparent));
      --panel:var(--market-lens-surface,#111d20);
      --line:var(--market-lens-border,#26383a);
      --mint:var(--market-lens-accent,#76e0b2);
      --app-bg:var(--market-lens-background,#0b1417);
      --bull:var(--market-lens-bull,color-mix(in srgb,var(--ink) 48%,#00a66c));
      --bear:var(--market-lens-bear,color-mix(in srgb,var(--ink) 48%,#d64555));
      --caution:var(--market-lens-caution,color-mix(in srgb,var(--ink) 48%,#bd7900));
    }
    [data-testid="stMainBlockContainer"] { max-width:1680px; padding-top:26px; padding-bottom:72px; }
    html, body, [class*="css"] { font-family:var(--market-lens-font-body,'Manrope',system-ui,sans-serif); }
    [data-testid="stSidebar"] { background:var(--market-lens-sidebar,var(--secondary-background-color,#0e191c)); border-right:1px solid var(--line); }
    h1,h2,h3 { letter-spacing:-.04em !important; }
    .st-key-market_lens_workspace_nav div[role="radiogroup"] { gap:4px; }
    .st-key-market_lens_workspace_nav label { border:1px solid transparent; border-radius:10px; padding:5px 8px; }
    .st-key-market_lens_workspace_nav label:focus-within { outline:2px solid var(--mint); outline-offset:2px; }
    .st-key-market_lens_workspace_nav label:has(input:checked) { background:color-mix(in srgb,var(--mint) 12%,var(--panel)); border-color:var(--line); }
    .workspace-heading { padding:8px 0 22px; margin:0 0 20px; border-bottom:1px solid var(--line); }
    .workspace-eyebrow { color:var(--mint); text-transform:uppercase; letter-spacing:.14em; font-size:10px; font-weight:800; }
    .workspace-heading h1 { color:var(--ink); font-size:clamp(30px,3.2vw,42px); line-height:1.12; margin:7px 0 6px; letter-spacing:-.045em; }
    .workspace-heading p { color:var(--muted); font-size:14px; line-height:1.55; margin:0; max-width:760px; }
    .brand { font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; color:var(--mint); }
    .jujosmi-home-link { display:block; margin:0 0 18px; line-height:0; }
    .jujosmi-home-link img { display:block; width:min(100%,205px); max-height:54px; object-fit:contain; object-position:left center; }
    .hero { padding:10px 0 24px; }
    .quick-nav { display:flex; flex-wrap:wrap; gap:8px; margin:-8px 0 22px; }
    .quick-nav a { display:inline-flex; align-items:center; padding:8px 12px; border:1px solid var(--line); border-radius:999px; background:color-mix(in srgb,var(--panel) 88%,transparent); color:var(--ink); font-size:12px; font-weight:700; text-decoration:none; transition:background .15s ease,border-color .15s ease,transform .15s ease; }
    .quick-nav a:hover { background:color-mix(in srgb,var(--mint) 14%,var(--panel)); border-color:var(--mint); transform:translateY(-1px); }
    .quick-nav a:focus-visible { outline:2px solid var(--mint); outline-offset:2px; }
    .section-anchor { height:1px; scroll-margin-top:18px; }
    .eyebrow { color:var(--muted); text-transform:uppercase; letter-spacing:.14em; font-size:10px; font-weight:700; }
    .hero h1 { font-size:42px; margin:4px 0 4px; }
    .snapshot-security { font-size:.56em; font-weight:600; color:var(--muted); letter-spacing:0; vertical-align:middle; white-space:normal; }
    .sub { color:var(--muted); font-size:14px; }
    .panel { background:linear-gradient(145deg,color-mix(in srgb,var(--panel) 96%,var(--mint) 4%),var(--panel)); border:1px solid var(--line); border-radius:18px; padding:20px 22px; height:100%; }
    .stMainBlockContainer button, .stMainBlockContainer [role="button"] { transition:background-color .15s ease,border-color .15s ease,box-shadow .15s ease; }
    .stMainBlockContainer button:focus-visible, .stMainBlockContainer a:focus-visible,
    .stMainBlockContainer input:focus-visible, .stMainBlockContainer [role="radio"]:focus-visible,
    [data-testid="stSidebar"] button:focus-visible, [data-testid="stSidebar"] input:focus-visible {
      outline:2px solid var(--mint) !important; outline-offset:2px !important;
    }
    .stMainBlockContainer [data-testid="stTextInput"] input,
    .stMainBlockContainer [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    .stMainBlockContainer [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
      background:var(--panel); border-color:var(--line); border-radius:10px;
    }
    .stMainBlockContainer [data-testid="stAlert"] { border-radius:12px; }
    .stMainBlockContainer [data-testid="stSpinner"] { color:var(--muted); }
    .metric-label { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.12em; font-weight:700; }
    .metric-value { font-family:var(--market-lens-font-financial,'DM Mono',monospace); font-size:26px; font-weight:500; margin-top:8px; color:var(--ink); }
    .metric-note { color:var(--muted); font-size:12px; margin-top:5px; }
    .metric-label-row { display:flex; align-items:center; gap:7px; }
    .help-icon { position:relative; display:inline-block; flex:0 0 20px; width:20px; height:20px; }
    .help-icon > summary { list-style:none; display:flex; align-items:center; justify-content:center; width:20px; height:20px; border:1px solid var(--line); border-radius:50%; color:var(--muted); font:700 11px Manrope,sans-serif; cursor:pointer; }
    .help-icon > summary::-webkit-details-marker { display:none; }
    .help-icon > summary::marker { content:""; }
    .help-icon > summary:hover, .help-icon[open] > summary { color:var(--app-bg); background:var(--mint); border-color:var(--mint); }
    .help-icon > summary:focus-visible { outline:2px solid var(--mint); outline-offset:3px; }
    .metric-tooltip { display:none; position:absolute; z-index:1000; right:-8px; bottom:24px; width:min(280px,calc(100vw - 40px)); max-height:min(60vh,320px); overflow:auto; padding:11px 13px; border:1px solid var(--line); border-radius:11px; color:var(--ink); background:var(--panel); box-shadow:0 12px 32px rgba(0,0,0,.18); font-size:11px; font-weight:500; line-height:1.5; text-transform:none; letter-spacing:0; }
    .help-icon:hover .metric-tooltip, .help-icon[open] .metric-tooltip { display:block; }
    .pill { display:inline-block; padding:5px 10px; border-radius:99px; font-size:11px; font-weight:800; letter-spacing:.04em; }
    .bull { color:var(--bull); background:color-mix(in srgb,#00a66c 12%,transparent); border:1px solid color-mix(in srgb,#00a66c 30%,transparent); }
    .bear { color:var(--bear); background:color-mix(in srgb,#d64555 11%,transparent); border:1px solid color-mix(in srgb,#d64555 29%,transparent); }
    .neutral { color:var(--muted); background:color-mix(in srgb,var(--muted) 10%,transparent); border:1px solid color-mix(in srgb,var(--muted) 25%,transparent); }
    .low { color:var(--caution); background:color-mix(in srgb,#bd7900 12%,transparent); border:1px solid color-mix(in srgb,#bd7900 30%,transparent); }
    .news-title { color:var(--ink); font-weight:650; text-decoration:none; font-size:14px; line-height:1.45; }
    .news-meta { color:var(--muted); font-size:11px; margin-top:8px; }
    .news-row { padding:15px 0; border-bottom:1px solid var(--line); }
    .news-row:last-child { border-bottom:0; }
    .smallcaps { color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:10px; font-weight:800; }
    div[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px 18px; }
    div[data-testid="stMetricLabel"] { color:var(--muted); }
    div[data-testid="stMetricValue"] { font-family:var(--market-lens-font-financial,'DM Mono',monospace); }
    button[kind="primary"] { background:var(--mint); color:var(--app-bg); border:0; }
    .stTabs [data-baseweb="tab-list"] { gap:10px; background:color-mix(in srgb,var(--panel) 88%,transparent); padding:6px 10px; border:1px solid var(--line); border-radius:12px; }
    .stTabs [data-baseweb="tab"] { color:var(--muted); border-radius:9px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color:var(--mint); background:color-mix(in srgb,var(--mint) 12%,transparent); }
    div[data-testid="stVerticalBlockBorderWrapper"] { background:color-mix(in srgb,var(--panel) 92%,transparent); border-color:var(--line); border-radius:18px; padding:18px 20px; margin:10px 0 22px; box-shadow:0 10px 28px rgba(0,0,0,.08); }
    div[data-testid="stVerticalBlockBorderWrapper"] h2 { margin-top:0; }
    div[data-testid="stVerticalBlockBorderWrapper"] h3 { margin-top:8px; }
    .st-key-market_lens_ai_helper { position:fixed !important; right:20px !important; bottom:20px !important; width:min(390px, calc(100vw - 24px)) !important; z-index:999999 !important; margin:0 !important; }
    .st-key-market_lens_ai_helper iframe { width:100% !important; border:0 !important; background:transparent !important; }
    .company-header { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:18px 28px; align-items:center; padding:20px 22px; margin:8px 0 22px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(135deg,color-mix(in srgb,var(--panel) 93%,var(--mint) 7%),var(--panel)); }
    .company-identity h2 { margin:3px 0 6px; font-size:clamp(22px,2.2vw,30px); letter-spacing:-.035em; }
    .company-ticker { display:inline-block; margin-left:8px; padding:3px 8px; border:1px solid var(--line); border-radius:8px; color:var(--mint); font:600 .56em var(--market-lens-font-financial,monospace); vertical-align:middle; letter-spacing:0; }
    .company-meta { color:var(--muted); font-size:13px; line-height:1.55; }
    .company-price-block { min-width:175px; text-align:right; }
    .company-price { color:var(--ink); font:600 clamp(24px,2.4vw,32px) var(--market-lens-font-financial,monospace); font-variant-numeric:tabular-nums; margin:2px 0; }
    .company-change { font-weight:750; font-variant-numeric:tabular-nums; }
    .company-change.positive { color:var(--bull); }
    .company-change.negative { color:var(--bear); }
    .company-change.neutral { color:var(--muted); }
    .company-freshness { grid-column:1/-1; display:flex; flex-wrap:wrap; gap:5px 12px; padding-top:11px; border-top:1px solid var(--line); color:var(--muted); font-size:11px; line-height:1.5; }
    .freshness-label { color:var(--ink); font-weight:700; }
    .section-heading { margin:4px 0 14px; }
    .section-heading h2 { margin:2px 0 4px; font-size:22px; letter-spacing:-.03em; }
    .section-eyebrow { color:var(--muted); font-size:10px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .section-description { color:var(--muted); font-size:13px; line-height:1.5; }
    .metric-card { min-height:126px; display:flex; flex-direction:column; }
    .metric-card.positive { border-top:2px solid var(--bull); }
    .metric-card.negative { border-top:2px solid var(--bear); }
    .metric-card.accent { border-top:2px solid var(--mint); }
    .metric-value { font-variant-numeric:tabular-nums; }
    .metric-note { line-height:1.45; }
    .st-key-market_chart_shell [data-testid="stVerticalBlockBorderWrapper"] { padding:20px clamp(14px,2vw,28px); }
    .st-key-market_chart_shell [data-testid="stPlotlyChart"] { margin-top:4px; }
    .st-key-market_snapshot_metrics [data-testid="stVerticalBlockBorderWrapper"] { margin-top:0; }
    .chart-control-caption { margin:10px 0 3px; color:var(--muted); font-size:10px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    .st-key-market_chart_controls { padding:12px 14px 8px; margin:8px 0 12px; border:1px solid var(--line); border-radius:12px; background:color-mix(in srgb,var(--panel) 88%,transparent); }
    .st-key-market_chart_controls [data-testid="stRadio"] div[role="radiogroup"] { display:flex; flex-wrap:wrap; gap:5px 9px; }
    .st-key-market_snapshot_metrics [data-testid="stHorizontalBlock"], .st-key-market_pulse_metrics [data-testid="stHorizontalBlock"] { align-items:stretch; }
    .st-key-research_indicator_groups [data-testid="stHorizontalBlock"] { align-items:flex-start; }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    .news-row { position:relative; padding:15px 16px; margin:10px 0; border:1px solid var(--line); border-radius:13px; background:color-mix(in srgb,var(--panel) 92%,transparent); }
    .news-title { display:block; padding-right:4px; font-size:15px; line-height:1.5; }
    .news-meta { line-height:1.8; }
    .news-source-link { display:inline-flex; margin-top:5px; color:var(--mint); font-weight:700; text-decoration:none; }
    .news-source-link:hover,.news-source-link:focus-visible { text-decoration:underline; outline:2px solid var(--mint); outline-offset:2px; }
    .news-source-link.unavailable { color:var(--muted); font-weight:500; }
    .market-data-note { padding:9px 12px; border-left:3px solid var(--mint); border-radius:0 9px 9px 0; background:color-mix(in srgb,var(--panel) 90%,transparent); color:var(--muted); font-size:12px; line-height:1.5; }
    @media (max-width: 900px) {
      .st-key-market_chart_controls [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 12px; }
      .st-key-market_chart_controls [data-testid="stHorizontalBlock"] > div { width:100% !important; min-width:0 !important; }
      .st-key-market_snapshot_metrics [data-testid="stHorizontalBlock"], .st-key-market_pulse_metrics [data-testid="stHorizontalBlock"], .st-key-research_indicator_groups [data-testid="stHorizontalBlock"], .st-key-research_fundamental_groups [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
      .st-key-market_snapshot_metrics [data-testid="stHorizontalBlock"] > div, .st-key-market_pulse_metrics [data-testid="stHorizontalBlock"] > div, .st-key-research_indicator_groups [data-testid="stHorizontalBlock"] > div, .st-key-research_fundamental_groups [data-testid="stHorizontalBlock"] > div { width:100% !important; min-width:0 !important; }
    }
    @media (max-width: 640px) {
      [data-testid="stMainBlockContainer"] { padding:12px 12px 48px; }
      .workspace-heading { padding:4px 0 14px; margin:0 0 14px; }
      .workspace-eyebrow { font-size:9px; letter-spacing:.1em; line-height:1.5; }
      .workspace-heading h1 { font-size:27px; margin:4px 0; }
      .workspace-heading p { font-size:13px; line-height:1.45; }
      .panel { padding:16px; border-radius:14px; }
      .st-key-market_chart_shell [data-testid="stVerticalBlockBorderWrapper"] { padding:12px 10px; }
      .st-key-market_chart_controls { padding:10px; margin:6px 0 10px; }
      .st-key-market_chart_controls [data-testid="stHorizontalBlock"] { gap:6px; }
      .st-key-market_chart_controls [data-testid="stRadio"] div[role="radiogroup"] { gap:4px 6px; }
      .st-key-market_chart_controls [data-testid="stRadio"] label { min-height:40px; }
      .st-key-market_chart_shell [data-testid="stPlotlyChart"] { max-width:100%; min-width:0; }
      .st-key-market_snapshot_metrics [data-testid="stHorizontalBlock"], .st-key-market_pulse_metrics [data-testid="stHorizontalBlock"] { grid-template-columns:minmax(0,1fr); gap:8px; }
      .st-key-market_snapshot_metrics .metric-card, .st-key-market_pulse_metrics .metric-card { min-height:0; }
      .st-key-market_snapshot_metrics .metric-value, .st-key-market_pulse_metrics .metric-value { font-size:23px; }
      .company-identity h2 { font-size:22px; }
      .company-price-block { min-width:0; text-align:left; }
      .news-row { padding:12px; margin:8px 0; }
      .news-title { font-size:14px; line-height:1.45; }
      .st-key-research_indicator_groups [data-testid="stHorizontalBlock"], .st-key-research_fundamental_groups [data-testid="stHorizontalBlock"] { gap:8px; }
      .st-key-research_indicator_groups .metric-card, .st-key-research_fundamental_groups .metric-card { min-height:0; }
      div[data-testid="stDataFrame"] { max-width:100%; min-width:0; overflow-x:auto; }
      .st-key-market_lens_workspace_nav label { min-height:42px; padding:8px 10px; }
      .stMainBlockContainer [data-testid="stSelectbox"] [data-baseweb="select"] > div,
      .stMainBlockContainer [data-testid="stButton"] button { min-height:42px; }
      .stMainBlockContainer [data-testid="stExpander"] summary { min-height:44px; }
      .st-key-market_lens_ai_helper { right:10px !important; bottom:10px !important; }
      .company-header { grid-template-columns:minmax(0,1fr); gap:10px; padding:14px; margin:4px 0 14px; }
      .company-price-block { text-align:left; }
      .company-freshness { grid-column:auto; flex-direction:column; gap:2px; padding-top:8px; }
      .section-heading h2 { font-size:20px; }
      .st-key-market_chart_controls [data-testid="stHorizontalBlock"] { grid-template-columns:minmax(0,1fr); }
      .st-key-research_indicator_groups [data-testid="stHorizontalBlock"], .st-key-research_fundamental_groups [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:minmax(0,1fr); gap:12px; }
      .st-key-research_indicator_groups [data-testid="stHorizontalBlock"] > div, .st-key-research_fundamental_groups [data-testid="stHorizontalBlock"] > div { width:100% !important; min-width:0 !important; }
      .stTabs [data-baseweb="tab-list"] { gap:4px; overflow-x:auto; }
      .stTabs [data-baseweb="tab"] { min-height:42px; font-size:12px; }
      .company-freshness,.news-meta { overflow-wrap:anywhere; }
    }
    @media (max-width: 430px) {
      [data-testid="stMainBlockContainer"] { padding-left:10px; padding-right:10px; }
      .st-key-market_chart_shell [data-testid="stVerticalBlockBorderWrapper"] { padding:10px 8px; }
      .workspace-heading h1 { font-size:25px; }
      .st-key-market_lens_ai_helper { right:8px !important; bottom:8px !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<style>" + app_background_css() + "</style>", unsafe_allow_html=True)

def as_float(value, default=np.nan):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tab_is_active(tab) -> bool:
    """Return whether a state-tracked Streamlit tab is the selected tab."""
    return bool(getattr(tab, "open", False))


def load_tab_data_if_active(tab, loader, inactive_value=None):
    """Avoid invoking provider work for a tab that is not currently open."""
    return loader() if tab_is_active(tab) else inactive_value


def preserve_workspace_widget_state() -> None:
    """Streamlit callback for saving the current view before branch changes."""
    save_workspace_widget_state(st.session_state)


@st.cache_data(ttl=3600, show_spinner=False)
def search_tickers(query: str) -> list[dict]:
    query = query.strip()
    if len(query) < 2:
        return []
    try:
        quotes = yf.Search(query, max_results=12, news_count=0, lists_count=0,
                           include_cb=False, include_nav_links=False, raise_errors=False).quotes
    except Exception:
        return []
    matches = []
    for quote in quotes or []:
        if quote.get("quoteType") not in ("EQUITY", "ETF"):
            continue
        symbol = quote.get("symbol")
        if not symbol:
            continue
        name = quote.get("shortname") or quote.get("longname") or symbol
        exchange = quote.get("exchDisp") or quote.get("exchange") or ""
        matches.append({"symbol":symbol, "name":name, "exchange":exchange,
                        "label":f"{symbol} · {name} · {exchange}".strip(" ·")})
    return matches


@st.cache_data(ttl=1800, show_spinner=False)
def load_profile(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).get_info()
    except Exception:
        info = {}
    return {"name":info.get("shortName") or info.get("longName") or symbol,
            "sector":info.get("sector") or "Unclassified",
            "industry":info.get("industry") or "Unclassified"}


def add_symbol_to_watchlist(symbol: str) -> None:
    normalized = str(symbol).strip().upper()
    current = [part.strip().upper() for part in st.session_state.get("watchlist_input", "").split(",") if part.strip()]
    if not normalized:
        return
    if normalized in current:
        st.session_state["watchlist_action_notice"] = ("info", f"{normalized} is already in your watchlist.")
    elif len(current) >= MAX_WATCHLIST_SIZE:
        st.session_state["watchlist_action_notice"] = ("warning", f"Your watchlist is full ({MAX_WATCHLIST_SIZE} tickers). Remove a ticker to add another.")
    else:
        current.append(normalized)
        st.session_state["watchlist_input"] = ", ".join(current)
        save_user_watchlist(current)
        st.session_state["watchlist_action_notice"] = ("success", f"Added {normalized} to your watchlist.")
    if normalized in current:
        st.session_state["focus_ticker"] = normalized


def persist_watchlist_input() -> None:
    symbols = [part.strip().upper() for part in st.session_state.get("watchlist_input", "").split(",") if part.strip()]
    save_user_watchlist(symbols[:MAX_WATCHLIST_SIZE])


def load_user_watchlist() -> list[str]:
    if HOSTED_MODE:
        saved = st.session_state.get("market_lens_saved_watchlist")
        if isinstance(saved, list) and saved:
            return saved[:MAX_WATCHLIST_SIZE]
        return DEFAULT_WATCHLIST.copy()
    return load_watchlist()


def save_user_watchlist(symbols: list[str]) -> None:
    cleaned = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))[:MAX_WATCHLIST_SIZE]
    if HOSTED_MODE:
        st.session_state["market_lens_saved_watchlist"] = cleaned
    else:
        save_watchlist(cleaned)


@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(symbol: str) -> dict:
    """Load inputs required by the selected-ticker snapshot and signal."""
    ticker = yf.Ticker(symbol)
    history_result = YahooFinanceProvider().history(symbol, period="2y", interval="1d")
    history = history_result.data
    if history.empty:
        raise ValueError(history_result.warning or f"No price history returned for {symbol}. Check the ticker and try again.")
    optional_warnings = []
    try:
        raw_info = ticker.get_info()
    except Exception as exc:
        LOGGER.warning("Yahoo Finance company profile request failed for %s (%s)",
                       symbol, type(exc).__name__, exc_info=True)
        raw_info = None
        profile_status = "error"
        optional_warnings.append("Company profile data could not be retrieved.")
    else:
        profile_status = "available"
    if isinstance(raw_info, dict):
        info = raw_info
        if not info:
            profile_status = "missing"
            optional_warnings.append("Yahoo Finance returned no company profile data.")
    elif raw_info is None and profile_status != "error":
        info = {}
        profile_status = "missing"
        optional_warnings.append("Yahoo Finance returned no company profile data.")
    else:
        info = {}
        if profile_status != "error":
            profile_status = "malformed"
            LOGGER.warning("Yahoo Finance company profile response had an unexpected type for %s: %s",
                           symbol, type(raw_info).__name__)
            optional_warnings.append("Company profile data was returned in an unsupported format.")
    # These recommendations feed the visible snapshot rating, and options
    # volatility feeds its expected-move card; retain both on the core path.
    recommendation_result = load_analyst_recommendation_result(symbol)
    recommendations = recommendation_result["data"]
    if recommendation_result["status"] == "error":
        optional_warnings.append(recommendation_result["message"])
    options_move = None
    options_expiry = None
    try:
        expiries = ticker.options
        if expiries:
            target = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=30)).date()
            expiry = min(expiries, key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d").date() - target).days))
            chain = ticker.option_chain(expiry)
            spot = float(history["Close"].iloc[-1])
            candidates = []
            for frame in (chain.calls, chain.puts):
                if not frame.empty and "impliedVolatility" in frame:
                    frame = frame.copy()
                    frame["distance"] = (frame["strike"] - spot).abs()
                    candidates.extend(frame.nsmallest(3, "distance")["impliedVolatility"].dropna().tolist())
            candidates = [x for x in candidates if 0.02 < x < 4]
            if candidates:
                iv = float(np.median(candidates))
                # IV is annualized; report a consistent 30-calendar-day range.
                options_move = iv * np.sqrt(30 / 365)
                options_expiry = expiry
    except Exception:
        pass
    return {"history": history, "history_result": history_result, "info": info,
            "optional_warnings":optional_warnings, "options_move": options_move,
            "options_expiry": options_expiry, "recommendations": recommendations,
            "recommendation_status":recommendation_result["status"],
            "recommendation_message":recommendation_result["message"],
            "profile_status":profile_status}


@st.cache_data(ttl=300, show_spinner=False)
def load_ticker_news(symbol: str) -> tuple[list[dict], str | None]:
    """Fetch headlines only for the headline section, not the ticker snapshot."""
    try:
        result = yf.Ticker(symbol).get_news(count=12)
    except Exception as exc:
        LOGGER.warning("Yahoo Finance headlines request failed for %s (%s)",
                       symbol, type(exc).__name__, exc_info=True)
        return [], "Recent headlines could not be retrieved."
    if result is None:
        return [], None
    if not isinstance(result, list):
        LOGGER.warning("Yahoo Finance headlines response had an unexpected type for %s: %s",
                       symbol, type(result).__name__)
        return [], "Recent headlines were returned in an unsupported format."
    return result, None


def _provider_failure_message(label: str) -> str:
    return f"{label} could not be retrieved from Yahoo Finance."


@st.cache_data(ttl=300, show_spinner=False)
def load_company_fundamentals(symbol: str) -> dict[str, object]:
    """Load statement rows only when the Business & valuation tab is opened."""
    try:
        statement = yf.Ticker(symbol).quarterly_income_stmt
    except Exception as exc:
        LOGGER.warning("Yahoo Finance quarterly income statement request failed for %s (%s)",
                       symbol, type(exc).__name__, exc_info=True)
        return {"data":None, "status":"error",
                "message":_provider_failure_message("Quarterly income statement data")}
    if statement is None or isinstance(statement, pd.DataFrame) and statement.empty:
        return {"data":None, "status":"missing", "message":None}
    if not isinstance(statement, pd.DataFrame):
        LOGGER.warning("Yahoo Finance quarterly income statement had an unexpected type for %s: %s",
                       symbol, type(statement).__name__)
        return {"data":None, "status":"malformed",
                "message":"Quarterly income statement data was returned in an unsupported format."}
    return {"data":statement, "status":"available", "message":None}


@st.cache_data(ttl=300, show_spinner=False)
def load_company_catalysts(symbol: str) -> dict[str, object]:
    """Load analyst, earnings, and filing research only when requested."""
    ticker = yf.Ticker(symbol)
    result: dict[str, object] = {
        "earnings_dates":None, "analyst_targets":None, "eps_revisions":None,
        "sec_filings":None, "upgrades":None, "_errors":{}, "_missing":[],
    }
    requests = (
        ("earnings_dates", lambda: ticker.get_earnings_dates(limit=8), pd.DataFrame),
        ("analyst_targets", lambda: ticker.analyst_price_targets, Mapping),
        ("eps_revisions", ticker.get_eps_revisions, pd.DataFrame),
        ("sec_filings", ticker.get_sec_filings, (pd.DataFrame, list, dict)),
        ("upgrades", ticker.get_upgrades_downgrades, pd.DataFrame),
    )
    for key, fetch, expected_type in requests:
        try:
            value = fetch()
        except Exception as exc:
            LOGGER.warning("Yahoo Finance research request %s failed for %s (%s)",
                           key, symbol, type(exc).__name__, exc_info=True)
            result["_errors"][key] = _provider_failure_message(
                {"earnings_dates":"Earnings dates", "analyst_targets":"Analyst targets",
                 "eps_revisions":"EPS revisions", "sec_filings":"SEC filings",
                 "upgrades":"Analyst rating changes"}[key]
            )
            continue
        if value is None or (isinstance(value, (pd.DataFrame, dict, list)) and len(value) == 0):
            result["_missing"].append(key)
            continue
        if not isinstance(value, expected_type):
            LOGGER.warning("Yahoo Finance research response %s had an unexpected type for %s: %s",
                           key, symbol, type(value).__name__)
            result["_errors"][key] = f"{key.replace('_', ' ').capitalize()} data was returned in an unsupported format."
            continue
        result[key] = value
    return result


@st.cache_data(ttl=300, show_spinner=False)
def load_benchmark() -> pd.DataFrame:
    return yf.Ticker("SPY").history(period="6mo", interval="1d", auto_adjust=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_snapshot(symbol: str):
    return YahooFinanceProvider().history(symbol, period="2y", interval="1d")


@st.cache_data(ttl=300, show_spinner=False)
def load_analyst_recommendation_result(symbol: str) -> dict[str, object]:
    try:
        recommendations = yf.Ticker(symbol).get_recommendations_summary()
    except Exception as exc:
        LOGGER.warning("Yahoo Finance analyst recommendation request failed for %s (%s)",
                       symbol, type(exc).__name__, exc_info=True)
        return {"data":None, "status":"error",
                "message":"Analyst recommendation data could not be retrieved."}
    if recommendations is None or isinstance(recommendations, pd.DataFrame) and recommendations.empty:
        return {"data":None, "status":"missing", "message":None}
    if not isinstance(recommendations, pd.DataFrame) or recommendation_distribution(recommendations) is None:
        LOGGER.warning("Yahoo Finance analyst recommendation response was malformed for %s", symbol)
        return {"data":None, "status":"malformed",
                "message":"Analyst recommendation data was returned in an unsupported format."}
    return {"data":recommendations, "status":"available", "message":None}


@st.cache_data(ttl=300, show_spinner=False)
def load_analyst_recommendations(symbol: str) -> pd.DataFrame | None:
    return load_analyst_recommendation_result(symbol)["data"]


@st.cache_data(ttl=900, show_spinner=False)
def load_chart_history(symbol: str, interval: str) -> tuple[pd.DataFrame, str | None]:
    """Load chart-specific bars without shortening the snapshot's daily history."""
    provider_intervals = {
        "15 minute":"15m", "30 minute":"30m", "1 hour":"1h", "1 day":"1d",
    }
    try:
        ticker = yf.Ticker(symbol)
        intraday_end = date.today() + timedelta(days=1)
        intraday_start = intraday_end - timedelta(days=60)
        if interval == "1 day":
            history = ticker.history(period="max", interval="1d", auto_adjust=True)
        elif interval in {"2 hours", "12 hours"}:
            hourly = ticker.history(start=intraday_start, end=intraday_end, interval="1h",
                                    auto_adjust=True, prepost=False)
            if hourly.empty:
                return pd.DataFrame(), "Yahoo Finance returned no hourly bars for this ticker."
            hours = 2 if interval == "2 hours" else 12
            aggregations = {column:operation for column, operation in {
                "Open":"first", "High":"max", "Low":"min", "Close":"last", "Volume":"sum",
            }.items() if column in hourly.columns}
            history = hourly.resample(
                f"{hours}h", origin="start_day", offset="9h30min", label="left", closed="left",
            ).agg(aggregations).dropna(subset=["Close"])
        else:
            provider_interval = provider_intervals.get(interval)
            if provider_interval is None:
                return pd.DataFrame(), f"Unsupported chart interval: {interval}."
            history = ticker.history(start=intraday_start, end=intraday_end, interval=provider_interval,
                                     auto_adjust=True, prepost=False)
        if history.empty:
            return pd.DataFrame(), f"Yahoo Finance returned no {interval} chart data for {symbol}."
        return history, None
    except Exception as exc:
        return pd.DataFrame(), f"{type(exc).__name__}: {str(exc)[:180]}"


@st.cache_data(ttl=300, show_spinner=False)
def load_market_context() -> dict:
    symbols = ["SPY", "QQQ", "IWM", "DIA", "^VIX", "^TNX", *SECTORS.values()]
    results = YahooFinanceProvider().histories(symbols, period="2y", interval="1d")
    context = {symbol: result.data for symbol, result in results.items() if not result.data.empty}
    context["_metadata"] = results
    return context


def clear_selected_ticker_data(symbol: str) -> None:
    """Clear cached data for one ticker without invalidating shared app caches."""
    cached_functions = {
        "load_market_data":load_market_data,
        "load_ticker_news":load_ticker_news,
        "load_company_fundamentals":load_company_fundamentals,
        "load_company_catalysts":load_company_catalysts,
        "load_snapshot":load_snapshot,
        "load_profile":load_profile,
        "load_analyst_recommendations":load_analyst_recommendations,
        "load_analyst_recommendation_result":load_analyst_recommendation_result,
        "load_chart_history":load_chart_history,
    }
    invalidate_ticker_caches(symbol, cached_functions)


@st.cache_data(ttl=86400, show_spinner=False)
def load_industry_index() -> pd.DataFrame:
    rows = []
    # Prefer the live industry key returned by Yahoo. Industry display names
    # cannot safely be converted to keys for the company-list request.
    sector_labels = {
        "technology":"Technology", "communication-services":"Communication Services",
        "consumer-cyclical":"Consumer Cyclical", "consumer-defensive":"Consumer Defensive",
        "energy":"Energy", "financial-services":"Financial Services", "healthcare":"Healthcare",
        "industrials":"Industrials", "basic-materials":"Basic Materials",
        "real-estate":"Real Estate", "utilities":"Utilities",
    }
    for sector_key in SECTOR_KEYS:
        try:
            sector = yf.Sector(sector_key)
            industries = sector.industries
            if not isinstance(industries, pd.DataFrame) or industries.empty:
                LOGGER.info("Yahoo Finance returned an empty industry directory for sector key %r", sector_key)
                continue
            sector_name = provider_text(sector.name) or sector_labels.get(
                sector_key, sector_key.replace("-", " ").title()
            )
            for idx, row in industries.iterrows():
                industry_key = provider_text(row.get("key")) or provider_text(row.get("industryKey"))
                # yfinance 1.x currently exposes canonical keys as the index;
                # reject numeric row positions rather than treating them as keys.
                if not industry_key:
                    index_key = provider_text(idx)
                    if index_key and not index_key.isdecimal():
                        industry_key = index_key
                industry_name = provider_text(row.get("name")) or provider_text(row.get("industryName"))
                if not industry_key or industry_key.isdecimal():
                    LOGGER.warning("Yahoo Finance returned an industry without a canonical key for sector %r", sector_key)
                    continue
                if not industry_name:
                    LOGGER.warning(
                        "Yahoo Finance returned an industry without a display name for sector %r and key %r",
                        sector_key, industry_key,
                    )
                    continue
                rows.append({"industry_key":industry_key, "industry":industry_name,
                             "sector_key":sector_key, "sector":sector_name, "source":"Yahoo Finance"})
        except Exception as exc:
            LOGGER.warning("Yahoo Finance sector industries request failed for %r (%s): %s",
                           sector_key, type(exc).__name__, str(exc)[:240])
            continue

    # The package supplies display names and candidate keys. Match each name
    # against its key list; company requests verify the key against live metadata.
    local_rows = canonical_local_industry_rows(
        SECTOR_INDUSTY_MAPPING, SECTOR_INDUSTY_MAPPING_LC, sector_labels,
    )
    known_industries = {
        (item["sector_key"].casefold(), industry_identity(item["industry"]))
        for item in rows
    }
    rows.extend(
        item for item in local_rows
        if (item["sector_key"].casefold(), industry_identity(item["industry"])) not in known_industries
    )

    return pd.DataFrame(rows).drop_duplicates(subset=["industry_key"]) if rows else pd.DataFrame(columns=["industry_key","industry","sector_key","sector","source"])


class _TransientIndustryProviderError(RuntimeError):
    """Marks an unsuccessful provider result so it is not kept in the long cache."""


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_industry_companies_cached(industry_key: str, industry_source: str, sector_key: str,
                                     industry_name: str, sector_name: str) -> tuple[pd.DataFrame, str | None]:
    """Short-cache all outcomes so temporary failures do not trigger rerun request storms."""
    canonical_keys = tuple(
        key for industry_keys in SECTOR_INDUSTY_MAPPING_LC.values()
        for key in industry_keys
    )
    return fetch_industry_companies(
        industry_key, industry_source, sector_key, industry_name, sector_name,
        industry_factory=yf.Industry, sector_factory=yf.Sector, ticker_factory=yf.Ticker,
        canonical_keys=canonical_keys, valid_sector_keys=SECTOR_KEYS,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def _load_successful_industry_companies_cached(industry_key: str, industry_source: str, sector_key: str,
                                               industry_name: str, sector_name: str) -> tuple[pd.DataFrame, str | None]:
    """Keep successful/valid-empty company results warm for one hour, not provider failures."""
    companies, error = _fetch_industry_companies_cached(
        industry_key, industry_source, sector_key, industry_name, sector_name,
    )
    if companies.empty and error:
        raise _TransientIndustryProviderError(error)
    return companies, error


def load_industry_companies(industry_key: str, industry_source: str, sector_key: str,
                            industry_name: str, sector_name: str) -> tuple[pd.DataFrame, str | None]:
    """Return validated companies; provider failures retry after a short cooldown."""
    try:
        return _load_successful_industry_companies_cached(
            industry_key, industry_source, sector_key, industry_name, sector_name,
        )
    except _TransientIndustryProviderError as exc:
        return pd.DataFrame(), str(exc)


def _clear_industry_company_caches(*args) -> None:
    _load_successful_industry_companies_cached.clear(*args)
    _fetch_industry_companies_cached.clear(*args)


# Preserve the cache-clear interface used by targeted ticker/Discovery tests.
load_industry_companies.clear = _clear_industry_company_caches


@st.cache_data(ttl=1800, show_spinner=False)
def rate_industry_companies(symbols: tuple[str, ...]) -> dict[str, str]:
    """Use analyst consensus as the headline rating, with a technical fallback."""
    if not symbols:
        return {}
    try:
        histories = YahooFinanceProvider().histories(list(symbols), period="2y", interval="1d")
        benchmark = load_benchmark()
    except Exception:
        return {symbol:"Unavailable" for symbol in symbols}

    def fetch_recommendations(symbol: str):
        return load_analyst_recommendations(symbol)

    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as executor:
        recommendation_frames = list(executor.map(fetch_recommendations, symbols))
    ratings = {}
    for symbol, recommendations in zip(symbols, recommendation_frames):
        result = histories.get(symbol)
        if result is None or result.data.empty:
            ratings[symbol] = "Unavailable"
            continue
        try:
            ratings[symbol] = analyze(result.data, {}, None, benchmark, recommendations).get("rating", "Unavailable")
        except Exception:
            ratings[symbol] = "Unavailable"
    return ratings


@st.cache_data(ttl=900, show_spinner=False)
def load_upcoming_events(start_date: date, end_date: date,
                         watchlist_symbols: tuple[str, ...] = (),
                         sections: tuple[str, ...] = ("Earnings", "IPOs", "Splits", "Economic events")) -> dict[str, object]:
    results: dict[str, object] = {
        "Earnings":pd.DataFrame(), "IPOs":pd.DataFrame(), "Splits":pd.DataFrame(),
        "Economic events":pd.DataFrame(), "_errors":{}, "_earnings_fallback":False,
    }
    errors: dict[str, str] = {}
    requested = set(sections)
    if requested:
        try:
            calendar = yf.Calendars(start=start_date, end=end_date)
        except Exception as exc:
            calendar = None
            errors["Calendar"] = f"{type(exc).__name__}: {str(exc)[:180]}"

        if calendar is not None:
            requests = {
                "Earnings":lambda:calendar.get_earnings_calendar(start=start_date, end=end_date, limit=100, filter_most_active=False),
                "IPOs":lambda:calendar.get_ipo_info_calendar(start=start_date, end=end_date, limit=100),
                "Splits":lambda:calendar.get_splits_calendar(start=start_date, end=end_date, limit=100),
                "Economic events":lambda:calendar.get_economic_events_calendar(start=start_date, end=end_date, limit=100),
            }
            for label, fetch in requests.items():
                if label not in requested:
                    continue
                try:
                    data = fetch()
                    results[label] = data if isinstance(data, pd.DataFrame) else pd.DataFrame()
                except Exception as exc:
                    errors[label] = f"{type(exc).__name__}: {str(exc)[:180]}"

    # Keep an earnings view available for the user's own symbols if Yahoo's
    # market-wide calendar query is empty or unavailable.
    if "Earnings" in requested and isinstance(results["Earnings"], pd.DataFrame) and results["Earnings"].empty:
        fallback_frames = []
        for symbol in watchlist_symbols:
            try:
                frame = yf.Ticker(symbol).get_earnings_dates(limit=12)
                if not isinstance(frame, pd.DataFrame) or frame.empty:
                    continue
                frame = frame.reset_index()
                date_column = frame.columns[0]
                event_dates = pd.to_datetime(frame[date_column], errors="coerce", utc=True).dt.date
                frame = frame.loc[(event_dates >= start_date) & (event_dates <= end_date)].copy()
                if frame.empty:
                    continue
                frame = frame.rename(columns={date_column:"Event Date"})
                frame.insert(0, "Symbol", symbol)
                fallback_frames.append(frame)
            except Exception:
                continue
        if fallback_frames:
            results["Earnings"] = pd.concat(fallback_frames, ignore_index=True)
            results["_earnings_fallback"] = True

    results["_errors"] = errors
    return results


@st.dialog("Fullscreen market chart")
def show_fullscreen_chart(figure, symbol: str) -> None:
    st.markdown(
        "<style>div[role='dialog']{width:96vw!important;max-width:96vw!important;}"
        "div[role='dialog'] [data-testid='stVerticalBlock']{gap:.6rem;}</style>",
        unsafe_allow_html=True,
    )
    st.caption(f"{symbol} · interactive price, moving-average, and volume chart")
    figure.update_layout(height=760)
    st.plotly_chart(
        figure, use_container_width=True, key="market_chart_fullscreen_view",
        config={"displayModeBar":True, "displaylogo":False, "scrollZoom":True,
                "responsive":True, "modeBarButtonsToAdd":["drawline", "drawopenpath", "eraseshape"]},
    )

def run_app() -> None:
    configure_app()
    with st.sidebar:
        st.markdown('<a class="jujosmi-home-link" href="https://jujosmi.com" target="_blank" rel="noopener noreferrer" aria-label="Visit jujosmi.com"><img src="app/static/jujosmi-logo-simple-shadow.png" alt="Jujosmi"></a>', unsafe_allow_html=True)
        st.markdown('<div class="brand">◉ &nbsp; JUJOSMI TRADE</div>', unsafe_allow_html=True)
        initialize_workspace_state(st.session_state)
        with st.container(key="market_lens_workspace_nav"):
            st.caption("WORKSPACES")
            st.radio(
                "Workspace", WORKSPACES, key=WORKSPACE_KEY,
                label_visibility="collapsed", on_change=preserve_workspace_widget_state,
            )
        workspace = st.session_state[WORKSPACE_KEY]
        restore_workspace_widget_state(st.session_state, workspace)
        st.markdown("### Your watchlist")
        if "watchlist_input" not in st.session_state:
            st.session_state["watchlist_input"] = ", ".join(load_user_watchlist() or DEFAULT_WATCHLIST)
        action_notice = st.session_state.pop("watchlist_action_notice", None)
        if action_notice:
            notice_type, notice_text = action_notice
            getattr(st, notice_type)(notice_text)
        raw_symbols = st.text_input("Tickers", key="watchlist_input", on_change=persist_watchlist_input,
                                    help="Enter up to 8 symbols separated by commas.")
        symbols = list(dict.fromkeys(s.strip().upper() for s in raw_symbols.split(",") if s.strip()))[:MAX_WATCHLIST_SIZE]
        if not symbols:
            symbols = ["SPY"]
        st.caption(f"{len(symbols)} of {MAX_WATCHLIST_SIZE} ticker slots used")
        query = st.text_input("Search ticker or company", key="ticker_search_query", placeholder="Type 2+ letters…")
        if len(query.strip()) >= 2:
            suggestions = search_tickers(query)
            if suggestions:
                st.caption("Choose a result to add it and focus the dashboard on that ticker.")
                watchlist_full = len(symbols) >= MAX_WATCHLIST_SIZE
                for suggestion in suggestions[:8]:
                    symbol = str(suggestion["symbol"]).strip().upper()
                    already_added = symbol in symbols
                    button_label = f"{'✓' if already_added else '＋'} {symbol} · {suggestion['name']}"
                    st.button(
                        button_label, key=f"ticker_search_add_{symbol}",
                        on_click=add_symbol_to_watchlist, args=(symbol,),
                        disabled=already_added or watchlist_full, use_container_width=True,
                    )
                if watchlist_full:
                    st.caption("Your watchlist is full. Remove a ticker above to make room.")
            else:
                st.caption("No ticker matches found. You can still enter a symbol above.")
        focused = st.session_state.get("focus_ticker")
        if focused not in symbols:
            st.session_state["focus_ticker"] = symbols[0]
        selected = st.selectbox("Ticker to analyze", symbols, key="focus_ticker")
        st.markdown("---")
        st.markdown('<div class="smallcaps">Signal guide</div>', unsafe_allow_html=True)
        st.caption("Search by ticker or company name to add symbols. Buy / Hold / Sell is a rule-based technical screen, not personalized advice. Expected move is a volatility range, not a directional price target.")
        st.markdown("---")
        if st.button("↻  Refresh data", use_container_width=True):
            clear_selected_ticker_data(selected)
            st.rerun()
        st.caption("Data via Yahoo Finance · refreshed every 5 min")
        if HOSTED_MODE:
            st.caption("Hosted mode: your watchlist stays in this browser session and is not shared with other visitors.")

    workspace_descriptions = {
        "Market Overview":"Selected-ticker snapshot, price action, and broad-market conditions.",
        "Discovery":"Browse verified industry listings and upcoming market events.",
        "Company Research":"Explore technical, financial, analyst, and headline research for the selected ticker.",
        "Watchlist":"Compare the current watchlist and filter companies by industry.",
    }
    render_workspace_heading(
        workspace, workspace_descriptions[workspace],
        eyebrow="Jujosmi Trade · Professional intelligence, simplified",
    )

    payload = context = stats = history = info = history_meta = None
    if workspace_requires_ticker_data(workspace):
        try:
            with st.spinner(f"Researching {selected} and the broader market…"):
                payload = load_market_data(selected)
                context = load_market_context()
            history, info = payload["history"], payload["info"]
            stats = analyze(history, info, payload["options_move"], context.get("SPY"), payload.get("recommendations"))
            history_meta = payload["history_result"]
        except Exception:
            LOGGER.exception("Selected-ticker core research failed for %s", selected)
            st.error("Selected-ticker research could not be loaded. Use Refresh data and try again.")
            st.stop()

    if workspace_requires_ticker_data(workspace):
        history_meta = payload["history_result"]
        daily_move = stats.get("change")
        change_direction = True if np.isfinite(daily_move) and daily_move > 0 else False if np.isfinite(daily_move) and daily_move < 0 else None
        render_company_header(
            name=stats.get("name") or selected, symbol=selected,
            exchange=info.get("fullExchangeName") or info.get("exchange") or "Exchange unavailable",
            sector=info.get("sector") or "Sector unavailable",
            industry=info.get("industry") or "Industry unavailable",
            price=f"${stats['last']:,.2f}" if np.isfinite(stats.get("last", np.nan)) else "Unavailable",
            daily_change=f"{daily_move:+.2f}% today" if np.isfinite(daily_move) else "Daily change unavailable",
            change_positive=change_direction, source=history_meta.source,
            retrieved=history_meta.retrieved_at.astimezone().strftime("%Y-%m-%d %H:%M %Z"),
            interval=history_meta.interval, status=history_meta.status,
            latest_bar=history_meta.last_observation or "unavailable",
            quote_delay=history_meta.provider_delay,
        )
        if history_meta.warning:
            if history_meta.status == "partial":
                st.caption(f"Data note · {history_meta.warning}")
            else:
                st.warning(history_meta.warning)
        for warning in payload.get("optional_warnings", []):
            st.warning(warning)

    if workspace == "Market Overview":
        st.markdown('<div id="selected-ticker" class="section-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True, key="market_chart_shell"):
            render_section_heading("Price chart", "Historical price action with selectable interval, range, style, and moving averages.", "Primary view")
            interval_options = ["15 minute", "30 minute", "1 hour", "2 hours", "12 hours", "1 day"]
            with st.container(key="market_chart_controls"):
                chart_controls = st.columns([1.2, 1.15, 1.55, 1.05])
                with chart_controls[0]:
                    chart_interval = st.selectbox("Bar interval", interval_options, index=5, key="market_chart_interval")
                chart_window_options = (["1D", "5D", "1M", "2M", "Max"] if chart_interval != "1 day"
                                        else ["1M", "3M", "6M", "1Y", "2Y", "5Y", "Max"])
                default_window = "6M" if chart_interval == "1 day" else "5D"
                if st.session_state.get("market_chart_range") not in chart_window_options:
                    st.session_state["market_chart_range"] = default_window
                average_unit = "day" if chart_interval == "1 day" else "bar"
                average_options = [f"20 {average_unit}", f"50 {average_unit}", f"200 {average_unit}"]
                default_averages = average_options[:2]
                selected_averages = st.session_state.get("market_chart_averages")
                if selected_averages is None or not set(selected_averages).issubset(average_options):
                    st.session_state["market_chart_averages"] = default_averages
                with chart_controls[1]:
                    chart_type = st.selectbox("Chart style", ["Candles", "Line"], key="market_chart_style")
                with chart_controls[2]:
                    chart_averages = st.multiselect("Moving averages", average_options, key="market_chart_averages")
                with chart_controls[3]:
                    open_fullscreen = st.button("⛶ Fullscreen", key="market_chart_open_fullscreen", use_container_width=True)
                st.markdown('<div class="chart-control-caption">Visible period</div>', unsafe_allow_html=True)
                chart_window = st.radio(
                    "Chart period", chart_window_options, horizontal=True,
                    label_visibility="collapsed", key="market_chart_range",
                )
            st.markdown(f'<div class="smallcaps">Price action · {chart_window} · {chart_interval} · {chart_type.lower()}</div>', unsafe_allow_html=True)
            with st.spinner(f"Loading {chart_interval} chart data for {selected}…"):
                if chart_interval == "1 day" and chart_window not in {"5Y", "Max"}:
                    chart_history, chart_error = history, None
                else:
                    chart_history, chart_error = load_chart_history(selected, chart_interval)
            if chart_history.empty:
                st.warning(f"Chart data is unavailable: {chart_error or 'no rows were returned.'}")
            else:
                price_figure = price_chart(
                    chart_history, selected, light_mode=LIGHT_THEME, chart_type=chart_type,
                    window=chart_window, overlays=chart_averages, interval=chart_interval,
                )
                if chart_interval != "1 day":
                    st.caption("Intraday history is limited to about 60 days. 2-hour and 12-hour bars are aggregated from hourly data.")
                st.plotly_chart(
                    price_figure, use_container_width=True, key="market_chart_main",
                    config={"displayModeBar":True, "displaylogo":False, "scrollZoom":True,
                            "responsive":True, "modeBarButtonsToAdd":["drawline", "drawopenpath", "eraseshape"]},
                )
                if open_fullscreen:
                    show_fullscreen_chart(price_figure, selected)

        with st.container(border=True):
            render_section_heading("Selected ticker snapshot", f"{stats.get('name') or selected} ({selected})", "Key readings")
            with st.container(key="market_snapshot_metrics"):
                cols = st.columns(4)
                move_explanation = ("A one-standard-deviation 30-day range from " + stats["move_source"] + ". This describes possible variability, not whether price is expected to rise or fall.")
                trend_note = f"RSI {stats['rsi']:.0f} · 20d / 50d / 200d trend" if np.isfinite(stats['rsi']) else "RSI unavailable · trend windows require full history"
                technical_stats = {**stats, "rating":stats.get("technical_rating"), "analyst_rating":None}
                analyst_note = (f"Wall Street consensus: {stats['analyst_rating']} ({stats['analyst_count']} ratings)" if stats.get("analyst_rating")
                                else "Analyst consensus unavailable · technical screen shown")
                metrics = [
                    ("Last close", f"${stats['last']:,.2f}" if np.isfinite(stats['last']) else "Unavailable",
                     f"{stats['change']:+.2f}% today" if np.isfinite(stats['change']) else "Daily change unavailable",
                     "Latest adjusted daily closing price returned by the provider. Today's change compares it with the prior available daily close.",
                     "positive" if np.isfinite(stats["change"]) and stats["change"] > 0 else "negative" if np.isfinite(stats["change"]) and stats["change"] < 0 else "neutral"),
                    ("30-day expected range", f"±{stats['move']*100:.1f}%" if np.isfinite(stats['move']) else "Unavailable",
                     f"Non-directional volatility range · {stats['move_source']}", move_explanation, "accent"),
                    ("Trend read", stats["state"], trend_note, trend_explanation(stats), ""),
                    ("Jujosmi Trade technical rating", stats["technical_rating"],
                     f"{stats['constructive_checks']} constructive · {stats['caution_checks']} caution · {analyst_note}",
                     rating_explanation(technical_stats), "accent"),
                ]
                for col, (label, value, note, explanation, tone) in zip(cols, metrics):
                    with col:
                        render_metric_card(label, value, note, explanation, tone)

        with st.expander("Market read · trend, momentum, and volatility context", expanded=False):
            above20 = stats["last"] > stats["sma20"] if np.isfinite(stats["sma20"]) else None
            above50 = stats["last"] > stats["sma50"] if np.isfinite(stats["sma50"]) else None
            trend_text = f"Price is {'above' if above20 is True else 'below' if above20 is False else 'unavailable versus'} its 20 day average and {'above' if above50 is True else 'below' if above50 is False else 'unavailable versus'} its 50 day average. The trend read is {stats['state'].lower()}."
            if np.isfinite(stats["rsi"]) and stats["rsi"] >= 70: rsi_text = "Momentum is elevated (RSI above 70), which can accompany an extended move."
            elif np.isfinite(stats["rsi"]) and stats["rsi"] <= 30: rsi_text = "Momentum is subdued (RSI below 30); this alone does not signal a reversal."
            elif np.isfinite(stats["rsi"]): rsi_text = "Momentum is in a middle range based on the 14 day RSI."
            else: rsi_text = "Momentum is unavailable because there is not enough history for a 14 day RSI."
            move_low, move_high = ((stats["last"] * (1-stats["move"]), stats["last"] * (1+stats["move"]))
                                   if np.isfinite(stats["move"]) else (np.nan, np.nan))
            st.markdown(f"**Trend.** {trend_text}")
            st.markdown(f"**Momentum.** {rsi_text}")
            if np.isfinite(stats["move"]):
                st.markdown(f"**Volatility range.** A one standard deviation estimate puts the 30 day range around **${move_low:,.2f}–${move_high:,.2f}**. It describes uncertainty, not direction.")
            else:
                st.markdown("**Volatility range.** Unavailable because neither a usable options estimate nor a full realized-volatility window was returned.")
            if payload["options_expiry"]:
                st.caption(f"Options snapshot uses near-the-money implied volatility around {payload['options_expiry']}.")
            elif np.isfinite(stats["hist_vol"]):
                st.caption("Options implied volatility unavailable; expected range uses the trailing 30-session realized volatility estimate.")
            else:
                st.caption(f"Options implied volatility unavailable; only {stats['hist_vol_observations']} of 30 realized-volatility sessions are available.")

    if workspace == "Discovery":
        st.markdown('<div id="discovery-index" class="section-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("## Discovery index")
            st.markdown('<div class="sub">Browse the market by industry and keep an eye on upcoming company and market events.</div>', unsafe_allow_html=True)
            event_window = st.selectbox("Event window", [30, 60, 90], index=1, format_func=lambda days:f"Next {days} days", key="discovery_event_window")
            event_start = date.today()
            event_end = event_start + timedelta(days=event_window)
            index_tab, earnings_tab, ipo_tab, events_tab = st.tabs(
                ["Industry directory", "Earnings soon", "IPOs soon", "Other events"],
                key="discovery_index_tabs", on_change="rerun",
            )
            st.caption(f"Industry and calendar data: Yahoo Finance via yfinance · retrieved {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} · coverage and provider delay are not verified.")
            with index_tab:
                industry_index = load_tab_data_if_active(index_tab, load_industry_index, pd.DataFrame())
                if industry_index.empty:
                    st.info("Industry directory data is temporarily unavailable. Use ticker search or the watchlist industry filter in the meantime.")
                else:
                    industry_index = industry_index.sort_values(["sector", "industry"])
                    st.caption("Yahoo Finance supplies canonical industry keys; a local directory keeps categories searchable if that lookup is unavailable.")
                    industry_options = [
                        {"label":f"{row.industry} · {row.sector}", "industry":str(row.industry),
                         "sector":str(row.sector), "sector_key":str(row.sector_key),
                         "key":str(row.industry_key), "source":str(row.source)}
                        for row in industry_index.itertuples()
                    ]
                    search_query = st.text_input(
                        "Find an industry", key="industry_directory_search",
                        placeholder="Search industries or sectors…",
                        help="Search is separate from the scrollable industry button list below.",
                    ).strip().casefold()
                    visible_industries = [
                        option for option in industry_options
                        if not search_query or search_query in option["label"].casefold()
                    ]
                    available_keys = {option["key"] for option in industry_options}
                    industry_key = st.session_state.get("industry_directory_selection")
                    if industry_key not in available_keys:
                        industry_key = industry_options[0]["key"]
                        st.session_state["industry_directory_selection"] = industry_key
                    st.caption(f"{len(visible_industries)} industries match · choose one to update the directory")
                    if visible_industries:
                        with st.container(height=300, border=True):
                            industry_columns = st.columns(3)
                            for index, option in enumerate(visible_industries):
                                with industry_columns[index % len(industry_columns)]:
                                    if st.button(
                                        option["label"], key=f"industry_pick_{option['key']}",
                                        type="primary" if option["key"] == industry_key else "secondary",
                                        use_container_width=True,
                                    ):
                                        # Read the button's return value directly so the
                                        # selected company list updates in this rerun too.
                                        industry_key = option["key"]
                                        st.session_state["industry_directory_selection"] = industry_key
                    else:
                        st.info("No industries match that search. Try a different industry or sector name.")

                    selected_option = next(option for option in industry_options if option["key"] == industry_key)
                    industry_label = selected_option["label"]
                    st.markdown(f"**Selected industry:** {industry_label}")
                    with st.spinner(f"Loading companies in {selected_option['industry']}…"):
                        companies, company_error = load_industry_companies(
                            industry_key, selected_option["source"], selected_option["sector_key"],
                            selected_option["industry"], selected_option["sector"],
                        )
                    if companies.empty:
                        if company_error:
                            st.warning(company_error)
                        else:
                            st.caption("Yahoo Finance returned no company listings for this industry or its validated sector fallback.")
                    else:
                        if company_error:
                            st.warning(company_error)
                        company_display = companies.copy()
                        company_symbols = tuple(dict.fromkeys(
                            str(symbol).strip().upper() for symbol in companies.index
                            if str(symbol).strip() and str(symbol).casefold() != "nan"
                        ))
                        company_ratings = rate_industry_companies(company_symbols)
                        company_display.insert(
                            0, "Jujosmi Trade rating",
                            [company_ratings.get(str(symbol).strip().upper(), "Unavailable") for symbol in company_display.index],
                        )
                        st.dataframe(company_display, use_container_width=True)
                        st.caption("Company lists use Yahoo Finance's industry listings. If those are unavailable, Discovery shows only sector top companies whose Yahoo profile industryKey or exact industry and sector fields confirm the selected category. Jujosmi Trade ratings use analyst consensus (at least 3 ratings), then the snapshot's technical screen as fallback. Unavailable means required price history or benchmark data was incomplete.")
                        company_frame = companies.reset_index()
                        symbol_column = next((col for col in company_frame.columns if str(col).lower() in ("symbol", "ticker")), None)
                        name_column = next((col for col in company_frame.columns if str(col).lower() in ("name", "company", "shortname")), None)
                        if symbol_column:
                            company_rows = []
                            for _, row in company_frame.iterrows():
                                symbol = str(row[symbol_column]).strip()
                                if not symbol or symbol.casefold() == "nan":
                                    continue
                                name = str(row[name_column]).strip() if name_column else symbol
                                company_rows.append((symbol, name if name and name.casefold() != "nan" else symbol))
                            if company_rows:
                                st.markdown("**Add a company to your watchlist**")
                                with st.container(height=260, border=True):
                                    company_columns = st.columns(2)
                                    for index, (symbol, name) in enumerate(company_rows):
                                        with company_columns[index % len(company_columns)]:
                                            st.button(
                                                f"＋ {symbol} · {name}",
                                                key=f"industry_company_add_{industry_key}_{symbol}",
                                                use_container_width=True, on_click=add_symbol_to_watchlist,
                                                args=(symbol,),
                                            )
            with earnings_tab:
                upcoming_events = load_tab_data_if_active(
                    earnings_tab,
                    lambda: load_upcoming_events(event_start, event_end, tuple(symbols), ("Earnings",)),
                    {},
                )
                earnings = upcoming_events.get("Earnings", pd.DataFrame())
                calendar_errors = upcoming_events.get("_errors", {})
                if earnings.empty:
                    if "Earnings" in calendar_errors or "Calendar" in calendar_errors:
                        detail = calendar_errors.get("Earnings") or calendar_errors.get("Calendar")
                        st.warning(f"The earnings calendar could not be loaded: {detail}")
                    else:
                        st.info(f"No earnings dates were returned for the next {event_window} days.")
                else:
                    st.dataframe(earnings.reset_index() if earnings.index.name else earnings, use_container_width=True, hide_index=True)
                    if upcoming_events.get("_earnings_fallback"):
                        st.caption("The market-wide calendar was empty, so these dates are from the ticker calendars in your watchlist.")
                st.caption(f"This is an earnings-date calendar for the next {event_window} days. An earnings call may take place after the results release; confirm the call time on the company’s investor relations site.")
            with ipo_tab:
                upcoming_events = load_tab_data_if_active(
                    ipo_tab, lambda: load_upcoming_events(event_start, event_end, tuple(symbols), ("IPOs",)), {},
                )
                calendar_errors = upcoming_events.get("_errors", {})
                ipo_calendar = upcoming_events.get("IPOs", pd.DataFrame())
                if ipo_calendar.empty:
                    if "IPOs" in calendar_errors or "Calendar" in calendar_errors:
                        detail = calendar_errors.get("IPOs") or calendar_errors.get("Calendar")
                        st.warning(f"The IPO calendar could not be loaded: {detail}")
                    else:
                        st.info(f"No IPO listings were returned for the next {event_window} days.")
                    st.markdown("Check exchange calendars: [Nasdaq IPO calendar](https://www.nasdaq.com/market-activity/ipos) · [NYSE IPO filings](https://www.nyse.com/ipo-center/filings)")
                else:
                    st.dataframe(ipo_calendar.reset_index() if ipo_calendar.index.name else ipo_calendar, use_container_width=True, hide_index=True)
                st.caption("IPO dates, offer prices and share counts can be preliminary and may change. Confirm with the issuer’s filings and exchange notices.")
            with events_tab:
                upcoming_events = load_tab_data_if_active(
                    events_tab,
                    lambda: load_upcoming_events(event_start, event_end, tuple(symbols), ("Splits", "Economic events")),
                    {},
                )
                calendar_errors = upcoming_events.get("_errors", {})
                market_events = upcoming_events.get("Economic events", pd.DataFrame())
                splits = upcoming_events.get("Splits", pd.DataFrame())
                if not market_events.empty:
                    st.markdown("#### Economic calendar")
                    st.dataframe(market_events, use_container_width=True, hide_index=True)
                if not splits.empty:
                    st.markdown("#### Upcoming stock splits")
                    st.dataframe(splits.reset_index() if splits.index.name else splits, use_container_width=True, hide_index=True)
                if market_events.empty and splits.empty:
                    st.info(f"No other events were returned for the next {event_window} days.")
                st.caption("Event coverage varies by market and issuer. Dates are provided by Yahoo Finance and may be incomplete.")

    if workspace == "Market Overview":
        st.markdown('<div id="market-pulse" class="section-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            pulse_title, pulse_refresh = st.columns([5, 1])
            with pulse_title:
                render_section_heading("Market pulse", "Broad-market direction, volatility regime, and sector participation.")
            if pulse_refresh.button("↻ Refresh pulse", key="refresh_market_context", use_container_width=True):
                load_market_context.clear()
                load_benchmark.clear()
                st.rerun()
            context_meta = context.get("_metadata", {})
            status_counts = pd.Series([meta.status for meta in context_meta.values()]).value_counts().to_dict() if context_meta else {}
            st.caption(f"Broad-market source: Yahoo Finance via yfinance · retrieved {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} · daily interval · quality statuses: {status_counts or 'unavailable'} · quote delay is not verified by this provider")
            benchmarks = []
            for symbol, label in (("SPY","S&P 500"),("QQQ","Nasdaq 100"),("IWM","Small caps"),("DIA","Dow")):
                frame = context.get(symbol)
                if frame is not None and not frame.empty:
                    price = frame["Close"].dropna()
                    day_move = float(price.iloc[-1]) / float(price.iloc[-2]) - 1 if len(price) >= 2 else np.nan
                    month_move = float(price.iloc[-1]) / float(price.iloc[-22]) - 1 if len(price) >= 22 else np.nan
                    above_50 = float(price.iloc[-1]) > float(price.tail(50).mean()) if len(price) >= 50 else np.nan
                    metadata = context_meta.get(symbol)
                    benchmarks.append({"Market":label,"Ticker":symbol,"Last":float(price.iloc[-1]),"Day":day_move,"1 month":month_move,"Above 50d":above_50,
                                       "As of":pd.Timestamp(price.index[-1]).strftime("%Y-%m-%d"),
                                       "Data status":metadata.status if metadata else "unknown"})
            vix_frame = context.get("^VIX")
            vix_level = float(vix_frame["Close"].dropna().iloc[-1]) if vix_frame is not None and not vix_frame.empty else np.nan
            spy_frame = context.get("SPY")
            spy_trend = "unclear"
            if spy_frame is not None and len(spy_frame) >= 200:
                spy_close = spy_frame["Close"].dropna()
                spy_last = float(spy_close.iloc[-1]); spy50 = float(spy_close.tail(50).mean()); spy200 = float(spy_close.tail(200).mean())
                spy_trend = "above 50d and 200d averages; 50d above 200d" if spy_last > spy50 > spy200 else "below 50d and 200d averages; 50d below 200d" if spy_last < spy50 < spy200 else "mixed moving-average alignment"
            elif spy_frame is not None:
                spy_trend = "insufficient history for 200d trend"
            sector_rows = []
            spy1m = np.nan; spy3m = np.nan
            if spy_frame is not None and len(spy_frame) >= 64:
                _spyclose = spy_frame["Close"].dropna()
                spy1m = float(_spyclose.iloc[-1]) / float(_spyclose.iloc[-22]) - 1
                spy3m = float(_spyclose.iloc[-1]) / float(_spyclose.iloc[-64]) - 1
            for sector, symbol in SECTORS.items():
                frame = context.get(symbol)
                if frame is not None and len(frame) >= 64:
                    close = frame["Close"].dropna()
                    perf1m = float(close.iloc[-1]) / float(close.iloc[-22]) - 1
                    perf3m = float(close.iloc[-1]) / float(close.iloc[-64]) - 1
                    metadata = context_meta.get(symbol)
                    sector_rows.append({"Sector":sector,"ETF":symbol,"1 month":perf1m,"vs S&P 1m":perf1m-spy1m if np.isfinite(spy1m) else np.nan,"3 months":perf3m,"vs S&P 3m":perf3m-spy3m if np.isfinite(spy3m) else np.nan,"Above 50d":float(close.iloc[-1]) > float(close.tail(50).mean()),"As of":pd.Timestamp(close.index[-1]).strftime("%Y-%m-%d"),"Data status":metadata.status if metadata else "unknown"})
            sector_rows.sort(key=lambda x:x["vs S&P 1m"] if np.isfinite(x["vs S&P 1m"]) else -999, reverse=True)
            pos_breadth = sum(1 for row in sector_rows if row["1 month"] > 0)
            vix_text = f"{vix_level:.1f}" if np.isfinite(vix_level) else "Unavailable"
            vix_label = "elevated" if np.isfinite(vix_level) and vix_level >= 25 else "moderate" if np.isfinite(vix_level) and vix_level >= 18 else "calm" if np.isfinite(vix_level) else "unavailable"
            tnx_frame = context.get("^TNX")
            yield10 = float(tnx_frame["Close"].dropna().iloc[-1]) if tnx_frame is not None and not tnx_frame.empty else np.nan
            yield_text = f"{yield10:.2f}%" if np.isfinite(yield10) else "Unavailable"
            vix_meta, tnx_meta = context_meta.get("^VIX"), context_meta.get("^TNX")
            vix_asof = pd.Timestamp(vix_frame["Close"].dropna().index[-1]).strftime("%Y-%m-%d") if vix_frame is not None and not vix_frame.empty else "unavailable"
            tnx_asof = pd.Timestamp(tnx_frame["Close"].dropna().index[-1]).strftime("%Y-%m-%d") if tnx_frame is not None and not tnx_frame.empty else "unavailable"
            vix_status = vix_meta.status if vix_meta else "unknown"
            tnx_status = tnx_meta.status if tnx_meta else "unknown"
            with st.container(key="market_pulse_metrics"):
                pulse_metrics = st.columns(4)
                cards = (
                    ("VIX · implied volatility", vix_text, f"{vix_label.title()} · {vix_asof} · {vix_status}",
                     "The VIX reflects options-implied, non-directional expected S&P 500 volatility over roughly 30 days. Its level does not indicate whether prices are expected to rise or fall."),
                    ("10-year Treasury proxy", yield_text, f"{tnx_asof} · {tnx_status}",
                     "Yahoo Finance's ^TNX quote is shown as a market proxy. It is not a direct Treasury yield quote."),
                    ("S&P 500 trend", spy_trend, "Daily ETF proxy · trend context", 
                     "The trend description compares SPY's last available close with its 50-session and 200-session averages; it is descriptive, not a forecast."),
                    ("Sector breadth", f"{pos_breadth} of {len(sector_rows)}", "Sectors with positive 1-month ETF return",
                     "Breadth counts available sector ETF rows with positive one-month returns. Sector ETFs are proxies and do not represent every constituent."),
                )
                for col, (label, value, note, explanation) in zip(pulse_metrics, cards):
                    with col:
                        render_metric_card(label, value, note, explanation, "accent")
            render_section_heading("Index performance", "Latest close, daily move, and one-month context for broad-market ETFs.")
            render_financial_table(
                pd.DataFrame(benchmarks),
                column_config={
                    "Last":st.column_config.NumberColumn(format="$%.2f"),
                    "Day":st.column_config.NumberColumn(format="%+.2f%%"),
                    "1 month":st.column_config.NumberColumn(format="%+.1f%%"),
                },
                key="market_pulse_index_table",
            )
            with st.expander("Sector rotation · 11 sector ETFs"):
                if sector_rows:
                    render_financial_table(
                        pd.DataFrame(sector_rows),
                        column_config={column:st.column_config.NumberColumn(format="%+.1f%%") for column in ("1 month","vs S&P 1m","3 months","vs S&P 3m")},
                        key="market_pulse_sector_table",
                    )
                    st.caption("Sector ETFs are proxies. Relative returns compare each sector ETF with SPY; this is not a complete measure of individual-stock market breadth.")
            st.caption("VIX reflects options-implied, non-directional 30-day S&P 500 volatility, not a forecast of whether the market will rise or fall. Its calm / moderate / elevated labels are rough display bands. [Cboe methodology](https://www.cboe.com/tradable_products/vix/faqs)")

            st.write("")
    if workspace == "Company Research":
        st.markdown('<div id="technical-analysis" class="section-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("## Company research")
            st.markdown('<div class="sub">Technical, business, analyst, event, and headline research for the selected company.</div>', unsafe_allow_html=True)
            tab_technical, tab_fundamentals, tab_catalysts, tab_headlines = st.tabs(
                ["Technical & relative strength", "Business & valuation", "Estimates, events & filings", "Headlines & sentiment"],
                key="research_desk_tabs", on_change="rerun",
            )
            with tab_technical:
                render_section_heading("Technical & relative strength", "Price structure, momentum, risk, and benchmark-relative performance.")
                tech_rows = [
                    ("Trend stack", stats["state"]),
                    ("20 day average", f"${stats['sma20']:,.2f} · {'price above' if stats['last'] > stats['sma20'] else 'price below'}" if np.isfinite(stats['sma20']) else "Unavailable · requires 20 closes"),
                    ("50 day average", f"${stats['sma50']:,.2f} · {'price above' if stats['last'] > stats['sma50'] else 'price below'}" if np.isfinite(stats['sma50']) else "Unavailable · requires 50 closes"),
                    ("200 day average", f"${stats['sma200']:,.2f} · {'price above' if stats['last'] > stats['sma200'] else 'price below'}" if np.isfinite(stats['sma200']) else "Unavailable · requires 200 closes"),
                    ("RSI (14)", f"{stats['rsi']:.1f} · {'overbought zone' if stats['rsi'] >= 70 else 'oversold zone' if stats['rsi'] <= 30 else 'middle range'}" if np.isfinite(stats['rsi']) else "Unavailable · requires 15 closes"),
                    ("MACD (12, 26, 9)", f"{'above' if stats['macd'] > stats['macd_signal'] else 'below'} signal · {stats['macd']:.2f}" if np.isfinite(stats['macd']) and np.isfinite(stats['macd_signal']) else "Unavailable · requires more history"),
                    ("Realized volatility", f"{stats['hist_vol']*100:.1f}% annualized · trailing 30 sessions" if np.isfinite(stats['hist_vol']) else f"Unavailable · {stats['hist_vol_observations']} of 30 sessions"),
                    ("Beta vs S&P 500", f"{stats['beta']:.2f}" if np.isfinite(stats["beta"]) else "Unavailable"),
                    ("52 week range", f"${stats['low52']:,.2f} – ${stats['high52']:,.2f}" if np.isfinite(stats['low52']) and np.isfinite(stats['high52']) else "Unavailable · requires 252 closes"),
                    ("Current drawdown from high", f"{stats['current_drawdown']:.1f}%" if np.isfinite(stats['current_drawdown']) else "Unavailable · requires 252 closes"),
                    ("Largest 1 year drawdown", f"{stats['drawdown']:.1f}%" if np.isfinite(stats['drawdown']) else f"Unavailable · {stats['drawdown_observations']} of 252 closes"),
                    ("Relative volume", f"{stats['relative_volume']:.2f}× 20 day median" if np.isfinite(stats["relative_volume"]) else "Unavailable"),
                ]
                readings = dict(tech_rows)
                groups = (
                    ("Trend & price structure", ("Trend stack", "20 day average", "50 day average", "200 day average", "52 week range", "Current drawdown from high")),
                    ("Momentum & volume", ("RSI (14)", "MACD (12, 26, 9)", "Relative volume")),
                    ("Risk & volatility", ("Realized volatility", "Beta vs S&P 500", "Largest 1 year drawdown")),
                )
                with st.container(key="research_indicator_groups"):
                    group_columns = st.columns(3)
                    for col, (title, labels) in zip(group_columns, groups):
                        with col:
                            st.markdown(f"#### {title}")
                            rows = [(label, readings[label]) for label in labels]
                            render_financial_table(pd.DataFrame(rows, columns=["Measure", "Reading"]), key=f"research_{title.casefold().replace(' ', '_').replace('&', 'and')}")
                render_section_heading("Performance vs S&P 500", "Provider-derived returns and excess return for the selected horizons.")
                rel_rows = [
                    {"Horizon":h.upper(), "Ticker return":r["asset"], "S&P 500":r["benchmark"], "Excess return":r["excess"]}
                    for h, r in stats["returns"].items()
                ]
                return_config = {column:st.column_config.NumberColumn(format="%+.1f%%") for column in ("Ticker return", "S&P 500", "Excess return")}
                render_financial_table(pd.DataFrame(rel_rows), column_config=return_config, key="research_relative_returns")
                positives = stats["constructive_checks"]
                risks = stats["caution_checks"]
                rating_coverage = "all required checks available" if stats["rating_checks_complete"] else "missing inputs prevent a rating"
                st.markdown(f"**Jujosmi Trade technical screen: {stats['technical_rating']}** · {positives} constructive checks vs {risks} caution checks · {rating_coverage}.")
                st.caption("This rule-based technical label is separate from Wall Street analyst consensus. Buy means at least 2 more constructive than caution checks; Sell means at least 2 more caution than constructive; Hold means the counts are within 1. All 10 checks must be available. It is not a forecast or a personal instruction to trade.")
                with st.expander("See the technical rating checks"):
                    check_rows = [
                        {"Side":check["side"], "Check":check["label"],
                         "Result":"Passed" if check["passed"] is True else "Not passed" if check["passed"] is False else "Unavailable"}
                        for check in stats.get("rating_check_details", [])
                    ]
                    render_financial_table(pd.DataFrame(check_rows), key="research_technical_rating_checks")
                    st.markdown("**Buy:** net score +2 or higher (constructive checks minus caution checks). **Hold:** net score −1, 0, or +1. **Sell:** net score −2 or lower. Each check has equal weight; a missing input makes the signal unavailable. The analyst consensus rating can differ because it reflects reported analyst opinions rather than historical technical conditions.")
            with tab_fundamentals:
                render_section_heading("Business & valuation", "Provider-reported profile metrics and quarterly financial history.")
                employee_note = f" · {info['fullTimeEmployees']:,} employees" if isinstance(info.get("fullTimeEmployees"), (int, float)) else ""
                st.caption(f"{info.get('sector') or 'Sector unavailable'} · {info.get('industry') or 'Industry unavailable'}{employee_note}")
                fund_rows = fundamentals_metric_table(info)
                if tab_is_active(tab_fundamentals):
                    if payload.get("profile_status") == "error":
                        st.warning("Company profile fundamentals could not be retrieved.")
                    elif not info or fund_rows["Latest value"].eq("—").all():
                        st.info("Yahoo Finance did not return company profile fundamentals for this ticker.")
                with st.container(key="research_fundamental_groups"):
                    fund_columns = st.columns(3)
                    fund_groups = (
                        ("Valuation & size", fund_rows.iloc[:6]),
                        ("Growth & profitability", fund_rows.iloc[6:10]),
                        ("Balance sheet & capital", fund_rows.iloc[10:]),
                    )
                    for col, (title, rows) in zip(fund_columns, fund_groups):
                        with col:
                            st.markdown(f"#### {title}")
                            render_financial_table(rows, key=f"fundamentals_{title.casefold().replace(' ', '_').replace('&', 'and')}")
                statement_result = load_tab_data_if_active(
                    tab_fundamentals, lambda: load_company_fundamentals(selected),
                    {"data":None, "status":"inactive", "message":None},
                )
                statement = statement_result.get("data")
                if statement_result.get("status") in {"error", "malformed"}:
                    st.warning(statement_result.get("message") or "Quarterly statement data is unavailable.")
                elif statement_result.get("status") == "missing" and tab_is_active(tab_fundamentals):
                    st.info("Yahoo Finance did not return a quarterly income statement for this ticker.")
                elif isinstance(statement, pd.DataFrame) and not statement.empty:
                    q_table = quarterly_statement_table(statement)
                    if q_table.empty:
                        st.info("A quarterly statement was returned, but it contained no supported income rows to display.")
                    else:
                        render_section_heading("Reported quarterly trend", "Amounts are in billions except diluted EPS; periods are provider-reported.")
                        render_financial_table(
                            q_table,
                            column_config={column:st.column_config.NumberColumn(format="$%.2f" if column == "Diluted EPS" else "$%.2f") for column in q_table.columns},
                            key="reported_quarterly_trend",
                        )
                st.caption("Company metrics come from Yahoo Finance snapshots; definitions, reporting periods, and coverage can vary by issuer. Compare valuation within an appropriate peer group.")
            with tab_catalysts:
                catalyst_data = load_tab_data_if_active(
                    tab_catalysts,
                    lambda: load_company_catalysts(selected),
                    {"_errors":{}, "_missing":[]},
                )
                for message in catalyst_data.get("_errors", {}).values():
                    st.warning(message)
                render_section_heading("Analyst & company events", "Wall Street research, company calendar data, and filing links.")
                cat_left, cat_right = st.columns([1,1])
                with cat_left:
                    st.markdown("#### Wall Street analyst consensus")
                    if stats.get("analyst_rating"):
                        st.metric("Current analyst consensus", stats["analyst_rating"], f"{stats['analyst_count']} analyst ratings")
                    elif tab_is_active(tab_catalysts):
                        st.info("Yahoo Finance did not return a sufficiently covered analyst consensus rating.")
                    st.markdown("#### Analyst price targets")
                    targets = analyst_target_summary(catalyst_data.get("analyst_targets"), stats["last"])
                    target_mean = targets.get("mean") if targets else None
                    target_count = info.get("numberOfAnalystOpinions")
                    if target_mean is not None and target_mean > 0:
                        upside = targets.get("upside_percent")
                        st.metric("Mean published target", f"${target_mean:,.2f}",
                                  f"{upside:+.1f}% vs last close" if upside is not None else None)
                        lo, hi = targets.get("low"), targets.get("high")
                        if lo is not None and hi is not None:
                            st.caption(f"Published range: ${lo:,.2f} – ${hi:,.2f}. Yahoo-reported analyst count: {target_count or 'unavailable'}.")
                    else:
                        if "analyst_targets" not in catalyst_data.get("_errors", {}) and tab_is_active(tab_catalysts):
                            st.info("Yahoo Finance did not return analyst price targets for this ticker.")
                    rec = payload.get("recommendations")
                    distribution = recommendation_distribution(rec)
                    if distribution is not None:
                        st.markdown("**Analyst recommendation distribution**")
                        render_financial_table(distribution, key="analyst_recommendation_distribution")
                    elif tab_is_active(tab_catalysts):
                        if payload.get("recommendation_status") in {"error", "malformed"}:
                            st.warning(payload.get("recommendation_message") or "Analyst recommendation distribution is unavailable.")
                        else:
                            st.info("Yahoo Finance did not return an analyst recommendation distribution for this ticker.")
                    revisions = eps_revision_table(catalyst_data.get("eps_revisions"))
                    if isinstance(revisions, pd.DataFrame) and not revisions.empty:
                        st.markdown("**EPS estimate revisions**")
                        render_financial_table(revisions, hide_index=False, key="analyst_eps_revisions")
                    elif "eps_revisions" not in catalyst_data.get("_errors", {}) and tab_is_active(tab_catalysts):
                        st.info("Yahoo Finance did not return EPS estimate revisions for this ticker.")
                    upgrades = catalyst_data.get("upgrades")
                    if isinstance(upgrades, pd.DataFrame) and not upgrades.empty:
                        st.markdown("**Recent analyst rating changes**")
                        render_financial_table(upgrades.head(8), hide_index=False, key="analyst_rating_changes")
                    elif "upgrades" not in catalyst_data.get("_errors", {}) and tab_is_active(tab_catalysts):
                        st.info("Yahoo Finance did not return recent analyst rating changes for this ticker.")
                with cat_right:
                    st.markdown("#### Earnings calendar")
                    dates = catalyst_data.get("earnings_dates")
                    if isinstance(dates, pd.DataFrame) and not dates.empty:
                        render_financial_table(dates.head(6), hide_index=False, key="research_earnings_calendar")
                    else:
                        st.caption("No earnings dates were returned.")
                    st.markdown("#### Recent SEC filings")
                    filings = catalyst_data.get("sec_filings")
                    if filings is None: filings = []
                    if isinstance(filings, pd.DataFrame): filings = filings.to_dict(orient="records")
                    if isinstance(filings, dict):
                        filings = filings.get("filings", list(filings.values()))
                    filing_rows = []
                    for filing in filings[:8] if isinstance(filings, list) else []:
                        if isinstance(filing, dict):
                            filing_rows.append({"Date":filing.get("date","—"),"Form":filing.get("type","—"),"Filing":filing.get("title","Open filing"),"URL":filing.get("url") or filing.get("link") or ""})
                    if filing_rows:
                        render_financial_table(
                            pd.DataFrame(filing_rows),
                            column_config={"URL":st.column_config.LinkColumn("SEC / filing source")},
                            key="research_sec_filings",
                        )
                    else:
                        st.caption("No filing links returned (funds, non-US issuers, or data coverage may differ).")
                st.caption("Analyst targets are third-party opinions, not price forecasts. Confirm dates and figures against original company releases and filings.")

            with tab_headlines:
                with st.container(border=True):
                    st.markdown("## Headlines & sentiment")
                    st.markdown('<div class="sub">Headlines are labeled Bullish, Bearish, or Neutral. Neutral means the title has weak, conflicting, broad-market, or unrelated evidence for the selected company.</div>', unsafe_allow_html=True)
                    news, news_warning = load_tab_data_if_active(
                        tab_headlines, lambda: load_ticker_news(selected), ([], None),
                    )
                    if news_warning and tab_is_active(tab_headlines):
                        st.caption(news_warning)
                    with st.expander("How the headline classifier works and what the research says"):
                        st.markdown("**Bullish** and **Bearish** require a clear directional score plus company-related context. **Neutral** is used when a headline is generic market coverage, does not clearly relate to the selected company, contains only weak wording, or has conflicting positive and negative cues. A single word such as *warning*, *probe*, or *recall* no longer automatically makes a story bearish. Nearby negation is checked for phrases such as **not beating estimates** or **approval denied**. Signal strength is a heuristic, not a probability or a forecast.")
                        st.markdown("Financial language depends on context: [Loughran and McDonald’s research](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2010.01625.x) found general-purpose negative word lists misclassify many terms in financial texts. [FinBERT](https://arxiv.org/abs/1908.10063) uses finance-trained context and three sentiment classes; Jujosmi Trade uses a transparent local ruleset, not a trained FinBERT model, so ambiguous headlines are now explicitly left Neutral.")
                    if not tab_is_active(tab_headlines):
                        st.info("Select Headlines & sentiment to load recent company news.")
                    elif not news:
                        st.info("No recent headlines were returned for this symbol.")
                    else:
                        positive = negative = neutral = low_signal = 0
                        parsed = []
                        for item in news:
                            content = (item.get("content") or item) if isinstance(item, dict) else {}
                            title = content.get("title") or item.get("title") or "Untitled story"
                            analysis = sentiment(title, symbol=selected, company_name=stats.get("name"))
                            label = analysis["label"]
                            positive += label == "Bullish"; negative += label == "Bearish"; neutral += label == "Neutral"
                            low_signal += analysis["confidence"] == "Low"
                            provider = content.get("provider", {}) or {}
                            publisher = provider.get("displayName") or item.get("publisher") or "News source"
                            canonical = content.get("canonicalUrl", {}) or {}
                            link = canonical.get("url") or item.get("link") or "#"
                            if isinstance(link, dict): link = link.get("url", "#")
                            ts = content.get("pubDate") or item.get("providerPublishTime")
                            if isinstance(ts, (int, float)):
                                published_at = datetime.fromtimestamp(ts).strftime("%b %d · %I:%M %p")
                            else:
                                published_at = str(ts)[:16] if ts else "Recent"
                            parsed.append((title, label, analysis["confidence"], analysis["reason"], publisher, published_at, link, news_topic(title)))
                        a, b, c, d = st.columns(4)
                        a.metric("Bullish headlines", positive)
                        b.metric("Bearish headlines", negative)
                        c.metric("Neutral headlines", neutral, help="Weak, mixed, broad-market, or unrelated headlines are not forced into a bullish or bearish label.")
                        d.metric("Low signal", low_signal, help="Low means the title provides limited directional evidence; it does not indicate bearishness.")
                        sentiment_filter = st.selectbox("Show headlines", ["All", "Bullish", "Bearish", "Neutral"], key="headline_sentiment_filter")
                        visible_headlines = [entry for entry in parsed if sentiment_filter == "All" or entry[1] == sentiment_filter]
                        if not visible_headlines:
                            st.info(f"No {sentiment_filter.lower()} headlines were returned for this ticker.")
                        for title, label, confidence, reason, publisher, published_at, link, topic in visible_headlines:
                            render_headline_card(
                                title=title, sentiment=label, confidence=confidence, topic=topic,
                                publisher=publisher, published_at=published_at, reason=reason,
                                source_url=link,
                            )

                    st.write("")

            st.write("")
    if workspace == "Watchlist":
        st.markdown('<div id="watchlist-snapshot" class="section-anchor"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("## Watchlist snapshot")
            rows = []
            for symbol in symbols:
                try:
                    snapshot_result = history_meta if symbol == selected else load_snapshot(symbol)
                    snapshot = snapshot_result.data
                    if snapshot.empty:
                        raise ValueError(snapshot_result.warning or "No price history")
                    s = stats if symbol == selected else analyze(
                        snapshot, {}, None, context.get("SPY"), load_analyst_recommendations(symbol)
                    )
                    profile = {"name":stats["name"],"sector":info.get("sector") or "Unclassified","industry":info.get("industry") or "Unclassified"} if symbol == selected else load_profile(symbol)
                    rows.append({"Ticker":symbol,"Company":profile["name"],"Sector":profile["sector"],"Industry":profile["industry"],"Last":s["last"],"Day":s["change"]/100,"30d range":s["move"],"Trend":s["state"],"Rating":s["rating"],"As of":snapshot_result.last_observation or "unavailable","Data status":snapshot_result.status,"Data warning":snapshot_result.warning or ""})
                except Exception:
                    profile = load_profile(symbol)
                    rows.append({"Ticker":symbol,"Company":profile["name"],"Sector":profile["sector"],"Industry":profile["industry"],"Last":np.nan,"Day":np.nan,"30d range":np.nan,"Trend":"Unavailable","Rating":"Unavailable","As of":"unavailable","Data status":"failed or missing","Data warning":"Price history or calculation was unavailable"})
            if rows:
                frame = pd.DataFrame(rows)
                industries = sorted(i for i in frame["Industry"].dropna().unique() if i != "Unclassified")
                industry_filter = st.selectbox("Filter by industry", ["All industries", *industries], key="industry_filter")
                if industry_filter != "All industries":
                    frame = frame[frame["Industry"] == industry_filter]
                st.dataframe(frame, use_container_width=True, hide_index=True,
                             column_config={"Last":st.column_config.NumberColumn(format="$%.2f"),"Day":st.column_config.NumberColumn(format="%+.2f%%"),"30d range":st.column_config.NumberColumn(format="±%.1f%%")})


    st.caption("Jujosmi Trade is an informational dashboard. Price, fundamentals, analyst data and third-party headlines are sourced through Yahoo Finance / yfinance; they may be delayed, incomplete or rate limited. Company filings link to SEC EDGAR when supplied by the feed. [yfinance project and usage notes](https://ranaroussi.github.io/yfinance/). Headline tags and market signals are rough analytical aids, not financial advice or forecasts.")
    chat_position = st.session_state.get("market_lens_chat_position")
    if isinstance(chat_position, dict):
        try:
            chat_left = max(0, int(chat_position.get("x", 0)))
            chat_top = max(0, int(chat_position.get("y", 0)))
            st.markdown(f"<style>.st-key-market_lens_ai_helper{{left:{chat_left}px!important;top:{chat_top}px!important;right:auto!important;bottom:auto!important;}}</style>", unsafe_allow_html=True)
        except (TypeError, ValueError):
            st.session_state.pop("market_lens_chat_position", None)

    if "market_lens_chat_messages" not in st.session_state:
        st.session_state["market_lens_chat_messages"] = []
    chat_event = floating_chat(
        messages=st.session_state["market_lens_chat_messages"],
        position=st.session_state.get("market_lens_chat_position"),
        ai_enabled=bool(get_api_key()),
    )
    if isinstance(chat_event, dict):
        event_id = str(chat_event.get("event_id", ""))
        if event_id and event_id != st.session_state.get("market_lens_chat_last_event"):
            st.session_state["market_lens_chat_last_event"] = event_id
            if chat_event.get("action") == "theme":
                theme_type = chat_event.get("theme_type")
                if theme_type in {"light", "dark"} and theme_type != st.session_state.get("market_lens_ui_theme"):
                    st.session_state["market_lens_ui_theme"] = theme_type
                    st.rerun()
            elif chat_event.get("action") == "move":
                try:
                    st.session_state["market_lens_chat_position"] = {
                        "x":max(0, int(chat_event.get("x", 0))),
                        "y":max(0, int(chat_event.get("y", 0))),
                    }
                except (TypeError, ValueError):
                    pass
                st.rerun()
            elif chat_event.get("action") == "send":
                question = str(chat_event.get("text", "")).strip()[:1800]
                if question:
                    st.session_state["market_lens_chat_messages"].append({"role":"user", "content":question})
                    with st.spinner("Preparing a terminology explanation…"):
                        answer = ask_ai(st.session_state["market_lens_chat_messages"])
                    st.session_state["market_lens_chat_messages"].append({"role":"assistant", "content":answer})
                    st.session_state["market_lens_chat_messages"] = st.session_state["market_lens_chat_messages"][-40:]
                    st.rerun()

    # Tell the website embed that the dashboard has rendered. The parent page uses
    # this signal to keep Streamlit's startup header covered until Jujosmi Trade is ready.
    components.html(
        '<script>window.parent.parent.postMessage({type:"market-lens-ready",token:"market-lens-ready-v1"},"*");</script>',
        height=1,
    )


if __name__ == '__main__':
    run_app()


