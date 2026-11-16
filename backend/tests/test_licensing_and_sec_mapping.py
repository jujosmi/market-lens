from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.providers.contracts import ProviderProvenance, ProviderResult
from app.providers.licensing import LicenseApproval, evaluate_public_use
from app.sec_edgar.mapping import SecIdentity, SecMappingError, map_company_facts
from app.sec_edgar.service import SecCompanyResearchService


NOW = datetime(2026, 11, 15, tzinfo=timezone.utc)


def result(permitted_use="public_display"):
    provenance = ProviderProvenance(provider_id="provider-x", product="daily", feed_kind="delayed",
                                    retrieved_at=NOW, permitted_use=permitted_use)
    return ProviderResult(data={"value": 1}, status="ok", provenance=provenance)


def approval(**overrides):
    defaults = dict(provider_id="provider-x", product="daily", agreement_id="signed-2026-01",
                    approved=True, valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    expires_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
                    allowed_actions=["public_display", "commercial_display"],
                    attribution_required=True, attribution_text="Data source: Provider X",
                    max_cache_age_seconds=3600)
    defaults.update(overrides)
    return LicenseApproval(**defaults)


def test_public_use_is_default_deny_even_when_metadata_claims_display_rights():
    assert not evaluate_public_use(result(), None, "public_display", now=NOW).allowed
    assert not evaluate_public_use(result(), approval(approved=False), "public_display", now=NOW).allowed


@pytest.mark.parametrize("label", ["unknown", "personal_only", "prototype_only"])
def test_non_public_provenance_labels_are_denied(label):
    decision = evaluate_public_use(result(label), approval(), "public_display", now=NOW)
    assert not decision.allowed


def test_agreement_must_be_scoped_current_and_cover_action():
    assert not evaluate_public_use(result(), approval(provider_id="another"), "public_display", now=NOW).allowed
    assert not evaluate_public_use(result(), approval(expires_at=NOW), "public_display", now=NOW).allowed
    assert not evaluate_public_use(result(), approval(allowed_actions=["public_display"]), "redistribute", now=NOW).allowed


def test_attribution_and_cache_limits_are_enforced():
    assert not evaluate_public_use(result(), approval(attribution_text=None), "public_display", now=NOW).allowed
    assert not evaluate_public_use(result(), approval(max_cache_age_seconds=30), "public_display",
                                   now=NOW, cache_age_seconds=31).allowed
    decision = evaluate_public_use(result(), approval(), "public_display", now=NOW,
                                   cache_age_seconds=120)
    assert decision.allowed and decision.attribution == "Data source: Provider X"


def test_stale_data_needs_an_explicit_age_check_and_commercial_scope():
    stale = result().model_copy(update={"stale": True})
    assert not evaluate_public_use(stale, approval(), "public_display", now=NOW).allowed
    assert evaluate_public_use(stale, approval(), "public_display", now=NOW,
                               cache_age_seconds=10).allowed
    assert not evaluate_public_use(result("public_display"), approval(), "commercial_display", now=NOW).allowed


def sec_fixture():
    cik = "9999999999"  # synthetic test-only identity; not an issuer assertion
    identity = SecIdentity(cik=cik, ticker="EXMP", name="Example Holdings, Inc.", identity_source="approved_fixture")
    submissions = {"cik": cik, "filings": {"recent": {
        "accessionNumber": ["9999999999-26-000002", "9999999999-26-000001"],
        "form": ["10-Q", "10-Q"], "filingDate": ["2026-11-01", "2026-10-20"],
        "reportDate": ["2026-09-30", "2026-09-30"],
        "primaryDocument": ["example-q3-amended.htm", "example-q3.htm"],
    }}}
    company_facts = {"cik": int(cik), "entityName": identity.name, "facts": {"us-gaap": {
        "Revenues": {"label": "Revenue", "units": {"USD": [
            {"val": 1250000, "accn": "9999999999-26-000001", "fy": 2026, "fp": "Q3", "form": "10-Q", "filed": "2026-10-20", "start": "2026-07-01", "end": "2026-09-30"},
            {"val": 1230000, "accn": "9999999999-26-000002", "fy": 2026, "fp": "Q3", "form": "10-Q", "filed": "2026-11-01", "start": "2026-07-01", "end": "2026-09-30"},
        ]}},
        "NetIncomeLoss": {"label": "Net income (loss)", "units": {"USD": [
            {"val": 200000, "accn": "9999999999-26-000002", "fy": 2026, "fp": "Q3", "form": "10-Q", "filed": "2026-11-01", "start": "2026-07-01", "end": "2026-09-30"},
        ]}},
    }}}
    return identity, submissions, company_facts


def test_sec_shaped_fixture_maps_identity_facts_units_periods_versions_and_links():
    identity, submissions, company_facts = sec_fixture()
    report = map_company_facts(identity=identity, requested_ticker="exmp",
                               company_facts=company_facts, submissions=submissions)
    revenues = [fact for fact in report.facts if fact.field == "revenue"]
    assert report.live_data is False
    assert report.identity.cik == "9999999999" and report.identity.ticker == "EXMP"
    assert len(revenues) == 2
    assert sum(fact.latest_reported_version for fact in revenues) == 1
    assert next(fact.value for fact in revenues if fact.latest_reported_version) == 1_230_000
    assert all(fact.currency == "USD" and fact.period_end.isoformat() == "2026-09-30" for fact in revenues)
    assert "example-q3-amended.htm" in next(fact.filing_url for fact in revenues if fact.latest_reported_version)
    assert "revenue" not in report.missing_fields and "diluted_eps" in report.missing_fields
    assert report.filings[0].accession_number == "9999999999-26-000002"


def test_sec_mapping_rejects_ticker_and_cik_mismatches_and_has_no_network_path():
    identity, submissions, company_facts = sec_fixture()
    with pytest.raises(SecMappingError):
        map_company_facts(identity=identity, requested_ticker="OTHER",
                          company_facts=company_facts, submissions=submissions)
    altered = {**company_facts, "cik": 1234567890}
    with pytest.raises(SecMappingError):
        map_company_facts(identity=identity, requested_ticker="EXMP",
                          company_facts=altered, submissions=submissions)


def test_sec_service_uses_injected_gateway_and_preserves_reported_provenance_without_network():
    fixture_identity, submissions, company_facts = sec_fixture()
    identity = fixture_identity.model_copy(update={"identity_source": "sec_company_tickers"})

    class FixtureGateway:
        def __init__(self):
            self.calls = []

        def resolve_ticker(self, ticker):
            self.calls.append(("identity", ticker))
            return identity

        def get_submissions(self, cik):
            self.calls.append(("submissions", cik))
            return submissions

        def get_company_facts(self, cik):
            self.calls.append(("facts", cik))
            return company_facts

    gateway = FixtureGateway()
    report = SecCompanyResearchService(gateway).get_company_report("exmp")
    assert gateway.calls == [("identity", "EXMP"), ("submissions", identity.cik), ("facts", identity.cik)]
    assert report.live_data is False
    assert report.source.endswith("not live-verified)")
    assert report.filings and report.facts
    assert all(fact.unit and fact.period_end and fact.accession_number and fact.filing_url for fact in report.facts)


def test_sec_service_rejects_unverified_fixture_identity_before_fetching_payloads():
    identity, _, _ = sec_fixture()

    class FixtureGateway:
        def resolve_ticker(self, ticker):
            return identity

        def get_submissions(self, cik):
            raise AssertionError("unverified identity must fail before data retrieval")

        def get_company_facts(self, cik):
            raise AssertionError("unverified identity must fail before data retrieval")

    with pytest.raises(SecMappingError, match="provider-verified"):
        SecCompanyResearchService(FixtureGateway()).get_company_report("EXMP")
