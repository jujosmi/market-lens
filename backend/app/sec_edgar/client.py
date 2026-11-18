"""Bounded, server-side adapter for official SEC EDGAR JSON endpoints."""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from .mapping import SecIdentity, SecMappingError

LOGGER = logging.getLogger("jujosmi_trade_api.sec_edgar")
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_DATA_ROOT = "https://data.sec.gov"


class SecClientError(RuntimeError):
    """Sanitized, user-safe SEC adapter failure."""


class SecConfigurationError(SecClientError):
    pass


class SecAccessBlocked(SecClientError):
    pass


class SecRateLimited(SecClientError):
    pass


@dataclass(frozen=True)
class SecEdgarSettings:
    user_agent: str

    @classmethod
    def from_env(cls) -> "SecEdgarSettings":
        value = os.getenv("SEC_EDGAR_USER_AGENT", "").strip()
        if len(value) < 10 or not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value):
            raise SecConfigurationError("SEC EDGAR is not configured with an identifying User-Agent contact.")
        if any(marker in value.lower() for marker in ("example.com", "your.email", "your-domain", "changeme", "placeholder")):
            raise SecConfigurationError("SEC EDGAR User-Agent must contain a real identifying contact.")
        return cls(user_agent=value)


class SharedRateLimiter:
    """A process-wide minimum interval, shared by all SEC client instances."""
    def __init__(self, interval_seconds: float = 0.5):
        self.interval = interval_seconds
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            delay = self.interval - (time.monotonic() - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


_GLOBAL_LIMITER = SharedRateLimiter()
_BLOCKED = threading.Event()


class SecEdgarHttpClient:
    """Only calls fixed SEC endpoints; caches successful JSON responses in memory."""
    def __init__(self, settings: SecEdgarSettings | None = None, *, transport: httpx.BaseTransport | None = None,
                 limiter: SharedRateLimiter | None = None, timeout_seconds: float = 7.0):
        self.settings = settings or SecEdgarSettings.from_env()
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds, connect=3.0), transport=transport,
            headers={"User-Agent": self.settings.user_agent, "Accept": "application/json"}, follow_redirects=False,
        )
        self._limiter = limiter or _GLOBAL_LIMITER
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._cache_lock = threading.Lock()
        self.cache_hits = 0
        self.cache_misses = 0
        self._request_state = threading.local()

    def begin_report(self) -> None:
        self._request_state.all_cached = True

    @property
    def report_cached(self) -> bool:
        return bool(getattr(self._request_state, "all_cached", False))

    def close(self) -> None:
        self._client.close()

    def get_ticker_directory(self) -> list[dict[str, Any]]:
        """Return the cached, normalized SEC ticker/CIK/exchange directory."""
        rows = self._get_json(TICKER_MAP_URL, ttl=86400, category="ticker-map")
        if not isinstance(rows, list):
            raise SecClientError("SEC issuer identity data was unavailable or malformed.")
        return rows

    def resolve_ticker(self, ticker: str, exchange: str | None = None) -> SecIdentity | None:
        symbol = ticker.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
            raise SecMappingError("Ticker symbol is invalid.")
        rows = self.get_ticker_directory()
        matches = [row for row in rows if isinstance(row, dict) and str(row.get("ticker", "")).upper() == symbol]
        if exchange:
            matches = [row for row in matches if str(row.get("exchange", "")).strip().casefold() == exchange.strip().casefold()]
        # Ambiguous ticker symbols are not guessed; callers can qualify by exchange.
        if len(matches) != 1:
            return None
        row = matches[0]
        try:
            cik = str(int(row["cik"])).zfill(10)
            exchange = str(row.get("exchange", "")).strip() or None
            return SecIdentity(cik=cik, ticker=symbol, name=str(row["name"]).strip(), exchange=exchange,
                               identity_source="sec_company_tickers")
        except (KeyError, TypeError, ValueError) as exc:
            raise SecClientError("SEC issuer identity data was malformed.") from exc

    def get_submissions(self, cik: str) -> dict[str, Any]:
        self._validate_cik(cik)
        payload = self._get_json(f"{SEC_DATA_ROOT}/submissions/CIK{cik}.json", ttl=900, category="submissions")
        if not isinstance(payload, dict) or not isinstance(payload.get("filings"), dict):
            LOGGER.warning("SEC submissions response had an unexpected JSON shape")
            raise SecClientError("SEC submissions data is currently unavailable.")
        return payload

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        self._validate_cik(cik)
        payload = self._get_json(f"{SEC_DATA_ROOT}/api/xbrl/companyfacts/CIK{cik}.json", ttl=900, category="company-facts")
        if not isinstance(payload, dict) or not isinstance(payload.get("facts"), dict):
            LOGGER.warning("SEC Company Facts response had an unexpected JSON shape")
            raise SecClientError("SEC Company Facts data is currently unavailable.")
        return payload

    @staticmethod
    def _validate_cik(cik: str) -> None:
        if not re.fullmatch(r"\d{10}", cik):
            raise SecMappingError("SEC CIK must contain ten digits.")

    def _get_json(self, url: str, *, ttl: int, category: str) -> Any:
        if url != TICKER_MAP_URL and not (url.startswith(f"{SEC_DATA_ROOT}/submissions/CIK") or url.startswith(f"{SEC_DATA_ROOT}/api/xbrl/companyfacts/CIK")):
            raise SecClientError("SEC endpoint is not approved for this integration.")
        if _BLOCKED.is_set():
            raise SecAccessBlocked("SEC access is temporarily disabled after an access-denied response.")
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(url)
            if cached and cached[0] > now:
                self._cache.move_to_end(url)
                self.cache_hits += 1
                return cached[1]
            self._request_state.all_cached = False
            self.cache_misses += 1
        for attempt in range(3):
            self._limiter.wait()
            try:
                with self._client.stream("GET", url) as response:
                    status_code = response.status_code
                    headers = response.headers
                    if status_code == 403:
                        _BLOCKED.set()
                        LOGGER.error("SEC %s request denied (HTTP 403); live requests disabled for this process", category)
                        raise SecAccessBlocked("SEC denied access; live SEC requests have been paused.")
                    if status_code == 429:
                        LOGGER.warning("SEC %s request rate limited (HTTP 429)", category)
                        raise SecRateLimited("SEC is rate limiting requests. Please try again later.")
                    if status_code in {502, 503, 504} and attempt < 2:
                        retry_after = headers.get("Retry-After", "")
                        try:
                            pause = min(2.0, max(0.25, float(retry_after)))
                        except ValueError:
                            pause = 0.25 * (2 ** attempt)
                        time.sleep(pause)
                        continue
                    if status_code != 200:
                        LOGGER.warning("SEC %s request failed (HTTP %s)", category, status_code)
                        raise SecClientError("SEC data is currently unavailable.")
                    body = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        body.extend(chunk)
                        if len(body) > 15 * 1024 * 1024:
                            LOGGER.warning("SEC %s response exceeded size limit", category)
                            raise SecClientError("SEC response exceeded the configured size limit.")
            except httpx.HTTPError as exc:
                LOGGER.warning("SEC %s request transport failure (%s)", category, type(exc).__name__)
                raise SecClientError("SEC data could not be reached. Please try again later.") from exc
            try:
                data = json.loads(body, parse_float=Decimal, parse_int=Decimal)
            except (ValueError, UnicodeDecodeError) as exc:
                LOGGER.warning("SEC %s returned invalid JSON", category)
                raise SecClientError("SEC returned an unreadable response.") from exc
            if category == "ticker-map":
                data = self._normalize_ticker_directory(data)
            valid_shape = (isinstance(data, list) if category == "ticker-map" else
                           isinstance(data, dict) and isinstance(data.get("filings"), dict) if category == "submissions" else
                           isinstance(data, dict) and isinstance(data.get("facts"), dict))
            if not valid_shape:
                LOGGER.warning("SEC %s response had an unexpected JSON shape", category)
                raise SecClientError("SEC returned an unsupported response shape.")
            with self._cache_lock:
                self._cache[url] = (time.monotonic() + ttl, data)
                self._cache.move_to_end(url)
                while len(self._cache) > 8:
                    self._cache.popitem(last=False)
            return data
        LOGGER.warning("SEC %s request failed after bounded retries", category)
        raise SecClientError("SEC data is temporarily unavailable.")

    @staticmethod
    def _normalize_ticker_directory(payload: Any) -> list[dict[str, Any]]:
        """Normalize SEC's columnar ticker/exchange file to issuer rows.

        The official company_tickers_exchange.json shape is an object with a
        ``fields`` array and a ``data`` array of ordered row arrays. Keeping
        this conversion at the HTTP boundary lets ticker identity resolution
        consume one predictable representation without weakening validation.
        """
        if not isinstance(payload, dict):
            raise SecClientError("SEC returned an unsupported response shape.")
        fields = payload.get("fields")
        rows = payload.get("data")
        if (not isinstance(fields, list) or not fields
                or not all(isinstance(field, str) and field for field in fields)
                or len(set(fields)) != len(fields)
                or not {"cik", "name", "ticker"}.issubset(fields)
                or not isinstance(rows, list)):
            raise SecClientError("SEC returned an unsupported response shape.")

        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, list) or len(row) != len(fields):
                raise SecClientError("SEC returned an unsupported response shape.")
            issuer = dict(zip(fields, row, strict=True))
            cik, name, ticker = issuer.get("cik"), issuer.get("name"), issuer.get("ticker")
            try:
                cik_number = int(cik) if isinstance(cik, (int, Decimal)) and not isinstance(cik, bool) else 0
            except (ValueError, TypeError, OverflowError):
                cik_number = 0
            if (cik_number <= 0 or cik != cik_number
                    or not isinstance(name, str) or not name.strip()
                    or not isinstance(ticker, str) or not ticker.strip()):
                raise SecClientError("SEC returned an unsupported response shape.")
            normalized.append(issuer)
        return normalized
