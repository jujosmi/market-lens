from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.main import allowed_hosts, allowed_origins


def test_explicit_localhost_origins_accept_approved_development_ports(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv(
        "TRADE_UI_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:5173",
    )
    assert allowed_origins() == ["http://localhost:3000", "http://127.0.0.1:5173"]


def test_default_local_origins_remain_available(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("TRADE_UI_ALLOWED_ORIGINS", raising=False)
    assert allowed_origins() == [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ]


def test_exact_render_https_frontend_origin_is_allowed_only_in_render_mode(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("TRADE_UI_ALLOWED_ORIGINS", "https://jujosmi-trade-v2.onrender.com")
    assert allowed_origins() == ["https://jujosmi-trade-v2.onrender.com"]


def test_render_mode_rejects_local_http_origins(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("TRADE_UI_ALLOWED_ORIGINS", "http://localhost:3000")
    with pytest.raises(RuntimeError, match="localhost development"):
        allowed_origins()


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://untrusted.example",
        "https://jujosmi-trade-v2.onrender.com/path",
        "https://user:pass@jujosmi-trade-v2.onrender.com",
        "https://jujosmi-trade-v2.onrender.com?x=1",
        "https://jujosmi-trade-v2.onrender.com#fragment",
        "https://jujosmi-trade-v2.onrender.com:bad",
        "https://jujosmi-trade-v2.onrender.com/",
        "https://jujosmi-trade-v2.onrender.com:443",
        "http://localhost:80",
    ],
)
def test_malformed_or_insecure_origins_are_rejected(origin, monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("TRADE_UI_ALLOWED_ORIGINS", origin)
    with pytest.raises(RuntimeError):
        allowed_origins()


def test_https_configuration_is_rejected_outside_render(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("TRADE_UI_ALLOWED_ORIGINS", "https://jujosmi-trade-v2.onrender.com")
    with pytest.raises(RuntimeError, match="hosted Render mode"):
        allowed_origins()


def test_explicit_localhost_https_default_port_is_only_rejected_by_scheme_policy(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("TRADE_UI_ALLOWED_ORIGINS", "http://localhost:443")
    # A non-default HTTP port is syntactically valid; HTTP is allowed only for loopback.
    assert allowed_origins() == ["http://localhost:443"]


def test_render_requires_explicit_frontend_origin_and_trusted_backend_host(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("TRADE_UI_ALLOWED_ORIGINS", raising=False)
    with pytest.raises(RuntimeError, match="explicitly list"):
        allowed_origins()
    monkeypatch.setenv("TRADE_UI_ALLOWED_ORIGINS", "https://jujosmi-trade-v2.onrender.com")
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    with pytest.raises(RuntimeError, match="RENDER_EXTERNAL_HOSTNAME"):
        allowed_hosts()
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "jujosmi-trade-api.onrender.com")
    assert allowed_hosts() == ["jujosmi-trade-api.onrender.com"]


def test_hosted_app_import_health_and_cors_preflight_in_isolated_process():
    frontend = "https://jujosmi-trade-v2.onrender.com"
    env = os.environ.copy()
    env.update(
        {
            "RENDER": "true",
            "RENDER_EXTERNAL_HOSTNAME": "jujosmi-trade-api.onrender.com",
            "TRADE_UI_ALLOWED_ORIGINS": frontend,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    script = f'''\
from fastapi.testclient import TestClient
from app.main import app

base = "https://jujosmi-trade-api.onrender.com"
approved = "{frontend}"
with TestClient(app, base_url=base) as client:
    health = client.get("/health")
    assert health.status_code == 200, health.text
    assert health.json() == {{"status": "ok", "mode": "synthetic-fixtures"}}

    preflight = client.options("/api/v1/overview", headers={{
        "Origin": approved,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "accept, content-type",
    }})
    assert preflight.status_code == 200, preflight.text
    assert preflight.headers.get("access-control-allow-origin") == approved
    assert "GET" in preflight.headers.get("access-control-allow-methods", "")

    unapproved = client.options("/api/v1/overview", headers={{
        "Origin": "https://untrusted.example",
        "Access-Control-Request-Method": "GET",
    }})
    assert unapproved.status_code == 400
    assert "access-control-allow-origin" not in unapproved.headers

    write_preflight = client.options("/api/v1/overview", headers={{
        "Origin": approved,
        "Access-Control-Request-Method": "POST",
    }})
    assert write_preflight.status_code == 400

    auth_header_preflight = client.options("/api/v1/overview", headers={{
        "Origin": approved,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }})
    assert auth_header_preflight.status_code == 400

paths = app.openapi()["paths"]
methods = {{method.lower() for operations in paths.values() for method in operations}}
assert methods == {{"get", "post"}}, methods
post_paths = {{path for path, operations in paths.items() if "post" in operations}}
assert post_paths == {{"/api/v1/discovery/filings/watchlist"}}, post_paths
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
