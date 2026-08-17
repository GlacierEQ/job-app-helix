from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from job_app_helix.cross_file_restoration import (
    apply_cross_file_packet,
    build_cross_file_packet,
    rollback_cross_file,
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


def test_cross_file_dependency_closure_restores_provider_and_consumer(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def amplify(value: int) -> int:\n"
        "    return value * 9\n\n"
        "def preserved_helper() -> str:\n"
        "    return 'old'\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "def recovered_engine(value: int) -> int:\n"
        "    return amplify(value) + 2\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "cross-file donor")

    (package / "helpers.py").write_text(
        "def preserved_helper() -> str:\n"
        "    return 'later-gain'\n\n"
        "def new_helper() -> str:\n"
        "    return 'keep-me'\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "ENGINE_VERSION = 2\n",
        encoding="utf-8",
    )
    target = _commit(repo, "later gains after cross-file contraction")
    before_engine = (package / "engine.py").read_bytes()
    before_helpers = (package / "helpers.py").read_bytes()

    packet = build_cross_file_packet(
        repo,
        donor_ref=donor,
        target_ref=target,
        root_path="pkg/engine.py",
        selected_symbols=("recovered_engine",),
    )
    assert {(item.provider_path, item.provider_symbol) for item in packet.dependencies} == {
        ("pkg/helpers.py", "amplify")
    }
    receipt = apply_cross_file_packet(repo, packet)

    assert "def recovered_engine" in (package / "engine.py").read_text()
    helper_text = (package / "helpers.py").read_text()
    assert "return value * 9" in helper_text
    assert "return 'later-gain'" in helper_text
    assert "return 'keep-me'" in helper_text

    namespace: dict[str, object] = {}
    helper_namespace: dict[str, object] = {}
    exec(compile(helper_text, "pkg/helpers.py", "exec"), helper_namespace)
    namespace["amplify"] = helper_namespace["amplify"]
    engine_text = (package / "engine.py").read_text().replace("from .helpers import amplify\n", "")
    exec(compile(engine_text, "pkg/engine.py", "exec"), namespace)
    assert namespace["recovered_engine"](4) == 38  # type: ignore[index,operator]

    rollback_cross_file(repo, receipt)
    assert (package / "engine.py").read_bytes() == before_engine
    assert (package / "helpers.py").read_bytes() == before_helpers


def test_cross_file_closure_recurses_across_import_chain(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "mathkit.py").write_text(
        "def scale(value: int) -> int:\n    return value * 5\n",
        encoding="utf-8",
    )
    (package / "helpers.py").write_text(
        "from .mathkit import scale\n\n"
        "def amplify(value: int) -> int:\n    return scale(value) + 1\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "def solve(value: int) -> int:\n    return amplify(value) + 2\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "recursive donor")
    (package / "mathkit.py").write_text("MATH_VERSION = 2\n", encoding="utf-8")
    (package / "helpers.py").write_text(
        "from .mathkit import scale\nHELPER_VERSION = 2\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\nENGINE_VERSION = 2\n",
        encoding="utf-8",
    )
    target = _commit(repo, "recursive contraction")

    packet = build_cross_file_packet(
        repo,
        donor_ref=donor,
        target_ref=target,
        root_path="pkg/engine.py",
        selected_symbols=("solve",),
    )
    assert {(item.provider_path, item.provider_symbol) for item in packet.dependencies} == {
        ("pkg/helpers.py", "amplify"),
        ("pkg/mathkit.py", "scale"),
    }
    receipt = apply_cross_file_packet(repo, packet)
    assert set(receipt.restored) == {"pkg/engine.py", "pkg/helpers.py", "pkg/mathkit.py"}


def test_changed_cross_file_provider_requires_explicit_replace(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def amplify(value: int) -> int:\n    return value * 10\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "def solve(value: int) -> int:\n    return amplify(value)\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "strong donor")
    (package / "helpers.py").write_text(
        "def amplify(value: int) -> int:\n    return value\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text("from .helpers import amplify\n", encoding="utf-8")
    target = _commit(repo, "weaken provider")

    with pytest.raises(RestorationError, match="refusing to replace later symbol capability"):
        build_cross_file_packet(
            repo,
            donor_ref=donor,
            target_ref=target,
            root_path="pkg/engine.py",
            selected_symbols=("solve",),
        )

    packet = build_cross_file_packet(
        repo,
        donor_ref=donor,
        target_ref=target,
        root_path="pkg/engine.py",
        selected_symbols=("solve",),
        allow_replace=True,
    )
    apply_cross_file_packet(repo, packet)
    assert "return value * 10" in (package / "helpers.py").read_text()


def test_preflight_prevents_partial_mutation_on_provider_drift(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def amplify(value: int) -> int:\n    return value * 2\n",
        encoding="utf-8",
    )
    (package / "engine.py").write_text(
        "from .helpers import amplify\n\n"
        "def solve(value: int) -> int:\n    return amplify(value)\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "donor")
    (package / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "engine.py").write_text("from .helpers import amplify\n", encoding="utf-8")
    target = _commit(repo, "target")
    packet = build_cross_file_packet(
        repo,
        donor_ref=donor,
        target_ref=target,
        root_path="pkg/engine.py",
        selected_symbols=("solve",),
    )
    engine_before = (package / "engine.py").read_bytes()
    (package / "helpers.py").write_text("VALUE = 999\n", encoding="utf-8")

    with pytest.raises(RestorationError, match="semantic packet is stale"):
        apply_cross_file_packet(repo, packet)
    assert (package / "engine.py").read_bytes() == engine_before
    assert (package / "helpers.py").read_text() == "VALUE = 999\n"


def test_cross_file_packet_is_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    package = repo / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text("def helper():\n    return 5\n", encoding="utf-8")
    (package / "engine.py").write_text(
        "from .helpers import helper\n\ndef solve():\n    return helper()\n",
        encoding="utf-8",
    )
    donor = _commit(repo, "donor")
    (package / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "engine.py").write_text("from .helpers import helper\n", encoding="utf-8")
    target = _commit(repo, "target")

    first = build_cross_file_packet(
        repo,
        donor_ref=donor,
        target_ref=target,
        root_path="pkg/engine.py",
        selected_symbols=("solve",),
    )
    second = build_cross_file_packet(
        repo,
        donor_ref=donor,
        target_ref=target,
        root_path="pkg/engine.py",
        selected_symbols=("solve",),
    )
    assert first.packet_sha256 == second.packet_sha256
