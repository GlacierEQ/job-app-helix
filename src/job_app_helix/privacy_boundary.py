"""Fail-closed boundary checks for recruiter-facing artifacts."""

from __future__ import annotations

from dataclasses import dataclass

PRIVATE_OPERATION_MARKERS = (
    "application submitted",
    "application status",
    "interview scheduled",
    "recruiter contact",
    "candidate contact",
    "private external receipt",
)


@dataclass(frozen=True)
class BoundaryFinding:
    kind: str
    marker: str


def scan_public_projection(text: str) -> list[BoundaryFinding]:
    """Detect private application operations in a proposed public projection."""
    lowered = text.casefold()
    return [
        BoundaryFinding("PRIVATE_APPLICATION_OPERATION", marker)
        for marker in PRIVATE_OPERATION_MARKERS
        if marker in lowered
    ]


def assert_public_projection_safe(text: str) -> None:
    """Reject operational application state from the public evidence surface."""
    findings = scan_public_projection(text)
    if findings:
        markers = ", ".join(finding.marker for finding in findings)
        raise ValueError(f"public projection contains private operations: {markers}")
