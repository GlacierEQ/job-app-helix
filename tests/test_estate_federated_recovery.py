from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from job_app_helix import estate_federated_recovery as recovery
from job_app_helix.estate_recovery_census import (
    EstateRecoveryCensus,
    RepositoryRecoveryObservation,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _observation(name: str, recovery_class: str, score: int) -> RepositoryRecoveryObservation:
    return RepositoryRecoveryObservation(
        repository=name,
        exists=True,
        archived=False,
        disabled=False,
        fork=False,
        size_kb=100,
        default_branch="main",
        pushed_at="2026-08-18T00:00:00Z",
        recent_messages=(),
        recovery_signal_count=1,
        power_signal_count=1,
        recovery_class=recovery_class,
        priority_score=score,
        error=None,
    )


def _census() -> EstateRecoveryCensus:
    rows = (
        _observation("ignored-healthy", "HEALTHY_MONITOR", 99),
        _observation("priority-donor", "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER", 90),
        _observation("lower-donor", "RECOVERY_IN_PROGRESS", 60),
    )
    return EstateRecoveryCensus(
        schema="glaciereq.estate-recovery-census.v1",
        owner="GlacierEQ",
        checked_count=len(rows),
        class_counts={},
        observations=rows,
    )


@dataclass(frozen=True)
class FakePacket:
    packet_sha256: str = "packet-123"

    def to_dict(self) -> dict[str, object]:
        return {"packet_sha256": self.packet_sha256}


@dataclass(frozen=True)
class FakeReceipt:
    receipt_sha256: str = "apply-123"

    def to_dict(self) -> dict[str, object]:
        return {"receipt_sha256": self.receipt_sha256}


def test_estate_census_routes_high_priority_repo_through_ref_graph_to_packet(
    tmp_path: Path,
    monkeypatch,
):
    target = tmp_path / "target"
    target.mkdir()
    _git(target, "init")
    _git(target, "config", "user.email", "test@example.com")
    _git(target, "config", "user.name", "APEX Test")
    (target / "README.md").write_text("target\n", encoding="utf-8")
    _git(target, "add", ".")
    _git(target, "commit", "-m", "target")

    donor_shas: dict[str, str] = {}

    def fake_clone(owner: str, repository: str, destination: Path) -> None:
        destination.mkdir()
        _git(destination, "init")
        _git(destination, "config", "user.email", "test@example.com")
        _git(destination, "config", "user.name", "APEX Test")
        source = destination / "src" / "engine.py"
        source.parent.mkdir(parents=True)
        source.write_text(
            "def recovered_ranker(value):\n    return value * 2\n\n"
            "class RecoveryEngine:\n    pass\n",
            encoding="utf-8",
        )
        _git(destination, "add", ".")
        _git(destination, "commit", "-m", "recovered executable capability")
        donor_shas[repository] = _git(destination, "rev-parse", "HEAD")

    def fake_graph(repo: Path, *, target_ref: str):
        repository = repo.name
        sha = donor_shas[repository]
        family = SimpleNamespace(
            representative_ref="feature/recovered-engine",
            representative_sha=sha,
            executable_path_count=1,
            test_path_count=1,
            unique_commit_count=1,
            preliminary_score=0.8,
            reconnaissance=SimpleNamespace(priority_score=0.95),
        )
        return SimpleNamespace(families=(family,), receipt_sha256=f"graph-{repository}")

    packet_calls: list[dict[str, object]] = []

    def fake_packet_builder(repo: Path, **kwargs):
        packet_calls.append(kwargs)
        return FakePacket()

    monkeypatch.setattr(recovery, "build_estate_recovery_census", lambda owner, repos: _census())
    monkeypatch.setattr(recovery, "_clone_repository", fake_clone)
    monkeypatch.setattr(recovery, "build_ref_graph", fake_graph)
    monkeypatch.setattr(recovery, "build_federated_packet", fake_packet_builder)

    result = recovery.execute_estate_federated_recovery(
        target,
        owner="GlacierEQ",
        repositories=("ignored-healthy", "priority-donor", "lower-donor"),
        max_repositories=1,
    )

    assert [route.repository for route in result.routes] == ["priority-donor"]
    route = result.routes[0]
    assert route.action == "PACKET_READY"
    assert route.selected_ref == "feature/recovered-engine"
    assert route.selected_path == "src/engine.py"
    assert route.selected_symbols == ("recovered_ranker", "RecoveryEngine")
    assert route.ref_graph_receipt_sha256 == "graph-priority-donor"
    assert route.packet_sha256 == "packet-123"
    assert packet_calls[0]["donor_ref"] == donor_shas["priority-donor"]


def test_apply_mode_composes_packet_after_exact_donor_selection(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()
    _git(target, "init")
    _git(target, "config", "user.email", "test@example.com")
    _git(target, "config", "user.name", "APEX Test")
    (target / "README.md").write_text("target\n", encoding="utf-8")
    _git(target, "add", ".")
    _git(target, "commit", "-m", "target")

    donor_sha = ""

    def fake_clone(owner: str, repository: str, destination: Path) -> None:
        nonlocal donor_sha
        destination.mkdir()
        _git(destination, "init")
        _git(destination, "config", "user.email", "test@example.com")
        _git(destination, "config", "user.name", "APEX Test")
        source = destination / "engine.py"
        source.write_text("def restore_me():\n    return 42\n", encoding="utf-8")
        _git(destination, "add", ".")
        _git(destination, "commit", "-m", "restorable")
        donor_sha = _git(destination, "rev-parse", "HEAD")

    def fake_graph(repo: Path, *, target_ref: str):
        family = SimpleNamespace(
            representative_ref="feature/restore",
            representative_sha=donor_sha,
            executable_path_count=1,
            test_path_count=0,
            unique_commit_count=1,
            preliminary_score=0.8,
            reconnaissance=SimpleNamespace(priority_score=0.9),
        )
        return SimpleNamespace(families=(family,), receipt_sha256="graph-apply")

    applied: list[FakePacket] = []
    monkeypatch.setattr(
        recovery,
        "build_estate_recovery_census",
        lambda owner, repos: EstateRecoveryCensus(
            schema="glaciereq.estate-recovery-census.v1",
            owner="GlacierEQ",
            checked_count=1,
            class_counts={},
            observations=(
                _observation("priority-donor", "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER", 90),
            ),
        ),
    )
    monkeypatch.setattr(recovery, "_clone_repository", fake_clone)
    monkeypatch.setattr(recovery, "build_ref_graph", fake_graph)
    monkeypatch.setattr(recovery, "build_federated_packet", lambda *args, **kwargs: FakePacket())
    monkeypatch.setattr(
        recovery,
        "apply_federated_packet",
        lambda repo, packet: applied.append(packet) or FakeReceipt(),
    )

    result = recovery.execute_estate_federated_recovery(
        target,
        owner="GlacierEQ",
        repositories=("priority-donor",),
        apply=True,
    )

    assert result.routes[0].action == "APPLIED"
    assert len(result.applied_receipts) == 1
    assert applied == [FakePacket()]
