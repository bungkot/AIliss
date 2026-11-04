---
applyTo: "**/*test*.py,tests/**,evals/**"
---

# Testing

- Prefer deterministic fixtures and local Playwright fixtures over live websites or credentials.
- Test policies, authorization, provenance, merge/correction, retries, malformed data, timeouts, and budget exhaustion.
- Keep provider/model tests offline and reproducible; use adapter-contract mocks for CI.
- Report extraction, deduplication, qualification, agent, privacy, and cost metrics required by the evaluation document.
- Add a measurable acceptance assertion for every functional or quality requirement changed.
- Test authorization denial, policy denial, provenance loss, idempotency, retries, and rollback paths before success-path optimization.
- Never relax thresholds to make a suite pass.
- Run RND acceptance tests without requiring PostgreSQL, Redis, MinIO, or production observability unless the tested change explicitly covers those services.
