from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_final_form_package.py"
SOURCE_COMMIT = "c" * 40


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_final_form_package",
        BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_builder_emits_verified_numbered_package_and_deterministic_zip(
    tmp_path: Path,
) -> None:
    builder = _load_builder()
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><title>Portfolio</title>\n")
    first = builder.build_package(
        tmp_path / "first",
        source_commit=SOURCE_COMMIT,
        site_dir=site,
    )
    second = builder.build_package(
        tmp_path / "second",
        source_commit=SOURCE_COMMIT,
        site_dir=site,
    )

    assert first.zip_sha256 == second.zip_sha256
    assert first.file_count > 20
    assert first.total_bytes > 0
    assert first.zip_path.is_file()
    assert (
        first.package_dir
        / "07_LIVE_PRESENTATION"
        / "STATIC_SITE_SNAPSHOT"
        / "index.html"
    ).is_file()

    receipt = json.loads(
        (first.package_dir / "BUILD_RECEIPT.json").read_text(encoding="utf-8")
    )
    assert receipt["state"] == "VERIFIED"
    assert receipt["public_contact_scan"] == "PASSED"
    assert receipt["private_contact_included"] is False
    assert receipt["static_snapshot_included"] is True

    with zipfile.ZipFile(first.zip_path) as archive:
        names = archive.namelist()
    assert names == sorted(names)
    assert any(name.endswith("00_START_HERE/SEND_THIS.md") for name in names)
    assert any(
        name.endswith("01_RESUME/Casey_Barton_Executive_Resume.md")
        for name in names
    )
    assert any(
        name.endswith(
            "02_ROADMAP/Casey_Barton_Deployment_and_Growth_Roadmap.md"
        )
        for name in names
    )


def test_root_aliases_make_declared_navigation_literal(tmp_path: Path) -> None:
    builder = _load_builder()
    result = builder.build_package(tmp_path / "package", source_commit=SOURCE_COMMIT)
    manifest = json.loads(
        (result.package_dir / "FINAL_FORM_MANIFEST.json").read_text(encoding="utf-8")
    )

    declared = [*manifest["reading_order"], *manifest["machine_entrypoints"]]
    missing = [name for name in declared if not (result.package_dir / name).is_file()]
    assert missing == []
    assert (result.package_dir / "SEND_THIS.md").is_file()
    assert (result.package_dir / "LICENSE").is_file()


def test_private_contact_is_isolated_from_public_scan(tmp_path: Path) -> None:
    builder = _load_builder()
    contact = tmp_path / "contact.txt"
    contact.write_text(
        "Recruiter-only contact: candidate@example.invalid | (555) 123-4567\n",
        encoding="utf-8",
    )

    result = builder.build_package(
        tmp_path / "package",
        source_commit=SOURCE_COMMIT,
        contact_file=contact,
    )

    private_card = result.package_dir / "00_START_HERE" / "PRIVATE_CONTACT_CARD.txt"
    assert private_card.read_text(encoding="utf-8") == contact.read_text(encoding="utf-8")
    receipt = json.loads(
        (result.package_dir / "BUILD_RECEIPT.json").read_text(encoding="utf-8")
    )
    live_readme = (
        result.package_dir / "07_LIVE_PRESENTATION" / "README.md"
    ).read_text(encoding="utf-8")
    assert receipt["private_contact_included"] is True
    assert receipt["static_snapshot_included"] is False
    assert "No offline static snapshot was included" in live_readme


def test_integrity_verifier_fails_after_payload_tampering(tmp_path: Path) -> None:
    builder = _load_builder()
    result = builder.build_package(
        tmp_path / "package",
        source_commit=SOURCE_COMMIT,
    )
    resume = result.package_dir / "01_RESUME" / "Casey_Barton_Executive_Resume.md"
    resume.write_text(resume.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")

    with pytest.raises(builder.PackageError, match="mismatch"):
        builder.verify_package(result.package_dir)


def test_integrity_verifier_rejects_unrecorded_payload(tmp_path: Path) -> None:
    builder = _load_builder()
    result = builder.build_package(tmp_path / "package", source_commit=SOURCE_COMMIT)
    (result.package_dir / "EXTRA.txt").write_text("unrecorded\n", encoding="utf-8")

    with pytest.raises(builder.PackageError, match="does not close over payload"):
        builder.verify_package(result.package_dir)


def test_integrity_verifier_rejects_traversal_record(tmp_path: Path) -> None:
    builder = _load_builder()
    result = builder.build_package(tmp_path / "package", source_commit=SOURCE_COMMIT)
    manifest_path = result.package_dir / "INTEGRITY_MANIFEST.json"
    receipt_path = result.package_dir / "BUILD_RECEIPT.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.txt"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["integrity_manifest_sha256"] = builder._sha256(manifest_path)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(builder.PackageError, match="path traversal"):
        builder.verify_package(result.package_dir)


def test_builder_allows_only_artifact_outputs_inside_repository() -> None:
    builder = _load_builder()
    allowed = ROOT / "artifacts" / "final-form-test"

    assert builder._validate_output(allowed) == allowed.resolve()
    for forbidden in (
        ROOT,
        ROOT.parent,
        ROOT / "hire_package" / "casey-barton",
        ROOT / "scripts" / "generated",
    ):
        with pytest.raises(builder.PackageError, match="protected source"):
            builder.build_package(forbidden, source_commit=SOURCE_COMMIT)


def test_builder_rejects_invalid_source_commit(tmp_path: Path) -> None:
    builder = _load_builder()

    with pytest.raises(builder.PackageError, match="40-character lowercase SHA"):
        builder.build_package(tmp_path / "package", source_commit="not-a-commit")
