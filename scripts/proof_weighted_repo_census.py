"""Conservative structural and executable census for one portfolio repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {
    ".coverage",
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}

LANGUAGE_BY_SUFFIX = {
    ".agda": "Agda",
    ".c": "C",
    ".capnp": "Cap'n Proto",
    ".cc": "C++",
    ".cpp": "C++",
    ".cu": "CUDA",
    ".cxx": "C++",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".fbs": "FlatBuffers",
    ".go": "Go",
    ".h": "C/C++",
    ".hpp": "C++",
    ".hs": "Haskell",
    ".java": "Java",
    ".jl": "Julia",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".lean": "Lean 4",
    ".mlir": "MLIR",
    ".mojo": "Mojo",
    ".odin": "Odin",
    ".onnx": "ONNX",
    ".php": "PHP",
    ".proto": "Protobuf",
    ".ps1": "PowerShell",
    ".py": "Python",
    ".r": "R",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".scala": "Scala/Chisel",
    ".sh": "Shell",
    ".sql": "SQL",
    ".sv": "SystemVerilog",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".v": "Verilog/Coq",
    ".vhd": "VHDL",
    ".vhdl": "VHDL",
    ".wasm": "WebAssembly",
    ".wat": "WebAssembly",
    ".zig": "Zig",
}

SOURCE_SUFFIXES = set(LANGUAGE_BY_SUFFIX)
TEST_NAME = re.compile(
    r"(^test[_-]|[_-]test\.|[_-]tests?\.|\.spec\.|\.test\.)",
    re.IGNORECASE,
)
PYTEST_COUNT = re.compile(r"(?P<count>\d+) passed(?:,|\s)")

AUDIENCE_TERMS = {
    "recruiter": (
        "business value",
        "executive summary",
        "for hiring managers",
        "for non-technical",
        "for recruiters",
        "why it matters",
    ),
    "expert": (
        "architecture",
        "failure modes",
        "for engineers",
        "for senior engineers",
        "limitations",
        "testing",
        "tradeoffs",
        "verification",
    ),
    "ai_mesh": (
        "ai ingestion",
        "reference graph",
        "for ai systems",
        "machine-readable",
        "mcp tool",
        "programmatic mesh",
        "protobuf",
        "repository mesh",
    ),
}

CLAIM_PATTERNS = {
    "universal_success": re.compile(
        r"\b(?:100%|zero failures?|all tests pass|fully operational)\b",
        re.IGNORECASE,
    ),
    "production_claim": re.compile(
        r"\b(?:production[- ]grade|production[- ]ready|enterprise[- ]ready|"
        r"flight[- ]ready|battle[- ]tested)\b",
        re.IGNORECASE,
    ),
    "latency_or_throughput": re.compile(
        r"\b(?:sub[- ]?\d+\s*(?:ms|millisecond)|"
        r"\d[\d,]*(?:\+)?\s*(?:packets?|requests?|tokens?|events?)"
        r"\s*/?\s*(?:s|sec|second)|"
        r"\d+(?:\.\d+)?%\s*(?:availability|uptime|accuracy))\b",
        re.IGNORECASE,
    ),
    "deployment_claim": re.compile(
        r"\b(?:deployed|in production|operational deployment|"
        r"powers?\s+\d|manages?\s+\d[\d,]*)\b",
        re.IGNORECASE,
    ),
    "employment_claim": re.compile(
        r"\b(?:at|for)\s+(?:OpenAI|Anthropic|xAI|SpaceX|NVIDIA|"
        r"Google|Microsoft|Apple)\b",
        re.IGNORECASE,
    ),
}

EXPLICIT_DOWNSTREAM_MARKERS = (
    "GLACIEREQ_DOWNSTREAM.md",
    "UPSTREAM.md",
)
UPSTREAM_LINEAGE_MARKERS = (
    "SOURCE_REV",
    "THIRD-PARTY-NOTICES",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def read_metadata(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def iter_files(root: Path) -> Iterator[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = [
            name
            for name in dirs
            if name not in EXCLUDED_DIRS and not name.startswith(".tox")
        ]
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
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return len(text.splitlines())


def read_readme(root: Path) -> tuple[Path | None, str]:
    for name in ("README.md", "Readme.md", "readme.md", "README.rst", "README.txt"):
        path = root / name
        if path.is_file():
            return path, path.read_text(encoding="utf-8", errors="ignore")
    return None, ""


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def extract_pytest_count(output: str) -> int:
    match = PYTEST_COUNT.search(output)
    return int(match.group("count")) if match else 0


def run_pytest(root: Path, timeout: int) -> dict[str, Any]:
    tests = [
        path
        for path in iter_files(root)
        if path.suffix == ".py" and TEST_NAME.search(path.name)
    ]
    if not tests:
        return {
            "status": "NO_TEST_PATH",
            "command": None,
            "exit_code": None,
            "observed_count": 0,
            "summary": "No Python test files detected.",
        }

    command = [sys.executable, "-m", "pytest", "-q"]
    try:
        process = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return {
            "status": "BLOCKED_TIMEOUT",
            "command": command,
            "exit_code": 124,
            "observed_count": 0,
            "summary": output[-8_000:],
        }

    output = (process.stdout or "")[-12_000:]
    observed_count = extract_pytest_count(output)
    dependency_error = re.search(
        r"(?:ModuleNotFoundError|ImportError:|No module named|"
        r"command not found|could not find)",
        output,
        re.IGNORECASE,
    )

    if process.returncode == 0 and observed_count > 0:
        status = "VERIFIED"
    elif process.returncode == 0:
        status = "UNVERIFIED_ZERO_PROOF"
    elif dependency_error:
        status = "BLOCKED_DEPENDENCY"
    elif process.returncode == 5 and "no tests ran" in output.casefold():
        status = "NO_TEST_PATH"
    else:
        status = "FAILED"

    return {
        "status": status,
        "command": command,
        "exit_code": process.returncode,
        "observed_count": observed_count,
        "summary": output,
    }


def detect_provenance(root: Path, metadata: dict[str, Any]) -> dict[str, object]:
    if metadata.get("fork"):
        return {
            "state": "GITHUB_FORK",
            "markers": ["metadata.fork=true"],
        }

    markers: list[str] = []
    for name in (*EXPLICIT_DOWNSTREAM_MARKERS, *UPSTREAM_LINEAGE_MARKERS):
        if (root / name).is_file():
            markers.append(name)

    if any(name in markers for name in EXPLICIT_DOWNSTREAM_MARKERS):
        state = "EXPLICIT_DOWNSTREAM"
    elif all(name in markers for name in UPSTREAM_LINEAGE_MARKERS):
        state = "EXPLICIT_UPSTREAM_LINEAGE"
    else:
        state = "UNRESOLVED"

    return {
        "state": state,
        "markers": markers,
    }


def classify_admission(
    metadata: dict[str, Any],
    readme: str,
    provenance_state: str,
) -> str:
    if metadata.get("private") or metadata.get("visibility") == "private":
        return "private_excluded"
    if metadata.get("archived"):
        return "archive_or_retired"
    if metadata.get("fork") or provenance_state == "GITHUB_FORK":
        return "supporting_reference_fork"
    if not readme.strip():
        return "candidate_missing_readme"
    if provenance_state in {"EXPLICIT_DOWNSTREAM", "EXPLICIT_UPSTREAM_LINEAGE"}:
        return "candidate_attributed_downstream"
    return "candidate_public_unresolved_provenance"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build_result(
    *,
    repo: str,
    root: Path,
    metadata: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    readme_path, readme = read_readme(root)
    provenance = detect_provenance(root, metadata)
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
            languages[LANGUAGE_BY_SUFFIX[suffix]] += 1
            source_files += 1
            source_lines += count_text_lines(path)
        parts = {part.casefold() for part in relative.parts}
        if TEST_NAME.search(path.name) or "tests" in parts:
            test_files += 1
        if (
            relative.parts[:2] == (".github", "workflows")
            and suffix in {".yml", ".yaml"}
        ):
            workflow_files += 1

    local_links = re.findall(
        r"(?:file://|/Users/|[A-Za-z]:\\\\Users\\\\)[^\s)\]>'\"]+",
        readme,
    )
    audience = {
        name: has_any(readme, terms) for name, terms in AUDIENCE_TERMS.items()
    }
    claim_flags = {
        name: len(pattern.findall(readme))
        for name, pattern in CLAIM_PATTERNS.items()
    }

    return {
        "schema": "glaciereq.portfolio.audit.v2",
        "repository": repo,
        "metadata": metadata,
        "provenance": provenance,
        "admission_class": classify_admission(
            metadata,
            readme,
            str(provenance["state"]),
        ),
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
            "audience_layer_count": sum(audience.values()),
            "local_only_links": sorted(set(local_links)),
            "claim_flags": claim_flags,
        },
        "verification": {"python": run_pytest(root, timeout)},
        "nonclaims": [
            "Public and non-fork metadata does not establish authorship or originality.",
            "Unresolved provenance blocks an original-work admission class.",
            "Structural presence does not establish deployment, production use, or impact.",
        ],
    }


def main() -> int:
    args = parse_args()
    root = args.path.resolve()
    result = build_result(
        repo=args.repo,
        root=root,
        metadata=read_metadata(args.metadata),
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
