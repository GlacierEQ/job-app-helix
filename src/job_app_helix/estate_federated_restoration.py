"""Turn estate recovery priority into exact-source federated restoration execution.

The census answers which repository needs attention. The ref graph answers which exact
historical branch family still carries unresolved executable capability. Federated
restoration answers how to compose that capability safely. This module joins all three
planes and can now derive executable restoration targets directly from live Git history,
without requiring a hand-authored donor/symbol manifest.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .estate_recovery_census import EstateRecoveryCensus, RepositoryRecoveryObservation
from .federated_restoration import (
    FederatedApplyReceipt,
    FederatedRestorationPacket,
    apply_federated_packet,
    build_federated_packet,
)
from .recovery_ref_graph import RecoveryRefGraphReport, build_ref_graph

RECOVERABLE_CLASSES = frozenset(
    {
        "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER",
        "THIN_EXECUTABLE_SURFACE",
        "RECOVERY_IN_PROGRESS",
    }
)
RECOVERABLE_DISPOSITIONS = frozenset({"HIGH_PRIORITY_STRANDED", "COMPOSITION_CANDIDATE"})

PacketBuilder = Callable[..., FederatedRestorationPacket]
PacketApplier = Callable[[Path, FederatedRestorationPacket], FederatedApplyReceipt]
RefGraphBuilder = Callable[..., RecoveryRefGraphReport]


@dataclass(frozen=True)
class RestorationTarget:
    repository: str
    donor_source: str
    donor_ref: str
    root_path: str
    selected_symbols: tuple[str, ...]
    allow_replace: bool = False
    max_depth: int = 8


@dataclass(frozen=True)
class EstateRestorationSelection:
    repository: str
    recovery_class: str
    priority_score: int
    target: RestorationTarget

    def as_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "recovery_class": self.recovery_class,
            "priority_score": self.priority_score,
            "target": asdict(self.target),
        }


@dataclass(frozen=True)
class EstateFederatedRestorationResult:
    schema: str
    selected: EstateRestorationSelection
    packet: FederatedRestorationPacket
    apply_receipt: FederatedApplyReceipt | None

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "selected": self.selected.as_dict(),
            "packet": self.packet.to_dict(),
            "apply_receipt": (
                self.apply_receipt.to_dict() if self.apply_receipt is not None else None
            ),
        }


def _observation_map(census: EstateRecoveryCensus) -> dict[str, RepositoryRecoveryObservation]:
    return {row.repository: row for row in census.observations}


def _repository_name(repo: Path) -> str:
    """Resolve the repository identity from origin when possible, then directory name."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        raw = proc.stdout.strip().rstrip("/")
        tail = raw.rsplit("/", 1)[-1].removesuffix(".git")
        if tail:
            return tail
    return repo.resolve().name


def _top_level_python_symbols(source: str) -> tuple[str, ...]:
    """Return donor-owned executable symbols in stable source order."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"donor Python source is not parseable: {exc}") from exc
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not (
            node.name.startswith("_")
        ):
            names.append(node.name)
    return tuple(names)


def derive_restoration_targets(
    repo: Path,
    graph: RecoveryRefGraphReport,
    *,
    repository: str | None = None,
    max_targets: int = 8,
    max_symbols_per_target: int = 12,
) -> tuple[RestorationTarget, ...]:
    """Convert ranked divergent ref families into exact, symbol-bound restoration targets.

    Only deeply qualified recovery families are admitted. A target must expose a Python
    source path with at least one public top-level executable symbol. The donor ref is the
    exact representative SHA, so later branch movement cannot silently alter the packet.
    """
    if max_targets <= 0 or max_symbols_per_target <= 0:
        raise ValueError("target and symbol limits must be positive")
    repo = repo.resolve()
    repo_name = repository or _repository_name(repo)
    targets: list[RestorationTarget] = []
    seen: set[tuple[str, str]] = set()

    for family in graph.families:
        reconnaissance = family.reconnaissance
        if reconnaissance is None or reconnaissance.disposition not in RECOVERABLE_DISPOSITIONS:
            continue
        candidate_paths = tuple(
            path
            for path in (*reconnaissance.top_paths, *reconnaissance.qualified_paths)
            if path.endswith(".py") and not Path(path).name.startswith("test_")
        )
        for path in dict.fromkeys(candidate_paths):
            key = (family.representative_sha, path)
            if key in seen:
                continue
            seen.add(key)
            proc = subprocess.run(
                ["git", "-C", str(repo), "show", f"{family.representative_sha}:{path}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                continue
            symbols = _top_level_python_symbols(proc.stdout)[:max_symbols_per_target]
            if not symbols:
                continue
            targets.append(
                RestorationTarget(
                    repository=repo_name,
                    donor_source=str(repo),
                    donor_ref=family.representative_sha,
                    root_path=path,
                    selected_symbols=symbols,
                )
            )
            break
        if len(targets) >= max_targets:
            break
    return tuple(targets)


def discover_restoration_targets(
    repo: Path,
    *,
    repository: str | None = None,
    target_ref: str = "HEAD",
    max_targets: int = 8,
    graph_builder: RefGraphBuilder = build_ref_graph,
) -> tuple[RestorationTarget, ...]:
    """Build live ref-graph reconnaissance and derive executable restoration targets."""
    graph = graph_builder(repo, target_ref=target_ref)
    targets = derive_restoration_targets(
        repo, graph, repository=repository, max_targets=max_targets
    )
    if not targets:
        raise ValueError("ref graph exposed no executable restoration targets")
    return targets


def select_restoration_target(
    census: EstateRecoveryCensus,
    targets: Sequence[RestorationTarget],
) -> EstateRestorationSelection:
    """Choose the highest-priority executable target backed by a live census row."""
    if not targets:
        raise ValueError("estate restoration requires at least one configured target")
    observations = _observation_map(census)
    candidates: list[EstateRestorationSelection] = []
    seen: set[tuple[str, str, str]] = set()
    for target in targets:
        identity = (target.repository, target.donor_ref, target.root_path)
        if identity in seen:
            raise ValueError(f"duplicate restoration target: {identity}")
        seen.add(identity)
        row = observations.get(target.repository)
        if row is None:
            raise ValueError(f"restoration target missing from census: {target.repository}")
        if not row.exists or row.archived or row.disabled:
            continue
        if row.recovery_class not in RECOVERABLE_CLASSES:
            continue
        if not target.selected_symbols:
            raise ValueError(f"restoration target has no selected symbols: {target.repository}")
        candidates.append(
            EstateRestorationSelection(
                repository=target.repository,
                recovery_class=row.recovery_class,
                priority_score=row.priority_score,
                target=target,
            )
        )
    if not candidates:
        raise ValueError("no executable restoration target survived census qualification")
    candidates.sort(
        key=lambda item: (
            -item.priority_score,
            item.repository.casefold(),
            item.target.root_path,
            item.target.donor_ref,
        )
    )
    return candidates[0]


def execute_estate_federated_restoration(
    target_repo: Path,
    census: EstateRecoveryCensus,
    targets: Sequence[RestorationTarget],
    *,
    target_ref: str = "HEAD",
    apply: bool = False,
    packet_builder: PacketBuilder = build_federated_packet,
    packet_applier: PacketApplier = apply_federated_packet,
) -> EstateFederatedRestorationResult:
    """Select one estate-priority donor, build an exact packet, and optionally apply it."""
    selection = select_restoration_target(census, targets)
    configured = selection.target
    packet = packet_builder(
        target_repo,
        donor_source=configured.donor_source,
        donor_ref=configured.donor_ref,
        target_ref=target_ref,
        root_path=configured.root_path,
        selected_symbols=configured.selected_symbols,
        allow_replace=configured.allow_replace,
        max_depth=configured.max_depth,
    )
    receipt = packet_applier(target_repo, packet) if apply else None
    return EstateFederatedRestorationResult(
        schema="glaciereq.estate-federated-restoration.v2",
        selected=selection,
        packet=packet,
        apply_receipt=receipt,
    )


def execute_auto_estate_federated_restoration(
    target_repo: Path,
    census: EstateRecoveryCensus,
    *,
    repository: str | None = None,
    target_ref: str = "HEAD",
    max_targets: int = 8,
    apply: bool = False,
    graph_builder: RefGraphBuilder = build_ref_graph,
    packet_builder: PacketBuilder = build_federated_packet,
    packet_applier: PacketApplier = apply_federated_packet,
) -> EstateFederatedRestorationResult:
    """Discover, qualify, bind, and optionally apply the strongest live restoration target."""
    targets = discover_restoration_targets(
        target_repo,
        repository=repository,
        target_ref=target_ref,
        max_targets=max_targets,
        graph_builder=graph_builder,
    )
    return execute_estate_federated_restoration(
        target_repo,
        census,
        targets,
        target_ref=target_ref,
        apply=apply,
        packet_builder=packet_builder,
        packet_applier=packet_applier,
    )


def load_targets(path: Path) -> tuple[RestorationTarget, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("targets") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("restoration target manifest requires non-empty targets")
    targets: list[RestorationTarget] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"targets[{index}] must be an object")
        symbols = row.get("selected_symbols")
        if not isinstance(symbols, list) or not all(
            isinstance(symbol, str) and symbol for symbol in symbols
        ):
            raise ValueError(f"targets[{index}].selected_symbols must be non-empty strings")
        targets.append(
            RestorationTarget(
                repository=str(row["repository"]),
                donor_source=str(row["donor_source"]),
                donor_ref=str(row["donor_ref"]),
                root_path=str(row["root_path"]),
                selected_symbols=tuple(symbols),
                allow_replace=bool(row.get("allow_replace", False)),
                max_depth=int(row.get("max_depth", 8)),
            )
        )
    return tuple(targets)


def load_census(path: Path) -> EstateRecoveryCensus:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("census must be an object")
    observations = tuple(RepositoryRecoveryObservation(**row) for row in payload["observations"])
    return EstateRecoveryCensus(
        schema=str(payload["schema"]),
        owner=str(payload["owner"]),
        checked_count=int(payload["checked_count"]),
        class_counts=dict(payload["class_counts"]),
        observations=observations,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-estate-restore")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--census", type=Path, required=True)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--repository")
    parser.add_argument("--target-ref", default="HEAD")
    parser.add_argument("--max-auto-targets", type=int, default=8)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    census = load_census(args.census)
    if args.targets is None:
        result = execute_auto_estate_federated_restoration(
            args.repo,
            census,
            repository=args.repository,
            target_ref=args.target_ref,
            max_targets=args.max_auto_targets,
            apply=args.apply,
        )
    else:
        result = execute_estate_federated_restoration(
            args.repo,
            census,
            load_targets(args.targets),
            target_ref=args.target_ref,
            apply=args.apply,
        )
    rendered = json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
