from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

IMPLEMENTATION_PROOF_SCHEMA = "glaciereq.implementation-proof.v1"

# These are intentionally strong markers: each one is an explicit assertion that
# the leaf is still a scaffold, not a heuristic based on file size or naming.
SCAFFOLD_MARKERS: tuple[tuple[str, str], ...] = (
    ("README.md", "This leaf is a **scaffold**"),
    ("README.md", "## Current scaffold state"),
    ("DEV_UP_INSTRUCTIONS.md", "Replace the stub mechanism"),
    ("DEV_UP_INSTRUCTIONS.md", "Implementation is the next agent's job"),
    ("DEV_UP_INSTRUCTIONS.md", "Implementation is the next agent\u2019s job"),
)
SOURCE_MARKERS = ("SCAFFOLD STUB", "scaffold_allow")
TEST_MARKERS = ("Behavioral scaffold tests", 'metrics.get("scaffold") is True')


@dataclass(frozen=True)
class PromotionAssessment:
    eligible: bool
    reasons: tuple[str, ...]
    scaffold_evidence: tuple[str, ...]
    implementation_proof_valid: bool
    source_sha: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "scaffold_evidence": list(self.scaffold_evidence),
            "implementation_proof_valid": self.implementation_proof_valid,
            "source_sha": self.source_sha,
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree_sha(leaf: Path) -> str:
    """Hash implementation-bearing files using the estate elevator convention."""
    parts: list[str] = []
    for sub in ("src", "scripts", "tests"):
        root = leaf / sub
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix in {".py", ".md", ".json"}:
                relative = path.relative_to(leaf).as_posix()
                parts.append(f"{relative}:{_sha256(path)}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        return needle in path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False


def detect_scaffold_evidence(leaf: Path) -> tuple[str, ...]:
    evidence: list[str] = []
    for rel, marker in SCAFFOLD_MARKERS:
        path = leaf / rel
        if _contains(path, marker):
            evidence.append(f"{rel}:{marker}")

    src = leaf / "src"
    if src.is_dir():
        for path in sorted(src.rglob("*.py")):
            for marker in SOURCE_MARKERS:
                if _contains(path, marker):
                    evidence.append(f"{path.relative_to(leaf).as_posix()}:{marker}")

    tests = leaf / "tests"
    if tests.is_dir():
        for path in sorted(tests.rglob("*.py")):
            for marker in TEST_MARKERS:
                if _contains(path, marker):
                    evidence.append(f"{path.relative_to(leaf).as_posix()}:{marker}")
    return tuple(dict.fromkeys(evidence))


def validate_implementation_proof(
    proof: Mapping[str, Any] | None,
    *,
    repository: str,
    expected_source_sha: str,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not isinstance(proof, Mapping):
        return False, ("IMPLEMENTATION_PROOF_MISSING",)
    if proof.get("schema") != IMPLEMENTATION_PROOF_SCHEMA:
        reasons.append("IMPLEMENTATION_PROOF_SCHEMA")
    if proof.get("repository") != repository:
        reasons.append("IMPLEMENTATION_PROOF_REPOSITORY")
    if proof.get("source_sha") != expected_source_sha:
        reasons.append("IMPLEMENTATION_PROOF_SOURCE_SHA")
    if proof.get("result") != "PASS":
        reasons.append("IMPLEMENTATION_PROOF_RESULT")
    if proof.get("scaffold") is not False:
        reasons.append("IMPLEMENTATION_PROOF_SCAFFOLD")

    behavioral = proof.get("behavioral_cases")
    adversarial = proof.get("adversarial_cases")
    invalid_behavioral = (
        not isinstance(behavioral, int) or isinstance(behavioral, bool) or behavioral < 3
    )
    if invalid_behavioral:
        reasons.append("IMPLEMENTATION_PROOF_BEHAVIORAL_CASES")
    invalid_adversarial = (
        not isinstance(adversarial, int) or isinstance(adversarial, bool) or adversarial < 1
    )
    if invalid_adversarial:
        reasons.append("IMPLEMENTATION_PROOF_ADVERSARIAL_CASES")

    return not reasons, tuple(reasons)


def assess_leaf_promotion(
    leaf: Path,
    repository: str | None = None,
) -> PromotionAssessment:
    repository = repository or f"GlacierEQ/{leaf.name}"
    source_sha = source_tree_sha(leaf)
    scaffold = detect_scaffold_evidence(leaf)
    reasons: list[str] = []
    if scaffold:
        reasons.append("SCAFFOLD_EVIDENCE_PRESENT")

    proof_path = leaf / "machine" / "implementation-proof.json"
    proof: Mapping[str, Any] | None = None
    if proof_path.is_file():
        try:
            loaded = json.loads(proof_path.read_text(encoding="utf-8"))
            proof = loaded if isinstance(loaded, Mapping) else None
        except (OSError, json.JSONDecodeError):
            reasons.append("IMPLEMENTATION_PROOF_INVALID_JSON")

    proof_ok, proof_reasons = validate_implementation_proof(
        proof,
        repository=repository,
        expected_source_sha=source_sha,
    )
    reasons.extend(proof_reasons)

    state_path = leaf / "machine" / "excellence-state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if scaffold and state.get("scaffold") is False:
                reasons.append("STATE_SCAFFOLD_CONTRADICTION")
            promoted_without_proof = state.get("principal_state") == "PROMOTED" and (
                scaffold or not proof_ok
            )
            if promoted_without_proof:
                reasons.append("PROMOTED_WITHOUT_IMPLEMENTATION_PROOF")
        except (OSError, json.JSONDecodeError):
            reasons.append("EXCELLENCE_STATE_INVALID_JSON")

    reasons = list(dict.fromkeys(reasons))
    return PromotionAssessment(
        eligible=not scaffold and proof_ok and not reasons,
        reasons=tuple(reasons),
        scaffold_evidence=scaffold,
        implementation_proof_valid=proof_ok,
        source_sha=source_sha,
    )


def enforce_nonpromoted_state(
    state: dict[str, Any],
    assessment: PromotionAssessment,
) -> dict[str, Any]:
    """Return a truth-preserving state when promotion eligibility is not earned.

    OPERABLE remains the principal-state ceiling for an executable scaffold in the
    existing state topology; Wave phase records the more precise SCAFFOLD_PROVEN label.
    """
    out = dict(state)
    if assessment.eligible:
        return out

    if out.get("principal_state") in {"PROMOTED", "SOURCE_BOUND", "EVOLVING"}:
        out["principal_state"] = "OPERABLE"
    out["scaffold"] = bool(assessment.scaffold_evidence)
    out["promotion_eligible"] = False
    out["promotion_blockers"] = list(assessment.reasons)
    wave = dict(out.get("wave") or {})
    if wave:
        phase = (
            "SCAFFOLD_PROVEN"
            if assessment.scaffold_evidence
            else "IMPLEMENTATION_PROOF_PENDING"
        )
        wave["phase"] = phase
        wave.pop("promoted_at", None)
        wave.pop("projection_truth_closed_at", None)
        out["wave"] = wave
    return out
