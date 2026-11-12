from __future__ import annotations

from pathlib import Path

from job_app_helix.readme_four_depth import (
    BEGIN_MARKER,
    END_MARKER,
    choose_titles,
    render_five_depth_block,
)
from job_app_helix.readme_mesh_manifest import load_mesh

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "readme_mesh.json"


def test_five_depth_order_and_stopping_points_are_explicit() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_five_depth_block(mesh, "GlacierEQ/job-app-helix")
    assert block.count(BEGIN_MARKER) == 1
    assert block.count(END_MARKER) == 1
    positions = [
        block.index("## 01 · RECRUITER"),
        block.index("## 02 · EXPERT"),
        block.index("## 03 · GENIUS"),
        block.index("## 04 · MACHINE"),
        block.index("## 05 · MESH"),
    ]
    assert positions == sorted(positions)
    assert "every layer is designed to be a truthful stopping point" in block


def test_visible_titles_are_not_generic_audience_headers() -> None:
    mesh = load_mesh(MANIFEST)
    node = next(node for node in mesh.repositories if node.repository == "GlacierEQ/job-app-helix")
    titles = choose_titles(node)
    for title in (titles.recruiter, titles.expert, titles.genius, titles.machine, titles.mesh):
        assert title
        assert title not in {
            "Overview",
            "Technical Details",
            "Architecture",
            "Links",
            "For recruiters and non-specialists",
            "For senior engineers and domain experts",
            "For AI systems and toolchains",
            "Portfolio mesh",
        }


def test_machine_layer_carries_psysoc_and_statute_backed_license_contract() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_five_depth_block(mesh, "GlacierEQ/job-app-helix")
    assert "schema: glaciereq.readme.five-depth/v1" in block
    assert "capability: stone-psysoc-x" in block
    assert "repository: GlacierEQ/AKOS" in block
    assert "presentation_may_change_truth_may_not" in block
    assert "GlacierEQ Proprietary Copyright License and Enforcement Notice v1.1" in block
    assert "status: ALL_RIGHTS_RESERVED_TITLE_17" in block
    assert "17 U.S.C. § 106" in block
    assert "17 U.S.C. §§ 501-505" in block
    assert "17 U.S.C. § 401(d)" in block
    assert "All rights reserved under U.S. copyright law" in block
    assert "17 U.S.C. § 501" in block


def test_recruiter_is_compact_while_expert_keeps_deeper_evidence() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_five_depth_block(mesh, "GlacierEQ/job-app-helix")
    recruiter = block.split("## 01 · RECRUITER", 1)[1].split("## 02 · EXPERT", 1)[0]
    expert = block.split("## 02 · EXPERT", 1)[1].split("## 03 · GENIUS", 1)[0]
    assert recruiter.count("—") <= expert.count("—")


def test_genius_is_synthesis_not_second_truth_source() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_five_depth_block(mesh, "GlacierEQ/job-app-helix")
    genius = block.split("## 03 · GENIUS", 1)[1].split("## 04 · MACHINE", 1)[0]
    assert "higher-order engineering meaning" in genius
    assert "does not manufacture new facts" in genius
    assert "Innovation:" in genius
    assert "Evolution:" in genius


def test_mesh_uses_typed_relationships_not_flat_related_links() -> None:
    mesh = load_mesh(MANIFEST)
    block = render_five_depth_block(mesh, "GlacierEQ/job-app-helix")
    mesh_section = block.split("## 05 · MESH", 1)[1]
    assert "Relationship" in mesh_section
    assert "Connected repository" in mesh_section
    assert "What becomes stronger together" in mesh_section
    assert "governed by" not in mesh_section.lower()
