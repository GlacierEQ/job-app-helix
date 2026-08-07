from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "estate_public_wave_1_2026-08-07.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _load() -> dict[str, object]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_wave_1_scope_and_estate_arithmetic_are_explicit() -> None:
    payload = _load()
    assert payload["schema"] == "glaciereq.estate-public-audit-wave.v2"
    scope = payload["scope"]
    assert scope["kind"] == "PUBLIC_DEFERRED_CANDIDATES_RECONCILED"
    assert scope["repository_count"] == 5
    assert scope["native_repository_count"] == 3
    assert scope["fork_repository_count"] == 2
    assert scope["native_repository_count"] + scope["fork_repository_count"] == 5

    estate = scope["estate_context"]
    assert estate["native_repositories"] + estate["fork_repositories"] == estate[
        "total_holdings"
    ]
    assert (
        estate["active_native_repositories"]
        + estate["archived_native_repositories"]
        == estate["native_repositories"]
    )
    assert (
        estate["public_active_native_repositories"]
        + estate["private_active_native_repositories"]
        == estate["active_native_repositories"]
    )


def test_wave_1_records_are_unique_exact_head_observations() -> None:
    payload = _load()
    records = payload["repositories"]
    assert isinstance(records, list)
    assert len(records) == payload["scope"]["repository_count"]

    repositories = [record["repository"] for record in records]
    assert len(repositories) == len(set(repositories))
    assert all(repository.startswith("GlacierEQ/") for repository in repositories)
    assert all(SHA40.fullmatch(record["head_sha"]) for record in records)

    native = [record for record in records if record["estate_layer"] == "NATIVE"]
    forks = [record for record in records if record["estate_layer"] == "FORK_REFERENCE"]
    assert len(native) == payload["scope"]["native_repository_count"]
    assert len(forks) == payload["scope"]["fork_repository_count"]
    assert all(record["github_fork"] is False for record in native)
    assert all(record["github_fork"] is True for record in forks)


def test_wave_1_dispositions_and_summary_reconcile() -> None:
    payload = _load()
    records = payload["repositories"]
    counts = Counter(record["disposition"] for record in records)
    assert counts == {
        "PROMOTION_CANDIDATE": 2,
        "CUSTOMIZED_FORK_DOWNSTREAM": 1,
        "REFERENCE_FORK": 1,
        "SUPPORTING_INFRASTRUCTURE": 1,
    }

    summary = payload["wave_summary"]
    assert summary == {
        "native_records": 3,
        "fork_records": 2,
        "promotion_candidates": 2,
        "customized_fork_downstreams": 1,
        "reference_forks": 1,
        "supporting_infrastructure": 1,
        "current_head_verified_promotion_candidates": 2,
        "activation_blocked_native_infrastructure": 1,
    }


def test_wave_1_preserves_exact_verification_and_activation_boundaries() -> None:
    payload = _load()
    by_repo = {record["repository"]: record for record in payload["repositories"]}

    echo = by_repo["GlacierEQ/ECHO"]
    assert echo["verification_state"] == "CURRENT_HEAD_VERIFIED"
    assert {item["conclusion"] for item in echo["execution_evidence"]} == {"success"}

    driller = by_repo["GlacierEQ/ai-auto-driller-unified"]
    assert driller["verification_state"] == "CURRENT_HEAD_CI_GREEN"
    assert driller["execution_evidence"][0]["run_id"] == 30897934181

    grok = by_repo["GlacierEQ/grok-build"]
    assert grok["github_fork"] is True
    assert grok["estate_layer"] == "FORK_REFERENCE"
    assert grok["upstream"] == "xai-org/grok-build"
    assert grok["recruiter_use"] == "DOWNSTREAM_DELTA_ONLY_WITH_ATTRIBUTION"
    assert {item["conclusion"] for item in grok["execution_evidence"]} == {
        "success",
        "failure",
    }

    kimi = by_repo["GlacierEQ/Kimi-K3"]
    assert kimi["github_fork"] is True
    assert kimi["estate_layer"] == "FORK_REFERENCE"
    assert kimi["upstream"] == "MoonshotAI/Kimi-K3"
    assert kimi["recruiter_use"] == "EXCLUDE_AS_GLACIEREQ_ENGINEERING"
    assert kimi["execution_evidence"] == []

    runner = by_repo["GlacierEQ/public-actions-runner-host"]
    assert runner["verification_state"] == "CURRENT_HEAD_CI_GREEN_ACTIVATION_BLOCKED"
    by_workflow = {item["workflow"]: item for item in runner["execution_evidence"]}
    assert by_workflow["CI"]["conclusion"] == "success"
    assert by_workflow["APEX Public Action Face"]["conclusion"] == "failure"
    assert "APEX_RUNNER_APP_CLIENT_ID" in by_workflow["APEX Public Action Face"][
        "failure_boundary"
    ]


def test_wave_1_forks_do_not_count_as_native() -> None:
    payload = _load()
    by_repo = {record["repository"]: record for record in payload["repositories"]}

    assert by_repo["GlacierEQ/grok-build"]["estate_layer"] != "NATIVE"
    assert by_repo["GlacierEQ/Kimi-K3"]["estate_layer"] != "NATIVE"
    assert "only three belong to the native-repository estate" in payload["nonclaims"][0]
