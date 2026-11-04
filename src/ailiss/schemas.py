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
