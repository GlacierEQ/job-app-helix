"""Cross-file semantic dependency recovery for surgical Python restoration.

A historical function rarely lives alone. Its real capability may depend on helpers
imported from neighboring modules, and those helpers may themselves have been clipped
or weakened. This module walks that import graph at exact donor/target commits, builds
one deterministic multi-file packet, validates every touched file before mutation, and
rolls back already-applied files if any later composition fails.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from .capability_archaeology import ArchaeologyError, read_donor_blob, resolve_commit
from .restoration_executor import RestorationError
from .symbol_restoration import (
    SymbolApplyReceipt,
    SymbolRestorationPacket,
    _snapshots,
    apply_symbol_packet,
    build_symbol_packet,
    excavate_python_symbols,
    rollback_symbols,
)


@dataclass(frozen=True)
class ImportedSymbol:
    local_name: str
    source_name: str
    module_path: str


@dataclass(frozen=True)
class SemanticDependency:
    consumer_path: str
    consumer_symbol: str
    provider_path: str
    provider_symbol: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CrossFileRestorationPacket:
    donor_sha: str
    target_sha: str
    root_path: str
    root_symbols: tuple[str, ...]
    symbol_packets: tuple[SymbolRestorationPacket, ...]
    dependencies: tuple[SemanticDependency, ...]
    packet_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "donor_sha": self.donor_sha,
            "target_sha": self.target_sha,
            "root_path": self.root_path,
            "root_symbols": list(self.root_symbols),
            "symbol_packets": [packet.to_dict() for packet in self.symbol_packets],
            "dependencies": [dependency.to_dict() for dependency in self.dependencies],
            "packet_sha256": self.packet_sha256,
        }


@dataclass(frozen=True)
class CrossFileApplyReceipt:
    packet_sha256: str
    restored: dict[str, tuple[str, ...]]
    file_receipts: tuple[SymbolApplyReceipt, ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "packet_sha256": self.packet_sha256,
            "restored": {path: list(symbols) for path, symbols in self.restored.items()},
            "file_receipts": [receipt.to_dict() for receipt in self.file_receipts],
            "receipt_sha256": self.receipt_sha256,
        }


def _sha(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _module_path(consumer_path: str, module: str | None, level: int) -> str | None:
    """Resolve one Python import to a repository-relative .py path."""
    consumer = PurePosixPath(consumer_path)
    if level:
        package = consumer.parent
        for _ in range(level - 1):
            package = package.parent
        parts = list(package.parts)
        if module:
            parts.extend(module.split("."))
    else:
        if not module:
            return None
        parts = module.split(".")
    candidate = PurePosixPath(*parts)
    return candidate.with_suffix(".py").as_posix()


def _imports(source: bytes, *, path: str) -> dict[str, ImportedSymbol]:
    try:
        tree = ast.parse(source.decode("utf-8"), filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ArchaeologyError(f"cannot parse Python imports {path}: {exc}") from exc
    imported: dict[str, ImportedSymbol] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        provider_path = _module_path(path, node.module, node.level)
        if provider_path is None:
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            imported[local_name] = ImportedSymbol(local_name, alias.name, provider_path)
    return imported


def _loaded_names(snapshot_source: str, *, path: str) -> set[str]:
    try:
        tree = ast.parse(snapshot_source, filename=path)
    except SyntaxError as exc:
        raise ArchaeologyError(f"cannot parse symbol source {path}: {exc}") from exc
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _candidate_for(report, symbol: str):
    return next((item for item in report.candidates if item.qualified_name == symbol), None)


def build_cross_file_packet(
    repo: Path,
    *,
    donor_ref: str,
    target_ref: str = "HEAD",
    root_path: str,
    selected_symbols: tuple[str, ...],
    allow_replace: bool = False,
    max_depth: int = 8,
) -> CrossFileRestorationPacket:
    """Build recursive imported-symbol closure for a restoration request.

    Only dependencies whose provider file exists at the target revision are composed
    here. Missing provider files remain a file-level archaeology problem and fail with
    an actionable error rather than silently manufacturing a module.
    """
    if max_depth < 1:
        raise RestorationError("max_depth must be at least 1")
    repo = repo.resolve()
    donor_sha = resolve_commit(repo, donor_ref)
    target_sha = resolve_commit(repo, target_ref)

    queue: list[tuple[str, str, int]] = [
        (root_path, symbol, 0) for symbol in selected_symbols
    ]
    requested: dict[str, set[str]] = {}
    dependencies: dict[tuple[str, str, str, str], SemanticDependency] = {}
    visited: set[tuple[str, str]] = set()

    while queue:
        path, symbol, depth = queue.pop(0)
        if (path, symbol) in visited:
            continue
        if depth > max_depth:
            raise RestorationError(
                f"semantic dependency closure exceeded max_depth={max_depth} at {path}:{symbol}"
            )
        visited.add((path, symbol))
        requested.setdefault(path, set()).add(symbol)

        donor_blob = read_donor_blob(repo, donor_sha=donor_sha, path=path)
        donor_symbols = _snapshots(donor_blob, path=path)
        snapshot = donor_symbols.get(symbol)
        if snapshot is None:
            raise RestorationError(
                f"donor symbol not found during semantic closure: {path}:{symbol}"
            )
        imports = _imports(donor_blob, path=path)
        for loaded_name in sorted(_loaded_names(snapshot.source, path=path)):
            imported = imports.get(loaded_name)
            if imported is None:
                continue
            try:
                read_donor_blob(repo, donor_sha=target_sha, path=imported.module_path)
            except ArchaeologyError as exc:
                raise RestorationError(
                    "semantic dependency requires missing provider file "
                    f"{imported.module_path}; recover the file before symbol composition"
                ) from exc
            provider_report = excavate_python_symbols(
                repo,
                donor_ref=donor_sha,
                target_ref=target_sha,
                path=imported.module_path,
            )
            candidate = _candidate_for(provider_report, imported.source_name)
            if candidate is None:
                continue
            dependencies[(path, symbol, imported.module_path, imported.source_name)] = (
                SemanticDependency(
                    consumer_path=path,
                    consumer_symbol=symbol,
                    provider_path=imported.module_path,
                    provider_symbol=imported.source_name,
                    status=candidate.status,
                )
            )
            queue.append((imported.module_path, imported.source_name, depth + 1))

    packets: list[SymbolRestorationPacket] = []
    for path in sorted(requested):
        report = excavate_python_symbols(
            repo,
            donor_ref=donor_sha,
            target_ref=target_sha,
            path=path,
        )
        restorables = {candidate.qualified_name for candidate in report.candidates}
        selected = tuple(sorted(requested[path] & restorables))
        if not selected:
            continue
        packets.append(
            build_symbol_packet(
                report,
                selected_symbols=selected,
                allow_replace=allow_replace,
                include_dependencies=True,
            )
        )

    if not packets:
        raise RestorationError("semantic closure produced no restorable symbols")
    dependency_tuple = tuple(dependencies[key] for key in sorted(dependencies))
    payload = {
        "donor_sha": donor_sha,
        "target_sha": target_sha,
        "root_path": root_path,
        "root_symbols": sorted(selected_symbols),
        "symbol_packets": [packet.to_dict() for packet in packets],
        "dependencies": [item.to_dict() for item in dependency_tuple],
    }
    return CrossFileRestorationPacket(
        donor_sha=donor_sha,
        target_sha=target_sha,
        root_path=root_path,
        root_symbols=tuple(sorted(selected_symbols)),
        symbol_packets=tuple(packets),
        dependencies=dependency_tuple,
        packet_sha256=_sha(payload),
    )


def _preflight(repo: Path, packet: CrossFileRestorationPacket) -> None:
    """Validate every touched file before the first write to avoid partial mutation."""
    for symbol_packet in packet.symbol_packets:
        for action in symbol_packet.actions:
            target = repo / action.path
            if not target.is_file():
                raise RestorationError(
                    f"target provider disappeared before apply: {action.path}"
                )
            current_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            if current_sha != action.expected_target_file_sha256:
                raise RestorationError(
                    f"target drift at {action.path}; semantic packet is stale"
                )
        action_path = symbol_packet.actions[0].path
        donor_blob = read_donor_blob(repo, donor_sha=packet.donor_sha, path=action_path)
        donor_symbols = _snapshots(donor_blob, path=action_path)
        for action in symbol_packet.actions:
            donor = donor_symbols.get(action.qualified_name)
            if donor is None or donor.source_sha256 != action.donor_symbol_sha256:
                raise ArchaeologyError(
                    f"donor symbol drift at {action.path}:{action.qualified_name}"
                )


def apply_cross_file_packet(
    repo: Path,
    packet: CrossFileRestorationPacket,
) -> CrossFileApplyReceipt:
    """Apply a multi-file semantic packet transactionally with rollback on failure."""
    repo = repo.resolve()
    _preflight(repo, packet)
    receipts: list[SymbolApplyReceipt] = []
    restored: dict[str, tuple[str, ...]] = {}
    try:
        for symbol_packet in packet.symbol_packets:
            receipt = apply_symbol_packet(repo, symbol_packet)
            receipts.append(receipt)
            path = symbol_packet.actions[0].path
            restored[path] = receipt.restored_symbols
    except Exception:
        for receipt in reversed(receipts):
            rollback_symbols(repo, receipt)
        raise

    payload = {
        "packet_sha256": packet.packet_sha256,
        "restored": {path: list(symbols) for path, symbols in sorted(restored.items())},
        "file_receipts": [receipt.to_dict() for receipt in receipts],
    }
    return CrossFileApplyReceipt(
        packet_sha256=packet.packet_sha256,
        restored=restored,
        file_receipts=tuple(receipts),
        receipt_sha256=_sha(payload),
    )


def rollback_cross_file(repo: Path, receipt: CrossFileApplyReceipt) -> None:
    """Restore every touched file to its byte-exact pre-composition state."""
    for file_receipt in reversed(receipt.file_receipts):
        rollback_symbols(repo, file_receipt)
