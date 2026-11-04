from sqlmodel import select

from ailiss.agents import (
    Budget,
    MockProvider,
    OllamaProvider,
    ProviderRequest,
    ProviderUnavailableError,
    ToolGateway,
    ToolOutcome,
    run_bounded_agent,
)
from ailiss.evaluation import enforce_phase3_gates, evaluate_dataset
from ailiss.models import AgentRun


def test_agent_run_is_persisted_and_readable(client, tmp_database):
    campaign = client.post(
        "/v1/campaigns",
        json={"name": "Phase 3", "discovery_prompt": "Evaluate approved evidence"},
    )
    assert campaign.status_code == 201

    response = client.post(
        "/v1/agent-runs",
        json={
            "campaign_id": campaign.json()["id"],
            "prompt": "Review the campaign evidence and recommend next steps.",
            "provider": "mock",
            "model": "qwen3:0.6b",
            "config_hash": "sha256:phase3-test",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["terminal_status"] == "complete"
    assert body["steps"] >= 6
    assert body["tool_calls"] == 1
    assert body["recommendation"]

    get_response = client.get(f"/v1/agent-runs/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["config_hash"] == "sha256:phase3-test"

    stored = tmp_database.exec(select(AgentRun)).first()
    assert stored is not None
    assert stored.citations == "campaign:" + campaign.json()["id"]


def test_tool_gateway_denies_write_and_unknown_tools():
    gateway = ToolGateway(
        {
            "campaign.get": lambda **kwargs: ToolOutcome(
                code="ok",
                data={"campaign_id": kwargs["campaign_id"]},
            )
        }
    )

    assert gateway.invoke("campaign.get", campaign_id="campaign-1").code == "ok"
    assert gateway.invoke("leads.approve", lead_id="lead-1").code == "denied"


def test_budget_exhaustion_is_typed():
    gateway = ToolGateway(
        {
            "campaign.get": lambda **kwargs: ToolOutcome(
                code="ok",
                data={"campaign_id": kwargs["campaign_id"]},
            )
        }
    )
    result = run_bounded_agent(
        campaign_id="campaign-1",
        prompt="short prompt",
        correlation_id="test-correlation",
        gateway=gateway,
        provider=MockProvider(),
        budget=Budget(max_steps=1, max_tool_calls=0, max_tokens=1, max_bytes=1),
    )

    assert result["terminal_status"] == "budget_exhausted"


def test_ollama_provider_contract_is_typed(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"response":"ok","model":"qwen3:0.6b","eval_count":3}'

    def urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["url"] = request.full_url
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    provider = OllamaProvider("http://127.0.0.1:11434", timeout_seconds=4.0)
    response = provider.generate(
        ProviderRequest(prompt="test", model="qwen3:0.6b", timeout_seconds=4.0)
    )

    assert captured["timeout"] == 4.0
    assert captured["url"].endswith("/api/generate")
    assert response.model == "qwen3:0.6b"
    assert response.tokens == 3


def test_ollama_provider_timeout_is_retryable(monkeypatch):
    attempts = {"count": 0}

    def urlopen(request, timeout):
        attempts["count"] += 1
        raise TimeoutError("provider timed out")

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    provider = OllamaProvider(
        "http://127.0.0.1:11434",
        timeout_seconds=4.0,
        max_attempts=2,
    )

    try:
        provider.generate(
            ProviderRequest(prompt="test", model="qwen3:0.6b", timeout_seconds=4.0)
        )
        raise AssertionError("ProviderUnavailableError was not raised")
    except ProviderUnavailableError:
        pass

    assert attempts["count"] == 2


def test_agent_maps_provider_unavailable_to_retryable():
    class UnavailableProvider:
        def generate(self, request):
            raise ProviderUnavailableError("dependency unavailable")

    gateway = ToolGateway(
        {
            "campaign.get": lambda **kwargs: ToolOutcome(
                code="ok",
                data={"campaign_id": kwargs["campaign_id"]},
            )
        }
    )
    result = run_bounded_agent(
        campaign_id="campaign-1",
        prompt="short prompt",
        correlation_id="test-correlation",
        gateway=gateway,
        provider=UnavailableProvider(),
        budget=Budget(),
    )

    assert result["terminal_status"] == "retryable"
    assert "retry" in result["recommendation"].lower()


def test_phase3_offline_evaluation_gates():
    report = evaluate_dataset("evals/phase3-agent-cases.json")
    gates = enforce_phase3_gates(report)

    assert report.case_count == 5
    assert gates == {
        "tool_validity": True,
        "policy_compliance": True,
        "schema_validity": True,
    }
