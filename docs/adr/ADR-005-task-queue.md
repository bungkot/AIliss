# Task Queue

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Extraction, enrichment, validation, exports, and scheduled operations require durable work, bounded concurrency, retries, backpressure, restart recovery, and operational visibility.

## Options considered

In-process scheduling loses work on restart. Database-only jobs add polling complexity. Redis with Celery provides persistent dispatch and split worker pools while keeping initial operations understandable.

## Decision

Use Celery with Redis as the baseline queue, PostgreSQL for durable job and audit state, and explicit task names, idempotency keys, retry classes, budgets, and dead-letter handling. Browser, default, and model workers remain independently scalable.

## Consequences

Queue operations gain restart recovery and backpressure controls, but broker visibility, retention, and idempotency become operational requirements. Revisit when scale or managed infrastructure justifies another queue.
