from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from job_app_helix.estate_visibility import (
    compile_estate_visibility,
    estate_visibility_payload,
)
from job_app_helix.portfolio_models import PortfolioProgramError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENSUS = ROOT / "state" / "owned-library-census.json"
DEFAULT_PROJECTION = ROOT / "manifests" / "portfolio_repositories.json"
DEFAULT_OUTPUT = ROOT / "state" / "estate-visibility-queue.json"


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile the authenticated full owner census into a zero-hidden internal "
            "relevance queue before job rollout admission"
        )
    )
    parser.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        candidates = compile_estate_visibility(
            census_path=args.census.resolve(),
            rollout_projection_path=args.projection.resolve(),
        )
        payload = estate_visibility_payload(candidates)
        _atomic_write(args.output.resolve(), payload)
    except PortfolioProgramError as exc:
        print(f"Estate visibility compile failed: {exc}")
        return 1
    print(
        "Estate visibility VERIFIED: "
        f"repositories={payload['repository_count']} hidden={payload['hidden_repository_count']} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
