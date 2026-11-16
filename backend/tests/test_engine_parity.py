from __future__ import annotations

import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from app import engine_adapter, engine_fixtures
from tests.test_api import client

BACKEND_ROOT = Path(__file__).parents[1]
SNAPSHOT_ROOT = BACKEND_ROOT / "engine_snapshot"
SOURCE_ROOT_VALUE = os.environ.get("JUJOSMI_TRADE_SOURCE_ROOT")
SOURCE_ROOT = Path(SOURCE_ROOT_VALUE) / "market_lens" if SOURCE_ROOT_VALUE else None


def source_module(module_name: str):
    path = (SOURCE_ROOT or SNAPSHOT_ROOT) / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"source_{module_name}", path)
    assert spec and spec.loader and path.is_file()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_engine_snapshot_is_byte_identical_to_approved_source():
    manifest = engine_adapter.ENGINE_COMMIT
    assert manifest == "91768e574576349466e95faba40ed6440eda921b"
    expected = json.loads((SNAPSHOT_ROOT / "snapshot-manifest.json").read_text(encoding="utf-8"))
    for name in ("analytics", "research", "news", "discovery"):
        snapshot = (SNAPSHOT_ROOT / f"{name}.py").read_bytes()
        entry = next(item for item in expected if item["file"] == f"{name}.py")
        digest = hashlib.sha256(snapshot).hexdigest().upper()
        assert digest == entry["snapshot_sha256"]
        assert digest == entry["source_sha256"]
        if SOURCE_ROOT is not None:
            assert snapshot == (SOURCE_ROOT / f"{name}.py").read_bytes()


def test_technical_analysis_matches_original_python_calculation():
    original = source_module("analytics")
    history = engine_fixtures.price_history("NVDA")
    benchmark = engine_fixtures.benchmark_history()
    recommendations = engine_fixtures.recommendations("NVDA")
    expected = original.analyze(history, info=engine_fixtures.profile("NVDA"), benchmark=benchmark, recommendations=recommendations)
    actual = engine_adapter.technical_analysis("NVDA")
    for key in ("last", "change", "move", "hist_vol", "sma20", "sma50", "sma200", "rsi", "macd", "macd_signal", "drawdown", "current_drawdown", "high52", "low52", "relative_volume", "beta"):
        expected_value = expected[key]
        result_value = actual["indicators"][key]
        if isinstance(expected_value, float) and not math.isfinite(expected_value):
            assert result_value is None
        else:
            assert result_value == pytest.approx(expected_value, rel=1e-12, abs=1e-12)
    assert actual["rating"] == expected["rating"]
    assert actual["rating_source"] == expected["rating_source"]
    assert actual["technical_rating"] == expected["technical_rating"]
    assert actual["rating_checks"] == expected["rating_check_details"]
    assert actual["constructive_checks"] == expected["constructive_checks"]
    assert actual["caution_checks"] == expected["caution_checks"]
    for period in expected["returns"]:
        for field in ("asset", "benchmark", "excess"):
            raw = expected["returns"][period][field]
            got = actual["returns"][period][field]
            if not np.isfinite(raw):
                assert got is None
            else:
                assert got == pytest.approx(raw, rel=1e-12, abs=1e-12)


def test_research_normalizers_match_original_presentation_functions():
    original = source_module("research")
    symbol = "AMZN"
    profile = engine_fixtures.profile(symbol)
    metric_table = original.fundamentals_metric_table(profile)
    statement_table = original.quarterly_statement_table(engine_fixtures.quarterly_statement(symbol))
    targets = original.analyst_target_summary(engine_fixtures.analyst_targets(symbol), profile["sampleBase"])
    recs = original.recommendation_distribution(engine_fixtures.recommendations(symbol))
    revisions = original.eps_revision_table(engine_fixtures.eps_revisions(symbol))
    result, missing = engine_adapter.normalized_research(symbol)
    assert [(row["label"], row["display_value"]) for row in result["fundamentals"]] == list(metric_table.itertuples(index=False, name=None))
    assert [row["period"] for row in result["quarterly_financials"]] == list(statement_table.index)
    assert result["analyst_targets"] == targets
    assert result["recommendation_distribution"] == [
        {"rating": row["Rating"], "count": int(row["Analyst count"])} for _, row in recs.iterrows()
    ]
    assert result["eps_revisions"][0]["period"] == revisions.index[0]
    assert result["eps_revisions"][0]["up_last_7days"] == revisions.iloc[0]["Up last 7 days"]
    assert "Dividend yield" in missing


def test_news_sentiment_and_relevance_match_original_classifier():
    original = source_module("news")
    company = next(item for item in engine_fixtures.company_rows() if item["symbol"] == "NVDA")
    rows = engine_adapter.classified_news("NVDA")["headlines"]
    for raw, actual in zip(engine_fixtures.news_items("NVDA"), rows):
        expected = original.classify_headline(raw["title"], symbol="NVDA", company_name=company["name"])
        assert actual["sentiment"] == expected["label"]
        assert actual["reason"] == expected["reason"]
        assert actual["issuer_relevant"] is expected["issuer_relevant"]
        assert actual["bull_score"] == expected["bull_score"]
        assert actual["bear_score"] == expected["bear_score"]
        assert actual["topic"] == original.classify_news_topic(raw["title"])


def test_engine_api_reports_source_provenance_and_missing_fields():
    analysis = client.get("/api/v1/tickers/NVDA/analysis").json()
    assert analysis["source"] == "python-engine-snapshot"
    assert analysis["provenance"].startswith("market_lens.analytics.analyze@")
    assert analysis["as_of"] == "2025-12-31T00:00:00+00:00"
    assert analysis["data"]["observations"] == 320
    assert analysis["data"]["rating_checks"]
    research = client.get("/api/v1/companies/NVDA/research").json()
    assert research["status"] == "partial"
    assert research["missing_fields"] == ["Dividend yield"]
    assert research["data"]["fundamentals"][-1]["display_value"] == "—"
    assert research["data"]["quarterly_financials"]
    assert research["data"]["analyst_consensus"]["count"] >= 3


def test_engine_news_api_classifies_bull_bear_and_neutral_fixture_text():
    response = client.get("/api/v1/companies/NVDA/news-events")
    body = response.json()
    assert body["source"] == "python-engine-snapshot"
    assert {item["sentiment"] for item in body["data"]["headlines"]} == {"Bullish", "Bearish", "Neutral"}
    assert all(item["issuer_relevant"] for item in body["data"]["headlines"])


def test_discovery_engine_rejects_unmatched_industry_and_returns_validated_fixture():
    valid = client.get("/api/v1/discovery", params={"sector": "Technology", "industry": "Semiconductors"})
    assert valid.json()["source"] == "python-engine-snapshot"
    assert [company["symbol"] for company in valid.json()["data"]["companies"]] == ["NVDA"]
    invalid = client.get("/api/v1/discovery", params={"sector": "Healthcare", "industry": "Semiconductors"})
    assert invalid.status_code == 422
    assert invalid.json()["status"] == "invalid"
    assert invalid.json()["data"] is None


def test_unknown_engine_symbol_is_unavailable_not_fabricated():
    response = client.get("/api/v1/tickers/ZZZZ/analysis")
    assert response.status_code == 404
    assert response.json()["status"] == "unavailable"

