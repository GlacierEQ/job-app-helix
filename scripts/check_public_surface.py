from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".yml", ".yaml", ".txt", ".sh"}
FORBIDDEN_PATH_PREFIXES = (
    ".agent-mem/",
    ".brainsync/",
    ".cursor/",
    ".gemini/",
    ".kiro/",
    ".windsurf/",
    "state/",
)
FORBIDDEN_PATH_PARTS = ("AEON-777", "__pycache__", "node_modules")
FORBIDDEN_CONTENT = {
    "file:///": "machine-local file URL",
    "/Users/": "absolute macOS user path",
    "C:\\Users\\": "absolute Windows user path",
    "AEON-777": "legal-workstream identifier",
    ".brainsync/backups": "generated IDE-memory backup",
    "PRODUCTION_READINESS_VERDICT": "unpublished local readiness artifact",
    "100% SOLID & DEPLOYABLE": "unqualified readiness claim",
}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{20,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
}
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in completed.stdout.split(b"\0") if item]


def check_paths(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(FORBIDDEN_PATH_PREFIXES):
            errors.append(f"forbidden tracked path: {relative}")
        if any(part in relative for part in FORBIDDEN_PATH_PARTS):
            errors.append(f"forbidden tracked path component: {relative}")
    return errors


def check_content(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == "scripts/check_public_surface.py":
            continue
        text = path.read_text(encoding="utf-8")
        for needle, label in FORBIDDEN_CONTENT.items():
            if needle in text:
                errors.append(f"{relative}: contains {label} ({needle!r})")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{relative}: contains a possible {label}")
    return errors


def check_markdown_links(files: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)}: link escapes repository: {raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken relative link: {raw_target}")
    return errors


def main() -> int:
    files = tracked_files()
    errors = check_paths(files) + check_content(files) + check_markdown_links(files)
    if errors:
        print("Public-surface check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Public-surface check passed for {len(files)} tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
