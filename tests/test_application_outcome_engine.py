from __future__ import annotations

import json
from pathlib import Path

from job_app_helix import cli
from job_app_helix.application_engine import (
    build_application_kit,
    find_target,
    load_targets,
    render_markdown,
    write_application_kit,
)

ROOT = Path(__file__).resolve().parents[1]


def targets():
    return load_targets(ROOT / "manifests")


def test_anthropic_application_kit_uses_admitted_public_proof() -> None:
    target = find_target("anthropic", targets())
    kit = build_application_kit(target, "Safety Systems Engineer")

    assert kit.company == "Anthropic"
    assert kit.role == "Safety Systems Engineer"
    assert kit.readiness == "READY_WITH_PUBLIC_PROOF"
    repositories = {
        row["repository"]
        for row in kit.proof_repositories
    }
    assert "GlacierEQ/anthropic-agent-coordinator" in repositories
    assert "GlacierEQ/anthropic-safety-monitor" in repositories
    assert all(
        row["state"] in {"PROMOTED", "REFERENCE_ONLY"}
        for row in kit.proof_repositories
    )
    assert "no Anthropic affiliation" in kit.non_affiliation


def test_blocked_and_experimental_repos_are_not_recruiter_proof() -> None:
    target = find_target("xai", targets())
    kit = build_application_kit(target)
    repositories = {
        row["repository"]
        for row in kit.proof_repositories
    }

    assert "GlacierEQ/xai-colossus-cooling" not in repositories
    assert "GlacierEQ/xai-colossus-cooling-alpha" not in repositories
    assert "GlacierEQ/xai-colossus-energy" in repositories


def test_unknown_role_is_rejected() -> None:
    target = find_target("anthropic", targets())
    try:
        build_application_kit(target, "Chief Astronaut")
    except ValueError as exc:
        assert "not a mapped target role" in str(exc)
    else:
        raise AssertionError("unmapped role must be rejected")


def test_application_kit_writes_real_json_and_markdown(tmp_path) -> None:
    kit = build_application_kit(find_target("anthropic", targets()))
    json_path, markdown_path = write_application_kit(kit, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["schema"] == "glaciereq.job-application-kit.v1"
    assert payload["readiness"] == "READY_WITH_PUBLIC_PROOF"
    assert "## Public technical proof" in markdown
    assert "anthropic-agent-coordinator" in markdown


def test_primary_cli_defaults_to_real_target_index(capsys) -> None:
    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert "anthropic" in output
    assert "READY_WITH_PUBLIC_PROOF" in output
    assert "Scenario:" not in output


def test_primary_cli_compiles_application_json(capsys) -> None:
    result = cli.main(
        [
            "application",
            "anthropic",
            "--role",
            "Safety Systems Engineer",
            "--json",
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["company_id"] == "anthropic"
    assert payload["role"] == "Safety Systems Engineer"
    assert payload["proof_repositories"]


def test_legacy_scenario_is_explicit_demo_compatibility(capsys) -> None:
    assert cli.main(["nominal", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scenario"] == "nominal"


def test_markdown_truth_boundary_is_present() -> None:
    kit = build_application_kit(find_target("anthropic", targets()))
    markdown = render_markdown(kit)
    assert "## Truth boundary" in markdown
    assert kit.non_affiliation in markdown
