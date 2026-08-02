#!/usr/bin/env python3
"""Compile one source-linked repository observation into a health assessment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from job_app_helix.live_evidence_adapter import (
    LiveEvidenceAdapterError,
    compile_repository_observation,
)
from job_app_helix.repository_health import RepositoryHealthError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("observation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-state")
    args = parser.parse_args()

    try:
        observation = json.loads(args.observation.read_text(encoding="utf-8"))
        result = compile_repository_observation(observation)
    except (OSError, json.JSONDecodeError, LiveEvidenceAdapterError, RepositoryHealthError) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")

    if args.require_state and result["assessment"]["health_state"] != args.require_state:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
