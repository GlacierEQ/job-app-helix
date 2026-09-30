#!/usr/bin/env python3
"""Classify Helix files and fail on obvious copied child-repository payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "status" / "portfolio-provenance-census.json"

HELIX_NATIVE_PREFIXES = (
    ".github/",
    "docs/",
    "manifests/",
    "proto/",
    "scripts/",
    "src/job_app_helix/",
    "tests/",
)
GENERATED_PREFIXES = ("site/", "status/", "receipts/")
FIXTURE_PARTS = {"fixtures", "fixture", "samples", "sample_data"}
FORBIDDEN_DIR_NAMES = {
    "copied_repositories",
    "repository_copies",
    "repo_copies",
    "source_mirrors",
    "vendored_repositories",
}
SOURCE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".swift", ".cpp", ".c", ".h"
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative: Path) -> tuple[str, list[str]]:
    posix = relative.as_posix()
    parts = set(relative.parts)
    reasons: list[str] = []

    if parts & FORBIDDEN_DIR_NAMES:
        return "FORBIDDEN_COPY", ["path contains a forbidden copied-repository directory"]
    if parts & FIXTURE_PARTS:
        return "TEST_FIXTURE", ["path is explicitly fixture or sample scoped"]
    if posix.startswith(GENERATED_PREFIXES):
        return "GENERATED_PROJECTION", ["path is under a generated or receipt surface"]
    if posix.startswith(HELIX_NATIVE_PREFIXES) or relative.name in {
        "README.md", "LICENSE", "pyproject.toml", "uv.lock", ".gitignore"
    }:
        return "HELIX_NATIVE", ["path belongs to the Helix control plane"]
    if posix.startswith("hire_package/"):
        return "GENERATED_PROJECTION", ["candidate package is a generated presentation surface"]
    if relative.suffix.lower() in SOURCE_SUFFIXES:
        reasons.append("source-like file outside recognized Helix-native implementation roots")
        return "HARD_COPY_CANDIDATE", reasons
    return "HELIX_NATIVE", ["unclassified project artifact defaults to Helix-native review scope"]


def census(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root)
        classification, reasons = classify(relative)
        counts[classification] = counts.get(classification, 0) + 1
        files.append(
            {
                "path": relative.as_posix(),
                "classification": classification,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "reasons": reasons,
            }
        )

    forbidden = [item["path"] for item in files if item["classification"] == "FORBIDDEN_COPY"]
    candidates = [item["path"] for item in files if item["classification"] == "HARD_COPY_CANDIDATE"]
    return {
        "schema": "glaciereq.portfolio.provenance-census.v1",
        "root": ".",
        "counts": counts,
        "forbidden": forbidden,
        "hard_copy_candidates": candidates,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = census(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "counts": report["counts"],
        "forbidden": report["forbidden"],
        "hard_copy_candidates": report["hard_copy_candidates"],
        "output": str(args.output),
    }, indent=2))

    if args.check and report["forbidden"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
