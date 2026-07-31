from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import zipfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "hire_package" / "casey-barton"
PACKAGE_NAME = "Casey_Barton_Applied_AI_Final_Form_2026-07-30"
FIXED_ZIP_TIME = (2026, 7, 30, 12, 0, 0)
SOURCE_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Fa-f])(?:\+?1[\s().-]*)?(?:\(\d{3}\)|\d{3})"
    r"[\s.-]*\d{3}[\s.-]*\d{4}(?![0-9A-Fa-f])"
)
TEXT_SUFFIXES = {".md", ".txt", ".html", ".css", ".js", ".json", ""}
COPY_MAP = {
    "SEND_THIS.md": "00_START_HERE/SEND_THIS.md",
    "EXECUTIVE_RESUME.md": "01_RESUME/Casey_Barton_Executive_Resume.md",
    "ROADMAP.md": "02_ROADMAP/Casey_Barton_Deployment_and_Growth_Roadmap.md",
    "FINAL_FORM_README.md": "03_THREE_LAYER_PRESENTATION/FINAL_FORM_README.md",
    "ROLE_POWER_MATRIX.md": "03_THREE_LAYER_PRESENTATION/ROLE_POWER_MATRIX.md",
    "TECHNICAL_PORTFOLIO_BRIEF.md": (
        "04_TECHNICAL_DILIGENCE/TECHNICAL_PORTFOLIO_BRIEF.md"
    ),
    "CLAIM_REGISTER.md": "04_TECHNICAL_DILIGENCE/CLAIM_REGISTER.md",
    "candidate_node.json": "05_MACHINE_CONTRACTS/candidate_node.json",
    "evidence_ledger.json": "05_MACHINE_CONTRACTS/evidence_ledger.json",
    "application_spiral.json": "05_MACHINE_CONTRACTS/application_spiral.json",
    "package_mesh.json": "05_MACHINE_CONTRACTS/package_mesh.json",
    "coordinator_candidate_receipt.json": (
        "05_MACHINE_CONTRACTS/coordinator_candidate_receipt.json"
    ),
    "FINAL_FORM_MANIFEST.json": "05_MACHINE_CONTRACTS/FINAL_FORM_MANIFEST.json",
    "LICENSE_SUMMARY.md": "06_LICENSING/LICENSE_SUMMARY.md",
}
REQUIRED_PACKAGE_PATHS = {
    *COPY_MAP.values(),
    "06_LICENSING/LICENSE",
    "07_LIVE_PRESENTATION/OPEN_LIVE_PRESENTATION.html",
    "07_LIVE_PRESENTATION/README.md",
    "INTEGRITY_MANIFEST.json",
    "BUILD_RECEIPT.json",
}


class PackageError(RuntimeError):
    pass


@dataclass(frozen=True)
class FileRecord:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class BuildResult:
    package_dir: Path
    zip_path: Path
    file_count: int
    total_bytes: int
    zip_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_output(output: Path) -> Path:
    resolved = output.resolve()
    protected = (ROOT.resolve(), CANDIDATE_ROOT.resolve())
    for source in protected:
        if resolved == source or source.is_relative_to(resolved):
            raise PackageError(f"Output path contains protected source: {resolved}")
        if resolved.is_relative_to(source):
            raise PackageError(f"Output path is inside protected source: {resolved}")
    return resolved


def _copy(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise PackageError(f"Required source is missing: {source}")
    if source.is_symlink():
        raise PackageError(f"Symbolic-link source is forbidden: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _copy_candidate_assets(package_dir: Path) -> None:
    for source_name, relative_destination in COPY_MAP.items():
        _copy(CANDIDATE_ROOT / source_name, package_dir / relative_destination)
    _copy(ROOT / "LICENSE", package_dir / "06_LICENSING" / "LICENSE")


def _copy_site(site_dir: Path, package_dir: Path) -> None:
    if not site_dir.is_dir():
        raise PackageError(f"Static presentation directory is missing: {site_dir}")
    destination_root = package_dir / "07_LIVE_PRESENTATION" / "STATIC_SITE_SNAPSHOT"
    for source in sorted(site_dir.rglob("*")):
        if source.is_symlink():
            raise PackageError(f"Static presentation contains a symlink: {source}")
        if not source.is_file():
            continue
        relative = source.relative_to(site_dir)
        _copy(source, destination_root / relative)


def _write_live_entry(package_dir: Path) -> None:
    live_url = "https://glaciereq.github.io/job-app-helix/"
    presentation = package_dir / "07_LIVE_PRESENTATION"
    presentation.mkdir(parents=True, exist_ok=True)
    (presentation / "README.md").write_text(
        "# Live Presentation\n\n"
        f"Open the canonical presentation: {live_url}\n\n"
        "The adjacent static snapshot is included for offline review and integrity "
        "inspection. The live site remains the primary share link.\n",
        encoding="utf-8",
    )
    (presentation / "OPEN_LIVE_PRESENTATION.html").write_text(
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Casey Barton - Applied AI Systems Portfolio</title></head>"
        '<body><main><h1>Casey Barton - Applied AI Systems Portfolio</h1>'
        f'<p><a href="{live_url}">Open the canonical live presentation</a></p>'
        "<p>This file performs no automatic redirect.</p></main></body></html>\n",
        encoding="utf-8",
    )


def _copy_private_contact(contact_file: Path | None, package_dir: Path) -> None:
    if contact_file is None:
        return
    _copy(contact_file.resolve(), package_dir / "00_START_HERE" / "PRIVATE_CONTACT_CARD.txt")


def _public_paths(package_dir: Path) -> Iterable[Path]:
    private_path = package_dir / "00_START_HERE" / "PRIVATE_CONTACT_CARD.txt"
    for path in sorted(package_dir.rglob("*")):
        if path.is_file() and path != private_path:
            yield path


def _scan_public_surface(package_dir: Path) -> None:
    for path in _public_paths(package_dir):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PackageError(f"Expected UTF-8 public payload: {path}") from exc
        if EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text):
            relative = path.relative_to(package_dir)
            raise PackageError(f"Direct contact data leaked into public payload: {relative}")


def _payload_records(package_dir: Path) -> list[FileRecord]:
    excluded = {"INTEGRITY_MANIFEST.json", "BUILD_RECEIPT.json"}
    records: list[FileRecord] = []
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or path.name in excluded:
            continue
        records.append(
            FileRecord(
                path=path.relative_to(package_dir).as_posix(),
                bytes=path.stat().st_size,
                sha256=_sha256(path),
            )
        )
    return records


def _write_manifests(
    package_dir: Path,
    *,
    source_commit: str,
    private_contact_included: bool,
) -> tuple[int, int]:
    records = _payload_records(package_dir)
    total_bytes = sum(record.bytes for record in records)
    integrity_payload: dict[str, object] = {
        "schema": "glaciereq.final-form-integrity.v1",
        "package": PACKAGE_NAME,
        "source_repository": "GlacierEQ/job-app-helix",
        "source_commit": source_commit,
        "file_count": len(records),
        "total_bytes": total_bytes,
        "files": [asdict(record) for record in records],
    }
    integrity_path = package_dir / "INTEGRITY_MANIFEST.json"
    _write_json(integrity_path, integrity_payload)
    receipt_payload: dict[str, object] = {
        "schema": "glaciereq.final-form-build-receipt.v1",
        "package": PACKAGE_NAME,
        "state": "VERIFIED",
        "source_commit": source_commit,
        "public_contact_scan": "PASSED",
        "private_contact_included": private_contact_included,
        "license": "PROPRIETARY_SOURCE_VISIBLE",
        "integrity_manifest_sha256": _sha256(integrity_path),
        "payload_file_count": len(records),
        "payload_total_bytes": total_bytes,
    }
    _write_json(package_dir / "BUILD_RECEIPT.json", receipt_payload)
    return len(records), total_bytes


def verify_package(package_dir: Path) -> None:
    manifest_path = package_dir / "INTEGRITY_MANIFEST.json"
    receipt_path = package_dir / "BUILD_RECEIPT.json"
    if not manifest_path.is_file() or not receipt_path.is_file():
        raise PackageError("Package is missing integrity records")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "glaciereq.final-form-integrity.v1":
        raise PackageError("Unsupported integrity manifest schema")
    if receipt.get("state") != "VERIFIED":
        raise PackageError("Build receipt is not VERIFIED")
    actual_paths = {
        path.relative_to(package_dir).as_posix()
        for path in package_dir.rglob("*")
        if path.is_file()
    }
    missing_required = sorted(REQUIRED_PACKAGE_PATHS - actual_paths)
    if missing_required:
        raise PackageError(f"Package is missing required paths: {missing_required}")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise PackageError("Integrity manifest has no file records")
    for raw in records:
        if not isinstance(raw, dict):
            raise PackageError(f"Invalid integrity record: {raw}")
        relative = raw.get("path")
        if not isinstance(relative, str):
            raise PackageError(f"Integrity record has no path: {raw}")
        path = (package_dir / relative).resolve()
        if not path.is_relative_to(package_dir.resolve()) or not path.is_file():
            raise PackageError(f"Integrity path is missing or escapes package: {relative}")
        if path.stat().st_size != raw.get("bytes"):
            raise PackageError(f"Byte count mismatch: {relative}")
        if _sha256(path) != raw.get("sha256"):
            raise PackageError(f"SHA-256 mismatch: {relative}")
    _scan_public_surface(package_dir)


def _write_zip(package_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(package_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = Path(PACKAGE_NAME) / path.relative_to(package_dir)
            info = zipfile.ZipInfo(relative.as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build_package(
    output: Path,
    *,
    source_commit: str,
    site_dir: Path | None = None,
    contact_file: Path | None = None,
) -> BuildResult:
    output = _validate_output(output)
    if (
        source_commit != "local-uncommitted"
        and SOURCE_COMMIT_PATTERN.fullmatch(source_commit) is None
    ):
        raise PackageError("source commit must be a 40-character lowercase SHA")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    package_dir = output / PACKAGE_NAME
    package_dir.mkdir()

    _copy_candidate_assets(package_dir)
    _write_live_entry(package_dir)
    if site_dir is not None:
        _copy_site(site_dir.resolve(), package_dir)
    _copy_private_contact(contact_file, package_dir)
    _scan_public_surface(package_dir)
    file_count, total_bytes = _write_manifests(
        package_dir,
        source_commit=source_commit,
        private_contact_included=contact_file is not None,
    )
    verify_package(package_dir)
    zip_path = output / f"{PACKAGE_NAME}.zip"
    _write_zip(package_dir, zip_path)
    return BuildResult(
        package_dir=package_dir,
        zip_path=zip_path,
        file_count=file_count,
        total_bytes=total_bytes,
        zip_sha256=_sha256(zip_path),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and verify the Casey Barton final-form recruiter package"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "final-form-package",
    )
    parser.add_argument(
        "--source-commit",
        default=os.environ.get("GITHUB_SHA", "local-uncommitted"),
    )
    parser.add_argument("--site-dir", type=Path)
    parser.add_argument("--contact-file", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_package(
            args.output,
            source_commit=str(args.source_commit),
            site_dir=args.site_dir,
            contact_file=args.contact_file,
        )
    except PackageError as exc:
        print(f"Final-form package failed closed: {exc}")
        return 1
    print(
        "Final-form package VERIFIED: "
        f"files={result.file_count} bytes={result.total_bytes} "
        f"zip_sha256={result.zip_sha256} path={result.zip_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
