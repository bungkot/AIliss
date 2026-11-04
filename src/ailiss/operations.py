import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from ailiss.models import (
    Campaign,
    DurableOperation,
    Lead,
    LeadStatus,
    RetentionPolicy,
)
from ailiss.services import audit


def register_durable_operation(
    session: Session,
    *,
    campaign_id: UUID,
    task_name: str,
    worker_pool: str,
    idempotency_key: str,
    payload: dict[str, Any],
    correlation_id: str,
    max_attempts: int = 3,
) -> DurableOperation:
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    existing = session.exec(
        select(DurableOperation).where(DurableOperation.idempotency_key == idempotency_key)
    ).first()
    if existing is not None:
        if existing.campaign_id != campaign_id or existing.payload_hash != payload_hash:
            raise ValueError("idempotency_conflict")
        return existing
    operation = DurableOperation(
        campaign_id=campaign_id,
        task_name=task_name,
        worker_pool=worker_pool,
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
        correlation_id=correlation_id,
        max_attempts=max_attempts,
    )
    session.add(operation)
    session.commit()
    session.refresh(operation)
    audit(
        session,
        actor="api",
        action="operation.enqueue",
        entity_type="durable_operation",
        entity_id=operation.id,
        correlation_id=correlation_id,
        reason=f"task:{task_name}",
    )
    session.commit()
    return operation


def upsert_retention_policy(
    session: Session,
    campaign_id: UUID,
    *,
    public_business_days: int,
    personal_data_days: int | None,
    export_enabled: bool,
    deletion_enabled: bool,
    legal_hold: bool,
    actor: str,
    correlation_id: str,
) -> RetentionPolicy:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise LookupError("campaign_not_found")
    policy = session.exec(
        select(RetentionPolicy).where(RetentionPolicy.campaign_id == campaign_id)
    ).first()
    if policy is None:
        policy = RetentionPolicy(
            campaign_id=campaign_id,
            public_business_days=public_business_days,
            personal_data_days=personal_data_days,
            export_enabled=export_enabled,
            deletion_enabled=deletion_enabled,
            legal_hold=legal_hold,
        )
    else:
        policy.public_business_days = public_business_days
        policy.personal_data_days = personal_data_days
        policy.export_enabled = export_enabled
        policy.deletion_enabled = deletion_enabled
        policy.legal_hold = legal_hold
        policy.updated_at = datetime.now(UTC)
    session.add(policy)
    session.commit()
    session.refresh(policy)
    audit(
        session,
        actor=actor,
        action="retention_policy.upsert",
        entity_type="retention_policy",
        entity_id=policy.id,
        correlation_id=correlation_id,
    )
    session.commit()
    return policy


def export_campaign(
    session: Session,
    campaign_id: UUID,
    *,
    actor: str,
    reason: str,
    correlation_id: str,
) -> dict[str, Any]:
    policy = session.exec(
        select(RetentionPolicy).where(RetentionPolicy.campaign_id == campaign_id)
    ).first()
    if policy is None or not policy.export_enabled:
        raise ValueError("export_disabled")
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise LookupError("campaign_not_found")
    leads = session.exec(select(Lead).where(Lead.campaign_id == campaign_id)).all()
    audit(
        session,
        actor=actor,
        action="campaign.export",
        entity_type="campaign",
        entity_id=campaign.id,
        correlation_id=correlation_id,
        reason=reason,
    )
    session.commit()
    return {
        "campaign": {
            "id": str(campaign.id),
            "name": campaign.name,
            "status": campaign.status.value,
        },
        "public_lead_ids": [str(lead.id) for lead in leads if lead.status != LeadStatus.ARCHIVED],
        "personal_data": "excluded",
    }


def archive_lead(
    session: Session,
    lead_id: UUID,
    *,
    actor: str,
    reason: str,
    correlation_id: str,
) -> Lead:
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise LookupError("lead_not_found")
    policy = session.exec(
        select(RetentionPolicy).where(RetentionPolicy.campaign_id == lead.campaign_id)
    ).first()
    if policy is None or not policy.deletion_enabled or policy.legal_hold:
        raise ValueError("deletion_disabled")
    lead.status = LeadStatus.ARCHIVED
    session.add(lead)
    audit(
        session,
        actor=actor,
        action="lead.archive",
        entity_type="lead",
        entity_id=lead.id,
        correlation_id=correlation_id,
        reason=reason,
    )
    session.commit()
    session.refresh(lead)
    return lead


def purge_archived_leads(
    session: Session,
    campaign_id: UUID,
    *,
    actor: str,
    reason: str,
    confirmation: str,
    correlation_id: str,
    as_of: datetime | None = None,
) -> int:
    if confirmation != "purge":
        raise ValueError("confirmation_required")
    policy = session.exec(
        select(RetentionPolicy).where(RetentionPolicy.campaign_id == campaign_id)
    ).first()
    if policy is None or not policy.deletion_enabled or policy.legal_hold:
        raise ValueError("deletion_disabled")
    now = as_of or datetime.now(UTC)
    cutoff = now - timedelta(days=policy.public_business_days)
    archived = session.exec(
        select(Lead).where(
            Lead.campaign_id == campaign_id,
            Lead.status == LeadStatus.ARCHIVED,
            Lead.created_at <= cutoff,
        )
    ).all()
    count = len(archived)
    for lead in archived:
        session.delete(lead)
    if count:
        audit(
            session,
            actor=actor,
            action="lead.purge",
            entity_type="campaign",
            entity_id=campaign_id,
            correlation_id=correlation_id,
            reason=f"{reason}; purged_count={count}",
        )
    session.commit()
    return count
