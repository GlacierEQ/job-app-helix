#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from job_app_helix.company_intelligence import parse_company_intelligence
from job_app_helix.estate_intelligence import (
    project_estate_intelligence,
    public_intelligence_projection,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def atomic_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Project the reference estate compiler bundle through role-fit, "
            "company intelligence, and support/reference boundaries."
        )
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "artifacts/estate-compiler/estate-compiler-bundle.json",
    )
    parser.add_argument(
        "--census",
        type=Path,
        default=ROOT / "artifacts/owned-library-census.json",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "manifests/estate_projection_policy.json",
    )
    parser.add_argument(
        "--company-intelligence",
        type=Path,
        default=(
            ROOT
            / "manifests/application_intelligence/company_bottleneck_atlas.external.json"
        ),
    )
    parser.add_argument(
        "--estate-facts",
        type=Path,
        default=ROOT / "manifests/estate_facts.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/estate-compiler/estate-intelligence-bundle.json",
    )
    parser.add_argument(
        "--public-output",
        type=Path,
        default=ROOT / "artifacts/estate-compiler/public-safe-company-projection-v2.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = load_json(args.bundle)
    census = load_json(args.census)
    policy = load_json(args.policy)
    facts = load_json(args.estate_facts)
    intelligence_manifest = load_json(args.company_intelligence)

    refs = intelligence_manifest.get("shards", [])
    if not isinstance(refs, list):
        raise ValueError("company intelligence shards must be a list")
    shards: dict[str, dict[str, Any]] = {}
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
            raise ValueError("company intelligence shard reference is invalid")
        path = ref["path"]
        shards[path] = load_json(ROOT / path)
    intelligence = parse_company_intelligence(intelligence_manifest, shards)

    projected = project_estate_intelligence(
        bundle,
        policy=policy,
        company_intelligence=intelligence,
        estate_facts=facts,
        census=census,
    )
    public = public_intelligence_projection(projected)

    atomic_write(args.output, projected)
    atomic_write(args.public_output, public)
    receipt_path = args.output.parent / "estate-intelligence-receipt.json"
    atomic_write(receipt_path, projected["receipt"])
    print(json.dumps(projected["receipt"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
