# Agent Orchestration Boundaries

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Agentic stages need typed state, bounded transitions, checkpoints, tool authorization, provider substitution, and auditable outcomes without unrestricted domain mutation.

## Options considered

Free-form tool-calling agents offer flexibility but expand policy and evaluation risk. Direct worker orchestration lacks adaptive recovery. LangGraph plus narrow MCP tools provides explicit states and capability boundaries.

## Decision

Use LangGraph for bounded state machines and MCP for authorized tool access. MCP tools expose schemas, idempotency, side-effect class, and typed failures. Mutations to domain truth remain behind transactional services and approvals.

## Consequences

The graph is longer-lived and requires step/token/time/cost budgets, but tool and policy boundaries are explicit. Revisit if graph/tool overhead or failure recovery cannot meet throughput or cost requirements.
