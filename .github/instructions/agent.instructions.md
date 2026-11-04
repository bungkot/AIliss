---
applyTo: "**/{agents,mcp}/**,docs/04-agentic-workflow.md,docs/05-context-engineering.md,docs/06-agent-harness-engineering.md,docs/07-mcp-architecture.md"
---

# Agent Engineering

- Load only the context needed for the current graph step.
- Cap steps, tool calls, tokens, wall time, bytes, and spend.
- Define typed terminal outcomes and failure classes.
- MCP tools require schemas, authorization scopes, idempotency, timeouts, and typed failures.
- Agents cannot approve leads, merge records, change retention, send outreach, export data, or bypass source policy.
