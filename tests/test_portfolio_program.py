from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from job_app_helix.portfolio_contract import validate_program
from job_app_helix.portfolio_discovery import build_plan, readme_contract
from job_app_helix.portfolio_execution import (
    atomic_write_json,
    execute_plan,
    extract_test_count,
    receipt_payload,
)
from job_app_helix.portfolio_models import (
    CommandSpec,
    EvidenceLevel,
    ExecutionMode,
    PortfolioProgramError,
    ProofMode,
    RepositoryPlan,
    VerificationState,
)


def _write_contracts(
    root: Path,
    *,
    inventory_repositories: list[str],
    rollout_repositories: list[str] | None = None,
) -> tuple[Path, Path]:
    inventory = root / "inventory.json"
    rollout = root / "rollout.json"
    inventory.write_text(
        json.dumps(
            {
                "schema": "test.inventory.v1",
                "owner": "GlacierEQ",
                "portfolio_root": "job-app-helix",
                "total_repositories": len(inventory_repositories) + 1,
                "workspace_repositories": inventory_repositories,
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
                    "promotion_path": [
                        "INVENTORY",
                        "DOCUMENTATION",
                        "STATIC_ANALYSIS",
                        "BUILD",
                        "TEST",
                        "INTEGRATION",
                        "DEPLOYMENT",
                    ],
                    "fail_closed": True,
                    "require_atomic_receipts": True,
                    "require_positive_test_count_for_test_evidence": True,
                },
                "waves": [
                    {
                        "id": "wave-1",
                        "priority": 1,
                        "mode": "VERIFY",
                        "objective": "Verify exact test repositories.",
                        "current_state": "UNVERIFIED",
                        "current_evidence": "INVENTORY",
                        "target_evidence": "TEST",
                        "acceptance": {
                            "require_readme_contract": True,
                            "require_positive_test_count": True,
                            "require_build_receipt": False,
                        },
                        "repositories": (
                            rollout_repositories
                            if rollout_repositories is not None
                            else inventory_repositories
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return inventory, rollout


def _write_readme(repository: Path) -> None:
    repository.mkdir(parents=True, exist_ok=True)
    repository.joinpath("README.md").write_text(
        "\n".join(
            (
                "# Test repository",
                "## For recruiters and non-technical reviewers",
                "Value.",
                "## For senior engineers and domain experts",
                "Architecture.",
                "## For AI systems and toolchains",
                "Contract.",
            )
        ),
        encoding="utf-8",
    )


def _plan(path: Path, command: CommandSpec) -> RepositoryPlan:
    return RepositoryPlan(
        repository=path.name,
        wave_id="wave-1",
        priority=1,
        mode=ExecutionMode.VERIFY,
        current_state=VerificationState.UNVERIFIED,
        current_evidence=EvidenceLevel.INVENTORY,
        target_evidence=EvidenceLevel.TEST,
        path=path,
        stacks=("python",),
        commands=(command,),
        blockers=(),
        readme_contract_satisfied=True,
    )


def test_validate_program_requires_exact_partition(tmp_path: Path) -> None:
    inventory, rollout = _write_contracts(
        tmp_path,
        inventory_repositories=["alpha", "omega"],
    )

    program = validate_program(inventory_path=inventory, rollout_path=rollout)

    assert program.repositories == ("alpha", "omega")


def test_validate_program_rejects_missing_repository(tmp_path: Path) -> None:
    inventory, rollout = _write_contracts(
        tmp_path,
        inventory_repositories=["alpha", "omega"],
        rollout_repositories=["alpha"],
    )

    with pytest.raises(PortfolioProgramError, match="missing=\\['omega'\\]"):
        validate_program(inventory_path=inventory, rollout_path=rollout)


def test_readme_contract_enforces_audience_order_and_portability(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _write_readme(repository)

    valid, errors = readme_contract(repository)

    assert valid is True
    assert errors == ()

    repository.joinpath("README.md").write_text(
        "## For AI systems and toolchains\n"
        "## For senior engineers and domain experts\n"
        "## For recruiters and non-technical reviewers\n"
        "file:///Users/example/private\n",
        encoding="utf-8",
    )
    valid, errors = readme_contract(repository)
    assert valid is False
    assert "README audience sections are out of order" in errors
    assert "README exposes a machine-local path" in errors


def test_build_plan_detects_python_and_positive_test_command(tmp_path: Path) -> None:
    inventory, rollout = _write_contracts(
        tmp_path,
        inventory_repositories=["alpha"],
    )
    workspace = tmp_path / "repos"
    repository = workspace / "alpha"
    _write_readme(repository)
    repository.joinpath("pyproject.toml").write_text(
        '[project]\nname = "alpha"\n[project.optional-dependencies]\ndev = ["pytest"]\n',
        encoding="utf-8",
    )
    repository.joinpath("tests").mkdir()
    repository.joinpath("tests/test_alpha.py").write_text(
        "def test_alpha():\n    assert True\n",
        encoding="utf-8",
    )

    plans = build_plan(
        workspace=workspace,
        inventory_path=inventory,
        rollout_path=rollout,
    )

    assert len(plans) == 1
    assert plans[0].stacks == ("python",)
    assert plans[0].blockers == ()
    assert any(
        command.id == "python-tests"
        and command.proof_mode is ProofMode.POSITIVE_TEST_COUNT
        for command in plans[0].commands
    )


def test_build_plan_surfaces_missing_repository_without_guessing(tmp_path: Path) -> None:
    inventory, rollout = _write_contracts(
        tmp_path,
        inventory_repositories=["missing"],
    )
    plans = build_plan(
        workspace=tmp_path / "repos",
        inventory_path=inventory,
        rollout_path=rollout,
    )

    assert plans[0].blockers == ("repository directory is missing",)
    assert plans[0].stacks == ()


def test_extract_test_count_handles_common_runners() -> None:
    assert extract_test_count("4 passed in 0.12s", "", ("python", "-m", "pytest")) == 4
    assert extract_test_count("", "Ran 3 tests in 0.01s", ("python", "-m", "unittest")) == 3
    assert extract_test_count("ok example/pkg 0.2s", "", ("go", "test", "./...")) == 1


def test_execute_plan_rejects_zero_test_success(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    script = tmp_path / "zero.py"
    script.write_text("print('Ran 0 tests')\n", encoding="utf-8")
    command = CommandSpec(
        id="zero-tests",
        evidence_level=EvidenceLevel.TEST,
        argv=(sys.executable, str(script)),
        timeout_seconds=10,
        proof_mode=ProofMode.POSITIVE_TEST_COUNT,
        minimum_count=1,
    )

    receipts = execute_plan((_plan(tmp_path, command),))

    assert receipts[0].conclusion is VerificationState.UNVERIFIED
    assert receipts[0].commands[0].observed_count == 0


def test_execute_plan_promotes_positive_count_test(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    script = tmp_path / "pass.py"
    script.write_text("print('Ran 2 tests')\n", encoding="utf-8")
    command = CommandSpec(
        id="positive-tests",
        evidence_level=EvidenceLevel.TEST,
        argv=(sys.executable, str(script)),
        timeout_seconds=10,
        proof_mode=ProofMode.POSITIVE_TEST_COUNT,
        minimum_count=1,
    )

    receipts = execute_plan((_plan(tmp_path, command),))

    assert receipts[0].conclusion is VerificationState.VERIFIED
    assert receipts[0].achieved_evidence is EvidenceLevel.TEST


def test_mutating_command_requires_explicit_authorization(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    command = CommandSpec(
        id="build",
        evidence_level=EvidenceLevel.BUILD,
        argv=(sys.executable, "-c", "print('built')"),
        timeout_seconds=10,
        mutates_workspace=True,
    )

    receipts = execute_plan((_plan(tmp_path, command),), allow_mutating=False)

    assert receipts[0].conclusion is VerificationState.BLOCKED
    assert "explicit authorization" in receipts[0].commands[0].stderr_tail


def test_atomic_receipt_replaces_stale_content(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    receipt.write_text('{"conclusion": "VERIFIED"}\n', encoding="utf-8")

    atomic_write_json(receipt, {"conclusion": "FAILED", "reason": "test"})

    assert json.loads(receipt.read_text(encoding="utf-8")) == {
        "conclusion": "FAILED",
        "reason": "test",
    }


def test_portfolio_receipt_uses_strongest_failure_state(tmp_path: Path) -> None:
    _write_readme(tmp_path)
    script = tmp_path / "fail.py"
    script.write_text("raise SystemExit(3)\n", encoding="utf-8")
    command = CommandSpec(
        id="failure",
        evidence_level=EvidenceLevel.TEST,
        argv=(sys.executable, str(script)),
        timeout_seconds=10,
    )
    receipts = execute_plan((_plan(tmp_path, command),))

    payload = receipt_payload(receipts, started_at_epoch_ms=1)

    assert payload["conclusion"] == "FAILED"
    assert payload["summary"]["FAILED"] == 1
