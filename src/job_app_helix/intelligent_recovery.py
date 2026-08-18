"""Intelligent multi-engine recovery planning and bounded execution.

This module composes the lower-level exact-source archaeology and restoration
machinery into a higher-order recovery brain. The design goal is simple:
recover lost capability aggressively while preserving stronger later work.

The engine separates five concerns:

1. lineage evidence: what exact donor/target revisions differ;
2. capability value: which displaced artifacts are worth recovering first;
3. dependency awareness: whether a missing Python artifact can stand alone;
4. preservation risk: whether recovery can overwrite later capability;
5. execution routing: file restore, semantic closure, or composition review.

Only high-confidence, target-absent source/test artifacts are eligible for
automatic file restoration. Modified target files are never overwritten by
this engine; they are routed to the surgical symbol/semantic machinery.
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .capability_archaeology import (
    ArchaeologyReport,
    CapabilityCandidate,
    excavate,
    read_donor_blob,
    resolve_commit,
)
from .restoration_executor import (
    ApplyReceipt,
    RestorationPacket,
    apply_packet,
    build_packet,
    rollback,
)

RecoveryMode = Literal[
    "RESTORE_FILE",
    "SEMANTIC_CLOSURE",
    "SYMBOL_COMPOSITION",
    "MANUAL_COMPOSITION",
    "EVIDENCE_ONLY",
]
ArtifactRole = Literal["SOURCE", "TEST", "WORKFLOW", "CONFIG", "DATA", "DOC", "OTHER"]


class IntelligentRecoveryError(RuntimeError):
    """Raised when intelligent recovery cannot preserve its invariants."""


@dataclass(frozen=True)
class DependencyProbe:
    local_imports: tuple[str, ...]
    unresolved_local_imports: tuple[str, ...]
    syntax_valid: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IntelligentRecoveryCandidate:
    candidate_id: str
    path: str
    donor_sha: str
    target_sha: str
    donor_blob_sha256: str
    target_blob_sha256: str | None
    status: str
    role: ArtifactRole
    mode: RecoveryMode
    recovery_score: float
    capability_value: float
    preservation_risk: float
    confidence: float
    auto_recoverable: bool
    public_symbol_count: int
    dependency_probe: DependencyProbe
    donor_aliases: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["dependency_probe"] = self.dependency_probe.to_dict()
        return payload


@dataclass(frozen=True)
class IntelligentRecoveryPlan:
    repository: str
    target_sha: str
    donor_shas: tuple[str, ...]
    candidates: tuple[IntelligentRecoveryCandidate, ...]
    auto_batch_ids: tuple[str, ...]
    review_ids: tuple[str, ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "glaciereq.intelligent-recovery-plan.v1",
            "repository": self.repository,
            "target_sha": self.target_sha,
            "donor_shas": list(self.donor_shas),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "auto_batch_ids": list(self.auto_batch_ids),
            "review_ids": list(self.review_ids),
            "receipt_sha256": self.receipt_sha256,
        }


@dataclass(frozen=True)
class IntelligentRecoveryExecutionReceipt:
    plan_sha256: str
    target_sha: str
    restored_candidate_ids: tuple[str, ...]
    restored_paths: tuple[str, ...]
    packet_receipts: tuple[dict[str, object], ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_SOURCE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java",
    ".kt", ".kts", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs",
    ".rb", ".php", ".sh",
}
_CONFIG_NAMES = {
    "pyproject.toml", "package.json", "package-lock.json", "pnpm-lock.yaml",
    "yarn.lock", "cargo.toml", "cargo.lock", "go.mod", "go.sum", "dockerfile",
    "compose.yaml", "docker-compose.yml",
}
_DOC_SUFFIXES = {".md", ".rst", ".adoc", ".txt"}
_DATA_SUFFIXES = {".json", ".jsonl", ".yaml", ".yml", ".toml", ".csv", ".sql"}


def _artifact_role(path: str) -> ArtifactRole:
    normalized = path.lower()
    name = Path(normalized).name
    suffix = Path(normalized).suffix
    parts = set(Path(normalized).parts)
    if ".github" in parts or "workflows" in parts:
        return "WORKFLOW"
    if "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "TEST"
    if suffix in _SOURCE_SUFFIXES or "src" in parts:
        return "SOURCE"
    if name in _CONFIG_NAMES or normalized.startswith("config/"):
        return "CONFIG"
    if suffix in _DOC_SUFFIXES or "docs" in parts:
        return "DOC"
    if suffix in _DATA_SUFFIXES or "manifests" in parts:
        return "DATA"
    return "OTHER"


def _public_symbol_count(blob: bytes, path: str) -> tuple[int, bool]:
    if not path.endswith(".py"):
        return 0, True
    try:
        tree = ast.parse(blob.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError):
        return 0, False
    count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                count += 1
    return count, True


def _module_candidates_for_relative_import(path: str, node: ast.ImportFrom) -> tuple[str, ...]:
    current = Path(path)
    package_parts = list(current.parent.parts)
    if node.level:
        climb = max(0, node.level - 1)
        if climb > len(package_parts):
            return ()
        package_parts = package_parts[: len(package_parts) - climb]
    module_parts = node.module.split(".") if node.module else []
    base_parts = [*package_parts, *module_parts]
    if not base_parts:
        return ()
    base = Path(*base_parts)
    return (f"{base}.py", str(base / "__init__.py"))


def _absolute_local_candidates(module: str) -> tuple[str, ...]:
    parts = module.split(".")
    if not parts:
        return ()
    base = Path(*parts)
    return (
        f"{base}.py",
        str(base / "__init__.py"),
        str(Path("src") / f"{base}.py"),
        str(Path("src") / base / "__init__.py"),
    )


def _dependency_probe(repo: Path, path: str, donor_blob: bytes) -> DependencyProbe:
    if not path.endswith(".py"):
        return DependencyProbe((), (), True)
    try:
        tree = ast.parse(donor_blob.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError):
        return DependencyProbe((), (), False)

    local_imports: list[str] = []
    unresolved: list[str] = []
    for node in ast.walk(tree):
        candidates: tuple[str, ...] = ()
        label = ""
        if isinstance(node, ast.ImportFrom):
            label = "." * node.level + (node.module or "")
            if node.level:
                candidates = _module_candidates_for_relative_import(path, node)
            elif node.module:
                root = node.module.split(".", 1)[0]
                package_root = Path(path).parts
                if root in package_root or root == "job_app_helix":
                    candidates = _absolute_local_candidates(node.module)
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names if alias.name.startswith("job_app_helix.")]
            if names:
                label = ",".join(names)
                candidate_paths: list[str] = []
                for name in names:
                    candidate_paths.extend(_absolute_local_candidates(name))
                candidates = tuple(candidate_paths)
        if not candidates:
            continue
        local_imports.append(label)
        if not any((repo / candidate).exists() for candidate in candidates):
            unresolved.append(label)

    return DependencyProbe(
        local_imports=tuple(sorted(set(local_imports))),
        unresolved_local_imports=tuple(sorted(set(unresolved))),
        syntax_valid=True,
    )


def _candidate_id(path: str, blob_sha256: str) -> str:
    digest = hashlib.sha256(f"{path}\0{blob_sha256}".encode()).hexdigest()[:16]
    return f"recovery-{digest}"


def _mode_for(candidate: CapabilityCandidate, role: ArtifactRole, probe: DependencyProbe) -> RecoveryMode:
    if candidate.target_blob_sha256 is None:
        if role in {"SOURCE", "TEST"} and probe.unresolved_local_imports:
            return "SEMANTIC_CLOSURE"
        return "RESTORE_FILE"
    if candidate.path.endswith(".py"):
        return "SYMBOL_COMPOSITION"
    if role in {"SOURCE", "TEST", "CONFIG", "WORKFLOW", "DATA"}:
        return "MANUAL_COMPOSITION"
    return "EVIDENCE_ONLY"


def _preservation_risk(candidate: CapabilityCandidate, role: ArtifactRole, probe: DependencyProbe) -> float:
    risk = 0.05
    if candidate.target_blob_sha256 is not None:
        risk += 0.58
    if role in {"WORKFLOW", "CONFIG"}:
        risk += 0.18
    if probe.unresolved_local_imports:
        risk += min(0.20, 0.05 * len(probe.unresolved_local_imports))
    if not probe.syntax_valid:
        risk += 0.30
    return round(min(1.0, risk), 6)


def _capability_value(
    candidate: CapabilityCandidate,
    role: ArtifactRole,
    public_symbol_count: int,
    duplicate_count: int,
) -> float:
    role_bonus = {
        "SOURCE": 0.24,
        "TEST": 0.20,
        "WORKFLOW": 0.12,
        "CONFIG": 0.10,
        "DATA": 0.09,
        "DOC": 0.06,
        "OTHER": 0.04,
    }[role]
    deletion_bonus = 0.16 if candidate.target_blob_sha256 is None else 0.0
    symbol_bonus = min(0.14, public_symbol_count * 0.02)
    uniqueness_bonus = 0.10 / max(1, duplicate_count)
    size_bonus = min(0.08, candidate.donor_size / 100_000)
    score = 0.46 * candidate.recovery_score + role_bonus + deletion_bonus
    score += symbol_bonus + uniqueness_bonus + size_bonus
    return round(min(1.0, score), 6)


def _confidence(
    candidate: CapabilityCandidate,
    role: ArtifactRole,
    probe: DependencyProbe,
    donor_aliases: Sequence[str],
) -> float:
    confidence = 0.62 + 0.22 * candidate.recovery_score
    if candidate.target_blob_sha256 is None:
        confidence += 0.08
    if role in {"SOURCE", "TEST"}:
        confidence += 0.04
    if len(donor_aliases) > 1:
        confidence += min(0.06, 0.02 * (len(donor_aliases) - 1))
    if probe.unresolved_local_imports:
        confidence -= min(0.18, 0.04 * len(probe.unresolved_local_imports))
    if not probe.syntax_valid:
        confidence -= 0.30
    return round(max(0.0, min(1.0, confidence)), 6)


def _is_auto_recoverable(
    candidate: CapabilityCandidate,
    role: ArtifactRole,
    mode: RecoveryMode,
    risk: float,
    confidence: float,
    probe: DependencyProbe,
) -> bool:
    return (
        candidate.target_blob_sha256 is None
        and candidate.status == "D"
        and role in {"SOURCE", "TEST"}
        and mode == "RESTORE_FILE"
        and risk <= 0.15
        and confidence >= 0.82
        and probe.syntax_valid
        and not probe.unresolved_local_imports
    )


def _reasons(
    candidate: CapabilityCandidate,
    role: ArtifactRole,
    mode: RecoveryMode,
    probe: DependencyProbe,
    risk: float,
    auto_recoverable: bool,
) -> tuple[str, ...]:
    reasons = [candidate.reason, f"artifact role={role}", f"route={mode}"]
    if candidate.target_blob_sha256 is None:
        reasons.append("target is absent; no later file bytes would be overwritten")
    else:
        reasons.append("target exists; later capability must be composed, not replaced")
    if probe.unresolved_local_imports:
        reasons.append(
            "unresolved local imports require dependency closure: "
            + ", ".join(probe.unresolved_local_imports)
        )
    if not probe.syntax_valid:
        reasons.append("donor Python syntax could not be validated")
    if role in {"WORKFLOW", "CONFIG"}:
        reasons.append("control-surface artifact requires explicit composition review")
    if risk >= 0.5:
        reasons.append("preservation risk is high")
    if auto_recoverable:
        reasons.append("eligible for bounded automatic restore")
    return tuple(reasons)


def _dedupe_reports(
    reports: Sequence[ArchaeologyReport],
) -> dict[tuple[str, str], tuple[CapabilityCandidate, tuple[str, ...]]]:
    grouped: dict[tuple[str, str], list[CapabilityCandidate]] = defaultdict(list)
    for report in reports:
        for candidate in report.candidates:
            grouped[(candidate.path, candidate.donor_blob_sha256)].append(candidate)

    deduped: dict[tuple[str, str], tuple[CapabilityCandidate, tuple[str, ...]]] = {}
    for key, candidates in grouped.items():
        chosen = max(
            candidates,
            key=lambda item: (
                item.recovery_score,
                item.target_blob_sha256 is None,
                item.donor_sha,
            ),
        )
        aliases = tuple(sorted({item.donor_sha for item in candidates}))
        deduped[key] = (chosen, aliases)
    return deduped


def build_intelligent_recovery_plan(
    repo: Path,
    *,
    donor_refs: Sequence[str],
    target_ref: str = "HEAD",
    include_paths: tuple[str, ...] = (),
    max_auto_actions: int = 8,
) -> IntelligentRecoveryPlan:
    """Build a deterministic cross-donor recovery plan."""
    if not donor_refs:
        raise IntelligentRecoveryError("at least one donor ref is required")
    if max_auto_actions <= 0:
        raise IntelligentRecoveryError("max_auto_actions must be positive")

    repo = repo.resolve()
    reports = [
        excavate(repo, donor_ref=donor_ref, target_ref=target_ref, include_paths=include_paths)
        for donor_ref in donor_refs
    ]
    target_shas = {report.target_sha for report in reports}
    if len(target_shas) != 1:
        raise IntelligentRecoveryError("all donor archaeology must bind to one target revision")
    target_sha = next(iter(target_shas))
    repository = reports[0].repository
    deduped = _dedupe_reports(reports)
    duplicate_counts = {
        key: sum(
            1
            for report in reports
            for row in report.candidates
            if (row.path, row.donor_blob_sha256) == key
        )
        for key in deduped
    }

    intelligent: list[IntelligentRecoveryCandidate] = []
    for key, (candidate, donor_aliases) in deduped.items():
        donor_blob = read_donor_blob(repo, donor_sha=candidate.donor_sha, path=candidate.path)
        role = _artifact_role(candidate.path)
        public_symbols, syntax_valid = _public_symbol_count(donor_blob, candidate.path)
        probe = _dependency_probe(repo, candidate.path, donor_blob)
        if not syntax_valid:
            probe = DependencyProbe(
                local_imports=probe.local_imports,
                unresolved_local_imports=probe.unresolved_local_imports,
                syntax_valid=False,
            )
        mode = _mode_for(candidate, role, probe)
        risk = _preservation_risk(candidate, role, probe)
        value = _capability_value(candidate, role, public_symbols, duplicate_counts[key])
        confidence = _confidence(candidate, role, probe, donor_aliases)
        auto = _is_auto_recoverable(candidate, role, mode, risk, confidence, probe)
        intelligent.append(
            IntelligentRecoveryCandidate(
                candidate_id=_candidate_id(candidate.path, candidate.donor_blob_sha256),
                path=candidate.path,
                donor_sha=candidate.donor_sha,
                target_sha=candidate.target_sha,
                donor_blob_sha256=candidate.donor_blob_sha256,
                target_blob_sha256=candidate.target_blob_sha256,
                status=candidate.status,
                role=role,
                mode=mode,
                recovery_score=candidate.recovery_score,
                capability_value=value,
                preservation_risk=risk,
                confidence=confidence,
                auto_recoverable=auto,
                public_symbol_count=public_symbols,
                dependency_probe=probe,
                donor_aliases=donor_aliases,
                reasons=_reasons(candidate, role, mode, probe, risk, auto),
            )
        )

    intelligent.sort(
        key=lambda item: (
            not item.auto_recoverable,
            -item.capability_value,
            item.preservation_risk,
            -item.confidence,
            item.path,
        )
    )
    auto_ids = tuple(item.candidate_id for item in intelligent if item.auto_recoverable)
    auto_ids = auto_ids[:max_auto_actions]
    auto_id_set = set(auto_ids)
    review_ids = tuple(item.candidate_id for item in intelligent if item.candidate_id not in auto_id_set)
    payload = {
        "schema": "glaciereq.intelligent-recovery-plan.v1",
        "repository": repository,
        "target_sha": target_sha,
        "donor_shas": sorted({report.donor_sha for report in reports}),
        "candidates": [item.to_dict() for item in intelligent],
        "auto_batch_ids": list(auto_ids),
        "review_ids": list(review_ids),
    }
    receipt = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return IntelligentRecoveryPlan(
        repository=repository,
        target_sha=target_sha,
        donor_shas=tuple(payload["donor_shas"]),
        candidates=tuple(intelligent),
        auto_batch_ids=auto_ids,
        review_ids=review_ids,
        receipt_sha256=receipt,
    )


def _candidate_by_id(
    plan: IntelligentRecoveryPlan, selected_ids: Sequence[str]
) -> tuple[IntelligentRecoveryCandidate, ...]:
    by_id = {candidate.candidate_id: candidate for candidate in plan.candidates}
    unknown = sorted(set(selected_ids) - set(by_id))
    if unknown:
        raise IntelligentRecoveryError(f"unknown recovery candidate ids: {unknown}")
    return tuple(by_id[candidate_id] for candidate_id in selected_ids)


def build_automatic_packets(
    repo: Path,
    plan: IntelligentRecoveryPlan,
    *,
    selected_ids: Sequence[str] | None = None,
) -> tuple[RestorationPacket, ...]:
    """Build exact donor packets for auto-recoverable candidates only."""
    ids = tuple(selected_ids) if selected_ids is not None else plan.auto_batch_ids
    if not ids:
        raise IntelligentRecoveryError("no automatic recovery candidates selected")
    selected = _candidate_by_id(plan, ids)
    unsafe = [candidate.candidate_id for candidate in selected if not candidate.auto_recoverable]
    if unsafe:
        raise IntelligentRecoveryError(
            "automatic packet refused non-auto-recoverable candidates: " + ", ".join(unsafe)
        )

    repo = repo.resolve()
    observed_target = resolve_commit(repo, "HEAD")
    if observed_target != plan.target_sha:
        raise IntelligentRecoveryError(
            f"target HEAD drifted: expected {plan.target_sha}, observed {observed_target}"
        )

    grouped: dict[str, list[IntelligentRecoveryCandidate]] = defaultdict(list)
    for candidate in selected:
        grouped[candidate.donor_sha].append(candidate)

    packets: list[RestorationPacket] = []
    for donor_sha, rows in sorted(grouped.items()):
        archaeology = excavate(repo, donor_ref=donor_sha, target_ref=plan.target_sha)
        exact_paths = tuple(sorted(candidate.path for candidate in rows))
        packets.append(
            build_packet(
                archaeology.candidates,
                selected_paths=exact_paths,
                allow_replace=False,
            )
        )
    return tuple(packets)


def execute_automatic_recovery(
    repo: Path,
    plan: IntelligentRecoveryPlan,
    *,
    selected_ids: Sequence[str] | None = None,
) -> IntelligentRecoveryExecutionReceipt:
    """Apply a bounded, transactional set of safe recovery packets."""
    packets = build_automatic_packets(repo, plan, selected_ids=selected_ids)
    applied: list[ApplyReceipt] = []
    try:
        for packet in packets:
            applied.append(apply_packet(repo, packet))
    except Exception:
        for receipt in reversed(applied):
            rollback(repo, receipt)
        raise

    restored_paths = tuple(sorted(path for receipt in applied for path in receipt.restored_paths))
    selected = tuple(selected_ids) if selected_ids is not None else plan.auto_batch_ids
    packet_receipts = tuple(receipt.to_dict() for receipt in applied)
    payload = {
        "plan_sha256": plan.receipt_sha256,
        "target_sha": plan.target_sha,
        "restored_candidate_ids": list(selected),
        "restored_paths": list(restored_paths),
        "packet_receipts": list(packet_receipts),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return IntelligentRecoveryExecutionReceipt(
        plan_sha256=plan.receipt_sha256,
        target_sha=plan.target_sha,
        restored_candidate_ids=selected,
        restored_paths=restored_paths,
        packet_receipts=packet_receipts,
        receipt_sha256=digest,
    )


def summarize_recovery_plan(plan: IntelligentRecoveryPlan) -> dict[str, object]:
    """Return a compact decision surface for humans and higher-level agents."""
    mode_counts: dict[str, int] = defaultdict(int)
    role_counts: dict[str, int] = defaultdict(int)
    for candidate in plan.candidates:
        mode_counts[candidate.mode] += 1
        role_counts[candidate.role] += 1
    return {
        "schema": "glaciereq.intelligent-recovery-summary.v1",
        "repository": plan.repository,
        "target_sha": plan.target_sha,
        "donor_count": len(plan.donor_shas),
        "candidate_count": len(plan.candidates),
        "auto_recoverable_count": len(plan.auto_batch_ids),
        "review_count": len(plan.review_ids),
        "mode_counts": dict(sorted(mode_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "top_candidates": [
            {
                "candidate_id": candidate.candidate_id,
                "path": candidate.path,
                "mode": candidate.mode,
                "capability_value": candidate.capability_value,
                "preservation_risk": candidate.preservation_risk,
                "confidence": candidate.confidence,
                "auto_recoverable": candidate.auto_recoverable,
            }
            for candidate in plan.candidates[:10]
        ],
        "receipt_sha256": plan.receipt_sha256,
    }
