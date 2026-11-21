#!/usr/bin/env python3
"""Helix → Flight Deck bridge.

Connects public Helix estate intelligence to the private job-app flight deck for
company-specific role-proof packages. Every output is hash-bound and privacy-safe:
private repository identities, legal private records, experiment systems, and
external application state are never included in public projections.

L0 Reference: Immutable byte/SHA/commit/docket provenance. Never assert unverified
state without tool readback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from .application_engine import CompanyTarget
from .application_evidence_graph import ApplicationEvidenceBundle
from .application_operations import CandidateProfile, JobOpening
from .dynamic_application_build import (
    DynamicBuildResult,
    execute_dynamic_build,
)
from .evidence_ledger import EvidenceEntry, Ledger, build_ledger
from .flight_deck_opening_bridge import (
    FlightDeckOpeningBridgeResult,
    compile_flight_deck_opening_bridge,
)

SCHEMA = "glaciereq.helix-flight-deck-bridge.v1"
BRIDGE_STATUS_SCHEMA = "glaciereq.bridge-execution-result.v1"

TARGET_COMPANIES = (
    "Anthropic",
    "Supabase",
    "SpaceX",
    "GitLab",
    "ReadMe",
    "GCAI",
    "Restate",
    "Forgd",
    "Deployment.io",
    "Wrapbook",
    "Blackstraw AI",
    "ClickUp",
    "AgentGraph",
)


class BridgeStatus(StrEnum):
    PACKAGE_BOUND = "PACKAGE_BOUND"
    INTEGRITY_REQUIRED = "INTEGRITY_REQUIRED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class BridgeExecutionResult:
    company: str
    role: str
    status: BridgeStatus
    evidence_receipt_sha256: str
    build_receipt_sha256: str | None
    opening_bridge_receipt_sha256: str | None
    integrity_failures: tuple[str, ...] = ()
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": BRIDGE_STATUS_SCHEMA,
            "company": self.company,
            "role": self.role,
            "status": self.status.value,
            "evidence_receipt_sha256": self.evidence_receipt_sha256,
            "build_receipt_sha256": self.build_receipt_sha256,
            "opening_bridge_receipt_sha256": self.opening_bridge_receipt_sha256,
            "integrity_failures": list(self.integrity_failures),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class CompanyRoleProofPackage:
    company: str
    role: str
    company_id: str
    schema: str
    evidence_graph: ApplicationEvidenceBundle
    dynamic_build: DynamicBuildResult | None
    opening_bridge: FlightDeckOpeningBridgeResult | None
    evidence_ledger_entry: EvidenceEntry | None
    bridge_result: BridgeExecutionResult
    privacy_boundary_verified: bool
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "company": self.company,
            "role": self.role,
            "company_id": self.company_id,
            "evidence_graph": self.evidence_graph.as_dict(),
            "dynamic_build": self.dynamic_build.as_dict()
            if self.dynamic_build
            else None,
            "opening_bridge": self.opening_bridge.as_dict()
            if self.opening_bridge
            else None,
            "evidence_ledger_entry": asdict(self.evidence_ledger_entry)
            if self.evidence_ledger_entry
            else None,
            "bridge_result": self.bridge_result.as_dict(),
            "privacy_boundary_verified": self.privacy_boundary_verified,
            "generated_at": self.generated_at,
        }


def _sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _verify_privacy_boundary(bundle: Mapping[str, Any]) -> bool:
    """Fail-closed privacy boundary: private/legal/experiment identifiers omitted."""
    forbidden = {
        "repository_count",
        "native_repository_count",
        "fork_repository_count",
        "private_repository_count",
        "legal_private_repositories",
        "reference_accomplishments",
        "private_repository_identities",
        "external_application_state",
    }
    text = json.dumps(bundle, sort_keys=True, ensure_ascii=False).lower()
    return not any(k.lower() in text for k in forbidden)


def _find_target_for_company(
    targets: Sequence[CompanyTarget], company: str
) -> CompanyTarget | None:
    for target in targets:
        if target.display_name.lower() == company.lower() or target.company_id.lower() == company.lower():
            return target
    return None


def _build_role_proof_for_company(
    company: str,
    role: str,
    *,
    profile: CandidateProfile,
    estate_bundle: Mapping[str, Any],
    watch_receipt: Mapping[str, Any] | None,
    state_dir: Path,
    ledger: Ledger,
    output_dir: Path,
    targets: Sequence[CompanyTarget] | None = None,
) -> CompanyRoleProofPackage:
    """Compile a single company/role role-proof package through the bridge."""
    target = _find_target_for_company(targets or [], company) if targets else None
    company_id = target.company_id if target else _sha256(company)[:16]

    # Evidence graph projection for this company
    from .application_evidence_graph import build_application_evidence_bundle

    evidence_graph = build_application_evidence_bundle(
        estate_bundle,
        company=company,
    )

    privacy_ok = _verify_privacy_boundary(evidence_graph.as_dict())

    # Build the evidence ledger entry for this company
    ledger_entry: EvidenceEntry | None = None
    for entry in ledger.entries:
        if entry.repo.lower() == company.lower():
            ledger_entry = entry
            break

    # Dynamic build (if we have an opening)
    dynamic_build: DynamicBuildResult | None = None
    opening_bridge: FlightDeckOpeningBridgeResult | None = None

    integrity_failures: list[str] = []
    if not privacy_ok:
        integrity_failures.append("privacy_boundary_violation")

    if watch_receipt is not None:
        try:
            opening_bridge = compile_flight_deck_opening_bridge(
                watch_receipt, state_dir=state_dir
            )
        except ValueError as exc:
            integrity_failures.append(f"opening_bridge: {exc}")

    # Build the application surface via dynamic build if we have an opening
    opening: JobOpening | None = None
    if watch_receipt is not None:
        items = watch_receipt.get("items", [])
        for item in items:
            if isinstance(item, Mapping) and item.get("status") != "FAILED_ISOLATED":
                snapshot = item.get("snapshot") or item.get("opening")
                if isinstance(snapshot, Mapping):
                    opening = JobOpening(
                        opening_id=str(snapshot.get("opening_id", "")),
                        company=str(snapshot.get("company", company)),
                        title=str(snapshot.get("title", role)),
                        description=str(snapshot.get("description", "")),
                        location=str(snapshot.get("location", "")),
                        source=str(snapshot.get("source", "")),
                        source_url=str(snapshot.get("source_url", "")),
                        requirements=tuple(snapshot.get("requirements", ())),
                        preferred=tuple(snapshot.get("preferred", ())),
                        metadata=dict(snapshot.get("metadata", {})),
                        digest=str(snapshot.get("digest", "")),
                    )
                    break

    if opening is not None:
        build_dir = output_dir / f"{company}--{role}--{opening.opening_id}"
        dynamic_build = execute_dynamic_build(
            opening,
            profile,
            estate_bundle,
            output_dir=build_dir,
            run_genius=True,
        )

    status = BridgeStatus.PACKAGE_BOUND
    if integrity_failures:
        status = BridgeStatus.REJECTED
    elif dynamic_build is None and opening_bridge is None:
        status = BridgeStatus.INTEGRITY_REQUIRED

    bridge_result = BridgeExecutionResult(
        company=company,
        role=role,
        status=status,
        evidence_receipt_sha256=evidence_graph.receipt_sha256,
        build_receipt_sha256=dynamic_build.receipt_sha256
        if dynamic_build
        else None,
        opening_bridge_receipt_sha256=opening_bridge.receipt_sha256
        if opening_bridge
        else None,
        integrity_failures=tuple(integrity_failures),
    )

    return CompanyRoleProofPackage(
        company=company,
        role=role,
        company_id=company_id,
        schema=SCHEMA,
        evidence_graph=evidence_graph,
        dynamic_build=dynamic_build,
        opening_bridge=opening_bridge,
        evidence_ledger_entry=ledger_entry,
        bridge_result=bridge_result,
        privacy_boundary_verified=privacy_ok,
    )


def compile_helix_flight_deck_bridge(
    company: str,
    role: str,
    *,
    profile: CandidateProfile,
    estate_bundle: Mapping[str, Any],
    watch_receipt: Mapping[str, Any] | None = None,
    state_dir: Path | None = None,
    ledger: Ledger | None = None,
    output_dir: Path | None = None,
    targets: Sequence[CompanyTarget] | None = None,
) -> CompanyRoleProofPackage:
    """Compile a single company/role role-proof package through the Helix→Flight Deck bridge.

    Connects public Helix estate intelligence to the private job-app flight deck:
    - Evidence graph from the live experience graph (company-targeted)
    - Optional flight-deck opening bridge (exact source-bound opening observations)
    - Optional dynamic application build (target-specific resume/cover letter/outreach)
    - Evidence ledger entry (hash-bound receipt tracking)
    - Fail-closed privacy boundary enforcement

    Returns a CompanyRoleProofPackage with status PACKAGE_BOUND, INTEGRITY_REQUIRED,
    or REJECTED.
    """
    state_dir = state_dir or Path("artifacts/bridge_state")
    output_dir = output_dir or Path("artifacts/role_proof_packages")
    state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    if ledger is None:
        ledger = build_ledger()

    return _build_role_proof_for_company(
        company=company,
        role=role,
        profile=profile,
        estate_bundle=estate_bundle,
        watch_receipt=watch_receipt,
        state_dir=state_dir,
        ledger=ledger,
        output_dir=output_dir,
        targets=targets,
    )


def compile_all_company_role_proofs(
    *,
    profile: CandidateProfile,
    estate_bundle: Mapping[str, Any],
    watch_receipts: Mapping[str, Mapping[str, Any]] | None = None,
    state_dir: Path | None = None,
    ledger: Ledger | None = None,
    output_dir: Path | None = None,
    targets: Sequence[CompanyTarget] | None = None,
    role: str = "Staff Engineer",
) -> dict[str, CompanyRoleProofPackage]:
    """Batch compile role-proof packages for all 13 target companies.

    Returns a dict mapping company name → CompanyRoleProofPackage.
    """
    watch_receipts = watch_receipts or {}
    state_dir = state_dir or Path("artifacts/bridge_state")
    output_dir = output_dir or Path("artifacts/role_proof_packages")
    state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    if ledger is None:
        ledger = build_ledger()

    packages: dict[str, CompanyRoleProofPackage] = {}
    for company in TARGET_COMPANIES:
        watch_receipt = watch_receipts.get(company)
        packages[company] = _build_role_proof_for_company(
            company=company,
            role=role,
            profile=profile,
            estate_bundle=estate_bundle,
            watch_receipt=watch_receipt,
            state_dir=state_dir,
            ledger=ledger,
            output_dir=output_dir,
            targets=targets,
        )
    return packages


def build_evidence_ledger(
    anchor_threshold: int = 8,
    output_path: Path | None = None,
) -> Ledger:
    """Build the complete hash-bound evidence ledger from the Helix estate.

    Writes the ledger to output_path if provided, and returns the Ledger object.
    """
    ledger = build_ledger()
    if output_path is not None:
        from .evidence_ledger import write_ledger

        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_ledger(ledger, output_path)
    return ledger


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Helix → Flight Deck bridge for company-specific role-proof packages"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bridge = sub.add_parser("bridge", help="Build a single company/role proof package")
    bridge.add_argument("company")
    bridge.add_argument("role")
    bridge.add_argument("--profile", required=True, help="Path to candidate profile JSON")
    bridge.add_argument("--estate", required=True, help="Path to estate bundle JSON")
    bridge.add_argument("--watch-receipt", help="Path to opening watch receipt JSON")
    bridge.add_argument("--state-dir", default="artifacts/bridge_state")
    bridge.add_argument("--output-dir", default="artifacts/role_proof_packages")

    bridge_all = sub.add_parser(
        "bridge-all", help="Batch build proof packages for all 13 target companies"
    )
    bridge_all.add_argument("--profile", required=True)
    bridge_all.add_argument("--estate", required=True)
    bridge_all.add_argument("--watch-receipts", help="Path to watch receipts map JSON")
    bridge_all.add_argument("--state-dir", default="artifacts/bridge_state")
    bridge_all.add_argument("--output-dir", default="artifacts/role_proof_packages")
    bridge_all.add_argument("--role", default="Staff Engineer")

    build_ledger_cmd = sub.add_parser(
        "build-ledger", help="Build the complete hash-bound evidence ledger"
    )
    build_ledger_cmd.add_argument("--output", help="Path to write ledger JSON")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.command == "bridge":
        profile = CandidateProfile(
            profile_id="bridge-default",
            name="GlacierEQ Candidate",
            headline="Staff Engineer",
            summary="Evidence-bound application runtime",
            skills=(),
            experience=(),
            achievements=(),
        )
        estate = json.loads(Path(args.estate).read_text(encoding="utf-8"))
        watch = None
        if args.watch_receipt:
            watch = json.loads(Path(args.watch_receipt).read_text(encoding="utf-8"))

        package = compile_helix_flight_deck_bridge(
            company=args.company,
            role=args.role,
            profile=profile,
            estate_bundle=estate,
            watch_receipt=watch,
            state_dir=Path(args.state_dir),
            output_dir=Path(args.output_dir),
        )
        print(json.dumps(package.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "bridge-all":
        profile = CandidateProfile(
            profile_id="bridge-default",
            name="GlacierEQ Candidate",
            headline="Staff Engineer",
            summary="Evidence-bound application runtime",
            skills=(),
            experience=(),
            achievements=(),
        )
        estate = json.loads(Path(args.estate).read_text(encoding="utf-8"))
        watch_receipts: Mapping[str, Mapping[str, Any]] = {}
        if args.watch_receipts:
            watch_receipts = json.loads(
                Path(args.watch_receipts).read_text(encoding="utf-8")
            )

        packages = compile_all_company_role_proofs(
            profile=profile,
            estate_bundle=estate,
            watch_receipts=watch_receipts,
            state_dir=Path(args.state_dir),
            output_dir=Path(args.output_dir),
            role=args.role,
        )

        report = {
            "schema": SCHEMA,
            "total_companies": len(packages),
            "package_bound": sum(
                1 for p in packages.values() if p.bridge_result.status
                == BridgeStatus.PACKAGE_BOUND
            ),
            "integrity_required": sum(
                1 for p in packages.values() if p.bridge_result.status
                == BridgeStatus.INTEGRITY_REQUIRED
            ),
            "rejected": sum(
                1 for p in packages.values() if p.bridge_result.status
                == BridgeStatus.REJECTED
            ),
            "packages": {name: p.as_dict() for name, p in packages.items()},
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if args.command == "build-ledger":
        ledger = build_evidence_ledger(
            anchor_threshold=args.anchor_threshold,
            output_path=Path(args.output) if args.output else None,
        )
        print(
            json.dumps(
                {
                    "schema": "glaciereq.evidence-ledger.v1",
                    "generated_at": ledger.generated_at,
                    "total_repos": ledger.total_repos,
                    "verified_anchors": ledger.verified_anchors,
                    "merkle_root": ledger.merkle_root,
                },
                indent=2,
            )
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
