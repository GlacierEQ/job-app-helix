#!/usr/bin/env python3
"""Reject private candidate application operations on public Helix surfaces.

This check does not purport to verify provider receipt authenticity or duplicate-
submission state; those are exclusively private job-app runtime responsibilities.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIRS = (
    "evidence/applications",
    "hire_package/casey-barton/applications",
)
PUBLIC_JSON_ROOTS = (
    "evidence",
    "manifests",
    "artifacts/pages-site",
    "hire_package/casey-barton",
    "solidify_records",
)
PRIVATE_RECEIPT_SCHEMA = "glaciereq.external-application-receipt.v1"
PUBLIC_QUEUE = "hire_package/casey-barton/AI_ARCHITECT_PROMOTION_QUEUE.md"
PRIVATE_QUEUE_MARKERS = re.compile(
    r"\b(?:post[- ]submission|application_received|submitted_received|"
    r"duplicate[- ]submission|do[- _]?not[- _]?resubmit|provider_acknowledgement|"
    r"receipt_displayed_recipient)\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    flags=re.IGNORECASE,
)


def _contains_provider_operations(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("schema") == PRIVATE_RECEIPT_SCHEMA:
            return True
        if "receipt_observation" in value:
            return True
        if "provider_acknowledgement" in value and (
            "application_state" in value or "lifecycle_state" in value
        ):
            return True
        return any(_contains_provider_operations(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_provider_operations(child) for child in value)
    return False


def violations(root: Path = ROOT) -> list[str]:
    """Return source-relative privacy violations; never display sensitive contents."""
    root = Path(root)
    failures: list[str] = []
    seen: set[Path] = set()
    for relative in PRIVATE_DIRS:
        protected = root / relative
        if protected.is_file():
            failures.append(f"private application path committed publicly: {relative}")
        elif protected.is_dir():
            for path in sorted(p for p in protected.rglob("*") if p.is_file()):
                failures.append(f"private application path committed publicly: {path.relative_to(root).as_posix()}")
                seen.add(path)
    public_queue = root / PUBLIC_QUEUE
    if public_queue.is_file():
        try:
            queue_text = public_queue.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            failures.append(f"public promotion queue could not be verified: {PUBLIC_QUEUE}")
        else:
            if PRIVATE_QUEUE_MARKERS.search(queue_text):
                failures.append(f"private applicant tracking inside public promotion queue: {PUBLIC_QUEUE}")
    for relative in PUBLIC_JSON_ROOTS:
        directory = root / relative
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            if path in seen or not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeError, OSError, json.JSONDecodeError):
                # General JSON-format validation is delegated to normal repository checks.
                continue
            if _contains_provider_operations(payload):
                failures.append(f"private provider-operation state in public JSON: {path.relative_to(root).as_posix()}")
    return failures


def main() -> int:
    errors = violations()
    if errors:
        for error in errors:
            print("PUBLIC APPLICATION PRIVACY FAIL: " + error)
        return 1
    print("PUBLIC APPLICATION PRIVACY PASS: private operations absent from guarded public surfaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
