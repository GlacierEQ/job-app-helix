from __future__ import annotations

import json

from job_app_helix import CampaignDecision, CampaignPolicy, LaunchScenario, run_campaign


def test_nominal_campaign_goes_without_refinement() -> None:
    report = run_campaign(LaunchScenario.nominal())

    assert report.decision is CampaignDecision.GO
    assert report.refinements == ()
    assert report.recovered is False
    assert all(result.acceptable for result in report.final_results)


def test_recoverable_campaign_uses_only_declared_contingencies() -> None:
    report = run_campaign(LaunchScenario.recoverable())

    assert report.decision is CampaignDecision.GO
    assert report.recovered is True
    assert {refinement.action for refinement in report.refinements} == {
        "replay-buffered-telemetry",
        "apply-predeclared-derated-profile",
        "activate-declared-ground-contingency",
    }
    assert all(result.acceptable for result in report.final_results)


def test_recoverable_campaign_holds_when_refinement_is_disabled() -> None:
    report = run_campaign(
        LaunchScenario.recoverable(),
        CampaignPolicy(allow_refinement=False),
    )

    assert report.decision is CampaignDecision.NO_GO
    assert report.refinements == ()


def test_hard_no_go_does_not_tune_itself_to_pass() -> None:
    report = run_campaign(LaunchScenario.hard_no_go())

    assert report.decision is CampaignDecision.NO_GO
    assert report.refinements == ()
    assert any(not result.acceptable for result in report.final_results)


def test_report_is_machine_readable() -> None:
    payload = run_campaign(LaunchScenario.nominal()).to_dict()
    encoded = json.dumps(payload)

    assert '"decision": "GO"' in encoded
    assert payload["metadata"]["engine"] == "job-app-helix"
