"""Compose estate recovery detection into exact-source semantic restoration.

This runtime bridges the repository-level recovery census to the existing ref-graph and
federated restoration engines. High-priority repositories are cloned read-only, their
branch families are ranked by exact ref-graph evidence, and the strongest Python-owned
mechanism is converted into a federated semantic packet for the target repository.
Application is opt-in; packet construction itself performs donor import and full semantic
closure validation, eliminating the former manual bridge between engines.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .estate_recovery_census import (
    EstateRecoveryCensus,
    build_estate_recovery_census,
    load_repository_names,
)
from .federated_restoration import (
    FederatedApplyReceipt,
    FederatedRestorationPacket,
    apply_federated_packet,
    build_federated_packet,
)
from .recovery_ref_graph import RecoveryRefGraphReport, RefFamily, build_ref_graph

ELIGIBLE_CLASSES = {
    "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER",
    "THIN_EXECUTABLE_SURFACE",
    "RECOVERY_IN_PROGRESS",
}


class EstateFederatedRecoveryError(RuntimeError):
    """Raised when automatic estate-to-semantic recovery cannot preserve its invariants."""


@dataclass(frozen=True)
class RepositoryRecoveryRoute:
    repository: str
    census_class: str
    census_priority: int
    donor_source: str
    selected_ref: str | None
    selected_sha: str | None
    selected_path: str | None
    selected_symbols: tuple[str, ...]
    ref_graph_receipt_sha256: str | None
    packet_sha256: str | None
    action: str
    blocker: str | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EstateFederatedRecoveryResult:
    schema: str
    target_sha: str
    census: EstateRecoveryCensus
    routes: tuple[RepositoryRecoveryRoute, ...]
    applied_receipts: tuple[FederatedApplyReceipt, ...]
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "target_sha": self.target_sha,
            "census": self.census.as_dict(),
            "routes": [row.as_dict() for row in self.routes],
            "applied_receipts": [row.to_dict() for row in self.applied_receipts],
            "receipt_sha256": self.receipt_sha256,
        }


def _run(command: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def _sha(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _clone_repository(owner: str, repository: str, destination: Path) -> None:
    proc = _run(
        (
            "git",
            "clone",
            "--quiet",
            f"https://github.com/{owner}/{repository}.git",
            str(destination),
        )
    )
    if proc.returncode:
        detail = (proc.stderr or proc.stdout or "clone failed").strip()[:300]
        raise EstateFederatedRecoveryError(f"unable to clone {owner}/{repository}: {detail}")


def _family_score(family: RefFamily) -> float:
    if family.reconnaissance is not None:
        return float(family.reconnaissance.priority_score)
    return family.preliminary_score


def _select_family(report: RecoveryRefGraphReport) -> RefFamily | None:
    candidates = [
        family
        for family in report.families
        if family.executable_path_count > 0 and _family_score(family) > 0
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            _family_score(row),
            row.executable_path_count,
            row.test_path_count,
            row.unique_commit_count,
            row.representative_ref,
        ),
    )


def _git_show(repo: Path, sha: str, path: str) -> str | None:
    proc = _run(("git", "show", f"{sha}:{path}"), cwd=repo)
    return proc.stdout if proc.returncode == 0 else None


def _python_symbols(source: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()
    symbols = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not node.name.startswith("_")
    ]
    return tuple(symbols)


def _select_python_mechanism(
    repo: Path,
    family: RefFamily,
) -> tuple[str, tuple[str, ...]] | None:
    proc = _run(
        (
            "git",
            "diff",
            "--name-only",
            "--diff-filter=AMRT",
            f"{family.representative_sha}^",
            family.representative_sha,
        ),
        cwd=repo,
    )
    recent_paths = [
        line.strip()
        for line in proc.stdout.splitlines()
        if line.strip().endswith(".py")
    ]
    if not recent_paths:
        proc = _run(
            ("git", "ls-tree", "-r", "--name-only", family.representative_sha),
            cwd=repo,
        )
        recent_paths = [
            line.strip()
            for line in proc.stdout.splitlines()
            if line.strip().endswith(".py")
        ]
    ranked = sorted(
        (
            path
            for path in recent_paths
            if "/tests/" not in f"/{path}"
            and not Path(path).name.startswith("test_")
        ),
        key=lambda path: ("/src/" not in f"/{path}", len(Path(path).parts), path),
    )
    for path in ranked:
        source = _git_show(repo, family.representative_sha, path)
        if source is None:
            continue
        symbols = _python_symbols(source)
        if symbols:
            return path, symbols
    return None


def execute_estate_federated_recovery(
    target_repo: Path,
    *,
    owner: str,
    repositories: Sequence[str],
    max_repositories: int = 5,
    min_priority: int = 60,
    apply: bool = False,
) -> EstateFederatedRecoveryResult:
    """Detect estate recovery candidates and automatically build semantic donor packets."""
    if max_repositories <= 0:
        raise ValueError("max_repositories must be positive")
    target_repo = target_repo.resolve()
    target_sha_proc = _run(("git", "rev-parse", "HEAD"), cwd=target_repo)
    if target_sha_proc.returncode:
        raise EstateFederatedRecoveryError("target repository HEAD is unavailable")
    target_sha = target_sha_proc.stdout.strip()

    census = build_estate_recovery_census(owner, repositories)
    selected = [
        row
        for row in census.observations
        if row.exists
        and not row.archived
        and not row.disabled
        and row.recovery_class in ELIGIBLE_CLASSES
        and row.priority_score >= min_priority
    ][:max_repositories]

    workspace = Path(tempfile.mkdtemp(prefix="helix-estate-recovery-"))
    routes: list[RepositoryRecoveryRoute] = []
    applied: list[FederatedApplyReceipt] = []
    try:
        for observation in selected:
            donor = workspace / observation.repository
            source = f"https://github.com/{owner}/{observation.repository}.git"
            try:
                _clone_repository(owner, observation.repository, donor)
                graph = build_ref_graph(donor, target_ref="HEAD")
                family = _select_family(graph)
                if family is None:
                    routes.append(
                        RepositoryRecoveryRoute(
                            observation.repository,
                            observation.recovery_class,
                            observation.priority_score,
                            source,
                            None,
                            None,
                            None,
                            (),
                            graph.receipt_sha256,
                            None,
                            "NO_DIVERGENT_EXECUTABLE_FAMILY",
                            "ref graph found no executable divergent family",
                        )
                    )
                    continue
                mechanism = _select_python_mechanism(donor, family)
                if mechanism is None:
                    routes.append(
                        RepositoryRecoveryRoute(
                            observation.repository,
                            observation.recovery_class,
                            observation.priority_score,
                            source,
                            family.representative_ref,
                            family.representative_sha,
                            None,
                            (),
                            graph.receipt_sha256,
                            None,
                            "NO_SEMANTIC_PYTHON_MECHANISM",
                            "selected family contains no importable public Python symbol",
                        )
                    )
                    continue
                root_path, symbols = mechanism
                packet: FederatedRestorationPacket = build_federated_packet(
                    target_repo,
                    donor_source=donor,
                    donor_ref=family.representative_sha,
                    target_ref=target_sha,
                    root_path=root_path,
                    selected_symbols=symbols,
                )
                action = "PACKET_READY"
                if apply:
                    receipt = apply_federated_packet(target_repo, packet)
                    applied.append(receipt)
                    action = "APPLIED"
                routes.append(
                    RepositoryRecoveryRoute(
                        observation.repository,
                        observation.recovery_class,
                        observation.priority_score,
                        source,
                        family.representative_ref,
                        family.representative_sha,
                        root_path,
                        symbols,
                        graph.receipt_sha256,
                        packet.packet_sha256,
                        action,
                        None,
                    )
                )
            except Exception as exc:
                routes.append(
                    RepositoryRecoveryRoute(
                        observation.repository,
                        observation.recovery_class,
                        observation.priority_score,
                        source,
                        None,
                        None,
                        None,
                        (),
                        None,
                        None,
                        "FAILED_ISOLATED",
                        str(exc)[:400],
                    )
                )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    base: dict[str, object] = {
        "schema": "glaciereq.estate-federated-recovery.v1",
        "target_sha": target_sha,
        "census": census.as_dict(),
        "routes": [row.as_dict() for row in routes],
        "applied_receipts": [row.to_dict() for row in applied],
    }
    return EstateFederatedRecoveryResult(
        schema="glaciereq.estate-federated-recovery.v1",
        target_sha=target_sha,
        census=census,
        routes=tuple(routes),
        applied_receipts=tuple(applied),
        receipt_sha256=_sha(base),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-estate-compose")
    parser.add_argument("--target-repo", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--owner", default="GlacierEQ")
    parser.add_argument("--max-repositories", type=int, default=5)
    parser.add_argument("--min-priority", type=int, default=60)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = execute_estate_federated_recovery(
        args.target_repo,
        owner=args.owner,
        repositories=load_repository_names(args.manifest),
        max_repositories=args.max_repositories,
        min_priority=args.min_priority,
        apply=args.apply,
    )
    rendered = json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if any(route.action == "FAILED_ISOLATED" for route in result.routes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
