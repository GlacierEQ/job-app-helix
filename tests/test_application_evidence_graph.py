from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.application_evidence_graph import (
    build_application_evidence_bundle,
    execute_application_evidence_projection,
)


def _graph() -> dict[str, object]:
    return {
        "schema": "glaciereq.live-experience-graph.v1",
        "snapshot_id": "a" * 64,
        "truth_boundary": {
            "inventory_is_not_authorship": True,
            "inventory_is_not_runtime_proof": True,
            "company_mapping_does_not_imply_affiliation": True,
            "private_repository_names_omitted_from_public_graph": True,
        },
        "companies": [
            {"company_id": "xai", "display_name": "xAI"},
            {"company_id": "spacex", "display_name": "SpaceX"},
        ],
        "graph": {
            "public": {
                "nodes": [
                    {"id": "company:xai", "kind": "company"},
                    {"id": "company:spacex", "kind": "company"},
                    {
                        "id": "repo:GlacierEQ/xai-cooling",
                        "kind": "repository",
                        "repository": "GlacierEQ/xai-cooling",
                        "visibility": "public",
                        "promotion_state": "VERIFIED",
                        "provenance_state": "SOURCE_BOUND",
                        "evidence_level": "L4_EXECUTABLE",
                    },
                    {
                        "id": "repo:GlacierEQ/xai-power",
                        "kind": "repository",
                        "repository": "GlacierEQ/xai-power",
                        "visibility": "public",
                        "promotion_state": "UNCLASSIFIED",
                        "provenance_state": "UNCLASSIFIED",
                        "evidence_level": None,
                    },
                    {
                        "id": "flagship:compute-fabric",
                        "kind": "flagship",
                        "system_id": "compute-fabric",
                    },
                    {
                        "id": "paradigm:physical-ai",
                        "kind": "paradigm",
                        "paradigm_id": "physical-ai",
                    },
                ],
                "edges": [
                    {
                        "source": "repo:GlacierEQ/xai-cooling",
                        "target": "company:xai",
                        "relationship": "addresses-company-challenge",
                    },
                    {
                        "source": "repo:GlacierEQ/xai-power",
                        "target": "company:xai",
                        "relationship": "addresses-company-challenge",
                    },
                    {
                        "source": "flagship:compute-fabric",
                        "target": "repo:GlacierEQ/xai-cooling",
                        "relationship": "implemented-by",
                    },
                    {
                        "source": "repo:GlacierEQ/xai-cooling",
                        "target": "paradigm:physical-ai",
                        "relationship": "expresses-paradigm",
                    },
                ],
            }
        },
    }


def test_ranks_stronger_public_proof_first() -> None:
    result = build_application_evidence_bundle(_graph(), company="xAI")

    assert result.evidence_count == 2
    assert [row.repository for row in result.evidence] == [
        "GlacierEQ/xai-cooling",
        "GlacierEQ/xai-power",
    ]
    strongest = result.evidence[0]
    assert strongest.flagship_systems == ("compute-fabric",)
    assert strongest.paradigms == ("physical-ai",)
    assert strongest.score > result.evidence[1].score
    assert "direct-company-challenge-link" in strongest.reasons
    assert result.receipt_sha256


def test_refuses_unsafe_truth_boundary() -> None:
    payload = _graph()
    boundary = payload["truth_boundary"]
    assert isinstance(boundary, dict)
    boundary["inventory_is_not_runtime_proof"] = False

    path = Path("unsafe-graph.json")
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="truth boundary"):
            execute_application_evidence_projection(path, company="xai")
    finally:
        path.unlink(missing_ok=True)


def test_refuses_private_repository_escape() -> None:
    payload = _graph()
    graph = payload["graph"]
    assert isinstance(graph, dict)
    public = graph["public"]
    assert isinstance(public, dict)
    nodes = public["nodes"]
    assert isinstance(nodes, list)
    repo = next(row for row in nodes if row.get("id") == "repo:GlacierEQ/xai-power")
    repo["visibility"] = "private"

    with pytest.raises(ValueError, match="private repository"):
        build_application_evidence_bundle(payload, company="xai")


def test_output_is_deterministic_and_limit_is_enforced(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.json"
    output = tmp_path / "APPLICATION_EVIDENCE.json"
    graph_path.write_text(json.dumps(_graph()), encoding="utf-8")

    first = execute_application_evidence_projection(
        graph_path,
        company="xai",
        output=output,
        limit=1,
    )
    second = execute_application_evidence_projection(
        graph_path,
        company="xAI",
        limit=1,
    )

    assert first.as_dict() == second.as_dict()
    assert first.evidence_count == 1
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["receipt_sha256"] == first.receipt_sha256


def test_wrong_or_ambiguous_company_fails_closed() -> None:
    with pytest.raises(ValueError, match="resolve exactly once"):
        build_application_evidence_bundle(_graph(), company="unknown")
