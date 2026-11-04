---
applyTo: "**/*.py"
---

# Python Engineering

- Target Python 3.12+ with strict, modern type hints.
- Use Pydantic v2 models at boundaries and SQLModel typed entities for persistence.
- SQLAlchemy is an underlying SQLModel implementation dependency; do not introduce direct SQLAlchemy declarative imports into API, domain, or repository code.
- Prefer small pure functions, dependency injection, explicit exceptions, structured logs, and context managers.
- Make external I/O time-bounded, retryable by policy, and idempotent.
- Keep secrets and raw personal data out of logs, exception messages, and tool arguments.
- Add focused tests beside behavior; run the smallest relevant suite.
- In local RND, use SQLModel and SQLite. Production persistence must remain isolated behind repository/service boundaries so PostgreSQL migration does not alter API or domain contracts.
