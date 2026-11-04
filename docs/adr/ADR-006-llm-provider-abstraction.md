# LLM Provider Abstraction

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The platform requires local Ollama support and potentially configurable hosted models. Provider changes must not alter domain or policy contracts.

## Options considered

Provider-specific calls couple orchestration to vendors; direct prompt libraries duplicate fallback and audit behavior. A common adapter with provider-specific configuration offers isolation.

## Decision

Define one provider interface with typed input/output, model version, token/cost metadata, timeout, fallback, and offline evaluation. Ollama and hosted providers implement it without direct agent access to secrets or storage.

## Consequences

Provider parity, quality, and cost need continuous measurement. Revisit if routing, privacy, latency, or evaluation constraints make the common interface materially unrepresentative.
