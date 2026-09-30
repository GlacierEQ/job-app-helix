from __future__ import annotations

import json
import subprocess
from pathlib import Path

from job_app_helix.estate_recovery_census import (
    build_estate_recovery_census,
    inspect_repository,
    load_repository_names,
)


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess((), returncode, stdout=stdout, stderr=stderr)


def test_manifest_normalizes_owner_qualified_names_and_deduplicates(tmp_path: Path) -> None:
    manifest = tmp_path / "repos.json"
    manifest.write_text(
        json.dumps({"repositories": ["GlacierEQ/AKOS", "AKOS", "ECHO"]}),
        encoding="utf-8",
    )
    assert load_repository_names(manifest) == ("AKOS", "ECHO")


def test_missing_repository_is_highest_priority_without_claiming_deletion() -> None:
    def runner(command):
        assert command[:2] == ("gh", "api")
        return _completed(stderr="HTTP 404", returncode=1)

    row = inspect_repository("GlacierEQ", "missing", runner=runner)
    assert row.exists is False
    assert row.recovery_class == "MISSING_OR_INACCESSIBLE"
    assert row.priority_score == 100
    assert "404" in (row.error or "")


def test_recovery_signal_without_power_is_prioritized_above_thin_repo() -> None:
    metadata = {
        "archived": False,
        "disabled": False,
        "fork": False,
        "size": 120,
        "default_branch": "main",
        "pushed_at": "2026-08-18T12:00:00Z",
    }

    def runner(command):
        endpoint = command[2]
        if endpoint.endswith("signal-only"):
            return _completed(json.dumps(metadata))
        if endpoint.endswith("thin"):
            return _completed(json.dumps({**metadata, "size": 4}))
        if "signal-only/commits" in endpoint:
            return _completed("restore clipped code\nrollback neutralization\n")
        if "thin/commits" in endpoint:
            return _completed("normal maintenance\n")
        raise AssertionError(command)

    census = build_estate_recovery_census(
        "GlacierEQ",
        ("thin", "signal-only"),
        runner=runner,
    )
    assert census.observations[0].repository == "signal-only"
    assert census.observations[0].recovery_class == "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER"
    assert census.observations[1].recovery_class == "THIN_EXECUTABLE_SURFACE"


def test_recovery_with_executable_power_is_not_mislabeled_as_powerless() -> None:
    metadata = json.dumps(
        {
            "archived": False,
            "disabled": False,
            "fork": False,
            "size": 300,
            "default_branch": "main",
            "pushed_at": "2026-08-18T12:00:00Z",
        }
    )

    def runner(command):
        if "/commits?" in command[2]:
            return _completed("restore runtime engine\nimplement proof executor\n")
        return _completed(metadata)

    row = inspect_repository("GlacierEQ", "powered", runner=runner)
    assert row.recovery_signal_count == 1
    assert row.power_signal_count == 2
    assert row.recovery_class == "RECOVERY_IN_PROGRESS"


def test_archived_repository_is_preserved_not_treated_as_missing() -> None:
    metadata = json.dumps(
        {
            "archived": True,
            "disabled": False,
            "fork": False,
            "size": 300,
            "default_branch": "main",
            "pushed_at": "2026-08-18T12:00:00Z",
        }
    )

    def runner(command):
        if "/commits?" in command[2]:
            return _completed("")
        return _completed(metadata)

    row = inspect_repository("GlacierEQ", "archive", runner=runner)
    assert row.exists is True
    assert row.recovery_class == "ARCHIVED_PRESERVE"
