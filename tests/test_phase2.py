import pytest
from sqlmodel import select

from ailiss.browser import destination_allowed, playwright_fetch, playwright_fetch_fixture
from ailiss.entity_resolution import resolve_company_match
from ailiss.extraction import canonicalize_domain, normalize_email
from ailiss.models import (
    Artifact,
    Evidence,
    ExtractionRun,
    Source,
    SourceStatus,
)
from ailiss.pipeline import parse_artifact, stage_fixture_artifact
from ailiss.services import create_campaign


def test_fixture_parser_removes_script_and_style(tmp_database):
    raw = (
        b"<html><body><h1>PT Example</h1><script>alert(1)</script><style>x{}</style></body></html>"
    )
    outcome = parse_artifact(raw, "https://example.com")
    assert outcome.observations == ("PT Example",)
    assert len(outcome.artifact_hash) == 64
    assert outcome.byte_count == len(raw)


@pytest.mark.parametrize(
    ("url", "domain"),
    [
        ("https://www.Example.com/about", "example.com"),
        ("example.com", "example.com"),
        ("http://example.com", None),
        ("https://127.0.0.1/private", "127.0.0.1"),
    ],
)
def test_domain_normalization(url, domain):
    assert canonicalize_domain(url) == domain


def test_normalize_email():
    assert normalize_email(" Sales@Example.COM ") == "sales@example.com"
    assert normalize_email("invalid") is None


def test_entity_resolution_precedence():
    assert (
        resolve_company_match("Example", "https://example.com", "Other", "https://example.com")[1]
        == "canonical_domain"
    )
    assert (
        resolve_company_match("PT Example Indonesia", None, "Example", None)[1]
        == "exact_normalized_name"
    )
    assert (
        resolve_company_match("Example Digital", None, "Completely Different", None)[1]
        == "no_match"
    )


def test_stage_fixture_artifact_creates_provenance(tmp_database):
    campaign = create_campaign(tmp_database, "Fixture Campaign", "fixture-only", "test-correlation")
    source = Source(
        campaign_id=campaign.id, url="https://example.com", status=SourceStatus.APPROVED
    )
    tmp_database.add(source)
    tmp_database.commit()
    tmp_database.refresh(source)
    run = ExtractionRun(
        campaign_id=campaign.id,
        source_id=source.id,
        config_hash="sha256:test",
        idempotency_key="fixture-run",
    )
    tmp_database.add(run)
    tmp_database.commit()
    tmp_database.refresh(run)

    artifact, evidence = stage_fixture_artifact(
        tmp_database,
        run.id,
        source.url,
        b"<html><body><h1>Fixture Company</h1></body></html>",
    )
    assert artifact.status == "staged"
    assert evidence[0].artifact_hash == artifact.raw_hash
    assert tmp_database.exec(select(Artifact)).one().id == artifact.id
    assert tmp_database.exec(select(Evidence)).one().run_id == run.id


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost/private",
        "https://127.0.0.1/private",
        "https://169.254.169.254/latest",
        "https://not-approved.example/about",
    ],
)
def test_browser_policy_rejects_non_https_or_private(url):
    assert not destination_allowed(url, {"example.com"})


def test_browser_fixture_budget_and_challenge_outcomes():
    approved = playwright_fetch_fixture(
        "https://example.com/about",
        {"example.com"},
        lambda: "<html><body>Fixture</body></html>",
    )
    assert approved.status == "complete"
    assert len(approved.artifact_hash) == 64
    challenged = playwright_fetch_fixture(
        "https://example.com/check",
        {"example.com"},
        lambda: None,
    )
    assert challenged.status == "challenge"
    denied = playwright_fetch_fixture(
        "https://127.0.0.1/check",
        {"example.com"},
        lambda: "<html></html>",
    )
    assert denied.status == "policy_rejected"


def test_real_playwright_adapter_rejects_before_launch():
    outcome = playwright_fetch(
        "https://127.0.0.1/private",
        {"example.com"},
        timeout_ms=5_000,
    )
    assert outcome.status == "policy_rejected"
