---
name: python-engineering
description: Apply Python 3.12+, FastAPI, Pydantic v2, SQLModel, and Alembic repository conventions.
---

# Python Engineering

1. Use modern typing and structured Pydantic settings/models.
2. Keep boundary validation at API/MCP/provider inputs.
3. Use SQLModel patterns and Alembic migrations with compatibility and rollback notes. Keep SQLAlchemy declarative APIs below repository boundaries.
4. Make Celery tasks idempotent, bounded, and typed around immutable IDs/config hashes.
5. Use dependency injection, context managers, explicit exceptions, and structured logs.
6. Redact secrets and personal fields; apply timeouts/backpressure to external work.
7. Add targeted unit/integration/contract tests and run the smallest relevant suite.
