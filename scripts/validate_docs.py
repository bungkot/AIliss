#!/usr/bin/env python3
"""Repository documentation validation. Standard library only."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAIN_DOCS = [
    "00-project-constitution.md", "01-product-requirements-document.md",
    "02-system-architecture.md", "03-domain-model.md", "04-agentic-workflow.md",
    "05-context-engineering.md", "06-agent-harness-engineering.md",
    "07-mcp-architecture.md", "08-playwright-extraction.md", "09-data-pipeline.md",
    "10-security-and-compliance.md", "11-observability.md", "12-testing-and-evaluation.md",
    "13-deployment-and-infrastructure.md", "14-api-specification.md",
    "15-development-workflow.md", "16-roadmap.md", "17-operational-runbook.md",
    "18-cost-optimization.md",
]

REQUIRED_HEADINGS = {
    "README.md": ["Project purpose", "Documentation map", "Development harness", "Repository boundaries"],
    "00-project-constitution.md": ["North Star", "Principles", "Quality gates"],
    "01-product-requirements-document.md": ["Product summary", "Functional requirements", "Non-functional requirements"],
    "02-system-architecture.md": ["Architecture overview", "Component responsibilities", "Technology decisions"],
    "03-domain-model.md": ["Core entities", "Entity lifecycle", "Provenance and lineage", "Deduplication", "Retention"],
    "04-agentic-workflow.md": ["Workflow overview", "Bounded agent loop", "Autonomous operations", "Failure handling"],
    "05-context-engineering.md": ["Context hierarchy", "Progressive disclosure", "Context budgets"],
    "06-agent-harness-engineering.md": ["Harness responsibilities", "Quality gates", "Resource and cost engineering"],
    "07-mcp-architecture.md": ["MCP topology", "Tool specifications", "Security boundaries"],
    "08-playwright-extraction.md": ["Extraction architecture", "Browser lifecycle", "Anti-blocking and resilience"],
    "09-data-pipeline.md": ["Pipeline stages", "Deduplication and retention", "Async processing"],
    "10-security-and-compliance.md": ["Threat model", "Indonesia PDP assessment", "Data controls"],
    "11-observability.md": ["Signals and ownership", "OpenTelemetry", "Prometheus and Grafana"],
    "12-testing-and-evaluation.md": ["Test strategy", "Evaluation metrics", "Quality gates"],
    "13-deployment-and-infrastructure.md": ["Target topology", "Deployment process", "Infrastructure decisions"],
    "14-api-specification.md": ["API conventions", "Endpoint catalog", "Error model"],
    "15-development-workflow.md": ["Local development", "Contribution workflow", "Quality gates"],
    "16-roadmap.md": [
        "Delivery phases", "Phase 1", "Phase 1 exit criteria",
        "Phase 2", "Phase 2 exit criteria", "Phase 3",
        "Phase 3 exit criteria", "Phase 4", "Phase 4 exit criteria",
        "Phase 5", "Phase 5 exit criteria",
    ],
    "17-operational-runbook.md": ["Operational ownership", "Routine operations", "Incident playbooks"],
    "18-cost-optimization.md": ["Cost model", "Budget controls", "Optimization policies"],
}

REQUIRED_ADRS = [
    "ADR-001-agent-orchestration.md",
    "ADR-002-database-and-persistence.md",
    "ADR-003-browser-automation.md",
    "ADR-004-mcp-integration.md",
    "ADR-005-task-queue.md",
    "ADR-006-llm-provider-abstraction.md",
]

REQUIRED_HARNESS = [
    ".github/copilot-instructions.md",
    ".github/instructions/python.instructions.md",
    ".github/instructions/testing.instructions.md",
    ".github/instructions/architecture.instructions.md",
    ".github/instructions/documentation.instructions.md",
    ".github/instructions/agent.instructions.md",
    ".github/instructions/security.instructions.md",
    ".github/workflows/ci.yml",
]

REQUIRED_SPECIALIST_AGENTS = [
    ".github/agents/architect.agent.md",
    ".github/agents/backend-engineer.agent.md",
    ".github/agents/browser-engineer.agent.md",
    ".github/agents/ai-agent-engineer.agent.md",
    ".github/agents/test-engineer.agent.md",
    ".github/agents/security-reviewer.agent.md",
    ".github/agents/code-reviewer.agent.md",
]

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)

# Root project index.
root_readme = ROOT / "README.md"
if not root_readme.is_file():
    fail("README.md: required file is missing")
else:
    root_text = root_readme.read_text(encoding="utf-8")
    for heading in REQUIRED_HEADINGS["README.md"]:
        if not re.search(rf"^##+\s+{re.escape(heading)}\s*$", root_text, re.M | re.I):
            fail(f"README.md: missing heading '{heading}'")


docs_dir = ROOT / "docs"
if not docs_dir.is_dir():
    fail("docs/: directory is missing")
else:
    for name in MAIN_DOCS:
        path = docs_dir / name
        if not path.is_file():
            fail(f"docs/{name}: required file is missing")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_HEADINGS.get(name, []):
            if not re.search(rf"^##+\s+{re.escape(heading)}\s*$", text, re.M | re.I):
                fail(f"docs/{name}: missing heading '{heading}'")
        for needle in ("TODO", "TBD"):
            if re.search(rf"\b{needle}\b", text):
                fail(f"docs/{name}: contains {needle} placeholder")
        fence_count = len(re.findall(r"^```", text, re.M))
        if fence_count % 2:
            fail(f"docs/{name}: unbalanced fenced code blocks")

    mermaid_total = sum(
        len(re.findall(r"^```mermaid\s*$", (docs_dir / name).read_text(encoding="utf-8"), re.M | re.I))
        for name in MAIN_DOCS if (docs_dir / name).is_file()
    )
    if mermaid_total == 0:
        fail("docs/: no Mermaid fenced blocks found")

    # Duplicate headings across each document.
    for name in MAIN_DOCS:
        path = docs_dir / name
        if not path.is_file():
            continue
        headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.M)
        normalized = [re.sub(r"\s+", " ", h.strip().lower()) for h in headings]
        seen: set[str] = set()
        for heading in normalized:
            if heading in seen:
                fail(f"docs/{name}: duplicate heading '{heading}'")
            seen.add(heading)

# Required ADR set and README.
adr_dir = docs_dir / "adr"
if not adr_dir.is_dir():
    fail("docs/adr/: directory is missing")
else:
    if not (adr_dir / "README.md").is_file():
        fail("docs/adr/README.md: required file is missing")
    for name in REQUIRED_ADRS:
        if not (adr_dir / name).is_file():
            fail(f"docs/adr/{name}: required ADR is missing")

for relative in REQUIRED_HARNESS:
    if not (ROOT / relative).is_file():
        fail(f"{relative}: required harness file is missing")
for relative in REQUIRED_SPECIALIST_AGENTS:
    if not (ROOT / relative).is_file():
        fail(f"{relative}: required specialist agent is missing")

# Local Markdown links: ignore web links and anchors; resolve relative files.
link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
for md in ROOT.rglob("*.md"):
    if ".git" in md.parts:
        continue
    text = md.read_text(encoding="utf-8")
    for _label, target in link_pattern.findall(text):
        target = target.strip().split()[0].strip("<>")
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue
        clean_target = target.split("#", 1)[0]
        if not clean_target:
            continue
        resolved = (md.parent / clean_target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            fail(f"{md.relative_to(ROOT)}: link escapes repository: {target}")
        if not resolved.exists():
            fail(f"{md.relative_to(ROOT)}: broken local link: {target}")

# Basic cross-document consistency.
domain = (docs_dir / "03-domain-model.md")
api = docs_dir / "14-api-specification.md"
architecture = docs_dir / "02-system-architecture.md"
if domain.is_file():
    entities = ["Company", "Contact", "Lead", "Source", "Campaign", "ExtractionRun"]
    text = domain.read_text(encoding="utf-8")
    missing = [e for e in entities if not re.search(rf"\b{e}\b", text)]
    if missing:
        fail("docs/03-domain-model.md: missing core entity names: " + ", ".join(missing))
if api.is_file():
    api_text = api.read_text(encoding="utf-8")
    for path in ("POST /v1/leads/import", "GET /v1/leads/{lead_id}", "POST /v1/extraction-runs"):
        if path not in api_text:
            fail(f"docs/14-api-specification.md: missing API path '{path}'")
if architecture.is_file():
    text = architecture.read_text(encoding="utf-8")
    for decision in ("FastAPI", "PostgreSQL", "Redis", "Celery", "LangGraph", "MCP", "Playwright", "Ollama"):
        if not re.search(rf"\b{re.escape(decision)}\b", text, re.I):
            fail(f"docs/02-system-architecture.md: missing technology '{decision}'")

if errors:
    print("Documentation validation failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Documentation validation passed: required docs, headings, Mermaid fences, links, and consistency checks.")
