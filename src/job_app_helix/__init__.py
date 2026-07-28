"""Public, reproducible core for the Job-App Helix campaign engine."""

from .campaign import CampaignPolicy, LaunchScenario, run_campaign
from .models import CampaignDecision, CampaignReport, StageResult, StageStatus

__all__ = [
    "CampaignDecision",
    "CampaignPolicy",
    "CampaignReport",
    "LaunchScenario",
    "StageResult",
    "StageStatus",
    "run_campaign",
]

__version__ = "0.1.0"
