from __future__ import annotations

import re

from job_app_helix.readme_estate import (
    START_MARKER,
    ClassificationEvidence,
    EstateReadmeError,
    ReadmeAction,
    append_missing_block,
    build_generated_contract,
    parse_machine_contract,
    plan_readme,
    render_machine_block,
)


def test_generated_contract_round_trip_and_identity() -> None:
    classification = ClassificationEvidence(
        primary_home="MIND_CAPABILITY.VERIFICATION.EXAMPLE_GATE",
        evidence_path="README.md",
        evidence_blob_sha="a" * 40,
        status="PLACED_SOURCE_BACKED",
    )
    contract = build_generated_contract(
        repository="GlacierEQ/example",
        default_branch="main",
        root_paths=["src", "tests", "pyproject.toml", "GENIUS.yaml"],
        classification=classification,
    )
    block = render_machine_block(contract)
    readme = f"# Example\n\n{block}\n"
    parsed = parse_machine_contract(readme, expected_repository="GlacierEQ/example")
    assert parsed is not None
    assert parsed["mesh"]["primary_home"] == classification.primary_home
    assert parsed["machine"]["repository_kind"] == "reusable-capability"
    assert {item["path"] for item in parsed["machine"]["entrypoints"]} == {
        "src",
        "tests",
        "pyproject.toml",
        "GENIUS.yaml",
    }
    assert re.fullmatch(r"[0-9a-f]{64}", parsed["provenance"]["contract_digest"])


def test_existing_valid_contract_is_adopted_without_rewrite() -> None:
    contract = build_generated_contract(
        repository="GlacierEQ/example",
        default_branch="main",
        root_paths=["src"],
    )
    original = f"# Human text\n\n{render_machine_block(contract)}\n\nKeep this exact prose.\n"
    plan = plan_readme(
        repository="GlacierEQ/example",
        current_readme=original,
        default_branch="main",
        root_paths=["src"],
    )
    assert plan.action == ReadmeAction.ADOPT
    assert plan.readme == original


def test_missing_block_is_appended_without_changing_human_prefix() -> None:
    original = "# Example\n\nHuman-authored explanation.\n"
    plan = plan_readme(
        repository="GlacierEQ/example",
        current_readme=original,
        default_branch="main",
        root_paths=["src", "tests"],
    )
    assert plan.action == ReadmeAction.INSERT_BLOCK
    assert plan.readme is not None
    assert plan.readme.startswith(original.rstrip())
    assert plan.readme.count(START_MARKER) == 1


def test_missing_readme_gets_minimal_noninflated_readme() -> None:
    plan = plan_readme(
        repository="GlacierEQ/no-readme",
        current_readme=None,
        default_branch="master",
        root_paths=["scripts"],
    )
    assert plan.action == ReadmeAction.CREATE_README
    assert plan.readme is not None
    assert plan.readme.startswith("# no-readme")
    assert "does not promote runtime or provider state" in plan.readme


def test_identity_mismatch_fails_into_repair_queue() -> None:
    wrong = build_generated_contract(
        repository="GlacierEQ/wrong",
        default_branch="main",
        root_paths=[],
    )
    readme = f"# Example\n\n{render_machine_block(wrong)}\n"
    plan = plan_readme(
        repository="GlacierEQ/example",
        current_readme=readme,
        default_branch="main",
        root_paths=[],
    )
    assert plan.action == ReadmeAction.REPAIR_REQUIRED
    assert "identity mismatch" in plan.reason


def test_archived_repo_is_represented_but_not_mutated() -> None:
    plan = plan_readme(
        repository="GlacierEQ/archive",
        current_readme="# Archive\n",
        default_branch="main",
        root_paths=["src"],
        archived=True,
    )
    assert plan.action == ReadmeAction.ARCHIVED_READ_ONLY
    assert plan.readme is None
    assert plan.contract is not None


def test_append_refuses_existing_marker_even_if_malformed() -> None:
    with __import__("pytest").raises(EstateReadmeError):
        append_missing_block("# X\n\n" + START_MARKER, "block")


def test_fork_is_not_promoted_to_original_capability_kind() -> None:
    contract = build_generated_contract(
        repository="GlacierEQ/fork",
        default_branch="main",
        root_paths=["src"],
        classification=ClassificationEvidence(
            primary_home="MIND_CAPABILITY.SOMETHING",
        ),
        fork=True,
    )
    assert contract["machine"]["repository_kind"] == "fork-or-derived-source"
