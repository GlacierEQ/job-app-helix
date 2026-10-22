from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_innovation_expansion_preserves_promoted_targets_without_duplicate_ownership() -> None:
    shard = json.loads(
        (
            ROOT
            / "manifests"
            / "company_dossiers"
            / "innovation_expansion_2026_08_09.json"
        ).read_text(encoding="utf-8")
    )

    active = {
        item["company_id"]
        for item in shard["companies"]
    }
    promoted = set(shard["promoted_elsewhere"])

    assert "harvey" in promoted
    assert "harvey" not in active
    assert active.isdisjoint(promoted)
    assert len(active) + len(promoted) == 90
