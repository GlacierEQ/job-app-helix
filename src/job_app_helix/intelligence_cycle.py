"""Run the complete attributable job-intelligence-to-application cycle.

This module composes Helix's live opening acquisition, provenance refresh, company-fit,
outcome-calibration, queue ranking, freshness-aware packet lineage, and recruiter-packet
engines into one executable runtime. Company failures are isolated so one bad source
cannot stall unrelated targets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .application_engine import CompanyTarget, find_target, load_targets
from .application_operations import (
    ApplicationStore,
    CandidateProfile,
    JobOpening,
    load_candidate_profile,
    load_job_opening,
)
from .batch_application_execution import DEFAULT_ACTIONABLE_LANES, BatchExecutionResult
from .calibration_diagnostics import CalibrationDiagnostics, diagnose_outcome_calibration
from .calibration_guard import CalibrationGuardDecision, apply_calibration_guard
from .company_fit import CompanyFitAssessment, assess_company_fit
from .company_intelligence import CompanyIntelligence, load_company_intelligence
from .company_intelligence_acquisition import (
    AcquisitionPlan,
    AcquisitionResult,
    Transport,
    acquire_company_intelligence,
    fetch_http_source,
    load_acquisition_plan,
)
from .company_intelligence_refresh import persist_refresh, refresh_company_intelligence
from .freshness_aware_batch import FreshnessAwareBatchResult, compile_freshness_aware_batch
from .opening_acquisition import OpeningFetcher, acquire_live_opening
from .opportunity_queue import QueueCandidate
from .outcome_calibration import (
    OutcomeCalibration,
    fit_outcome_calibration,
    load_outcome_examples,
)


@dataclass(frozen=True)
class IntelligenceCycleCandidate:
    company: str
    acquisition_plan_path: Path
    opening_path: Path | None = None
    opening_url: str | None = None
    current_intelligence_path: Path | None = None
    role: str | None = None


@dataclass(frozen=True)
class CompanyCycleResult:
    company_id: str
    company: str
    opening_id: str
    status: str
    opening_status: str
    opening_receipt_sha256: str | None
    opening_changed_fields: tuple[str, ...]
    acquisition_receipt_sha256: str | None
    refresh_receipt_sha256: str | None
    active_intelligence_sha256: str | None
    company_fit_score: float | None
    fresh_signal_count: int
    state_dir: str
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IntelligenceCycleResult:
    schema: str
    candidate_count: int
    successful_company_count: int
    failed_company_count: int
    calibration: OutcomeCalibration
    calibration_sha256: str
    calibration_diagnostics: CalibrationDiagnostics
    calibration_guard: CalibrationGuardDecision
    companies: tuple[CompanyCycleResult, ...]
    freshness: FreshnessAwareBatchResult
    batch: BatchExecutionResult
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "candidate_count": self.candidate_count,
            "successful_company_count": self.successful_company_count,
            "failed_company_count": self.failed_company_count,
            "calibration": self.calibration.as_dict(),
            "calibration_sha256": self.calibration_sha256,
            "calibration_diagnostics": self.calibration_diagnostics.as_dict(),
            "calibration_guard": self.calibration_guard.as_dict(),
            "companies": [row.as_dict() for row in self.companies],
            "freshness": self.freshness.as_dict(),
            "batch": self.batch.as_dict(),
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _intelligence_sha256(intelligence: CompanyIntelligence) -> str:
    return _canonical_sha256(intelligence.as_dict())


def _persist_initial_intelligence(
    intelligence: CompanyIntelligence,
    *,
    active_path: Path,
    receipt_path: Path,
    acquisition: AcquisitionResult,
) -> str:
    """Persist first-observed state without fabricating a prior snapshot."""
    _write_json(active_path, intelligence.as_dict())
    receipt: dict[str, object] = {
        "schema": "glaciereq.company-intelligence-bootstrap.v1",
        "company_id": intelligence.company_id,
        "company": intelligence.company,
        "collected_at": intelligence.collected_at,
        "active_count": len(intelligence.signals),
        "acquisition_receipt_sha256": acquisition.receipt_sha256,
        "active_intelligence_sha256": _intelligence_sha256(intelligence),
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    _write_json(receipt_path, receipt)
    return str(receipt["receipt_sha256"])


def _resolve_current_intelligence(
    candidate: IntelligenceCycleCandidate,
    active_path: Path,
) -> CompanyIntelligence | None:
    if candidate.current_intelligence_path is not None:
        return load_company_intelligence(candidate.current_intelligence_path)
    if active_path.is_file():
        return load_company_intelligence(active_path)
    return None


def _validate_identity(
    plan: AcquisitionPlan,
    target: CompanyTarget,
    opening: JobOpening,
) -> None:
    if plan.company_id != target.company_id:
        raise ValueError(
            "acquisition company_id does not match target: "
            f"{plan.company_id} != {target.company_id}"
        )
    if opening.company.casefold() != plan.company.casefold():
        raise ValueError(
            "opening company does not match acquisition plan: "
            f"{opening.company!r} != {plan.company!r}"
        )


def _company_paths(root: Path, company_id: str) -> dict[str, Path]:
    company_root = root / "companies" / company_id
    return {
        "root": company_root,
        "opening": company_root / "OPENING_SNAPSHOT.json",
        "opening_receipt": company_root / "OPENING_ACQUISITION_RECEIPT.json",
        "incoming": company_root / "INCOMING_INTELLIGENCE.json",
        "active": company_root / "ACTIVE_INTELLIGENCE.json",
        "history": company_root / "INTELLIGENCE_HISTORY.jsonl",
        "acquisition": company_root / "ACQUISITION_RECEIPT.json",
        "refresh": company_root / "REFRESH_RECEIPT.json",
        "fit": company_root / "COMPANY_FIT.json",
    }


def _resolve_opening(
    candidate: IntelligenceCycleCandidate,
    paths: Mapping[str, Path],
    opening_fetcher: OpeningFetcher | None,
) -> tuple[JobOpening, str, str | None, tuple[str, ...]]:
    if candidate.opening_url is not None:
        kwargs: dict[str, object] = {
            "snapshot_path": paths["opening"],
            "receipt_path": paths["opening_receipt"],
        }
        if opening_fetcher is not None:
            kwargs["fetcher"] = opening_fetcher
        acquisition = acquire_live_opening(candidate.opening_url, **kwargs)
        return (
            acquisition.opening,
            acquisition.change.status,
            acquisition.receipt_sha256,
            acquisition.change.changed_fields,
        )
    if candidate.opening_path is None:
        raise ValueError("candidate requires opening_path or opening_url")
    return load_job_opening(candidate.opening_path), "STATIC", None, ()


def _run_company_cycle(
    candidate: IntelligenceCycleCandidate,
    profile: CandidateProfile,
    *,
    state_dir: Path,
    targets: Sequence[CompanyTarget],
    transport: Transport,
    opening_fetcher: OpeningFetcher | None,
) -> tuple[QueueCandidate, CompanyCycleResult]:
    target = find_target(candidate.company, targets)
    plan = load_acquisition_plan(candidate.acquisition_plan_path)
    paths = _company_paths(state_dir, plan.company_id)
    opening, opening_status, opening_receipt_sha, opening_changed_fields = _resolve_opening(
        candidate,
        paths,
        opening_fetcher,
    )
    _validate_identity(plan, target, opening)

    acquisition = acquire_company_intelligence(plan, transport=transport)
    _write_json(paths["incoming"], acquisition.intelligence.as_dict())
    _write_json(paths["acquisition"], acquisition.to_dict())

    current = _resolve_current_intelligence(candidate, paths["active"])
    if current is None:
        active = acquisition.intelligence
        refresh_sha = _persist_initial_intelligence(
            active,
            active_path=paths["active"],
            receipt_path=paths["refresh"],
            acquisition=acquisition,
        )
        status = "INITIALIZED"
    else:
        refresh = refresh_company_intelligence(current, acquisition.intelligence)
        persist_refresh(
            refresh,
            active_path=paths["active"],
            history_path=paths["history"],
            receipt_path=paths["refresh"],
        )
        active = refresh.intelligence
        refresh_sha = refresh.receipt.receipt_sha256
        status = "REFRESHED"

    fit: CompanyFitAssessment = assess_company_fit(profile, active)
    _write_json(paths["fit"], fit.as_dict())
    active_sha = _intelligence_sha256(active)
    result = CompanyCycleResult(
        company_id=plan.company_id,
        company=plan.company,
        opening_id=opening.opening_id,
        status=status,
        opening_status=opening_status,
        opening_receipt_sha256=opening_receipt_sha,
        opening_changed_fields=opening_changed_fields,
        acquisition_receipt_sha256=acquisition.receipt_sha256,
        refresh_receipt_sha256=refresh_sha,
        active_intelligence_sha256=active_sha,
        company_fit_score=fit.score,
        fresh_signal_count=fit.fresh_signal_count,
        state_dir=str(paths["root"]),
    )
    return (opening, target, active, candidate.role), result


def execute_intelligence_cycle(
    candidates: Sequence[IntelligenceCycleCandidate],
    profile: CandidateProfile,
    *,
    output_dir: Path,
    state_dir: Path,
    store: ApplicationStore,
    transport: Transport = fetch_http_source,
    opening_fetcher: OpeningFetcher | None = None,
    actionable_lanes: Sequence[str] = DEFAULT_ACTIONABLE_LANES,
    limit: int | None = None,
    calibration: OutcomeCalibration | None = None,
    continue_on_company_error: bool = True,
) -> IntelligenceCycleResult:
    """Execute live opening refresh through freshness-aware packet compilation."""
    if not candidates:
        raise ValueError("intelligence cycle requires at least one candidate")

    targets = load_targets()
    queue_candidates: list[QueueCandidate] = []
    company_results: list[CompanyCycleResult] = []
    for candidate in candidates:
        try:
            queue_candidate, result = _run_company_cycle(
                candidate,
                profile,
                state_dir=state_dir,
                targets=targets,
                transport=transport,
                opening_fetcher=opening_fetcher,
            )
        except Exception as exc:
            if not continue_on_company_error:
                raise
            fallback_opening_id = (
                candidate.opening_path.stem if candidate.opening_path is not None else "live-opening"
            )
            company_results.append(
                CompanyCycleResult(
                    company_id=candidate.company.casefold().replace(" ", "-"),
                    company=candidate.company,
                    opening_id=fallback_opening_id,
                    status="FAILED_ISOLATED",
                    opening_status="FAILED",
                    opening_receipt_sha256=None,
                    opening_changed_fields=(),
                    acquisition_receipt_sha256=None,
                    refresh_receipt_sha256=None,
                    active_intelligence_sha256=None,
                    company_fit_score=None,
                    fresh_signal_count=0,
                    state_dir=str(state_dir / "companies"),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        queue_candidates.append(queue_candidate)
        company_results.append(result)

    if not queue_candidates:
        failures = "; ".join(row.error or row.company for row in company_results)
        raise RuntimeError(f"all company intelligence candidates failed: {failures}")

    examples = load_outcome_examples(store.path)
    source_calibration = calibration or fit_outcome_calibration(examples)
    diagnostics = diagnose_outcome_calibration(examples, source_calibration)
    effective_calibration, guard = apply_calibration_guard(source_calibration, diagnostics)

    source_payload = source_calibration.as_dict()
    calibration_payload = effective_calibration.as_dict()
    calibration_sha = _canonical_sha256(calibration_payload)
    _write_json(state_dir / "OUTCOME_CALIBRATION_SOURCE.json", source_payload)
    _write_json(state_dir / "OUTCOME_CALIBRATION_DIAGNOSTICS.json", diagnostics.as_dict())
    _write_json(state_dir / "OUTCOME_CALIBRATION_GUARD.json", guard.as_dict())
    _write_json(state_dir / "OUTCOME_CALIBRATION.json", calibration_payload)

    freshness = compile_freshness_aware_batch(
        tuple(queue_candidates),
        profile,
        output_dir=output_dir,
        store=store,
        actionable_lanes=actionable_lanes,
        limit=limit,
        calibration=effective_calibration,
    )
    batch = freshness.batch
    base_receipt: dict[str, object] = {
        "schema": "glaciereq.job-intelligence-cycle.v3",
        "candidate_count": len(candidates),
        "successful_company_count": len(queue_candidates),
        "failed_company_count": len(candidates) - len(queue_candidates),
        "calibration_sha256": calibration_sha,
        "calibration_diagnostics": diagnostics.as_dict(),
        "calibration_guard": guard.as_dict(),
        "companies": [row.as_dict() for row in company_results],
        "freshness": freshness.as_dict(),
        "batch": batch.as_dict(),
    }
    receipt_sha = _canonical_sha256(base_receipt)
    result = IntelligenceCycleResult(
        schema="glaciereq.job-intelligence-cycle.v3",
        candidate_count=len(candidates),
        successful_company_count=len(queue_candidates),
        failed_company_count=len(candidates) - len(queue_candidates),
        calibration=effective_calibration,
        calibration_sha256=calibration_sha,
        calibration_diagnostics=diagnostics,
        calibration_guard=guard,
        companies=tuple(company_results),
        freshness=freshness,
        batch=batch,
        receipt_sha256=receipt_sha,
    )
    _write_json(state_dir / "INTELLIGENCE_CYCLE_RECEIPT.json", result.as_dict())
    return result


def load_cycle_manifest(path: Path) -> tuple[IntelligenceCycleCandidate, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("intelligence cycle manifest must be an object")
    raw = payload.get("candidates")
    if not isinstance(raw, list) or not raw:
        raise ValueError("intelligence cycle manifest requires non-empty candidates")
    root = path.parent
    rows: list[IntelligenceCycleCandidate] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"cycle candidates[{index}] must be an object")
        for field in ("company", "acquisition_plan"):
            if not item.get(field):
                raise ValueError(f"cycle candidates[{index}] requires {field}")
        opening = item.get("opening")
        opening_url = item.get("opening_url")
        if bool(opening) == bool(opening_url):
            raise ValueError(
                f"cycle candidates[{index}] requires exactly one of opening or opening_url"
            )
        current = item.get("current_intelligence")
        rows.append(
            IntelligenceCycleCandidate(
                company=str(item["company"]),
                acquisition_plan_path=root / str(item["acquisition_plan"]),
                opening_path=root / str(opening) if opening else None,
                opening_url=str(opening_url) if opening_url else None,
                current_intelligence_path=root / str(current) if current else None,
                role=str(item["role"]) if item.get("role") else None,
            )
        )
    return tuple(rows)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-cycle",
        description=(
            "Refresh attributable live openings and company intelligence, calculate fit, "
            "health-gate learned calibration, rank openings, quarantine stale packet lineage, "
            "and compile recruiter packets."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--lane", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    candidates = load_cycle_manifest(args.manifest)
    profile = load_candidate_profile(args.profile)
    lanes = tuple(args.lane) if args.lane else DEFAULT_ACTIONABLE_LANES
    with ApplicationStore(args.database) as store:
        result = execute_intelligence_cycle(
            candidates,
            profile,
            output_dir=args.output_dir,
            state_dir=args.state_dir,
            store=store,
            actionable_lanes=lanes,
            limit=args.limit,
            continue_on_company_error=not args.fail_fast,
        )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.batch.selected_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
