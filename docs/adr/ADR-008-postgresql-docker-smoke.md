# PostgreSQL Docker Compatibility Smoke

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

SQLite is the default local RND persistence profile. Production targets
PostgreSQL, so Docker and CI must exercise the real SQLAlchemy dialect and
migrations before production persistence work begins.

## Options considered

Replacing SQLite would increase local RND setup cost and couple fixture and unit
tests to PostgreSQL availability. A PostgreSQL-only integration profile would
leave SQLite startup regressions untested. An explicit PostgreSQL smoke service
preserves the simple SQLite default while validating production dialect
compatibility.

## Decision

Keep SQLite as the default RND API profile. Add a Docker Compose
`postgres` profile with PostgreSQL 16 and a dedicated API service. CI builds this
profile, waits for migration health, verifies `/health`, and removes containers
and volumes. The Python matrix continues to use deterministic SQLite and mocked
providers; live providers and browser navigation remain disabled.

## Consequences

Docker Desktop can validate both local and production-compatible persistence
without changing the minimum RND stack. PostgreSQL image pull, startup, and
memory use are explicit and bounded. The profile is RND only; production
credentials, backups, HA, TLS, and queue services remain phase 4 concerns.
