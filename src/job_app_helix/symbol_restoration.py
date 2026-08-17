"""AST-bound capability archaeology and surgical Python symbol restoration.

File restoration is intentionally too coarse when later gains share a file with a
lost historical mechanism. This module binds restoration to exact donor/target
commits, hashes individual function/class/method source spans, computes same-file
symbol dependencies, and edits only selected AST spans.
"""
from __future__ import annotations

import ast
import hashlib
import json
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path

from .capability_archaeology import ArchaeologyError, read_donor_blob, resolve_commit
from .restoration_executor import RestorationError


_SUPPORTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclass(frozen=True)
class SymbolSnapshot:
    qualified_name: str
    kind: str
    source_sha256: str
    source: str
    start_line: int
    end_line: int
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class SymbolCandidate:
    path: str
    qualified_name: str
    kind: str
    status: str
    donor_sha: str
    target_sha: str
    donor_symbol_sha256: str
    target_symbol_sha256: str | None
    expected_target_file_sha256: str
    dependencies: tuple[str, ...]
    recovery_score: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SymbolArchaeologyReport:
    path: str
    donor_sha: str
    target_sha: str
    candidates: tuple[SymbolCandidate, ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "donor_sha": self.donor_sha,
            "target_sha": self.target_sha,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "receipt_sha256": self.receipt_sha256,
        }


@dataclass(frozen=True)
class SymbolRestorationAction:
    path: str
    qualified_name: str
    donor_symbol_sha256: str
    expected_target_symbol_sha256: str | None
    expected_target_file_sha256: str
    mode: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SymbolRestorationPacket:
    donor_sha: str
    target_sha: str
    actions: tuple[SymbolRestorationAction, ...]
    packet_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "donor_sha": self.donor_sha,
            "target_sha": self.target_sha,
            "actions": [action.to_dict() for action in self.actions],
            "packet_sha256": self.packet_sha256,
        }


@dataclass(frozen=True)
class SymbolApplyReceipt:
    packet_sha256: str
    restored_symbols: tuple[str, ...]
    backups: dict[str, str]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_span(lines: list[str], node: ast.AST) -> tuple[int, int, str]:
    start = getattr(node, "lineno", 1)
    decorators = getattr(node, "decorator_list", ())
    if decorators:
        start = min(start, *(decorator.lineno for decorator in decorators))
    end = getattr(node, "end_lineno", start)
    return start, end, "".join(lines[start - 1 : end])


def _dependency_names(node: ast.AST, local_names: set[str], own_name: str) -> tuple[str, ...]:
    loaded = {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }
    return tuple(sorted((loaded & local_names) - {own_name}))


def _snapshots(source: bytes, *, path: str) -> dict[str, SymbolSnapshot]:
    try:
        text = source.decode("utf-8")
        tree = ast.parse(text, filename=path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ArchaeologyError(f"cannot parse Python source {path}: {exc}") from exc
    lines = text.splitlines(keepends=True)
    top_level = {node.name for node in tree.body if isinstance(node, _SUPPORTED)}
    snapshots: dict[str, SymbolSnapshot] = {}

    def capture(node: ast.AST, qualified_name: str, local_names: set[str]) -> None:
        start, end, segment = _source_span(lines, node)
        own_name = qualified_name.rsplit(".", 1)[-1]
        snapshots[qualified_name] = SymbolSnapshot(
            qualified_name=qualified_name,
            kind=type(node).__name__,
            source_sha256=_sha(segment.encode()),
            source=segment,
            start_line=start,
            end_line=end,
            dependencies=_dependency_names(node, local_names, own_name),
        )

    for node in tree.body:
        if not isinstance(node, _SUPPORTED):
            continue
        capture(node, node.name, top_level)
        if isinstance(node, ast.ClassDef):
            method_names = {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    capture(child, f"{node.name}.{child.name}", method_names | top_level)
    return snapshots


def excavate_python_symbols(
    repo: Path,
    *,
    donor_ref: str,
    path: str,
    target_ref: str = "HEAD",
) -> SymbolArchaeologyReport:
    """Find missing or changed Python functions/classes/methods at exact revisions."""
    if not path.endswith(".py"):
        raise ArchaeologyError("symbol archaeology currently supports Python source only")
    repo = repo.resolve()
    donor_sha = resolve_commit(repo, donor_ref)
    target_sha = resolve_commit(repo, target_ref)
    donor_blob = read_donor_blob(repo, donor_sha=donor_sha, path=path)
    target_blob = read_donor_blob(repo, donor_sha=target_sha, path=path)
    donor_symbols = _snapshots(donor_blob, path=path)
    target_symbols = _snapshots(target_blob, path=path)
    target_file_sha = _sha(target_blob)
    candidates: list[SymbolCandidate] = []
    for name, donor in donor_symbols.items():
        target = target_symbols.get(name)
        if target and target.source_sha256 == donor.source_sha256:
            continue
        status = "missing" if target is None else "changed"
        candidates.append(
            SymbolCandidate(
                path=path,
                qualified_name=name,
                kind=donor.kind,
                status=status,
                donor_sha=donor_sha,
                target_sha=target_sha,
                donor_symbol_sha256=donor.source_sha256,
                target_symbol_sha256=target.source_sha256 if target else None,
                expected_target_file_sha256=target_file_sha,
                dependencies=donor.dependencies,
                recovery_score=1.0 if target is None else 0.72,
            )
        )
    candidates.sort(key=lambda item: (-item.recovery_score, item.qualified_name))
    payload = {
        "path": path,
        "donor_sha": donor_sha,
        "target_sha": target_sha,
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    receipt = _sha(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return SymbolArchaeologyReport(path, donor_sha, target_sha, tuple(candidates), receipt)


def build_symbol_packet(
    report: SymbolArchaeologyReport,
    *,
    selected_symbols: tuple[str, ...],
    allow_replace: bool = False,
    include_dependencies: bool = True,
) -> SymbolRestorationPacket:
    """Build a surgical packet, expanding missing same-file symbol dependencies."""
    if not selected_symbols:
        raise RestorationError("selected_symbols cannot be empty")
    by_name = {candidate.qualified_name: candidate for candidate in report.candidates}
    selected = set(selected_symbols)
    unknown = sorted(selected - set(by_name))
    if unknown:
        raise RestorationError(f"selected symbols not present in archaeology report: {unknown}")
    if include_dependencies:
        queue = list(selected)
        while queue:
            candidate = by_name[queue.pop()]
            for dependency in candidate.dependencies:
                dependency_candidate = by_name.get(dependency)
                if (
                    dependency_candidate
                    and dependency_candidate.status == "missing"
                    and dependency not in selected
                ):
                    selected.add(dependency)
                    queue.append(dependency)
    actions: list[SymbolRestorationAction] = []
    for name in sorted(selected):
        candidate = by_name[name]
        if candidate.status == "changed" and not allow_replace:
            raise RestorationError(
                f"refusing to replace later symbol capability at {name}; "
                "pass allow_replace=True after composition review"
            )
        actions.append(
            SymbolRestorationAction(
                path=candidate.path,
                qualified_name=name,
                donor_symbol_sha256=candidate.donor_symbol_sha256,
                expected_target_symbol_sha256=candidate.target_symbol_sha256,
                expected_target_file_sha256=candidate.expected_target_file_sha256,
                mode="insert" if candidate.status == "missing" else "replace",
            )
        )
    payload = {
        "donor_sha": report.donor_sha,
        "target_sha": report.target_sha,
        "actions": [action.to_dict() for action in actions],
    }
    digest = _sha(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return SymbolRestorationPacket(report.donor_sha, report.target_sha, tuple(actions), digest)


def _replace_lines(text: str, start: int, end: int, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    lines[start - 1 : end] = [replacement if replacement.endswith("\n") else replacement + "\n"]
    return "".join(lines)


def _insert_top_level(text: str, source: str) -> str:
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    insertion = len(lines)
    for node in tree.body:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            rendered = ast.unparse(node.test)
            if "__name__" in rendered and "__main__" in rendered:
                insertion = node.lineno - 1
                break
    block = "\n" + textwrap.dedent(source).rstrip() + "\n\n"
    lines[insertion:insertion] = [block]
    return "".join(lines)


def _insert_method(text: str, class_name: str, source: str) -> str:
    tree = ast.parse(text)
    cls = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if cls is None:
        raise RestorationError(f"target class missing for method restoration: {class_name}")
    lines = text.splitlines(keepends=True)
    indent = " " * (cls.col_offset + 4)
    normalized = textwrap.dedent(source).rstrip().splitlines()
    block = "\n" + "\n".join(indent + line if line else line for line in normalized) + "\n"
    lines[cls.end_lineno : cls.end_lineno] = [block]
    return "".join(lines)


def apply_symbol_packet(repo: Path, packet: SymbolRestorationPacket) -> SymbolApplyReceipt:
    """Apply exact donor symbols while preserving all unrelated target-file bytes."""
    repo = repo.resolve()
    backups: dict[str, str] = {}
    restored: list[str] = []
    grouped: dict[str, list[SymbolRestorationAction]] = {}
    for action in packet.actions:
        grouped.setdefault(action.path, []).append(action)

    for path, actions in grouped.items():
        target = repo / path
        current_bytes = target.read_bytes()
        expected_file_sha = {action.expected_target_file_sha256 for action in actions}
        if len(expected_file_sha) != 1 or _sha(current_bytes) != next(iter(expected_file_sha)):
            raise RestorationError(f"target drift at {path}; symbol packet requires exact target file")
        backups[path] = current_bytes.hex()
        text = current_bytes.decode("utf-8")
        donor_blob = read_donor_blob(repo, donor_sha=packet.donor_sha, path=path)
        donor_symbols = _snapshots(donor_blob, path=path)

        # Replacements run bottom-up so their original AST line offsets remain valid.
        current_symbols = _snapshots(text.encode(), path=path)
        replacements = [action for action in actions if action.mode == "replace"]
        replacements.sort(
            key=lambda item: current_symbols[item.qualified_name].start_line,
            reverse=True,
        )
        for action in replacements:
            current = current_symbols.get(action.qualified_name)
            donor = donor_symbols.get(action.qualified_name)
            if current is None or donor is None:
                raise RestorationError(f"symbol missing during replacement: {action.qualified_name}")
            if current.source_sha256 != action.expected_target_symbol_sha256:
                raise RestorationError(f"symbol drift at {action.qualified_name}")
            if donor.source_sha256 != action.donor_symbol_sha256:
                raise ArchaeologyError(f"donor symbol drift at {action.qualified_name}")
            replacement = donor.source
            if "." in action.qualified_name:
                prefix = current.source[: len(current.source) - len(current.source.lstrip())]
                replacement = textwrap.indent(textwrap.dedent(replacement), prefix)
            text = _replace_lines(text, current.start_line, current.end_line, replacement)
            restored.append(action.qualified_name)

        for action in (item for item in actions if item.mode == "insert"):
            donor = donor_symbols.get(action.qualified_name)
            if donor is None or donor.source_sha256 != action.donor_symbol_sha256:
                raise ArchaeologyError(f"donor symbol drift at {action.qualified_name}")
            if "." in action.qualified_name:
                class_name, _ = action.qualified_name.split(".", 1)
                text = _insert_method(text, class_name, donor.source)
            else:
                text = _insert_top_level(text, donor.source)
            restored.append(action.qualified_name)
        try:
            compile(text, path, "exec")
        except SyntaxError as exc:
            raise RestorationError(f"composed source is invalid at {path}: {exc}") from exc
        target.write_text(text, encoding="utf-8")

    payload = {
        "packet_sha256": packet.packet_sha256,
        "restored_symbols": sorted(restored),
        "backups": backups,
    }
    digest = _sha(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return SymbolApplyReceipt(packet.packet_sha256, tuple(sorted(restored)), backups, digest)


def rollback_symbols(repo: Path, receipt: SymbolApplyReceipt) -> None:
    """Restore exact pre-composition files from a symbol apply receipt."""
    repo = repo.resolve()
    for path, encoded in receipt.backups.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes.fromhex(encoded))
