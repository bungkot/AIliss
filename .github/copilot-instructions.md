# Repository Instructions

## Scope

This repository designs the AI Lead Intelligence and Scraping System. Documentation and harness work must not create application source, package manifests, migrations, or dependencies unless a future explicit implementation task requests them.

## Sources of truth

- `docs/00-project-constitution.md`: invariants.
- `docs/01-product-requirements-document.md`: behavior.
- `docs/02-system-architecture.md` and `docs/adr/`: boundaries and decisions.
- `docs/03-domain-model.md`: entities and lifecycle.
- `docs/04-agentic-workflow.md` through `docs/09-data-pipeline.md`: implementation contracts.
- `.github/instructions/`, `.github/agents/`, `.github/prompts/`, and `.github/skills/`: development behavior.

## Working rules

1. Prefer repository-specific evidence over invented conventions.
2. Make the smallest change satisfying the requested feature.
3. Keep deterministic code and policy checks outside unbounded agents.
4. Preserve provenance, authorization, idempotency, retention, and audit behavior.
5. Update tests and directly related documentation with implementation changes.
6. Use Windows-compatible paths when tooling or examples are host-specific.
7. Do not weaken security, quality, evaluation, or cost gates without review.

## Local RND profile

- The minimum implementation environment is FastAPI, SQLModel, SQLite, Ollama, and Playwright.
- RND SQLite is file-backed and deployed locally with SQLModel; PostgreSQL remains the production persistence target.
- Ollama runs on the Windows host for RND, with `qwen3:0.6b` as the minimum reasoning model.
- Playwright must remain isolated; do not share browser state or bypass source policy.
- Redis, Celery, MinIO, Prometheus, and Grafana are optional and excluded from the minimum stack.
- In-process or single-process tasks are acceptable for RND only; production queue behavior requires Redis/Celery contracts unless an ADR changes that decision.

## Handoff

Architect sets contracts; backend implements API/persistence; browser engineer owns Playwright isolation; AI engineer owns graphs/MCP/providers; test engineer adds coverage; security reviewer assesses policy/privacy; code reviewer finds implementation defects.
