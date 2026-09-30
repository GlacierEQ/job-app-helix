"""Finalize a prepared Greenhouse application into a hash-bound review-complete packet.

The preparation runtime deliberately leaves attachments and unresolved applicant decisions
outside automatic mutation. This module closes that last internal gap without submitting an
application: it binds explicit attachment files to exact live Greenhouse file fields, verifies
preparation/field-bundle lineage, resolves required fields, and emits a deterministic final
review packet. A packet is marked ready only when every required user-authored field has an
answer or attachment that can be traced to concrete source evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


class GreenhouseApplicationFinalizationError(RuntimeError):
    """Raised when application finalization cannot preserve field identity or source integrity."""


@dataclass(frozen=True)
class AttachmentBinding:
    field_name: str
    path: str
    sha256: str
    size_bytes: int
    provenance: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FinalFieldResolution:
    field_name: str
    label: str
    field_type: str
    required: bool
    status: str
    value: str | None
    attachment: AttachmentBinding | None
    provenance: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["attachment"] = self.attachment.as_dict() if self.attachment is not None else None
        return payload


@dataclass(frozen=True)
class GreenhouseApplicationFinalization:
    schema: str
    application_id: str
    opening_id: str
    packet_dir: str
    preparation_receipt_sha256: str
    field_bundle_receipt_sha256: str
    fields: tuple[FinalFieldResolution, ...]
    attachments: tuple[AttachmentBinding, ...]
    required_field_count: int
    resolved_required_count: int
    unresolved_required_fields: tuple[str, ...]
    ready_for_human_submission: bool
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "application_id": self.application_id,
            "opening_id": self.opening_id,
            "packet_dir": self.packet_dir,
            "preparation_receipt_sha256": self.preparation_receipt_sha256,
            "field_bundle_receipt_sha256": self.field_bundle_receipt_sha256,
            "fields": [item.as_dict() for item in self.fields],
            "attachments": [item.as_dict() for item in self.attachments],
            "required_field_count": self.required_field_count,
            "resolved_required_count": self.resolved_required_count,
            "unresolved_required_fields": list(self.unresolved_required_fields),
            "ready_for_human_submission": self.ready_for_human_submission,
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


def _read_object(path: Path, *, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GreenhouseApplicationFinalizationError(f"invalid {label} at {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise GreenhouseApplicationFinalizationError(f"{label} must be a JSON object: {path}")
    return value


def _required_string(value: Mapping[str, object], field: str, *, label: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result.strip():
        raise GreenhouseApplicationFinalizationError(f"{label} requires non-empty {field}")
    return result.strip()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_attachments(paths: Sequence[Path]) -> tuple[AttachmentBinding, ...]:
    bindings: list[AttachmentBinding] = []
    seen: dict[str, AttachmentBinding] = {}
    for source_path in paths:
        payload = _read_object(source_path, label="attachment source")
        rows = payload.get("attachments")
        if not isinstance(rows, list) or not rows:
            raise GreenhouseApplicationFinalizationError(
                f"attachment source requires non-empty attachments: {source_path}"
            )
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise GreenhouseApplicationFinalizationError(
                    f"attachment #{index} must be an object: {source_path}"
                )
            field_name = _required_string(row, "field_name", label=f"attachment #{index}")
            raw_path = _required_string(row, "path", label=f"attachment #{index}")
            artifact_path = Path(raw_path).expanduser().resolve()
            if not artifact_path.is_file():
                raise GreenhouseApplicationFinalizationError(
                    f"attachment file does not exist for {field_name}: {artifact_path}"
                )
            size = artifact_path.stat().st_size
            if size <= 0:
                raise GreenhouseApplicationFinalizationError(
                    f"attachment file is empty for {field_name}: {artifact_path}"
                )
            provenance_value = row.get("provenance")
            provenance = (
                provenance_value.strip()
                if isinstance(provenance_value, str) and provenance_value.strip()
                else f"{source_path}#attachments[{index}]"
            )
            binding = AttachmentBinding(
                field_name=field_name,
                path=str(artifact_path),
                sha256=_file_sha256(artifact_path),
                size_bytes=size,
                provenance=provenance,
            )
            existing = seen.get(field_name)
            if existing is not None and existing.sha256 != binding.sha256:
                raise GreenhouseApplicationFinalizationError(
                    f"conflicting attachments for live field {field_name}"
                )
            if existing is None:
                seen[field_name] = binding
                bindings.append(binding)
    return tuple(bindings)


def _load_preparation(path: Path) -> tuple[Mapping[str, object], Path]:
    preparation = _read_object(path, label="Greenhouse application preparation")
    schema = _required_string(preparation, "schema", label="Greenhouse application preparation")
    if schema not in {
        "glaciereq.greenhouse-application-preparation.v1",
        "glaciereq.greenhouse-application-preparation.v2",
    }:
        raise GreenhouseApplicationFinalizationError(f"unsupported preparation schema: {schema}")
    packet_dir = Path(
        _required_string(preparation, "packet_dir", label="Greenhouse application preparation")
    )
    if not packet_dir.is_dir():
        raise GreenhouseApplicationFinalizationError(
            f"prepared packet directory is unavailable: {packet_dir}"
        )
    return preparation, packet_dir


def _index_live_fields(field_bundle: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    rows = field_bundle.get("fields")
    if not isinstance(rows, list) or not rows:
        raise GreenhouseApplicationFinalizationError("field bundle requires non-empty fields")
    indexed: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        field = row.get("field")
        if not isinstance(field, Mapping):
            continue
        name = field.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        if name in indexed:
            raise GreenhouseApplicationFinalizationError(f"duplicate live field identity: {name}")
        indexed[name] = field
    if not indexed:
        raise GreenhouseApplicationFinalizationError(
            "field bundle contains no usable field identities"
        )
    return indexed


def _index_prompts(preparation: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    rows = preparation.get("prompts")
    if not isinstance(rows, list) or not rows:
        raise GreenhouseApplicationFinalizationError("preparation requires non-empty prompts")
    indexed: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = row.get("field_name")
        if not isinstance(name, str) or not name.strip():
            continue
        if name in indexed:
            raise GreenhouseApplicationFinalizationError(
                f"duplicate prepared field identity: {name}"
            )
        indexed[name] = row
    return indexed


def _resolve_field(
    field: Mapping[str, object],
    prompt: Mapping[str, object] | None,
    attachment: AttachmentBinding | None,
) -> FinalFieldResolution:
    name = _required_string(field, "name", label="live field")
    label = _required_string(field, "label", label=f"live field {name}")
    field_type = _required_string(field, "field_type", label=f"live field {name}")
    required = bool(field.get("required"))

    if field_type == "input_hidden":
        return FinalFieldResolution(
            name,
            label,
            field_type,
            required,
            "PROVIDER_MANAGED",
            None,
            None,
            (),
            "Hidden provider field is excluded from user-authored completeness gating.",
        )
    if field_type == "input_file":
        if attachment is not None:
            return FinalFieldResolution(
                name,
                label,
                field_type,
                required,
                "ATTACHMENT_BOUND",
                None,
                attachment,
                (attachment.provenance, f"sha256:{attachment.sha256}"),
                "Exact local attachment is hash-bound to the current live file field.",
            )
        return FinalFieldResolution(
            name,
            label,
            field_type,
            required,
            "UNRESOLVED_REQUIRED" if required else "OPTIONAL_UNRESOLVED",
            None,
            None,
            (),
            "No attachment was supplied for this live provider file field.",
        )

    if prompt is None:
        return FinalFieldResolution(
            name,
            label,
            field_type,
            required,
            "UNRESOLVED_REQUIRED" if required else "OPTIONAL_UNRESOLVED",
            None,
            None,
            (),
            "No prepared answer is bound to this live field identity.",
        )
    status = str(prompt.get("status") or "").strip()
    draft = prompt.get("draft")
    value = draft.strip() if isinstance(draft, str) and draft.strip() else None
    raw_provenance = prompt.get("provenance")
    provenance = (
        tuple(str(item).strip() for item in raw_provenance if str(item).strip())
        if isinstance(raw_provenance, list)
        else ()
    )

    accepted_statuses = {"AUTO_FILL_VERIFIED", "APPLICANT_CONFIRMED"}
    if status in accepted_statuses and value is not None:
        return FinalFieldResolution(
            name,
            label,
            field_type,
            required,
            "ANSWER_BOUND",
            value,
            None,
            provenance,
            f"Prepared {status} value is source-bound to the current live field.",
        )
    return FinalFieldResolution(
        name,
        label,
        field_type,
        required,
        "UNRESOLVED_REQUIRED" if required else "OPTIONAL_UNRESOLVED",
        value,
        None,
        provenance,
        (
            "Drafts and undecided values are not promoted to final answers without "
            "applicant confirmation."
        ),
    )


def finalize_greenhouse_application(
    preparation_path: Path,
    *,
    attachment_sources: Sequence[Path] = (),
    output_path: Path | None = None,
) -> GreenhouseApplicationFinalization:
    """Build a deterministic final-review packet without performing external submission."""
    preparation, packet_dir = _load_preparation(preparation_path)
    field_bundle_path = packet_dir / "GREENHOUSE_APPLICATION_FIELDS.json"
    field_bundle = _read_object(field_bundle_path, label="Greenhouse application field bundle")

    expected_field_receipt = _required_string(
        preparation,
        "field_bundle_receipt_sha256",
        label="Greenhouse application preparation",
    )
    actual_field_receipt = _required_string(
        field_bundle,
        "receipt_sha256",
        label="Greenhouse application field bundle",
    )
    if actual_field_receipt != expected_field_receipt:
        raise GreenhouseApplicationFinalizationError(
            "preparation/field-bundle lineage mismatch; refusing stale or mixed application state"
        )

    application_id = _required_string(
        preparation,
        "application_id",
        label="Greenhouse application preparation",
    )
    opening_id = _required_string(
        preparation,
        "opening_id",
        label="Greenhouse application preparation",
    )
    if str(field_bundle.get("job_id") or "").strip() != opening_id:
        raise GreenhouseApplicationFinalizationError(
            "preparation/field-bundle opening identity mismatch"
        )

    attachments = _load_attachments(attachment_sources)
    live_fields = _index_live_fields(field_bundle)
    prompts = _index_prompts(preparation)
    by_attachment = {item.field_name: item for item in attachments}
    for field_name in by_attachment:
        field = live_fields.get(field_name)
        if field is None:
            raise GreenhouseApplicationFinalizationError(
                f"attachment field is not present in live provider schema: {field_name}"
            )
        if str(field.get("field_type") or "") != "input_file":
            raise GreenhouseApplicationFinalizationError(
                f"attachment cannot bind to non-file live field {field_name}"
            )

    resolutions = tuple(
        _resolve_field(field, prompts.get(name), by_attachment.get(name))
        for name, field in live_fields.items()
    )
    user_required = tuple(
        item for item in resolutions if item.required and item.status != "PROVIDER_MANAGED"
    )
    unresolved = tuple(
        item.field_name for item in user_required if item.status == "UNRESOLVED_REQUIRED"
    )
    base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-application-finalization.v1",
        "application_id": application_id,
        "opening_id": opening_id,
        "packet_dir": str(packet_dir),
        "preparation_receipt_sha256": _required_string(
            preparation,
            "receipt_sha256",
            label="Greenhouse application preparation",
        ),
        "field_bundle_receipt_sha256": actual_field_receipt,
        "fields": [item.as_dict() for item in resolutions],
        "attachments": [item.as_dict() for item in attachments],
        "required_field_count": len(user_required),
        "resolved_required_count": len(user_required) - len(unresolved),
        "unresolved_required_fields": list(unresolved),
        "ready_for_human_submission": not unresolved,
    }
    result = GreenhouseApplicationFinalization(
        schema=str(base["schema"]),
        application_id=application_id,
        opening_id=opening_id,
        packet_dir=str(packet_dir),
        preparation_receipt_sha256=str(base["preparation_receipt_sha256"]),
        field_bundle_receipt_sha256=actual_field_receipt,
        fields=resolutions,
        attachments=attachments,
        required_field_count=len(user_required),
        resolved_required_count=len(user_required) - len(unresolved),
        unresolved_required_fields=unresolved,
        ready_for_human_submission=not unresolved,
        receipt_sha256=_reference_sha256(base),
    )
    destination = output_path or packet_dir / "GREENHOUSE_APPLICATION_FINAL.json"
    _write_json(destination, result.as_dict())
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-greenhouse-finalize")
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--attachment-source", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = finalize_greenhouse_application(
        args.preparation,
        attachment_sources=tuple(args.attachment_source),
        output_path=args.output,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.ready_for_human_submission else 2


if __name__ == "__main__":
    raise SystemExit(main())
