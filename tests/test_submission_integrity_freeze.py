from __future__ import annotations

from pathlib import Path

import pytest

from job_app_helix import application_operations as operations
from job_app_helix.application_operations import ApplicationStore


def test_live_json_submission_adapter_is_removed() -> None:
    assert not hasattr(operations, "JsonApiApplicationAdapter")


def test_store_rejects_submission_state_before_lookup() -> None:
    store = object.__new__(ApplicationStore)

    with pytest.raises(ValueError, match="invalid application status: SUBMITTED"):
        store.transition("app-integrity-test", "SUBMITTED")


def test_external_reference_cannot_mutate_lifecycle_state() -> None:
    store = object.__new__(ApplicationStore)

    with pytest.raises(ValueError, match="external_reference may not mutate"):
        store.transition(
            "app-integrity-test",
            "READY",
            external_reference="ats-123",
        )


def test_source_contains_no_retired_submission_signatures() -> None:
    source = Path(operations.__file__).read_text(encoding="utf-8")
    forbidden = (
        "class JsonApiApplicationAdapter",
        "SUBMISSION_PACKET.json",
        'method="POST"',
        '"status": "SUBMITTED" if 200 <= response.status < 300',
        'raise ValueError("SUBMITTED requires external_reference")',
    )
    for signature in forbidden:
        assert signature not in source, signature
