#!/usr/bin/env python3
"""Fail closed when an acknowledged external application is demoted to READY.

Provider-side state outranks later internal packet generation. Once a receipt records
that an employer received an application, recruiter/application artifacts for the same
provider job ID must carry a no-resubmit guard and must not instruct a second submit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_ROOT = ROOT / "evidence" / "applications"
PACKAGE_ROOT = ROOT / "hire_package" / "casey-barton" / "applications"
PROMOTION_QUEUE = ROOT / "hire_package" / "casey-barton" / "AI_ARCHITECT_PROMOTION_QUEUE.md"

ACKNOWLEDGED_STATES = {"APPLICATION_RECEIVED", "SUBMITTED", "SUBMITTED_RECEIVED"}
PROHIBITED_READY_PATTERNS = (
    re.compile(r"Current application state:\*\*\s*`READY_FOR_MANUAL_SUBMISSION`"),
    re.compile(r"application_state_before:\s*READY_FOR_MANUAL_SUBMISSION"),
    re.compile(r"\bsubmit the current .*package through the provider application surface\b", re.I),
)


class ExternalApplicationReceiptError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalApplicationReceiptError(f"cannot read receipt {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ExternalApplicationReceiptError(f"receipt root must be an object: {path}")
    return payload


def _receipt_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.json"))


def _guarded_receipts(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    guarded: list[tuple[Path, dict[str, Any]]] = []
    for path in _receipt_files(root):
        payload = _load_json(path)
        if payload.get("duplicate_submission_guard") is True:
            guarded.append((path, payload))
    return guarded


def _candidate_text_files(root: Path, provider_job_id: str) -> list[Path]:
    if not root.exists():
        return []
    result: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ExternalApplicationReceiptError(f"cannot read package {path}: {exc}") from exc
        if provider_job_id in text:
            result.append(path)
    return result


def validate(root: Path = ROOT) -> dict[str, Any]:
    receipt_root = root / "evidence" / "applications"
    package_root = root / "hire_package" / "casey-barton" / "applications"
    queue_path = root / "hire_package" / "casey-barton" / "AI_ARCHITECT_PROMOTION_QUEUE.md"

    guarded = _guarded_receipts(receipt_root)
    checked_packages = 0
    guarded_job_ids: list[str] = []

    for receipt_path, receipt in guarded:
        provider_job_id = str(receipt.get("provider_job_id") or "").strip()
        if not provider_job_id:
            raise ExternalApplicationReceiptError(
                f"duplicate-submission guard missing provider_job_id: {receipt_path}"
            )
        application_state = str(receipt.get("application_state") or "").strip()
        lifecycle_state = str(receipt.get("lifecycle_state") or "").strip()
        if application_state not in ACKNOWLEDGED_STATES and lifecycle_state not in ACKNOWLEDGED_STATES:
            raise ExternalApplicationReceiptError(
                f"guarded receipt does not establish acknowledged state: {receipt_path}"
            )
        if receipt.get("resubmission_permitted") is not False:
            raise ExternalApplicationReceiptError(
                f"guarded receipt must set resubmission_permitted=false: {receipt_path}"
            )

        guarded_job_ids.append(provider_job_id)
        package_files = _candidate_text_files(package_root, provider_job_id)
        if not package_files:
            raise ExternalApplicationReceiptError(
                f"guarded job {provider_job_id} has no application record"
            )
        for package_path in package_files:
            text = package_path.read_text(encoding="utf-8")
            checked_packages += 1
            for pattern in PROHIBITED_READY_PATTERNS:
                if pattern.search(text):
                    raise ExternalApplicationReceiptError(
                        f"guarded job {provider_job_id} regressed to submission-ready state in {package_path}"
                    )
            if f"DO_NOT_RESUBMIT_{provider_job_id}" not in text:
                raise ExternalApplicationReceiptError(
                    f"guarded job {provider_job_id} package lacks explicit no-resubmit guard: {package_path}"
                )

        if queue_path.exists():
            queue = queue_path.read_text(encoding="utf-8")
            if provider_job_id in queue:
                for pattern in PROHIBITED_READY_PATTERNS:
                    if pattern.search(queue):
                        raise ExternalApplicationReceiptError(
                            f"guarded job {provider_job_id} has a duplicate-submit instruction in promotion queue"
                        )

    return {
        "schema": "glaciereq.external-application-receipt-integrity.v1",
        "status": "PASS",
        "guarded_receipt_count": len(guarded),
        "guarded_provider_job_ids": sorted(set(guarded_job_ids)),
        "checked_application_records": checked_packages,
        "invariants": {
            "provider_acknowledgement_cannot_be_demoted_to_ready": True,
            "guarded_application_requires_explicit_no_resubmit_marker": True,
            "provider_side_state_outranks_later_internal_readiness_generation": True,
        },
    }


def main() -> int:
    try:
        result = validate()
    except ExternalApplicationReceiptError as exc:
        print(f"external application receipt integrity: FAIL: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
