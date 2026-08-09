from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "site" / "capability_proof_lens.js"


def test_role_match_is_scoped_to_selected_depth_systems() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "routeCapabilities = (company, role, systemIds)" in script
    assert "!systemIds.has(row.system_id)" in script
    assert "routeCapabilities(company, role, systemIds)" in script
    assert "profile_capabilities.forEach" not in script


def test_evidence_link_path_is_normalized_before_url_construction() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "safeEvidencePath" in script
    assert 'ref.replaceAll("\\\\", "/")' in script
    assert 'segment === ".."' in script
    assert "segments.map(encodeURIComponent)" in script


def test_route_summary_counts_distinct_exact_head_receipts() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "const distinctReceipts = new Set()" in script
    assert "`${proof.source_repository}|${proof.head_sha}|${receipt.id}`" in script
    assert "const receiptCount = distinctReceipts.size" in script
