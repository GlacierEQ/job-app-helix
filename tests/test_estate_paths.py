"""Job-App Helix estate path and evidence-ledger regression tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from job_app_helix import estate_paths
from job_app_helix.errors import PortfolioSourceError
from job_app_helix.evidence_ledger import (
    EMPTY_MERKLE_ROOT,
    LedgerError,
    build_ledger,
    set_repo_root,
)

SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "job_app_helix"


def test_helix_root_resolves_to_repository_root() -> None:
    root = estate_paths.helix_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "manifests").is_dir()


def test_sibling_roots_are_derived_not_hardcoded() -> None:
    assert estate_paths.monolith_root().parent == estate_paths.helix_root().parent
    assert estate_paths.tower_root().parent == estate_paths.helix_root().parent
    assert estate_paths.monolith_root().name == "monolith"
    assert estate_paths.tower_root().name == "the-tower-of-babel"


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JOB_APP_HELIX_ROOT", str(tmp_path / "helix"))
    monkeypatch.setenv("MONOLITH_ROOT", str(tmp_path / "monolith"))
    monkeypatch.setenv("TOWER_ROOT", str(tmp_path / "tower"))
    monkeypatch.setenv("LEGAL_SPINES_PATH", str(tmp_path / "spines"))
    assert estate_paths.helix_root() == tmp_path / "helix"
    assert estate_paths.monolith_root() == tmp_path / "monolith"
    assert estate_paths.tower_root() == tmp_path / "tower"
    assert estate_paths.legal_spines_path() == tmp_path / "spines"


def test_no_machine_absolute_paths_in_source() -> None:
    offenders = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for needle in ("/data/data/", "com.termux", "/root/workspace"):
            if needle in text:
                offenders.append(f"{path.name}:{needle}")
    assert offenders == []


def _seed_portfolio(root: Path, repositories: list[dict[str, object]]) -> None:
    (root / "manifests").mkdir(parents=True)
    (root / "solidify_records").mkdir(parents=True)
    (root / "manifests" / "unified_deserving_manifest.json").write_text(
        json.dumps({"repositories": repositories}),
        encoding="utf-8",
    )


def test_build_ledger_is_fail_closed_on_missing_sources(tmp_path: Path) -> None:
    set_repo_root(tmp_path)
    with pytest.raises(LedgerError, match="portfolio manifest not found"):
        build_ledger()


def test_build_ledger_is_fail_closed_on_empty_manifest(tmp_path: Path) -> None:
    _seed_portfolio(tmp_path, [])
    set_repo_root(tmp_path)
    with pytest.raises(LedgerError, match="manifest is empty"):
        build_ledger()


def test_build_ledger_is_fail_closed_without_solidify_records(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir(parents=True)
    (tmp_path / "manifests" / "unified_deserving_manifest.json").write_text(
        json.dumps({"repositories": [{"repo": "alpha", "family": "core", "source_state": "x"}]}),
        encoding="utf-8",
    )
    set_repo_root(tmp_path)
    with pytest.raises(LedgerError, match="solidify record directory not found"):
        build_ledger()


def test_build_ledger_derives_entries_from_sources(tmp_path: Path) -> None:
    _seed_portfolio(
        tmp_path,
        [
            {"repo": "alpha", "family": "core", "source_state": "core_wholes"},
            {"repo": "beta", "family": "core", "source_state": "in_preparation"},
        ],
    )
    (tmp_path / "solidify_records" / "alpha.json").write_text(
        json.dumps({"repo": "alpha", "worthy_rating": 9, "evidence_hash": "a" * 16}),
        encoding="utf-8",
    )
    set_repo_root(tmp_path)
    try:
        ledger = build_ledger()
        assert ledger.total_repos == 2
        assert ledger.verified_anchors == 0
        assert ledger.merkle_root != EMPTY_MERKLE_ROOT
        by_repo = {entry.repo: entry for entry in ledger.entries}
        assert by_repo["alpha"].worthy == 9
        assert by_repo["alpha"].evidence_hash == "a" * 16
        assert by_repo["beta"].worthy == 0
    finally:
        set_repo_root(estate_paths.helix_root())


def test_anchor_threshold_is_applied(tmp_path: Path) -> None:
    _seed_portfolio(tmp_path, [{"repo": "AKOS", "family": "GlacierEQ-core"}])
    (tmp_path / "solidify_records" / "AKOS.json").write_text(
        json.dumps({"repo": "AKOS", "worthy_rating": 9}),
        encoding="utf-8",
    )
    set_repo_root(tmp_path)
    try:
        assert build_ledger(8).verified_anchors == 1
        assert build_ledger(10).verified_anchors == 0
    finally:
        set_repo_root(estate_paths.helix_root())


def test_live_ledger_is_populated_and_non_empty() -> None:
    ledger = build_ledger()
    assert ledger.total_repos == 225
    assert len(ledger.entries) == 225
    assert ledger.merkle_root != EMPTY_MERKLE_ROOT
    assert hashlib.sha256(ledger.merkle_root.encode()).hexdigest()
    assert all(entry.evidence_hash for entry in ledger.entries)


def test_sibling_loaders_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from job_app_helix import evidence_bridge, monolith_sync

    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    monkeypatch.setattr(monolith_sync, "JOB_APP_HELIX_ROOT", empty_root)
    monkeypatch.setattr(evidence_bridge, "JOB_APP_HELIX_ROOT", empty_root)

    with pytest.raises(PortfolioSourceError, match="portfolio manifest not found"):
        monolith_sync.load_portfolio_manifest()
    with pytest.raises(PortfolioSourceError, match="solidify record directory not found"):
        monolith_sync.load_solidify_records()
    with pytest.raises(PortfolioSourceError, match="unified evidence ledger not found"):
        evidence_bridge.load_evidence_ledger()
