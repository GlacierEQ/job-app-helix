from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from job_app_helix.capability_archaeology import excavate
from job_app_helix.restoration_executor import RestorationError, apply_packet, build_packet, rollback


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


def test_deleted_capability_is_excavated_restored_and_rolled_back(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    capability = repo / "src" / "solver.py"
    capability.parent.mkdir(parents=True)
    capability.write_text("def solve():\n    return 'strong'\n", encoding="utf-8")
    donor = _commit(repo, "strong solver")

    capability.unlink()
    (repo / "README.md").write_text("later gain\n", encoding="utf-8")
    target = _commit(repo, "remove solver but add later docs")

    report = excavate(repo, donor_ref=donor, target_ref=target)
    candidate = next(item for item in report.candidates if item.path == "src/solver.py")
    assert candidate.status == "D"
    assert candidate.recovery_score == 1.0
    assert candidate.target_blob_sha256 is None

    packet = build_packet(report.candidates, selected_paths=("src/solver.py",))
    receipt = apply_packet(repo, packet)

    assert capability.read_text(encoding="utf-8") == "def solve():\n    return 'strong'\n"
    assert (repo / "README.md").read_text(encoding="utf-8") == "later gain\n"
    assert receipt.restored_paths == ("src/solver.py",)

    rollback(repo, receipt)
    assert not capability.exists()
    assert (repo / "README.md").read_text(encoding="utf-8") == "later gain\n"


def test_existing_later_capability_requires_explicit_replace_permission(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "engine.py"
    path.write_text("VALUE = 'old'\n", encoding="utf-8")
    donor = _commit(repo, "old implementation")
    path.write_text("VALUE = 'new'\n", encoding="utf-8")
    target = _commit(repo, "later implementation")

    report = excavate(repo, donor_ref=donor, target_ref=target)
    with pytest.raises(RestorationError, match="refusing to overwrite later target capability"):
        build_packet(report.candidates, selected_paths=("engine.py",))

    packet = build_packet(
        report.candidates,
        selected_paths=("engine.py",),
        allow_replace=True,
    )
    receipt = apply_packet(repo, packet)
    assert path.read_text(encoding="utf-8") == "VALUE = 'old'\n"
    rollback(repo, receipt)
    assert path.read_text(encoding="utf-8") == "VALUE = 'new'\n"


def test_target_drift_fails_closed_without_partial_overwrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "engine.py"
    path.write_text("VALUE = 'old'\n", encoding="utf-8")
    donor = _commit(repo, "old implementation")
    path.write_text("VALUE = 'new'\n", encoding="utf-8")
    target = _commit(repo, "later implementation")

    report = excavate(repo, donor_ref=donor, target_ref=target)
    packet = build_packet(
        report.candidates,
        selected_paths=("engine.py",),
        allow_replace=True,
    )
    path.write_text("VALUE = 'drifted'\n", encoding="utf-8")

    with pytest.raises(RestorationError, match="target drift"):
        apply_packet(repo, packet)
    assert path.read_text(encoding="utf-8") == "VALUE = 'drifted'\n"


def test_report_and_packet_receipts_are_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    path = repo / "feature.py"
    path.write_text("POWER = 10\n", encoding="utf-8")
    donor = _commit(repo, "feature")
    path.unlink()
    target = _commit(repo, "remove feature")

    first = excavate(repo, donor_ref=donor, target_ref=target)
    second = excavate(repo, donor_ref=donor, target_ref=target)
    assert first.receipt_sha256 == second.receipt_sha256

    packet_a = build_packet(first.candidates, selected_paths=("feature.py",))
    packet_b = build_packet(second.candidates, selected_paths=("feature.py",))
    assert packet_a.packet_sha256 == packet_b.packet_sha256
