from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from job_app_helix.restoration_executor import RestorationError
from job_app_helix.symbol_restoration import (
    apply_symbol_packet,
    build_symbol_packet,
    excavate_python_symbols,
    rollback_symbols,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "APEX Test")
    _git(repo, "config", "user.email", "apex@example.invalid")
    return repo


def test_missing_function_is_restored_without_replacing_later_file_gains(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "engine.py"
    path.write_text(
        "def recovered_power(value: int) -> int:\n"
        "    return value * 8\n\n"
        "def survivor() -> str:\n"
        "    return 'donor'\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "powerful donor")
    path.write_text(
        "def survivor() -> str:\n"
        "    return 'later-gain'\n\n"
        "def new_capability() -> str:\n"
        "    return 'preserve-me'\n",
        encoding="utf-8",
    )
    target = _commit(repo, "later gains after lost power")
    before = path.read_bytes()

    report = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="engine.py")
    missing = next(item for item in report.candidates if item.qualified_name == "recovered_power")
    assert missing.status == "missing"
    packet = build_symbol_packet(report, selected_symbols=("recovered_power",))
    receipt = apply_symbol_packet(repo, packet)

    composed = path.read_text(encoding="utf-8")
    assert "return value * 8" in composed
    assert "return 'later-gain'" in composed
    assert "return 'preserve-me'" in composed
    namespace: dict[str, object] = {}
    exec(compile(composed, "engine.py", "exec"), namespace)
    assert namespace["recovered_power"](3) == 24  # type: ignore[index,operator]
    assert receipt.restored_symbols == ("recovered_power",)

    rollback_symbols(repo, receipt)
    assert path.read_bytes() == before


def test_missing_dependency_is_auto_composed_with_selected_symbol(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "solver.py"
    path.write_text(
        "def _amplify(value: int) -> int:\n"
        "    return value * 3\n\n"
        "def solve(value: int) -> int:\n"
        "    return _amplify(value) + 1\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "composed donor")
    path.write_text("RESULT_VERSION = 2\n", encoding="utf-8")
    target = _commit(repo, "remove solver functions")

    report = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="solver.py")
    solve = next(item for item in report.candidates if item.qualified_name == "solve")
    assert solve.dependencies == ("_amplify",)
    packet = build_symbol_packet(report, selected_symbols=("solve",))
    assert {action.qualified_name for action in packet.actions} == {"_amplify", "solve"}

    apply_symbol_packet(repo, packet)
    namespace: dict[str, object] = {}
    exec(compile(path.read_text(), "solver.py", "exec"), namespace)
    assert namespace["solve"](4) == 13  # type: ignore[index,operator]
    assert namespace["RESULT_VERSION"] == 2


def test_missing_class_method_is_inserted_without_replacing_class(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "worker.py"
    path.write_text(
        "class Worker:\n"
        "    def restored(self) -> str:\n"
        "        return 'restored'\n\n"
        "    def existing(self) -> str:\n"
        "        return 'old'\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "worker donor")
    path.write_text(
        "class Worker:\n"
        "    def existing(self) -> str:\n"
        "        return 'new'\n\n"
        "    def later(self) -> str:\n"
        "        return 'later'\n",
        encoding="utf-8",
    )
    target = _commit(repo, "worker later gains")

    report = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="worker.py")
    packet = build_symbol_packet(report, selected_symbols=("Worker.restored",))
    apply_symbol_packet(repo, packet)
    namespace: dict[str, object] = {}
    exec(compile(path.read_text(), "worker.py", "exec"), namespace)
    worker = namespace["Worker"]()  # type: ignore[operator]
    assert worker.restored() == "restored"
    assert worker.existing() == "new"
    assert worker.later() == "later"


def test_changed_symbol_requires_explicit_replace_and_preserves_neighbors(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "engine.py"
    path.write_text(
        "def score() -> int:\n    return 100\n\n"
        "def neighbor() -> str:\n    return 'same'\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "strong score")
    path.write_text(
        "def score() -> int:\n    return 1\n\n"
        "def neighbor() -> str:\n    return 'same'\n\n"
        "def later() -> str:\n    return 'gain'\n",
        encoding="utf-8",
    )
    target = _commit(repo, "weaken score but add later gain")

    report = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="engine.py")
    with pytest.raises(RestorationError, match="refusing to replace later symbol capability"):
        build_symbol_packet(report, selected_symbols=("score",))
    packet = build_symbol_packet(report, selected_symbols=("score",), allow_replace=True)
    apply_symbol_packet(repo, packet)
    text = path.read_text()
    assert "return 100" in text
    assert "return 'gain'" in text


def test_target_file_drift_fails_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "engine.py"
    path.write_text("def lost():\n    return 7\n", encoding="utf-8")
    donor = _commit(repo, "donor")
    path.write_text("VALUE = 2\n", encoding="utf-8")
    target = _commit(repo, "target")
    report = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="engine.py")
    packet = build_symbol_packet(report, selected_symbols=("lost",))
    path.write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(RestorationError, match="target drift"):
        apply_symbol_packet(repo, packet)
    assert path.read_text() == "VALUE = 3\n"


def test_symbol_receipts_are_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "engine.py"
    path.write_text("def lost():\n    return 7\n", encoding="utf-8")
    donor = _commit(repo, "donor")
    path.write_text("VALUE = 2\n", encoding="utf-8")
    target = _commit(repo, "target")
    first = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="engine.py")
    second = excavate_python_symbols(repo, donor_ref=donor, target_ref=target, path="engine.py")
    assert first.receipt_sha256 == second.receipt_sha256
    assert build_symbol_packet(first, selected_symbols=("lost",)).packet_sha256 == build_symbol_packet(
        second, selected_symbols=("lost",)
    ).packet_sha256
