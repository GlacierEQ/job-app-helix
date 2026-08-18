"""Turn estate-wide recovery priority into exact-source federated restoration packets.

The census answers which repository needs attention. Federated restoration answers how
an exact donor revision can be composed safely into a target repository. This module
joins those planes so a ranked estate observation can become an executable, SHA-bound
restoration packet instead of stopping at archaeology.
"""

from __future__ import annotations

import argparse
import json
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

RECOVERABLE_CLASSES = frozenset(
    {
        "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER",
        "THIN_EXECUTABLE_SURFACE",
        "RECOVERY_IN_PROGRESS",
    }
)

PacketBuilder = Callable[..., FederatedRestorationPacket]
PacketApplier = Callable[[Path, FederatedRestorationPacket], FederatedApplyReceipt]


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


def select_restoration_target(
    census: EstateRecoveryCensus,
    targets: Sequence[RestorationTarget],
) -> EstateRestorationSelection:
    """Choose the highest-priority executable target backed by a live census row."""
    if not targets:
        raise ValueError("estate restoration requires at least one configured target")
    observations = _observation_map(census)
    candidates: list[EstateRestorationSelection] = []
    seen: set[str] = set()
    for target in targets:
        if target.repository in seen:
            raise ValueError(f"duplicate restoration target: {target.repository}")
        seen.add(target.repository)
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
        schema="glaciereq.estate-federated-restoration.v1",
        selected=selection,
        packet=packet,
        apply_receipt=receipt,
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
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--target-ref", default="HEAD")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = execute_estate_federated_restoration(
        args.repo,
        load_census(args.census),
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
