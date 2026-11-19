"""Independent, fail-closed validator for Kestrel research bridge V1."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

BRIDGE_ID = "KESTREL_TRADE_RESEARCH_BRIDGE_V1"
MANIFEST_ID = "KESTREL_TRADE_RESEARCH_BRIDGE_MANIFEST_V1"
M97_ID = "KESTREL_RESEARCH_API_V1"
M95_ID = "KESTREL_UNIFIED_RESEARCH_RECORD_V1"
M913_ID = "KESTREL_M9_13_OPERATIONAL_SPY_RESEARCH"
INSTRUMENT_ID = "JLC:US_ETF:SPY"
M95_SCHEMA_SHA256 = "4d7b99d4e0e7e601b3729bee5da51e5da8d2c0f29a9f454c356b51639a48d32e"
M97_SCHEMA_SHA256 = "33ad7e58151dde43470ff7b272820dd8c9b4b75d554911e250abcb4c9f54c11f"
M95_FIELDS = frozenset("schema_id schema_version methodology_version instrument timeframe_context research_observation_timestamp_utc research_availability_timestamp_utc daily_context intraday_context unified_descriptive_classification classification_type source_eligibility research_use_restrictions completeness_status data_quality_flags abstention_reasons provenance configuration configuration_sha256 record_sha256".split())
RECORD_FIELDS = frozenset("bridge_contract_id schema_version record_type producer_id source_mode scenario_id instrument observation_timing research_status m913_quality_notes source_provenance research_response".split())
MANIFEST_FIELDS = frozenset("manifest_id schema_version record_sha256 m97_response_sha256 m95_record_sha256 m913_input_sha256 m95_schema_sha256 m97_schema_sha256 source_data_sha256 source_manifest_sha256 source_row_counts synthetic_only acquisition_authorized manifest_sha256".split())
RESPONSE_FIELDS = frozenset("contract_id schema_version outcome http_status request_id served_at_utc request research_record availability data_use error".split())
VALID_CLASSIFICATIONS = frozenset("directionally_aligned directionally_conflicting mixed_or_range_bound daily_only intraday_only unavailable insufficiently_qualified".split())


class BridgeValidationError(ValueError):
    """A transfer record did not match the frozen synthetic bridge contract."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BridgeValidationError("The bridge record contains invalid JSON values.") from exc


def _digest(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _require(ok: bool, message: str = "The bridge record failed validation.") -> None:
    if not ok:
        raise BridgeValidationError(message)


def _utc(value: Any) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"))
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BridgeValidationError("The bridge timestamp is invalid.") from exc
    _require(parsed.utcoffset() == timedelta(0))
    return parsed.astimezone(timezone.utc)


def _finite_tree(value: Any) -> None:
    if isinstance(value, float):
        _require(math.isfinite(value), "The bridge record contains non-finite numeric values.")
    elif isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).casefold()
            _require(not any(term in lowered for term in ("prediction", "predictive", "forecast", "probability")), "Predictive records are not supported.")
            _finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            _finite_tree(item)


def _keys(value: Any, expected: frozenset[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def validate_bundle(bundle: Any) -> dict[str, Any]:
    """Validate exact bridge/M9.7/M9.5 structure, synthetic provenance, and hashes."""
    _finite_tree(bundle)
    _require(_keys(bundle, frozenset({"record", "manifest"})))
    record, manifest = bundle["record"], bundle["manifest"]
    _require(_keys(record, RECORD_FIELDS) and _keys(manifest, MANIFEST_FIELDS))
    _require(record["bridge_contract_id"] == BRIDGE_ID and record["schema_version"] == 1)
    _require(record["record_type"] == "descriptive_research" and record["producer_id"] == M913_ID)
    _require(record["source_mode"] == "synthetic_offline_only" and record["scenario_id"] in {"complete", "missing_intraday_segment"})
    _require(record["instrument"] == {"instrument_id": INSTRUMENT_ID, "symbol": "SPY"})
    _require(isinstance(record["m913_quality_notes"], list) and all(isinstance(x, str) for x in record["m913_quality_notes"]))

    response = record["research_response"]
    _require(_keys(response, RESPONSE_FIELDS))
    _require(response["contract_id"] == M97_ID and response["schema_version"] == 1)
    _require(response["outcome"] in {"complete", "partial", "abstained"} and response["http_status"] == 200 and response["error"] is None)
    _require(isinstance(response["request_id"], str) and 1 <= len(response["request_id"]) <= 128)
    request = response["request"]
    _require(_keys(request, frozenset({"instrument_id", "as_of_utc", "timeframe", "methodology_version"})))
    _require(request == {
        "instrument_id": INSTRUMENT_ID,
        "as_of_utc": request["as_of_utc"],
        "timeframe": "m95_unified",
        "methodology_version": "KESTREL_UNIFIED_OFFLINE_RESEARCH_M95_V1",
    })

    research = response["research_record"]
    _require(_keys(research, M95_FIELDS))
    _require(research["schema_id"] == M95_ID and research["schema_version"] == 1)
    _require(research["methodology_version"] == "KESTREL_UNIFIED_OFFLINE_RESEARCH_M95_V1")
    _require(research["classification_type"] == "descriptive_technical_state")
    _require(research["unified_descriptive_classification"] in VALID_CLASSIFICATIONS)
    _require(research["completeness_status"] in {"complete", "partial", "unavailable"})
    _require(isinstance(research["daily_context"], dict) and isinstance(research["intraday_context"], dict))
    _require(isinstance(research["timeframe_context"], dict) and set(research["timeframe_context"]) == {"daily", "intraday"})
    _require(research["instrument"].get("instrument_id") == INSTRUMENT_ID and research["instrument"].get("symbol") == "SPY")
    _require(research["source_eligibility"].get("mode") == "synthetic_offline_only")
    _require(research["source_eligibility"].get("acquisition_authorized") is False)
    _require(research["source_eligibility"].get("real_data_activation") == "NO_GO")
    for name in ("research_use_restrictions", "data_quality_flags", "abstention_reasons"):
        _require(isinstance(research[name], list) and all(isinstance(x, str) for x in research[name]))
    _require(bool(research["research_use_restrictions"]))
    _require(isinstance(research["configuration"], dict))
    _require(_is_sha(research["configuration_sha256"]) and research["configuration_sha256"] == _digest(research["configuration"]))

    timing = record["observation_timing"]
    _require(_keys(timing, frozenset({"observation_timestamp_utc", "availability_timestamp_utc", "served_at_utc"})))
    observed, available, served = (_utc(timing[k]) for k in ("observation_timestamp_utc", "availability_timestamp_utc", "served_at_utc"))
    request_time, response_served = _utc(request["as_of_utc"]), _utc(response["served_at_utc"])
    _require(observed <= available <= request_time <= response_served)
    _require(_utc(research["research_observation_timestamp_utc"]) == observed)
    _require(_utc(research["research_availability_timestamp_utc"]) == available and served == response_served)
    for time_value in (observed, request_time):
        _require(not ("2026-11-09" <= time_value.date().isoformat() <= "2027-11-08"), "Protected prospective observations are not accepted.")

    status = record["research_status"]
    _require(_keys(status, frozenset({"outcome", "completeness_status", "classification_type", "classification"})))
    _require(status == {
        "outcome": response["outcome"],
        "completeness_status": research["completeness_status"],
        "classification_type": research["classification_type"],
        "classification": research["unified_descriptive_classification"],
    })

    availability = response["availability"]
    _require(_keys(availability, frozenset({"source_state", "latest_observation_timestamp_utc", "available_at_utc", "source_finality"})))
    _require(availability["source_state"] in {"complete", "partial"})
    _require(_utc(availability["latest_observation_timestamp_utc"]) == observed and _utc(availability["available_at_utc"]) == available)
    _require(availability["source_finality"] in {"unknown", "final"})
    use = response["data_use"]
    _require(_keys(use, frozenset({"source_class", "audience", "rights_status", "rights_evidence_sha256", "public_display_authorized", "commercial_use_authorized", "acquisition_authorized", "public_response_eligible", "restrictions"})))
    _require(use["source_class"] == "synthetic_demo" and use["audience"] == "private_local_research")
    _require(use["rights_status"] == "unverified" and use["rights_evidence_sha256"] is None)
    _require(all(use[key] is False for key in ("public_display_authorized", "commercial_use_authorized", "acquisition_authorized", "public_response_eligible")))
    _require(isinstance(use["restrictions"], list) and bool(use["restrictions"]))

    provenance = record["source_provenance"]
    _require(_keys(provenance, frozenset({"daily", "intraday"})) and research["provenance"] == provenance)
    for name in ("daily", "intraday"):
        source = provenance[name]
        _require(isinstance(source, dict))
        _require(source.get("source_provider") == "synthetic_provider_shape_v1")
        _require(isinstance(source.get("source_feed_id"), str) and source["source_feed_id"].startswith("synthetic_"))
        _require(_is_sha(source.get("source_data_sha256")) and _is_sha(source.get("source_manifest_sha256")))

    _require(manifest["manifest_id"] == MANIFEST_ID and manifest["schema_version"] == 1)
    _require(manifest["m95_schema_sha256"] == M95_SCHEMA_SHA256 and manifest["m97_schema_sha256"] == M97_SCHEMA_SHA256)
    _require(manifest["synthetic_only"] is True and manifest["acquisition_authorized"] is False)
    _require(_is_sha(manifest["m913_input_sha256"]))
    _require(manifest["m95_record_sha256"] == research["record_sha256"] and _is_sha(research["record_sha256"]))
    _require(manifest["record_sha256"] == _digest(record) and manifest["m97_response_sha256"] == _digest(response))
    _require(manifest["source_data_sha256"] == {k: provenance[k]["source_data_sha256"] for k in ("daily", "intraday")})
    _require(manifest["source_manifest_sha256"] == {k: provenance[k]["source_manifest_sha256"] for k in ("daily", "intraday")})
    _require(_keys(manifest["source_row_counts"], frozenset({"daily", "intraday"})))
    _require(all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in manifest["source_row_counts"].values()))
    unsigned = dict(manifest)
    manifest_hash = unsigned.pop("manifest_sha256")
    _require(_is_sha(manifest_hash) and manifest_hash == _digest(unsigned))
    unsigned_record = dict(research)
    record_hash = unsigned_record.pop("record_sha256")
    _require(_is_sha(record_hash) and record_hash == _digest(unsigned_record))

    if record["scenario_id"] == "missing_intraday_segment":
        _require(research["unified_descriptive_classification"] == "daily_only")
        _require("missing_intraday_bars:1" in record["m913_quality_notes"])
        _require(all(research["intraday_context"].get(k) == "unavailable" for k in ("trend_1m", "trend_5m", "price_vs_vwap")))
        _require("intraday_context_incomplete_or_unavailable" in research["data_quality_flags"])
    return bundle


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise BridgeValidationError("Duplicate JSON keys are not accepted.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise BridgeValidationError("Non-finite JSON values are not accepted.")


def load_bundle_from_directory(directory_text: str | None) -> dict[str, Any]:
    """Load one fixed filename from an explicitly configured local directory."""
    if not directory_text:
        raise BridgeValidationError("The approved synthetic fixture is unavailable.")
    root = Path(directory_text)
    if not root.is_absolute() or root.is_symlink():
        raise BridgeValidationError("The approved synthetic fixture is unavailable.")
    try:
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise BridgeValidationError("The approved synthetic fixture is unavailable.")
        candidate = resolved / "kestrel_bridge_v1.json"
        if candidate.is_symlink():
            raise BridgeValidationError("The approved synthetic fixture is unavailable.")
        file_path = candidate.resolve(strict=True)
        if file_path.parent != resolved or not file_path.is_file() or file_path.stat().st_size > 1_048_576:
            raise BridgeValidationError("The approved synthetic fixture is unavailable.")
        value = json.loads(file_path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeValidationError("The approved synthetic fixture is unavailable.") from exc
    return validate_bundle(value)


def is_local_peer(host: str | None, client_host: str | None) -> bool:
    if host not in {"localhost", "127.0.0.1", "[::1]", "::1"} or not client_host:
        return False
    import ipaddress
    try:
        return ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        return False


def freshness_status(observation_timestamp_utc: str, now: datetime | None = None) -> tuple[bool, float]:
    observed = _utc(observation_timestamp_utc)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_hours = max(0.0, (current - observed).total_seconds() / 3600)
    return age_hours > 24, round(age_hours, 2)