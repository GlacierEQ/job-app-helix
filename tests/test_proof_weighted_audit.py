from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_job_app_repository_roles_are_unique() -> None:
    path = ROOT / "manifests" / "job_app_repository_ownership.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    roles = [item["role"] for item in payload["repositories"]]

    assert len(roles) == len(set(roles))
    assert payload["authority"]["branch"] == "main"
    assert payload["uniqueness_constraints"] == {
        "portfolio_control_plane": 1,
        "private_application_workspace": 1,
        "public_recruiter_distribution": 1,
        "technology_placement_authority": 1,
    }


def test_current_public_portal_and_control_plane_commits_are_recorded() -> None:
    path = ROOT / "manifests" / "job_app_repository_ownership.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    repositories = {
        item["repository"]: item for item in payload["repositories"]
    }

    assert repositories["GlacierEQ/job-application"]["verified_commit"].startswith(
        "0ff1946f"
    )
    assert repositories["GlacierEQ/job-app-helix"]["verified_commit"].startswith(
        "04b86016"
    )


def test_featured_verifier_rejects_zero_test_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_script("run_featured_verification")
    command = [
        sys.executable,
        "-c",
        "print('0 passed in 0.01s')",
        "pytest",
    ]
    monkeypatch.setattr(
        module,
        "collect_pytest_count",
        lambda argv, cwd, timeout, env: (0, "", 0),
    )

    exit_code, output, observed = module.run_commands(
        [command],
        tmp_path,
        timeout=10,
    )

    assert exit_code == 3
    assert observed == 0
    assert "UNVERIFIED" in output


def test_featured_verifier_resolves_exact_checked_out_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_script("run_featured_verification")
    expected = "a" * 40

    def fake_run(argv, **kwargs):
        assert argv == ["git", "rev-parse", "--verify", "HEAD^{commit}"]
        assert kwargs["cwd"] == tmp_path
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(argv, 0, expected + "\n", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.resolve_commit_sha(tmp_path) == expected


def test_featured_verifier_rejects_mutable_ref_as_commit_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_script("run_featured_verification")

    def fake_run(argv, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(argv, 0, "main\n", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.resolve_commit_sha(tmp_path) is None


def test_census_reports_missing_tests_without_inventing_provenance(
    tmp_path: Path,
) -> None:
    module = load_script("proof_weighted_repo_census")
    (tmp_path / "README.md").write_text(
        "# Example\n\nWhy it matters.\n\n## Architecture\n\n## Machine-readable contract\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text("VALUE = 1\n", encoding="utf-8")

    result = module.build_result(
        repo="GlacierEQ/example",
        root=tmp_path,
        metadata={"visibility": "public", "fork": False},
        timeout=10,
    )

    assert result["schema"] == "glaciereq.portfolio.audit.v2"
    assert result["verification"]["python"]["status"] == "NO_TEST_PATH"
    assert result["verification"]["python"]["observed_count"] == 0
    assert result["provenance"] == {"state": "UNRESOLVED", "markers": []}
    assert result["admission_class"] == "candidate_public_unresolved_provenance"


def test_census_recognizes_explicit_downstream_without_claiming_originality(
    tmp_path: Path,
) -> None:
    module = load_script("proof_weighted_repo_census")
    (tmp_path / "README.md").write_text("# Downstream\n", encoding="utf-8")
    (tmp_path / "GLACIEREQ_DOWNSTREAM.md").write_text(
        "Upstream: example/upstream\n",
        encoding="utf-8",
    )

    result = module.build_result(
        repo="GlacierEQ/downstream",
        root=tmp_path,
        metadata={"visibility": "public", "fork": False},
        timeout=10,
    )

    assert result["provenance"] == {
        "state": "EXPLICIT_DOWNSTREAM",
        "markers": ["GLACIEREQ_DOWNSTREAM.md"],
    }
    assert result["admission_class"] == "candidate_attributed_downstream"


def test_census_recognizes_paired_upstream_lineage_markers(tmp_path: Path) -> None:
    module = load_script("proof_weighted_repo_census")
    (tmp_path / "README.md").write_text("# Derived\n", encoding="utf-8")
    (tmp_path / "SOURCE_REV").write_text("abc123\n", encoding="utf-8")
    (tmp_path / "THIRD-PARTY-NOTICES").write_text(
        "Upstream notices\n",
        encoding="utf-8",
    )

    result = module.build_result(
        repo="GlacierEQ/derived",
        root=tmp_path,
        metadata={"visibility": "public", "fork": False},
        timeout=10,
    )

    assert result["provenance"] == {
        "state": "EXPLICIT_UPSTREAM_LINEAGE",
        "markers": ["SOURCE_REV", "THIRD-PARTY-NOTICES"],
    }
    assert result["admission_class"] == "candidate_attributed_downstream"


def test_census_keeps_github_forks_in_reference_class(tmp_path: Path) -> None:
    module = load_script("proof_weighted_repo_census")
    (tmp_path / "README.md").write_text("# Fork\n", encoding="utf-8")

    result = module.build_result(
        repo="GlacierEQ/forked",
        root=tmp_path,
        metadata={"visibility": "public", "fork": True},
        timeout=10,
    )

    assert result["provenance"] == {
        "state": "GITHUB_FORK",
        "markers": ["metadata.fork=true"],
    }
    assert result["admission_class"] == "supporting_reference_fork"
