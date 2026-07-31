from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hire_package" / "casey-barton"
EXPECTED_STAGES = [
    "OBSERVE",
    "RECOVER",
    "PLAN",
    "ROUTE",
    "ACT",
    "VERIFY",
    "PERSIST",
    "RESUME",
]
ALLOWED_RELATIONS = {
    "GOVERNED_BY",
    "ORCHESTRATES",
    "VERIFIES",
    "PROVIDES_CAPABILITY",
    "CONSUMES",
    "EXTENDS",
    "PERSISTS_RECEIPTS_TO",
    "EXECUTES_THROUGH",
}
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")


def _load(name: str) -> dict[str, object]:
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def _variant_key(role: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", role).strip("_")


def test_candidate_json_contracts_parse_and_use_timezone_aware_provenance() -> None:
    candidate = _load("candidate_node.json")
    ledger = _load("evidence_ledger.json")
    receipt = _load("coordinator_candidate_receipt.json")

    for value in (
        candidate["status"]["verified_at"],
        ledger["generated_at"],
        receipt["generated_at"],
    ):
        parsed = datetime.fromisoformat(str(value))
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() is not None


def test_spiral_sequence_is_canonical_across_human_and_machine_views() -> None:
    spiral = _load("application_spiral.json")
    stages = spiral["stages"]
    assert [stage["order"] for stage in stages] == list(range(1, 9))
    assert [stage["name"] for stage in stages] == EXPECTED_STAGES

    sequence = " -> ".join(EXPECTED_STAGES)
    for path in (PACKAGE / "README.md", PACKAGE / "TECHNICAL_PORTFOLIO_BRIEF.md"):
        assert sequence in path.read_text(encoding="utf-8")


def test_status_semantics_keep_blocked_and_unverified_scope_distinct() -> None:
    status = _load("candidate_node.json")["status"]
    assert status["blocked_scope"] == ["APEX GitHub App bridge activation"]
    assert "agent coordinator hosted multi-version promotion" in status["unverified_scope"]

    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    assert "APEX runner activation remains `BLOCKED`" in readme
    assert "coordinator hosted promotion remains `UNVERIFIED`" in readme


def test_primary_role_variants_are_routable() -> None:
    candidate = _load("candidate_node.json")
    mesh = _load("package_mesh.json")
    declared = {_variant_key(role) for role in candidate["primary_role_variants"]}
    routed = set(mesh["role_variants"])
    assert declared == routed
    assert set(candidate["adjacent_role_families"]).isdisjoint(
        set(candidate["primary_role_variants"])
    )


def test_relationships_use_compiled_enum_and_correct_direction() -> None:
    relationships = _load("candidate_node.json")["relationships"]
    assert relationships
    assert {item["relation"] for item in relationships} <= ALLOWED_RELATIONS

    coordinator = next(
        item
        for item in relationships
        if item["target"] == "GlacierEQ/anthropic-agent-coordinator"
    )
    assert coordinator["relation"] == "CONSUMES"
    assert "consumes" in coordinator["combined_value"].lower()


def test_precise_claims_have_immutable_or_local_receipts() -> None:
    ledger = _load("evidence_ledger.json")
    claims = {item["id"]: item for item in ledger["claims"]}

    akos = claims["akos_tests"]
    assert "/actions/runs/" in akos["evidence"]
    assert HEX_40.fullmatch(akos["source_commit"])
    assert HEX_40.fullmatch(akos["promotion_merge"])

    coordinator = claims["coordinator_tests"]
    receipt_path = PACKAGE / coordinator["evidence"]
    assert receipt_path.is_file()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["result"] == {
        "collected": 62,
        "executed": 62,
        "passed": 62,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "conclusion": "VERIFIED",
        "evidence_level": "TEST",
    }
    assert HEX_40.fullmatch(receipt["source_ref"])
    assert HEX_64.fullmatch(receipt["junit_sha256"])

    runner = claims["runner_activation"]
    assert "/actions/runs/" in runner["evidence"]
    assert HEX_40.fullmatch(runner["catalog_merge"])
    assert runner["activation_issue"].endswith("/issues/58")


def test_repository_mesh_paths_resolve_without_mixed_bases() -> None:
    mesh = _load("package_mesh.json")
    repository = mesh["contexts"]["repository_source"]
    assert repository["base"] == "hire_package/casey-barton"
    assert (PACKAGE / repository["entry"]).is_file()

    for paths in repository["audiences"].values():
        for relative in paths:
            assert not relative.startswith("hire_package/")
            assert (PACKAGE / relative).is_file()

    portable = mesh["contexts"]["portable_package"]
    assert portable["base"] == "package_root"
    for paths in portable["audiences"].values():
        assert all(not path.startswith("hire_package/") for path in paths)


def test_public_entry_point_links_candidate_surface() -> None:
    summary = (ROOT / "RECRUITER_EXECUTIVE_SUMMARY.md").read_text(encoding="utf-8")
    assert "hire_package/casey-barton/README.md" in summary


def test_public_source_contains_no_direct_contact_pii_or_unregistered_lint_count() -> None:
    resume = (PACKAGE / "EXECUTIVE_RESUME.md").read_text(encoding="utf-8")
    assert EMAIL.search(resume) is None
    assert PHONE.search(resume) is None
    assert "117" not in resume
    assert "Direct recruiter contact in the downloadable application package" in resume


def test_excluded_claims_do_not_leak_into_recruiter_or_expert_surfaces() -> None:
    excluded = set(_load("evidence_ledger.json")["excluded"])
    surfaces = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PACKAGE / "README.md",
            PACKAGE / "EXECUTIVE_RESUME.md",
            PACKAGE / "TECHNICAL_PORTFOLIO_BRIEF.md",
        )
    ).lower()
    for claim in excluded:
        assert claim.lower() not in surfaces
