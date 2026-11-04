import ipaddress
from urllib.parse import urlparse
from uuid import UUID

from sqlmodel import Session, select

from ailiss.models import (
    AuditEvent,
    Campaign,
    CampaignStatus,
    ExtractionRun,
    Lead,
    LeadStatus,
    RunStatus,
    Source,
    SourcePolicy,
    SourceStatus,
)


def policy_error() -> ValueError:
    return ValueError("policy_denied")


def split_values(value: str) -> list[str]:
    return [item for item in (part.strip() for part in value.split(",")) if item]


def join_values(value: list[str]) -> str:
    return ",".join(sorted(set(item.strip().lower() for item in value if item.strip())))


def audit(
    session: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    correlation_id: str,
    reason: str | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor=actor[:200],
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            correlation_id=correlation_id,
            reason=reason,
        )
    )


def create_campaign(session: Session, name: str, prompt: str, correlation_id: str) -> Campaign:
    campaign = Campaign(name=name, discovery_prompt=prompt)
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    audit(
        session,
        actor="api",
        action="campaign.create",
        entity_type="campaign",
        entity_id=campaign.id,
        correlation_id=correlation_id,
    )
    session.commit()
    return campaign


def pause_campaign(session: Session, campaign_id: UUID, correlation_id: str) -> Campaign:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise LookupError("campaign_not_found")
    campaign.status = CampaignStatus.PAUSED
    session.add(campaign)
    audit(
        session,
        actor="operator",
        action="campaign.pause",
        entity_type="campaign",
        entity_id=campaign.id,
        correlation_id=correlation_id,
        reason="operator pause",
    )
    session.commit()
    session.refresh(campaign)
    return campaign


def create_source_policy(
    session: Session,
    campaign_id: UUID,
    allowed_domains: list[str],
    allowed_fields: list[str],
    require_personal_data_review: bool,
    correlation_id: str,
) -> SourcePolicy:
    if session.get(Campaign, campaign_id) is None:
        raise LookupError("campaign_not_found")
    existing = session.exec(
        select(SourcePolicy).where(SourcePolicy.campaign_id == campaign_id)
    ).first()
    if existing is not None:
        raise ValueError("source_policy_exists")
    policy = SourcePolicy(
        campaign_id=campaign_id,
        allowed_domains=join_values(allowed_domains),
        allowed_fields=join_values(allowed_fields),
        require_personal_data_review=require_personal_data_review,
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)
    audit(
        session,
        actor="policy_owner",
        action="source_policy.create",
        entity_type="source_policy",
        entity_id=policy.id,
        correlation_id=correlation_id,
    )
    session.commit()
    return policy


def source_allowed(policy: SourcePolicy, url: str) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            return False
    except ValueError:
        pass
    for domain in split_values(policy.allowed_domains):
        domain = domain.lower().lstrip(".")
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False


def register_source(
    session: Session, campaign_id: UUID, url: str, access_basis: str | None, correlation_id: str
) -> Source:
    policy = session.exec(
        select(SourcePolicy).where(SourcePolicy.campaign_id == campaign_id)
    ).first()
    if policy is None:
        raise policy_error()
    if not source_allowed(policy, url):
        raise policy_error()
    source = Source(
        campaign_id=campaign_id,
        url=url.strip(),
        access_basis=access_basis,
        status=SourceStatus.APPROVED,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    audit(
        session,
        actor="api",
        action="source.register",
        entity_type="source",
        entity_id=source.id,
        correlation_id=correlation_id,
    )
    session.commit()
    return source


def create_extraction_run(
    session: Session,
    campaign_id: UUID,
    source_id: UUID,
    config_hash: str,
    idempotency_key: str,
    correlation_id: str,
) -> ExtractionRun:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise LookupError("campaign_not_found")
    if campaign.status != CampaignStatus.ACTIVE:
        raise ValueError("campaign_paused")
    source = session.get(Source, source_id)
    if (
        source is None
        or source.campaign_id != campaign_id
        or source.status != SourceStatus.APPROVED
    ):
        raise policy_error()
    existing = session.exec(
        select(ExtractionRun).where(ExtractionRun.idempotency_key == idempotency_key)
    ).first()
    if existing is not None:
        if (
            existing.campaign_id != campaign_id
            or existing.source_id != source_id
            or existing.config_hash != config_hash
        ):
            raise ValueError("idempotency_conflict")
        return existing
    run = ExtractionRun(
        campaign_id=campaign_id,
        source_id=source_id,
        config_hash=config_hash,
        idempotency_key=idempotency_key,
        status=RunStatus.QUEUED,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    audit(
        session,
        actor="api",
        action="extraction_run.create",
        entity_type="extraction_run",
        entity_id=run.id,
        correlation_id=correlation_id,
    )
    session.commit()
    return run


def approve_lead(
    session: Session, lead_id: UUID, decision: str, reason: str, actor: str, correlation_id: str
) -> Lead:
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise LookupError("lead_not_found")
    if decision == "approve":
        lead.status = LeadStatus.RETAINED
    else:
        lead.status = LeadStatus.REJECTED
    session.add(lead)
    from ailiss.models import Approval

    session.add(Approval(lead_id=lead.id, actor=actor, decision=decision, reason=reason))
    audit(
        session,
        actor=actor,
        action=f"lead.{decision}",
        entity_type="lead",
        entity_id=lead.id,
        correlation_id=correlation_id,
        reason=reason,
    )
    session.commit()
    session.refresh(lead)
    return lead


def record_merge_decision(
    session: Session,
    kept_company_id: UUID,
    merged_company_ids: list[UUID],
    match_evidence: str,
    threshold: float,
    actor: str,
    reversal_data: str,
    correlation_id: str,
) -> None:
    if threshold < 0.85:
        raise ValueError("merge_threshold_too_low")
    if kept_company_id in merged_company_ids:
        raise ValueError("merge_kept_id_conflict")
    from ailiss.models import EntityResolutionDecision

    decision = EntityResolutionDecision(
        kept_company_id=kept_company_id,
        merged_company_ids=",".join(str(item) for item in merged_company_ids),
        match_evidence=match_evidence,
        threshold=threshold,
        actor=actor,
        reversal_data=reversal_data,
    )
    session.add(decision)
    audit(
        session,
        actor=actor,
        action="entity_resolution.merge",
        entity_type="company",
        entity_id=kept_company_id,
        correlation_id=correlation_id,
        reason=match_evidence,
    )
    session.commit()
