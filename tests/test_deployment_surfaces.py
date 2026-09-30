from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "deployment_surfaces.json"


def test_public_portfolio_has_bounded_observed_production_receipt() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["schema"] == "glaciereq.deployment-surfaces.v1"
    assert payload["authority"] == "OBSERVED_EXTERNAL_STATE"
    assert len(payload["surfaces"]) == 1

    surface = payload["surfaces"][0]
    assert surface["provider"] == "vercel"
    assert surface["production"]["ready_state"] == "READY"
    assert surface["production"]["aliases"]
    assert surface["runtime_health"] == {
        "window": "24h",
        "error_clusters": 0,
        "state": "NO_RUNTIME_ERRORS_OBSERVED",
    }

    nonclaims = set(surface["claim_boundary"]["this_receipt_does_not_prove"])
    assert "every job-engineering repository is deployed" in nonclaims
    assert (
        "the production surface contains the current unmerged productization branch"
        in nonclaims
    )
