from __future__ import annotations

import subprocess
from pathlib import Path

from job_app_helix.recovery_ref_graph import build_ref_graph, inspect_ref


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Ref Graph Test")
    _git(repo, "config", "user.email", "ref-graph@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _commit(repo, "base")
    return repo


def test_equivalent_branch_deltas_collapse_into_one_recovery_family(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = _git(repo, "rev-parse", "main")

    _git(repo, "switch", "-c", "feature-a", base)
    source = repo / "src" / "engine.py"
    source.parent.mkdir(parents=True)
    source.write_text("def engine():\n    return 7\n", encoding="utf-8")
    head_a = _commit(repo, "feature a")

    _git(repo, "switch", "main")
    _git(repo, "switch", "-c", "feature-b", base)
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("def engine():\n    return 7\n", encoding="utf-8")
    head_b = _commit(repo, "feature b same bytes")

    _git(repo, "switch", "main")
    (repo / "README.md").write_text("modern target\n", encoding="utf-8")
    target = _commit(repo, "advance main")

    report = build_ref_graph(
        repo,
        target_ref=target,
        namespaces=("refs/heads",),
        max_deep_families=8,
    )

    family = next(family for family in report.families if "feature-a" in family.aliases)
    assert set(family.aliases) == {"feature-a", "feature-b"}
    assert family.representative_sha in {head_a, head_b}
    assert family.executable_path_count == 1
    assert family.reconnaissance is not None
    assert family.reconnaissance.deleted_source_test_count == 1
    assert family.reconnaissance.disposition == "HIGH_PRIORITY_STRANDED"


def test_cherry_equivalent_branch_is_not_a_recovery_family(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = _git(repo, "rev-parse", "main")

    _git(repo, "switch", "-c", "integrated-feature", base)
    source = repo / "src" / "integrated.py"
    source.parent.mkdir(parents=True)
    source.write_text("def integrated():\n    return True\n", encoding="utf-8")
    donor = _commit(repo, "branch patch")

    _git(repo, "switch", "main")
    (repo / "README.md").write_text("main advanced first\n", encoding="utf-8")
    _commit(repo, "independent main advance")
    _git(repo, "cherry-pick", donor)
    target = _git(repo, "rev-parse", "HEAD")

    delta = inspect_ref(
        repo,
        ref_name="refs/heads/integrated-feature",
        head_sha=donor,
        target_sha=target,
    )
    report = build_ref_graph(
        repo,
        target_ref=target,
        namespaces=("refs/heads",),
        max_deep_families=8,
    )

    assert delta.state == "PATCH_EQUIVALENT"
    assert report.equivalent_refs >= 1
    assert all("integrated-feature" not in family.aliases for family in report.families)


def test_deep_scan_preserves_only_branch_owned_capability(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inherited = repo / "src" / "old_baseline.py"
    inherited.parent.mkdir(parents=True)
    inherited.write_text("def historical():\n    return 'old'\n", encoding="utf-8")
    base = _commit(repo, "shared old baseline")

    _git(repo, "switch", "-c", "stranded", base)
    unique = repo / "src" / "unique_engine.py"
    unique.write_text("def recover_me():\n    return 'unique'\n", encoding="utf-8")
    _commit(repo, "unique stranded engine")

    _git(repo, "switch", "main")
    inherited.unlink()
    (repo / "README.md").write_text("newer main\n", encoding="utf-8")
    target = _commit(repo, "later main removes unrelated baseline")

    report = build_ref_graph(
        repo,
        target_ref=target,
        namespaces=("refs/heads",),
        max_deep_families=8,
    )
    family = next(family for family in report.families if "stranded" in family.aliases)
    recon = family.reconnaissance

    assert recon is not None
    assert recon.lineage_mode == "DIVERGED_BRANCH"
    assert recon.qualified_paths == ("src/unique_engine.py",)
    assert recon.excluded_baseline_count >= 1
    assert "src/old_baseline.py" not in recon.qualified_paths
    assert report.deep_reconnaissance is not None
    summary = report.deep_reconnaissance.intelligent_plan_summary
    assert summary is not None
    paths = [candidate["path"] for candidate in summary["top_candidates"]]
    assert "src/unique_engine.py" in paths
    assert "src/old_baseline.py" not in paths


def test_graph_is_deterministic_and_ignores_target_and_ancestor_refs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    ancestor = _git(repo, "rev-parse", "main")
    _git(repo, "branch", "historical-alias", ancestor)
    (repo / "README.md").write_text("target advance\n", encoding="utf-8")
    target = _commit(repo, "advance target")

    first = build_ref_graph(
        repo,
        target_ref=target,
        namespaces=("refs/heads",),
        max_deep_families=8,
    )
    second = build_ref_graph(
        repo,
        target_ref=target,
        namespaces=("refs/heads",),
        max_deep_families=8,
    )

    assert first.receipt_sha256 == second.receipt_sha256
    assert first.target_sha == target
    assert first.ancestor_refs >= 1
    assert first.divergent_refs == 0
    assert first.families == ()
    assert first.deep_reconnaissance is None
