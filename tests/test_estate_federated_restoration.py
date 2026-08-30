from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from job_app_helix.estate_federated_restoration import (
    RestorationTarget,
    derive_restoration_targets,
    execute_auto_estate_federated_restoration,
    execute_estate_federated_restoration,
    select_restoration_target,
)
from job_app_helix.estate_recovery_census import (
    EstateRecoveryCensus,
    RepositoryRecoveryObservation,
)


def observation(name: str, recovery_class: str, score: int, *, exists: bool = True):
    return RepositoryRecoveryObservation(
        repository=name,
        exists=exists,
        archived=False,
        disabled=False,
        fork=False,
        size_kb=100,
        default_branch="main",
        pushed_at="2026-08-18T00:00:00Z",
        recent_messages=(),
        recovery_signal_count=1,
        power_signal_count=0,
        recovery_class=recovery_class,
        priority_score=score,
        error=None,
    )


def census(*rows: RepositoryRecoveryObservation) -> EstateRecoveryCensus:
    return EstateRecoveryCensus(
        schema="glaciereq.estate-recovery-census.v1",
        owner="GlacierEQ",
        checked_count=len(rows),
        class_counts={},
        observations=rows,
    )


def target(name: str) -> RestorationTarget:
    return RestorationTarget(
        repository=name,
        donor_source=f"https://github.com/GlacierEQ/{name}.git",
        donor_ref="main",
        root_path="src/engine.py",
        selected_symbols=("Engine",),
    )


def test_selects_highest_priority_executable_census_target():
    state = census(
        observation("thin", "THIN_EXECUTABLE_SURFACE", 75),
        observation("stranded", "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER", 90),
        observation("healthy", "HEALTHY_MONITOR", 10),
    )

    selected = select_restoration_target(
        state,
        (target("thin"), target("stranded"), target("healthy")),
    )

    assert selected.repository == "stranded"
    assert selected.priority_score == 90


def test_missing_archived_or_healthy_targets_never_become_restoration_packets():
    state = census(
        observation("missing", "MISSING_OR_INACCESSIBLE", 100, exists=False),
        observation("healthy", "HEALTHY_MONITOR", 10),
    )

    with pytest.raises(ValueError, match="no executable restoration target"):
        select_restoration_target(state, (target("missing"), target("healthy")))


@dataclass(frozen=True)
class FakePacket:
    donor_source: str
    donor_ref: str
    target_ref: str
    symbols: tuple[str, ...]

    def to_dict(self):
        return {
            "donor_source": self.donor_source,
            "donor_ref": self.donor_ref,
            "target_ref": self.target_ref,
            "symbols": list(self.symbols),
        }


@dataclass(frozen=True)
class FakeReceipt:
    applied: bool = True

    def to_dict(self):
        return {"applied": self.applied}


def test_execution_binds_ranked_estate_target_to_exact_packet_builder_and_apply(tmp_path: Path):
    calls: list[tuple[str, object]] = []

    def builder(repo, **kwargs):
        calls.append(("build", kwargs))
        return FakePacket(
            donor_source=kwargs["donor_source"],
            donor_ref=kwargs["donor_ref"],
            target_ref=kwargs["target_ref"],
            symbols=kwargs["selected_symbols"],
        )

    def applier(repo, packet):
        calls.append(("apply", packet))
        return FakeReceipt()

    state = census(
        observation("lower", "THIN_EXECUTABLE_SURFACE", 75),
        observation("winner", "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER", 90),
    )
    result = execute_estate_federated_restoration(
        tmp_path,
        state,
        (target("lower"), target("winner")),
        target_ref="main",
        apply=True,
        packet_builder=builder,
        packet_applier=applier,
    )

    assert result.selected.repository == "winner"
    assert result.packet.donor_source.endswith("/winner.git")
    assert result.packet.target_ref == "main"
    assert result.apply_receipt is not None
    assert [name for name, _ in calls] == ["build", "apply"]


def test_duplicate_target_configuration_fails_closed():
    state = census(observation("winner", "THIN_EXECUTABLE_SURFACE", 75))
    with pytest.raises(ValueError, match="duplicate restoration target"):
        select_restoration_target(state, (target("winner"), target("winner")))


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def _donor_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "job-app-helix"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "APEX Test")
    source = repo / "src" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def recovered_ranker(value):\n    return value * 2\n\n"
        "class RecoveryEngine:\n    pass\n\n"
        "def _internal_helper():\n    return None\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "donor capability")
    return repo, _git(repo, "rev-parse", "HEAD")


def _graph(donor_sha: str, disposition: str = "HIGH_PRIORITY_STRANDED"):
    reconnaissance = SimpleNamespace(
        disposition=disposition,
        top_paths=("src/engine.py",),
        qualified_paths=("src/engine.py",),
    )
    family = SimpleNamespace(
        representative_sha=donor_sha,
        reconnaissance=reconnaissance,
    )
    return SimpleNamespace(families=(family,))


def test_derives_exact_sha_symbol_bound_target_from_ranked_ref_graph(tmp_path: Path):
    repo, donor_sha = _donor_repo(tmp_path)

    targets = derive_restoration_targets(
        repo,
        _graph(donor_sha),
        repository="job-app-helix",
    )

    assert len(targets) == 1
    assert targets[0].donor_ref == donor_sha
    assert targets[0].donor_source == str(repo.resolve())
    assert targets[0].root_path == "src/engine.py"
    assert targets[0].selected_symbols == ("recovered_ranker", "RecoveryEngine")


def test_derivation_rejects_evidence_only_family_even_when_python_exists(tmp_path: Path):
    repo, donor_sha = _donor_repo(tmp_path)

    targets = derive_restoration_targets(
        repo,
        _graph(donor_sha, disposition="EVIDENCE_CANDIDATE"),
        repository="job-app-helix",
    )

    assert targets == ()


def test_auto_execution_discovers_target_then_builds_packet_without_manifest(tmp_path: Path):
    repo, donor_sha = _donor_repo(tmp_path)
    calls: list[dict[str, object]] = []

    def graph_builder(repo_path, *, target_ref):
        assert target_ref == "HEAD"
        return _graph(donor_sha)

    def builder(repo_path, **kwargs):
        calls.append(kwargs)
        return FakePacket(
            donor_source=kwargs["donor_source"],
            donor_ref=kwargs["donor_ref"],
            target_ref=kwargs["target_ref"],
            symbols=kwargs["selected_symbols"],
        )

    result = execute_auto_estate_federated_restoration(
        repo,
        census(observation("job-app-helix", "RECOVERY_IN_PROGRESS", 60)),
        repository="job-app-helix",
        graph_builder=graph_builder,
        packet_builder=builder,
    )

    assert result.selected.target.donor_ref == donor_sha
    assert result.selected.target.root_path == "src/engine.py"
    assert result.packet.symbols == ("recovered_ranker", "RecoveryEngine")
    assert len(calls) == 1
