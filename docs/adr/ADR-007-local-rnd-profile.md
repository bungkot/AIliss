# Local RND Profile

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The laptop development environment has approximately 3.70 GiB available to Docker Desktop and 4 logical CPUs. Running PostgreSQL, Redis, Celery, Ollama, Playwright, object storage, and observability simultaneously does not leave enough memory for reliable development.

The local environment still needs:

- FastAPI for typed API development and provider integration.
- SQLite with SQLModel for a minimal persistent data store.
- Ollama with a small reasoning model, defaulting to `qwen3:0.6b`.
- Playwright Chromium for fixture development and isolated extraction tests.

## Options considered

PostgreSQL plus Redis/Celery preserves the production baseline but adds containers and operational dependencies before basic local behavior is proven. SQLite plus an in-process task runner is simpler, but it lacks production concurrency and durable queue recovery.

Running Ollama in Docker shares the 3.5 GiB Docker limit and can prevent the browser or API from starting. Running Ollama on the Windows host keeps the Docker limit isolated from the model process.

## Decision

Use a local RND profile with:

- FastAPI as the application process.
- SQLModel and a file-backed SQLite database.
- Ollama on the Windows host with `qwen3:0.6b` as the minimum reasoning profile.
- Playwright Chromium as an explicit host or optional Compose profile.
- A bounded in-process task runner for RND.
- No PostgreSQL, Redis, Celery, MinIO, Prometheus, or Grafana in the minimum stack.
- Local filesystem storage for artifacts until S3-compatible storage behavior is tested.

Preserve the production domain model, API contracts, provenance requirements, source-policy gates, provider abstraction, typed outcomes, migrations, and deterministic tests across profiles. Repository/service boundaries must allow SQLite RND persistence to be replaced by PostgreSQL without changing domain behavior.

Redis/Celery may be introduced in RND only for measured restart, scheduling, concurrency, or queue compatibility work. PostgreSQL remains the production persistence target.

## Consequences

The minimum profile is cheaper to start and is usable for API, model, and browser development. SQLite concurrency, cross-process coordination, backup behavior, and queue recovery differ from production and must be validated separately.

Qwen3 0.6B is the first accepted local default, but it is not assumed adequate. Offline evaluation determines whether the model advances to `qwen3:1.7b` or `qwen3:4b`.

## Revisit triggers

Revisit this profile when:

- SQLite write concurrency becomes a measured bottleneck.
- Durable restart, scheduling, retries, or split-worker behavior are required.
- RND needs multiple concurrent API processes.
- A migration to PostgreSQL or another queue is implementation-blocking.
- Offline evaluation shows that the small model misses quality thresholds.
