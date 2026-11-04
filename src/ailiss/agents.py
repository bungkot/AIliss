import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


class Budget(BaseModel):
    max_steps: int = Field(default=8, ge=1, le=100)
    max_tool_calls: int = Field(default=6, ge=0, le=100)
    max_tokens: int = Field(default=4000, ge=1, le=100_000)
    max_wall_seconds: float = Field(default=30.0, gt=0, le=3600)
    max_bytes: int = Field(default=100_000, ge=1, le=10_000_000)
    max_spend_usd: float = Field(default=0.25, ge=0, le=1000)


class ToolOutcome(BaseModel):
    code: str
    data: Mapping[str, Any] | None = None
    message: str | None = None


class ProviderRequest(BaseModel):
    prompt: str = Field(max_length=4000)
    model: str = Field(max_length=128)
    max_tokens: int = Field(default=4000, ge=1, le=100_000)
    timeout_seconds: float = Field(default=10.0, gt=0, le=60)


class ProviderResponse(BaseModel):
    text: str
    model: str
    tokens: int = Field(default=0, ge=0)
    bytes_used: int = Field(default=0, ge=0)
    spend_usd: float = Field(default=0.0, ge=0.0)


class ProviderAdapter:
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError


class ProviderUnavailableError(RuntimeError):
    pass


class MockProvider(ProviderAdapter):
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        text = (
            "Recommendation: gather only approved public evidence for the named campaign. "
            "No lead promotion or merge is authorized."
        )
        return ProviderResponse(
            text=text,
            model=request.model,
            tokens=min(len(request.prompt.split()) + 24, request.max_tokens),
            bytes_used=len(text.encode("utf-8")),
        )


class OllamaProvider(ProviderAdapter):
    def __init__(self, base_url: str, timeout_seconds: float = 10.0, max_attempts: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = min(max(max_attempts, 1), 3)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        payload = json.dumps(
            {
                "model": request.model,
                "prompt": request.prompt,
                "stream": False,
                "think": False,
                "options": {"num_predict": min(request.max_tokens, 1024)},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout_seconds = min(request.timeout_seconds, self.timeout_seconds)
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                    result = json.loads(response.read().decode("utf-8"))
                break
            except (
                TimeoutError,
                urllib.error.URLError,
                urllib.error.HTTPError,
                json.JSONDecodeError,
            ) as exc:
                if attempt == self.max_attempts:
                    raise ProviderUnavailableError(
                        f"Ollama provider unavailable after {attempt} attempts"
                    ) from exc
                time.sleep(min(attempt, 2))
        else:
            raise ProviderUnavailableError("Ollama provider returned no response")
        text = str(result.get("response", ""))
        if not text.strip():
            raise ProviderUnavailableError("Ollama provider returned an empty response")
        tokens = int(result.get("eval_count", len(text.split())))
        return ProviderResponse(
            text=text,
            model=str(result.get("model", request.model)),
            tokens=tokens,
            bytes_used=len(text.encode("utf-8")),
        )


class ToolDeclaration(BaseModel):
    name: str
    authorization_scope: str
    side_effect_class: str
    timeout_seconds: float = 10.0
    idempotency_required: bool = False


class ToolGateway:
    def __init__(self, tools: Mapping[str, Callable[..., ToolOutcome]]):
        self.tools = dict(tools)
        self.declarations = {
            "campaign.get": ToolDeclaration(
                name="campaign.get",
                authorization_scope="campaign:read",
                side_effect_class="read",
            ),
            "source.policy_check": ToolDeclaration(
                name="source.policy_check",
                authorization_scope="policy:read",
                side_effect_class="read",
            ),
        }

    def invoke(self, name: str, **kwargs: Any) -> ToolOutcome:
        handler = self.tools.get(name)
        if handler is None:
            return ToolOutcome(code="denied", message=f"tool_not_allowlisted:{name}")
        declaration = self.declarations.get(name)
        if declaration is None or declaration.side_effect_class != "read":
            return ToolOutcome(code="denied", message="write_tools_not_permitted")
        return handler(**kwargs)


class AgentState(TypedDict, total=False):
    prompt: str
    campaign_id: str
    correlation_id: str
    provider: ProviderAdapter
    budget: Budget
    steps: int
    tool_calls: int
    tokens: int
    bytes_used: int
    spend_usd: float
    recommendation: str
    citations: list[str]
    terminal_status: str
    model: str


def bounded_graph(
    gateway: ToolGateway,
    provider: ProviderAdapter,
    budget: Budget,
) -> Any:
    workflow = StateGraph(AgentState)

    def increment(state: AgentState) -> AgentState:
        state["steps"] = state.get("steps", 0) + 1
        return state

    def plan(state: AgentState) -> AgentState:
        state = increment(state)
        state["recommendation"] = ""
        state["citations"] = []
        state["terminal_status"] = "complete"
        return state

    def inspect(state: AgentState) -> AgentState:
        state = increment(state)
        outcome = gateway.invoke(
            "campaign.get",
            campaign_id=state["campaign_id"],
            correlation_id=state["correlation_id"],
        )
        state["tool_calls"] = state.get("tool_calls", 0) + 1
        if outcome.code != "ok":
            state["terminal_status"] = "policy_rejected"
            state["recommendation"] = outcome.message or "Inspection denied"
        return state

    def retrieve(state: AgentState) -> AgentState:
        state = increment(state)
        state["citations"] = [
            f"campaign:{state['campaign_id']}",
        ]
        return state

    def evaluate(state: AgentState) -> AgentState:
        state = increment(state)
        try:
            response = provider.generate(
                ProviderRequest(
                    prompt=state["prompt"],
                    model=state.get("model", "qwen3:0.6b"),
                    max_tokens=min(budget.max_tokens, 1024),
                    timeout_seconds=min(budget.max_wall_seconds, 60.0),
                )
            )
        except ProviderUnavailableError:
            state["terminal_status"] = "retryable"
            state["recommendation"] = (
                "Model provider unavailable; retry the agent run after dependency recovery"
            )
            return state
        state["recommendation"] = response.text
        state["tokens"] = state.get("tokens", 0) + response.tokens
        state["bytes_used"] = state.get("bytes_used", 0) + response.bytes_used
        state["spend_usd"] = state.get("spend_usd", 0.0) + response.spend_usd
        return state

    def verify(state: AgentState) -> AgentState:
        state = increment(state)
        if state.get("steps", 0) > budget.max_steps:
            state["terminal_status"] = "budget_exhausted"
        elif state.get("tool_calls", 0) > budget.max_tool_calls:
            state["terminal_status"] = "budget_exhausted"
        elif state.get("tokens", 0) > budget.max_tokens:
            state["terminal_status"] = "budget_exhausted"
        elif state.get("bytes_used", 0) > budget.max_bytes:
            state["terminal_status"] = "budget_exhausted"
        elif state.get("spend_usd", 0.0) > budget.max_spend_usd:
            state["terminal_status"] = "budget_exhausted"
        elif not state.get("citations"):
            state["terminal_status"] = "blocked"
            state["recommendation"] = "Evidence grounding missing"
        return state

    def recommend(state: AgentState) -> AgentState:
        state = increment(state)
        return state

    def escalate(state: AgentState) -> AgentState:
        if not state.get("recommendation"):
            state["recommendation"] = "Escalated for deterministic policy and human review"
        return state

    workflow.add_node("plan", plan)
    workflow.add_node("inspect", inspect)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("evaluate", evaluate)
    workflow.add_node("verify", verify)
    workflow.add_node("recommend", recommend)
    workflow.add_node("escalate", escalate)
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "inspect")
    workflow.add_edge("inspect", "retrieve")
    workflow.add_edge("retrieve", "evaluate")
    workflow.add_edge("evaluate", "verify")
    workflow.add_conditional_edges(
        "verify",
        lambda state: ("recommend" if state["terminal_status"] == "complete" else "escalate"),
    )
    workflow.add_edge("recommend", END)
    workflow.add_edge("escalate", END)
    return workflow.compile()


def run_bounded_agent(
    *,
    campaign_id: str,
    prompt: str,
    correlation_id: str,
    gateway: ToolGateway,
    provider: ProviderAdapter,
    budget: Budget,
    model: str = "qwen3:0.6b",
) -> AgentState:
    started = time.monotonic()
    graph = bounded_graph(gateway, provider, budget)
    state = graph.invoke(
        {
            "campaign_id": campaign_id,
            "prompt": prompt,
            "correlation_id": correlation_id,
            "steps": 0,
            "tool_calls": 0,
            "tokens": 0,
            "bytes_used": 0,
            "spend_usd": 0.0,
            "terminal_status": "complete",
            "model": model,
        }
    )
    wall_seconds = time.monotonic() - started
    if wall_seconds > budget.max_wall_seconds:
        state["terminal_status"] = "budget_exhausted"
    state["wall_seconds"] = wall_seconds
    return state
