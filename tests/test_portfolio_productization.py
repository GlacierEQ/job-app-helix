from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.portfolio_contract import load_rollout
from job_app_helix.portfolio_models import EvidenceLevel, ExecutionMode, PortfolioProgramError
from job_app_helix.portfolio_productization import (
    DeliveryForm,
    compile_productization_targets,
    productization_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_readme(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "README.md").write_text(
        "\n".join(
            (
                "# Product",
                "## For recruiters and non-technical reviewers",
                "Useful outcome.",
                "## For senior engineers and domain experts",
                "Architecture.",
                "## For AI systems and toolchains",
                "Machine contract.",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _write_contracts(
    root: Path,
    repository: str,
    *,
    mode: str = "CONSOLIDATE_OR_ARCHIVE",
    target: str = "DOCUMENTATION",
) -> tuple[Path, Path]:
    inventory = root / "inventory.json"
    rollout = root / "rollout.json"
    inventory.write_text(
        json.dumps(
            {
                "schema": "test.inventory.v1",
                "owner": "GlacierEQ",
                "portfolio_root": "job-app-helix",
                "total_repositories": 2,
                "workspace_repositories": [repository],
            }
        ),
        encoding="utf-8",
    )
    rollout.write_text(
        json.dumps(
            {
                "schema": "test.rollout.v1",
                "portfolio_root": "GlacierEQ/job-app-helix",
                "policy": {
                    "default_timeout_seconds": 10,
                    "promotion_path": [level.name for level in EvidenceLevel],
                    "fail_closed": True,
                    "require_atomic_receipts": True,
                    "require_positive_test_count_for_test_evidence": True,
                },
                "waves": [
                    {
                        "id": "wave-legacy",
                        "priority": 1,
                        "mode": mode,
                        "objective": "Old archive-first objective.",
                        "current_state": "UNVERIFIED",
                        "current_evidence": "INVENTORY",
                        "target_evidence": target,
                        "acceptance": {
                            "require_readme_contract": True,
                            "require_positive_test_count": False,
                            "require_build_receipt": False,
                        },
                        "repositories": [repository],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return inventory, rollout


def test_current_archive_wave_compiles_to_productize() -> None:
    program = load_rollout(ROOT / "manifests" / "portfolio_rollout.json")
    wave = next(wave for wave in program.waves if wave.id == "wave-4-consolidation")

    assert wave.mode is ExecutionMode.PRODUCTIZE
    assert wave.historical_mode == "CONSOLIDATE_OR_ARCHIVE"
    assert wave.target_evidence >= EvidenceLevel.TEST
    assert wave.require_positive_test_count is True
    assert "real deployment" in wave.objective
    assert "explicit operator authorization" in wave.objective


def test_legacy_archive_mode_cannot_drive_active_execution(tmp_path: Path) -> None:
    _, rollout = _write_contracts(tmp_path, "alpha")
    program = load_rollout(rollout)
    wave = program.waves[0]

    assert wave.mode is ExecutionMode.PRODUCTIZE
    assert wave.historical_mode == ExecutionMode.CONSOLIDATE_OR_ARCHIVE.value
    assert wave.target_evidence is EvidenceLevel.TEST
    assert wave.require_positive_test_count is True


def test_active_deploy_mode_requires_deployment_evidence(tmp_path: Path) -> None:
    _, rollout = _write_contracts(
        tmp_path,
        "alpha",
        mode="DEPLOY",
        target="TEST",
    )

    with pytest.raises(PortfolioProgramError, match="requires target evidence >= DEPLOYMENT"):
        load_rollout(rollout)


def test_productization_compiler_detects_cli_package_and_forbids_archive(tmp_path: Path) -> None:
    inventory, rollout = _write_contracts(tmp_path, "alpha")
    workspace = tmp_path / "repos"
    repo = workspace / "alpha"
    _write_readme(repo)
    (repo / "pyproject.toml").write_text(
        "\n".join(
            (
                "[project]",
                'name = "alpha"',
                "[project.scripts]",
                'alpha = "alpha.cli:main"',
                "[project.optional-dependencies]",
                'dev = ["pytest"]',
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_alpha.py").write_text(
        "def test_alpha():\n    assert True\n",
        encoding="utf-8",
    )

    targets = compile_productization_targets(
        workspace=workspace,
        inventory_path=inventory,
        rollout_path=rollout,
    )
    payload = productization_payload(targets)

    assert targets[0].delivery_form is DeliveryForm.CLI_PACKAGE
    assert targets[0].target_evidence >= EvidenceLevel.TEST
    assert targets[0].blockers == ()
    assert "clean environment" in targets[0].next_checkpoint
    assert payload["targets"][0]["archive_allowed"] is False
    assert payload["retirement_policy"] == "OPERATOR_AUTHORIZATION_REQUIRED"


def test_productization_compiler_prefers_real_static_deployment(tmp_path: Path) -> None:
    inventory, rollout = _write_contracts(tmp_path, "portal")
    workspace = tmp_path / "repos"
    repo = workspace / "portal"
    _write_readme(repo)
    (repo / "package.json").write_text(
        json.dumps(
            {
                "name": "portal",
                "scripts": {
                    "build": "node build.mjs",
                    "test": "node --test",
                    "deploy": "vercel --prod",
                },
            }
        ),
        encoding="utf-8",
    )
    (repo / "vercel.json").write_text("{}\n", encoding="utf-8")

    targets = compile_productization_targets(
        workspace=workspace,
        inventory_path=inventory,
        rollout_path=rollout,
    )

    target = targets[0]
    assert target.delivery_form is DeliveryForm.STATIC_SITE
    assert "vercel" in target.deployment_signals
    assert "npm:deploy" in target.deployment_signals
    assert "deploy" in target.next_checkpoint
    assert "live site receipt" in target.next_checkpoint
