from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_operations import CandidateProfile, JobOpening
from job_app_helix.dynamic_application_build import (
    derive_evidence_graph,
    execute_dynamic_build,
)


def _opening(company: str = "NewCo") -> JobOpening:
    return JobOpening(
        opening_id="job-123",
        company=company,
        title="Staff Agent Systems Engineer",
        description="Build agent orchestration, recovery, and distributed AI systems in Python.",
        location="Remote",
        source="fixture",
        source_url="https://example.test/jobs/123",
        requirements=(
            "agent orchestration",
            "distributed systems",
            "Python",
        ),
        preferred=("recovery systems",),
        metadata={},
        digest="a" * 64,
    )


def _profile() -> CandidateProfile:
    return CandidateProfile(
        profile_id="candidate-1",
        name="Casey Example",
        headline="AI systems engineer",
        summary="Builds agent systems and resilient infrastructure.",
        skills=("Python", "distributed systems", "agent orchestration"),
        experience=("Built resilient orchestration systems.",),
        achievements=("Shipped evidence-backed AI infrastructure.",),
        contact={},
        source_digest="b" * 64,
    )


def _estate() -> dict[str, object]:
    return {
        "system_registry": {
            "systems": [
                {
                    "system_id": "agent-core",
                    "source_repository": "GlacierEQ/agent-core",
                    "flagship_level": "L5",
                    "flagship_state": "PROMOTED",
                    "visibility": "public",
                    "role": "Agent orchestration and distributed recovery",
                    "evidence": "Exact-head tests prove orchestration and recovery.",
                },
                {
                    "system_id": "private-lab",
                    "source_repository": "GlacierEQ/private-lab",
                    "flagship_level": "L4",
                    "flagship_state": "PROMOTED",
                    "visibility": "private",
                    "role": "Distributed systems research",
                    "evidence": "Internal implementation evidence.",
                },
                {
                    "system_id": "unrelated",
                    "source_repository": "GlacierEQ/unrelated",
                    "flagship_level": "L3",
                    "flagship_state": "PROMOTED",
                    "visibility": "public",
                    "role": "Document rendering",
                    "evidence": "PDF rendering.",
                },
            ]
        },
        "capability_donor_registry": {
            "capabilities": [
                {
                    "capability_id": "reasoning-and-agent-systems",
                    "donor_systems": ["agent-core"],
                    "proof_refs": [{"system_id": "agent-core", "evidence": "tests"}],
                    "verification_state": "EVIDENCE_BOUND",
                },
                {
                    "capability_id": "distributed-state-and-recovery",
                    "donor_systems": ["agent-core", "private-lab"],
                    "proof_refs": [{"system_id": "agent-core", "evidence": "tests"}],
                    "verification_state": "EVIDENCE_BOUND",
                },
            ]
        },
        "company_projection_registry": {
            "projections": [],
        },
    }


def test_unknown_company_builds_from_full_estate_without_static_manifest() -> None:
    evidence = derive_evidence_graph(_opening("NeverPredeclaredCo"), _estate())

    assert evidence
    assert evidence[0].repository == "GlacierEQ/agent-core"
    assert any(row.repository == "GlacierEQ/private-lab" for row in evidence)
    assert all(row.repository != "GlacierEQ/unrelated" for row in evidence)


def test_private_donor_can_help_engineering_but_cannot_be_public_proof() -> None:
    evidence = derive_evidence_graph(_opening(), _estate())
    private = next(row for row in evidence if row.repository == "GlacierEQ/private-lab")
    public = next(row for row in evidence if row.repository == "GlacierEQ/agent-core")

    assert private.public_proof is False
    assert public.public_proof is True


def test_company_projection_is_bonus_not_prerequisite() -> None:
    estate = _estate()
    estate["company_projection_registry"] = {
        "projections": [
            {
                "company_id": "newco",
                "display_name": "NewCo",
                "ranked_evidence": [
                    {
                        "system_id": "agent-core",
                        "promotion_state": "PROMOTED",
                        "visibility": "public",
                        "visibility_decision": "PUBLIC_ELIGIBLE",
                        "capability_ids": [
                            "reasoning-and-agent-systems",
                            "distributed-state-and-recovery",
                        ],
                    }
                ],
            }
        ]
    }

    evidence = derive_evidence_graph(_opening(), estate)

    assert evidence[0].source == "COMPANY_PROJECTION_RUNTIME_MATCH"
    assert evidence[0].score > 0.25


def test_dynamic_build_materializes_real_application_artifacts(tmp_path: Path) -> None:
    result = execute_dynamic_build(
        _opening(),
        _profile(),
        _estate(),
        output_dir=tmp_path,
        run_genius=False,
    )

    assert result.application_id is not None
    assert "GlacierEQ/agent-core" in result.public_proof_repositories
    assert "GlacierEQ/private-lab" in result.engineering_donor_repositories

    build_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(build_dirs) == 1
    build_dir = build_dirs[0]

    assert (build_dir / "RESUME.md").is_file()
    assert (build_dir / "COVER_LETTER.md").is_file()
    assert (build_dir / "OUTREACH.md").is_file()
    assert (build_dir / "MATCH.json").is_file()
    assert (build_dir / "DYNAMIC_BUILD.json").is_file()

    receipt = json.loads((build_dir / "DYNAMIC_BUILD.json").read_text(encoding="utf-8"))
    assert receipt["company"] == "NewCo"
    assert receipt["role"] == "Staff Agent Systems Engineer"
    assert receipt["public_proof_repositories"] == ["GlacierEQ/agent-core"]
    assert any(
        row["action"] == "COMPOSE_ENGINEERING_DONOR"
        and row["repository"] == "GlacierEQ/private-lab"
        for row in receipt["build_actions"]
    )


def test_dynamic_build_preserves_uncovered_demand_for_new_engineering(tmp_path: Path) -> None:
    opening = JobOpening(
        opening_id="job-quantum",
        company="NewCo",
        title="Quantum Runtime Engineer",
        description="Build quantum error correction runtimes.",
        location="Remote",
        source="fixture",
        source_url=None,
        requirements=("quantum error correction",),
        preferred=(),
        metadata={},
        digest="c" * 64,
    )

    result = execute_dynamic_build(
        opening,
        _profile(),
        _estate(),
        output_dir=tmp_path,
        run_genius=False,
    )

    assert result.application_id is None
    assert {"quantum", "error", "correction"} <= set(result.uncovered_signals)
    assert any(row["action"] == "EVOLVE_OR_INVENT" for row in result.build_actions)
