from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

from .portfolio_models import (
    EvidenceLevel,
    ExecutionMode,
    PortfolioProgramError,
    RolloutProgram,
    VerificationState,
    Wave,
)

REPOSITORY_RE: Final = re.compile(r"^[A-Za-z0-9_.-]+$")


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PortfolioProgramError(f"{label} must be an object")
    return value


def _require_string(mapping: dict[str, Any], key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PortfolioProgramError(f"{label}.{key} must be a non-empty string")
    return value.strip()


def _require_bool(mapping: dict[str, Any], key: str, label: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise PortfolioProgramError(f"{label}.{key} must be a boolean")
    return value


def load_inventory(path: Path) -> tuple[str, str, tuple[str, ...]]:
    payload = _require_mapping(json.loads(path.read_text(encoding="utf-8")), "inventory")
    owner = _require_string(payload, "owner", "inventory")
    root = _require_string(payload, "portfolio_root", "inventory")
    raw_repositories = payload.get("workspace_repositories")
    if not isinstance(raw_repositories, list) or not raw_repositories:
        raise PortfolioProgramError("inventory.workspace_repositories must be a non-empty list")

    repositories: list[str] = []
    for index, value in enumerate(raw_repositories):
        if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
            raise PortfolioProgramError(
                f"inventory.workspace_repositories[{index}] is not a safe repository name"
            )
        repositories.append(value)

    if len(set(repositories)) != len(repositories):
        raise PortfolioProgramError("inventory contains duplicate repository names")

    declared_total = payload.get("total_repositories")
    if declared_total != len(repositories) + 1:
        raise PortfolioProgramError(
            "inventory.total_repositories must equal workspace repositories plus the root"
        )
    return owner, root, tuple(repositories)


def load_rollout(path: Path) -> RolloutProgram:
    payload = _require_mapping(json.loads(path.read_text(encoding="utf-8")), "rollout")
    schema = _require_string(payload, "schema", "rollout")
    portfolio_root = _require_string(payload, "portfolio_root", "rollout")
    policy = _require_mapping(payload.get("policy"), "rollout.policy")
    timeout = policy.get("default_timeout_seconds")
    if not isinstance(timeout, int) or timeout <= 0:
        raise PortfolioProgramError(
            "rollout.policy.default_timeout_seconds must be a positive integer"
        )

    raw_promotion_path = policy.get("promotion_path")
    expected_path = tuple(level.name for level in EvidenceLevel)
    if not isinstance(raw_promotion_path, list) or tuple(raw_promotion_path) != expected_path:
        raise PortfolioProgramError(
            "rollout.policy.promotion_path must declare the complete evidence ladder "
            f"in order: {list(expected_path)}"
        )
    fail_closed = _require_bool(policy, "fail_closed", "rollout.policy")
    require_atomic_receipts = _require_bool(
        policy, "require_atomic_receipts", "rollout.policy"
    )
    require_positive_test_count = _require_bool(
        policy,
        "require_positive_test_count_for_test_evidence",
        "rollout.policy",
    )
    if not fail_closed or not require_atomic_receipts or not require_positive_test_count:
        raise PortfolioProgramError(
            "rollout policy must remain fail-closed, atomic, and positive-count enforced"
        )

    raw_waves = payload.get("waves")
    if not isinstance(raw_waves, list) or not raw_waves:
        raise PortfolioProgramError("rollout.waves must be a non-empty list")

    waves: list[Wave] = []
    wave_ids: set[str] = set()
    for index, raw_wave in enumerate(raw_waves):
        label = f"rollout.waves[{index}]"
        wave_payload = _require_mapping(raw_wave, label)
        wave_id = _require_string(wave_payload, "id", label)
        if wave_id in wave_ids:
            raise PortfolioProgramError(f"duplicate wave id: {wave_id}")
        wave_ids.add(wave_id)

        priority = wave_payload.get("priority")
        if not isinstance(priority, int) or priority <= 0:
            raise PortfolioProgramError(f"{label}.priority must be a positive integer")

        try:
            mode = ExecutionMode(_require_string(wave_payload, "mode", label))
            current_state = VerificationState(
                _require_string(wave_payload, "current_state", label)
            )
        except ValueError as exc:
            raise PortfolioProgramError(f"{label} contains an invalid enum value") from exc

        current_evidence = EvidenceLevel.parse(
            _require_string(wave_payload, "current_evidence", label)
        )
        target_evidence = EvidenceLevel.parse(
            _require_string(wave_payload, "target_evidence", label)
        )
        if mode is ExecutionMode.VERIFY and target_evidence < current_evidence:
            raise PortfolioProgramError(
                f"{label}.target_evidence cannot be lower than current_evidence"
            )

        acceptance = _require_mapping(wave_payload.get("acceptance"), f"{label}.acceptance")
        raw_repositories = wave_payload.get("repositories")
        if not isinstance(raw_repositories, list) or not raw_repositories:
            raise PortfolioProgramError(f"{label}.repositories must be a non-empty list")

        repositories: list[str] = []
        for repo_index, repository in enumerate(raw_repositories):
            if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
                raise PortfolioProgramError(
                    f"{label}.repositories[{repo_index}] is not a safe repository name"
                )
            repositories.append(repository)
        if len(set(repositories)) != len(repositories):
            raise PortfolioProgramError(f"{label}.repositories contains duplicates")

        waves.append(
            Wave(
                id=wave_id,
                priority=priority,
                mode=mode,
                objective=_require_string(wave_payload, "objective", label),
                current_state=current_state,
                current_evidence=current_evidence,
                target_evidence=target_evidence,
                repositories=tuple(repositories),
                require_readme_contract=_require_bool(
                    acceptance, "require_readme_contract", f"{label}.acceptance"
                ),
                require_positive_test_count=_require_bool(
                    acceptance, "require_positive_test_count", f"{label}.acceptance"
                ),
                require_build_receipt=_require_bool(
                    acceptance, "require_build_receipt", f"{label}.acceptance"
                ),
            )
        )

    return RolloutProgram(
        schema=schema,
        portfolio_root=portfolio_root,
        default_timeout_seconds=timeout,
        promotion_path=tuple(EvidenceLevel[name] for name in raw_promotion_path),
        fail_closed=fail_closed,
        require_atomic_receipts=require_atomic_receipts,
        require_positive_test_count_for_test_evidence=require_positive_test_count,
        waves=tuple(sorted(waves, key=lambda wave: (wave.priority, wave.id))),
    )


def validate_program(
    *,
    inventory_path: Path,
    rollout_path: Path,
) -> RolloutProgram:
    owner, root, inventory = load_inventory(inventory_path)
    program = load_rollout(rollout_path)
    expected_root = f"{owner}/{root}"
    if program.portfolio_root != expected_root:
        raise PortfolioProgramError(
            f"rollout portfolio_root must be {expected_root!r}, got {program.portfolio_root!r}"
        )

    declared = program.repositories
    duplicates = sorted(
        repository for repository in set(declared) if declared.count(repository) > 1
    )
    missing = sorted(set(inventory) - set(declared))
    unexpected = sorted(set(declared) - set(inventory))
    if duplicates or missing or unexpected:
        raise PortfolioProgramError(
            "rollout must partition the exact inventory; "
            f"duplicates={duplicates}, missing={missing}, unexpected={unexpected}"
        )
    return program
