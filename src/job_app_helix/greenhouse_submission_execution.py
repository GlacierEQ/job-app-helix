"""Compile and execute an evidence-bound Greenhouse application submission.

This module extends ``GREENHOUSE_APPLICATION_FINAL.json`` without weakening its review
boundary. It can always emit a deterministic submission plan. Direct provider mutation is
available only when the final packet is complete, every attachment still matches its recorded
hash, the exact board/job identity is preserved, an employer-issued Greenhouse Job Board API
key is supplied, and the caller presents the packet-specific authorization token.

Greenhouse's public Job Board GET endpoints do not require authentication. The application
POST endpoint does. Applicants normally do not possess the employer's Job Board API key, so
lack of that credential is represented as an explicit handoff state rather than fabricated
submission success.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import secrets
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class GreenhouseSubmissionError(RuntimeError):
    """Raised when the submission boundary cannot preserve evidence or provider identity."""


@dataclass(frozen=True)
class SubmissionAnswer:
    field_name: str
    label: str
    field_type: str
    category: str
    values: tuple[str, ...]
    provenance: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["values"] = list(self.values)
        payload["provenance"] = list(self.provenance)
        return payload


@dataclass(frozen=True)
class SubmissionAttachment:
    field_name: str
    label: str
    path: str
    sha256: str
    size_bytes: int
    mime_type: str
    provenance: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GreenhouseSubmissionPlan:
    schema: str
    application_id: str
    board_key: str
    job_id: str
    packet_dir: str
    finalization_path: str
    finalization_receipt_sha256: str
    field_bundle_receipt_sha256: str
    submission_endpoint: str
    answers: tuple[SubmissionAnswer, ...]
    attachments: tuple[SubmissionAttachment, ...]
    direct_api_eligible: bool
    direct_api_blockers: tuple[str, ...]
    handoff_state: str
    idempotency_key: str
    authorization_token: str
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "application_id": self.application_id,
            "board_key": self.board_key,
            "job_id": self.job_id,
            "packet_dir": self.packet_dir,
            "finalization_path": self.finalization_path,
            "finalization_receipt_sha256": self.finalization_receipt_sha256,
            "field_bundle_receipt_sha256": self.field_bundle_receipt_sha256,
            "submission_endpoint": self.submission_endpoint,
            "answers": [item.as_dict() for item in self.answers],
            "attachments": [item.as_dict() for item in self.attachments],
            "direct_api_eligible": self.direct_api_eligible,
            "direct_api_blockers": list(self.direct_api_blockers),
            "handoff_state": self.handoff_state,
            "idempotency_key": self.idempotency_key,
            "authorization_token": self.authorization_token,
            "receipt_sha256": self.receipt_sha256,
        }


@dataclass(frozen=True)
class GreenhouseSubmissionReceipt:
    schema: str
    application_id: str
    board_key: str
    job_id: str
    idempotency_key: str
    plan_receipt_sha256: str
    status: str
    http_status: int | None
    provider_response: object | None
    provider_response_sha256: str | None
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


SubmissionTransport = Callable[
    [str, str, Sequence[SubmissionAnswer], Sequence[SubmissionAttachment]], tuple[int, bytes]
]


def _reference_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GreenhouseSubmissionError(f"invalid {label} at {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise GreenhouseSubmissionError(f"{label} must be a JSON object: {path}")
    return payload


def _required_string(payload: Mapping[str, object], field: str, *, label: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise GreenhouseSubmissionError(f"{label} requires non-empty {field}")
    return value.strip()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _field_index(field_bundle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = field_bundle.get("fields")
    if not isinstance(rows, list) or not rows:
        raise GreenhouseSubmissionError("field bundle requires non-empty fields")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        field = row.get("field")
        if not isinstance(field, Mapping):
            continue
        name = field.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        if name in result:
            raise GreenhouseSubmissionError(f"duplicate live field identity: {name}")
        result[name] = field
    if not result:
        raise GreenhouseSubmissionError("field bundle contains no usable live fields")
    return result


def _parse_answer_values(field_type: str, value: str, field_name: str) -> tuple[tuple[str, ...], str | None]:
    if field_type != "multi_value_multi_select":
        return (value,), None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return (), f"{field_name}: multi-select answer must be an explicit JSON array"
    if not isinstance(parsed, list) or not parsed or not all(
        isinstance(item, (str, int, float, bool)) for item in parsed
    ):
        return (), f"{field_name}: multi-select answer must be a non-empty scalar JSON array"
    return tuple(str(item) for item in parsed), None


def build_greenhouse_submission_plan(
    finalization_path: Path,
    *,
    output_path: Path | None = None,
) -> GreenhouseSubmissionPlan:
    """Compile a deterministic provider submission plan from a complete finalization packet."""
    finalization_path = finalization_path.expanduser().resolve()
    finalization = _read_object(finalization_path, label="Greenhouse finalization")
    schema = _required_string(finalization, "schema", label="Greenhouse finalization")
    if schema != "glaciereq.greenhouse-application-finalization.v1":
        raise GreenhouseSubmissionError(f"unsupported finalization schema: {schema}")
    if finalization.get("ready_for_human_submission") is not True:
        unresolved = finalization.get("unresolved_required_fields")
        raise GreenhouseSubmissionError(
            f"finalization is not submission-ready; unresolved required fields: {unresolved!r}"
        )

    packet_dir = Path(_required_string(finalization, "packet_dir", label="Greenhouse finalization"))
    if not packet_dir.is_dir():
        raise GreenhouseSubmissionError(f"finalization packet directory is unavailable: {packet_dir}")
    packet_dir = packet_dir.resolve()
    field_bundle_path = packet_dir / "GREENHOUSE_APPLICATION_FIELDS.json"
    field_bundle = _read_object(field_bundle_path, label="Greenhouse field bundle")

    expected_field_receipt = _required_string(
        finalization,
        "field_bundle_receipt_sha256",
        label="Greenhouse finalization",
    )
    actual_field_receipt = _required_string(
        field_bundle,
        "receipt_sha256",
        label="Greenhouse field bundle",
    )
    if expected_field_receipt != actual_field_receipt:
        raise GreenhouseSubmissionError(
            "finalization/field-bundle lineage mismatch; refusing stale submission state"
        )

    application_id = _required_string(finalization, "application_id", label="Greenhouse finalization")
    job_id = _required_string(finalization, "opening_id", label="Greenhouse finalization")
    if str(field_bundle.get("job_id") or "").strip() != job_id:
        raise GreenhouseSubmissionError("finalization/field-bundle job identity mismatch")
    board_key = _required_string(field_bundle, "board_key", label="Greenhouse field bundle")
    submission_endpoint = (
        f"https://boards-api.greenhouse.io/v1/boards/{board_key}/jobs/{job_id}"
    )

    live_fields = _field_index(field_bundle)
    rows = finalization.get("fields")
    if not isinstance(rows, list) or not rows:
        raise GreenhouseSubmissionError("finalization requires non-empty fields")

    answers: list[SubmissionAnswer] = []
    attachments: list[SubmissionAttachment] = []
    blockers: list[str] = []
    final_field_names: set[str] = set()

    for row in rows:
        if not isinstance(row, Mapping):
            raise GreenhouseSubmissionError("finalization field rows must be objects")
        field_name = _required_string(row, "field_name", label="finalization field")
        if field_name in final_field_names:
            raise GreenhouseSubmissionError(f"duplicate finalized field identity: {field_name}")
        final_field_names.add(field_name)
        live = live_fields.get(field_name)
        if live is None:
            raise GreenhouseSubmissionError(
                f"finalized field is absent from exact live field bundle: {field_name}"
            )
        status = _required_string(row, "status", label=f"finalization field {field_name}")
        label = _required_string(live, "label", label=f"live field {field_name}")
        field_type = _required_string(live, "field_type", label=f"live field {field_name}")
        category = str(live.get("category") or "question")

        if status == "PROVIDER_MANAGED":
            continue
        if status == "ANSWER_BOUND":
            value = row.get("value")
            if not isinstance(value, str) or not value.strip():
                raise GreenhouseSubmissionError(f"answer-bound field lacks value: {field_name}")
            values, blocker = _parse_answer_values(field_type, value.strip(), field_name)
            if blocker is not None:
                blockers.append(blocker)
            raw_provenance = row.get("provenance")
            provenance = (
                tuple(str(item).strip() for item in raw_provenance if str(item).strip())
                if isinstance(raw_provenance, list)
                else ()
            )
            answers.append(
                SubmissionAnswer(
                    field_name=field_name,
                    label=label,
                    field_type=field_type,
                    category=category,
                    values=values,
                    provenance=provenance,
                )
            )
            continue
        if status == "ATTACHMENT_BOUND":
            attachment = row.get("attachment")
            if not isinstance(attachment, Mapping):
                raise GreenhouseSubmissionError(
                    f"attachment-bound field lacks attachment metadata: {field_name}"
                )
            raw_path = _required_string(
                attachment,
                "path",
                label=f"attachment for {field_name}",
            )
            path = Path(raw_path).expanduser().resolve()
            if not path.is_file():
                raise GreenhouseSubmissionError(
                    f"finalized attachment is unavailable for {field_name}: {path}"
                )
            expected_sha = _required_string(
                attachment,
                "sha256",
                label=f"attachment for {field_name}",
            )
            actual_sha = _file_sha256(path)
            if actual_sha != expected_sha:
                raise GreenhouseSubmissionError(
                    f"attachment hash drift for {field_name}; refusing mixed submission state"
                )
            expected_size = attachment.get("size_bytes")
            if not isinstance(expected_size, int) or expected_size <= 0:
                raise GreenhouseSubmissionError(
                    f"attachment for {field_name} requires positive size_bytes"
                )
            actual_size = path.stat().st_size
            if actual_size != expected_size:
                raise GreenhouseSubmissionError(
                    f"attachment size drift for {field_name}; refusing mixed submission state"
                )
            provenance = _required_string(
                attachment,
                "provenance",
                label=f"attachment for {field_name}",
            )
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            attachments.append(
                SubmissionAttachment(
                    field_name=field_name,
                    label=label,
                    path=str(path),
                    sha256=actual_sha,
                    size_bytes=actual_size,
                    mime_type=mime_type,
                    provenance=provenance,
                )
            )
            continue
        raise GreenhouseSubmissionError(
            f"submission-ready finalization contains non-final status {status!r} for {field_name}"
        )

    missing = tuple(sorted(set(live_fields) - final_field_names))
    if missing:
        raise GreenhouseSubmissionError(
            f"finalization does not cover every live field identity: {missing!r}"
        )

    final_receipt = _required_string(
        finalization,
        "receipt_sha256",
        label="Greenhouse finalization",
    )
    identity_base: dict[str, object] = {
        "application_id": application_id,
        "board_key": board_key,
        "job_id": job_id,
        "finalization_receipt_sha256": final_receipt,
        "field_bundle_receipt_sha256": actual_field_receipt,
        "answers": [item.as_dict() for item in answers],
        "attachments": [item.as_dict() for item in attachments],
    }
    idempotency_key = _reference_sha256(identity_base)
    authorization_token = hashlib.sha256(
        f"greenhouse-submit:{idempotency_key}".encode("utf-8")
    ).hexdigest()
    direct_api_eligible = not blockers
    handoff_state = (
        "DIRECT_API_READY_WHEN_EMPLOYER_KEY_AND_EXPLICIT_AUTHORIZATION_ARE_PRESENT"
        if direct_api_eligible
        else "HOSTED_FORM_HANDOFF_REQUIRED"
    )
    base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-submission-plan.v1",
        "application_id": application_id,
        "board_key": board_key,
        "job_id": job_id,
        "packet_dir": str(packet_dir),
        "finalization_path": str(finalization_path),
        "finalization_receipt_sha256": final_receipt,
        "field_bundle_receipt_sha256": actual_field_receipt,
        "submission_endpoint": submission_endpoint,
        "answers": [item.as_dict() for item in answers],
        "attachments": [item.as_dict() for item in attachments],
        "direct_api_eligible": direct_api_eligible,
        "direct_api_blockers": blockers,
        "handoff_state": handoff_state,
        "idempotency_key": idempotency_key,
        "authorization_token": authorization_token,
    }
    plan = GreenhouseSubmissionPlan(
        schema=str(base["schema"]),
        application_id=application_id,
        board_key=board_key,
        job_id=job_id,
        packet_dir=str(packet_dir),
        finalization_path=str(finalization_path),
        finalization_receipt_sha256=final_receipt,
        field_bundle_receipt_sha256=actual_field_receipt,
        submission_endpoint=submission_endpoint,
        answers=tuple(answers),
        attachments=tuple(attachments),
        direct_api_eligible=direct_api_eligible,
        direct_api_blockers=tuple(blockers),
        handoff_state=handoff_state,
        idempotency_key=idempotency_key,
        authorization_token=authorization_token,
        receipt_sha256=_reference_sha256(base),
    )
    destination = output_path or packet_dir / "GREENHOUSE_SUBMISSION_PLAN.json"
    _write_json(destination, plan.as_dict())
    return plan


def _multipart_body(
    answers: Sequence[SubmissionAnswer],
    attachments: Sequence[SubmissionAttachment],
) -> tuple[bytes, str]:
    boundary = f"----job-app-helix-{secrets.token_hex(16)}"
    chunks: list[bytes] = []

    def add_text(name: str, value: str) -> None:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    for answer in answers:
        for value in answer.values:
            add_text(answer.field_name, value)
    for attachment in attachments:
        path = Path(attachment.path)
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{attachment.field_name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode(),
                f"Content-Type: {attachment.mime_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def _post_multipart(
    endpoint: str,
    api_key: str,
    answers: Sequence[SubmissionAnswer],
    attachments: Sequence[SubmissionAttachment],
) -> tuple[int, bytes]:
    body, boundary = _multipart_body(answers, attachments)
    auth = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "job-app-helix/0.3",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30.0) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()


def _plan_from_payload(payload: Mapping[str, Any]) -> GreenhouseSubmissionPlan:
    schema = _required_string(payload, "schema", label="Greenhouse submission plan")
    if schema != "glaciereq.greenhouse-submission-plan.v1":
        raise GreenhouseSubmissionError(f"unsupported submission plan schema: {schema}")
    answers_raw = payload.get("answers")
    attachments_raw = payload.get("attachments")
    if not isinstance(answers_raw, list) or not isinstance(attachments_raw, list):
        raise GreenhouseSubmissionError("submission plan requires answers and attachments arrays")
    answers = tuple(
        SubmissionAnswer(
            field_name=_required_string(row, "field_name", label="submission answer"),
            label=_required_string(row, "label", label="submission answer"),
            field_type=_required_string(row, "field_type", label="submission answer"),
            category=_required_string(row, "category", label="submission answer"),
            values=tuple(str(value) for value in row.get("values", [])),
            provenance=tuple(str(value) for value in row.get("provenance", [])),
        )
        for row in answers_raw
        if isinstance(row, Mapping)
    )
    attachments = tuple(
        SubmissionAttachment(
            field_name=_required_string(row, "field_name", label="submission attachment"),
            label=_required_string(row, "label", label="submission attachment"),
            path=_required_string(row, "path", label="submission attachment"),
            sha256=_required_string(row, "sha256", label="submission attachment"),
            size_bytes=int(row.get("size_bytes") or 0),
            mime_type=_required_string(row, "mime_type", label="submission attachment"),
            provenance=_required_string(row, "provenance", label="submission attachment"),
        )
        for row in attachments_raw
        if isinstance(row, Mapping)
    )
    blockers_raw = payload.get("direct_api_blockers")
    blockers = (
        tuple(str(item) for item in blockers_raw) if isinstance(blockers_raw, list) else ()
    )
    return GreenhouseSubmissionPlan(
        schema=schema,
        application_id=_required_string(payload, "application_id", label="submission plan"),
        board_key=_required_string(payload, "board_key", label="submission plan"),
        job_id=_required_string(payload, "job_id", label="submission plan"),
        packet_dir=_required_string(payload, "packet_dir", label="submission plan"),
        finalization_path=_required_string(payload, "finalization_path", label="submission plan"),
        finalization_receipt_sha256=_required_string(
            payload, "finalization_receipt_sha256", label="submission plan"
        ),
        field_bundle_receipt_sha256=_required_string(
            payload, "field_bundle_receipt_sha256", label="submission plan"
        ),
        submission_endpoint=_required_string(payload, "submission_endpoint", label="submission plan"),
        answers=answers,
        attachments=attachments,
        direct_api_eligible=payload.get("direct_api_eligible") is True,
        direct_api_blockers=blockers,
        handoff_state=_required_string(payload, "handoff_state", label="submission plan"),
        idempotency_key=_required_string(payload, "idempotency_key", label="submission plan"),
        authorization_token=_required_string(payload, "authorization_token", label="submission plan"),
        receipt_sha256=_required_string(payload, "receipt_sha256", label="submission plan"),
    )


def execute_greenhouse_submission(
    plan_path: Path,
    *,
    api_key: str,
    authorization_token: str,
    transport: SubmissionTransport = _post_multipart,
    receipt_path: Path | None = None,
) -> GreenhouseSubmissionReceipt:
    """Execute one explicitly authorized provider mutation with local duplicate-attempt fencing."""
    plan_path = plan_path.expanduser().resolve()
    plan_payload = _read_object(plan_path, label="Greenhouse submission plan")
    plan = _plan_from_payload(plan_payload)
    if not plan.direct_api_eligible:
        raise GreenhouseSubmissionError(
            f"direct provider submission is blocked: {plan.direct_api_blockers!r}"
        )
    if not api_key.strip():
        raise GreenhouseSubmissionError("Greenhouse Job Board API key is required for direct POST")
    if authorization_token.strip() != plan.authorization_token:
        raise GreenhouseSubmissionError(
            "explicit authorization token does not match this exact finalized packet"
        )

    journal_path = receipt_path or Path(plan.packet_dir) / "GREENHOUSE_SUBMISSION_RECEIPT.json"
    if journal_path.exists():
        existing = _read_object(journal_path, label="Greenhouse submission receipt")
        existing_key = str(existing.get("idempotency_key") or "")
        existing_status = str(existing.get("status") or "")
        if existing_key == plan.idempotency_key and existing_status in {
            "ATTEMPT_STARTED",
            "PROVIDER_OUTCOME_UNKNOWN",
            "SUBMITTED",
        }:
            raise GreenhouseSubmissionError(
                "an attempt for this exact packet already exists; reconcile provider state before retry"
            )

    started_base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-submission-receipt.v1",
        "application_id": plan.application_id,
        "board_key": plan.board_key,
        "job_id": plan.job_id,
        "idempotency_key": plan.idempotency_key,
        "plan_receipt_sha256": plan.receipt_sha256,
        "status": "ATTEMPT_STARTED",
        "http_status": None,
        "provider_response": None,
        "provider_response_sha256": None,
    }
    started_base["receipt_sha256"] = _reference_sha256(started_base)
    _write_json(journal_path, started_base)

    try:
        status_code, response_body = transport(
            plan.submission_endpoint,
            api_key.strip(),
            plan.answers,
            plan.attachments,
        )
    except Exception as exc:
        unknown: dict[str, object] = dict(started_base)
        unknown["status"] = "PROVIDER_OUTCOME_UNKNOWN"
        unknown["provider_response"] = {"error_type": type(exc).__name__}
        unknown.pop("receipt_sha256", None)
        unknown["receipt_sha256"] = _reference_sha256(unknown)
        _write_json(journal_path, unknown)
        raise GreenhouseSubmissionError(
            "submission transport failed after attempt start; provider outcome requires reconciliation"
        ) from exc

    decoded = response_body.decode("utf-8", errors="replace")
    try:
        provider_response: object = json.loads(decoded) if decoded else None
    except json.JSONDecodeError:
        provider_response = decoded
    final_status = "SUBMITTED" if 200 <= status_code < 300 else "PROVIDER_REJECTED"
    response_sha = _bytes_sha256(response_body)
    final_base: dict[str, object] = {
        "schema": "glaciereq.greenhouse-submission-receipt.v1",
        "application_id": plan.application_id,
        "board_key": plan.board_key,
        "job_id": plan.job_id,
        "idempotency_key": plan.idempotency_key,
        "plan_receipt_sha256": plan.receipt_sha256,
        "status": final_status,
        "http_status": status_code,
        "provider_response": provider_response,
        "provider_response_sha256": response_sha,
    }
    receipt = GreenhouseSubmissionReceipt(
        schema=str(final_base["schema"]),
        application_id=plan.application_id,
        board_key=plan.board_key,
        job_id=plan.job_id,
        idempotency_key=plan.idempotency_key,
        plan_receipt_sha256=plan.receipt_sha256,
        status=final_status,
        http_status=status_code,
        provider_response=provider_response,
        provider_response_sha256=response_sha,
        receipt_sha256=_reference_sha256(final_base),
    )
    _write_json(journal_path, receipt.as_dict())
    if final_status != "SUBMITTED":
        raise GreenhouseSubmissionError(
            f"Greenhouse rejected submission with HTTP {status_code}; receipt preserved at {journal_path}"
        )
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-greenhouse-submit")
    parser.add_argument("--finalization", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--authorization")
    parser.add_argument("--api-key-env", default="GREENHOUSE_JOB_BOARD_API_KEY")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    plan = build_greenhouse_submission_plan(args.finalization, output_path=args.plan)
    if not args.submit:
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    if not args.authorization:
        raise GreenhouseSubmissionError(
            "--submit requires --authorization matching this exact plan's authorization_token"
        )
    api_key = os.environ.get(args.api_key_env, "")
    plan_path = args.plan or Path(plan.packet_dir) / "GREENHOUSE_SUBMISSION_PLAN.json"
    receipt = execute_greenhouse_submission(
        plan_path,
        api_key=api_key,
        authorization_token=args.authorization,
        receipt_path=args.receipt,
    )
    print(json.dumps(receipt.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
