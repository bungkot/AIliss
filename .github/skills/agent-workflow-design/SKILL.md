---
name: agent-workflow-design
description: Design bounded LangGraph workflows, typed states, retries, terminal outcomes, and agent handoffs.
---

# Agent Workflow Design

1. Decompose work into explicit states owned by deterministic services where possible.
2. Define typed input, evidence, policy decision, tool result, and terminal state.
3. Set maximum steps, calls, tokens, bytes, time, and cost.
4. Permit only narrow MCP tools with idempotency and authorization.
5. Add retryable, policy-rejected, conflict, partial, and blocked outcomes.
6. Add checkpoint and replay rules without storing secrets or raw personal fields.
7. Evaluate task success, grounding, tool validity, step count, cost, fallback, and refusal behavior.
