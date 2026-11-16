from __future__ import annotations

import logging
import os
import re
import threading
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import (
    ApiEnvelope, ChartData, DiscoveryCalendarData, DiscoveryData, NewsEventsData, OverviewData,
    ResearchData, TechnicalAnalysis, TickerSearchData, WatchlistSummary, WatchlistSummaryData,
)
from .providers import SyntheticOfflineProvider
from .providers.cache import CachePolicy, ProviderCache
from .providers.contracts import ProviderResult
from .sec_edgar.client import SecAccessBlocked, SecClientError, SecConfigurationError, SecEdgarHttpClient, SecEdgarSettings, SecRateLimited
from .sec_edgar.mapping import SecCompanyReport, SecMappingError
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
_sec_request_slots = threading.BoundedSemaphore(4)
_sec_init_lock = threading.Lock()


def allowed_origins() -> list[str]:
    configured = os.getenv("TRADE_UI_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174")
    origins = [item.strip() for item in configured.split(",") if item.strip()]
    if not origins:
        raise RuntimeError("At least one local frontend origin must be configured.")
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError("Development CORS origins must be explicit http localhost origins.")
    return origins


@asynccontextmanager
async def lifespan(_app):
    try:
        yield
    finally:
        close_sec_client()


app = FastAPI(title="Jujosmi Trade UI 2.0 Demo API", version="0.1.0", docs_url="/docs", redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver", "testclient", "[::1]"])
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


@app.get(f"{API_PREFIX}/companies/{{symbol}}/sec-research", response_model=ApiEnvelope[SecCompanyReport])
def get_sec_research(symbol: Annotated[str, Path(min_length=1, max_length=10, pattern=SYMBOL_PATTERN)]):
    """Read official SEC submissions and Company Facts; never used by chart calculations."""
    global _sec_service, _sec_client
    if not _sec_request_slots.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="SEC research is busy. Please retry shortly.")
    try:
        try:
            if _sec_service is None:
                with _sec_init_lock:
                    if _sec_service is None:
                        _sec_client = SecEdgarHttpClient(SecEdgarSettings.from_env())
                        _sec_service = SecCompanyResearchService(_sec_client, live_data_verified=True)
            report = _sec_service.get_company_report(symbol.upper())
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
