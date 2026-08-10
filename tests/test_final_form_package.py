from __future__ import annotations

import importlib.util
import json
import re
import sys
import tomli as tomllib
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hire_package" / "casey-barton"
BUILDER = ROOT / "scripts" / "build_recruiter_site.py"
SOURCE_COMMIT = "b" * 40
EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Fa-f])(?:\+?1[\s().-]*)?(?:\(\d{3}\)|\d{3})"
    r"[\s.-]*\d{3}[\s.-]*\d{4}(?![0-9A-Fa-f])"
)


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_recruiter_site", BUILDER)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_final_form_manifest_routes_every_declared_asset() -> None:
    manifest = json.loads(
        (PACKAGE / "FINAL_FORM_MANIFEST.json").read_text(encoding="utf-8")
    )

    assert manifest["schema"] == "glaciereq.candidate-final-form-manifest.v1"
    assert manifest["canonical_url"] == "https://casey-barton-glaciereq.vercel.app/"
    assert manifest["deploy_repository"] == "GlacierEQ/job-application"
    assert manifest["public_surface_policy"]["sole_share_url"] == (
        "https://casey-barton-glaciereq.vercel.app/"
    )
    assert "https://glaciereq.github.io/job-app-helix/" in (
        manifest["public_surface_policy"]["forbidden_share_urls"]
    )
    assert manifest["license"]["state"] == "PROPRIETARY_SOURCE_VISIBLE"
    assert manifest["truth_policy"]["fail_closed"] is True
    assert manifest["reading_order"][:2] == ["EXECUTIVE_RESUME.md", "ROADMAP.md"]

    declared = [*manifest["reading_order"], *manifest["machine_entrypoints"]]
    missing = [name for name in declared if not (PACKAGE / name).is_file()]
    assert missing == []


def test_public_hire_package_locks_canonical_share_url() -> None:
    """Primary share surfaces must use Vercel; dead/wrong URLs only as forbid lists."""
    required = "https://casey-barton-glaciereq.vercel.app/"
    send_this = (PACKAGE / "SEND_THIS.md").read_text(encoding="utf-8")
    resume = (PACKAGE / "EXECUTIVE_RESUME.md").read_text(encoding="utf-8")
    final_readme = (PACKAGE / "FINAL_FORM_README.md").read_text(encoding="utf-8")
    claim = (PACKAGE / "CLAIM_REGISTER.md").read_text(encoding="utf-8")
    manifest = json.loads(
        (PACKAGE / "FINAL_FORM_MANIFEST.json").read_text(encoding="utf-8")
    )

    # Primary share link is the first bold/URL block in SEND_THIS.
    assert send_this.splitlines()[4].strip() == f"**{required}**"
    assert resume.splitlines()[4].startswith(f"Portfolio: {required}")
    assert "Start here:** https://casey-barton-glaciereq.vercel.app/" in final_readme
    assert "Only share:** https://casey-barton-glaciereq.vercel.app/" in claim
    assert manifest["canonical_url"] == required
    assert manifest["three_layer_surfaces"]["public_site"] == required
    # Explicitly catalogued as forbidden so agents do not re-promote them.
    forbidden = set(manifest["public_surface_policy"]["forbidden_share_urls"])
    assert "https://glaciereq.github.io/job-app-helix/" in forbidden
    assert "https://job-application.vercel.app/" in forbidden


def test_candidate_and_role_power_surfaces_have_three_distinct_layers() -> None:
    final_readme = (PACKAGE / "FINAL_FORM_README.md").read_text(encoding="utf-8")
    role_matrix = (PACKAGE / "ROLE_POWER_MATRIX.md").read_text(encoding="utf-8")

    for marker in (
        "## Layer 1 - Recruiters, Hiring Leaders, and Human Decision-Makers",
        "## Layer 2 - Senior Engineers, Architects, and Technical Diligence",
        "## Layer 3 - ATS, AI Systems, Agents, and Toolchains",
    ):
        assert marker in final_readme

    for role in (
        "Applied AI Architect",
        "Forward-Deployed AI Engineer",
        "Agent Infrastructure Engineer",
        "AI Solutions Architect",
    ):
        assert role in role_matrix
    assert role_matrix.count("### Layer 1 - Human value") == 4
    assert role_matrix.count("### Layer 2 - Engineering scope") == 4
    assert role_matrix.count("### Layer 3 - ATS / AI routing") == 4


def test_public_final_form_docs_exclude_direct_contact_pii() -> None:
    public_docs = (
        "EXECUTIVE_RESUME.md",
        "ROADMAP.md",
        "FINAL_FORM_README.md",
        "ROLE_POWER_MATRIX.md",
        "SEND_THIS.md",
        "LICENSE_SUMMARY.md",
    )
    for name in public_docs:
        text = (PACKAGE / name).read_text(encoding="utf-8")
        assert EMAIL_PATTERN.search(text) is None, name
        assert PHONE_PATTERN.search(text) is None, name


def test_current_distribution_is_explicitly_proprietary() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    normalized_license = " ".join(license_text.split())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = project["project"]["classifiers"]

    assert "PROPRIETARY" in license_text
    assert "LIMITED EVALUATION PERMISSION" in license_text
    assert "previously granted rights are not retroactively revoked" in normalized_license
    assert "License :: Other/Proprietary License" in classifiers
    assert "License :: OSI Approved :: MIT License" not in classifiers


def test_final_site_build_exposes_pinned_final_form_paths(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"

    builder.build(output, SOURCE_COMMIT)

    index = (output / "index.html").read_text(encoding="utf-8")
    assert "Final-form package" in index
    assert "Open 30/60/90 roadmap" in index
    assert "Read the three-layer story" in index
    assert "Route by role" in index
    assert "Proprietary licensing" in index
    assert f"/blob/{SOURCE_COMMIT}/hire_package/casey-barton/ROADMAP.md" in index
    assert f"/blob/{SOURCE_COMMIT}/hire_package/casey-barton/FINAL_FORM_README.md" in index
    assert f"/blob/{SOURCE_COMMIT}/hire_package/casey-barton/ROLE_POWER_MATRIX.md" in index
    assert f"/blob/{SOURCE_COMMIT}/hire_package/casey-barton/FINAL_FORM_MANIFEST.json" in index
    assert "{{" not in index and "}}" not in index


def test_one_shot_hardening_authority_is_absent() -> None:
    forbidden = (
        ROOT / ".github" / "workflows" / "final-review-hardening.yml",
        ROOT / ".github" / "workflows" / "dispatch-final-review-hardening.yml",
        ROOT / "scripts" / "apply_final_review_fixes.py",
    )
    assert [path for path in forbidden if path.exists()] == []
