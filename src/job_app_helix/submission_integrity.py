from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class SubmissionIntegrityError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArtifactRecord:
    name: str
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class ArtifactSet:
    application_id: str
    artifacts: tuple[ArtifactRecord, ...]
    digest: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "glaciereq.application-artifact-set.v1",
            "application_id": self.application_id,
            "artifact_count": len(self.artifacts),
            "artifact_set_digest": self.digest,
            "artifacts": [asdict(item) for item in self.artifacts],
        }


def build_artifact_set(packet: Mapping[str, Any]) -> ArtifactSet:
    application_id = str(packet.get("application_id") or "").strip()
    if not application_id:
        raise SubmissionIntegrityError("application packet has no application_id")

    raw_artifacts = packet.get("artifacts")
    if not isinstance(raw_artifacts, Mapping):
        raise SubmissionIntegrityError("application packet has no artifact mapping")
    if len(raw_artifacts) < 2:
        raise SubmissionIntegrityError(
            "multi-artifact submission requires at least two declared artifacts"
        )

    records: list[ArtifactRecord] = []
    seen_paths: set[str] = set()
    for name, raw_path in sorted(raw_artifacts.items(), key=lambda item: str(item[0])):
        artifact_name = str(name).strip()
        path = Path(str(raw_path)).expanduser().resolve()
        if not artifact_name:
            raise SubmissionIntegrityError("artifact name may not be empty")
        if not path.is_file():
            raise SubmissionIntegrityError(f"artifact is missing: {artifact_name} -> {path}")
        normalized = str(path)
        if normalized in seen_paths:
            raise SubmissionIntegrityError(f"duplicate artifact path: {path}")
        seen_paths.add(normalized)
        records.append(
            ArtifactRecord(
                name=artifact_name,
                path=normalized,
                bytes=path.stat().st_size,
                sha256=_sha256(path),
            )
        )

    digest_payload = [
        {
            "name": record.name,
            "bytes": record.bytes,
            "sha256": record.sha256,
        }
        for record in records
    ]
    return ArtifactSet(
        application_id=application_id,
        artifacts=tuple(records),
        digest=_canonical_digest(digest_payload),
    )


def write_artifact_set_manifest(
    packet: Mapping[str, Any],
    output_dir: Path,
) -> Mapping[str, Any]:
    artifact_set = build_artifact_set(packet)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "ARTIFACT_SET_MANIFEST.json"
    payload = {
        **artifact_set.as_dict(),
        "state": "PREPARED_NOT_SUBMITTED",
        "submission_performed": False,
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "artifact_set": artifact_set,
        "manifest_path": str(path),
        "artifact_set_digest": artifact_set.digest,
    }


def verify_external_submission_receipt(
    artifact_set: ArtifactSet,
    receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    if receipt.get("status") != "ACCEPTED_ARTIFACT_SET_VERIFIED":
        raise SubmissionIntegrityError(
            "external receipt does not prove accepted artifact-set integrity"
        )
    external_reference = str(receipt.get("external_reference") or "").strip()
    if not external_reference:
        raise SubmissionIntegrityError("external receipt has no external reference")
    if receipt.get("artifact_set_digest") != artifact_set.digest:
        raise SubmissionIntegrityError("external artifact-set digest mismatch")

    raw_accepted = receipt.get("accepted_artifacts")
    if not isinstance(raw_accepted, list):
        raise SubmissionIntegrityError("external receipt has no accepted artifact list")
    accepted: dict[str, str] = {}
    for row in raw_accepted:
        if not isinstance(row, Mapping):
            raise SubmissionIntegrityError("invalid accepted artifact record")
        name = str(row.get("name") or "").strip()
        digest = str(row.get("sha256") or "").strip()
        if not name or not digest:
            raise SubmissionIntegrityError("accepted artifact record is incomplete")
        if name in accepted:
            raise SubmissionIntegrityError(f"duplicate accepted artifact: {name}")
        accepted[name] = digest

    intended = {record.name: record.sha256 for record in artifact_set.artifacts}
    if accepted != intended:
        missing = sorted(set(intended) - set(accepted))
        unexpected = sorted(set(accepted) - set(intended))
        changed = sorted(
            name
            for name in set(intended) & set(accepted)
            if intended[name] != accepted[name]
        )
        raise SubmissionIntegrityError(
            "external handoff changed the intended artifact set: "
            f"missing={missing} unexpected={unexpected} changed={changed}"
        )

    return {
        "status": "SUBMITTED_VERIFIED",
        "submission_performed": True,
        "external_reference": external_reference,
        "artifact_set_digest": artifact_set.digest,
        "accepted_artifact_count": len(accepted),
    }
