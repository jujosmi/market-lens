"""P4F tests for synthetic source validation, integrity, and local route gates."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.integrations.kestrel.bridge_v1 import BridgeValidationError, freshness_status, is_local_peer, load_bundle_from_directory, validate_bundle
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "p4f_kestrel_bridge_v1"


@pytest.mark.parametrize("filename", ["spy_bridge_complete.json", "spy_bridge_missing_intraday_segment.json"])
def test_validates_kestrel_generated_record(filename):
    bundle = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    assert validate_bundle(bundle) == bundle


def test_gap_scenario_stays_daily_only_and_intraday_is_unavailable():
    bundle = json.loads((FIXTURES / "spy_bridge_missing_intraday_segment.json").read_text(encoding="utf-8"))
    research = validate_bundle(bundle)["record"]["research_response"]["research_record"]
    assert research["unified_descriptive_classification"] == "daily_only"
    assert all(research["intraday_context"][k] == "unavailable" for k in ("trend_1m", "trend_5m", "price_vs_vwap"))


def test_tampering_and_unknown_schema_are_rejected():
    original = json.loads((FIXTURES / "spy_bridge_complete.json").read_text(encoding="utf-8"))
    tampered = deepcopy(original)
    tampered["record"]["research_status"]["classification"] = "daily_only"
    with pytest.raises(BridgeValidationError):
        validate_bundle(tampered)
    unknown = deepcopy(original)
    unknown["record"]["schema_version"] = 2
    with pytest.raises(BridgeValidationError):
        validate_bundle(unknown)


@pytest.mark.parametrize(("field", "value"), [("source_mode", "provider_data"), ("record_type", "predictive_model")])
def test_provider_and_predictive_records_are_rejected(field, value):
    bundle = json.loads((FIXTURES / "spy_bridge_complete.json").read_text(encoding="utf-8"))
    bundle["record"][field] = value
    with pytest.raises(BridgeValidationError):
        validate_bundle(bundle)


def test_real_provider_provenance_is_rejected():
    bundle = json.loads((FIXTURES / "spy_bridge_complete.json").read_text(encoding="utf-8"))
    bundle["record"]["source_provenance"]["daily"]["source_provider"] = "alpaca"
    with pytest.raises(BridgeValidationError):
        validate_bundle(bundle)


def test_loader_rejects_duplicate_keys_nonfinite_and_untrusted_location(tmp_path):
    path = tmp_path / "kestrel_bridge_v1.json"
    path.write_text('{"record":{},"record":{}}', encoding="utf-8")
    with pytest.raises(BridgeValidationError):
        load_bundle_from_directory(str(tmp_path))
    path.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(BridgeValidationError):
        load_bundle_from_directory(str(tmp_path))
    with pytest.raises(BridgeValidationError):
        load_bundle_from_directory("relative-bridge-path")


@pytest.mark.parametrize(("host", "peer", "expected"), [
    ("127.0.0.1", "127.0.0.1", True), ("localhost", "::1", True),
    ("example.com", "127.0.0.1", False), ("127.0.0.1", "10.0.0.8", False),
])
def test_both_peer_and_host_must_be_local(host, peer, expected):
    assert is_local_peer(host, peer) is expected


def test_preview_route_is_disabled_by_default_and_when_render_marked(monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1")
    monkeypatch.delenv("JUJOSMI_KESTREL_BRIDGE_ENABLED", raising=False)
    monkeypatch.delenv("JUJOSMI_TRADE_RUNTIME_MODE", raising=False)
    assert client.get("/api/v1/dev/kestrel/research").status_code == 404
    monkeypatch.setenv("JUJOSMI_KESTREL_BRIDGE_ENABLED", "true")
    monkeypatch.setenv("JUJOSMI_TRADE_RUNTIME_MODE", "local_development")
    monkeypatch.setenv("RENDER", "true")
    production = client.get("/api/v1/dev/kestrel/research")
    assert production.status_code == 404
    assert "C:" not in production.text and "spy_bridge" not in production.text


def test_query_path_input_is_rejected(monkeypatch):
    client = TestClient(app, base_url="http://127.0.0.1")
    monkeypatch.setenv("JUJOSMI_KESTREL_BRIDGE_ENABLED", "true")
    monkeypatch.setenv("JUJOSMI_TRADE_RUNTIME_MODE", "local_development")
    monkeypatch.delenv("RENDER", raising=False)
    response = client.get("/api/v1/dev/kestrel/research?path=C:/Windows/win.ini")
    assert response.status_code == 404


def test_historical_synthetic_observations_are_marked_stale():
    stale, hours = freshness_status("2025-06-02T16:30:00Z")
    assert stale and hours > 24