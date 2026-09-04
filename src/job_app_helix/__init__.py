"""Public, reproducible core for the Job-App Helix campaign and README Mesh engines.

Capability-focused portfolio control plane — executes evidence-led hiring automation,
federates capabilities via monolith catalog, resolves multi-language placement via Tower of Babel.
"""

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

from .evidence_ledger import build_ledger, EvidenceEntry, Ledger, write_ledger
from .capability_federation import federate_capabilities, CapabilityQuery, FederatedCapability, ResolutionReceipt
from .monolith_sync import main as sync_monolith
from .tower_resolution import resolve_placement, CapabilityRequirement, PlacementDecision, ResolutionReceipt as TowerResolutionReceipt
from .automation_engine import run_automation, run_proof, AutomationResult
from .evidence_bridge import bridge_evidence, bridge_from_ledger, EvidenceItem, SpineEntry, BridgeReceipt
from .agent_cli import main as agent_main

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
    "build_ledger",
    "EvidenceEntry",
    "Ledger",
    "write_ledger",
    "federate_capabilities",
    "CapabilityQuery",
    "FederatedCapability",
    "ResolutionReceipt",
    "sync_monolith",
    "resolve_placement",
    "CapabilityRequirement",
    "PlacementDecision",
    "TowerResolutionReceipt",
    "run_automation",
    "run_proof",
    "AutomationResult",
    "bridge_evidence",
    "bridge_from_ledger",
    "EvidenceItem",
    "SpineEntry",
    "BridgeReceipt",
    "agent_main",
]

__version__ = "1.0.0-capability"