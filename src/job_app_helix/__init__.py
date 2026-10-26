"""Public, reproducible core for the Job-App Helix campaign and README Mesh engines.

Capability-focused portfolio control plane — executes evidence-led hiring automation,
federates capabilities via monolith catalog, resolves multi-language placement via Tower of Babel.
"""

from .agent_cli import main as agent_main
from .automation_engine import AutomationResult, run_automation, run_proof
from .campaign import CampaignPolicy, LaunchScenario, run_campaign
from .capability_federation import (
    CapabilityQuery,
    FederatedCapability,
    ResolutionReceipt,
    federate_capabilities,
)
from .evidence_bridge import (
    BridgeReceipt,
    EvidenceItem,
    SpineEntry,
    bridge_evidence,
    bridge_from_ledger,
)
from .evidence_ledger import EvidenceEntry, Ledger, build_ledger, write_ledger
from .models import CampaignDecision, CampaignReport, StageResult, StageStatus
from .monolith_sync import main as sync_monolith
from .readme_mesh import (
    MeshArtifacts,
    ReadmeMeshError,
    apply_block,
    build_artifacts,
    render_repository_block,
    validate_mesh,
)
from .readme_mesh_manifest import load_mesh
from .tower_resolution import CapabilityRequirement, PlacementDecision, resolve_placement
from .tower_resolution import ResolutionReceipt as TowerResolutionReceipt

__all__ = [
    "AutomationResult",
    "BridgeReceipt",
    "CampaignDecision",
    "CampaignPolicy",
    "CampaignReport",
    "CapabilityQuery",
    "CapabilityRequirement",
    "EvidenceEntry",
    "EvidenceItem",
    "FederatedCapability",
    "LaunchScenario",
    "Ledger",
    "MeshArtifacts",
    "PlacementDecision",
    "ReadmeMeshError",
    "ResolutionReceipt",
    "SpineEntry",
    "StageResult",
    "StageStatus",
    "TowerResolutionReceipt",
    "agent_main",
    "apply_block",
    "bridge_evidence",
    "bridge_from_ledger",
    "build_artifacts",
    "build_ledger",
    "federate_capabilities",
    "load_mesh",
    "render_repository_block",
    "resolve_placement",
    "run_automation",
    "run_campaign",
    "run_proof",
    "sync_monolith",
    "validate_mesh",
    "write_ledger",
]

__version__ = "1.0.0-capability"