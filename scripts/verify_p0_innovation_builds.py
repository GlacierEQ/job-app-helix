#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from job_app_helix.p0_builds import P0_IDS, verify_reference_builds

ROOT = Path(__file__).resolve().parents[1]
QUEUE = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "company_innovation_execution_queue.v1.json"
)
IMPLEMENTATION = ROOT / "src" / "job_app_helix" / "p0_builds.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue_ids = tuple(item["company_id"] for item in queue["queue"])
    if queue_ids != P0_IDS:
        raise SystemExit("P0 queue/build registry mismatch")

    verification = verify_reference_builds()
    if verification["status"] != "PASS" or verification["verified_count"] != 25:
        raise SystemExit(f"P0 reference build verification failed: {verification}")

    receipt = {
        "schema": "glaciereq.p0-innovation-build-verification.v1",
        "source_commit": os.environ.get("GITHUB_SHA", "LOCAL"),
        "queue_path": str(QUEUE.relative_to(ROOT)),
        "queue_sha256": sha256(QUEUE),
        "implementation_path": str(IMPLEMENTATION.relative_to(ROOT)),
        "implementation_sha256": sha256(IMPLEMENTATION),
        "expected_count": 25,
        "verified_count": 25,
        "status": "PASS",
        "checks": verification["checks"],
        "truth_boundary": {
            "reference_build_is_not_company_deployment": True,
            "reference_build_is_not_company_affiliation": True,
            "successful_build_does_not_equal_promotion_ready": True,
            "promotion_still_requires_measurement_and_adversarial_review": True,
        },
    }
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
