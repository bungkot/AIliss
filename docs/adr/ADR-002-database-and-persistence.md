# Database and Persistence Baseline

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The system needs typed API contracts, transactional domain state, asynchronous extraction, scheduled jobs, and operationally simple deployment for the first release.

## Options considered

Immediate microservices increase deployment and coordination complexity. A modular monolith API plus worker pools preserves separation while sharing contracts and migrations initially.

Raw SQLAlchemy declarative models and direct SQLAlchemy imports were considered, but they duplicate typed API schemas and increase boundary conversion in FastAPI.

## Decision

Use Python 3.12+, FastAPI, Pydantic v2, SQLModel, Alembic, PostgreSQL, Redis, and Celery.

- Define database entities and API boundary models with SQLModel where practical.
- Treat SQLAlchemy as the underlying SQLModel engine and ORM implementation; application services and API modules must not depend on SQLAlchemy declarative APIs directly.
- Use SQLite only for the local RND profile.
- Use PostgreSQL as the production database.
- Keep repository and service boundaries so database-driver/session changes do not leak domain behavior.
- Use Alembic for schema migrations in both SQLite RND and PostgreSQL production.
- Split worker pools for browser, default, and model workloads.

Replacing SQLModel, the database engine, Redis, or Celery requires a migration ADR with compatibility and rollback evidence.

## Consequences

Redis/Celery remains the baseline queue and cache. The team gains robust typed APIs and transactions, with queue memory, idempotency, retry, and worker compatibility requirements. Revisit after throughput, latency, operational, or managed-service constraints conflict with this baseline.
