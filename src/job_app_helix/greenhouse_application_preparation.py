"""Prepare a live Greenhouse application packet with evidence-bound answer drafts.

This composes an APPLICATION_READY release, the live Greenhouse field schema, candidate
and portfolio evidence, and optional applicant-confirmed answers. Confirmed answers are
bound to exact live field identities and provider options before packet mutation. Nothing
in this module submits an application or changes the existing APPLICATION_READY receipt.
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
    ApplicationField,
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
class ApplicantConfirmedAnswer:
    field_name: str
    value: str
    provenance: str
    source_sha256: str

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
    applicant_answers: tuple[ApplicantConfirmedAnswer, ...]
    prompts: tuple[PromptPreparation, ...]
    drafted_count: int
    applicant_confirmed_count: int
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
            "applicant_answers": [item.as_dict() for item in self.applicant_answers],
            "prompts": [item.as_dict() for item in self.prompts],
            "drafted_count": self.drafted_count,
            "applicant_confirmed_count": self.applicant_confirmed_count,
            "review_required_count": self.review_required_count,
            "receipt_sha256": self.receipt_sha256,
        }


def _reference_sha256(payload: Mapping[str, object]) -> str:
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


def load_applicant_answers(paths: Sequence[Path]) -> tuple[ApplicantConfirmedAnswer, ...]:
    """Load explicit applicant answers from hashed JSON sources without inferring values."""
    answers: list[ApplicantConfirmedAnswer] = []
    seen: dict[str, ApplicantConfirmedAnswer] = {}
    for path in paths:
        payload = _read_object(path, label="applicant answer source")
        raw_answers = payload.get("answers")
        if not isinstance(raw_answers, list) or not raw_answers:
            raise GreenhouseApplicationPreparationError(
                f"applicant answer source requires non-empty answers: {path}"
            )
        digest = _file_sha256(path)
        for index, row in enumerate(raw_answers):
            if not isinstance(row, Mapping):
                raise GreenhouseApplicationPreparationError(
                    f"applicant answer #{index} must be an object: {path}"
                )
            field_name = _required_string(row, "field_name", label=f"applicant answer #{index}")
            value = _required_string(row, "value", label=f"applicant answer #{index}")
            provenance_value = row.get("provenance")
            provenance = (
                str(provenance_value).strip()
                if isinstance(provenance_value, str) and provenance_value.strip()
                else f"{path}#answers[{index}]"
            )
            answer = ApplicantConfirmedAnswer(field_name, value, provenance, digest)
            existing = seen.get(field_name)
            if existing is not None and existing.value != value:
                raise GreenhouseApplicationPreparationError(
                    f"conflicting applicant answers for live field {field_name}"
                )
            if existing is None:
                seen[field_name] = answer
                answers.append(answer)
    return tuple(answers)


def _normalize_option_value(field: ApplicationField, value: str) -> str:
    if not field.options:
        return value
    folded = value.casefold().strip()
    matches = [
        option_value
        for option_value, label in field.options
        if folded in {option_value.casefold().strip(), label.casefold().strip()}
    ]
    if len(matches) != 1:
        labels = ", ".join(label for _, label in field.options)
        raise GreenhouseApplicationPreparationError(
            f"applicant answer for {field.name} must match one live provider option: {labels}"
        )
    return matches[0]


def _bind_applicant_answers(
    field_bundle: GreenhouseApplicationBundle,
    answers: Sequence[ApplicantConfirmedAnswer],
) -> dict[str, ApplicantConfirmedAnswer]:
    by_field = {item.field.name: item.field for item in field_bundle.fields}
    bound: dict[str, ApplicantConfirmedAnswer] = {}
    for answer in answers:
        field = by_field.get(answer.field_name)
        if field is None:
            message = "applicant answer field is not present in live provider schema: "
            raise GreenhouseApplicationPreparationError(message + answer.field_name)
        if field.field_type in {"input_hidden", "input_file"}:
            raise GreenhouseApplicationPreparationError(
                f"applicant answer cannot override provider-managed field {answer.field_name}"
            )
        value = _normalize_option_value(field, answer.value)
        bound[answer.field_name] = ApplicantConfirmedAnswer(
            field_name=answer.field_name,
            value=value,
            provenance=answer.provenance,
            source_sha256=answer.source_sha256,
        )
    return bound


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
    applicant_answer: ApplicantConfirmedAnswer | None = None,
) -> PromptPreparation:
    field = field_answer.field
    if applicant_answer is not None:
        return PromptPreparation(
            field_name=field.name,
            label=field.label,
            status="APPLICANT_CONFIRMED",
            draft=applicant_answer.value,
            provenance=(applicant_answer.provenance, f"sha256:{applicant_answer.source_sha256}"),
            reason=(
                "Exact applicant-supplied answer bound to the current live provider field "
                "schema."
            ),
        )
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
    applicant_answer_sources: Sequence[Path] = (),
    output_path: Path | None = None,
    transport: JsonTransport = _fetch_json,
) -> GreenhouseApplicationPreparation:
    """Bind a live Greenhouse form and bounded applicant evidence to one release packet."""
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
    applicant_answers = load_applicant_answers(applicant_answer_sources)
    bound_answers = _bind_applicant_answers(field_bundle, applicant_answers)
    prompts = tuple(
        _prepare_prompt(item, evidence, bound_answers.get(item.field.name))
        for item in field_bundle.fields
    )
    base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-application-preparation.v2",
        "application_id": application_id,
        "opening_id": opening_id,
        "packet_dir": str(packet_dir),
        "release_receipt_sha256": release_receipt,
        "field_bundle_receipt_sha256": field_bundle.receipt_sha256,
        "evidence": [item.as_dict() for item in evidence],
        "applicant_answers": [item.as_dict() for item in applicant_answers],
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
        applicant_answers=applicant_answers,
        prompts=prompts,
        drafted_count=sum(item.status == "DRAFT_REVIEW_REQUIRED" for item in prompts),
        applicant_confirmed_count=sum(item.status == "APPLICANT_CONFIRMED" for item in prompts),
        review_required_count=sum(
            item.status in {"DRAFT_REVIEW_REQUIRED", "REVIEW_REQUIRED", "USER_DECISION_REQUIRED"}
            for item in prompts
        ),
        receipt_sha256=_reference_sha256(base),
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
    parser.add_argument("--applicant-answer-source", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = prepare_greenhouse_application_release(
        args.release,
        load_candidate_profile(args.profile),
        board_key=args.board_key,
        job_id=args.job_id,
        evidence_sources=tuple(args.evidence_source),
        applicant_answer_sources=tuple(args.applicant_answer_source),
        output_path=args.output,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
