"""Regressions for capability suppression in Helix's default execution paths."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from job_app_helix import genius_build
from job_app_helix.genius_engine import invent_estate, select_mechanisms


def _wave_module():
    path = Path(__file__).resolve().parents[1] / "excellence/tools/run_wave_c_elevate.py"
    spec = importlib.util.spec_from_file_location("wave_c_limit_seed_regression", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wave_c_never_deletes_an_existing_regression_test(tmp_path, monkeypatch):
    wave = _wave_module()
    leaf = tmp_path / "repos/leaf"
    test_file = leaf / "tests/test_excellence_state_contract.py"
    test_file.parent.mkdir(parents=True)
    original = "def test_preserved():\n    assert True\n"
    test_file.write_text(original, encoding="utf-8")
    observed = []

    def elevator(leaf_path, scratch):
        observed.append(test_file.read_text(encoding="utf-8") if test_file.exists() else None)
        return {"name": leaf_path.name, "grade": "GAP", "blocker": "NEEDS_ENGINEERING"}

    monkeypatch.setattr(wave, "ROOT", tmp_path)
    monkeypatch.setattr(wave, "REPOS", tmp_path / "repos")
    monkeypatch.setattr(wave, "_load_elevator", lambda: SimpleNamespace(elevate_leaf=elevator))
    wave.elevate_one("leaf", None)
    assert observed == [original]
    assert test_file.read_text(encoding="utf-8") == original


def test_wave_c_partial_execution_is_not_marked_closed(tmp_path, monkeypatch):
    wave = _wave_module()
    plan_path = tmp_path / "excellence/waves/wave_c_plan.json"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps({"generated_at": "2026-08-10", "leaves": [{"leaf": "leaf"}]}))
    (tmp_path / "excellence/receipts").mkdir(parents=True)
    (tmp_path / "excellence/framework").mkdir(parents=True)
    monkeypatch.setattr(wave, "ROOT", tmp_path)
    monkeypatch.setattr(wave, "elevate_one", lambda name, _: {"name": name, "grade": "GAP", "blocker": "NEXT_CAPABILITY"})
    monkeypatch.setattr(sys, "argv", ["wave-c", "--workers", "1"])
    wave.main()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    receipt = json.loads((tmp_path / "excellence/receipts/wave_c_latest.json").read_text())
    assert "closed_at" not in plan
    assert receipt["wave_c"]["phase"] == "IN_PROGRESS"
    assert receipt["run"] == "WAVE-C-PARTIAL"


def test_impact_subject_default_includes_all_discovered_leaves(tmp_path, monkeypatch):
    queue = tmp_path / "registry/impact_queue.json"
    queue.parent.mkdir(parents=True)
    names = [f"GlacierEQ/capability-{i:02}" for i in range(40)]
    queue.write_text(json.dumps({"queue": [{"suggested_leaves": names}]}))
    monkeypatch.setattr(genius_build, "library_of_links_root", lambda: tmp_path)
    found = genius_build.subjects_from_impact()
    assert set(names).issubset({row["repository"] for row in found})
    assert len(found) >= len(names)
    assert len(genius_build.subjects_from_impact(limit=2)) == 2


def test_default_mechanism_selection_is_not_top_four():
    assert len(select_mechanisms("general")) > 4
    assert len(select_mechanisms("general", limit=2)) == 2


def test_default_estate_invent_preserves_alternate_solutions(tmp_path):
    bundle = invent_estate(
        [{"repository": "GlacierEQ/engineering-innovation", "description": "full-stack engineering recovery"}],
        live_research=False,
        accumulate=False,
        publish_links=False,
        root=tmp_path,
    )
    assert bundle["count"] == 1
    assert len(bundle["runs"][0]["solutions"]) > 1


def test_limited_wave_run_does_not_claim_full_wave_completion(tmp_path, monkeypatch):
    wave = _wave_module()
    plan_path = tmp_path / "excellence/waves/wave_c_plan.json"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps({"generated_at": "2026-08-10", "leaves": [{"leaf": "one"}, {"leaf": "two"}]}))
    (tmp_path / "excellence/receipts").mkdir(parents=True)
    (tmp_path / "excellence/framework").mkdir(parents=True)
    monkeypatch.setattr(wave, "ROOT", tmp_path)
    monkeypatch.setattr(wave, "elevate_one", lambda name, _: {"name": name, "grade": "PROMOTED"})
    monkeypatch.setattr(sys, "argv", ["wave-c", "--limit", "1", "--workers", "1"])
    wave.main()
    plan = json.loads(plan_path.read_text())
    receipt = json.loads((tmp_path / "excellence/receipts/wave_c_latest.json").read_text())
    assert plan["run_status"] == "IN_PROGRESS"
    assert "closed_at" not in plan
    assert receipt["wave_c"]["enrolled"] == 2
    assert receipt["wave_c"]["selected"] == 1
    assert receipt["wave_c"]["full_scope"] is False


def test_failed_evolution_proof_preserves_the_evolution_target():
    from job_app_helix.promotion_invariants import PromotionAssessment, enforce_nonpromoted_state
    assessment = PromotionAssessment(
        eligible=False,
        reasons=("IMPLEMENTATION_PROOF_MISSING",),
        scaffold_evidence=(),
        implementation_proof_valid=False,
        source_sha="abc",
    )
    corrected = enforce_nonpromoted_state(
        {"principal_state": "EVOLVING", "capability_target": "autonomous engineering synthesis"},
        assessment,
    )
    assert corrected["principal_state"] == "OPERABLE"  # truth-preserving proof label
    assert corrected["target_principal_state"] == "EVOLVING"
    assert corrected["capability_target"] == "autonomous engineering synthesis"
    assert corrected["recovery_required"] is True


def test_public_compiler_does_not_silently_hide_evidence_capabilities():
    site = Path(__file__).resolve().parents[1] / "site"
    compiler = (site / "compiler.js").read_text(encoding="utf-8")
    proofs = (site / "capability_proof_lens.js").read_text(encoding="utf-8")
    for forbidden in (
        "rows.slice(0, 3)",
        "capabilities.slice(0, 10)",
        "matched.slice(0, 6)",
        "Array.from(matched).slice(0, 2)",
    ):
        assert forbidden not in compiler, forbidden
    for forbidden in (
        "evidence.slice(0, 4)",
        "receipts.slice(0, 5)",
        'proofs.slice(0, depth === "recruiter" ? 3 : 6)',
    ):
        assert forbidden not in proofs, forbidden
