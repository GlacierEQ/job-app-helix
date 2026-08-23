"""Public, reproducible core for the Job-App Helix campaign and README Mesh engines."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .campaign import CampaignPolicy, LaunchScenario, run_campaign
from .models import CampaignDecision, CampaignReport, StageResult, StageStatus
from .readme_mesh import (
    MeshArtifacts,
    ReadmeMeshError,
    apply_block,
    build_artifacts,
    render_repository_block,
    validate_mesh,
)
from .readme_mesh_manifest import load_mesh

SUBMISSION_INTEGRITY_FREEZE = True
SUBMISSION_INTEGRITY_FREEZE_REASON = (
    "SUBMISSION_FROZEN: Helix may prepare application artifacts, but live "
    "submission is disabled until the external handoff proves the intended "
    "artifact set survived without single-file collapse and returns a "
    "verifiable submission receipt."
)


def _install_submission_integrity_freeze() -> None:
    """Fail closed before any adapter or state store can claim SUBMITTED."""
    from .application_operations import ApplicationStore, JsonApiApplicationAdapter

    original_transition = ApplicationStore.transition
    original_submit = JsonApiApplicationAdapter.submit

    def guarded_transition(
        self: ApplicationStore,
        application_id: str,
        status: str,
        *,
        external_reference: str | None = None,
        note: str = "",
    ) -> None:
        if status.upper() == "SUBMITTED":
            raise RuntimeError(SUBMISSION_INTEGRITY_FREEZE_REASON)
        original_transition(
            self,
            application_id,
            status,
            external_reference=external_reference,
            note=note,
        )

    def guarded_submit(
        self: JsonApiApplicationAdapter,
        packet: Mapping[str, Any],
        *,
        submit: bool = False,
    ) -> Mapping[str, Any]:
        if submit:
            raise RuntimeError(SUBMISSION_INTEGRITY_FREEZE_REASON)
        return original_submit(self, packet, submit=False)

    ApplicationStore.transition = guarded_transition
    JsonApiApplicationAdapter.submit = guarded_submit


_install_submission_integrity_freeze()

__all__ = [
    "CampaignDecision",
    "CampaignPolicy",
    "CampaignReport",
    "LaunchScenario",
    "MeshArtifacts",
    "ReadmeMeshError",
    "SUBMISSION_INTEGRITY_FREEZE",
    "SUBMISSION_INTEGRITY_FREEZE_REASON",
    "StageResult",
    "StageStatus",
    "apply_block",
    "build_artifacts",
    "load_mesh",
    "render_repository_block",
    "run_campaign",
    "validate_mesh",
]

__version__ = "0.2.0"
