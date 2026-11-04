from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import select

from ailiss.models import AuditEvent, Campaign, DurableOperation, Lead, LeadStatus
from ailiss.operations import purge_archived_leads


def create_campaign(client, name: str = "Phase 4 Campaign"):
    response = client.post(
        "/v1/campaigns",
        json={"name": name, "discovery_prompt": "Find approved public companies"},
        headers={"x-correlation-id": "phase4-test"},
    )
    assert response.status_code == 201
    return response.json()


def test_liveness_readiness_and_metrics(client):
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert "ailiss_requests_total" in metrics.text
    assert "x-correlation-id" in metrics.headers


def test_durable_operation_is_idempotent(client, tmp_database):
    campaign = create_campaign(client)
    payload = {
        "campaign_id": campaign["id"],
        "task_name": "ailiss.tasks.extract",
        "worker_pool": "browser",
        "idempotency_key": "phase4-operation-1",
        "payload": {"source_id": "fixture-source"},
        "max_attempts": 3,
    }
    first = client.post("/v1/operations", json=payload)
    assert first.status_code == 202
    repeated = client.post("/v1/operations", json=payload, headers={"x-correlation-id": "same"})
    assert repeated.status_code == 202
    assert repeated.json()["id"] == first.json()["id"]

    operation = tmp_database.exec(
        select(DurableOperation).where(DurableOperation.idempotency_key == "phase4-operation-1")
    ).one()
    assert operation.attempts == 0
    assert operation.status.value == "queued"


def test_durable_operation_conflicts_on_reused_idempotency_key(client):
    campaign = create_campaign(client)
    base = {
        "campaign_id": campaign["id"],
        "task_name": "ailiss.tasks.export",
        "worker_pool": "default",
        "idempotency_key": "phase4-operation-conflict",
        "payload": {"export": True},
    }
    assert client.post("/v1/operations", json=base).status_code == 202
    conflict = dict(base, payload={"export": False})
    response = client.post("/v1/operations", json=conflict)
    assert response.status_code == 409
    assert response.json()["detail"] == "idempotency_conflict"


def test_retention_export_archive_and_audit(client, tmp_database):
    campaign = create_campaign(client)

    policy = client.post(
        f"/v1/campaigns/{campaign['id']}/retention-policy",
        json={
            "public_business_days": 30,
            "personal_data_days": 7,
            "export_enabled": True,
            "deletion_enabled": True,
            "legal_hold": False,
        },
    )
    assert policy.status_code == 200
    assert policy.json()["personal_data_days"] == 7

    lead = Lead(campaign_id=UUID(campaign["id"]))
    tmp_database.add(lead)
    tmp_database.commit()
    tmp_database.refresh(lead)

    export = client.post(
        f"/v1/campaigns/{campaign['id']}/export",
        json={"actor": "privacy-officer", "reason": "subject access request"},
    )
    assert export.status_code == 200
    assert export.json()["personal_data"] == "excluded"
    assert str(lead.id) in export.json()["public_lead_ids"]

    archive = client.post(
        f"/v1/leads/{lead.id}/archive",
        json={"actor": "privacy-officer", "reason": "retention expiry"},
    )
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"

    audit_events = tmp_database.exec(
        select(AuditEvent).where(AuditEvent.entity_id.in_([str(lead.id), campaign["id"]]))
    ).all()
    assert any(event.action in {"campaign.export", "lead.archive"} for event in audit_events)


def test_export_and_archive_are_denied_without_policy(client, tmp_database):
    campaign = create_campaign(client)
    lead = Lead(campaign_id=UUID(campaign["id"]))
    tmp_database.add(lead)
    tmp_database.commit()
    tmp_database.refresh(lead)

    export = client.post(
        f"/v1/campaigns/{campaign['id']}/export",
        json={"actor": "privacy-officer", "reason": "request"},
    )
    assert export.status_code == 403
    archive = client.post(
        f"/v1/leads/{lead.id}/archive",
        json={"actor": "privacy-officer", "reason": "request"},
    )
    assert archive.status_code == 403


def test_purge_requires_confirmation_policy_and_retention_age(client, tmp_database):
    campaign_record = Campaign(name="Purge Campaign", discovery_prompt="Approved sources")
    tmp_database.add(campaign_record)
    tmp_database.commit()
    tmp_database.refresh(campaign_record)

    policy = client.post(
        f"/v1/campaigns/{campaign_record.id}/retention-policy",
        json={
            "public_business_days": 30,
            "deletion_enabled": True,
            "legal_hold": False,
        },
    )
    assert policy.status_code == 200

    old_lead = Lead(
        campaign_id=campaign_record.id,
        status=LeadStatus.ARCHIVED,
        created_at=datetime.now(UTC) - timedelta(days=31),
    )
    new_lead = Lead(
        campaign_id=campaign_record.id,
        status=LeadStatus.ARCHIVED,
        created_at=datetime.now(UTC),
    )
    tmp_database.add(old_lead)
    tmp_database.add(new_lead)
    tmp_database.commit()
    tmp_database.refresh(old_lead)

    count = purge_archived_leads(
        tmp_database,
        campaign_record.id,
        actor="retention-worker",
        reason="scheduled retention",
        confirmation="purge",
        correlation_id="purge-test",
    )
    assert count == 1
    assert tmp_database.get(Lead, old_lead.id) is None
    assert tmp_database.get(Lead, new_lead.id) is not None
