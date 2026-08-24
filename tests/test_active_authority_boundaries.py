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


def test_restoration_machine_scopes_all_system_roles() -> None:
    machine = load_json("machine/job_ecosystem_restoration.json")
    split = machine["authority_split"]

    assert split["operator_authority"] == "Casey Barton"
    assert "identity_os" not in split
    assert "placement_authority" not in split
    assert split["identity_capability_donor"] == "GlacierEQ/AKOS"
    assert split["technology_placement_capability"] == "GlacierEQ/the-tower-of-babel"
    assert "no repository" in split["project_direction_rule"].lower()
    assert "project-direction authority" in split["project_direction_rule"].lower()


def test_estate_compiler_keeps_lineage_power_without_project_authority() -> None:
    policy = load_json("manifests/estate_compiler.json")
    authority = policy["authority"].lower()

    assert authority.startswith("no_project_direction_authority:")
    assert "casey barton controls project direction" in authority
    assert "repository-native source state remains authoritative" in authority
    assert "canonical_system_registry" in policy["pipeline"]
    assert policy["outputs"]["canonical_system_registry"] == "canonical-system-registry.json"
    assert "deduplication only" in policy["lineage_policy"]["successor_semantics"]
    assert "does not create project-direction authority" in policy["lineage_policy"][
        "successor_semantics"
    ]


def test_portfolio_compiler_is_coordination_not_project_authority() -> None:
    compiler = load_json("manifests/portfolio_compiler.json")
    authority = compiler["portfolio_truth_authority"].lower()

    assert compiler["source_of_truth"] == "repository_native_factual_state"
    assert authority.startswith("no_project_direction_authority:")
    assert "casey barton controls project direction" in authority
    assert "each repository controls its own factual source state" in authority
    assert "canonical_system_registry" in compiler["estate_outputs"]


def test_recruiter_surfaces_do_not_reintroduce_governor_hierarchy() -> None:
    executive = (ROOT / "RECRUITER_EXECUTIVE_SUMMARY.md").read_text(
        encoding="utf-8"
    ).lower()
    candidate = (ROOT / "hire_package/casey-barton/README.md").read_text(
        encoding="utf-8"
    ).lower()
    tower = (ROOT / "hire_package/casey-barton/TOWER_OF_BABEL_INTEGRATION.md").read_text(
        encoding="utf-8"
    ).lower()

    for text in (executive, candidate, tower):
        assert "akos supplies authority" not in text
        assert "tower governs" not in text
        assert "helix governs candidate" not in text

    assert "capability donor" in executive
    assert "neither relationship transfers project-direction authority" in candidate
    assert "scoped technology-placement" in tower
    assert "casey barton retains project-direction authority" in tower


def test_portfolio_root_documentation_is_non_governing() -> None:
    text = (ROOT / "docs/PORTFOLIO_ROOT_TRUTH.md").read_text(encoding="utf-8").lower()

    assert "one governed source" not in text
    assert "canonical portfolio control plane" not in text
    assert "two inventory planes, one authority" not in text
    assert "portfolio evidence root" in text
    assert "casey barton" in text
    assert "no project-direction authority" in text


def test_legacy_wire_name_is_explicitly_non_authoritative() -> None:
    index = load_json("manifests/readme_mesh.json")
    assert index["projection_semantics"] == "LEGACY_PUBLIC_EVIDENCE_ONLY"
    assert index["project_direction_authority"] is False

    readme_mesh_source = (ROOT / "src/job_app_helix/readme_mesh.py").read_text(
        encoding="utf-8"
    )
    assert "retired GOVERNED_BY" in readme_mesh_source
    assert "LEGACY_NON_AUTHORITATIVE_RELATIONS" in readme_mesh_source
