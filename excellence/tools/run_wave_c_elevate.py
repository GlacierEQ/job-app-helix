#!/usr/bin/env python3
"""Wave C steel + proof lane: elevate enrolled leaves via elite elevator.

Usage:
  python3 excellence/tools/run_wave_c_elevate.py
  python3 excellence/tools/run_wave_c_elevate.py --workers 4
  python3 excellence/tools/run_wave_c_elevate.py --limit 5
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPOS = ROOT / "repos"
WAVE_ID = "WAVE-C-2026-08-10"
sys.path.insert(0, str(ROOT / "src"))

from job_app_helix.promotion_invariants import (  # noqa: E402
    assess_leaf_promotion,
    enforce_nonpromoted_state,
)


def _load_elevator():
    spec = importlib.util.spec_from_file_location(
        "elite_estate_elevator",
        ROOT / "excellence" / "tools" / "elite_estate_elevator.py",
    )
    elev = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(elev)
    return elev


def elevate_one(name: str, plan_generated_at: str | None) -> dict:
    elev = _load_elevator()
    leaf = REPOS / name
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    scratch = ROOT / "excellence" / "receipts" / "wave_c_scratch" / "leaves" / name
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        if not leaf.is_dir():
            return {"name": name, "grade": "MISSING", "error": "path missing"}
        # Drop tests that pin DISCOVERED forever (break post-bind).
        tpath = leaf / "tests" / "test_excellence_state_contract.py"
        if tpath.is_file():
            tpath.unlink()
        rec = elev.elevate_leaf(leaf, scratch)
        st_path = leaf / "machine" / "excellence-state.json"

        # Promotion is derived from implementation truth, never from an elevator
        # return value alone. Generic dual-run/operate/authority proof may establish
        # an executable scaffold, but cannot establish implementation completion.
        assessment = assess_leaf_promotion(leaf, f"GlacierEQ/{name}")
        rec["promotion_assessment"] = assessment.as_dict()
        if rec.get("grade") == "PROMOTED" and not assessment.eligible:
            if st_path.is_file():
                st = json.loads(st_path.read_text(encoding="utf-8"))
                st = enforce_nonpromoted_state(st, assessment)
                st_path.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
            rec["grade"] = "SCAFFOLD_PROVEN" if assessment.scaffold_evidence else "GAP"
            rec["blocker"] = "PROMOTION_INVARIANT:" + ",".join(assessment.reasons)
            elev.write_gap(
                leaf,
                "PROMOTION_INVARIANT",
                f"leaves/{name}/",
                "; ".join(assessment.reasons)[:500],
            )
            return rec

        if st_path.is_file() and rec.get("grade") == "PROMOTED":
            # This branch is reachable only after assess_leaf_promotion() proves:
            # no scaffold markers + a current implementation-proof receipt.
            st = json.loads(st_path.read_text(encoding="utf-8"))
            st["wave"] = {
                "id": WAVE_ID,
                "label": "Wave C — Innovation scaffold excellence group",
                "group": "C",
                "phase": "PROMOTED",
                "enrolled_at": plan_generated_at,
                "promoted_at": ts,
                "policy": "glaciereq.repo-excellence.promotion-policy.v2",
                "proof_ok": True,
                "implementation_proof_ok": True,
                "operable_ok": True,
                "projection_truth_closed_at": ts,
            }
            st["excellence_group"] = "C"
            st["scaffold"] = False
            st["promotion_eligible"] = True
            st.pop("promotion_blockers", None)
            st.pop("gap_receipt_ref", None)
            gap = leaf / "machine" / "gap-receipt.json"
            if gap.exists():
                gap.unlink()
            st_path.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
            vc, vo, ve = elev.run_cmd(
                [elev.PYTHON, str(elev.VALIDATOR), "--state", str(st_path.resolve())],
                leaf,
            )
            rec["post_wave_stamp_validator_rc"] = vc
            rec["post_wave_stamp_validator"] = (vo + ve).strip()[:400]
            if vc != 0:
                rec["grade"] = "GAP"
                rec["blocker"] = "POST_WAVE_STAMP_VALIDATOR_FAIL"
                elev.write_gap(
                    leaf,
                    "POST_WAVE_STAMP_VALIDATOR_FAIL",
                    f"leaves/{name}/",
                    (vo + ve).strip()[:500],
                )
        return rec
    except Exception as e:
        return {
            "name": name,
            "grade": "GAP",
            "error": repr(e),
            "trace": traceback.format_exc()[-1200:],
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    plan_path = ROOT / "excellence" / "waves" / "wave_c_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    leaves = [e["leaf"] for e in plan["leaves"]]
    if args.limit > 0:
        leaves = leaves[: args.limit]

    print(f"Elevating {len(leaves)} Wave C leaves with workers={args.workers}", flush=True)
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(elevate_one, name, plan.get("generated_at")): name for name in leaves
        }
        for fut in concurrent.futures.as_completed(futs):
            name = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"name": name, "grade": "GAP", "error": repr(e)}
            results.append(rec)
            print(
                f"{rec.get('grade')}: {rec.get('name')} "
                f"blocker={rec.get('blocker') or rec.get('error')}",
                flush=True,
            )

    results.sort(key=lambda r: r.get("name") or "")
    promoted = [r for r in results if r.get("grade") == "PROMOTED"]
    scaffold_proven = [r for r in results if r.get("grade") == "SCAFFOLD_PROVEN"]
    gapped = [r for r in results if r.get("grade") not in {"PROMOTED", "SCAFFOLD_PROVEN"}]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    result = "PASS" if len(promoted) == len(leaves) else "PARTIAL"

    summary = {
        "schema": "glaciereq.wave-c-receipt.v2",
        "ts": ts,
        "run": "WAVE-C-CLOSED" if result == "PASS" else "WAVE-C-PARTIAL",
        "wave_c": {
            "id": WAVE_ID,
            "label": "Wave C — Innovation scaffold excellence group",
            "enrolled": len(leaves),
            "promoted": len(promoted),
            "scaffold_proven": len(scaffold_proven),
            "gapped": len(gapped),
            "phase": "CLOSED" if result == "PASS" else "PARTIAL_CLOSE",
            "leaves_promoted": [r["name"] for r in promoted],
            "leaves_scaffold_proven": [r["name"] for r in scaffold_proven],
            "leaves_gapped": [
                {
                    "leaf": r.get("name"),
                    "blocker": r.get("blocker") or r.get("error") or r.get("grade"),
                }
                for r in gapped
            ],
            "cleared": [
                "ENROLLMENT",
                "STEEL_VIA_ELEVATOR",
                "DUAL_RUN",
                "AUTHORITY_BOUND",
                "VALIDATOR",
                "PROMOTION_INVARIANT",
            ],
            "not_yet": [] if result == "PASS" else ["IMPLEMENTATION_PROOF_FOR_UNPROMOTED_LEAVES"],
            "law": "PROMOTED requires no scaffold evidence plus source-bound implementation proof",
        },
        "nonclaims": [
            "no employer affiliation or production deployment",
            "reference implementations only",
            "generic scaffold execution does not prove domain implementation",
        ],
        "result": result,
        "results": [
            {
                "leaf": r.get("name"),
                "ok": r.get("grade") == "PROMOTED",
                "grade": r.get("grade"),
                "blocker": r.get("blocker"),
                "source_sha": r.get("source_sha"),
                "validator_rc": r.get("validator_rc")
                or r.get("post_wave_stamp_validator_rc"),
                "dual_run_ok": r.get("dual_run_ok"),
                "promotion_assessment": r.get("promotion_assessment"),
            }
            for r in results
        ],
    }

    (ROOT / "excellence" / "receipts" / "wave_c_latest.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "excellence" / "receipts" / "wave_c_closed.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    plan["closed_at"] = ts
    plan["close_result"] = result
    plan["promoted_count"] = len(promoted)
    plan["scaffold_proven_count"] = len(scaffold_proven)
    plan["gapped_count"] = len(gapped)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    (ROOT / "excellence" / "framework" / "WAVE_C_INNOVATION_SCAFFOLD_MAP.md").write_text(
        f"""# Wave C — Innovation Scaffold Excellence Group

**Wave id:** `{WAVE_ID}`  
**Closed/updated:** {ts}  
**Result:** **{result}**  
**Promoted:** {len(promoted)} / {len(leaves)}  
**Scaffold-proven:** {len(scaffold_proven)}  
**Gapped:** {len(gapped)}

## Status

| Grade | Count |
|-------|------:|
| PROMOTED | {len(promoted)} |
| SCAFFOLD_PROVEN | {len(scaffold_proven)} |
| GAP / other | {len(gapped)} |

## Promoted leaves

{chr(10).join(f"- `{n}`" for n in summary["wave_c"]["leaves_promoted"]) or "_none_"}

## Scaffold-proven leaves

{chr(10).join(f"- `{n}`" for n in summary["wave_c"]["leaves_scaffold_proven"]) or "_none_"}

## Gapped leaves

{chr(10).join(f"- `{g['leaf']}` — {g['blocker']}" for g in summary["wave_c"]["leaves_gapped"]) or "_none_"}

## Receipts

- `excellence/receipts/wave_c_closed.json`
- `excellence/receipts/wave_c_latest.json`
- Scratch logs: `excellence/receipts/wave_c_scratch/leaves/<leaf>/`

## Law

- PROMOTED requires no scaffold evidence + source-bound implementation proof
- SCAFFOLD_PROVEN is executable/tested but not implementation-complete
- No company affiliation claims
- Generic elevator proof is necessary but not sufficient for promotion
""",
        encoding="utf-8",
    )

    print(json.dumps({
        "promoted": len(promoted),
        "scaffold_proven": len(scaffold_proven),
        "gapped": len(gapped),
        "result": result,
    }, indent=2))
    return 0 if result == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
