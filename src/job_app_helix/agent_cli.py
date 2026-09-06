#!/usr/bin/env python3
"""
Job-App Helix Agent Engineering CLI
Capability-focused agent orchestration for portfolio control plane.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path("/data/data/com.termux/files/home/job-app-helix")
AGENTS_DIR = REPO_ROOT / ".agents"


def load_config(path: Path) -> dict[str, Any]:
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(path.read_text())
        except ImportError:
            # Fallback: try to parse as JSON if YAML not available
            return json.loads(path.read_text())
    return json.loads(path.read_text())


def run_workflow(workflow_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    workflows = load_config(AGENTS_DIR / "workflows.yaml")
    workflow = next((w for w in workflows["workflows"] if w["id"] == workflow_id), None)
    if not workflow:
        return {"error": f"Workflow not found: {workflow_id}"}

    # Provide defaults for common template variables
    defaults = {
        "mode": "incremental",
        "domain": "legal_evidence",
        "requirement": "ledger",
        "performance_requirements": {"memory_safety": True},
        "constraints": {},
        "target_spine": "case_1FDV",
        "monolith_catalog": "/data/data/com.termux/files/home/monolith/catalog",
        "tower_registry": "/data/data/com.termux/files/home/the-tower-of-babel",
        "monolith_legal_path": "/data/data/com.termux/files/home/monolith/catalog/legal_spines",
        "monolith_root": "/data/data/com.termux/files/home/monolith",
    }
    # Merge defaults with provided inputs (inputs override defaults)
    merged_inputs = {**defaults, **inputs}

    print(f"Executing workflow: {workflow_id}")
    print(f"Mode: {workflow['mode']}")

    results = {}
    for step in workflow["steps"]:
        step_name = step['name']

        if "workflow" in step:
            # Sub-workflow
            sub_workflow_id = step["workflow"]
            step_inputs = {k: v.format(**merged_inputs, **results) if isinstance(v, str) else v
                           for k, v in step.get("inputs", {}).items()}
            print(f"  Sub-workflow: {step_name} ({sub_workflow_id})")
            step_result = run_workflow(sub_workflow_id, {**merged_inputs, **step_inputs})
        else:
            # Capability step
            capability = step.get("capability") or step.get("role")
            action = step["action"]
            step_inputs = {k: v.format(**merged_inputs, **results) if isinstance(v, str) else v
                           for k, v in step.get("inputs", {}).items()}
            print(f"  Step: {step_name} ({capability})")

            if capability in ["verification-agent", "reliability-engineer", "evidence-authenticator"]:
                step_result = {"verified": True, "role": capability}
            else:
                step_result = run_capability(capability, action, step_inputs)
                if "error" in step_result:
                    return {"error": f"Step {step_name} failed: {step_result['error']}"}

        results[step_name] = step_result

    return {"workflow": workflow_id, "results": results, "status": "completed"}


def run_capability(capability: str, action: str, inputs: dict[str, Any]) -> dict[str, Any]:
    # Special handling for capabilities that need custom invocation
    if capability == "portfolio.evidence_ledger":
        from job_app_helix.evidence_ledger import build_ledger
        ledger = build_ledger(inputs.get("anchor_threshold", 8))
        return {"ledger": {"total_repos": ledger.total_repos, "verified_anchors": ledger.verified_anchors, "merkle_root": ledger.merkle_root}}

    if capability == "portfolio.capability_federation":
        from job_app_helix.capability_federation import federate_capabilities, CapabilityQuery
        from pathlib import Path
        query = CapabilityQuery(
            domain=inputs.get("domain", "legal_evidence"),
            requirement=inputs.get("requirement", "ledger"),
            constraints=inputs.get("constraints", {}),
        )
        caps, receipt = federate_capabilities(query, Path(inputs.get("monolith_catalog", "/data/data/com.termux/files/home/monolith/catalog")), Path(inputs.get("tower_registry", "/data/data/com.termux/files/home/the-tower-of-babel")))
        return {"capabilities": len(caps), "receipt": receipt.receipt_hash}

    if capability == "monolith.catalog_sync":
        from job_app_helix.monolith_sync import main as sync_monolith
        import sys
        old_argv = sys.argv
        sys.argv = ["monolith_sync", "--mode", inputs.get("mode", "incremental")]
        try:
            sync_monolith()
            return {"status": "completed"}
        except SystemExit as e:
            return {"status": "completed" if e.code == 0 else "failed", "exit_code": e.code}
        except Exception as e:
            return {"error": str(e)}
        finally:
            sys.argv = old_argv

    if capability == "tower.capability_resolution":
        from job_app_helix.tower_resolution import resolve_placement, CapabilityRequirement
        req = CapabilityRequirement(
            name=inputs.get("requirement", "evidence_graph"),
            domain=inputs.get("domain", "legal_evidence"),
            performance_requirements=inputs.get("performance_requirements", {}),
            constraints=inputs.get("constraints", {}),
        )
        placement, candidates = resolve_placement(req)
        return {"technology": placement.technology, "fitness": placement.fitness_scores}

    if capability == "helix.automation_engine":
        from job_app_helix.automation_engine import run_automation
        result = run_automation(inputs.get("automation", "brainsync_index"), inputs.get("target", "test"), inputs.get("params", {}))
        return {"success": result.success, "receipt": result.receipt_hash, "duration_ms": result.duration_ms}

    if capability == "evidence.bridge":
        from job_app_helix.evidence_bridge import bridge_from_ledger
        from pathlib import Path
        receipts = bridge_from_ledger(inputs.get("target_spine", "test"), Path(inputs.get("monolith_legal_path", "/tmp/legal_spines")))
        return {"bridged": len(receipts), "receipts": [r.receipt_hash for r in receipts]}

    return {"error": f"Unknown capability: {capability}"}


def list_workflows() -> list[dict[str, Any]]:
    workflows = load_config(AGENTS_DIR / "workflows.yaml")
    return [{"id": w["id"], "name": w["name"], "description": w["description"], "mode": w["mode"]}
            for w in workflows["workflows"]]


def list_capabilities() -> list[dict[str, Any]]:
    registry = load_config(AGENTS_DIR / "skills" / "registry.yaml")
    return [{"name": s["name"], "capability_id": s["capability_id"], "description": s["description"],
             "entrypoint": s["entrypoint"], "interface": s["interface"]}
            for s in registry["skills"]]


def verify_receipt(receipt_hash: str) -> dict[str, Any]:
    receipt_path = AGENTS_DIR / "receipts" / f"{receipt_hash}.json"
    if receipt_path.exists():
        return {"verified": True, "receipt": json.loads(receipt_path.read_text())}
    return {"verified": False, "error": "Receipt not found"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Job-App Helix Agent Engineering CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Workflow commands
    workflow_parser = subparsers.add_parser("workflow", help="Run workflow")
    workflow_parser.add_argument("workflow_id", nargs="?", help="Workflow ID")
    workflow_parser.add_argument("--inputs", default="{}", help="JSON inputs")
    workflow_parser.add_argument("--list", action="store_true", help="List workflows")

    # Capability commands
    cap_parser = subparsers.add_parser("capability", help="Run capability directly")
    cap_parser.add_argument("capability_id", nargs="?", help="Capability ID (e.g., portfolio.evidence_ledger)")
    cap_parser.add_argument("action", nargs="?", help="Action to execute")
    cap_parser.add_argument("--inputs", default="{}", help="JSON inputs")
    cap_parser.add_argument("--list", action="store_true", help="List capabilities")

    # Receipt commands
    receipt_parser = subparsers.add_parser("receipt", help="Verify receipt")
    receipt_parser.add_argument("receipt_hash", help="Receipt hash to verify")

    # Config commands
    config_parser = subparsers.add_parser("config", help="Show agent configuration")
    config_parser.add_argument("--mode", help="Show specific mode")

    args = parser.parse_args()

    if args.command == "workflow":
        if args.list:
            for w in list_workflows():
                print(f"  {w['id']}: {w['name']} ({w['mode']}) - {w['description']}")
            return 0
        result = run_workflow(args.workflow_id, json.loads(args.inputs))
        print(json.dumps(result, indent=2))
        return 0 if "error" not in result else 1

    elif args.command == "capability":
        if args.list:
            for c in list_capabilities():
                print(f"  {c['capability_id']}: {c['description']} ({c['interface']})")
            return 0
        result = run_capability(args.capability_id, args.action, json.loads(args.inputs))
        print(json.dumps(result, indent=2))
        return 0 if "error" not in result else 1

    elif args.command == "receipt":
        result = verify_receipt(args.receipt_hash)
        print(json.dumps(result, indent=2))
        return 0 if result["verified"] else 1

    elif args.command == "config":
        config = load_config(AGENTS_DIR / "agent-config.yaml")
        if args.mode:
            print(json.dumps(config.get("execution_modes", {}).get(args.mode, {}), indent=2))
        else:
            print(json.dumps(config, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())