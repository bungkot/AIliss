from uuid import UUID

from sqlmodel import select

from ailiss.models import ExpansionRelease, ExpansionStatus, ResourceBudget


def create_campaign(client, name: str = "Phase 5 Campaign"):
    response = client.post(
        "/v1/campaigns",
        json={"name": name, "discovery_prompt": "Find public approved companies"},
        headers={"x-correlation-id": "phase5-test"},
    )
    assert response.status_code == 201
    return response.json()


def evidence_hash(value: str) -> str:
    return value.encode("ascii").hex().ljust(64, "0")[:64]


def policy(client, campaign_id: str):
    response = client.post(
        f"/v1/campaigns/{campaign_id}/source-policy",
        json={
            "allowed_domains": ["example.com"],
            "allowed_fields": ["company_name", "website", "industry"],
            "require_personal_data_review": True,
        },
    )
    assert response.status_code == 200


def release_payload(campaign_id: str, target_type: str, target_name: str):
    return {
        "campaign_id": campaign_id,
        "target_type": target_type,
        "target_name": target_name,
        "config_hash": evidence_hash("config"),
        "policy_evidence_hash": evidence_hash("policy"),
        "fixture_evidence_hash": evidence_hash("fixture"),
        "evaluation_evidence_hash": evidence_hash("evaluation"),
        "rollout_percent": 0,
        "reason": "approved staged expansion",
        "approved_by": "release-owner",
    }


def test_source_expansion_requires_allowed_domain(client, tmp_database):
    campaign = create_campaign(client)
    policy(client, campaign["id"])

    allowed = client.post(
        "/v1/expansion-releases",
        json=release_payload(campaign["id"], "source", "www.example.com"),
    )
    assert allowed.status_code == 201
    assert allowed.json()["status"] == "approved"
    assert allowed.json()["rollout_percent"] == 0

    denied = client.post(
        "/v1/expansion-releases",
        json=release_payload(campaign["id"], "source", "evil.example.net"),
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "policy_denied"

    releases = tmp_database.exec(select(ExpansionRelease)).all()
    assert len(releases) == 1


def test_personal_field_expansion_is_denied(client):
    campaign = create_campaign(client)
    policy(client, campaign["id"])
    response = client.post(
        "/v1/expansion-releases",
        json=release_payload(campaign["id"], "field", "email"),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "policy_denied"


def test_public_field_expansion_stages_pauses_and_rolls_back(client, tmp_database):
    campaign = create_campaign(client)
    policy(client, campaign["id"])
    created = client.post(
        "/v1/expansion-releases",
        json=release_payload(campaign["id"], "field", "industry"),
    )
    assert created.status_code == 201
    release_id = created.json()["id"]

    staged = client.post(
        f"/v1/expansion-releases/{release_id}/stage",
        json={
            "actor": "release-owner",
            "reason": "start 10 percent canary",
            "rollout_percent": 10,
        },
    )
    assert staged.status_code == 200
    assert staged.json()["status"] == "staged"
    assert staged.json()["rollout_percent"] == 10

    paused = client.post(
        f"/v1/expansion-releases/{release_id}/pause",
        json={"actor": "release-owner", "reason": "quality regression"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    resumed = client.post(
        f"/v1/expansion-releases/{release_id}/resume",
        json={"actor": "release-owner", "reason": "quality issue resolved"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "staged"

    rolled_back = client.post(
        f"/v1/expansion-releases/{release_id}/rollback",
        json={"actor": "release-owner", "reason": "cost regression", "rollout_percent": 0},
    )
    assert rolled_back.status_code == 200
    assert rolled_back.json()["status"] == "rolled_back"
    assert rolled_back.json()["rollout_percent"] == 0

    release = tmp_database.get(ExpansionRelease, UUID(release_id))
    assert release.status == ExpansionStatus.ROLLED_BACK


def test_stage_requires_positive_rollout(client):
    campaign = create_campaign(client)
    policy(client, campaign["id"])
    created = client.post(
        "/v1/expansion-releases",
        json=release_payload(campaign["id"], "field", "company_name"),
    )
    response = client.post(
        f"/v1/expansion-releases/{created.json()['id']}/stage",
        json={"actor": "release-owner", "reason": "invalid stage"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "rollout_percent_required"


def test_resource_budget_is_isolated_by_worker_pool(client, tmp_database):
    campaign = create_campaign(client)
    payload = {
        "campaign_id": campaign["id"],
        "worker_pool": "browser",
        "max_concurrency": 2,
        "max_requests_per_second": 5,
        "max_bytes": 500_000,
        "max_tokens": 0,
        "max_spend_usd": 0.50,
        "enabled": True,
    }
    payload["max_tokens"] = 4000
    first = client.post("/v1/resource-budgets", json=payload)
    assert first.status_code == 200
    payload["max_concurrency"] = 1
    updated = client.post("/v1/resource-budgets", json=payload)
    assert updated.status_code == 200
    assert updated.json()["max_concurrency"] == 1

    budgets = tmp_database.exec(
        select(ResourceBudget).where(
            ResourceBudget.campaign_id == UUID(campaign["id"]),
            ResourceBudget.worker_pool == "browser",
        )
    ).all()
    assert len(budgets) == 1
