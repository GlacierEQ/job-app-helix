from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import build_final_form_package as base

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = ROOT / "artifacts"
EXTRA_COPY_MAP = {
    "PORTFOLIO_EXPANSION_MAP.md": (
        "04_TECHNICAL_DILIGENCE/PORTFOLIO_EXPANSION_MAP.md"
    ),
    "owned_library_census.json": (
        "05_MACHINE_CONTRACTS/owned_library_census.json"
    ),
}


@contextmanager
def complete_package_contract() -> Iterator[None]:
    original_copy_map = dict(base.COPY_MAP)
    original_required_paths = set(base.BASE_REQUIRED_PACKAGE_PATHS)
    try:
        base.COPY_MAP.update(EXTRA_COPY_MAP)
        base.BASE_REQUIRED_PACKAGE_PATHS.update(EXTRA_COPY_MAP)
        base.BASE_REQUIRED_PACKAGE_PATHS.update(EXTRA_COPY_MAP.values())
        yield
    finally:
        base.COPY_MAP.clear()
        base.COPY_MAP.update(original_copy_map)
        base.BASE_REQUIRED_PACKAGE_PATHS.clear()
        base.BASE_REQUIRED_PACKAGE_PATHS.update(original_required_paths)


def build_complete_package(
    output: Path,
    *,
    source_commit: str,
    site_dir: Path | None = None,
    contact_file: Path | None = None,
) -> base.BuildResult:
    with complete_package_contract():
        return base.build_package(
            output,
            source_commit=source_commit,
            site_dir=site_dir,
            contact_file=contact_file,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the complete Casey Barton recruiter delivery package"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ARTIFACTS_ROOT / "complete-delivery-package",
    )
    parser.add_argument(
        "--source-commit",
        default=os.environ.get("GITHUB_SHA", "local-uncommitted"),
    )
    parser.add_argument("--site-dir", type=Path)
    parser.add_argument("--contact-file", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_complete_package(
            args.output,
            source_commit=str(args.source_commit),
            site_dir=args.site_dir,
            contact_file=args.contact_file,
        )
    except base.PackageError as exc:
        print(f"Complete delivery package failed closed: {exc}")
        return 1
    print(
        "Complete delivery package VERIFIED: "
        f"files={result.file_count} bytes={result.total_bytes} "
        f"zip_sha256={result.zip_sha256} path={result.zip_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
