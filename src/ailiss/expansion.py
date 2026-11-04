import re
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from ailiss.models import (
    Campaign,
    ExpansionRelease,
    ExpansionStatus,
    ExpansionType,
    ResourceBudget,
    SourcePolicy,
)
from ailiss.services import audit, split_values

PUBLIC_FIELD_ALLOWLIST = frozenset(
    {
        "company_name",
        "website",
        "domain",
        "public_address",
        "industry",
        "employee_range",
    }
)
PERSONAL_FIELD_NAMES = frozenset(
    {"email", "phone", "role", "display_name", "contact_name"}
)


def _valid_domain(value: str) -> bool:
    if len(value) > 253:
        return False
    labels = value.lower().rstrip(".").split(".")
    return len(labels) >= 2 and all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    )


def create_expansion_release(
    session: Session,
    *,
    campaign_id: UUID,
    target_type: str,
    target_name: str,
    config_hash: str,
    policy_evidence_hash: str,
    fixture_evidence_hash: str,
    evaluation_evidence_hash: str,
    rollout_percent: int,
    reason: str,
    approved_by: str | None,
    correlation_id: str,
) -> ExpansionRelease:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise LookupError("campaign_not_found")

    policy = session.exec(
        select(SourcePolicy).where(SourcePolicy.campaign_id == campaign_id)
    ).first()
    target_name = target_name.strip().lower()
    typed_target = ExpansionType(target_type)

    if typed_target == ExpansionType.SOURCE:
        if policy is None or not _valid_domain(target_name):
            raise ValueError("policy_denied")
        allowed_domains = split_values(policy.allowed_domains)
        if not any(
            target_name == domain or target_name.endswith("." + domain)
            for domain in allowed_domains
        ):
            raise ValueError("policy_denied")
    elif typed_target == ExpansionType.FIELD:
        if target_name in PERSONAL_FIELD_NAMES:
            raise ValueError("policy_denied")
        if target_name not in PUBLIC_FIELD_ALLOWLIST:
            raise ValueError("policy_denied")
        if policy is None or target_name not in split_values(policy.allowed_fields):
            raise ValueError("policy_denied")

    if rollout_percent != 0:
        raise ValueError("expansion_must_start_at_zero")
    if approved_by is None:
        raise ValueError("approval_required")

    existing = session.exec(
        select(ExpansionRelease).where(
            ExpansionRelease.campaign_id == campaign_id,
            ExpansionRelease.target_type == typed_target,
            ExpansionRelease.target_name == target_name,
        )
    ).first()
    if existing is not None:
        raise ValueError("expansion_release_exists")

    release = ExpansionRelease(
        campaign_id=campaign_id,
        target_type=typed_target,
        target_name=target_name,
        config_hash=config_hash.lower(),
        policy_evidence_hash=policy_evidence_hash.lower(),
        fixture_evidence_hash=fixture_evidence_hash.lower(),
        evaluation_evidence_hash=evaluation_evidence_hash.lower(),
        rollout_percent=0,
        status=ExpansionStatus.APPROVED,
        approved_by=approved_by,
        reason=reason,
    )
    session.add(release)
    session.commit()
    session.refresh(release)
    audit(
        session,
        actor=approved_by,
        action="expansion.release_approved",
        entity_type="expansion_release",
        entity_id=release.id,
        correlation_id=correlation_id,
        reason=reason,
    )
    session.commit()
    return release


def transition_expansion_release(
    session: Session,
    release_id: UUID,
    *,
    action: str,
    actor: str,
    reason: str,
    rollout_percent: int | None,
    correlation_id: str,
) -> ExpansionRelease:
    release = session.get(ExpansionRelease, release_id)
    if release is None:
        raise LookupError("expansion_release_not_found")

    if action == "stage":
        if release.status not in {
            ExpansionStatus.APPROVED,
            ExpansionStatus.PAUSED,
        }:
            raise ValueError("invalid_expansion_transition")
        if rollout_percent is None or rollout_percent < 1:
            raise ValueError("rollout_percent_required")
        release.status = ExpansionStatus.STAGED
        release.rollout_percent = rollout_percent
    elif action == "pause":
        release.status = ExpansionStatus.PAUSED
    elif action == "disable":
        release.status = ExpansionStatus.DISABLED
        release.rollout_percent = 0
    elif action == "rollback":
        release.status = ExpansionStatus.ROLLED_BACK
        release.rollout_percent = 0
    elif action == "resume":
        if release.status != ExpansionStatus.PAUSED:
            raise ValueError("invalid_expansion_transition")
        release.status = ExpansionStatus.STAGED
    else:
        raise ValueError("invalid_expansion_action")

    release.updated_at = datetime.now(UTC)
    session.add(release)
    audit(
        session,
        actor=actor,
        action=f"expansion.{action}",
        entity_type="expansion_release",
        entity_id=release.id,
        correlation_id=correlation_id,
        reason=reason,
    )
    session.commit()
    session.refresh(release)
    return release


def upsert_resource_budget(
    session: Session,
    *,
    campaign_id: UUID,
    worker_pool: str,
    max_concurrency: int,
    max_requests_per_second: int,
    max_bytes: int,
    max_tokens: int,
    max_spend_usd: float,
    enabled: bool,
    actor: str,
    correlation_id: str,
) -> ResourceBudget:
    if session.get(Campaign, campaign_id) is None:
        raise LookupError("campaign_not_found")
    budget = session.exec(
        select(ResourceBudget).where(
            ResourceBudget.campaign_id == campaign_id,
            ResourceBudget.worker_pool == worker_pool,
        )
    ).first()
    if budget is None:
        budget = ResourceBudget(
            campaign_id=campaign_id,
            worker_pool=worker_pool,
        )
    budget.max_concurrency = max_concurrency
    budget.max_requests_per_second = max_requests_per_second
    budget.max_bytes = max_bytes
    budget.max_tokens = max_tokens
    budget.max_spend_usd = max_spend_usd
    budget.enabled = enabled
    budget.updated_at = datetime.now(UTC)
    session.add(budget)
    session.commit()
    session.refresh(budget)
    audit(
        session,
        actor=actor,
        action="resource_budget.upsert",
        entity_type="resource_budget",
        entity_id=budget.id,
        correlation_id=correlation_id,
    )
    session.commit()
    return budget
