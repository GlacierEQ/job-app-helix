#!/usr/bin/env python3
"""Sanitize or gate BrainSync artifacts that embed absolute local paths.

BrainSync (IDE extension) writes machine-local paths into generated files
(rootPath, projectPath, sourcePath, Full workspace path, sync-state keys).
Those files must not be committed.

Modes:
  check   Fail if tracked/staged paths still contain absolute local roots.
  scrub   Rewrite files in-place: absolute repo root → "." (repo-relative).

Examples:
  python3 helix/automations/brainsync_path_sanitize.py check
  python3 helix/automations/brainsync_path_sanitize.py scrub --path .brainsync/memory.jsonl
  python3 helix/automations/brainsync_path_sanitize.py check --staged
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Absolute path patterns that must not land in commits.
ABS_PATH_RE = re.compile(
    r"(?:/Users/[^/\s\"']+|/home/[^/\s\"']+|[A-Za-z]:\\\\Users\\\\[^\\\s\"']+|"
    r"[A-Za-z]:/Users/[^/\s\"']+)"
)

# JSON keys BrainSync uses for workspace absolute paths.
PATH_KEYS = frozenset({"rootPath", "projectPath", "sourcePath", "path", "workspacePath"})

DEFAULT_SCAN_GLOBS = (
    ".brainsync/**",
    "AGENTS.md",
    "GEMINI.md",
    "CLAUDE.md",
    "AGENT.md",
    ".cursor/active-context.md",
    ".cursor/rules/brainsync.mdc",
    ".windsurf/rules/brainsync.md",
    ".kiro/steering/brainsync.md",
    ".agents/rules/brainsyncory.md",
    ".mcp.json",
    ".vscode/mcp.json",
)


def git_repo_root() -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return REPO_ROOT


def list_tracked(paths: Iterable[str] | None = None) -> list[Path]:
    cmd = ["git", "ls-files", "-z"]
    if paths:
        cmd.extend(paths)
    try:
        raw = subprocess.check_output(cmd, cwd=REPO_ROOT)
    except subprocess.CalledProcessError:
        return []
    if not raw:
        return []
    return [REPO_ROOT / p for p in raw.decode().split("\0") if p]


def list_staged(*, include_deletions: bool = False) -> list[Path]:
    """List staged paths. Default: only add/copy/modify (content that would ship)."""
    # ACM = Added / Copied / Modified. Deletions remove path leaks and must pass.
    filters = "ACMD" if include_deletions else "ACM"
    try:
        raw = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", f"--diff-filter={filters}", "-z"],
            cwd=REPO_ROOT,
        )
    except subprocess.CalledProcessError:
        return []
    if not raw:
        return []
    return [REPO_ROOT / p for p in raw.decode().split("\0") if p]


def iter_default_files() -> list[Path]:
    """Resolve default scan set from working tree (tracked or local).

    Skips `.brainsync/backups/**` — historical snapshots stay local and are
    gitignored; scrubbing hundreds of them is wasteful.
    """
    found: list[Path] = []
    for pattern in DEFAULT_SCAN_GLOBS:
        if "**" in pattern:
            base, _, _rest = pattern.partition("/**")
            base_path = REPO_ROOT / base
            if not base_path.is_dir():
                continue
            for p in base_path.rglob("*"):
                if not p.is_file():
                    continue
                if p.name.endswith((".db", ".db-shm", ".db-wal")):
                    continue
                # Never rewrite backup snapshots by default
                try:
                    rel_parts = p.relative_to(REPO_ROOT).parts
                except ValueError:
                    rel_parts = p.parts
                if (
                    len(rel_parts) >= 2
                    and rel_parts[0] == ".brainsync"
                    and rel_parts[1] == "backups"
                ):
                    continue
                found.append(p)
        else:
            p = REPO_ROOT / pattern
            if p.is_file():
                found.append(p)
    return found


def absolute_hits(text: str) -> list[str]:
    return ABS_PATH_RE.findall(text)


def scrub_text(text: str, repo_root: Path) -> str:
    """Replace absolute repo root with '.' and drop home-prefixed abs paths generically."""
    root = str(repo_root)
    # POSIX + trailing slash variants
    variants = {
        root,
        root + "/",
        root + os.sep if not root.endswith(os.sep) else root,
    }
    # Also normalize realpath
    try:
        real = str(repo_root.resolve())
        variants.add(real)
        variants.add(real + "/")
    except OSError:
        pass

    out = text
    # Prefer longest prefix; replace `root/` with `./` so nested paths stay valid.
    for v in sorted(variants, key=len, reverse=True):
        if v.endswith("/") or v.endswith("\\"):
            out = out.replace(v, "./")
        else:
            # Bare root value → "."; root as path prefix handled via slash variants.
            out = out.replace(f'"{v}"', '"."')
            out = out.replace(v + "/", "./")
            out = out.replace(v + "\\", "./")
            out = out.replace(v, ".")

    # JSON path fields that still point at other abs locations → relative placeholder
    def _json_path_replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        val = match.group(2)
        if ABS_PATH_RE.search(val):
            # Prefer repo-relative if under root
            for v in variants:
                base = v.rstrip("/\\")
                if val == base:
                    return f'"{key}": "."'
                if val.startswith(base + "/") or val.startswith(base + "\\"):
                    rel = val[len(base) :].lstrip("/\\")
                    return f'"{key}": "{rel or "."}"'
            return f'"{key}": "."'
        return match.group(0)

    out = re.sub(
        r'"(rootPath|projectPath|sourcePath|workspacePath)"\s*:\s*"([^"]*)"',
        _json_path_replacer,
        out,
    )

    # Markdown "Full workspace path: /abs/..."
    out = re.sub(
        r"(Full workspace path:\s*)(/Users/[^\s]+|/home/[^\s]+)",
        r"\1.",
        out,
    )
    out = re.sub(
        r"(Project path:\s*)(/Users/[^\s]+|/home/[^\s]+)",
        r"\1.",
        out,
    )

    # Remaining home abs paths outside this repo: redact (do not invent fake relatives).
    # Replacing only `/Users/you` with `.` would turn `/Users/you/.config/x` into
    # `./.config/x`, which is wrong and can break local tooling (e.g. .mcp.json).
    out = ABS_PATH_RE.sub("<local-abs-path>", out)
    return out


def scrub_jsonl_line(line: str, repo_root: Path) -> str:
    line = line.rstrip("\n")
    if not line.strip():
        return line
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return scrub_text(line, repo_root)

    def walk(node: object) -> object:
        if isinstance(node, dict):
            out: dict = {}
            for k, v in node.items():
                if k in PATH_KEYS and isinstance(v, str) and ABS_PATH_RE.search(v):
                    root = str(repo_root)
                    if v.startswith(root):
                        rel = v[len(root) :].lstrip("/\\")
                        out[k] = rel or "."
                    else:
                        out[k] = "."
                else:
                    out[k] = walk(v)
            return out
        if isinstance(node, list):
            return [walk(x) for x in node]
        if isinstance(node, str) and ABS_PATH_RE.search(node):
            return scrub_text(node, repo_root)
        return node

    return json.dumps(walk(obj), ensure_ascii=False, separators=(",", ":"))


def scrub_file(path: Path, repo_root: Path) -> bool:
    """Return True if file content changed."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    if path.suffix == ".jsonl":
        lines = [scrub_jsonl_line(ln, repo_root) for ln in raw.splitlines()]
        new = "\n".join(lines)
        if raw.endswith("\n"):
            new += "\n"
    elif path.suffix == ".json":
        try:
            data = json.loads(raw)
            text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            # re-load via text scrub for key rewrite then pretty-print again
            scrubbed = scrub_text(text, repo_root)
            try:
                data2 = json.loads(scrubbed)
                new = json.dumps(data2, indent=2, ensure_ascii=False) + "\n"
            except json.JSONDecodeError:
                new = scrubbed
        except json.JSONDecodeError:
            new = scrub_text(raw, repo_root)
    else:
        new = scrub_text(raw, repo_root)

    if new != raw:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def check_files(files: list[Path]) -> list[tuple[Path, list[str]]]:
    failures: list[tuple[Path, list[str]]] = []
    for path in files:
        if not path.is_file():
            continue
        # skip binary-ish
        if path.suffix in {".db", ".db-shm", ".db-wal", ".png", ".jpg", ".pdf"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits = absolute_hits(text)
        if hits:
            # unique sample
            sample = sorted(set(hits))[:5]
            failures.append((path, sample))
    return failures


def cmd_check(args: argparse.Namespace) -> int:
    if args.staged:
        files = list_staged()
        # only care about brainsync-ish / path-leaky names
        files = [
            p
            for p in files
            if ".brainsync" in p.parts
            or p.name
            in {
                "AGENTS.md",
                "GEMINI.md",
                "CLAUDE.md",
                "AGENT.md",
                "brainsync.md",
                "brainsync.mdc",
                "brainsyncory.md",
                "active-context.md",
                "mcp.json",
            }
            or p.name.endswith("mcp.json")
        ]
    elif args.path:
        files = [Path(p).resolve() for p in args.path]
    else:
        # tracked BrainSync artifacts only (what would ship)
        files = list_tracked([".brainsync", "AGENTS.md", "GEMINI.md", "CLAUDE.md", "AGENT.md"])
        # also common mirrors if still tracked
        files.extend(
            list_tracked(
                [
                    ".cursor/active-context.md",
                    ".cursor/rules/brainsync.mdc",
                    ".windsurf/rules/brainsync.md",
                    ".kiro/steering/brainsync.md",
                    ".agents/rules/brainsyncory.md",
                    ".mcp.json",
                    ".vscode/mcp.json",
                ]
            )
        )
        # de-dupe
        files = list(dict.fromkeys(files))

    failures = check_files(files)
    if not failures:
        print("brainsync_path_sanitize: OK — no absolute local paths in scanned set")
        return 0

    print("brainsync_path_sanitize: FAIL — absolute local paths found:", file=sys.stderr)
    for path, sample in failures:
        rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
        print(f"  {rel}: {', '.join(sample)}", file=sys.stderr)
    print(
        "\nFix: ensure .gitignore covers BrainSync generated files, then:\n"
        "  git rm -r --cached .brainsync/memory.jsonl .brainsync/index.json ...\n"
        "Or scrub local copies:\n"
        "  python3 helix/automations/brainsync_path_sanitize.py scrub --path <file>",
        file=sys.stderr,
    )
    return 1


def cmd_scrub(args: argparse.Namespace) -> int:
    repo = git_repo_root()
    targets = [Path(p).resolve() for p in args.path] if args.path else iter_default_files()

    changed = 0
    for path in targets:
        if scrub_file(path, repo):
            rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
            print(f"scrubbed: {rel}")
            changed += 1
    print(f"brainsync_path_sanitize: scrubbed {changed} file(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="Fail if absolute local paths present")
    p_check.add_argument("--staged", action="store_true", help="Only check staged files")
    p_check.add_argument("--path", action="append", help="Explicit path(s) to check")
    p_check.set_defaults(func=cmd_check)

    p_scrub = sub.add_parser("scrub", help="Rewrite absolute paths to repo-relative")
    p_scrub.add_argument("--path", action="append", help="Explicit path(s) to scrub")
    p_scrub.set_defaults(func=cmd_scrub)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
