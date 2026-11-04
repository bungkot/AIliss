# Phase 5 Controlled Expansion

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Adding sources, fields, providers, parsers, browser adapters, storage, and queue
behavior can increase policy, quality, cost, or operational risk. Expansion
must remain reversible and must not become an implicit authorization mechanism.

## Options considered

Direct configuration changes are fastest but bypass audit, staged rollout, and
rollback contracts. An unrestricted feature flag provider would duplicate source
and field policy logic. A typed campaign-scoped expansion release reuses the
existing policy, fixture, evaluation, migration, and audit boundaries.

## Decision

- Register expansion releases with immutable config and evidence hashes.
- Start source and field releases at zero rollout.
- Allow personal fields only after separate authorization and legal/review gates.
- Restrict public fields to a fixed allowlist until an approved policy contract expands it.
- Validate source domains against the campaign source policy.
- Stage percentages only after approval, fixture evidence, and evaluation evidence exist.
- Preserve pause, resume, disable, and rollback transitions with audit events.
- Store campaign worker budgets for default, browser, and model pools.
- Require concurrency, byte, token, spend, and request-rate ceilings.
- Keep live source navigation and external writes disabled by implementation policy.

## Consequences

Phase 5 provides controlled rollout primitives and measurable budgets while
remaining compatible with the modular-monolith baseline. Model/provider,
browser/parser/storage, and queue behavior still require adapter-specific tests,
ADR evidence, security review, production credentials, and deployment ownership.
