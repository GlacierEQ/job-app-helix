#!/usr/bin/env python3
"""Validate base + modular company second-depth overrides as one effective authority."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_VALIDATOR = ROOT / "scripts" / "validate_company_second_depth.py"
OVERRIDE_INDEX = ROOT / "manifests" / "company_second_depth_overrides" / "index.json"


def load_base_validator():
    spec = importlib.util.spec_from_file_location("company_second_depth_base", BASE_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load base company second-depth validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def effective_second_depth(root: Path = ROOT) -> dict[str, Any]:
    base = load_base_validator()
    base_result = base.validate_second_depth(root)

    company_index = load_json(root / "manifests" / "company_dossiers.json")
    registry_path = company_index["second_depth_registry"]
    registry = load_json(root / registry_path)
    defaults = registry["default_company_state"]
    inline_overrides = registry["company_overrides"]
    required_tracks = set(company_index["required_company_tracks"])
    stage_index = {stage: ordinal for ordinal, stage in enumerate(base.EXPECTED_STAGES)}

    modular: dict[str, dict[str, Any]] = {}
    if OVERRIDE_INDEX.exists():
        index = load_json(OVERRIDE_INDEX)
        if index.get("schema") != "glaciereq.company-second-depth-overrides.v1":
            raise ValueError("unexpected modular override index schema")
        if index.get("authority") != "GlacierEQ/job-app-helix":
            raise ValueError("unexpected modular override authority")
        rows = index.get("overrides")
        if not isinstance(rows, list):
            raise ValueError("modular override index overrides must be an array")

        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("modular override index row must be an object")
            company_id = row.get("company_id")
            relative_path = row.get("path")
            if not isinstance(company_id, str) or not company_id:
                raise ValueError("modular override company_id must be non-empty text")
            if company_id in seen:
                raise ValueError(f"duplicate modular override: {company_id}")
            seen.add(company_id)
            if company_id not in required_tracks:
                raise ValueError(f"modular override references unknown company: {company_id}")
            if company_id in inline_overrides:
                raise ValueError(
                    f"company {company_id} cannot have both inline and modular overrides"
                )
            if not isinstance(relative_path, str) or not relative_path.startswith(
                "manifests/company_second_depth_overrides/"
            ):
                raise ValueError(f"invalid modular override path for {company_id}")

            payload = load_json(root / relative_path)
            if payload.get("schema") != "glaciereq.company-second-depth-company.v1":
                raise ValueError(f"unexpected modular company schema for {company_id}")
            if payload.get("company_id") != company_id:
                raise ValueError(f"modular company identity mismatch for {company_id}")
            override = payload.get("state")
            if not isinstance(override, dict):
                raise ValueError(f"modular company state must be an object for {company_id}")
            state = base.resolved_state(defaults, override)
            base.validate_state(company_id, state, stage_index)
            modular[company_id] = state

    counts = {stage: 0 for stage in base.EXPECTED_STAGES}
    for company_id in sorted(required_tracks):
        if company_id in modular:
            state = modular[company_id]
        else:
            state = base.resolved_state(defaults, inline_overrides.get(company_id, {}))
        counts[state["stage"]] += 1

    return {
        **base_result,
        "status": "PASS",
        "modular_overrides": len(modular),
        "effective_company_overrides": len(inline_overrides) + len(modular),
        "effective_stage_counts": counts,
        "modular_company_ids": sorted(modular),
        "effective_merge_rule": "base registry -> inline override OR modular override",
    }


def main() -> int:
    try:
        result = effective_second_depth(ROOT)
    except Exception as exc:  # fail closed at the CLI boundary
        print(f"COMPANY SECOND-DEPTH EFFECTIVE FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
