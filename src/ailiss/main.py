import base64
import binascii
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ailiss.agents import (
    Budget,
    MockProvider,
    OllamaProvider,
    ToolGateway,
    ToolOutcome,
    run_bounded_agent,
)
from ailiss.config import get_settings
from ailiss.db import create_db_and_tables, database_is_ready, get_session
from ailiss.models import AgentRun, AgentTerminalStatus, Campaign, ExtractionRun, Lead
from ailiss.pipeline import stage_fixture_artifact
from ailiss.schemas import (
    AgentRunCreate,
    AgentRunResponse,
    ApprovalCreate,
    ArtifactCreate,
    ArtifactResponse,
    CampaignCreate,
    CampaignResponse,
    ExtractionRunCreate,
    ExtractionRunResponse,
    LeadResponse,
    MergeDecisionCreate,
    SourceCreate,
    SourcePolicyCreate,
    SourcePolicyResponse,
    SourceResponse,
)
from ailiss.services import (
    approve_lead,
    audit,
    create_campaign,
    create_extraction_run,
    create_source_policy,
    pause_campaign,
    record_merge_decision,
    register_source,
    split_values,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)


def correlation_id(request: Request, x_correlation_id: str | None = Header(default=None)) -> str:
    return x_correlation_id or str(uuid4())


@app.middleware("http")
async def add_correlation_header(request: Request, call_next):
    response = await call_next(request)
    correlation = request.headers.get("x-correlation-id")
    if correlation:
        response.headers["x-correlation-id"] = correlation
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    correlation = request.headers.get("x-correlation-id") or str(uuid4())
    mapping = {
        "policy_denied": status.HTTP_403_FORBIDDEN,
        "campaign_paused": status.HTTP_409_CONFLICT,
        "idempotency_conflict": status.HTTP_409_CONFLICT,
        "source_policy_exists": status.HTTP_409_CONFLICT,
    }
    code = str(exc)
    return JSONResponse(
        status_code=mapping.get(code, status.HTTP_400_BAD_REQUEST),
        headers={"x-correlation-id": correlation},
        content={
            "code": code,
            "message": "The request could not be processed.",
            "correlation_id": correlation,
        },
    )


@app.get("/health")
def health():
    if not database_is_ready():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "environment": settings.environment},
        )
    return {"status": "healthy", "environment": settings.environment}


@app.post("/v1/agent-runs", response_model=AgentRunResponse, status_code=status.HTTP_202_ACCEPTED)
def post_agent_run(
    payload: AgentRunCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    campaign = session.get(Campaign, payload.campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="campaign_not_found")

    def campaign_get(*, campaign_id: str, correlation_id: str) -> ToolOutcome:
        if campaign_id != str(payload.campaign_id):
            return ToolOutcome(code="denied", message="campaign_scope_mismatch")
        return ToolOutcome(
            code="ok",
            data={
                "campaign_id": str(campaign.id),
                "status": campaign.status.value,
            },
        )

    gateway = ToolGateway({"campaign.get": campaign_get})
    provider = (
        OllamaProvider(
            settings.ollama_base_url,
            timeout_seconds=min(settings.agent_max_wall_seconds, 10.0),
        )
        if payload.provider == "ollama"
        else MockProvider()
    )
    budget = Budget(
        max_steps=settings.agent_max_steps,
        max_tool_calls=settings.agent_max_tool_calls,
        max_tokens=settings.agent_max_tokens,
        max_wall_seconds=settings.agent_max_wall_seconds,
        max_bytes=settings.agent_max_bytes,
        max_spend_usd=settings.agent_max_spend_usd,
    )
    result = run_bounded_agent(
        campaign_id=str(payload.campaign_id),
        prompt=payload.prompt,
        correlation_id=correlation,
        gateway=gateway,
        provider=provider,
        budget=budget,
        model=payload.model,
    )
    terminal_status = AgentTerminalStatus(result["terminal_status"])
    agent_run = AgentRun(
        campaign_id=payload.campaign_id,
        prompt=payload.prompt,
        prompt_version="phase3-agent-1",
        provider=payload.provider,
        model=payload.model,
        config_hash=payload.config_hash,
        tool_allowlist="campaign.get,source.policy_check",
        redaction_flags="no-personal-fields",
        citations=",".join(result.get("citations", [])),
        terminal_status=terminal_status,
        recommendation=result.get("recommendation", ""),
        steps=result.get("steps", 0),
        tool_calls=result.get("tool_calls", 0),
        tokens=result.get("tokens", 0),
        bytes_used=result.get("bytes_used", 0),
        spend_usd=result.get("spend_usd", 0.0),
        wall_seconds=result.get("wall_seconds", 0.0),
    )
    session.add(agent_run)
    session.commit()
    session.refresh(agent_run)
    audit(
        session,
        actor="agent",
        action="agent.run",
        entity_type="agent_run",
        entity_id=agent_run.id,
        correlation_id=correlation,
        reason=f"terminal_status:{terminal_status.value}",
    )
    session.commit()
    return agent_run


@app.get("/v1/agent-runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(run_id: str, session: Session = Depends(get_session)):
    agent_run = session.get(AgentRun, UUID(run_id))
    if agent_run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="agent_run_not_found")
    return agent_run


@app.post("/v1/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def post_campaign(
    payload: CampaignCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    return create_campaign(session, payload.name, payload.discovery_prompt, correlation)


@app.post("/v1/campaigns/{campaign_id}/pause", response_model=CampaignResponse)
def post_pause_campaign(
    campaign_id: str,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    try:
        return pause_campaign(session, UUID(campaign_id), correlation)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/v1/campaigns/{campaign_id}/source-policy", response_model=SourcePolicyResponse)
def post_source_policy(
    campaign_id: str,
    payload: SourcePolicyCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    try:
        policy = create_source_policy(
            session,
            UUID(campaign_id),
            payload.allowed_domains,
            payload.allowed_fields,
            payload.require_personal_data_review,
            correlation,
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SourcePolicyResponse(
        id=policy.id,
        campaign_id=policy.campaign_id,
        allowed_domains=split_values(policy.allowed_domains),
        allowed_fields=split_values(policy.allowed_fields),
        require_personal_data_review=policy.require_personal_data_review,
    )


@app.post(
    "/v1/campaigns/{campaign_id}/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_source(
    campaign_id: str,
    payload: SourceCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    return register_source(
        session, UUID(campaign_id), payload.url, payload.access_basis, correlation
    )


@app.post(
    "/v1/extraction-runs",
    response_model=ExtractionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_extraction_run(
    payload: ExtractionRunCreate,
    idempotency_key: str = Header(min_length=1, max_length=128),
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    try:
        run = create_extraction_run(
            session,
            payload.campaign_id,
            payload.source_id,
            payload.config_hash,
            idempotency_key,
            correlation,
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return run


@app.get("/v1/extraction-runs/{run_id}", response_model=ExtractionRunResponse)
def get_extraction_run(run_id: str, session: Session = Depends(get_session)):
    from ailiss.models import ExtractionRun

    run = session.get(ExtractionRun, UUID(run_id))
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="extraction_run_not_found")
    return run


@app.get("/v1/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, session: Session = Depends(get_session)):
    lead = session.get(Lead, UUID(lead_id))
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="lead_not_found")
    return lead


@app.post("/v1/leads/{lead_id}/approve", response_model=LeadResponse)
def post_lead_approval(
    lead_id: str,
    payload: ApprovalCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    try:
        return approve_lead(
            session,
            UUID(lead_id),
            payload.decision,
            payload.reason,
            payload.actor,
            correlation,
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post(
    "/v1/extraction-runs/{run_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_fixture_artifact(
    run_id: str,
    payload: ArtifactCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    run = session.get(ExtractionRun, UUID(run_id))
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="extraction_run_not_found")
    try:
        raw = base64.b64decode(payload.encoded_content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_base64_content") from exc
    try:
        artifact, _evidence = stage_fixture_artifact(
            session,
            run.id,
            payload.source_url,
            raw,
            payload.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ArtifactResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        source_url=artifact.source_url,
        content_type=artifact.content_type,
        byte_count=artifact.byte_count,
        raw_hash=artifact.raw_hash,
        status=artifact.status,
    )


@app.post("/v1/entity-resolution/merge", status_code=status.HTTP_201_CREATED)
def post_merge_decision(
    payload: MergeDecisionCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    try:
        record_merge_decision(
            session,
            payload.kept_company_id,
            payload.merged_company_ids,
            payload.match_evidence,
            payload.threshold,
            payload.actor,
            payload.reversal_data,
            correlation,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {
        "status": "recorded",
        "kept_company_id": payload.kept_company_id,
        "merged_company_ids": payload.merged_company_ids,
    }
