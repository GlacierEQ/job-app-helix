from __future__ import annotations

import json
import re
from pathlib import Path

from job_app_helix.role_proof_contracts import build_role_proof_contract, role_contract_ids

ROOT = Path(__file__).resolve().parents[1]
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}(?!\d)")
PRIVATE_OPERATIONAL_STATES = {
    "DRAFTED",
    "SOURCE_CHECKED",
    "READY_TO_SEND",
    "SENT",
    "ACKNOWLEDGED",
    "INTERVIEW",
    "CLOSED",
    "NO_RESPONSE",
    "SUBMITTED_AWAITING_REVIEW",
}


def test_role_proof_contracts_never_carry_private_application_operations() -> None:
    forbidden_keys = {
        "recruiter",
        "recruiter_contact",
        "recruiter_message_verbatim",
        "draft_reply",
        "message_id",
        "phone",
        "email",
        "provider_receipts",
        "submission_receipt",
        "application_state",
        "submission_state",
        "workflow_state",
        "approval_required",
        "external_receipt",
        "received_at_local",
        "sent",
    }

    for role_id in role_contract_ids():
        contract = build_role_proof_contract(role_id)
        rendered = json.dumps(contract, sort_keys=True)
        assert not EMAIL.search(rendered)
        assert not PHONE.search(rendered)

        def walk(value: object) -> None:
            if isinstance(value, dict):
                assert forbidden_keys.isdisjoint(value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
            elif isinstance(value, str):
                assert value not in PRIVATE_OPERATIONAL_STATES

        walk(contract)


def test_public_company_dossiers_are_intelligence_only_without_person_pii() -> None:
    forbidden_keys = {
        "recruiter_contact",
        "recruiter_message_verbatim",
        "draft_reply",
        "message_id",
        "phone",
        "email",
        "provider_receipts",
        "submission_receipt",
        "application_state",
        "interview_state",
        "submission_state",
        "workflow_state",
        "approval_required",
        "external_receipt",
        "received_at_local",
        "sent",
    }
    dossier_dir = ROOT / "manifests" / "company_dossiers"

    for path in sorted(dossier_dir.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        assert not EMAIL.search(text), path
        assert not PHONE.search(text), path

        def walk(value: object, source: Path) -> None:
            if isinstance(value, dict):
                assert forbidden_keys.isdisjoint(value), source
                for child in value.values():
                    walk(child, source)
            elif isinstance(value, list):
                for child in value:
                    walk(child, source)

        walk(payload, path)


def test_blackstraw_public_dossier_is_role_intelligence_only() -> None:
    path = (
        ROOT
        / "manifests"
        / "company_dossiers"
        / "blackstraw_ai_role_intelligence_2026_10_02.json"
    )
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["companies"][0]["company_id"] == "blackstraw_ai"
    assert payload["companies"][0]["track_state"] == (
        "LIVE_ROLE_INTELLIGENCE_TRANSFERABLE_PROOF"
    )
    assert "Murali" not in text
    assert "unsent" not in text.lower()
    assert "draft" not in text.lower()


def test_public_helix_does_not_persist_active_application_campaign_state() -> None:
    leaked = sorted((ROOT / "status").glob("ACTIVE_JOB_CAMPAIGN_*.json"))
    assert leaked == []
