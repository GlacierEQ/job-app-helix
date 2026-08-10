from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = (
    ROOT / "manifests" / "public_repository_surface_decisions_2026-08-08.json"
)

EXPECTED_HISTORICAL_UNASSESSED = {
    "GlacierEQ/AEON-777",
    "GlacierEQ/ECHO",
    "GlacierEQ/GlacierEQ_Swarm",
    "GlacierEQ/Pro-comet-agent",
    "GlacierEQ/Template",
    "GlacierEQ/ai-auto-driller-unified",
    "GlacierEQ/anthropic-agent-coordinator",
    "GlacierEQ/anthropic-safety-monitor",
    "GlacierEQ/apex-cli",
    "GlacierEQ/apex-control-plane",
    "GlacierEQ/apple-ane-kv-quantizer",
    "GlacierEQ/aws-trainium-neuron-sentinel",
    "GlacierEQ/colossus-gateway",
    "GlacierEQ/colossus-training-flux",
    "GlacierEQ/comet-browser-agent-bridge",
    "GlacierEQ/computer-user-storage",
    "GlacierEQ/deepmind-tpu-mesh-optimizer",
    "GlacierEQ/deepseek-mla-moe-sentinel",
    "GlacierEQ/fiat-justitia",
    "GlacierEQ/glaciereq-mcp-stack",
    "GlacierEQ/grokodile",
    "GlacierEQ/kimi-mooncake-kv-stream",
    "GlacierEQ/legal-powerhouse",
    "GlacierEQ/lovable-design-app-synth",
    "GlacierEQ/manus-autonomous-web-agent",
    "GlacierEQ/megamind",
    "GlacierEQ/meta-llama-collective-sentinel",
    "GlacierEQ/microsoft-azure-ops",
    "GlacierEQ/microsoft-identity-zero-trust",
    "GlacierEQ/notion-mcp-empowerment-engine",
    "GlacierEQ/notion-workflow-intelligence",
    "GlacierEQ/notion-workspace-optimizer",
    "GlacierEQ/nvidia-deep-reasoning",
    "GlacierEQ/nvidia-gpu-health",
    "GlacierEQ/openclaw",
    "GlacierEQ/opencode",
    "GlacierEQ/opera-neon-spatial-workspace",
    "GlacierEQ/public-actions-runner-host",
    "GlacierEQ/qwen-vl-flash-router",
    "GlacierEQ/robotics-vla-torque-sentinel",
    "GlacierEQ/sigma-glue",
    "GlacierEQ/spacex-autonomy",
    "GlacierEQ/spacex-conjunction-sentinel",
    "GlacierEQ/spacex-cryogenics",
    "GlacierEQ/spacex-ground-network",
    "GlacierEQ/spacex-launch-sequencer",
    "GlacierEQ/spacex-mission-control",
    "GlacierEQ/spacex-orbital-mechanics",
    "GlacierEQ/spacex-pad-weather-gate",
    "GlacierEQ/spacex-propulsion-monitor",
    "GlacierEQ/spacex-satellite-mesh",
    "GlacierEQ/spacex-telemetry",
    "GlacierEQ/spacex-thermal-protection",
    "GlacierEQ/spiral-engine",
    "GlacierEQ/tasklet-micro-agent-engine",
    "GlacierEQ/tesla-fsd-occupancy-stream",
    "GlacierEQ/the-tower-of-babel",
    "GlacierEQ/token_saver",
}


def load() -> dict:
    return json.loads(DECISIONS.read_text(encoding="utf-8"))


def test_decision_wave_resolves_every_historical_unknown() -> None:
    payload = load()
    items = payload["items"]
    repos = [item["repository"] for item in items]
    assert len(items) == 58
    assert len(set(repos)) == 58
    assert set(repos) == EXPECTED_HISTORICAL_UNASSESSED
    assert payload["unassessed_remaining"] == 0
    assert all(item["historical_assessment"] == "UNASSESSED" for item in items)
    assert all(item["decision"] != "UNASSESSED" for item in items)


def test_decisions_are_fail_closed_and_counted() -> None:
    payload = load()
    allowed = {"ADMIT", "REPAIR_REQUIRED", "QUARANTINED", "REFERENCE", "SUPERSEDED"}
    decisions = Counter(item["decision"] for item in payload["items"])
    assert set(decisions) <= allowed
    assert decisions == Counter(
        {
            "REPAIR_REQUIRED": 52,
            "QUARANTINED": 3,
            "ADMIT": 2,
            "REFERENCE": 1,
        }
    )
    assert payload["decision_counts"] == {
        "ADMIT": 2,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 52,
    }
    assert "SUPERSEDED" not in decisions
    assert all(item["next_gate"].strip() for item in payload["items"])


def test_admit_is_restricted_to_exact_head_evidence() -> None:
    admitted = {
        item["repository"]: item
        for item in load()["items"]
        if item["decision"] == "ADMIT"
    }
    assert set(admitted) == {
        "GlacierEQ/anthropic-agent-coordinator",
        "GlacierEQ/anthropic-safety-monitor",
    }
    assert admitted["GlacierEQ/anthropic-agent-coordinator"]["evidence"][
        "canonical_head"
    ] == "ac977563cfd59deb8e87177f53082184f6468aa8"
    assert admitted["GlacierEQ/anthropic-safety-monitor"]["evidence"][
        "canonical_head"
    ] == "a5c21172e32ce6054994402c38d86f7ef94bc56b"


def test_public_legal_and_identity_risks_are_quarantined() -> None:
    quarantined = {
        item["repository"]
        for item in load()["items"]
        if item["decision"] == "QUARANTINED"
    }
    assert quarantined == {
        "GlacierEQ/fiat-justitia",
        "GlacierEQ/legal-powerhouse",
        "GlacierEQ/opencode",
    }


def test_tower_does_not_inherit_older_admission_after_new_governance_failure() -> None:
    tower = next(
        item
        for item in load()["items"]
        if item["repository"] == "GlacierEQ/the-tower-of-babel"
    )
    assert tower["decision"] == "REPAIR_REQUIRED"
    assert tower["excellence_state"] == "BLOCKED"
    assert tower["evidence"]["canonical_head"] == (
        "9055c92c638d3f5f98d17c2ac07f56afdc227cd1"
    )
    assert "Main Ruleset Contract" in tower["evidence"]["finding"]
