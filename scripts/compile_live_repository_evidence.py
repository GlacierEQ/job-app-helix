#!/usr/bin/env python3
"""Compile one source-linked repository observation into a health assessment."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from job_app_helix.live_evidence_adapter import (
    LiveEvidenceAdapterError,
    compile_repository_observation,
)
from job_app_helix.repository_health import RepositoryHealthError


def atomic_write_text(path: Path, content: str) -> None:
    """Write a complete UTF-8 file and atomically replace the destination."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("observation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-state")
    args = parser.parse_args()

    try:
        observation = json.loads(args.observation.read_text(encoding="utf-8"))
        result = compile_repository_observation(observation)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            atomic_write_text(args.output, rendered)
    except (
        OSError,
        json.JSONDecodeError,
        LiveEvidenceAdapterError,
        RepositoryHealthError,
    ) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        return 2

    print(rendered, end="")
    if args.require_state and result["assessment"]["health_state"] != args.require_state:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
