"""Educational trading-terminology assistant and floating Streamlit component."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit.components.v1 as components


_COMPONENT = None
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4.1-mini"
MAX_HISTORY_MESSAGES = 10
MAX_MESSAGE_CHARS = 1800

SYSTEM_INSTRUCTIONS = """You are Jujosmi Trade's beginner-friendly markets terminology coach.
Explain trading and investing language in plain English. Define jargon before using it,
give a short example when helpful, and distinguish historical indicators from forecasts.
You may explain concepts such as bid/ask spread, market cap, volume, beta, RSI, MACD,
moving averages, implied and realized volatility, drawdown, P/E, EPS, ETFs, dividends,
short interest, earnings, guidance, support/resistance, and order types.
Do not recommend buying, selling, holding, or trading a specific security; do not make
price predictions or claim to know current market conditions. If asked about a live
quote or breaking news, say this chat does not fetch live research. Keep answers concise,
beginner-friendly, and educational. This is not personalized financial advice."""


def get_api_key() -> str:
    """Read a key from the server environment or Streamlit secrets; never send it to JS."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        return str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    except Exception:
        return ""


def get_model() -> str:
    """Use an optional server-side model override or the configured default."""
    model = os.environ.get("MARKET_LENS_AI_MODEL", "").strip()
    if model:
        return model
    try:
        import streamlit as st

        return str(st.secrets.get("MARKET_LENS_AI_MODEL", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
    except Exception:
        return DEFAULT_MODEL


def explain_from_glossary(question: str) -> str:
    """Small offline fallback when no AI key is configured."""
    terms = {
        "bid ask spread": "The bid is the highest displayed price a buyer offers; the ask is the lowest price a seller requests. The spread is ask minus bid. A narrower spread often means lower trading friction, though it does not guarantee a good price.",
        "spread": "The bid/ask spread is the gap between the best displayed buy price (bid) and sell price (ask). It is one part of trading cost.",
        "market cap": "Market capitalization is share price multiplied by shares outstanding. It describes the market value of a company's equity, not the company's cash or total enterprise value.",
        "volume": "Trading volume is the number of shares or contracts traded during a period. High volume can indicate more activity; volume alone does not tell you whether activity is bullish or bearish.",
        "beta": "Beta estimates how much an asset's returns have moved with a benchmark's returns. A beta above 1 has historically moved more than the benchmark on average; it is not a forecast.",
        "rsi": "The Relative Strength Index (RSI) summarizes recent gains versus losses on a 0–100 scale. Jujosmi Trade uses Wilder's 14-period RSI. Above 70 is often called overbought and below 30 oversold, but neither level guarantees a reversal.",
        "macd": "MACD compares shorter- and longer-term exponential moving averages. Jujosmi Trade compares the MACD line with its signal line; crossovers are historical momentum signals and can lag or whipsaw.",
        "moving average": "A moving average is the mean price over a rolling number of observations. Jujosmi Trade requires every close in the named 20-, 50-, or 200-session window; it does not fill a short history with a partial average.",
        "volatility": "Volatility describes how widely returns have varied. It does not describe direction. Jujosmi Trade's expected-move range is a one-standard-deviation estimate, not a price target.",
        "implied volatility": "Implied volatility is backed out from option prices and reflects the market's option pricing for future variability. It is not a direction signal or a guarantee of future movement.",
        "realized volatility": "Realized volatility measures how much past returns varied. Jujosmi Trade annualizes the sample standard deviation of 30 daily returns using the square root of 252.",
        "drawdown": "A drawdown is the percentage fall from a previous peak to a later value. It describes a past decline, not the probability or timing of a recovery.",
        "p/e": "The price-to-earnings (P/E) ratio compares share price with earnings per share. It can be misleading when earnings are negative, unusually high/low, or measured across different periods.",
        "eps": "Earnings per share (EPS) is a company's earnings allocated per share, using a stated share-count method. Compare the period and adjusted-versus-reported definition before interpreting it.",
        "etf": "An exchange-traded fund (ETF) holds a basket of assets and trades on an exchange. Jujosmi Trade uses sector ETFs as proxies for sector performance; they are not the same as every stock in that sector.",
        "short interest": "Short interest is the number of shares sold short and not yet covered, usually reported periodically. It can be stale and does not by itself predict a short squeeze or price decline.",
        "support resistance": "Support and resistance are chart-analysis terms for price areas where trading previously paused or reversed. They are interpretations of past price action, not guaranteed floors or ceilings.",
        "limit order": "A limit order sets the worst price you are willing to accept: a maximum buy price or minimum sell price. It may not execute. Jujosmi Trade is read-only and does not place orders.",
        "market order": "A market order seeks execution promptly at available prices, but the final price can differ from the last quote, especially in fast or illiquid markets. Jujosmi Trade cannot place orders.",
        "earnings guidance": "Guidance is management's outlook for future business results. It is a company estimate, can change, and is not a guarantee.",
    }
    lowered = " ".join(question.lower().replace("/", " ").split())
    for term in sorted(terms, key=len, reverse=True):
        if term in lowered:
            return terms[term]
    return ("AI chat is not connected yet, so I can only answer built-in glossary terms offline. "
            "Try asking about RSI, MACD, beta, market cap, bid/ask spread, volatility, "
            "drawdown, P/E, EPS, ETFs, or order types. Add an OpenAI API key to enable "
            "open-ended terminology questions.")


def ask_ai(messages: list[dict], api_key: str | None = None) -> str:
    """Ask the configured OpenAI Responses API without exposing the key to the browser."""
    key = (api_key if api_key is not None else get_api_key()).strip()
    if not key:
        question = next((item.get("content", "") for item in reversed(messages) if item.get("role") == "user"), "")
        return explain_from_glossary(question)
    history = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        role = message.get("role")
        content = str(message.get("content", ""))[:MAX_MESSAGE_CHARS]
        if role in ("user", "assistant") and content.strip():
            history.append({"role":role, "content":content})
    payload = {
        "model":get_model(),
        "instructions":SYSTEM_INSTRUCTIONS,
        "input":history,
        "max_output_tokens":450,
        "store":False,
    }
    request = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":f"Bearer {key}", "Content-Type":"application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=35) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 401:
            return "The AI provider rejected the API key. Check OPENAI_API_KEY or your Streamlit secret."
        if exc.code == 429:
            return "The AI provider is rate-limiting requests or the account has no available quota. Try again later or check its usage settings."
        return f"The AI provider returned HTTP {exc.code}. Try again later."
    except (URLError, TimeoutError, OSError):
        return "The AI provider could not be reached. Check your internet connection and try again."
    except (json.JSONDecodeError, KeyError, TypeError):
        return "The AI provider returned an unreadable response. Try again later."

    for item in result.get("output", []):
        if item.get("type") == "message":
            text = "".join(part.get("text", "") for part in item.get("content", []) if part.get("type") == "output_text")
            if text.strip():
                return text.strip()
    return "I couldn't find a text answer in the AI response. Please try rephrasing your question."


def floating_chat(messages: list[dict], position: dict | None = None, ai_enabled: bool = False):
    """Render the movable corner chat and return one frontend action, if any."""
    global _COMPONENT
    if _COMPONENT is None:
        _COMPONENT = components.declare_component(
            "market_lens_ai_helper",
            path=str(Path(__file__).with_name("chat_component")),
        )
    return _COMPONENT(messages=messages, position=position, ai_enabled=ai_enabled,
                      default=None, key="market_lens_ai_helper")
