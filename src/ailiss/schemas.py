from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ailiss.models import CampaignStatus, LeadStatus, RunStatus, SourceStatus


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    discovery_prompt: str = Field(min_length=1, max_length=4000)


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    discovery_prompt: str
    status: CampaignStatus


class SourcePolicyCreate(BaseModel):
    allowed_domains: list[str] = Field(default_factory=list, max_length=500)
    allowed_fields: list[str] = Field(default_factory=list, max_length=500)
    require_personal_data_review: bool = True


class SourcePolicyResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    allowed_domains: list[str]
    allowed_fields: list[str]
    require_personal_data_review: bool


class SourceCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    access_basis: str | None = Field(default=None, max_length=500)


class SourceResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    url: str
    status: SourceStatus
    access_basis: str | None


class ExtractionRunCreate(BaseModel):
    campaign_id: UUID
    source_id: UUID
    config_hash: str = Field(min_length=1, max_length=128)


class ExtractionRunResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    source_id: UUID
    config_hash: str
    status: RunStatus


class LeadResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    status: LeadStatus


class ApprovalCreate(BaseModel):
    decision: str = Field(pattern=r"^(approve|reject)$")
    reason: str = Field(min_length=1, max_length=2000)
    actor: str = Field(min_length=1, max_length=200)


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlation_id: str


class ArtifactCreate(BaseModel):
    source_url: str = Field(min_length=1, max_length=2048)
    content_type: str = Field(default="text/html", max_length=100)
    encoded_content: str = Field(min_length=1, max_length=2_800_000)


class ArtifactResponse(BaseModel):
    id: UUID
    run_id: UUID
    source_url: str
    content_type: str
    byte_count: int
    raw_hash: str
    status: str


class MergeDecisionCreate(BaseModel):
    kept_company_id: UUID
    merged_company_ids: list[UUID] = Field(min_length=1, max_length=500)
    match_evidence: str = Field(min_length=1, max_length=4000)
    threshold: float = Field(ge=0.0, le=1.0)
    actor: str = Field(min_length=1, max_length=200)
    reversal_data: str = Field(min_length=1, max_length=4000)


class AgentRunCreate(BaseModel):
    campaign_id: UUID
    prompt: str = Field(min_length=1, max_length=4000)
    provider: str = Field(default="mock", pattern=r"^(mock|ollama)$")
    model: str = Field(default="qwen3:0.6b", max_length=128)
    config_hash: str = Field(min_length=1, max_length=128)


class AgentRunResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    provider: str
    model: str
    config_hash: str
    terminal_status: str
    recommendation: str
    steps: int
    tool_calls: int
    tokens: int
    bytes_used: int
    spend_usd: float
    wall_seconds: float


class RetentionPolicyCreate(BaseModel):
    public_business_days: int = Field(default=365, ge=1, le=3650)
    personal_data_days: int | None = Field(default=None, ge=1, le=3650)
    export_enabled: bool = False
    deletion_enabled: bool = False
    legal_hold: bool = False


class RetentionPolicyResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    public_business_days: int
    personal_data_days: int | None
    export_enabled: bool
    deletion_enabled: bool
    legal_hold: bool


class PrivacyActionCreate(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    confirmation: str | None = Field(default=None, pattern=r"^(purge|delete)?$")


class DurableOperationResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    task_name: str
    worker_pool: str
    status: str
    attempts: int
    max_attempts: int
    correlation_id: str


class DurableOperationCreate(BaseModel):
    campaign_id: UUID
    task_name: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z][a-z0-9_.]*(?:\.[a-z][a-z0-9_.]*)*$",
    )
    worker_pool: str = Field(pattern=r"^(browser|default|model)$")
    idempotency_key: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict, max_length=1000)
    max_attempts: int = Field(default=3, ge=1, le=10)


class ExpansionReleaseCreate(BaseModel):
    campaign_id: UUID
    target_type: str = Field(
        pattern=r"^(source|field|provider|browser|parser|storage|queue)$"
    )
    target_name: str = Field(min_length=1, max_length=128)
    config_hash: str = Field(min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$")
    policy_evidence_hash: str = Field(
        min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$"
    )
    fixture_evidence_hash: str = Field(
        min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$"
    )
    evaluation_evidence_hash: str = Field(
        min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$"
    )
    rollout_percent: int = Field(default=0, ge=0, le=100)
    reason: str = Field(min_length=1, max_length=2000)
    approved_by: str | None = Field(default=None, max_length=200)


class ExpansionReleaseResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    target_type: str
    target_name: str
    rollout_percent: int
    status: str
    reason: str
    approved_by: str | None


class ExpansionActionCreate(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    rollout_percent: int | None = Field(default=None, ge=0, le=100)


class ResourceBudgetCreate(BaseModel):
    campaign_id: UUID
    worker_pool: str = Field(pattern=r"^(default|browser|model)$")
    max_concurrency: int = Field(default=1, ge=1, le=100)
    max_requests_per_second: int = Field(default=1, ge=1, le=1000)
    max_bytes: int = Field(default=100_000, ge=1, le=100_000_000)
    max_tokens: int = Field(default=4000, ge=1, le=1_000_000)
    max_spend_usd: float = Field(default=0.25, ge=0.0, le=100000.0)
    enabled: bool = True


class ResourceBudgetResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    worker_pool: str
    max_concurrency: int
    max_requests_per_second: int
    max_bytes: int
    max_tokens: int
    max_spend_usd: float
    enabled: bool
