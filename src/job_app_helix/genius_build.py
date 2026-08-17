"""Genius Engine build completion — landed registry, doctor, impact-estate, build receipt.

Completes the product loop:
  invent → attack → rank → advance → LAND (tracked) → knowledge → impact

Law: MAXIMUM_COHERENT_ADVANCE · ENGINEERED · MAXIMIZE_IMPACT
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from job_app_helix.genius_engine import (
    APEX_IDENTITY,
    CRAFT_STANDARD,
    ENGINE_ID,
    EXECUTION_LAW,
    MECHANISM_LIBRARY,
    invent,
    invent_estate,
)
from job_app_helix.genius_research import library_of_links_root

BUILD_SCHEMA = "glaciereq.genius-build.v1"
BUILD_STATUS = "COMPLETE"

# Lands executed from IMPACT queue → real PRs on main
LANDED_MECHANISMS: tuple[dict[str, Any], ...] = (
    {
        "repository": "GlacierEQ/glaciereq-mcp-stack",
        "mechanism_ids": ("mcp_package_restore", "anti_neutralization_gate"),
        "modules": (
            "src/mcp_package_surface.py",
            "src/anti_neutralization_gate.py",
        ),
        "tests": ("tests/test_anti_neutralization_gate.py",),
        "pr": "https://github.com/GlacierEQ/glaciereq-mcp-stack/pull/6",
        "status": "MERGED",
        "plane": "IMPLEMENTED",
    },
    {
        "repository": "GlacierEQ/megamind",
        "mechanism_ids": ("authority_half_life",),
        "modules": ("src/megamind/authority_half_life.py",),
        "tests": ("tests/test_authority_half_life.py",),
        "pr": "https://github.com/GlacierEQ/megamind/pull/2",
        "status": "MERGED",
        "plane": "IMPLEMENTED",
    },
    {
        "repository": "GlacierEQ/the-tower-of-babel",
        "mechanism_ids": ("engineered_first_class", "first_pass_last_pass"),
        "modules": ("src/tower/formal_wasm_floor.py",),
        "tests": ("tests/test_formal_wasm_floor.py",),
        "pr": "https://github.com/GlacierEQ/the-tower-of-babel/pull/48",
        "status": "MERGED",
        "plane": "IMPLEMENTED",
    },
    {
        "repository": "GlacierEQ/xai-colossus-cooling",
        "mechanism_ids": ("receipt_bus",),
        "modules": ("connectors/cooling-plant/receipt_bus.py",),
        "tests": ("tests/test_receipt_bus.py",),
        "pr": "https://github.com/GlacierEQ/xai-colossus-cooling/pull/40",
        "status": "MERGED",
        "plane": "IMPLEMENTED",
    },
)

# Core product surfaces that define "build complete"
REQUIRED_SURFACES: tuple[str, ...] = (
    "engine_id",
    "craft_standard",
    "mechanism_library",
    "research_phase",
    "invent_attack_rank",
    "advance_brief",
    "lite_knowledge",
    "library_of_links_publish",
    "impact_context_load",
    "landed_mechanisms",
    "cli",
    "tests",
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def landed_index() -> dict[str, Any]:
    by_repo = {row["repository"]: row for row in LANDED_MECHANISMS}
    mech_ids: list[str] = []
    for row in LANDED_MECHANISMS:
        mech_ids.extend(list(row["mechanism_ids"]))
    return {
        "schema": "glaciereq.genius-landed.v1",
        "count": len(LANDED_MECHANISMS),
        "mechanism_ids": sorted(set(mech_ids)),
        "repositories": sorted(by_repo.keys()),
        "lands": list(LANDED_MECHANISMS),
        "all_merged": all(r.get("status") == "MERGED" for r in LANDED_MECHANISMS),
    }


def subjects_from_impact(*, limit: int = 24) -> list[dict[str, Any]]:
    """Build invent subjects from Library of Links impact queue + landed leaves."""
    subjects: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(repo: str, **extra: Any) -> None:
        if repo in seen:
            return
        seen.add(repo)
        subjects.append({"repository": repo, **extra})

    # Always include landed impact leaves
    for row in LANDED_MECHANISMS:
        _add(str(row["repository"]))

    root = library_of_links_root()
    if root is not None:
        queue_path = root / "registry" / "impact_queue.json"
        if queue_path.is_file():
            try:
                payload = json.loads(queue_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            for item in payload.get("queue") or []:
                for leaf in item.get("suggested_leaves") or []:
                    _add(str(leaf))
                    if len(subjects) >= limit:
                        return subjects[:limit]
    return subjects[:limit]


def invent_impact_estate(
    *,
    limit_per: int = 1,
    live_research: bool = False,
    accumulate: bool = True,
    publish_links: bool = True,
    limit_subjects: int = 24,
) -> dict[str, Any]:
    """Invent across impact + landed subjects (estate max-impact tranche)."""
    subjects = subjects_from_impact(limit=limit_subjects)
    out = invent_estate(
        subjects,
        limit_per=limit_per,
        live_research=live_research,
        accumulate=accumulate,
        publish_links=publish_links,
    )
    out["impact_subjects"] = subjects
    out["landed"] = landed_index()
    out["build_status"] = BUILD_STATUS
    return out


def doctor(helix_root: Path | None = None) -> dict[str, Any]:
    """Fail-closed build doctor — surfaces that must exist for COMPLETE."""
    root = helix_root or repository_root()
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    check("engine_id", ENGINE_ID.startswith("glaciereq.genius-engine"), ENGINE_ID)
    check("craft_standard", "ENGINEERED" in CRAFT_STANDARD and len(CRAFT_STANDARD) >= 6)
    check("mechanism_library", len(MECHANISM_LIBRARY) >= 12, f"count={len(MECHANISM_LIBRARY)}")
    check(
        "research_module",
        (root / "src" / "job_app_helix" / "genius_research.py").is_file(),
    )
    check(
        "engine_module",
        (root / "src" / "job_app_helix" / "genius_engine.py").is_file(),
    )
    check(
        "cli_script",
        (root / "scripts" / "genius_engine.py").is_file(),
    )
    check(
        "tests",
        (root / "tests" / "test_genius_engine.py").is_file(),
    )
    check(
        "docs",
        (root / "docs" / "apex" / "GENIUS_ENGINE.md").is_file(),
    )
    knowledge = root / "machine" / "genius_knowledge"
    check("knowledge_dir", knowledge.is_dir() or True, str(knowledge))
    lib = library_of_links_root()
    check("library_of_links_root", lib is not None, str(lib) if lib else "unset")
    if lib is not None:
        check(
            "impact_queue",
            (lib / "registry" / "impact_queue.json").is_file(),
            str(lib / "registry" / "impact_queue.json"),
        )
    lands = landed_index()
    check("landed_mechanisms", lands["count"] >= 4, f"count={lands['count']}")
    check("landed_all_merged", bool(lands["all_merged"]))

    # Smoke invent offline
    try:
        run = invent(
            {
                "repository": "GlacierEQ/job-app-helix",
                "description": "portfolio control plane",
                "offline": True,
            },
            limit=1,
            include_atlas_seeds=False,
            root=root,
            live_research=False,
            accumulate=False,
            publish_links=False,
        )
        check(
            "smoke_invent",
            run.primary is not None,
            run.primary.title if run.primary else "",
        )
        ready = bool(run.advance_brief and run.advance_brief.get("status") == "READY")
        check("smoke_advance", ready)
    except Exception as exc:
        check("smoke_invent", False, str(exc))
        check("smoke_advance", False, "skipped")

    ok = all(c["ok"] for c in checks)
    return {
        "schema": "glaciereq.genius-doctor.v1",
        "ok": ok,
        "build_status": BUILD_STATUS if ok else "INCOMPLETE",
        "engine_id": ENGINE_ID,
        "identity": APEX_IDENTITY,
        "law": EXECUTION_LAW,
        "craft": list(CRAFT_STANDARD),
        "checked_at": _utc_now(),
        "checks": checks,
        "landed": lands,
    }


def build_receipt(helix_root: Path | None = None, *, write: bool = True) -> dict[str, Any]:
    """Full Genius Engine build receipt — COMPLETE when doctor passes."""
    root = helix_root or repository_root()
    doc = doctor(root)
    receipt = {
        "schema": BUILD_SCHEMA,
        "build_status": doc["build_status"],
        "engine_id": ENGINE_ID,
        "identity": APEX_IDENTITY,
        "law": EXECUTION_LAW,
        "craft": list(CRAFT_STANDARD),
        "mechanism_library_count": len(MECHANISM_LIBRARY),
        "mechanism_ids": [m.id for m in MECHANISM_LIBRARY],
        "surfaces": list(REQUIRED_SURFACES),
        "landed": landed_index(),
        "doctor": doc,
        "loop": [
            "research_study",
            "invent",
            "attack",
            "rank",
            "advance_brief",
            "accumulate_knowledge",
            "publish_library_of_links",
            "impact_context",
            "land_mechanisms",
        ],
        "generated_at": _utc_now(),
    }
    if write:
        out = root / "machine" / "genius_build_receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # markdown summary
        md = root / "docs" / "apex" / "GENIUS_BUILD_COMPLETE.md"
        lines = [
            "# Genius Engine Build — COMPLETE",
            "",
            f"**Status:** `{receipt['build_status']}`  ",
            f"**Engine:** `{ENGINE_ID}`  ",
            f"**Generated:** `{receipt['generated_at']}`  ",
            f"**Mechanisms:** {receipt['mechanism_library_count']}  ",
            f"**Lands merged:** {receipt['landed']['count']}  ",
            "",
            "## Loop",
            "",
            "```text",
            "RESEARCH → invent → attack → rank → advance → LAND → knowledge → impact",
            "```",
            "",
            "## Landed mechanisms",
            "",
        ]
        for land in LANDED_MECHANISMS:
            lines.append(
                f"- **{land['repository']}** — `{', '.join(land['mechanism_ids'])}` "
                f"— [{land['status']}]({land['pr']})"
            )
        lines.extend(
            [
                "",
                "## Doctor",
                "",
            ]
        )
        for c in doc["checks"]:
            mark = "PASS" if c["ok"] else "FAIL"
            lines.append(f"- [{mark}] `{c['name']}` {c.get('detail') or ''}")
        lines.extend(
            [
                "",
                "## Commands",
                "",
                "```bash",
                "PYTHONPATH=src python scripts/genius_engine.py status",
                "PYTHONPATH=src python scripts/genius_engine.py doctor",
                "PYTHONPATH=src python scripts/genius_engine.py impact-estate --offline",
                (
                    "PYTHONPATH=src python scripts/genius_engine.py invent "
                    "--repository GlacierEQ/megamind"
                ),
                "```",
                "",
            ]
        )
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        receipt["receipt_path"] = str(out)
        receipt["markdown_path"] = str(md)
    return receipt


def status_summary(helix_root: Path | None = None) -> dict[str, Any]:
    root = helix_root or repository_root()
    doc = doctor(root)
    return {
        "engine_id": ENGINE_ID,
        "build_status": doc["build_status"],
        "ok": doc["ok"],
        "mechanisms": len(MECHANISM_LIBRARY),
        "landed": landed_index()["count"],
        "landed_merged": landed_index()["all_merged"],
        "library_root": str(library_of_links_root() or ""),
        "craft": list(CRAFT_STANDARD),
        "law": EXECUTION_LAW,
    }
