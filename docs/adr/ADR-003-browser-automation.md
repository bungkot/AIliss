# Browser Automation

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

Browser extraction introduces identity, storage, network, challenge, resource, and process risks. Pages are untrusted, and source access must remain policy-controlled.

## Options considered

Browser automation inside the API offers convenience but couples secrets and resource exhaustion to interactive traffic. Shared browser state improves setup but cross-campaign leakage risk.

## Decision

Use Playwright Chromium in dedicated workers with isolated contexts, approved destinations, fixed timeouts, source-specific rate limits, process cleanup, artifact hashing, and screenshots only under policy. Never bypass CAPTCHA or reuse sessions across campaigns.

## Consequences

Browser capacity becomes a pool-level resource and operational dependency. Revisit when browser isolation exceeds worker limits or a rendering requirement has evidence for another engine.
