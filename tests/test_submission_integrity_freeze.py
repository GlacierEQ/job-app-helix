from __future__ import annotations

import pytest

import job_app_helix
from job_app_helix.application_operations import (
    ApplicationStore,
    JsonApiApplicationAdapter,
)


def test_live_adapter_submission_is_frozen() -> None:
    adapter = JsonApiApplicationAdapter("https://example.invalid/applications")
    packet = {"application_id": "app-integrity-test"}

    dry_run = adapter.submit(packet)
    assert dry_run["status"] == "DRY_RUN"
    assert dry_run["submission_performed"] is False

    with pytest.raises(RuntimeError, match="SUBMISSION_FROZEN"):
        adapter.submit(packet, submit=True)


def test_store_cannot_claim_submitted_from_external_reference() -> None:
    store = object.__new__(ApplicationStore)

    with pytest.raises(RuntimeError, match="SUBMISSION_FROZEN"):
        store.transition(
            "app-integrity-test",
            "SUBMITTED",
            external_reference="ats-123",
        )


def test_freeze_is_public_runtime_state() -> None:
    assert job_app_helix.SUBMISSION_INTEGRITY_FREEZE is True
    assert "artifact set" in job_app_helix.SUBMISSION_INTEGRITY_FREEZE_REASON
