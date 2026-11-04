# Phase 4 Operation Controls

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Phase 4 requires durable operation state, bounded worker pools, readiness
separation, measurable operation activity, and privacy-retention controls
without enabling live collection or personal-field processing.

## Options considered

An API-only implementation would lack restart recovery. Keeping queue behavior
inside SQLite would couple worker scheduling to application persistence and
would not provide the production queue boundary documented by the architecture.
An unbounded middleware metric implementation would not expose stable
operational signals.

## Decision

- Keep PostgreSQL as the production database and SQLite as the local RND database.
- Use the existing Redis/Celery baseline for production operation dispatch.
- Keep browser, default, and model workers on separate queues and concurrency profiles.
- Persist durable operations in SQLModel/Alembic with immutable payload hashes, unique
  idempotency keys, correlation IDs, attempt ceilings, and typed outcomes.
- Expose liveness and database readiness separately.
- Expose lightweight application metrics through `/metrics`; production collectors
  remain optional until the OpenTelemetry profile is activated.
- Export public lead identifiers only; personal data is excluded by this contract.
- Archive and purge only when campaign retention policy permits deletion, legal hold
  is false, and purge confirmation is explicit.

## Consequences

The repository gains restartable operation contracts and auditable privacy
controls. Queue delivery, worker result handlers, secrets, backups, alerting,
legal approval, and live worker rollout still require operational evidence and
deployment authorization.
