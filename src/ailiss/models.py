import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


class CampaignStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class Campaign(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    name: str = Field(min_length=1, max_length=200)
    discovery_prompt: str = Field(min_length=1, max_length=4000)
    status: CampaignStatus = Field(default=CampaignStatus.ACTIVE)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class SourcePolicy(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", index=True)
    allowed_domains: str = Field(default="", max_length=4000)
    allowed_fields: str = Field(default="", max_length=4000)
    require_personal_data_review: bool = True
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class SourceStatus(StrEnum):
    DISCOVERED = "discovered"
    APPROVED = "approved"
    DENIED = "denied"


class Source(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", index=True)
    url: str = Field(min_length=1, max_length=2048)
    status: SourceStatus = Field(default=SourceStatus.DISCOVERED)
    access_basis: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    POLICY_REJECTED = "policy_rejected"


class ExtractionRun(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", index=True)
    source_id: uuid.UUID = Field(foreign_key="source.id", index=True)
    config_hash: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128, index=True)
    status: RunStatus = Field(default=RunStatus.QUEUED)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class EvidenceStatus(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    CONFLICT = "conflict"
    QUARANTINED = "quarantined"


class Evidence(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    run_id: uuid.UUID = Field(foreign_key="extractionrun.id", index=True)
    value: str = Field(max_length=8000)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_status: EvidenceStatus = Field(default=EvidenceStatus.CANDIDATE)
    source_url: str = Field(max_length=2048)
    artifact_hash: str = Field(min_length=1, max_length=128)
    extractor_version: str = Field(min_length=1, max_length=128)
    normalization_version: str = Field(min_length=1, max_length=128)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class LeadStatus(StrEnum):
    CANDIDATE = "candidate"
    REVIEWED = "reviewed"
    RETAINED = "retained"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Company(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    name: str = Field(min_length=1, max_length=500)
    domain: str | None = Field(default=None, max_length=253, index=True)
    status: str = Field(default="candidate", max_length=32)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class Contact(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    company_id: uuid.UUID | None = Field(default=None, foreign_key="company.id", index=True)
    display_name: str = Field(min_length=1, max_length=500)
    role: str | None = Field(default=None, max_length=200)
    purpose: str | None = Field(default=None, max_length=500)
    retention_class: str = Field(default="standard", max_length=32)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class Lead(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", index=True)
    status: LeadStatus = Field(default=LeadStatus.CANDIDATE)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class Artifact(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    run_id: uuid.UUID = Field(foreign_key="extractionrun.id", index=True)
    source_url: str = Field(max_length=2048)
    content_type: str = Field(max_length=100)
    byte_count: int = Field(default=0, ge=0)
    raw_hash: str = Field(min_length=1, max_length=128)
    browser_version: str | None = Field(default=None, max_length=128)
    parser_version: str = Field(default="phase2-html-1", max_length=128)
    status: str = Field(default="staged", max_length=32)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class EntityResolutionDecision(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    kept_company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    merged_company_ids: str = Field(min_length=1, max_length=4000)
    match_evidence: str = Field(min_length=1, max_length=4000)
    threshold: float = Field(ge=0.0, le=1.0)
    actor: str = Field(min_length=1, max_length=200)
    reversal_data: str = Field(min_length=1, max_length=4000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class Approval(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    lead_id: uuid.UUID = Field(foreign_key="lead.id", index=True)
    actor: str = Field(min_length=1, max_length=200)
    decision: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class AuditEvent(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    actor: str = Field(max_length=200)
    action: str = Field(min_length=1, max_length=100)
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: str = Field(min_length=1, max_length=128)
    correlation_id: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class AgentTerminalStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    RETRYABLE = "retryable"
    POLICY_REJECTED = "policy_rejected"
    BUDGET_EXHAUSTED = "budget_exhausted"


class AgentRun(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", index=True)
    prompt: str = Field(min_length=1, max_length=4000)
    prompt_version: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    config_hash: str = Field(min_length=1, max_length=128)
    tool_allowlist: str = Field(min_length=1, max_length=4000)
    redaction_flags: str = Field(min_length=1, max_length=1000)
    citations: str = Field(default="", max_length=8000)
    terminal_status: AgentTerminalStatus = Field(default=AgentTerminalStatus.BLOCKED)
    recommendation: str = Field(default="", max_length=4000)
    steps: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    tokens: int = Field(default=0, ge=0)
    bytes_used: int = Field(default=0, ge=0)
    spend_usd: float = Field(default=0.0, ge=0.0)
    wall_seconds: float = Field(default=0.0, ge=0.0)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class DurableOperationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRYABLE = "retryable"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"


class DurableOperation(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", index=True)
    task_name: str = Field(min_length=1, max_length=128, index=True)
    worker_pool: str = Field(min_length=1, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128, unique=True, index=True)
    status: DurableOperationStatus = Field(default=DurableOperationStatus.QUEUED)
    payload_hash: str = Field(min_length=64, max_length=64)
    correlation_id: str = Field(min_length=1, max_length=128, index=True)
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    last_error: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class RetentionPolicy(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid_pk, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaign.id", unique=True, index=True)
    public_business_days: int = Field(default=365, ge=1, le=3650)
    personal_data_days: int | None = Field(default=None, ge=1, le=3650)
    export_enabled: bool = Field(default=False)
    deletion_enabled: bool = Field(default=False)
    legal_hold: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
