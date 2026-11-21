from __future__ import annotations

import logging
import os
import re
import threading
import ipaddress
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import (
    ApiEnvelope, ChartData, DiscoveryCalendarData, DiscoveryData, NewsEventsData, OverviewData,
    ResearchData, SecDirectoryData, SecFilingsData, SecIndustryData, SecWatchlistActivityData, SecWatchlistActivityRequest,
    SecWatchlistActivityEntry, TechnicalAnalysis, TickerSearchData, WatchlistSummary, WatchlistSummaryData,
)
from .providers import SyntheticOfflineProvider
from app.integrations.kestrel.router import router as kestrel_research_router
from .providers.cache import CachePolicy, ProviderCache
from .providers.contracts import ProviderResult
from .sec_edgar.client import SecAccessBlocked, SecClientError, SecConfigurationError, SecEdgarHttpClient, SecEdgarSettings, SecRateLimited
from .sec_edgar.mapping import SecCompanyReport, SecMappingError
from .sec_edgar.discovery import SecDiscoveryService, WATCHLIST_ACTIVITY_FORMS
from .sec_edgar.service import SecCompanyResearchService

LOGGER = logging.getLogger("jujosmi_trade_api")
API_PREFIX = "/api/v1"
SYMBOL_PATTERN = r"^[A-Z][A-Z0-9.-]{0,9}$"
provider = SyntheticOfflineProvider()
provider_cache = ProviderCache(CachePolicy(
    success_ttl_seconds=300,
    failure_ttl_seconds=5,
    stale_if_error_seconds=900,
    max_entries=128,
    timeout_seconds=3,
))
_sec_service: SecCompanyResearchService | None = None
_sec_client: SecEdgarHttpClient | None = None
_sec_discovery_service: SecDiscoveryService | None = None
_sec_request_slots = threading.BoundedSemaphore(4)
_sec_init_lock = threading.Lock()


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_LOCAL_ORIGINS = (
    "http://127.0.0.1:5173,http://localhost:5173,"
    "http://127.0.0.1:5174,http://localhost:5174"
)
DNS_HOST_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def _render_mode() -> bool:
    return os.getenv("RENDER", "").strip().lower() == "true"


def _valid_dns_hostname(hostname: str) -> bool:
    return hostname == hostname.lower() and DNS_HOST_PATTERN.fullmatch(hostname) is not None


def _validated_origin(origin: str) -> tuple[str, str]:
    """Validate and return (scheme, host) for a canonical browser origin."""
    if (
        not origin
        or origin != origin.strip()
        or any(character.isspace() for character in origin)
        or origin == "*"
        or "\\" in origin
        or "?" in origin
        or "#" in origin
    ):
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must contain canonical origin URLs.")
    try:
        parsed = urlsplit(origin)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS contains a malformed origin URL.") from exc

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must contain origin URLs without credentials or paths.")

    try:
        ipaddress.ip_address(hostname)
        is_ip_address = True
    except ValueError:
        is_ip_address = False

    if is_ip_address:
        canonical_host = f"[{hostname}]" if ":" in hostname else hostname
    else:
        if not _valid_dns_hostname(hostname) and hostname != "localhost":
            raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS contains an invalid hostname.")
        canonical_host = hostname

    if (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443):
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must omit default ports from canonical origins.")
    expected = f"{parsed.scheme}://{canonical_host}" + (f":{port}" if port is not None else "")
    if origin != expected:
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must contain canonical origin URLs.")

    if parsed.scheme == "http":
        if _render_mode() or hostname not in LOCAL_HOSTS:
            raise RuntimeError("HTTP CORS origins are restricted to explicit localhost development origins.")
    else:
        if not _render_mode():
            raise RuntimeError("HTTPS CORS origins are accepted only in hosted Render mode.")
        if hostname in LOCAL_HOSTS or is_ip_address or not _valid_dns_hostname(hostname):
            raise RuntimeError("Hosted HTTPS CORS origins must use an explicit public DNS hostname.")
    return parsed.scheme, hostname


def allowed_origins() -> list[str]:
    configured = os.getenv("TRADE_UI_ALLOWED_ORIGINS")
    if _render_mode() and configured is None:
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must explicitly list the hosted frontend origin on Render.")
    if configured is None:
        configured = DEFAULT_LOCAL_ORIGINS
    if not configured.strip():
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must contain at least one explicit origin.")
    origins = [item.strip() for item in configured.split(",")]
    if any(not item for item in origins):
        raise RuntimeError("TRADE_UI_ALLOWED_ORIGINS must not contain empty entries.")
    for origin in origins:
        _validated_origin(origin)
    return origins


def allowed_hosts() -> list[str]:
    if not _render_mode():
        return ["127.0.0.1", "localhost", "testserver", "testclient", "[::1]"]
    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if not _valid_dns_hostname(hostname):
        raise RuntimeError("Render must provide a valid RENDER_EXTERNAL_HOSTNAME for trusted-host validation.")
    return [hostname]


@asynccontextmanager
async def lifespan(_app):
    try:
        yield
    finally:
        close_sec_client()


app = FastAPI(title="Jujosmi Trade UI 2.0 Demo API", version="0.1.0", docs_url="/docs", redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
app.include_router(kestrel_research_router, prefix=API_PREFIX)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


def envelope(data, status: str = "ok", warnings: list[str] | None = None, *, source: str = "synthetic-fixtures",
             as_of: str | None = None, provenance: str | None = None, missing_fields: list[str] | None = None):
    return ApiEnvelope(data=data, status=status, source=source, as_of=as_of, provenance=provenance,
                       missing_fields=missing_fields or [], warnings=warnings or [])


def provider_envelope(result: ProviderResult):
    """Translate provider outcome and provenance to the stable public API envelope."""
    if result.data is None:
        status_code = {"invalid": 422, "unavailable": 404, "rate_limited": 429}.get(result.status, 500)
        message = result.warnings[0] if result.warnings else "Provider data is unavailable."
        raise HTTPException(status_code=status_code, detail=message)
    provenance = result.provenance.calculation or f"{result.provenance.provider_id}:{result.provenance.product}"
    response = envelope(
        result.data,
        status=result.status,
        warnings=result.warnings,
        source="python-engine-snapshot" if result.provenance.source_revision else "synthetic-fixtures",
        as_of=result.provenance.as_of.isoformat() if result.provenance.as_of else None,
        provenance=provenance,
        missing_fields=result.missing_fields,
    )
    response.stale = result.stale
    return response


async def fetch_provider(operation: str, parameters: dict, loader):
    """Run a provider request under bounded timeout and provider-scoped cache policy."""
    provenance = provider._provenance(operation)
    return await provider_cache.get_or_load(provider.provider_id, operation, parameters, loader, provenance)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    LOGGER.info("Rejected invalid API input (%s validation issue(s))", len(exc.errors()))
    return JSONResponse(status_code=422, content=ApiEnvelope[None](data=None, status="invalid", warnings=["Request parameters are invalid or outside the allowed limits."]).model_dump())


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    status = ("unavailable" if exc.status_code in {404, 503} else "invalid" if exc.status_code in {400, 422}
              else "rate_limited" if exc.status_code == 429 else "failed")
    message = str(exc.detail) if exc.status_code < 500 or (exc.status_code == 503 and str(exc.detail).startswith("SEC ")) else "The demonstration API could not complete this request."
    return JSONResponse(status_code=exc.status_code, content=ApiEnvelope[None](data=None, status=status, warnings=[message]).model_dump())


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception):
    LOGGER.exception("Unhandled synthetic API failure (%s)", type(exc).__name__)
    return JSONResponse(status_code=500, content=ApiEnvelope[None](data=None, status="failed", warnings=["The demonstration API could not complete this request."]).model_dump())


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "synthetic-fixtures"}


@app.get(f"{API_PREFIX}/overview", response_model=ApiEnvelope[OverviewData])
async def get_overview():
    return provider_envelope(await fetch_provider("overview", {}, provider.overview))


@app.get(f"{API_PREFIX}/tickers/search", response_model=ApiEnvelope[TickerSearchData])
async def search_tickers(q: Annotated[str, Query(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9.& -]+$")]):
    normalized = re.sub(r"\s+", " ", q.strip())
    if not normalized:
        raise HTTPException(status_code=422, detail="Search query is required.")
    return provider_envelope(await fetch_provider("ticker_search", {"query": normalized.casefold()}, lambda: provider.ticker_search(normalized)))


@app.get(f"{API_PREFIX}/tickers/{{symbol}}/chart", response_model=ApiEnvelope[ChartData])
async def get_chart(
    symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)],
    range: Literal["1D", "1W", "1M", "3M", "1Y", "ALL"] = "1M",
    interval: Literal["15m", "30m", "1h", "2h", "12h", "1d"] = "1d",
):
    return provider_envelope(await fetch_provider("history", {"symbol": symbol, "period": range, "interval": interval}, lambda: provider.history(symbol, range, interval)))


@app.get(f"{API_PREFIX}/tickers/{{symbol}}/analysis", response_model=ApiEnvelope[TechnicalAnalysis])
async def get_analysis(symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)]):
    return provider_envelope(await fetch_provider("technical_analysis", {"symbol": symbol}, lambda: provider.technical_analysis(symbol)))


@app.get(f"{API_PREFIX}/discovery", response_model=ApiEnvelope[DiscoveryData])
async def get_discovery(
    sector: Annotated[str | None, Query(max_length=48, pattern=r"^[A-Za-z0-9 &.-]*$")] = None,
    industry: Annotated[str | None, Query(max_length=64, pattern=r"^[A-Za-z0-9 &.-]*$")] = None,
    q: Annotated[str, Query(max_length=32, pattern=r"^[A-Za-z0-9.& -]*$")] = "",
):
    sector_value = sector.strip() if sector else None
    industry_value = industry.strip() if industry else None
    query = re.sub(r"\s+", " ", q.strip())
    return provider_envelope(await fetch_provider("directory", {"sector": sector_value, "industry": industry_value, "query": query.casefold()}, lambda: provider.directory(sector_value, industry_value, query)))


@app.get(f"{API_PREFIX}/discovery/calendar", response_model=ApiEnvelope[DiscoveryCalendarData])
async def get_discovery_calendar(
    kind: Literal["earnings", "ipos"] = "earnings",
    window_days: Annotated[int, Query(ge=1, le=180)] = 60,
):
    return provider_envelope(await fetch_provider("calendar", {"kind": kind, "window_days": window_days}, lambda: provider.calendar(kind, window_days)))


@app.get(f"{API_PREFIX}/watchlist/summaries", response_model=ApiEnvelope[WatchlistSummaryData])
async def get_watchlist_summaries(
    symbols: Annotated[str, Query(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9., -]+$")],
):
    raw_symbols = [part.strip().upper() for part in symbols.split(",") if part.strip()]
    if not raw_symbols or len(raw_symbols) > 10:
        raise HTTPException(status_code=422, detail="Provide between one and ten supported symbols.")
    requested = list(dict.fromkeys(raw_symbols))
    if len(requested) > 10:
        raise HTTPException(status_code=422, detail="Provide between one and ten supported symbols.")
    return provider_envelope(await fetch_provider("watchlist_summaries", {"symbols": requested}, lambda: provider.watchlist_summaries(",".join(requested))))


@app.get(f"{API_PREFIX}/companies/{{symbol}}/research", response_model=ApiEnvelope[ResearchData])
async def get_research(symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)]):
    return provider_envelope(await fetch_provider("company_research", {"symbol": symbol}, lambda: provider.company_research(symbol)))


@app.get(f"{API_PREFIX}/companies/{{symbol}}/news-events", response_model=ApiEnvelope[NewsEventsData])
async def get_news_events(symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)]):
    return provider_envelope(await fetch_provider("news_events", {"symbol": symbol}, lambda: provider.news_events(symbol)))


def close_sec_client() -> None:
    if _sec_client is not None:
        _sec_client.close()


def _get_sec_client() -> SecEdgarHttpClient:
    """Initialize the single shared SEC adapter, retaining its cache and limiter."""
    global _sec_client, _sec_discovery_service
    if _sec_client is None:
        with _sec_init_lock:
            if _sec_client is None:
                _sec_client = SecEdgarHttpClient(SecEdgarSettings.from_env())
                _sec_discovery_service = SecDiscoveryService(_sec_client)
    return _sec_client


def _sec_error_http(exc: Exception) -> HTTPException:
    if isinstance(exc, SecConfigurationError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, SecRateLimited):
        return HTTPException(status_code=429, detail=str(exc))
    if isinstance(exc, SecAccessBlocked):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, SecClientError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, SecMappingError):
        if str(exc).startswith(("SEC payload", "SEC Company Facts issuer", "SEC submissions issuer", "SEC company data", "SEC submissions data", "SEC recent filings", "SEC standard taxonomy")):
            LOGGER.warning("SEC identity or response validation rejected provider data (%s)", type(exc).__name__)
            return HTTPException(status_code=503, detail="SEC returned inconsistent or unsupported company data.")
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=503, detail="SEC data is currently unavailable.")


@app.get(f"{API_PREFIX}/discovery/companies", response_model=ApiEnvelope[SecDirectoryData])
def get_sec_company_directory(
    q: Annotated[str, Query(max_length=60, pattern=r"^[A-Za-z0-9 .&,'-]*$")] = "",
    exchange: Annotated[str | None, Query(max_length=40, pattern=r"^[A-Za-z0-9 .&-]*$")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    """Search the cached official SEC ticker/CIK/exchange association file locally."""
    global _sec_discovery_service
    try:
        client = _get_sec_client()
        client.begin_report()
        if _sec_discovery_service is None:
            _sec_discovery_service = SecDiscoveryService(client)
        data = _sec_discovery_service.list_companies(query=" ".join(q.split()), exchange=exchange, limit=limit, offset=offset)
    except (SecConfigurationError, SecRateLimited, SecAccessBlocked, SecClientError, SecMappingError) as exc:
        raise _sec_error_http(exc) from exc
    return ApiEnvelope[SecDirectoryData](data=data, status="ok", source="sec-edgar",
        freshness="cached" if client.report_cached else "live", as_of=datetime.now(timezone.utc).isoformat(),
        provenance="SEC EDGAR company_tickers_exchange.json", warnings=[])


@app.get(f"{API_PREFIX}/discovery/industry-companies", response_model=ApiEnvelope[SecIndustryData])
def get_sec_industry_companies(
    q: Annotated[str, Query(min_length=2, max_length=60, pattern=r"^[A-Za-z0-9 .&,'-]+$")],
    exchange: Annotated[str | None, Query(max_length=40, pattern=r"^[A-Za-z0-9 .&-]*$")] = None,
    limit: Annotated[int, Query(ge=1, le=10)] = 10,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    """Classify only a bounded, user-searched page using issuer SEC submissions."""
    global _sec_discovery_service
    try:
        client = _get_sec_client()
        client.begin_report()
        if _sec_discovery_service is None:
            _sec_discovery_service = SecDiscoveryService(client)
        data, warnings = _sec_discovery_service.industry_companies(
            query=" ".join(q.split()), exchange=exchange, limit=limit, offset=offset,
        )
    except (SecConfigurationError, SecRateLimited, SecAccessBlocked, SecClientError, SecMappingError) as exc:
        raise _sec_error_http(exc) from exc
    status = "partial" if warnings or data.unclassified_count else "ok"
    return ApiEnvelope[SecIndustryData](
        data=data, status=status, source="sec-edgar",
        freshness="cached" if client.report_cached else "live",
        as_of=datetime.now(timezone.utc).isoformat(),
        provenance="Official SEC issuer submissions SIC code and description", warnings=warnings,
    )


@app.get(f"{API_PREFIX}/discovery/filings/{{symbol}}", response_model=ApiEnvelope[SecFilingsData])
def get_sec_discovery_filings(
    symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)],
    exchange: Annotated[str | None, Query(max_length=40, pattern=r"^[A-Za-z0-9 .&-]*$")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    """Load recent supported filing rows only for a specific, selected SEC issuer."""
    global _sec_discovery_service
    try:
        client = _get_sec_client()
        client.begin_report()
        if _sec_discovery_service is None:
            _sec_discovery_service = SecDiscoveryService(client)
        data, warnings = _sec_discovery_service.recent_filings(symbol.upper(), exchange=exchange, limit=limit)
    except (SecConfigurationError, SecRateLimited, SecAccessBlocked, SecClientError, SecMappingError) as exc:
        raise _sec_error_http(exc) from exc
    return ApiEnvelope[SecFilingsData](data=data, status="partial" if warnings else "ok", source="sec-edgar",
        freshness="cached" if client.report_cached else "live", as_of=datetime.now(timezone.utc).isoformat(),
        provenance="Official SEC EDGAR issuer submissions", warnings=warnings)


@app.post(f"{API_PREFIX}/discovery/filings/watchlist", response_model=ApiEnvelope[SecWatchlistActivityData])
def get_sec_watchlist_filing_activity(payload: SecWatchlistActivityRequest):
    """Retrieve a bounded set of recent company filings sequentially through the shared SEC client."""
    global _sec_discovery_service
    try:
        client = _get_sec_client()
        client.begin_report()
        if _sec_discovery_service is None:
            _sec_discovery_service = SecDiscoveryService(client)
    except (SecConfigurationError, SecRateLimited, SecAccessBlocked, SecClientError, SecMappingError) as exc:
        raise _sec_error_http(exc) from exc

    entries: list[SecWatchlistActivityEntry] = []
    for company in payload.companies:
        ticker = company.ticker.upper()
        try:
            data, warnings = _sec_discovery_service.recent_filings(
                ticker,
                exchange=company.exchange,
                limit=20,
                allowed_forms=WATCHLIST_ACTIVITY_FORMS,
            )
            entries.append(SecWatchlistActivityEntry(
                requested_ticker=ticker,
                requested_exchange=company.exchange,
                status="partial" if warnings else "ok",
                data=data,
                warnings=warnings,
            ))
        except (SecConfigurationError, SecRateLimited, SecAccessBlocked, SecClientError, SecMappingError) as exc:
            http_error = _sec_error_http(exc)
            status = "rate_limited" if isinstance(exc, SecRateLimited) else "unavailable"
            entries.append(SecWatchlistActivityEntry(
                requested_ticker=ticker,
                requested_exchange=company.exchange,
                status=status,
                error=str(http_error.detail),
            ))

    unavailable_count = sum(entry.status in {"unavailable", "rate_limited", "failed"} for entry in entries)
    partial = unavailable_count > 0 or any(entry.status == "partial" for entry in entries)
    warnings = [f"{unavailable_count} of {len(entries)} company filing checks were unavailable."] if unavailable_count else []
    return ApiEnvelope[SecWatchlistActivityData](
        data=SecWatchlistActivityData(
            entries=entries,
            limit=5,
            disclosure="Recent SEC issuer submissions are factual filing records, not forecasts or investment advice. No filing is interpreted as a prediction.",
        ),
        status="partial" if partial else "ok",
        source="sec-edgar",
        freshness="cached" if client.report_cached else "live",
        as_of=datetime.now(timezone.utc).isoformat(),
        provenance="Official SEC EDGAR issuer submissions",
        warnings=warnings,
    )


@app.get(f"{API_PREFIX}/companies/{{symbol}}/sec-research", response_model=ApiEnvelope[SecCompanyReport])
def get_sec_research(
    symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)],
    exchange: Annotated[str | None, Query(max_length=40, pattern=r"^[A-Za-z0-9 .&-]*$")] = None,
):
    """Read official SEC submissions and Company Facts; never used by chart calculations."""
    global _sec_service, _sec_client
    if not _sec_request_slots.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="SEC research is busy. Please retry shortly.")
    try:
        try:
            if _sec_service is None:
                client = _get_sec_client()
                with _sec_init_lock:
                    if _sec_service is None:
                        _sec_service = SecCompanyResearchService(client, live_data_verified=True)
            report = _sec_service.get_company_report(symbol.upper(), exchange=exchange)
        except SecConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SecRateLimited as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except SecAccessBlocked as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SecClientError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SecMappingError as exc:
            provider_mismatch = str(exc).startswith(("SEC payload", "SEC Company Facts issuer", "SEC submissions issuer", "SEC company data", "SEC submissions data", "SEC recent filings", "SEC standard taxonomy"))
            if provider_mismatch:
                LOGGER.warning("SEC identity or response validation rejected provider data (%s)", type(exc).__name__)
                raise HTTPException(status_code=503, detail="SEC returned inconsistent or unsupported company data.") from exc
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        _sec_request_slots.release()
    return ApiEnvelope[SecCompanyReport](data=report, status=report.status, source="sec-edgar",
        freshness=report.freshness, as_of=report.as_of, provenance="Official SEC EDGAR submissions and Company Facts",
        missing_fields=report.missing_fields, warnings=report.warnings)
