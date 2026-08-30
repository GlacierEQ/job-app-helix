from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from job_app_helix.repo_excellence import (
    ExcellenceContractError,
    validate_repo_excellence_record,
)

QUARANTINE_MESSAGE = (
    "HyperExcellenceEngine automatic promotion is quarantined. "
    "This entrypoint may validate an existing excellence record, but it must not "
    "create gates, fabricate tests, mint authority, synthesize proof receipts, "
    "or persist a promoted state. Use the reference proof-producing workflow."
)


class HyperExcellenceEngine:
    """Read-only quarantine wrapper for the retired synthetic promotion engine."""

    def __init__(self, target_repo: str | Path):
        self.repo_path = Path(target_repo)
        self.state_file = self.repo_path / "machine" / "excellence-state.json"
        if not self.state_file.is_file():
            raise ExcellenceContractError(
                "missing machine/excellence-state.json; synthetic bootstrap is disabled"
            )

        try:
            raw = self.state_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ExcellenceContractError("unreadable machine/excellence-state.json") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExcellenceContractError("invalid excellence-state.json") from exc
        if not isinstance(payload, dict):
            raise ExcellenceContractError("excellence-state.json must contain an object")
        self.state: dict[str, Any] = payload

    def verify_existing_state(self) -> dict[str, Any]:
        """Validate the existing record without mutating repository state."""
        return validate_repo_excellence_record(self.state)

    def enforce_all_gates(self) -> None:
        """Fail closed: automatic gate mutation and promotion are disabled."""
        self.verify_existing_state()
        raise ExcellenceContractError(QUARANTINE_MESSAGE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an excellence record; automatic promotion is quarantined."
    )
    parser.add_argument("repo", help="Path to the repository to inspect.")
    args = parser.parse_args()

    try:
        engine = HyperExcellenceEngine(args.repo)
        engine.enforce_all_gates()
    except ExcellenceContractError as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
