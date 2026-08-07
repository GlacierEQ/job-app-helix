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
    scope = payload["scope"]
    assert scope["kind"] == "PUBLIC_NATIVE_DEFERRED_CANDIDATES"
    assert scope["repository_count"] == 5

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


def test_wave_1_dispositions_and_summary_reconcile() -> None:
    payload = _load()
    records = payload["repositories"]
    counts = Counter(record["disposition"] for record in records)
    assert counts == {
        "PROMOTION_CANDIDATE": 2,
        "CUSTOMIZED_DOWNSTREAM": 1,
        "REFERENCE_IMPORT": 1,
        "SUPPORTING_INFRASTRUCTURE": 1,
    }

    summary = payload["wave_summary"]
    assert summary == {
        "promotion_candidates": 2,
        "customized_downstreams": 1,
        "reference_imports": 1,
        "supporting_infrastructure": 1,
        "currently_fresh_verified_for_promotion": 0,
    }


def test_wave_1_preserves_known_truth_boundaries() -> None:
    payload = _load()
    by_repo = {record["repository"]: record for record in payload["repositories"]}

    assert by_repo["GlacierEQ/ECHO"]["verification_state"] == "REFRESH_REQUIRED"
    assert (
        by_repo["GlacierEQ/ai-auto-driller-unified"]["verification_state"]
        == "REFRESH_REQUIRED"
    )
    assert (
        by_repo["GlacierEQ/grok-build"]["recruiter_use"]
        == "DOWNSTREAM_DELTA_ONLY_WITH_ATTRIBUTION"
    )
    assert by_repo["GlacierEQ/grok-build"]["upstream"] == "xai-org/grok-build"
    assert by_repo["GlacierEQ/Kimi-K3"]["recruiter_use"] == (
        "EXCLUDE_AS_GLACIEREQ_ENGINEERING"
    )
    assert by_repo["GlacierEQ/public-actions-runner-host"]["verification_state"] == (
        "IMPLEMENTED_NOT_ACTIVATED"
    )
