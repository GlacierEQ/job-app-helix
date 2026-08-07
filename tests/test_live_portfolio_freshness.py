from __future__ import annotations

from importlib import util
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audit_live_portfolio_freshness.py"
)
spec = util.spec_from_file_location("audit_live_portfolio_freshness", SCRIPT)
assert spec and spec.loader
module = util.module_from_spec(spec)
spec.loader.exec_module(module)


def portfolio(*, evidence_head: str | None = None):
    evidence = {}
    if evidence_head is not None:
        evidence["GlacierEQ/public-system"] = {
            "repository": "GlacierEQ/public-system",
            "observed_head_sha": evidence_head,
            "state": "VERIFIED",
        }
    return {
        "inventory_total": 3,
        "inventory_repositories": {
            "GlacierEQ/public-system",
            "GlacierEQ/private-system",
        },
        "company_ids": {"example"},
        "declarations": {
            "GlacierEQ/public-system": [
                {
                    "company_id": "example",
                    "level": "L4",
                    "promotion_state": "PROMOTED",
                    "visibility": "public",
                    "inventory_scope": "HELIX_ADMITTED",
                    "provenance_state": "ORIGINAL_CANDIDATE",
                }
            ],
            "GlacierEQ/private-system": [
                {
                    "company_id": "example",
                    "level": "L2",
                    "promotion_state": "PRIVATE_REFERENCE",
                    "visibility": "private",
                    "inventory_scope": "HELIX_ADMITTED",
                    "provenance_state": "ORIGINAL_CANDIDATE",
                }
            ],
        },
        "flagships": [
            {
                "system_id": "public",
                "repository": "GlacierEQ/public-system",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
            },
            {
                "system_id": "private",
                "repository": "GlacierEQ/private-system",
                "state": "PRIVATE_REFERENCE",
                "public_surface": "SANITIZED_CARD_ONLY",
            },
        ],
        "evidence_by_repository": evidence,
        "all_repositories": [
            "GlacierEQ/private-system",
            "GlacierEQ/public-system",
        ],
    }


def getter(
    *,
    public_visibility: str = "public",
    public_head: str = "abc",
    private_unobservable: bool = True,
):
    def get(path: str):
        if path == "/repos/GlacierEQ/public-system":
            return {
                "private": public_visibility == "private",
                "archived": False,
                "fork": False,
                "default_branch": "main",
                "html_url": "https://github.com/GlacierEQ/public-system",
                "pushed_at": "2026-08-07T00:00:00Z",
            }
        if path == "/repos/GlacierEQ/public-system/commits/main":
            return {"sha": public_head}
        if path == "/repos/GlacierEQ/private-system":
            if private_unobservable:
                return {"_unobservable": True, "_http_status": 404}
            return {
                "private": True,
                "archived": False,
                "fork": False,
                "default_branch": "main",
                "html_url": "https://github.com/GlacierEQ/private-system",
                "pushed_at": "2026-08-07T00:00:00Z",
            }
        raise AssertionError(path)

    return get


def finding_codes(receipt):
    return [row["code"] for row in receipt["findings"]]


def test_scoped_private_404_is_not_treated_as_missing_repository():
    with patch.object(
        module,
        "compile_portfolio",
        return_value=portfolio(evidence_head="abc"),
    ):
        receipt = module.audit(getter(private_unobservable=True), "FIXTURE")
    assert "PRIVATE_OR_SCOPED_REPOSITORY_UNOBSERVABLE" in finding_codes(
        receipt
    )
    assert "DECLARED_PUBLIC_REPOSITORY_UNOBSERVABLE" not in finding_codes(
        receipt
    )
    assert receipt["freshness"]["declared_visibility_matches_live"] is True


def test_declared_public_visibility_mismatch_is_an_error():
    with patch.object(
        module,
        "compile_portfolio",
        return_value=portfolio(evidence_head="abc"),
    ):
        receipt = module.audit(
            getter(
                public_visibility="private",
                private_unobservable=False,
            ),
            "FIXTURE",
        )
    assert "LIVE_VISIBILITY_MISMATCH" in finding_codes(receipt)
    assert "AMBIGUOUS_PUBLIC_SURFACE_PRIVATE_SOURCE" in finding_codes(
        receipt
    )
    assert receipt["freshness"]["declared_visibility_matches_live"] is False


def test_missing_live_evidence_is_visible_without_fabricating_failure():
    with patch.object(
        module,
        "compile_portfolio",
        return_value=portfolio(evidence_head=None),
    ):
        receipt = module.audit(getter(), "FIXTURE")
    assert "MISSING_FLAGSHIP_LIVE_EVIDENCE" in finding_codes(receipt)
    assert receipt["portfolio"]["recruiter_eligible_missing_live_evidence"] == 1
    assert receipt["freshness"]["all_flagship_evidence_current"] is False


def test_stale_live_evidence_is_an_error():
    with patch.object(
        module,
        "compile_portfolio",
        return_value=portfolio(evidence_head="old"),
    ):
        receipt = module.audit(getter(public_head="new"), "FIXTURE")
    assert "STALE_FLAGSHIP_LIVE_EVIDENCE" in finding_codes(receipt)
    flagship = next(
        row for row in receipt["flagships"] if row["system_id"] == "public"
    )
    assert flagship["evidence_head"] == "old"
    assert flagship["current_head"] == "new"
    assert flagship["head_matches"] is False


def test_current_evidence_and_public_visibility_can_be_clean():
    with patch.object(
        module,
        "compile_portfolio",
        return_value=portfolio(evidence_head="abc"),
    ):
        receipt = module.audit(getter(public_head="abc"), "FIXTURE")
    errors = [
        row for row in receipt["findings"] if row["severity"] == "ERROR"
    ]
    assert not errors
    assert receipt["freshness"]["all_flagship_evidence_current"] is True
    assert receipt["freshness"]["declared_visibility_matches_live"] is True
