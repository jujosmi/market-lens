"""Loopback-only development endpoint for the local Kestrel preview."""
from datetime import datetime, timezone
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .bridge_v1 import BridgeValidationError, freshness_status, is_local_peer, load_bundle_from_directory

router = APIRouter(tags=["development-only"])


def _enabled(request: Request) -> bool:
    if os.getenv("JUJOSMI_KESTREL_BRIDGE_ENABLED") != "true":
        return False
    if os.getenv("JUJOSMI_TRADE_RUNTIME_MODE") != "local_development":
        return False
    if os.getenv("RENDER", "").strip():
        return False
    return is_local_peer(request.url.hostname, request.client.host if request.client else None)


@router.get("/dev/kestrel/research")
def get_kestrel_research_preview(request: Request):
    if not _enabled(request) or request.query_params:
        raise HTTPException(status_code=404, detail="Research preview is unavailable.")
    try:
        bundle = load_bundle_from_directory(os.getenv("JUJOSMI_KESTREL_BRIDGE_FIXTURE_DIR"))
    except BridgeValidationError:
        raise HTTPException(status_code=503, detail="The approved synthetic research preview is unavailable.") from None
    observation = bundle["record"]["observation_timing"]["observation_timestamp_utc"]
    stale, age_hours = freshness_status(observation)
    return JSONResponse({
        "preview_contract_id": "JUJOSMI_TRADE_KESTREL_LOCAL_PREVIEW_V1",
        "status": "accepted",
        "source_mode": "synthetic_offline_only",
        "freshness": "stale" if stale else "historical_synthetic",
        "stale": stale,
        "current_market_data": False,
        "age_hours": age_hours,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bundle": bundle,
    }, headers={"Cache-Control": "no-store, max-age=0"})