#!/usr/bin/env python3
"""Fail when the public repository surface leaks local or private assumptions."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "PUBLIC_READINESS.md",
    ROOT / "HELIX.md",
    ROOT / "APEX_ARCHITECTURE.md",
    ROOT / "HIERARCHICAL_PORTFOLIO_MAP.md",
    ROOT / "docs" / "REPOSITORY_BOUNDARIES.md",
)
FORBIDDEN_TEXT = ("file://", "/Users/", "\\Users\\", "~/GlacierEQ_Swarm")
FORBIDDEN_TRACKED_PREFIXES = (
    ".brainsync/",
    ".cursor/",
    ".windsurf/",
    ".kiro/",
    ".agent-mem/",
    ".gemini/",
    ".agents/",
    "elevate/elevate_p1/AEON-777/",
)
FORBIDDEN_TRACKED_FILES = {"GEMINI.md"}
PUBLIC_LEGAL_TOKENS = ("AEON-777",)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def tracked_files() -> list[str]:
    completed = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True)
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def check_entry_documents(errors: list[str]) -> None:
    for path in ENTRY_DOCUMENTS:
        if not path.is_file():
            errors.append(f"missing public entry document: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TEXT:
            if token in text:
                errors.append(f"{path.relative_to(ROOT)} contains forbidden local path token: {token}")
        for token in PUBLIC_LEGAL_TOKENS:
            if token in text:
                errors.append(f"{path.relative_to(ROOT)} contains excluded legal-project token: {token}")
        for target in MARKDOWN_LINK.findall(text):
            target = target.strip()
            if not target or target.startswith(("http://", "https://", "#", "mailto:")) or "://" in target:
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)} link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)} has broken relative link: {target}")


def check_tracked_tree(errors: list[str]) -> None:
    for tracked in tracked_files():
        if tracked in FORBIDDEN_TRACKED_FILES:
            errors.append(f"forbidden generated file is tracked: {tracked}")
        for prefix in FORBIDDEN_TRACKED_PREFIXES:
            if tracked.startswith(prefix):
                errors.append(f"forbidden generated/private path is tracked: {tracked}")
                break


def main() -> int:
    errors: list[str] = []
    check_entry_documents(errors)
    check_tracked_tree(errors)
    if errors:
        print("PUBLIC SURFACE AUDIT: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("PUBLIC SURFACE AUDIT: PASS")
    print(f"checked_documents={len(ENTRY_DOCUMENTS)} tracked_files={len(tracked_files())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
