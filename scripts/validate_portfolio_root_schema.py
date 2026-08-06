#!/usr/bin/env python3
"""Validate the portfolio root manifest against its Draft 2020-12 schema."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "portfolio_root_truth.json"
SCHEMA = ROOT / "schemas" / "portfolio_root_truth.schema.json"


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load(MANIFEST)
    schema = load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.absolute_path))
    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            print(f"{location}: {error.message}")
        return 1
    print("portfolio root truth schema: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
