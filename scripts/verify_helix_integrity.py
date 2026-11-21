#!/usr/bin/env python3
"""Verify the helix bounded-surface hash manifest.

Exit code 0 means every declared hash matches and no unlisted source file is
present. Any drift fails the check, so the integrity surface cannot silently
stale out again.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HELIX_ROOT = Path(__file__).resolve().parents[1] / "helix"
MANIFEST_PATH = HELIX_ROOT / ".integrity" / "file_hashes.json"
IGNORED_PARTS = {"__pycache__"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def listed_source_files() -> set[str]:
    found = set()
    for path in HELIX_ROOT.rglob("*"):
        if not path.is_file() or path == MANIFEST_PATH:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        found.add(path.relative_to(HELIX_ROOT).as_posix())
    return found


def main() -> int:
    if not MANIFEST_PATH.is_file():
        print(f"FAIL: integrity manifest missing: {MANIFEST_PATH}")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    declared: dict[str, str] = manifest.get("hashes", {})
    problems: list[str] = []

    if manifest.get("file_count") != len(declared):
        problems.append(
            f"file_count {manifest.get('file_count')} does not match {len(declared)} listed hashes"
        )

    for relative, expected in sorted(declared.items()):
        path = HELIX_ROOT / relative
        if not path.is_file():
            problems.append(f"MISSING {relative}")
        elif sha256_file(path) != expected:
            problems.append(f"MISMATCH {relative}")

    unlisted = sorted(listed_source_files() - set(declared))
    for relative in unlisted:
        problems.append(f"UNLISTED {relative}")

    if problems:
        print(f"FAIL: helix integrity drift ({len(problems)} problem(s))")
        for problem in problems:
            print(f"  {problem}")
        return 1

    print(f"OK: helix integrity verified for {len(declared)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
