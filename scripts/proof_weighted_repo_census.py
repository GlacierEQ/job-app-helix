#!/usr/bin/env python3
"""Proof-weighted structural and executable census for one portfolio repository.

The census is intentionally conservative. It does not install project dependencies,
execute package lifecycle scripts, or convert a README claim into implementation
proof. It records what can be observed and safely executed in the audit runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "vendor",
    "dist", "build", "target", ".pytest_cache", "__pycache__", ".mypy_cache",
    ".ruff_cache", ".next", ".turbo", "coverage", ".coverage",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".c": "C", ".h": "C/C++",
    ".cc": "C++", ".cpp": "C++", ".cxx": "C++", ".hpp": "C++", ".java": "Java",
    ".kt": "Kotlin", ".swift": "Swift", ".zig": "Zig", ".odin": "Odin",
    ".mojo": "Mojo", ".cu": "CUDA", ".sql": "SQL", ".proto": "Protobuf",
    ".wat": "WebAssembly", ".wasm": "WebAssembly", ".lean": "Lean 4",
    ".v": "Verilog/Coq", ".sv": "SystemVerilog", ".vhd": "VHDL", ".vhdl": "VHDL",
    ".scala": "Scala/Chisel", ".hs": "Haskell", ".ex": "Elixir", ".exs": "Elixir",
    ".jl": "Julia", ".r": "R", ".R": "R", ".onnx": "ONNX", ".mlir": "MLIR",
    ".fbs": "FlatBuffers", ".capnp": "Cap'n Proto", ".agda": "Agda",
    ".php": "PHP", ".rb": "Ruby", ".sh": "Shell", ".ps1": "PowerShell",
}

SOURCE_SUFFIXES = set(LANGUAGE_BY_SUFFIX)
TEST_NAME = re.compile(r"(^test[_-]|[_-]test\.|[_-]tests?\.|\.spec\.|\.test\.)", re.I)

RECRUITER_TERMS = (
    "for recruiters", "for hiring managers", "for recruiters and non-specialists",
    "executive summary", "why it matters", "business value", "for non-technical",
)
ENGINEER_TERMS = (
    "for engineers", "for senior engineers", "technical architecture", "architecture",
    "failure modes", "tradeoffs", "verification", "testing", "limitations",
)
AI_TERMS = (
    "for ai systems", "programmatic mesh", "ai ingestion", "repository mesh",
    "machine-readable", "protobuf", "canonical graph", "mcp tool",
)

CLAIM_PATTERNS = {
    "universal_success": re.compile(r"\b(?:100%|zero failures?|all tests pass|fully operational)\b", re.I),
    "production_claim": re.compile(r"\b(?:production[- ]grade|production[- ]ready|enterprise[- ]ready|flight[- ]ready|battle[- ]tested)\b", re.I),
    "latency_or_throughput": re.compile(r"\b(?:sub[- ]?\d+\s*(?:ms|millisecond)|\d[\d,]*(?:\+)?\s*(?:packets?|requests?|tokens?|events?)\s*/?\s*(?:s|sec|second)|\d+(?:\.\d+)?%\s*(?:availability|uptime|accuracy))\b", re.I),
    "deployment_claim": re.compile(r"\b(?:deployed|in production|operational deployment|powers?\s+\d|manages?\s+\d[\d,]*)\b", re.I),
    "employment_claim": re.compile(r"\b(?:at|for)\s+(?:OpenAI|Anthropic|xAI|SpaceX|NVIDIA|Google|Microsoft|Apple)\b", re.I),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def read_metadata(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".tox")]
        base = Path(current)
        for name in files:
            path = base / name
            try:
                if path.is_symlink() or path.stat().st_size > 5_000_000:
                    continue
            except OSError:
                continue
            yield path


def count_text_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except OSError:
        return 0


def read_readme(root: Path) -> tuple[Path | None, str]:
    candidates = [
        root / "README.md", root / "Readme.md", root / "readme.md",
        root / "README.rst", root / "README.txt",
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return path, path.read_text(encoding="utf-8", errors="ignore")
    return None, ""


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def run_pytest(root: Path, timeout: int) -> dict[str, Any]:
    tests = [path for path in iter_files(root) if TEST_NAME.search(path.name) and path.suffix == ".py"]
    if not tests:
        return {"status": "NO_TEST_PATH", "command": None, "exit_code": None, "summary": "No Python test files detected."}

    command = [sys.executable, "-m", "pytest", "-q"]
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else ""
        return {"status": "BLOCKED_TIMEOUT", "command": command, "exit_code": 124, "summary": output}

    output = proc.stdout[-12000:]
    if proc.returncode == 0:
        status = "VERIFIED"
    elif re.search(r"(?:ModuleNotFoundError|ImportError:|No module named|command not found|could not find)", output, re.I):
        status = "BLOCKED_DEPENDENCY"
    elif proc.returncode == 5 and re.search(r"no tests ran", output, re.I):
        status = "NO_TEST_PATH"
    else:
        status = "FAILED"
    return {"status": status, "command": command, "exit_code": proc.returncode, "summary": output}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_admission(metadata: dict[str, Any], readme_text: str) -> str:
    if metadata.get("private") or metadata.get("visibility") == "private":
        return "private_excluded"
    if metadata.get("archived"):
        return "archive_or_retired"
    if metadata.get("fork"):
        return "supporting_reference_fork"
    if not readme_text.strip():
        return "candidate_missing_readme"
    return "candidate_original_public"


def main() -> int:
    args = parse_args()
    root = args.path.resolve()
    metadata = read_metadata(args.metadata)
    readme_path, readme = read_readme(root)

    languages: Counter[str] = Counter()
    source_files = 0
    source_lines = 0
    test_files = 0
    workflow_files = 0
    total_files = 0

    for path in iter_files(root):
        total_files += 1
        relative = path.relative_to(root)
        suffix = path.suffix
        if suffix in SOURCE_SUFFIXES:
            language = LANGUAGE_BY_SUFFIX[suffix]
            languages[language] += 1
            source_files += 1
            source_lines += count_text_lines(path)
        if TEST_NAME.search(path.name) or "tests" in {part.casefold() for part in relative.parts}:
            test_files += 1
        if relative.parts[:2] == (".github", "workflows") and suffix in {".yml", ".yaml"}:
            workflow_files += 1

    local_links = re.findall(r"(?:file://|/Users/|[A-Za-z]:\\\\Users\\\\)[^\s)\]>'\"]+", readme)
    claims = {name: len(pattern.findall(readme)) for name, pattern in CLAIM_PATTERNS.items()}
    python_result = run_pytest(root, args.timeout)

    audience = {
        "recruiter": has_any(readme, RECRUITER_TERMS),
        "expert": has_any(readme, ENGINEER_TERMS),
        "ai_mesh": has_any(readme, AI_TERMS),
    }
    audience_score = sum(audience.values())

    result = {
        "schema": "glaciereq.portfolio.audit.v1",
        "repository": args.repo,
        "metadata": metadata,
        "admission_class": classify_admission(metadata, readme),
        "structure": {
            "total_files_scanned": total_files,
            "source_files": source_files,
            "source_lines": source_lines,
            "test_files": test_files,
            "workflow_files": workflow_files,
            "languages": dict(languages.most_common()),
        },
        "readme": {
            "path": str(readme_path.relative_to(root)) if readme_path else None,
            "sha256": sha256_text(readme) if readme else None,
            "line_count": len(readme.splitlines()),
            "audience_layers": audience,
            "audience_layer_count": audience_score,
            "local_only_links": sorted(set(local_links)),
            "claim_flags": claims,
        },
        "verification": {"python": python_result},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
