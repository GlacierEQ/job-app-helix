import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPABASE_AUDIT = ROOT / "manifests" / "application_intelligence" / "supabase_lineage_audit.json"
MOTHERDUCK_AUDIT = ROOT / "manifests" / "application_intelligence" / "motherduck_lineage_audit.json"
DOSSIER = ROOT / "manifests" / "company_dossiers" / "expansion_targets.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _company(company_id: str) -> dict:
    dossier = _load(DOSSIER)
    return next(row for row in dossier["companies"] if row["company_id"] == company_id)


def test_supabase_verified_forks_are_excluded_from_authorship() -> None:
    audit = _load(SUPABASE_AUDIT)
    rows = {row["repository"]: row for row in audit["repositories"]}
    expected = {
        "GlacierEQ/supabase": "supabase/supabase",
        "GlacierEQ/supabase-mcp": "supabase/mcp",
        "GlacierEQ/supabase-grafana": "supabase/supabase-grafana",
    }
    for repository, upstream in expected.items():
        row = rows[repository]
        assert row["fork"] is True
        assert row["upstream"] == upstream
        assert row["classification"] == "EXCLUDED_AUTHORSHIP"
        assert row["provenance_state"] == "UPSTREAM"
        assert row["recruiter_admission"] is False


def test_aspen_grove_supabase_stays_private_read_only_reference() -> None:
    audit = _load(SUPABASE_AUDIT)
    row = next(
        row
        for row in audit["repositories"]
        if row["repository"] == "GlacierEQ/aspen-grove-supabase"
    )
    assert row["fork"] is False
    assert row["classification"] == "PRIVATE_REFERENCE"
    assert row["provenance_state"] == "ORIGINAL_CANDIDATE"
    assert row["mutation_policy"] == "READ_ONLY"
    assert row["sensitive_scope"] == "LEGAL_EVIDENCE"
    assert row["recruiter_admission"] is False
    assert audit["recruiter_ready_direct_repositories"] == 0


def test_motherduck_backup_stays_private_read_only_reference() -> None:
    audit = _load(MOTHERDUCK_AUDIT)
    row = audit["repositories"][0]
    assert row["repository"] == "GlacierEQ/Z-BACKUP-apex-motherduck-engine"
    assert row["fork"] is False
    assert row["backup_identity"] is True
    assert row["classification"] == "PRIVATE_REFERENCE"
    assert row["mutation_policy"] == "READ_ONLY"
    assert row["sensitive_scope"] == "LEGAL_EVIDENCE"
    assert row["recruiter_admission"] is False
    assert audit["recruiter_ready_direct_repositories"] == 0


def test_company_dossier_matches_supabase_and_motherduck_lineage() -> None:
    supabase = _company("supabase")
    supabase_repos = {row[0]: row for row in supabase["repositories"]}
    assert supabase["track_state"] == "SEMANTIC_CAPABILITY_DONORS_ADMITTED"
    assert supabase_repos["GlacierEQ/supabase"][2] == "EXCLUDED_AUTHORSHIP"
    assert supabase_repos["GlacierEQ/supabase-mcp"][2] == "EXCLUDED_AUTHORSHIP"
    assert supabase_repos["GlacierEQ/supabase-grafana"][2] == "EXCLUDED_AUTHORSHIP"
    assert supabase_repos["GlacierEQ/aspen-grove-supabase"][2] == "PRIVATE_REFERENCE"

    motherduck = _company("motherduck")
    motherduck_repos = {row[0]: row for row in motherduck["repositories"]}
    expected_state = "SEMANTIC_CAPABILITY_DONORS_ADMITTED_WITH_DEPLOYMENT_BOUNDARY"
    assert motherduck["track_state"] == expected_state
    assert motherduck_repos["GlacierEQ/Z-BACKUP-apex-motherduck-engine"][2] == "PRIVATE_REFERENCE"
    assert motherduck_repos["GlacierEQ/Z-BACKUP-apex-motherduck-engine"][5] == "ORIGINAL_CANDIDATE"
