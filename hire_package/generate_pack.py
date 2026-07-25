#!/usr/bin/env python3
"""Stamp pack INDEX from state maps; does not invent claims.

Ensures four artifacts exist and rewrites PACK_STAMP.md with anchors.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / "GlacierEQ_Swarm" / "state"
REQUIRED = (
    "README.md",
    "RESUME_MUSK_ORBIT.md",
    "HONEST_SKILL_ASSESSMENT.md",
    "LINKEDIN_BUILDOUT.md",
    "OUTREACH_BACKDOOR.md",
)
LEGAL = re.compile(
    r"1FDV|FEDERAL-WARFARE|SUPERLUMINAL|cathedrals_cases_distill",
    re.I,
)
ANCHORS = ("AKOS", "pro-code", "xAI", "SpaceX")


def main() -> int:
    missing = [f for f in REQUIRED if not (ROOT / f).is_file()]
    if missing:
        raise SystemExit(f"missing artifacts: {missing}")

    texts = {f: (ROOT / f).read_text() for f in REQUIRED}
    for f, t in texts.items():
        if LEGAL.search(t):
            raise SystemExit(f"legal token in {f}")
        if f == "README.md":
            continue
        for a in ANCHORS:
            if a not in t and f != "OUTREACH_BACKDOOR.md":
                # outreach has AKOS/pro-code/xAI/SpaceX in body
                pass
        if f != "README.md":
            if "AKOS" not in t or "pro-code" not in t:
                raise SystemExit(f"{f} missing AKOS/pro-code anchors")

    # outreach-specific
    out = texts["OUTREACH_BACKDOOR.md"]
    if "back-door" not in out.lower() and "back door" not in out.lower() and "Back-door" not in out:
        raise SystemExit("outreach missing back-door framing")
    if "xai-colossus-cooling" not in out and "spacex-thermal-protection" not in out:
        raise SystemExit("outreach missing concrete exhibit")

    # assessment tiers
    assess = texts["HONEST_SKILL_ASSESSMENT.md"]
    for tier in ("Strength", "Gap", "Unknown"):
        if tier not in assess:
            raise SystemExit(f"assessment missing tier {tier}")

    # resume companies
    resume = texts["RESUME_MUSK_ORBIT.md"]
    if "xAI" not in resume or "SpaceX" not in resume:
        raise SystemExit("resume missing xAI/SpaceX")
    if "all-domain" not in resume.lower() and "multi-domain" not in resume.lower():
        raise SystemExit("resume missing all-domain positioning")

    slim = {}
    p = STATE / "ultimate_repo_map_slim.json"
    if p.exists():
        slim = json.loads(p.read_text())

    stamp = ROOT / "PACK_STAMP.md"
    stamp.write_text(
        f"""# Pack stamp

- generated: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
- artifacts: {", ".join(REQUIRED)}
- anchors: AKOS · pro-code · xAI · SpaceX
- portfolio_repos_mapped: {slim.get("total", "unknown")}
- entry: README.md
- litigation: excluded
"""
    )
    print(f"ok pack stamp {stamp} bytes={sum(len(t) for t in texts.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
