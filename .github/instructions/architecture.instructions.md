---
applyTo: "**/{src,app,api,workers,agents,mcp,extractors}/**,docs/adr/**,docs/02-system-architecture.md"
---

# Architecture

- Preserve modular boundaries and the modular-monolith-first baseline.
- API validates and commands; workers execute; agents propose; deterministic services mutate domain truth.
- Use FastAPI, SQLModel/Alembic, Celery/Redis, MCP, LangGraph, Playwright, and provider adapters according to ADRs.
- Use FastAPI, SQLModel, and SQLite only in the documented local RND profile; production PostgreSQL and queue contracts remain unchanged unless a superseding ADR is accepted.
- Record technology or service-boundary changes in a new or superseding ADR.
- Propagate correlation IDs and typed outcomes through every external boundary.
