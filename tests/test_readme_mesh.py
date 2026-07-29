from __future__ import annotations

import json
from pathlib import Path

import pytest
from google.protobuf import json_format

from job_app_helix import readme_mesh_pb2
from job_app_helix.readme_mesh import (
    BEGIN_MARKER,
    END_MARKER,
    ReadmeMeshError,
    apply_block,
    build_artifacts,
    render_repository_block,
    validate_mesh,
)
from job_app_helix.readme_mesh_manifest import load_mesh

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "readme_mesh.json"


def test_manifest_is_valid_and_has_three_audiences_per_repository() -> None:
    source = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert source["manifest_kind"] == "readme_mesh_index"
    mesh = load_mesh(MANIFEST)
    assert len(mesh.repositories) >= 10
    for node in mesh.repositories:
        assert {section.audience for section in node.sections} == {
            readme_mesh_pb2.RECRUITER,
            readme_mesh_pb2.EXPERT,
            readme_mesh_pb2.AI_AGENT,
        }


def test_protobuf_round_trip_is_deterministic() -> None:
    mesh = load_mesh(MANIFEST)
    artifacts = build_artifacts(mesh)
    decoded = readme_mesh_pb2.ReadmeMesh.FromString(artifacts.binary)
    assert decoded == mesh
    assert decoded.SerializeToString(deterministic=True) == artifacts.binary
    protojson = json.loads(artifacts.protojson)
    reparsed = readme_mesh_pb2.ReadmeMesh()
    json_format.ParseDict(protojson, reparsed)
    assert reparsed == mesh


def test_rendered_block_is_three_audience_and_machine_readable() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_repository_block(mesh, "GlacierEQ/job-app-helix")
    assert block.count(BEGIN_MARKER) == 1
    assert block.count(END_MARKER) == 1
    assert "For recruiters and non-specialists" in block
    assert "For senior engineers and domain experts" in block
    assert "For AI systems and toolchains" in block
    assert "```protobuf" in block
    assert "Repository mesh" in block


def test_apply_block_is_idempotent() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_repository_block(mesh, "GlacierEQ/job-app-helix")
    original = "# Example\n\nIntro.\n\n## Existing\n\nKeep me.\n"
    first = apply_block(original, block)
    second = apply_block(first, block)
    assert first == second
    assert "Keep me." in second


def test_unknown_edge_target_is_rejected() -> None:
    mesh = load_mesh(MANIFEST)
    mesh.edges[0].target = "GlacierEQ/does-not-exist"
    with pytest.raises(ReadmeMeshError, match="edge target"):
        validate_mesh(mesh)


def test_missing_audience_is_rejected() -> None:
    mesh = load_mesh(MANIFEST)
    del mesh.repositories[0].sections[-1]
    with pytest.raises(ReadmeMeshError, match="exactly one section"):
        validate_mesh(mesh)


def test_legal_case_vocabulary_is_rejected() -> None:
    mesh = load_mesh(MANIFEST)
    mesh.repositories[0].innovation = "Links a family court docket"
    with pytest.raises(ReadmeMeshError, match="excluded legal/case vocabulary"):
        validate_mesh(mesh)
