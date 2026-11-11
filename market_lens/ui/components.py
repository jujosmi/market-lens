'''Shared, presentation-only Streamlit components for MarketLens.'''

from __future__ import annotations

from html import escape
from urllib.parse import urlparse
from typing import Any

import streamlit as st


def render_section_heading(title: str, description: str | None = None, eyebrow: str | None = None) -> None:
    '''Render a compact, consistent heading for a meaningful research group.'''
    label = f'<div class="section-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    detail = f'<div class="section-description">{escape(description)}</div>' if description else ""
    st.markdown(
        f'<div class="section-heading">{label}<h2>{escape(title)}</h2>{detail}</div>',
        unsafe_allow_html=True,
    )


def render_workspace_heading(title: str, description: str, eyebrow: str = "Jujosmi Trade · Research workspace") -> None:
    """Render a consistent page heading with a visible workspace context."""
    st.markdown(
        f'<header class="workspace-heading"><div class="workspace-eyebrow">{escape(eyebrow)}</div>'
        f'<h1>{escape(title)}</h1><p>{escape(description)}</p></header>',
        unsafe_allow_html=True,
    )


def render_company_header(
    *, name: str, symbol: str, exchange: str, sector: str, industry: str,
    price: str, daily_change: str, change_positive: bool | None,
    source: str, retrieved: str, interval: str, status: str,
    latest_bar: str, quote_delay: str,
) -> None:
    '''Present already-loaded company identity, price, and provider freshness.'''
    direction = "positive" if change_positive is True else "negative" if change_positive is False else "neutral"
    identity = " | ".join(escape(value or "Unavailable") for value in (exchange, sector, industry))
    freshness = " | ".join(escape(value or "unavailable") for value in (
        source, f"Retrieved {retrieved}", f"Interval {interval}",
        f"Latest bar {latest_bar}", f"Quote delay {quote_delay}",
    ))
    st.markdown(
        f'''<div class="company-header" role="region" aria-label="Selected company and price data">
          <div class="company-identity">
            <div class="section-eyebrow">Selected security</div>
            <h2>{escape(name or symbol)} <span class="company-ticker">{escape(symbol)}</span></h2>
            <div class="company-meta">{identity}</div>
          </div>
          <div class="company-price-block">
            <div class="section-eyebrow">Last close</div>
            <div class="company-price">{escape(price)}</div>
            <div class="company-change {direction}">{escape(daily_change)}</div>
          </div>
          <div class="company-freshness"><span class="freshness-label">Price data | {escape(status or 'unknown')}</span>
            <span>{freshness}</span></div>
        </div>''',
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, note: str, explanation: str, tone: str = "") -> None:
    '''Render a financial metric and its accessible short explanation.'''
    safe_title = escape(title)
    safe_tone = tone if tone in {"positive", "negative", "neutral", "accent"} else ""
    st.markdown(
        f'''<div class="panel metric-card {safe_tone}">
          <div class="metric-label-row"><div class="metric-label">{safe_title}</div>
            <details class="help-icon">
              <summary aria-label="Why {safe_title}?"><span aria-hidden="true">i</span></summary>
              <span class="metric-tooltip">{escape(explanation)}</span>
            </details>
          </div><div class="metric-value">{escape(value)}</div>
          <div class="metric-note">{escape(note)}</div></div>''',
        unsafe_allow_html=True,
    )


def render_financial_table(
    data: Any, *, column_config: dict[str, Any] | None = None,
    hide_index: bool = True, key: str | None = None, height: int | str | None = None,
) -> None:
    '''Render tabular data at available width without altering provider values.'''
    kwargs: dict[str, Any] = {
        "column_config": column_config,
        "hide_index": hide_index,
        "width": "stretch",
    }
    if key is not None:
        kwargs["key"] = key
    if height is not None:
        kwargs["height"] = height
    st.dataframe(data, **kwargs)


def render_headline_card(
    *, title: str, sentiment: str, confidence: str, topic: str,
    publisher: str, published_at: str, reason: str, source_url: str,
) -> None:
    '''Render a readable headline with its existing label and source attribution.'''
    labels = {"Bullish":"bull", "Bearish":"bear", "Neutral":"neutral"}
    badge = labels.get(sentiment, "neutral")
    confidence_badge = "low" if confidence.casefold() == "low" else badge
    parsed = urlparse(source_url or "")
    safe_url = escape(source_url, quote=True) if parsed.scheme in {"http", "https"} else "#"
    safe_title = escape(title or "Untitled story")
    title_markup = (
        f'<a class="news-title" href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_title}</a>'
        if safe_url != "#" else f'<span class="news-title">{safe_title}</span>'
    )
    source_markup = (
        f'<a class="news-source-link" href="{safe_url}" target="_blank" rel="noopener noreferrer" aria-label="Open original source for {safe_title}">Open original source</a>'
        if safe_url != "#" else '<span class="news-source-link unavailable">Source link unavailable</span>'
    )
    st.markdown(
        f'''<article class="news-row">{title_markup}
          <div class="news-meta">{escape(publisher or 'News source')} | {escape(published_at or 'Recent')} | {escape(topic or 'General')}
            | <span class="pill {badge}">{escape(sentiment.upper())}</span>
            | <span class="pill {confidence_badge}">{escape(confidence.upper())} SIGNAL</span>
            <br>{escape(reason or '')}</div>{source_markup}
        </article>''',
        unsafe_allow_html=True,
    )


