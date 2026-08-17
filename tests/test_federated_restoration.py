from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from job_app_helix.federated_restoration import (
    apply_federated_packet,
    build_federated_packet,
    rollback_federated,
)
from job_app_helix.restoration_executor import RestorationError


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "APEX Test")
    _git(path, "config", "user.email", "apex@example.invalid")
    return path


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _write_donor(repo: Path) -> str:
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def amplify(value: int) -> int:\n"
        "    return value * 12\n\n"
        "def donor_only() -> str:\n"
        "    return 'historical'\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "def restored_engine(value: int) -> int:\n"
        "    return amplify(value) + 7\n",
        encoding="utf-8",
    )
    return _commit(repo, "strong donor capability")


def _write_target(repo: Path) -> str:
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def later_gain() -> str:\n"
        "    return 'preserve-me'\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "ENGINE_VERSION = 3\n",
        encoding="utf-8",
    )
    return _commit(repo, "target after capability contraction")


def test_federated_restoration_recovers_cross_repo_dependency_graph(tmp_path: Path) -> None:
    donor_repo = _repo(tmp_path / "donor")
    donor_sha = _write_donor(donor_repo)
    target_repo = _repo(tmp_path / "target")
    target_sha = _write_target(target_repo)
    before_engine = (target_repo / "pkg/engine.py").read_bytes()
    before_helpers = (target_repo / "pkg/helpers.py").read_bytes()

    packet = build_federated_packet(
        target_repo,
        donor_source=donor_repo,
        donor_ref=donor_sha,
        target_ref=target_sha,
        root_path="pkg/engine.py",
        selected_symbols=("restored_engine",),
    )

    assert packet.donor.donor_sha == donor_sha
    assert packet.target_sha == target_sha
    assert packet.donor.imported_ref.startswith("refs/apex/donors/")
    assert {(item.provider_path, item.provider_symbol) for item in packet.semantic_packet.dependencies} == {
        ("pkg/helpers.py", "amplify")
    }

    receipt = apply_federated_packet(target_repo, packet)
    engine_text = (target_repo / "pkg/engine.py").read_text()
    helpers_text = (target_repo / "pkg/helpers.py").read_text()
    assert "def restored_engine" in engine_text
    assert "return value * 12" in helpers_text
    assert "return 'preserve-me'" in helpers_text

    namespace: dict[str, object] = {}
    helper_namespace: dict[str, object] = {}
    exec(compile(helpers_text, "pkg/helpers.py", "exec"), helper_namespace)
    namespace["amplify"] = helper_namespace["amplify"]
    executable_engine = engine_text.replace("from .helpers import amplify\n", "")
    exec(compile(executable_engine, "pkg/engine.py", "exec"), namespace)
    assert namespace["restored_engine"](3) == 43  # type: ignore[index,operator]

    rollback_federated(target_repo, receipt)
    assert (target_repo / "pkg/engine.py").read_bytes() == before_engine
    assert (target_repo / "pkg/helpers.py").read_bytes() == before_helpers


def test_federated_packet_is_deterministic_for_same_exact_sources(tmp_path: Path) -> None:
    donor_repo = _repo(tmp_path / "donor")
    donor_sha = _write_donor(donor_repo)
    target_repo = _repo(tmp_path / "target")
    target_sha = _write_target(target_repo)

    kwargs = {
        "donor_source": donor_repo,
        "donor_ref": donor_sha,
        "target_ref": target_sha,
        "root_path": "pkg/engine.py",
        "selected_symbols": ("restored_engine",),
    }
    first = build_federated_packet(target_repo, **kwargs)
    second = build_federated_packet(target_repo, **kwargs)
    assert first.packet_sha256 == second.packet_sha256
    assert first.donor.receipt_sha256 == second.donor.receipt_sha256


def test_federated_apply_refuses_imported_donor_ref_drift(tmp_path: Path) -> None:
    donor_repo = _repo(tmp_path / "donor")
    donor_sha = _write_donor(donor_repo)
    target_repo = _repo(tmp_path / "target")
    target_sha = _write_target(target_repo)
    packet = build_federated_packet(
        target_repo,
        donor_source=donor_repo,
        donor_ref=donor_sha,
        target_ref=target_sha,
        root_path="pkg/engine.py",
        selected_symbols=("restored_engine",),
    )

    _git(target_repo, "update-ref", packet.donor.imported_ref, target_sha)
    with pytest.raises(RestorationError, match="federated donor ref drifted"):
        apply_federated_packet(target_repo, packet)

    assert "restored_engine" not in (target_repo / "pkg/engine.py").read_text()
