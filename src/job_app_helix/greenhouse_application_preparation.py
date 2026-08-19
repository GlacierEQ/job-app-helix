"""Prepare a live Greenhouse application packet with evidence-bound custom-answer drafts.

This composes three already-proven Helix surfaces: an APPLICATION_READY release, the live
Greenhouse field schema, and candidate/portfolio evidence. It writes preparation sidecars
into the selected recruiter packet but never submits an application or changes the existing
APPLICATION_READY receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .application_operations import CandidateProfile, load_candidate_profile
from .greenhouse_application_fields import (
    FieldAnswer,
    GreenhouseApplicationBundle,
    JsonTransport,
    _fetch_json,
    build_greenhouse_application_bundle,
)


class GreenhouseApplicationPreparationError(RuntimeError):
    """Raised when a release cannot be prepared without losing identity or provenance."""


@dataclass(frozen=True)
class EvidenceFragment:
    text: str
    provenance: str
    evidence_class: str
    source_sha256: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PromptPreparation:
    field_name: str
    label: str
    status: str
    draft: str | None
    provenance: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GreenhouseApplicationPreparation:
    schema: str
    application_id: str
    opening_id: str
    packet_dir: str
    release_receipt_sha256: str
    field_bundle_receipt_sha256: str
    evidence: tuple[EvidenceFragment, ...]
    prompts: tuple[PromptPreparation, ...]
    drafted_count: int
    review_required_count: int
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "application_id": self.application_id,
            "opening_id": self.opening_id,
            "packet_dir": self.packet_dir,
            "release_receipt_sha256": self.release_receipt_sha256,
            "field_bundle_receipt_sha256": self.field_bundle_receipt_sha256,
            "evidence": [item.as_dict() for item in self.evidence],
            "prompts": [item.as_dict() for item in self.prompts],
            "drafted_count": self.drafted_count,
            "review_required_count": self.review_required_count,
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_object(path: Path, *, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GreenhouseApplicationPreparationError(f"invalid {label} at {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise GreenhouseApplicationPreparationError(f"{label} must be a JSON object: {path}")
    return value


def _required_string(value: Mapping[str, object], field: str, *, label: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise GreenhouseApplicationPreparationError(f"{label} requires non-empty {field}")
    return result.strip()


def _profile_evidence(profile: CandidateProfile) -> tuple[EvidenceFragment, ...]:
    fragments: list[EvidenceFragment] = []
    for index, text in enumerate(profile.achievements):
        fragments.append(
            EvidenceFragment(
                text=text,
                provenance=f"CandidateProfile.achievements[{index}]",
                evidence_class="candidate_achievement",
            )
        )
    for index, text in enumerate(profile.experience):
        fragments.append(
            EvidenceFragment(
                text=text,
                provenance=f"CandidateProfile.experience[{index}]",
                evidence_class="candidate_experience",
            )
        )
    return tuple(fragments)


def _constellation_evidence(path: Path) -> tuple[EvidenceFragment, ...]:
    """Extract only bounded, source-reviewed precise claims from a constellation markdown table."""
    text = path.read_text(encoding="utf-8")
    digest = _file_sha256(path)
    fragments: list[EvidenceFragment] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "**Directly supported**" not in line and "**Strongly supported**" not in line:
            continue
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        precise_claim = re.sub(r"\s+", " ", cells[-2]).strip()
        if not precise_claim:
            continue
        fragments.append(
            EvidenceFragment(
                text=precise_claim,
                provenance=f"{path}:L{line_number}",
                evidence_class="source_reviewed_portfolio_claim",
                source_sha256=digest,
            )
        )
    return tuple(fragments)


def collect_evidence(
    profile: CandidateProfile,
    evidence_sources: Sequence[Path],
) -> tuple[EvidenceFragment, ...]:
    fragments = list(_profile_evidence(profile))
    for path in evidence_sources:
        if not path.is_file():
            raise GreenhouseApplicationPreparationError(f"evidence source does not exist: {path}")
        fragments.extend(_constellation_evidence(path))
    deduped: list[EvidenceFragment] = []
    seen: set[str] = set()
    for fragment in fragments:
        key = fragment.text.casefold().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(fragment)
    return tuple(deduped)


def _exceptional_work_draft(evidence: Sequence[EvidenceFragment]) -> PromptPreparation | None:
    if not evidence:
        return None
    achievements = [item for item in evidence if item.evidence_class == "candidate_achievement"]
    reviewed = [
        item for item in evidence if item.evidence_class == "source_reviewed_portfolio_claim"
    ]
    experience = [item for item in evidence if item.evidence_class == "candidate_experience"]
    selected = (achievements + reviewed + experience)[:3]
    if not selected:
        return None
    body = "Examples of work I can substantiate include: " + "; ".join(
        item.text.rstrip(". ") for item in selected
    ) + "."
    return PromptPreparation(
        field_name="",
        label="",
        status="DRAFT_REVIEW_REQUIRED",
        draft=body,
        provenance=tuple(item.provenance for item in selected),
        reason=(
            "Draft is assembled only from exact CandidateProfile or source-reviewed portfolio "
            "claims; applicant review is still required."
        ),
    )


def _prepare_prompt(
    field_answer: FieldAnswer,
    evidence: Sequence[EvidenceFragment],
) -> PromptPreparation:
    field = field_answer.field
    combined = f"{field.label} {field.name}".casefold()
    if field_answer.status == "AUTO_FILL":
        return PromptPreparation(
            field_name=field.name,
            label=field.label,
            status="AUTO_FILL_VERIFIED",
            draft=field_answer.value,
            provenance=(field_answer.provenance,) if field_answer.provenance else (),
            reason=field_answer.reason,
        )
    if "exceptional work" in combined and field.field_type in {"textarea", "input_text"}:
        drafted = _exceptional_work_draft(evidence)
        if drafted is not None:
            return PromptPreparation(
                field_name=field.name,
                label=field.label,
                status=drafted.status,
                draft=drafted.draft,
                provenance=drafted.provenance,
                reason=drafted.reason,
            )
    return PromptPreparation(
        field_name=field.name,
        label=field.label,
        status=field_answer.status,
        draft=None,
        provenance=(),
        reason=field_answer.reason,
    )


def _resolve_release(release_path: Path) -> tuple[str, str, Path, str]:
    release = _read_object(release_path, label="application-ready release")
    receipt = _required_string(release, "receipt_sha256", label="application-ready release")
    selected = release.get("selected")
    if not isinstance(selected, Mapping):
        raise GreenhouseApplicationPreparationError("application-ready release requires selected")
    application_id = _required_string(selected, "application_id", label="selected release")
    opening_id = _required_string(selected, "opening_id", label="selected release")
    packet_dir = Path(_required_string(selected, "packet_dir", label="selected release"))
    if not packet_dir.is_dir():
        raise GreenhouseApplicationPreparationError(
            f"selected packet directory is unavailable: {packet_dir}"
        )
    return application_id, opening_id, packet_dir, receipt


def prepare_greenhouse_application_release(
    release_path: Path,
    profile: CandidateProfile,
    *,
    board_key: str,
    job_id: str | int,
    evidence_sources: Sequence[Path] = (),
    output_path: Path | None = None,
    transport: JsonTransport = _fetch_json,
) -> GreenhouseApplicationPreparation:
    """Bind a live Greenhouse form and bounded evidence to one APPLICATION_READY packet."""
    application_id, opening_id, packet_dir, release_receipt = _resolve_release(release_path)
    job_id_text = str(job_id).strip()
    if opening_id != job_id_text:
        raise GreenhouseApplicationPreparationError(
            f"release/provider opening identity drift: {opening_id} != {job_id_text}"
        )
    field_bundle: GreenhouseApplicationBundle = build_greenhouse_application_bundle(
        board_key,
        job_id_text,
        profile,
        transport=transport,
    )
    evidence = collect_evidence(profile, evidence_sources)
    prompts = tuple(_prepare_prompt(item, evidence) for item in field_bundle.fields)
    base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-application-preparation.v1",
        "application_id": application_id,
        "opening_id": opening_id,
        "packet_dir": str(packet_dir),
        "release_receipt_sha256": release_receipt,
        "field_bundle_receipt_sha256": field_bundle.receipt_sha256,
        "evidence": [item.as_dict() for item in evidence],
        "prompts": [item.as_dict() for item in prompts],
    }
    result = GreenhouseApplicationPreparation(
        schema=str(base["schema"]),
        application_id=application_id,
        opening_id=opening_id,
        packet_dir=str(packet_dir),
        release_receipt_sha256=release_receipt,
        field_bundle_receipt_sha256=field_bundle.receipt_sha256,
        evidence=evidence,
        prompts=prompts,
        drafted_count=sum(item.status == "DRAFT_REVIEW_REQUIRED" for item in prompts),
        review_required_count=sum(
            item.status in {"DRAFT_REVIEW_REQUIRED", "REVIEW_REQUIRED", "USER_DECISION_REQUIRED"}
            for item in prompts
        ),
        receipt_sha256=_canonical_sha256(base),
    )
    _write_json(packet_dir / "GREENHOUSE_APPLICATION_FIELDS.json", field_bundle.as_dict())
    _write_json(packet_dir / "GREENHOUSE_APPLICATION_PREPARATION.json", result.as_dict())
    if output_path is not None:
        _write_json(output_path, result.as_dict())
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-greenhouse-prepare")
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--board-key", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--evidence-source", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = prepare_greenhouse_application_release(
        args.release,
        load_candidate_profile(args.profile),
        board_key=args.board_key,
        job_id=args.job_id,
        evidence_sources=tuple(args.evidence_source),
        output_path=args.output,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
