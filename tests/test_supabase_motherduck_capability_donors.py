import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DONORS = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "supabase_motherduck_capability_donors.json"
)
DOSSIER = ROOT / "manifests" / "company_dossiers" / "expansion_targets.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _company(dossier: dict, company_id: str) -> dict:
    matches = [row for row in dossier["companies"] if row["company_id"] == company_id]
    assert len(matches) == 1, f"expected one company {company_id!r}, found {len(matches)}"
    return matches[0]


def _capability(donors: dict, capability_id: str) -> dict:
    matches = [
        row for row in donors["capabilities"] if row["capability_id"] == capability_id
    ]
    assert len(matches) == 1, (
        f"expected one capability {capability_id!r}, found {len(matches)}"
    )
    return matches[0]


def _assert_projection_is_canonical(
    donors: dict,
    dossier_company: dict,
    company_id: str,
) -> None:
    projection = donors["company_projection"][company_id]
    canonical = {
        row["capability_id"]: row
        for row in donors["capabilities"]
        if row["company_id"] == company_id
    }
    assert canonical

    dossier_ids = {row[1] for row in dossier_company["capability_donors"]}
    dossier_repos = {row[0] for row in dossier_company["capability_donors"]}
    projected_ids = set(projection["capability_ids"])
    projected_repos = set(projection["donor_repositories"])
    canonical_repos = {row["donor_repository"] for row in canonical.values()}

    assert projected_ids == dossier_ids == set(canonical)
    assert projected_repos == dossier_repos == canonical_repos
    assert projected_repos <= set(donors["donor_systems"])
    assert all(row[3] == "REFERENCE_ONLY" for row in dossier_company["capability_donors"])


def test_private_and_legal_lineage_sources_never_become_donor_systems() -> None:
    donors = _load(DONORS)
    dossier = _load(DOSSIER)
    donor_repos = set(donors["donor_systems"])

    truth = donors["truth_boundary"]
    assert truth["private_or_legal_lineage_sources_are_read_only_inputs"] is True
    assert truth["private_or_legal_lineage_sources_are_never_capability_donors"] is True
    assert truth["no_private_code_or_data_is_copied"] is True
    assert truth["blocked_repository_cannot_be_recruiter_capability_donor"] is True

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

    for donor in donor_systems.values():
        assert donor["visibility"] == "public"
        assert donor["fork"] is False
        assert re.fullmatch(r"[0-9a-f]{40}", donor["head_sha"])
        assert "VERIFIED" in donor["proof_state"]

        inventory = donor["evidence_inventory"]
        assert isinstance(inventory, list) and inventory
        inventory_paths = set()
        for evidence in inventory:
            assert isinstance(evidence, dict)
            assert isinstance(evidence.get("path"), str) and evidence["path"].strip()
            assert re.fullmatch(r"[0-9a-f]{40}", evidence["blob_sha"])
            inventory_paths.add(evidence["path"])
        assert len(inventory_paths) == len(inventory)

        receipts = donor["proof_receipts"]
        assert isinstance(receipts, list) and receipts
        for receipt in receipts:
            assert receipt["kind"] == "check_run"
            assert isinstance(receipt["id"], int) and receipt["id"] > 0
            assert receipt["head_sha"] == donor["head_sha"]
            assert receipt["conclusion"] == "success"
            assert isinstance(receipt["name"], str) and receipt["name"].strip()

    for capability in donors["capabilities"]:
        capability_id = capability["capability_id"]
        capability_ids.add(capability_id)
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", capability_id)
        assert capability["donor_repository"] in donor_systems
        donor = donor_systems[capability["donor_repository"]]
        assert capability["head_sha"] == donor["head_sha"]

        evidence_refs = capability["evidence_refs"]
        assert isinstance(evidence_refs, list) and evidence_refs
        assert all(isinstance(ref, str) and ref.strip() for ref in evidence_refs)
        inventory_paths = {row["path"] for row in donor["evidence_inventory"]}
        assert set(evidence_refs) <= inventory_paths
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
    _assert_projection_is_canonical(donors, supabase, "supabase")

    private_refs = {
        row[0] for row in supabase["repositories"] if row[2] == "PRIVATE_REFERENCE"
    }
    assert private_refs.isdisjoint(projection["donor_repositories"])


def test_motherduck_projection_preserves_no_deployment_boundary() -> None:
    donors = _load(DONORS)
    dossier = _load(DOSSIER)
    motherduck = _company(dossier, "motherduck")
    projection = donors["company_projection"]["motherduck"]

    expected_state = "SEMANTIC_CAPABILITY_DONORS_ADMITTED_WITH_DEPLOYMENT_BOUNDARY"
    assert motherduck["track_state"] == expected_state
    assert projection["state"] == expected_state
    assert projection["affiliation_claim"] is False
    assert projection["deployment_claim"] is False
    _assert_projection_is_canonical(donors, motherduck, "motherduck")

    private_refs = {
        row[0]
        for row in motherduck["repositories"]
        if row[2] == "PRIVATE_REFERENCE"
    }
    assert private_refs.isdisjoint(projection["donor_repositories"])
    assert set(projection["donor_repositories"]) == {"GlacierEQ/colossus-gateway"}
    assert set(projection["capability_ids"]) == {
        "motherduck-query-facade",
        "motherduck-structured-health-telemetry",
    }


def test_blocked_xai_mechanisms_are_leads_not_admitted_donors() -> None:
    donors = _load(DONORS)
    blocked = donors["blocked_candidate_systems"]["GlacierEQ/xai-colossus-cooling"]
    assert blocked["governing_state"] == "BLOCKED"
    assert blocked["recruiter_admission"] is False
    assert "GlacierEQ/xai-colossus-cooling" not in donors["donor_systems"]
    assert all(
        capability["donor_repository"] != "GlacierEQ/xai-colossus-cooling"
        for capability in donors["capabilities"]
    )


def test_motherduck_gateway_claim_excludes_case_specific_helpers_and_false_fallback() -> None:
    donors = _load(DONORS)
    capability = _capability(donors, "motherduck-query-facade")
    assert capability["donor_repository"] == "GlacierEQ/colossus-gateway"
    assert set(capability["excluded_scope"]) == {
        "createCaseTable",
        "upsertCase",
        "searchDocuments",
    }

    health = _capability(donors, "motherduck-structured-health-telemetry")
    excluded = " ".join(health["excluded_claims"]).casefold()
    assert "no fallback claim" in excluded
    assert "no live service availability" in excluded
