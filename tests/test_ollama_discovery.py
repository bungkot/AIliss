import base64
import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlmodel import select

from ailiss.models import Lead

pytestmark = pytest.mark.skipif(
    os.getenv("AILISS_LIVE_OLLAMA") != "1",
    reason="live Ollama smoke test is opt-in",
)


def test_authorized_discovery_pipeline_with_ollama(client, tmp_database):
    wedding_categories = [
        "Wedding organizer",
        "Wedding planner",
        "Jasa foto prewedding",
        "Fotografer wedding",
        "Fotografer prewedding",
        "Studio foto wedding",
        "Studio foto couple",
        "Wedding photography",
        "Prewedding photography",
        "Wedding videographer",
        "Jasa video cinematic wedding",
        "Wedding content creator",
        "Vendor undangan digital",
        "Jasa undangan pernikahan digital",
        "Bridal studio",
        "Wedding gallery",
        "Paket wedding all in",
        "Paket prewedding",
    ]
    locations = ["Jakarta", "Bandung", "Surabaya", "Semarang", "Yogyakarta", "Denpasar"]
    target_count = int(os.getenv("AILISS_DISCOVERY_TARGET_COUNT", "200"))
    discovery_prompt = os.getenv(
        "AILISS_DISCOVERY_PROMPT",
        (
            "Build 200 candidate customer leads for Indonesian wedding vendors. "
            "Categories include wedding organizers, photographers, videographers, "
            "content creators, bridal studios, and digital invitation vendors. "
            "Each candidate must have at least one business contact."
        ),
    )
    if not 1 <= target_count <= 500:
        raise AssertionError("AILISS_DISCOVERY_TARGET_COUNT must be between 1 and 500")
    campaign = client.post(
        "/v1/campaigns",
        json={
            "name": "GitHub Actions discovery",
            "discovery_prompt": discovery_prompt,
        },
        headers={"x-correlation-id": "github-actions-discovery"},
    )
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]

    policy = client.post(
        f"/v1/campaigns/{campaign_id}/source-policy",
        json={
            "allowed_domains": ["example.com"],
            "allowed_fields": [
                "company_name",
                "website",
                "industry",
                "instagram",
                "whatsapp",
                "google_maps",
            ],
            "require_personal_data_review": True,
        },
    )
    assert policy.status_code == 200

    source = client.post(
        f"/v1/campaigns/{campaign_id}/sources",
        json={
            "url": "https://www.example.com/discovery",
            "access_basis": "approved public fixture source",
        },
    )
    assert source.status_code == 201

    run = client.post(
        "/v1/extraction-runs",
        json={
            "campaign_id": campaign_id,
            "source_id": source.json()["id"],
            "config_hash": "sha256:github-actions-discovery",
        },
        headers={"Idempotency-Key": "github-actions-discovery-run"},
    )
    assert run.status_code == 202
    assert run.json()["status"] == "queued"

    fixture_path = Path(__file__).parent / "fixtures" / "wedding-vendors.html"
    raw = fixture_path.read_bytes()
    artifact = client.post(
        f"/v1/extraction-runs/{run.json()['id']}/artifacts",
        json={
            "source_url": source.json()["url"],
            "content_type": "text/html",
            "encoded_content": base64.b64encode(raw).decode("ascii"),
        },
    )
    assert artifact.status_code == 201
    assert artifact.json()["status"] == "staged"
    assert len(artifact.json()["raw_hash"]) == 64

    candidate_leads = []
    for index in range(1, target_count + 1):
        category = wedding_categories[(index - 1) % len(wedding_categories)]
        location = locations[(index - 1) % len(locations)]
        confidence_score = round(0.95 - ((index - 1) % 50) * 0.005, 3)
        candidate = {
            "lead_number": index,
            "company_name": f"Fixture Wedding Vendor {index:03d}",
            "business_category": category,
            "location": location,
            "website": f"https://www.example.com/vendor-{index:03d}",
            "instagram": f"https://www.instagram.com/fixture_vendor_{index:03d}",
            "whatsapp": f"https://wa.me/628000000{index:03d}",
            "google_maps": (
                f"https://maps.google.com/?q=Fixture+Wedding+Vendor+{index:03d}"
            ),
            "evidence_url": source.json()["url"],
            "artifact_hash": artifact.json()["raw_hash"],
            "verification_status": "candidate",
            "confidence_score": confidence_score,
            "status": "candidate",
        }
        candidate_leads.append(candidate)

        lead = Lead(campaign_id=UUID(campaign_id))
        tmp_database.add(lead)

    tmp_database.commit()
    assert len(candidate_leads) == target_count
    assert len(tmp_database.exec(select(Lead)).all()) == target_count
    assert all(
        lead["website"]
        or lead["instagram"]
        or lead["whatsapp"]
        or lead["google_maps"]
        for lead in candidate_leads
    )

    ranked_leads = sorted(
        candidate_leads,
        key=lambda lead: (
            -lead["confidence_score"],
            sum(
                bool(lead[field])
                for field in ("website", "instagram", "whatsapp", "google_maps")
            ) * -1,
            lead["lead_number"],
        ),
    )
    for rank, lead in enumerate(ranked_leads, start=1):
        lead["rank"] = rank
        lead["ranking_reason"] = (
            "deterministic_fixture_score; policy-approved source; "
            "business contact evidence present"
        )
    assert all(
        ranked_leads[index]["confidence_score"]
        >= ranked_leads[index + 1]["confidence_score"]
        for index in range(len(ranked_leads) - 1)
    )

    agent = client.post(
        "/v1/agent-runs",
        json={
            "campaign_id": campaign_id,
            "prompt": campaign.json()["discovery_prompt"],
            "provider": "ollama",
            "model": "qwen3:0.6b",
            "config_hash": "sha256:github-actions-agent",
        },
    )
    assert agent.status_code == 202
    agent_result = agent.json()
    assert agent_result["terminal_status"] == "complete"
    assert agent_result["recommendation"].strip()
    assert agent_result["tool_calls"] == 1

    retrieved = client.get(f"/v1/agent-runs/{agent_result['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["recommendation"] == agent_result["recommendation"]

    output = os.getenv("AILISS_DISCOVERY_OUTPUT")
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "mode": "fixture-only",
                    "campaign_id": campaign_id,
                    "target_count": target_count,
                    "candidate_count": len(candidate_leads),
                    "lead_status": "candidate",
                    "human_review_required": True,
                    "personal_data_collection": "disabled",
                    "terminal_status": agent_result["terminal_status"],
                    "leads": candidate_leads,
                    "ranked_leads": ranked_leads,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
