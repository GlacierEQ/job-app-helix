#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from job_app_helix.estate_compiler import compile_estate, public_safe_projection

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def atomic_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        temp = Path(stream.name)
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the authenticated GlacierEQ estate into systems, capabilities, "
            "and company projections."
        )
    )
    parser.add_argument(
        "--census",
        type=Path,
        default=ROOT / "artifacts" / "owned-library-census.json",
    )
    parser.add_argument(
        "--flagships",
        type=Path,
        default=ROOT / "manifests" / "flagship_registry.json",
    )
    parser.add_argument(
        "--companies",
        type=Path,
        default=ROOT / "manifests" / "company_dossiers.json",
    )
    parser.add_argument(
        "--semantic-capabilities",
        type=Path,
        default=(
            ROOT
            / "manifests"
            / "application_intelligence"
            / "supabase_motherduck_capability_donors.json"
        ),
    )
    facts = parser.add_mutually_exclusive_group()
    facts.add_argument("--estate-facts", type=Path)
    facts.add_argument("--lineage", dest="estate_facts", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts" / "estate-compiler",
    )
    parser.add_argument("--public-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    census = load_json(args.census)
    flagships = load_json(args.flagships)
    index = load_json(args.companies)
    shard_paths = index.get("dossier_files", [])
    if not isinstance(shard_paths, list):
        raise ValueError("company_dossiers.dossier_files must be a list")
    shards = [load_json(ROOT / path) for path in shard_paths]
    estate_facts = load_json(args.estate_facts) if args.estate_facts else None
    semantic_capabilities = (
        load_json(args.semantic_capabilities)
        if args.semantic_capabilities and args.semantic_capabilities.exists()
        else None
    )

    bundle = compile_estate(
        census,
        flagships=flagships,
        company_index=index,
        company_shards=shards,
        lineage=estate_facts,
        semantic_capabilities=semantic_capabilities,
    )
    out = args.output_dir
    atomic_write(out / "canonical-system-registry.json", bundle["canonical_system_registry"])
    atomic_write(out / "capability-donor-registry.json", bundle["capability_donor_registry"])
    atomic_write(out / "company-projection-registry.json", bundle["company_projection_registry"])
    atomic_write(out / "experiment-pipeline.json", bundle["experiment_pipeline"])
    atomic_write(out / "estate-compiler-receipt.json", bundle["receipt"])
    atomic_write(out / "estate-compiler-bundle.json", bundle)
    if args.public_output:
        atomic_write(args.public_output, public_safe_projection(bundle))
    print(json.dumps(bundle["receipt"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
