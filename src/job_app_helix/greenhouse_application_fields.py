"""Discover Greenhouse application fields and prepare provenance-bound answer guidance.

The public Greenhouse Job Board API can expose the exact application questions for a live
job post. This module turns that provider schema into an auditable pre-submission bundle:
contact fields are filled only from CandidateProfile evidence, attachments are surfaced as
explicit requirements, and custom/sensitive questions remain human-review decisions rather
than being guessed. Nothing in this module submits an application.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .application_operations import CandidateProfile, load_candidate_profile

JsonTransport = Callable[[str], Any]
SENSITIVE_LABEL_TERMS = (
    "gender",
    "race",
    "ethnicity",
    "disability",
    "veteran",
    "sexual orientation",
    "transgender",
    "demographic",
)
CONTACT_ALIASES = {
    "email": ("email", "e-mail"),
    "phone": ("phone", "telephone", "mobile"),
    "linkedin": ("linkedin",),
    "github": ("github",),
    "website": ("website", "portfolio", "personal site"),
}


class GreenhouseApplicationFieldError(RuntimeError):
    """Raised when provider data cannot satisfy the application-field contract."""


@dataclass(frozen=True)
class ApplicationField:
    label: str
    name: str
    field_type: str
    required: bool
    options: tuple[tuple[str, str], ...] = ()
    category: str = "question"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FieldAnswer:
    field: ApplicationField
    status: str
    value: str | None
    provenance: str | None
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "field": self.field.as_dict(),
            "status": self.status,
            "value": self.value,
            "provenance": self.provenance,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GreenhouseApplicationBundle:
    schema: str
    board_key: str
    job_id: str
    source_url: str
    profile_id: str
    profile_source_digest: str
    fields: tuple[FieldAnswer, ...]
    auto_fill_count: int
    attachment_count: int
    review_required_count: int
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "board_key": self.board_key,
            "job_id": self.job_id,
            "source_url": self.source_url,
            "profile_id": self.profile_id,
            "profile_source_digest": self.profile_source_digest,
            "fields": [item.as_dict() for item in self.fields],
            "auto_fill_count": self.auto_fill_count,
            "attachment_count": self.attachment_count,
            "review_required_count": self.review_required_count,
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "job-app-helix/0.3"},
    )
    with urllib.request.urlopen(request, timeout=20.0) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def _field_options(field: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    values = field.get("values")
    if not isinstance(values, list):
        return ()
    result: list[tuple[str, str]] = []
    for option in values:
        if not isinstance(option, Mapping):
            continue
        value = option.get("value")
        label = option.get("label")
        if value is None or label is None:
            continue
        result.append((str(value), str(label)))
    return tuple(result)


def _normalize_questions(payload: Mapping[str, Any]) -> tuple[ApplicationField, ...]:
    normalized: list[ApplicationField] = []
    for category in ("questions", "location_questions", "compliance"):
        rows = payload.get(category)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            label = str(row.get("label") or "").strip()
            required = bool(row.get("required"))
            fields = row.get("fields")
            if not isinstance(fields, list):
                continue
            for field in fields:
                if not isinstance(field, Mapping):
                    continue
                name = str(field.get("name") or "").strip()
                field_type = str(field.get("type") or "").strip()
                if not name or not field_type:
                    continue
                normalized.append(
                    ApplicationField(
                        label=label or name,
                        name=name,
                        field_type=field_type,
                        required=required,
                        options=_field_options(field),
                        category=category,
                    )
                )
    demographic = payload.get("demographic_questions")
    if isinstance(demographic, Mapping):
        rows = demographic.get("questions")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                label = str(
                    row.get("label") or row.get("name") or "Demographic question"
                ).strip()
                normalized.append(
                    ApplicationField(
                        label=label,
                        name=str(row.get("id") or row.get("name") or label),
                        field_type=str(row.get("type") or "demographic"),
                        required=bool(row.get("required")),
                        category="demographic_questions",
                    )
                )
    return tuple(normalized)


def _name_parts(name: str) -> tuple[str, str]:
    parts = tuple(part for part in re.split(r"\s+", name.strip()) if part)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def _contact_lookup(profile: CandidateProfile, aliases: Sequence[str]) -> tuple[str, str] | None:
    for key, value in profile.contact.items():
        normalized = key.casefold().replace("_", " ").replace("-", " ")
        if any(alias in normalized for alias in aliases) and str(value).strip():
            return str(value).strip(), f"CandidateProfile.contact.{key}"
    return None


def _answer_field(field: ApplicationField, profile: CandidateProfile) -> FieldAnswer:
    label = field.label.casefold()
    name = field.name.casefold()
    combined = f"{label} {name}"

    if field.field_type == "input_hidden":
        return FieldAnswer(
            field,
            "PROVIDER_MANAGED",
            None,
            None,
            "Hidden provider field is not user-authored.",
        )
    if field.category in {"compliance", "demographic_questions"} or any(
        term in combined for term in SENSITIVE_LABEL_TERMS
    ):
        return FieldAnswer(
            field,
            "USER_DECISION_REQUIRED",
            None,
            None,
            "Sensitive or compliance response must be chosen by the applicant.",
        )
    if field.field_type == "input_file" or name in {"resume", "cover_letter"}:
        return FieldAnswer(
            field,
            "ATTACHMENT_REQUIRED",
            None,
            None,
            "The provider requires an attachment; no path or document is invented.",
        )

    first_name, last_name = _name_parts(profile.name)
    if name == "first_name" and first_name:
        return FieldAnswer(
            field,
            "AUTO_FILL",
            first_name,
            "CandidateProfile.name",
            "Exact profile name evidence.",
        )
    if name == "last_name" and last_name:
        return FieldAnswer(
            field,
            "AUTO_FILL",
            last_name,
            "CandidateProfile.name",
            "Exact profile name evidence.",
        )

    for contact_kind, aliases in CONTACT_ALIASES.items():
        if contact_kind in combined or any(alias in combined for alias in aliases):
            hit = _contact_lookup(profile, aliases)
            if hit is not None:
                value, provenance = hit
                return FieldAnswer(
                    field,
                    "AUTO_FILL",
                    value,
                    provenance,
                    "Exact profile contact evidence.",
                )

    if name == "email":
        hit = _contact_lookup(profile, CONTACT_ALIASES["email"])
        if hit is not None:
            return FieldAnswer(
                field,
                "AUTO_FILL",
                hit[0],
                hit[1],
                "Exact profile contact evidence.",
            )
    if name == "phone":
        hit = _contact_lookup(profile, CONTACT_ALIASES["phone"])
        if hit is not None:
            return FieldAnswer(
                field,
                "AUTO_FILL",
                hit[0],
                hit[1],
                "Exact profile contact evidence.",
            )

    return FieldAnswer(
        field,
        "REVIEW_REQUIRED",
        None,
        None,
        "No exact CandidateProfile evidence safely answers this provider field.",
    )


def build_greenhouse_application_bundle(
    board_key: str,
    job_id: str | int,
    profile: CandidateProfile,
    *,
    transport: JsonTransport = _fetch_json,
) -> GreenhouseApplicationBundle:
    board_key = board_key.strip()
    job_id_text = str(job_id).strip()
    if not board_key or not job_id_text:
        raise GreenhouseApplicationFieldError("board_key and job_id are required")
    source_url = (
        f"https://boards-api.greenhouse.io/v1/boards/{board_key}/jobs/"
        f"{job_id_text}?questions=true"
    )
    payload = transport(source_url)
    if not isinstance(payload, Mapping):
        raise GreenhouseApplicationFieldError("Greenhouse job response must be a JSON object")
    provider_id = payload.get("id")
    if provider_id is not None and str(provider_id) != job_id_text:
        raise GreenhouseApplicationFieldError(
            f"Greenhouse job identity drift: requested {job_id_text}, received {provider_id}"
        )
    fields = _normalize_questions(payload)
    if not fields:
        raise GreenhouseApplicationFieldError("Greenhouse job returned no application fields")
    answers = tuple(_answer_field(field, profile) for field in fields)
    base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-application-fields.v1",
        "board_key": board_key,
        "job_id": job_id_text,
        "source_url": source_url,
        "profile_id": profile.profile_id,
        "profile_source_digest": profile.source_digest,
        "fields": [item.as_dict() for item in answers],
    }
    receipt_sha = _canonical_sha256(base)
    return GreenhouseApplicationBundle(
        schema=str(base["schema"]),
        board_key=board_key,
        job_id=job_id_text,
        source_url=source_url,
        profile_id=profile.profile_id,
        profile_source_digest=profile.source_digest,
        fields=answers,
        auto_fill_count=sum(item.status == "AUTO_FILL" for item in answers),
        attachment_count=sum(item.status == "ATTACHMENT_REQUIRED" for item in answers),
        review_required_count=sum(
            item.status in {"REVIEW_REQUIRED", "USER_DECISION_REQUIRED"} for item in answers
        ),
        receipt_sha256=receipt_sha,
    )


def write_greenhouse_application_bundle(
    board_key: str,
    job_id: str | int,
    profile: CandidateProfile,
    output: Path,
    *,
    transport: JsonTransport = _fetch_json,
) -> GreenhouseApplicationBundle:
    bundle = build_greenhouse_application_bundle(board_key, job_id, profile, transport=transport)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    rendered = json.dumps(bundle.as_dict(), indent=2, sort_keys=True) + "\n"
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(output)
    return bundle


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-greenhouse-fields")
    parser.add_argument("--board-key", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    profile = load_candidate_profile(args.profile)
    bundle = write_greenhouse_application_bundle(
        args.board_key,
        args.job_id,
        profile,
        args.output,
    )
    print(json.dumps(bundle.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
