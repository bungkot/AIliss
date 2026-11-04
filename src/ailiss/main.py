from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ailiss.config import get_settings
from ailiss.db import create_db_and_tables, get_session
from ailiss.models import Lead
from ailiss.schemas import (
    ApprovalCreate,
    CampaignCreate,
    CampaignResponse,
    ExtractionRunCreate,
    ExtractionRunResponse,
    LeadResponse,
    SourceCreate,
    SourcePolicyCreate,
    SourcePolicyResponse,
    SourceResponse,
)
from ailiss.services import (
    create_campaign,
    create_extraction_run,
    create_source_policy,
    pause_campaign,
    register_source,
    split_values,
    approve_lead,
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
        content={"code": code, "message": "The request could not be processed.", "correlation_id": correlation},
    )


@app.get("/health")
def health():
    return {"status": "healthy", "environment": settings.environment}


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


@app.post("/v1/campaigns/{campaign_id}/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def post_source(
    campaign_id: str,
    payload: SourceCreate,
    correlation: str = Depends(correlation_id),
    session: Session = Depends(get_session),
):
    return register_source(session, UUID(campaign_id), payload.url, payload.access_basis, correlation)


@app.post("/v1/extraction-runs", response_model=ExtractionRunResponse, status_code=status.HTTP_202_ACCEPTED)
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
