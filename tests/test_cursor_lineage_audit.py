import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "manifests" / "application_intelligence" / "cursor_lineage_audit.json"
DOSSIER = ROOT / "manifests" / "company_dossiers" / "expansion_targets.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_cursor_lineage_excludes_verified_upstream_forks_from_authorship() -> None:
    audit = _load(AUDIT)
    rows = {row["repository"]: row for row in audit["repositories"]}

    assert rows["GlacierEQ/cursor"]["github_fork"] is True
    assert rows["GlacierEQ/cursor"]["parent"] == "cursor/cursor"
    assert rows["GlacierEQ/cursor"]["classification"] == "UPSTREAM"
    assert rows["GlacierEQ/cursor"]["recruiter_admission"] is False

    assert rows["GlacierEQ/cursor-vip"]["github_fork"] is True
    assert rows["GlacierEQ/cursor-vip"]["parent"] == "kingparks/cursor-vip"
    assert rows["GlacierEQ/cursor-vip"]["classification"] == "UPSTREAM"
    assert rows["GlacierEQ/cursor-vip"]["recruiter_admission"] is False


def test_cursor_nonfork_reference_remains_provenance_unresolved() -> None:
    audit = _load(AUDIT)
    rows = {row["repository"]: row for row in audit["repositories"]}
    row = rows["GlacierEQ/awesome-cursorrules"]

    assert row["github_fork"] is False
    assert row["homepage"] == "https://github.com/PatrickJS/awesome-cursorrules"
    assert row["classification"] == "UPSTREAM_SHAPED_PROVENANCE_UNRESOLVED"
    assert row["recruiter_admission"] is False
    assert audit["truth_boundary"]["current_recruiter_ready_direct_repositories"] == 0


def test_cursor_dossier_matches_lineage_decision() -> None:
    dossier = _load(DOSSIER)
    cursor = next(
        (row for row in dossier["companies"] if row["company_id"] == "cursor"),
        None,
    )
    assert cursor is not None, "Cursor company not found in expansion_targets.json"

    repos = {row[0]: row for row in cursor["repositories"]}
    for repo_name, repo_data in repos.items():
        assert len(repo_data) >= 6, (
            f"Repository {repo_name} has insufficient fields: "
            f"expected at least 6, got {len(repo_data)}"
        )

    assert cursor["track_state"] == "DIRECT_ESTATE_DISCOVERED_PROVENANCE_AUDIT"
    assert repos["GlacierEQ/cursor"][2] == "EXCLUDED_AUTHORSHIP"
    assert repos["GlacierEQ/cursor"][5] == "UPSTREAM"
    assert repos["GlacierEQ/cursor-vip"][2] == "EXCLUDED_AUTHORSHIP"
    assert repos["GlacierEQ/cursor-vip"][5] == "UPSTREAM"
    assert repos["GlacierEQ/awesome-cursorrules"][2] == "AUDIT_UPSTREAM_DELTA"
    assert repos["GlacierEQ/awesome-cursorrules"][5] == "UPSTREAM_SHAPED"
