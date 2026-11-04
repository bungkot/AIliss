# MCP Integration

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The platform needs standardized integrations for search, browser, validation, enrichment, database, CRM, and reporting tools. Tools require explicit schemas, permissions, authentication, and audit boundaries.

## Options considered

Direct SDK calls reduce protocol overhead but create inconsistent authorization and auditing. MCP adds a tool contract boundary while LangGraph remains responsible for orchestration.

## Decision

Use MCP as the tool integration layer. Every server declares typed inputs and outputs, permissions, authentication, side-effect class, rate limits, retries, and observability. Domain mutations pass through transactional application services and approval policy.

## Consequences

Tools become independently deployable and testable, with additional operational configuration. Revisit if protocol overhead or deployment complexity conflicts with measured requirements.
