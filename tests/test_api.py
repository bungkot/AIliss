from sqlmodel import select
from uuid import UUID

from ailiss.models import AuditEvent, Lead


def create_campaign(client, name: str = "Indonesia B2B Test"):
    response = client.post(
        "/v1/campaigns",
        json={"name": name, "discovery_prompt": "Find approved public company websites"},
        headers={"x-correlation-id": "test-campaign"},
    )
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_campaign_policy_source_and_run(client):
    campaign = create_campaign(client)

    policy = client.post(
        f"/v1/campaigns/{campaign['id']}/source-policy",
        json={
            "allowed_domains": ["example.com"],
            "allowed_fields": ["company_name", "website"],
            "require_personal_data_review": True,
        },
    )
    assert policy.status_code == 200
    assert policy.json()["allowed_domains"] == ["example.com"]

    source = client.post(
        f"/v1/campaigns/{campaign['id']}/sources",
        json={"url": "https://www.example.com/about", "access_basis": "approved public source"},
    )
    assert source.status_code == 201

    run = client.post(
        "/v1/extraction-runs",
        json={
            "campaign_id": campaign["id"],
            "source_id": source.json()["id"],
            "config_hash": "sha256:test-config",
        },
        headers={"Idempotency-Key": "run-key-1"},
    )
    assert run.status_code == 202
    assert run.json()["status"] == "queued"

    repeated = client.post(
        "/v1/extraction-runs",
        json={
            "campaign_id": campaign["id"],
            "source_id": source.json()["id"],
            "config_hash": "sha256:test-config",
        },
        headers={"Idempotency-Key": "run-key-1"},
    )
    assert repeated.status_code == 202
    assert repeated.json()["id"] == run.json()["id"]


def test_unapproved_source_is_denied(client):
    campaign = create_campaign(client)
    client.post(
        f"/v1/campaigns/{campaign['id']}/source-policy",
        json={"allowed_domains": ["example.com"], "allowed_fields": ["company_name"]},
    )
    response = client.post(
        f"/v1/campaigns/{campaign['id']}/sources",
        json={"url": "http://localhost/private"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "policy_denied"


def test_pause_blocks_new_runs(client):
    campaign = create_campaign(client)
    pause = client.post(f"/v1/campaigns/{campaign['id']}/pause")
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    policy = client.post(
        f"/v1/campaigns/{campaign['id']}/source-policy",
        json={"allowed_domains": ["example.com"], "allowed_fields": ["company_name"]},
    )
    assert policy.status_code == 200
    source = client.post(
        f"/v1/campaigns/{campaign['id']}/sources",
        json={"url": "https://example.com"},
    )
    run = client.post(
        "/v1/extraction-runs",
        json={
            "campaign_id": campaign["id"],
            "source_id": source.json()["id"],
            "config_hash": "sha256:test-config",
        },
        headers={"Idempotency-Key": "paused-run"},
    )
    assert run.status_code == 409


def test_promotion_requires_approval_audit(client, tmp_database):
    campaign = create_campaign(client)
    lead = Lead(campaign_id=UUID(campaign["id"]))
    tmp_database.add(lead)
    tmp_database.commit()
    tmp_database.refresh(lead)

    response = client.post(
        f"/v1/leads/{lead.id}/approve",
        json={"decision": "approve", "reason": "verified evidence", "actor": "reviewer-1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "retained"

    audit_events = tmp_database.exec(
        select(AuditEvent).where(AuditEvent.entity_id == str(lead.id))
    ).all()
    assert audit_events
