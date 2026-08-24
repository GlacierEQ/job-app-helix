from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_agents_surface_is_operator_first() -> None:
    text = (ROOT / "agents.md").read_text(encoding="utf-8").lower()
    assert "casey barton" in text
    assert "sole human authority" in text
    assert "mermicorn grove federation rules" not in text
    assert "cherry — domain judgment and final decisions" not in text


def test_portfolio_root_coordinates_without_project_authority() -> None:
    root = load_json("manifests/portfolio_root_truth.json")
    model = root["truth_model"]
    authority = model["portfolio_authority"].lower()

    assert authority.startswith("no_project_direction_authority:")
    assert "helix owns" not in authority
    assert "do not grant helix authority" in authority
    assert "project-direction authority" in root["purpose"].lower()
    assert any(
        "never grant project-direction authority" in item.lower()
        for item in root["invariants"]
    )


def test_active_readme_mesh_has_no_governor_edges() -> None:
    edges = load_json("manifests/readme_mesh.d/edges.json")["edges"]
    assert edges
    assert all(edge["relation"] != "GOVERNED_BY" for edge in edges)
    akos_edges = [edge for edge in edges if edge["target"] == "GlacierEQ/AKOS"]
    assert akos_edges
    assert all(edge["relation"] == "CONSUMES" for edge in akos_edges)
    assert all("project-direction authority" in edge["value"] for edge in akos_edges)


def test_candidate_machine_surface_does_not_inherit_akos_authority() -> None:
    candidate = load_json("hire_package/casey-barton/candidate_node.json")
    relationships = candidate["relationships"]
    assert all(row["relation"] != "GOVERNED_BY" for row in relationships)
    akos = next(row for row in relationships if row["target"] == "GlacierEQ/AKOS")
    assert akos["relation"] == "CONSUMES"
    assert "no project-direction authority" in akos["combined_value"].lower()


def test_public_readme_uses_current_apex_boundary() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()

    assert "primary operator:** casey barton" in lowered
    assert "helix is a **coordination and execution plane**, not an estate ruler" in lowered
    assert "governance and verification center" not in lowered
    assert "akos supplies authority" not in lowered
    assert "helix governs the evidence boundary" not in lowered
    assert "docs/readme_apex_template.md" in lowered


def test_legacy_wire_name_is_explicitly_non_authoritative() -> None:
    index = load_json("manifests/readme_mesh.json")
    assert index["projection_semantics"] == "LEGACY_PUBLIC_EVIDENCE_ONLY"
    assert index["project_direction_authority"] is False

    readme_mesh_source = (ROOT / "src/job_app_helix/readme_mesh.py").read_text(
        encoding="utf-8"
    )
    assert "retired GOVERNED_BY" in readme_mesh_source
    assert "LEGACY_NON_AUTHORITATIVE_RELATIONS" in readme_mesh_source
