#!/usr/bin/env python3
"""
Automated Executive DM Generator (generate_outreach_dms.py).
Generates concise 3-sentence exhibit-first DMs tailored to target orbits and contacts.
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGING_FILE = ROOT / "hire_package" / "OUTREACH_STAGING.md"

TEMPLATES = {
    "spacex_sp": {
        "draft_a": "Hi {name}, I noticed your work on Starship/thermal systems. I built a Starship PICA-X reentry thermal failure predictor (`spacex-thermal-protection`) with exact heat-flux degradation math and a 61-node APEX Highway mesh (`demo_heroes.sh` passes in 150ms). Would love to share the private repo exhibit if you're open to special-projects problem solvers."
    },
    "xai_colossus": {
        "draft_a": "Hi {name}, saw your focus on Colossus cluster scaling. I built `xai-colossus-cooling` (liquid thermal physics engine predicting margin & PUE 1.08 across 100k GPUs) coupled with NVLink GPU health telemetry. Happy to share a live 3-minute CLI demo if you're looking for systems/infra builders."
    },
    "nvidia": {
        "draft_a": "Hi {name}, following your work on GPU cluster telemetry. I built `nvidia-deep-reasoning` (health-gated token admittance & FLOP budgeting) integrated with NVLink ECC health monitoring. Would love to send over the technical exhibit if you're open to connecting."
    },
    "anthropic": {
        "draft_a": "Hi {name}, I built `anthropic-safety-monitor` (real-time agent action boundary governor) operating under an AKOS Double-Helix kernel. If you're exploring agent coordination and safety runtime infrastructure, I'd value sharing the exhibit."
    }
}

def generate_dm(orbit: str, contact: str) -> str:
    template_info = TEMPLATES.get(orbit, TEMPLATES["spacex_sp"])
    template = template_info["draft_a"]
    msg = template.format(name=contact)
    
    output = f"""## Outreach Draft: {contact} [{orbit.upper()}]

```text
{msg}
```
"""
    return output

def main():
    parser = argparse.ArgumentParser(description="Generate exhibit-first executive outreach DMs.")
    parser.add_argument("--orbit", type=str, default="spacex_sp", help="Target orbit: spacex_sp, xai_colossus, nvidia, anthropic")
    parser.add_argument("--contact", type=str, default="Engineering Leader", help="Contact name or title")
    args = parser.parse_args()
    
    dm_text = generate_dm(args.orbit, args.contact)
    
    existing = ""
    if STAGING_FILE.exists():
        existing = STAGING_FILE.read_text(encoding="utf-8")
        
    updated = existing + "\n" + dm_text if existing else "# Executive Outreach DM Staging\n\n" + dm_text
    STAGING_FILE.write_text(updated, encoding="utf-8")
    
    print(f"Generated outreach DM for {args.contact} ({args.orbit}) -> {STAGING_FILE}")
    print("\n--- DM TEXT ---")
    print(dm_text.strip())

if __name__ == "__main__":
    main()
