"""Apply current proof reconciliation without rewriting historical surface decisions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .repository_health import sha256_json
from .repository_surface import (
    ADMIT_FORBIDDEN_BASE_ADMISSIONS,
    ADMIT_FORBIDDEN_FINDINGS,
    ADMIT_FORBIDDEN_LINEAGE_STATES,
    EXACT_SHA_RE,
    GOVERNED_DECISION_STATES,
    RepositorySurfaceError,
)

RECONCILIATION_SCHEMA = "glaciereq.public-repository-surface-reconciliation.v1"


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RepositorySurfaceError(f"{label} must be an object")
    return deepcopy(dict(value))


def _finding_delta(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RepositorySurfaceError(f"{label} must be a list")
    findings: list[str] = []
    for index, raw in enumerate(value):
        finding = str(raw).strip().upper()
        if not finding:
            raise RepositorySurfaceError(f"{label}[{index}] must not be empty")
        if finding not in findings:
            findings.append(finding)
    return findings


def _apply_finding_delta(
    record: dict[str, Any], item: Mapping[str, Any], repository: str
) -> tuple[list[str], list[str]]:
    additions = _finding_delta(item.get("findings_add"), f"{repository}.findings_add")
    removals = _finding_delta(
        item.get("findings_remove"), f"{repository}.findings_remove"
    )
    findings = [
        str(value).strip().upper()
        for value in record.get("findings", [])
        if str(value).strip()
    ]
    removal_set = set(removals)
    findings = [finding for finding in findings if finding not in removal_set]
    for finding in additions:
        if finding not in findings:
            findings.append(finding)
    record["findings"] = findings
    return additions, removals


def _proof_receipts(evidence: Mapping[str, Any], repository: str) -> list[dict[str, Any]]:
    raw = evidence.get("proof_receipts")
    if not isinstance(raw, list) or not raw:
        raise RepositorySurfaceError(
            f"ADMIT reconciliation for {repository} requires proof_receipts"
        )
    receipts: list[dict[str, Any]] = []
    for index, value in enumerate(raw):
        receipt = _object(value, f"{repository}.proof_receipts[{index}]")
        receipts.append(receipt)
    return receipts


def _validate_admit(
    record: Mapping[str, Any], evidence: Mapping[str, Any], repository: str
) -> None:
    source_head = str(evidence.get("source_head", "")).strip()
    if EXACT_SHA_RE.fullmatch(source_head) is None:
        raise RepositorySurfaceError(
            f"ADMIT reconciliation for {repository} requires exact source_head"
        )

    blockers: list[str] = []
    if record.get("public") is not True:
        blockers.append("repository_not_public")

    admission = str(record.get("admission", "")).upper()
    if admission in ADMIT_FORBIDDEN_BASE_ADMISSIONS:
        blockers.append(f"admission:{admission}")

    lineage = str(record.get("lineage_state", "")).upper()
    if lineage in ADMIT_FORBIDDEN_LINEAGE_STATES:
        blockers.append(f"lineage_state:{lineage}")

    findings = {str(value).upper() for value in record.get("findings", [])}
    for finding in sorted(findings.intersection(ADMIT_FORBIDDEN_FINDINGS)):
        blockers.append(f"finding:{finding}")

    if blockers:
        raise RepositorySurfaceError(
            f"ADMIT reconciliation for {repository} conflicts with blockers: "
            + ", ".join(blockers)
        )

    for receipt in _proof_receipts(evidence, repository):
        if receipt.get("conclusion") != "success":
            raise RepositorySurfaceError(
                f"ADMIT reconciliation for {repository} has unsuccessful proof receipt"
            )
        if str(receipt.get("head_sha", "")).strip() != source_head:
            raise RepositorySurfaceError(
                f"ADMIT reconciliation for {repository} has proof/head drift"
            )
        if not str(receipt.get("name", "")).strip():
            raise RepositorySurfaceError(
                f"ADMIT reconciliation for {repository} has unnamed proof receipt"
            )


def _repair_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue = [
        {
            "repository": item["repository"],
            "priority": item["repair_priority"],
            "admission": item["admission"],
            "findings": item["findings"],
        }
        for item in records
        if item.get("repair_priority")
    ]
    rank = {"P0": 0, "P1": 1, "P2": 2}
    queue.sort(key=lambda item: (rank[item["priority"]], item["repository"]))
    return queue


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    admission = Counter(item["admission"] for item in records)
    assessment = Counter(item["assessment_state"] for item in records)
    priority = Counter(
        item["repair_priority"] for item in records if item.get("repair_priority")
    )
    repair_queue = _repair_queue(records)
    return {
        "summary": {
            "admission": dict(sorted(admission.items())),
            "assessment": dict(sorted(assessment.items())),
            "repair_priority": dict(sorted(priority.items())),
            "xai_repair_count": sum(
                1
                for item in repair_queue
                if next(
                    record["company_family"]
                    for record in records
                    if record["repository"] == item["repository"]
                )
                == "xai"
            ),
            "metadata_repair_count": sum(
                1
                for item in repair_queue
                if any(value.startswith("METADATA_") for value in item["findings"])
            ),
        },
        "repair_queue": repair_queue,
        "xai_truth_hardening_queue": [
            item
            for item in repair_queue
            if next(
                record["company_family"]
                for record in records
                if record["repository"] == item["repository"]
            )
            == "xai"
        ],
        "metadata_cleanup_queue": [
            item
            for item in repair_queue
            if any(value.startswith("METADATA_") for value in item["findings"])
        ],
    }


def apply_surface_reconciliation(
    report: Mapping[str, Any], reconciliation: Mapping[str, Any]
) -> dict[str, Any]:
    """Advance selected current decisions while preserving predecessor state."""

    if reconciliation.get("schema") != RECONCILIATION_SCHEMA:
        raise RepositorySurfaceError("unsupported surface reconciliation schema")
    if "governed_overlay" not in report:
        raise RepositorySurfaceError(
            "surface reconciliation requires a governed decision report"
        )

    body = deepcopy(dict(report))
    records = body.get("repositories")
    if not isinstance(records, list) or not records:
        raise RepositorySurfaceError("surface report repositories must be non-empty")
    by_repository = {str(item.get("repository", "")): item for item in records}

    raw_items = reconciliation.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise RepositorySurfaceError("surface reconciliation items must be non-empty")

    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        item = _object(raw, f"items[{index}]")
        repository = str(item.get("repository", "")).strip()
        if repository in seen:
            raise RepositorySurfaceError(
                f"surface reconciliation contains duplicate repository: {repository}"
            )
        seen.add(repository)
        if repository not in by_repository:
            raise RepositorySurfaceError(
                f"surface reconciliation references unknown repository: {repository}"
            )

        record = by_repository[repository]
        if record.get("governed_decision") is None:
            raise RepositorySurfaceError(
                f"surface reconciliation requires predecessor decision: {repository}"
            )

        prior_decision = str(record.get("admission", "")).upper()
        expected_prior = str(item.get("prior_decision", "")).strip().upper()
        if expected_prior != prior_decision:
            raise RepositorySurfaceError(
                f"surface reconciliation prior decision drift for {repository}: "
                f"expected {expected_prior}, observed {prior_decision}"
            )

        decision = str(item.get("decision", "")).strip().upper()
        if decision not in GOVERNED_DECISION_STATES:
            raise RepositorySurfaceError(
                f"invalid reconciled decision for {repository}: {decision}"
            )
        next_gate = str(item.get("next_gate", "")).strip()
        if not next_gate:
            raise RepositorySurfaceError(
                f"surface reconciliation for {repository} requires next_gate"
            )
        evidence = _object(item.get("evidence"), f"items[{index}].evidence")
        findings_add, findings_remove = _apply_finding_delta(record, item, repository)
        if decision == "ADMIT":
            _validate_admit(record, evidence, repository)

        history = record.setdefault("reconciliation_history", [])
        history.append(
            {
                "prior_decision": prior_decision,
                "decision": decision,
                "generated_at": reconciliation.get("generated_at"),
                "evidence": evidence,
                "findings_add": findings_add,
                "findings_remove": findings_remove,
                "next_gate": next_gate,
            }
        )
        record["prior_reconciled_admission"] = prior_decision
        record["admission"] = decision
        record["governed_decision"] = decision
        record["decision_evidence"] = evidence
        record["decision_next_gate"] = next_gate
        record["decision_excellence_state"] = item.get("excellence_state")
        record["assessment_state"] = (
            "PARTIAL" if decision == "REPAIR_REQUIRED" else "COMPLETE"
        )
        if decision == "QUARANTINED":
            record["repair_priority"] = "P0"
        elif decision == "REPAIR_REQUIRED":
            priority = str(item.get("repair_priority", "")).strip().upper()
            if priority not in {"P0", "P1", "P2"}:
                priority = record.get("repair_priority") or "P2"
            record["repair_priority"] = priority
        else:
            record["repair_priority"] = None

    prior_report_id = body.pop("report_id", None)
    body.update(_summary(records))
    counts = Counter(item["admission"] for item in records)
    body["reconciliation_overlay"] = {
        "schema": reconciliation.get("schema"),
        "generated_at": reconciliation.get("generated_at"),
        "predecessor": reconciliation.get("predecessor_decisions"),
        "item_count": len(seen),
        "prior_report_id": prior_report_id,
        "admission_counts": dict(sorted(counts.items())),
    }
    body["report_id"] = sha256_json(body)
    return body
