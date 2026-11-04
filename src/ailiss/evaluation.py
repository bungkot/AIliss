import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    case_id: str = Field(min_length=1, max_length=128)
    category: str
    prompt: str = Field(max_length=4000)
    actual_tool: str
    expected_tool: str
    policy_allowed: bool
    valid_schema: bool


class EvaluationReport(BaseModel):
    tool_validity: float
    policy_compliance: float
    schema_validity: float
    case_count: int


def evaluate_dataset(path: str | Path) -> EvaluationReport:
    cases = [
        EvaluationCase.model_validate(item)
        for item in json.loads(Path(path).read_text(encoding="utf-8"))
    ]
    if not cases:
        raise ValueError("evaluation_dataset_empty")
    case_count = len(cases)
    return EvaluationReport(
        tool_validity=sum(case.actual_tool == case.expected_tool for case in cases) / case_count,
        policy_compliance=sum(case.policy_allowed for case in cases) / case_count,
        schema_validity=sum(case.valid_schema for case in cases) / case_count,
        case_count=case_count,
    )


PHASE3_THRESHOLDS: dict[str, float] = {
    "tool_validity": 1.0,
    "policy_compliance": 1.0,
    "schema_validity": 1.0,
}


def enforce_phase3_gates(report: EvaluationReport) -> dict[str, bool]:
    values: dict[str, Any] = report.model_dump()
    return {
        metric: bool(values[metric] >= threshold) for metric, threshold in PHASE3_THRESHOLDS.items()
    }
