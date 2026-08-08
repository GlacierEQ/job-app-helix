from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from discover_experience_graph import digest, load_company_catalog, write_atomic
from estate_compiler.capabilities import build_capability_registry
from estate_compiler.canonical import build_canonical_registry
from estate_compiler.common import (
    EstateCompilerError,
    latest_assessments,
    load_json,
    native_records,
)
from estate_compiler.intelligence import load_external_company_intelligence
from estate_compiler.projections import build_company_registry, build_public_projection

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "estate-intelligence"
DEFAULT_INTELLIGENCE = (
    ROOT / "manifests/application_intelligence/company_bottleneck_atlas.external.json"
)


def compile_all(
    census: dict[str, Any],
    company_index: dict[str, Any],
    second_depth: dict[str, Any],
    flagships: dict[str, Any],
    lineage: dict[str, Any],
    policy: dict[str, Any],
    assessment_by_repo: dict[str, dict[str, Any]],
    company_intelligence: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    native = native_records(census)
    companies, repo_meta = load_company_catalog(ROOT, company_index)
    canonical, repo_to_system = build_canonical_registry(
        native,
        flagships,
        lineage,
        policy,
        repo_meta,
    )
    capability, by_system = build_capability_registry(
        canonical, flagships, assessment_by_repo, policy
    )
    company = build_company_registry(
        companies,
        repo_meta,
        second_depth,
        canonical,
        repo_to_system,
        by_system,
        assessment_by_repo,
        policy,
        company_intelligence,
    )
    public = build_public_projection(canonical, capability, company)
    result = {
        "canonical_system_registry": canonical,
        "capability_donor_registry": capability,
        "company_projection_registry": company,
        "public_projection": public,
    }
    manifest = {
        "schema": "glaciereq.estate-intelligence-build.v2",
        "artifacts": {name: digest(value) for name, value in result.items()},
        "sources": {
            "census": digest(census),
            "company_index": digest(company_index),
            "second_depth": digest(second_depth),
            "flagships": digest(flagships),
            "lineage": digest(lineage),
            "policy": digest(policy),
            "assessments": digest(assessment_by_repo),
            "company_intelligence": digest(company_intelligence or {}),
        },
        "privacy_boundary": {
            "full_census_runner_local": True,
            "internal_registries_not_public_artifacts": True,
            "public_projection_contains_no_private_repository_identities": True,
        },
    }
    manifest["build_id"] = digest(manifest)
    result["build_manifest"] = manifest
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile estate intelligence into proof-bound audience projections"
    )
    parser.add_argument(
        "--census", type=Path, default=ROOT / "artifacts/owned-library-census.json"
    )
    parser.add_argument(
        "--companies", type=Path, default=ROOT / "manifests/company_dossiers.json"
    )
    parser.add_argument(
        "--second-depth",
        type=Path,
        default=ROOT / "manifests/company_second_depth.json",
    )
    parser.add_argument(
        "--flagships", type=Path, default=ROOT / "manifests/flagship_registry.json"
    )
    parser.add_argument(
        "--lineage",
        type=Path,
        default=ROOT / "manifests/estate_lineage_assertions.json",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "policies/estate_intelligence_compiler.json",
    )
    parser.add_argument(
        "--company-intelligence",
        type=Path,
        default=DEFAULT_INTELLIGENCE,
    )
    parser.add_argument(
        "--assessments",
        type=Path,
        default=ROOT / "status/repository-assessments",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        intelligence_manifest = load_json(args.company_intelligence.resolve())
        company_intelligence = load_external_company_intelligence(
            ROOT, intelligence_manifest
        )
        result = compile_all(
            load_json(args.census.resolve()),
            load_json(args.companies.resolve()),
            load_json(args.second_depth.resolve()),
            load_json(args.flagships.resolve()),
            load_json(args.lineage.resolve(), optional=True),
            load_json(args.policy.resolve()),
            latest_assessments(args.assessments.resolve()),
            company_intelligence,
        )
        output = args.output.resolve()
        for name, payload in result.items():
            write_atomic(output / f"{name}.json", payload)
    except EstateCompilerError as exc:
        print(f"Estate intelligence compiler failed closed: {exc}")
        return 1
    canonical = result["canonical_system_registry"]
    print(
        "Estate intelligence compiled: "
        f"declared={canonical['current_declared_canonical_system_count']} "
        f"unresolved={canonical['unresolved_native_repository_count']} "
        f"build={result['build_manifest']['build_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
