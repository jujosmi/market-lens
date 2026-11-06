from __future__ import annotations

import html
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
try:
    # yfinance ships this mapping locally, so the industry directory can still
    # render and be searched when Yahoo's sector endpoint is temporarily down.
    from yfinance.const import SECTOR_INDUSTY_MAPPING
except Exception:
    SECTOR_INDUSTY_MAPPING = {}
from market_lens.analytics import analyze
from market_lens.assistant import ask_ai, floating_chat, get_api_key
from market_lens.charts import price_chart
from market_lens.config import DEFAULT_WATCHLIST, MAX_WATCHLIST_SIZE, SECTORS, SECTOR_KEYS
from market_lens.explanations import rating_explanation, trend_explanation
from market_lens.news import classify_headline as sentiment, classify_news_topic as news_topic
from market_lens.providers import YahooFinanceProvider
from market_lens.storage import load_watchlist, save_watchlist


st.set_page_config(page_title="Market Lens", page_icon="◉", layout="wide", initial_sidebar_state="expanded")

try:
    ACTIVE_THEME = st.session_state.get("market_lens_ui_theme") or st.context.theme.type
except Exception:
    ACTIVE_THEME = "dark"
LIGHT_THEME = ACTIVE_THEME == "light"
THEME_COLORS = ({
    "text":"#17312b", "muted":"#61756f", "surface":"#ffffff", "sidebar":"#eaf1ee", "border":"#dce7e2",
    "accent":"#087f63", "background":"#f3f7f5", "bull":"#08734f", "bear":"#b42335", "caution":"#8a5b00",
} if LIGHT_THEME else {
    "text":"#edf4f2", "muted":"#91a6a3", "surface":"#111d20", "sidebar":"#0e191c", "border":"#26383a",
    "accent":"#76e0b2", "background":"#0b1417", "bull":"#8ee6b6", "bear":"#ff9999", "caution":"#ffd27d",
})
st.markdown(
    "<style>:root{" + ";".join(f"--{name}:{value}" for name, value in {
        "text-color":THEME_COLORS["text"], "background-color":THEME_COLORS["background"],
        "secondary-background-color":THEME_COLORS["surface"], "border-color":THEME_COLORS["border"],
        "market-lens-sidebar":THEME_COLORS["sidebar"],
        "primary-color":THEME_COLORS["accent"], "market-lens-muted":THEME_COLORS["muted"],
        "market-lens-bull":THEME_COLORS["bull"], "market-lens-bear":THEME_COLORS["bear"],
        "market-lens-caution":THEME_COLORS["caution"],
    }.items()) + "}</style>",
    unsafe_allow_html=True,
)


def session_isolated_mode() -> bool:
    configured = os.environ.get("MARKET_LENS_HOSTED", "").strip().lower()
    if configured in {"1", "true", "yes", "on"}:
        return True
    try:
        return str(st.secrets.get("MARKET_LENS_HOSTED", "")).strip().lower() in {"1", "true", "yes", "on"}
    except Exception:
        return False


HOSTED_MODE = session_isolated_mode()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
  --ink:var(--text-color,#edf4f2);
  --muted:var(--market-lens-muted,color-mix(in srgb,var(--ink) 62%,transparent));
  --panel:var(--secondary-background-color,#111d20);
  --line:var(--border-color,#26383a);
  --mint:var(--primary-color,#76e0b2);
  --app-bg:var(--background-color,#0b1417);
  --bull:var(--market-lens-bull,color-mix(in srgb,var(--ink) 48%,#00a66c));
  --bear:var(--market-lens-bear,color-mix(in srgb,var(--ink) 48%,#d64555));
  --caution:var(--market-lens-caution,color-mix(in srgb,var(--ink) 48%,#bd7900));
}
html, body, [class*="css"] { font-family:'Manrope',sans-serif; }
.stApp { background:radial-gradient(ellipse at 78% -5%,color-mix(in srgb,var(--mint) 11%,var(--app-bg)) 0%,var(--app-bg) 48%); color:var(--ink); }
[data-testid="stSidebar"] { background:var(--market-lens-sidebar,var(--secondary-background-color,#0e191c)); border-right:1px solid var(--line); }
[data-testid="stHeader"] { display:none; }
h1,h2,h3 { letter-spacing:-.04em !important; }
.brand { font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; color:var(--mint); }
.jujosmi-home-link { display:block; margin:0 0 18px; line-height:0; }
.jujosmi-home-link img { display:block; width:min(100%,205px); max-height:62px; object-fit:contain; object-position:left center; }
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
.metric-label { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.12em; font-weight:700; }
.metric-value { font-family:'DM Mono',monospace; font-size:26px; font-weight:500; margin-top:8px; color:var(--ink); }
.metric-note { color:var(--muted); font-size:12px; margin-top:5px; }
.metric-label-row { display:flex; align-items:center; gap:7px; }
.help-icon { position:relative; display:inline-flex; align-items:center; justify-content:center; width:17px; height:17px; border:1px solid var(--line); border-radius:50%; color:var(--muted); font:700 11px Manrope,sans-serif; cursor:help; outline:none; }
.help-icon:hover, .help-icon:focus { color:var(--app-bg); background:var(--mint); border-color:var(--mint); }
.metric-tooltip { visibility:hidden; opacity:0; position:absolute; z-index:1000; right:-8px; bottom:24px; width:280px; padding:11px 13px; border:1px solid var(--line); border-radius:11px; color:var(--ink); background:var(--panel); box-shadow:0 12px 32px rgba(0,0,0,.18); font-size:11px; font-weight:500; line-height:1.5; text-transform:none; letter-spacing:0; transition:opacity .12s ease; }
.metric-card:hover .metric-tooltip, .metric-card:focus-within .metric-tooltip, .help-icon:hover .metric-tooltip, .help-icon:focus .metric-tooltip { visibility:visible; opacity:1; }
.pill { display:inline-block; padding:5px 10px; border-radius:99px; font-size:11px; font-weight:800; letter-spacing:.04em; }
.bull { color:var(--bull); background:color-mix(in srgb,#00a66c 12%,transparent); border:1px solid color-mix(in srgb,#00a66c 30%,transparent); }
.bear { color:var(--bear); background:color-mix(in srgb,#d64555 11%,transparent); border:1px solid color-mix(in srgb,#d64555 29%,transparent); }
.low { color:var(--caution); background:color-mix(in srgb,#bd7900 12%,transparent); border:1px solid color-mix(in srgb,#bd7900 30%,transparent); }
.news-title { color:var(--ink); font-weight:650; text-decoration:none; font-size:14px; line-height:1.45; }
.news-meta { color:var(--muted); font-size:11px; margin-top:8px; }
.news-row { padding:15px 0; border-bottom:1px solid var(--line); }
.news-row:last-child { border-bottom:0; }
.smallcaps { color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:10px; font-weight:800; }
div[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:16px 18px; }
div[data-testid="stMetricLabel"] { color:var(--muted); }
div[data-testid="stMetricValue"] { font-family:'DM Mono',monospace; }
button[kind="primary"] { background:var(--mint); color:var(--app-bg); border:0; }
.stTabs [data-baseweb="tab-list"] { gap:10px; background:color-mix(in srgb,var(--panel) 88%,transparent); padding:6px 10px; border:1px solid var(--line); border-radius:12px; }
.stTabs [data-baseweb="tab"] { color:var(--muted); border-radius:9px; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color:var(--mint); background:color-mix(in srgb,var(--mint) 12%,transparent); }
div[data-testid="stVerticalBlockBorderWrapper"] { background:color-mix(in srgb,var(--panel) 92%,transparent); border-color:var(--line); border-radius:18px; padding:18px 20px; margin:10px 0 22px; box-shadow:0 10px 28px rgba(0,0,0,.08); }
div[data-testid="stVerticalBlockBorderWrapper"] h2 { margin-top:0; }
div[data-testid="stVerticalBlockBorderWrapper"] h3 { margin-top:8px; }
.st-key-market_lens_ai_helper { position:fixed !important; right:20px !important; bottom:20px !important; width:min(390px, calc(100vw - 24px)) !important; z-index:999999 !important; margin:0 !important; }
.st-key-market_lens_ai_helper iframe { width:100% !important; border:0 !important; background:transparent !important; }
</style>
""", unsafe_allow_html=True)


def as_float(value, default=np.nan):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
    ticker = yf.Ticker(symbol)
    history_result = YahooFinanceProvider().history(symbol, period="2y", interval="1d")
    history = history_result.data
    if history.empty:
        raise ValueError(history_result.warning or f"No price history returned for {symbol}. Check the ticker and try again.")
    optional_warnings = []
    try:
        info = ticker.get_info()
    except Exception as exc:
        info = {}
        optional_warnings.append(f"Company profile unavailable ({type(exc).__name__}).")
    try:
        news = ticker.get_news(count=12)
    except Exception as exc:
        news = []
        optional_warnings.append(f"Recent headlines unavailable ({type(exc).__name__}).")
    recommendations = None
    earnings_dates = None
    analyst_targets = None
    eps_revisions = None
    sec_filings = None
    upgrades = None
    quarterly_income = None
    try:
        recommendations = ticker.get_recommendations_summary()
    except Exception:
        pass
    try:
        earnings_dates = ticker.get_earnings_dates(limit=8)
    except Exception:
        pass
    try:
        analyst_targets = ticker.analyst_price_targets
    except Exception:
        pass
    try:
        eps_revisions = ticker.get_eps_revisions()
    except Exception:
        pass
    try:
        sec_filings = ticker.get_sec_filings()
    except Exception:
        pass
    try:
        upgrades = ticker.get_upgrades_downgrades()
    except Exception:
        pass
    try:
        quarterly_income = ticker.quarterly_income_stmt
    except Exception:
        pass
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
    return {"history": history, "history_result": history_result, "info": info, "news": news, "optional_warnings":optional_warnings, "options_move": options_move, "options_expiry": options_expiry,
            "recommendations": recommendations, "earnings_dates": earnings_dates, "analyst_targets": analyst_targets,
            "eps_revisions": eps_revisions, "sec_filings": sec_filings, "upgrades": upgrades,
            "quarterly_income": quarterly_income}


@st.cache_data(ttl=300, show_spinner=False)
def load_benchmark() -> pd.DataFrame:
    return yf.Ticker("SPY").history(period="6mo", interval="1d", auto_adjust=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_snapshot(symbol: str):
    return YahooFinanceProvider().history(symbol, period="2y", interval="1d")


@st.cache_data(ttl=300, show_spinner=False)
def load_market_context() -> dict:
    symbols = ["SPY", "QQQ", "IWM", "DIA", "^VIX", "^TNX", *SECTORS.values()]
    results = YahooFinanceProvider().histories(symbols, period="2y", interval="1d")
    context = {symbol: result.data for symbol, result in results.items() if not result.data.empty}
    context["_metadata"] = results
    return context


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
                continue
            sector_name = sector.name or sector_labels.get(sector_key, sector_key.replace("-", " ").title())
            for idx, row in industries.iterrows():
                industry_key = row.get("key") or row.get("industryKey") or str(idx)
                industry_name = row.get("name") or str(industry_key).replace("-", " ").title()
                rows.append({"industry_key":str(industry_key), "industry":str(industry_name),
                             "sector_key":sector_key, "sector":str(sector_name), "source":"Yahoo Finance"})
        except Exception:
            continue

    # Keep the directory searchable if the live sector listing is unavailable.
    for sector_key in SECTOR_KEYS:
        sector_name = sector_labels.get(sector_key, sector_key.replace("-", " ").title())
        for industry_name in SECTOR_INDUSTY_MAPPING.get(sector_name, set()):
            name = str(industry_name).strip()
            industry_key = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").casefold()
            industry_key = re.sub(r"[^a-z0-9]+", "-", industry_key).strip("-")
            already_listed = any(
                item["industry"].casefold() == name.casefold()
                or item["industry_key"].casefold() == industry_key
                for item in rows
            )
            if name and not already_listed:
                rows.append({"industry_key":industry_key, "industry":name,
                             "sector_key":sector_key, "sector":sector_name, "source":"Built-in directory"})

    return pd.DataFrame(rows).drop_duplicates(subset=["industry_key"]) if rows else pd.DataFrame(columns=["industry_key","industry","sector_key","sector","source"])


@st.cache_data(ttl=3600, show_spinner=False)
def load_industry_companies(industry_key: str) -> tuple[pd.DataFrame, str | None]:
    try:
        industry = yf.Industry(industry_key)
        frames = []
        for list_name, attribute in (("Top performing", "top_performing_companies"),
                                     ("Top growth", "top_growth_companies")):
            companies = getattr(industry, attribute, None)
            if isinstance(companies, pd.DataFrame) and not companies.empty:
                frame = companies.copy()
                frame["Company list"] = list_name
                frames.append(frame)
        if not frames:
            return pd.DataFrame(), None
        combined = pd.concat(frames, axis=0)
        combined = combined.loc[~combined.index.astype(str).duplicated(keep="first")]
        return combined, None
    except Exception as exc:
        return pd.DataFrame(), f"{type(exc).__name__}: {str(exc)[:180]}"


@st.cache_data(ttl=1800, show_spinner=False)
def rate_industry_companies(symbols: tuple[str, ...]) -> dict[str, str]:
    """Apply the same technical screen used by the selected-ticker snapshot."""
    if not symbols:
        return {}
    try:
        histories = YahooFinanceProvider().histories(list(symbols), period="2y", interval="1d")
        benchmark = load_benchmark()
    except Exception:
        return {symbol:"Unavailable" for symbol in symbols}

    ratings = {}
    for symbol in symbols:
        result = histories.get(symbol)
        if result is None or result.data.empty:
            ratings[symbol] = "Unavailable"
            continue
        try:
            ratings[symbol] = analyze(result.data, {}, None, benchmark).get("rating", "Unavailable")
        except Exception:
            ratings[symbol] = "Unavailable"
    return ratings


@st.cache_data(ttl=900, show_spinner=False)
def load_upcoming_events(start_date: date, end_date: date,
                         watchlist_symbols: tuple[str, ...] = ()) -> dict[str, object]:
    results: dict[str, object] = {
        "Earnings":pd.DataFrame(), "IPOs":pd.DataFrame(), "Splits":pd.DataFrame(),
        "Economic events":pd.DataFrame(), "_errors":{}, "_earnings_fallback":False,
    }
    errors: dict[str, str] = {}
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
            try:
                data = fetch()
                results[label] = data if isinstance(data, pd.DataFrame) else pd.DataFrame()
            except Exception as exc:
                errors[label] = f"{type(exc).__name__}: {str(exc)[:180]}"

    # Keep an earnings view available for the user's own symbols if Yahoo's
    # market-wide calendar query is empty or unavailable.
    if isinstance(results["Earnings"], pd.DataFrame) and results["Earnings"].empty:
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


with st.sidebar:
    st.markdown('<a class="jujosmi-home-link" href="https://jujosmi.com" target="_blank" rel="noopener noreferrer" aria-label="Visit jujosmi.com"><img src="app/static/jujosmi-logo-simple-shadow.png" alt="Jujosmi"></a>', unsafe_allow_html=True)
    st.markdown('<div class="brand">◉ &nbsp; MARKET LENS</div>', unsafe_allow_html=True)
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
        st.cache_data.clear()
        st.rerun()
    st.caption("Data via Yahoo Finance · refreshed every 5 min")
    if HOSTED_MODE:
        st.caption("Hosted mode: your watchlist stays in this browser session and is not shared with other visitors.")

st.markdown('<div class="hero"><div class="eyebrow">Markets, in focus</div><h1>Market Lens</h1><div class="sub">A calm, evidence-led view of price action, volatility and the headlines moving your watchlist.</div></div>', unsafe_allow_html=True)
st.markdown('<nav class="quick-nav" aria-label="Jump to a dashboard section"><a href="#selected-ticker">Ticker snapshot</a><a href="#discovery-index">Discovery</a><a href="#market-pulse">Market pulse</a><a href="#technical-analysis">Analysis</a><a href="#headlines">Headlines</a><a href="#watchlist-snapshot">Watchlist</a></nav>', unsafe_allow_html=True)

try:
    with st.spinner(f"Researching {selected} and the broader market…"):
        payload = load_market_data(selected)
        context = load_market_context()
    history, info, news = payload["history"], payload["info"], payload["news"]
    stats = analyze(history, info, payload["options_move"], context.get("SPY"))
except Exception as exc:
    st.error(str(exc))
    st.stop()

up = np.isfinite(stats["change"]) and stats["change"] >= 0
change_color = ("#087f63" if LIGHT_THEME else "#76e0b2") if up else ("#b42335" if LIGHT_THEME else "#ff8585")
company_industry = html.escape(info.get("industry") or info.get("sector") or "Industry unavailable")
history_meta = payload["history_result"]
with st.container(border=True):
    st.markdown(f'<div class="eyebrow">{html.escape(stats["name"] or selected)} &nbsp;·&nbsp; {selected} &nbsp;·&nbsp; {company_industry} &nbsp;·&nbsp; {datetime.now().strftime("%A, %B %d")}</div>', unsafe_allow_html=True)
    st.caption(f"Price source: {history_meta.source} · retrieved: {history_meta.retrieved_at.astimezone().strftime('%Y-%m-%d %H:%M %Z')} · interval: {history_meta.interval} · status: {history_meta.status} · latest bar: {history_meta.last_observation or 'unavailable'} · quote delay: {history_meta.provider_delay}")
    if history_meta.warning:
        if history_meta.status == "partial":
            st.caption(f"Data note · {history_meta.warning}")
        else:
            st.warning(history_meta.warning)
    for warning in payload.get("optional_warnings", []):
        st.warning(warning)
    
st.markdown('<div id="selected-ticker" class="section-anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    snapshot_symbol = html.escape(selected)
    snapshot_company = html.escape(stats.get("name") or selected)
    st.markdown(f'## Selected ticker snapshot <span class="snapshot-security">({snapshot_symbol} · {snapshot_company})</span>', unsafe_allow_html=True)
    cols = st.columns(4)
    move_explanation = ("A one-standard-deviation 30-day range from " + stats["move_source"] + ". This describes possible variability, not whether price is expected to rise or fall.")
    trend_note = f"RSI {stats['rsi']:.0f} · 20d / 50d / 200d trend" if np.isfinite(stats['rsi']) else "RSI unavailable · trend windows require full history"
    metrics = [
        ("Last close", f"${stats['last']:,.2f}", f"<span style='color:{change_color}'>{stats['change']:+.2f}% today</span>" if np.isfinite(stats['change']) else "Daily change unavailable",
         "Latest adjusted daily closing price returned by the provider. Today's change compares it with the prior available daily close."),
        ("30 day expected move", f"±{stats['move']*100:.1f}%" if np.isfinite(stats['move']) else "Unavailable", stats["move_source"], move_explanation),
        ("Trend read", stats["state"], trend_note, trend_explanation(stats)),
        ("Signal rating", stats["rating"], f"{stats['constructive_checks']} constructive · {stats['caution_checks']} caution checks", rating_explanation(stats)),
    ]
    for col, (label, value, note, explanation) in zip(cols, metrics):
        safe_label = html.escape(label)
        safe_explanation = html.escape(explanation)
        col.markdown(f'<div class="panel metric-card"><div class="metric-label-row"><div class="metric-label">{safe_label}</div><span class="help-icon" tabindex="0" role="button" aria-label="Explanation for {safe_label}">i<span class="metric-tooltip" role="tooltip">{safe_explanation}</span></span></div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)
    
    st.write("")
    left, right = st.columns([1.55, 1])
    with left:
        st.markdown('<div class="panel"><div class="smallcaps">Price action · 6 months</div>', unsafe_allow_html=True)
        price_figure = price_chart(history, selected)
        if LIGHT_THEME:
            price_figure.update_traces(line={"color":"#087f63"}, selector={"name":selected})
            price_figure.update_traces(line={"color":"#536ac7"}, selector={"name":"20 day average"})
            price_figure.update_layout(font={"color":"#61756f","family":"Manrope"})
            price_figure.update_yaxes(gridcolor="#e1e9e5")
        st.plotly_chart(price_figure, use_container_width=True, config={"displayModeBar":False})
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="smallcaps">Market read</div>', unsafe_allow_html=True)
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
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("")
st.markdown('<div id="discovery-index" class="section-anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("## Discovery index")
    st.markdown('<div class="sub">Browse the market by industry and keep an eye on upcoming company and market events.</div>', unsafe_allow_html=True)
    event_window = st.selectbox("Event window", [30, 60, 90], index=1, format_func=lambda days:f"Next {days} days", key="discovery_event_window")
    event_start = date.today()
    event_end = event_start + timedelta(days=event_window)
    with st.spinner("Loading upcoming company and market events…"):
        upcoming_events = load_upcoming_events(event_start, event_end, tuple(symbols))
    index_tab, earnings_tab, ipo_tab, events_tab = st.tabs(["Industry directory", "Earnings soon", "IPOs soon", "Other events"])
    st.caption(f"Industry and calendar data: Yahoo Finance via yfinance · retrieved {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')} · coverage and provider delay are not verified.")
    with index_tab:
        industry_index = load_industry_index()
        if industry_index.empty:
            st.info("Industry directory data is temporarily unavailable. Use ticker search or the watchlist industry filter in the meantime.")
        else:
            industry_index = industry_index.sort_values(["sector", "industry"])
            st.caption("Yahoo Finance supplies canonical industry keys; a local directory keeps categories searchable if that lookup is unavailable.")
            industry_options = [
                {"label":f"{row.industry} · {row.sector}", "industry":str(row.industry),
                 "sector":str(row.sector), "key":str(row.industry_key)}
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
                companies, company_error = load_industry_companies(industry_key)
            if companies.empty:
                if company_error:
                    st.warning(f"Yahoo Finance could not load companies for this industry: {company_error}")
                else:
                    st.caption("Yahoo Finance returned no top-performing or top-growth companies for this industry.")
            else:
                company_display = companies.copy()
                company_symbols = tuple(dict.fromkeys(
                    str(symbol).strip().upper() for symbol in companies.index
                    if str(symbol).strip() and str(symbol).casefold() != "nan"
                ))
                company_ratings = rate_industry_companies(company_symbols)
                company_display.insert(
                    0, "Market Lens rating",
                    [company_ratings.get(str(symbol).strip().upper(), "Unavailable") for symbol in company_display.index],
                )
                st.dataframe(company_display, use_container_width=True)
                st.caption("Market Lens rating uses the same technical checks as the ticker snapshot. Unavailable means the required price history or benchmark data was incomplete. Industry listings are Yahoo Finance’s top-performing and top-growth companies, not a complete exchange-wide security master.")
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
    
st.markdown('<div id="market-pulse" class="section-anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("## Market pulse")
    st.markdown("### Index performance")
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
    mc1, mc2 = st.columns([1, 2])
    with mc1:
        vix_text = f"{vix_level:.1f}" if np.isfinite(vix_level) else "Unavailable"
        vix_label = "elevated" if np.isfinite(vix_level) and vix_level >= 25 else "moderate" if np.isfinite(vix_level) and vix_level >= 18 else "calm" if np.isfinite(vix_level) else "—"
        tnx_frame = context.get("^TNX")
        yield10 = float(tnx_frame["Close"].dropna().iloc[-1]) if tnx_frame is not None and not tnx_frame.empty else np.nan
        yield_text = f"{yield10:.2f}%" if np.isfinite(yield10) else "—"
        vix_meta, tnx_meta = context_meta.get("^VIX"), context_meta.get("^TNX")
        vix_asof = pd.Timestamp(vix_frame["Close"].dropna().index[-1]).strftime("%Y-%m-%d") if vix_frame is not None and not vix_frame.empty else "unavailable"
        tnx_asof = pd.Timestamp(tnx_frame["Close"].dropna().index[-1]).strftime("%Y-%m-%d") if tnx_frame is not None and not tnx_frame.empty else "unavailable"
        vix_status = vix_meta.status if vix_meta else "unknown"
        tnx_status = tnx_meta.status if tnx_meta else "unknown"
        st.markdown(f'<div class="panel"><div class="smallcaps">Regime & volatility</div><div class="metric-value">{vix_text} <span style="font:500 14px Manrope;color:var(--muted)">VIX · {vix_label}</span></div><div class="metric-note">VIX as of {vix_asof} · {vix_status}</div><div class="metric-note">S&P 500 trend: {spy_trend}</div><div class="metric-note">10Y Treasury proxy: {yield_text} · as of {tnx_asof} · {tnx_status}</div><div class="metric-note">{pos_breadth} of {len(sector_rows)} sectors positive over the past month</div></div>', unsafe_allow_html=True)
    with mc2:
        st.dataframe(pd.DataFrame(benchmarks), use_container_width=True, hide_index=True,
                     column_config={"Last":st.column_config.NumberColumn(format="$%.2f"),"Day":st.column_config.NumberColumn(format="%+.2f%%"),"1 month":st.column_config.NumberColumn(format="%+.1f%%")})
    with st.expander("Sector rotation · 11 sector ETFs"):
        if sector_rows:
            st.dataframe(pd.DataFrame(sector_rows), use_container_width=True, hide_index=True,
                         column_config={column:st.column_config.NumberColumn(format="%+.1f%%") for column in ("1 month","vs S&P 1m","3 months","vs S&P 3m")})
            st.caption("Sector ETFs are proxies. Relative returns compare each sector ETF with SPY; this is not a complete measure of individual-stock market breadth.")
    st.caption("VIX reflects options-implied, non-directional 30-day S&P 500 volatility, not a forecast of whether the market will rise or fall. Its calm / moderate / elevated labels are rough display bands. [Cboe methodology](https://www.cboe.com/tradable_products/vix/faqs)")
    
    st.write("")
st.markdown('<div id="technical-analysis" class="section-anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("## Research desk")
    st.markdown('<div class="sub">Price structure, business quality, expectations, catalysts, and primary-source filings in one view.</div>', unsafe_allow_html=True)
    tab_technical, tab_fundamentals, tab_catalysts = st.tabs(["Technical & relative strength", "Business & valuation", "Estimates, events & filings"])
    with tab_technical:
        tech_left, tech_right = st.columns([1, 1])
        with tech_left:
            st.markdown("#### Trend and risk signals")
            tech_rows = [
                ("Trend stack", stats["state"]), ("20 day average", f"${stats['sma20']:,.2f} · {'price above' if stats['last'] > stats['sma20'] else 'price below'}" if np.isfinite(stats['sma20']) else "Unavailable · requires 20 closes"),
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
            st.dataframe(pd.DataFrame(tech_rows, columns=["Measure", "Reading"]), use_container_width=True, hide_index=True)
        with tech_right:
            st.markdown("#### Performance vs S&P 500")
            rel_rows = [{"Horizon":h,"Ticker":r["asset"],"S&P 500":r["benchmark"],"Excess return":r["excess"]} for h,r in stats["returns"].items()]
            st.dataframe(pd.DataFrame(rel_rows), use_container_width=True, hide_index=True,
                         column_config={"Ticker":st.column_config.NumberColumn(format="%+.1f%%"),"S&P 500":st.column_config.NumberColumn(format="%+.1f%%"),"Excess return":st.column_config.NumberColumn(format="%+.1f%%")})
            st.markdown("#### Read-through")
            positives = stats["constructive_checks"]
            risks = stats["caution_checks"]
            rating_coverage = "all required checks available" if stats["rating_checks_complete"] else "missing inputs prevent a rating"
            st.markdown(f"**Screening label: {stats['rating']}** · {positives} constructive checks vs {risks} caution checks · {rating_coverage}.")
            st.caption("Market Lens Buy / Hold / Sell is a technical screen, separate from analyst consensus. Buy means at least 2 more constructive than caution checks; Sell means at least 2 more caution than constructive; Hold means the counts are within 1. All 10 checks must be available. It is not a forecast or a personal instruction to trade.")
            with st.expander("See the rating checks"):
                st.markdown("**Buy:** net score +2 or higher (constructive checks minus caution checks). **Hold:** net score −1, 0, or +1. **Sell:** net score −2 or lower. Each check has equal weight; a missing input makes the signal unavailable.\n\n**Constructive checks:** price above the 50-day average; 50-day average above the 200-day average; MACD above its signal line; positive 3-month excess return versus SPY; RSI from 50 up to, but not including, 70.\n\n**Caution checks:** price below the 200-day average; MACD below its signal line; negative 3-month excess return versus SPY; RSI at or above 70; current price at least 20% below its 52-week high. An analyst Buy / Strong Buy can coexist with a Market Lens Sell because analyst consensus and this historical technical screen use different inputs and time horizons.")
    with tab_fundamentals:
        st.markdown("#### Business profile & valuation")
        st.caption(f"{info.get('sector') or 'Sector unavailable'} · {info.get('industry') or 'Industry unavailable'} · {info.get('fullTimeEmployees') or '—':,} employees" if isinstance(info.get('fullTimeEmployees'), (int,float)) else f"{info.get('sector') or 'Sector unavailable'} · {info.get('industry') or 'Industry unavailable'}")
        fundamentals = [
            ("Market cap", info.get("marketCap"), "currency"), ("Trailing P/E", info.get("trailingPE")), ("Forward P/E", info.get("forwardPE")), ("PEG ratio", info.get("pegRatio")),
            ("Price / sales", info.get("priceToSalesTrailing12Months")), ("EV / EBITDA", info.get("enterpriseToEbitda")),
            ("Revenue growth", info.get("revenueGrowth"), "percent"), ("Profit margin", info.get("profitMargins"), "percent"),
            ("Operating margin", info.get("operatingMargins"), "percent"), ("Return on equity", info.get("returnOnEquity"), "percent"),
            ("Debt / equity", info.get("debtToEquity")), ("Current ratio", info.get("currentRatio")),
            ("Free cash flow", info.get("freeCashflow"), "currency"), ("Dividend yield", info.get("dividendYield"), "percent"),
        ]
        fund_rows = []
        for entry in fundamentals:
            label, value = entry[0], entry[1]
            kind = entry[2] if len(entry) > 2 else "number"
            if value is None or not np.isfinite(as_float(value)):
                display = "—"
            elif kind == "percent": display = f"{as_float(value)*100:.1f}%"
            elif kind == "currency": display = f"${as_float(value)/1e12:.2f}T" if abs(as_float(value)) >= 1e12 else f"${as_float(value)/1e9:.2f}B"
            else: display = f"{as_float(value):,.2f}"
            fund_rows.append({"Metric":label,"Latest value":display})
        fund_left, fund_right = st.columns([1, 1])
        with fund_left:
            st.dataframe(pd.DataFrame(fund_rows[:7]), use_container_width=True, hide_index=True)
        with fund_right:
            st.dataframe(pd.DataFrame(fund_rows[7:]), use_container_width=True, hide_index=True)
        quarterly = payload.get("quarterly_income")
        if isinstance(quarterly, pd.DataFrame) and not quarterly.empty:
            q_rows = {}
            for label, candidates in (("Revenue ($B)",("Total Revenue",)),("Operating income ($B)",("Operating Income",)),("Net income ($B)",("Net Income",)),("Diluted EPS",("Diluted EPS",))):
                match = next((candidate for candidate in candidates if candidate in quarterly.index), None)
                if match:
                    series = quarterly.loc[match].iloc[:4]
                    q_rows[label] = [as_float(value)/1e9 if label.endswith("($B)") else as_float(value) for value in series]
            if q_rows:
                q_periods = [pd.to_datetime(period).strftime("%b %Y") for period in quarterly.columns[:4]]
                q_table = pd.DataFrame(q_rows, index=q_periods)
                st.markdown("#### Reported quarterly trend")
                st.dataframe(q_table, use_container_width=True,
                             column_config={column:st.column_config.NumberColumn(format="$%.2f" if column == "Diluted EPS" else "%.2f") for column in q_table.columns})
        st.caption("Company metrics come from Yahoo Finance snapshots; definitions, reporting periods, and coverage can vary by issuer. Compare valuation within an appropriate peer group.")
    with tab_catalysts:
        cat_left, cat_right = st.columns([1,1])
        with cat_left:
            st.markdown("#### Analyst expectations")
            targets = payload.get("analyst_targets") or {}
            target_mean = as_float(targets.get("mean")) if isinstance(targets, dict) else np.nan
            target_count = info.get("numberOfAnalystOpinions")
            if np.isfinite(target_mean) and target_mean > 0:
                st.metric("Mean published target", f"${target_mean:,.2f}", f"{(target_mean/stats['last']-1)*100:+.1f}% vs last close")
                lo, hi = as_float(targets.get("low")), as_float(targets.get("high"))
                if np.isfinite(lo) and np.isfinite(hi): st.caption(f"Published range: ${lo:,.2f} – ${hi:,.2f}. Yahoo-reported analyst count: {target_count or 'unavailable'}.")
            else:
                st.info("Analyst price targets are not available for this symbol.")
            rec = payload.get("recommendations")
            if isinstance(rec, pd.DataFrame) and not rec.empty:
                current = rec.iloc[0]
                fields = ["strongBuy","buy","hold","sell","strongSell"]
                if all(field in rec.columns for field in fields):
                    st.markdown("**Latest rating distribution**")
                    st.dataframe(pd.DataFrame({"Rating":["Strong buy","Buy","Hold","Sell","Strong sell"],"Analyst count":[int(as_float(current[f],0)) for f in fields]}), use_container_width=True, hide_index=True)
            revisions = payload.get("eps_revisions")
            if isinstance(revisions, pd.DataFrame) and not revisions.empty:
                st.markdown("**EPS estimate revisions**")
                st.dataframe(revisions, use_container_width=True)
            upgrades = payload.get("upgrades")
            if isinstance(upgrades, pd.DataFrame) and not upgrades.empty:
                st.markdown("**Recent analyst rating changes**")
                st.dataframe(upgrades.head(8), use_container_width=True)
        with cat_right:
            st.markdown("#### Earnings calendar")
            dates = payload.get("earnings_dates")
            if isinstance(dates, pd.DataFrame) and not dates.empty:
                st.dataframe(dates.head(6), use_container_width=True)
            else:
                st.caption("No earnings dates were returned.")
            st.markdown("#### Recent SEC filings")
            filings = payload.get("sec_filings")
            if filings is None: filings = []
            if isinstance(filings, pd.DataFrame): filings = filings.to_dict(orient="records")
            if isinstance(filings, dict):
                filings = filings.get("filings", list(filings.values()))
            filing_rows = []
            for filing in filings[:8] if isinstance(filings, list) else []:
                if isinstance(filing, dict):
                    filing_rows.append({"Date":filing.get("date","—"),"Form":filing.get("type","—"),"Filing":filing.get("title","Open filing"),"URL":filing.get("url") or filing.get("link") or ""})
            if filing_rows:
                st.dataframe(pd.DataFrame(filing_rows), use_container_width=True, hide_index=True,
                             column_config={"URL":st.column_config.LinkColumn("SEC / filing source")})
            else:
                st.caption("No filing links returned (funds, non-US issuers, or data coverage may differ).")
        st.caption("Analyst targets are third-party opinions, not price forecasts. Confirm dates and figures against original company releases and filings.")
    
    st.write("")
st.markdown('<div id="headlines" class="section-anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown("## Headlines & sentiment")
    st.markdown('<div class="sub">Financial phrases, weighted polarity terms and negation checks drive each Bullish / Bearish tag. Low signal means the headline gives limited directional evidence.</div>', unsafe_allow_html=True)
    with st.expander("How the headline classifier works and what the research says"):
        st.markdown("The lightweight local classifier scores finance-specific phrases such as **beats estimates**, **cuts guidance**, and **shares fall**, then checks for nearby negation such as **not**, **failed to**, or **denied**. Signal strength depends on how much evidence appears and how clearly one side outweighs the other; it is not a calibrated probability. A score tie is forced to **Bearish · Low signal** to keep a binary display; that tie-break is not evidence that the story is bad news.")
        st.markdown("This follows the finance-specific vocabulary idea behind the [Loughran–McDonald dictionary](https://sraf.nd.edu/loughranmcdonald-master-dictionary/) and adds phrase and negation rules. Research on [FinBERT](https://arxiv.org/abs/1908.10063) finds finance-domain contextual models outperform earlier methods on financial sentiment datasets; this app uses a transparent rule set, not a trained FinBERT model. [Negation scope research](https://www.sciencedirect.com/science/article/abs/pii/S0167923616300823) also supports treating negation as part of financial headline interpretation.")
    if not news:
        st.info("No recent headlines were returned for this symbol.")
    else:
        positive = negative = low_signal = 0
        parsed = []
        for item in news:
            content = (item.get("content") or item) if isinstance(item, dict) else {}
            title = content.get("title") or item.get("title") or "Untitled story"
            analysis = sentiment(title)
            label = analysis["label"]
            positive += label == "Bullish"; negative += label == "Bearish"
            low_signal += analysis["confidence"] == "Low"
            provider = content.get("provider", {}) or {}
            publisher = provider.get("displayName") or item.get("publisher") or "News source"
            canonical = content.get("canonicalUrl", {}) or {}
            link = canonical.get("url") or item.get("link") or "#"
            if isinstance(link, dict): link = link.get("url", "#")
            ts = content.get("pubDate") or item.get("providerPublishTime")
            if isinstance(ts, (int, float)):
                date = datetime.fromtimestamp(ts).strftime("%b %d · %I:%M %p")
            else:
                date = str(ts)[:16] if ts else "Recent"
            parsed.append((title, label, analysis["confidence"], analysis["reason"], publisher, date, link, news_topic(title)))
        a, b, c = st.columns(3)
        a.metric("Bullish headlines", positive)
        b.metric("Bearish headlines", negative)
        c.metric("Low signal", low_signal, help="Binary label has weak or conflicting headline evidence.")
        for title, label, confidence, reason, publisher, date, link, topic in parsed:
            badge = "bull" if label == "Bullish" else "bear"
            confidence_badge = "low" if confidence == "Low" else badge
            safe_link = link if urlparse(link).scheme in ("http", "https") else "#"
            safe_link = html.escape(safe_link, quote=True)
            st.markdown(f'<div class="news-row"><a class="news-title" href="{safe_link}" target="_blank" rel="noopener noreferrer">{html.escape(title)}</a><div class="news-meta">{html.escape(publisher)} &nbsp;·&nbsp; {html.escape(date)} &nbsp;·&nbsp; {html.escape(topic)} &nbsp;·&nbsp; <span class="pill {badge}">{label.upper()}</span> &nbsp; <span class="pill {confidence_badge}">{confidence.upper()} SIGNAL</span><br>{html.escape(reason)}</div></div>', unsafe_allow_html=True)
    
    st.write("")
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
            s = stats if symbol == selected else analyze(snapshot, {}, None, context.get("SPY"))
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
    
    st.caption("Market Lens is an informational dashboard. Price, fundamentals, analyst data and third-party headlines are sourced through Yahoo Finance / yfinance; they may be delayed, incomplete or rate limited. Company filings link to SEC EDGAR when supplied by the feed. [yfinance project and usage notes](https://ranaroussi.github.io/yfinance/). Headline tags and market signals are rough analytical aids, not financial advice or forecasts.")

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
# this signal to keep Streamlit's startup header covered until Market Lens is ready.
components.html(
    '<script>window.parent.parent.postMessage({type:"market-lens-ready",token:"market-lens-ready-v1"},"*");</script>',
    height=1,
)
