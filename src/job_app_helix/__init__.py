"""Public, reproducible core for the Job-App Helix campaign and README Mesh engines."""

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

__all__ = [
    "CampaignDecision",
    "CampaignPolicy",
    "CampaignReport",
    "LaunchScenario",
    "MeshArtifacts",
    "ReadmeMeshError",
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
