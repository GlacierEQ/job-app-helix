import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONORS = ROOT / "manifests" / "application_intelligence" / "supabase_motherduck_capability_donors.json"
DOSSIER = ROOT / "manifests" / "company_dossiers" / "expansion_targets.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _company(dossier: dict, company_id: str) -> dict:
    return next(row for row in dossier["companies"] if row["company_id"] == company_id)


def test_private_and_legal_lineage_sources_never_become_donor_systems() -> None:
    donors = _load(DONORS)
    dossier = _load(DOSSIER)
    donor_repos = set(donors["donor_systems"])

    assert donors["truth_boundary"]["private_or_legal_lineage_sources_are_read_only_inputs"] is True
    assert donors["truth_boundary"]["private_or_legal_lineage_sources_are_never_capability_donors"] is True
    assert donors["truth_boundary"]["no_private_code_or_data_is_copied"] is True

    private_reference_repos = {
        repo[0]
        for company in dossier["companies"]
        for repo in company.get("repositories", [])
        if len(repo) >= 3 and repo[2] == "PRIVATE_REFERENCE"
    }
    assert private_reference_repos
    assert private_reference_repos.isdisjoint(donor_repos)


def test_every_admitted_capability_is_public_evidence_bound_and_exact_headed() -> None:
    donors = _load(DONORS)
    donor_systems = donors["donor_systems"]
    capability_ids = set()

    for repo, donor in donor_systems.items():
        assert donor["visibility"] == "public"
        assert donor["fork"] is False
        assert re.fullmatch(r"[0-9a-f]{40}", donor["head_sha"])
        assert donor["proof_state"]

    for capability in donors["capabilities"]:
        capability_id = capability["capability_id"]
        capability_ids.add(capability_id)
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", capability_id)
        assert capability["donor_repository"] in donor_systems
        assert capability["head_sha"] == donor_systems[capability["donor_repository"]]["head_sha"]
        assert capability["evidence_refs"]
        assert capability["mechanism"]
        assert capability["recruiter_safe_claim"]

    assert len(capability_ids) == len(donors["capabilities"])


def test_supabase_company_projection_uses_only_public_semantic_donors() -> None:
    donors = _load(DONORS)
    dossier = _load(DOSSIER)
    supabase = _company(dossier, "supabase")
    projection = donors["company_projection"]["supabase"]

    assert supabase["track_state"] == "SEMANTIC_CAPABILITY_DONORS_ADMITTED"
    assert projection["state"] == supabase["track_state"]
    assert projection["affiliation_claim"] is False

    dossier_ids = {row[1] for row in supabase["capability_donors"]}
    assert dossier_ids == set(projection["capability_ids"])
    assert {row[0] for row in supabase["capability_donors"]} == set(projection["donor_repositories"])

    private_refs = {row[0] for row in supabase["repositories"] if row[2] == "PRIVATE_REFERENCE"}
    assert private_refs.isdisjoint(projection["donor_repositories"])


def test_motherduck_projection_preserves_no_deployment_boundary() -> None:
    donors = _load(DONORS)
    dossier = _load(DOSSIER)
    motherduck = _company(dossier, "motherduck")
    projection = donors["company_projection"]["motherduck"]

    assert motherduck["track_state"] == "SEMANTIC_CAPABILITY_DONORS_ADMITTED_WITH_DEPLOYMENT_BOUNDARY"
    assert projection["state"] == motherduck["track_state"]
    assert projection["affiliation_claim"] is False
    assert projection["deployment_claim"] is False

    dossier_ids = {row[1] for row in motherduck["capability_donors"]}
    assert dossier_ids == set(projection["capability_ids"])
    assert {row[0] for row in motherduck["capability_donors"]} == set(projection["donor_repositories"])

    private_refs = {row[0] for row in motherduck["repositories"] if row[2] == "PRIVATE_REFERENCE"}
    assert private_refs.isdisjoint(projection["donor_repositories"])

    xai_donor = donors["donor_systems"]["GlacierEQ/xai-colossus-cooling"]
    assert xai_donor["proof_state"] == "SOURCE_AND_CORE_CI_VERIFIED_DEPLOYMENT_NOT_CLAIMED"
    assert xai_donor["proof"]["deployment_workflow"].endswith(":failure")


def test_motherduck_gateway_claim_excludes_case_specific_helpers() -> None:
    donors = _load(DONORS)
    capability = next(
        row for row in donors["capabilities"]
        if row["capability_id"] == "motherduck-query-health-facade"
    )
    assert capability["donor_repository"] == "GlacierEQ/colossus-gateway"
    assert set(capability["excluded_scope"]) == {
        "createCaseTable",
        "upsertCase",
        "searchDocuments",
    }
