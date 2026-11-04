import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from ailiss.extraction import parse_fixture_html
from ailiss.models import Artifact, Evidence, EvidenceStatus


@dataclass(frozen=True)
class ParserOutcome:
    observations: tuple[str, ...]
    artifact_hash: str
    byte_count: int
    parser_version: str


def parse_artifact(raw: bytes, source_url: str) -> ParserOutcome:
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("artifact_too_large")
    html = raw.decode("utf-8", errors="strict")
    observations = tuple(parse_fixture_html(html))
    if not observations:
        raise ValueError("no_extractable_observations")
    return ParserOutcome(
        observations=observations,
        artifact_hash=hashlib.sha256(raw).hexdigest(),
        byte_count=len(raw),
        parser_version="phase2-html-1",
    )


def stage_fixture_artifact(
    session: Session,
    run_id: UUID,
    source_url: str,
    raw: bytes,
    content_type: str = "text/html",
) -> tuple[Artifact, list[Evidence]]:
    outcome = parse_artifact(raw, source_url)
    artifact = Artifact(
        run_id=run_id,
        source_url=source_url,
        content_type=content_type,
        byte_count=outcome.byte_count,
        raw_hash=outcome.artifact_hash,
        parser_version=outcome.parser_version,
        status="staged",
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)

    evidence = [
        Evidence(
            run_id=run_id,
            value=observation[:8000],
            confidence=0.8,
            verification_status=EvidenceStatus.CANDIDATE,
            source_url=source_url,
            artifact_hash=outcome.artifact_hash,
            extractor_version="fixture-html-parser-1",
            normalization_version=outcome.parser_version,
        )
        for observation in outcome.observations
    ]
    session.add_all(evidence)
    session.commit()
    for item in evidence:
        session.refresh(item)
    return artifact, evidence
