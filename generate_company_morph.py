#!/usr/bin/env python3
"""
Automated Target Package Compiler (generate_company_morph.py).
Compiles orbit-specific hire packages based on docs/COMPANY_MORPH_MAP.json.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MORPH_MAP_FILE = ROOT / "docs" / "COMPANY_MORPH_MAP.json"
HIRE_PACKAGE_DIR = ROOT / "hire_package"

def load_morph_map() -> dict:
    if not MORPH_MAP_FILE.exists():
        print(f"Error: {MORPH_MAP_FILE} not found.")
        sys.exit(1)
    return json.loads(MORPH_MAP_FILE.read_text(encoding="utf-8"))

def generate_package(orbit_id: str, target_info: dict) -> Path:
    out_file = HIRE_PACKAGE_DIR / f"HIRE_PACKAGE_{orbit_id.upper()}.md"
    lead_repos = target_info.get("lead", [])
    gov_repos = target_info.get("governance", [])
    sup_repos = target_info.get("support", [])
    
    lead_links = [f"- [{r}](file://{ROOT / 'repos' / r})" for r in lead_repos]
    gov_links = [f"- [{r}](file://{ROOT / 'repos' / r})" for r in gov_repos]
    sup_links = [f"- [{r}](file://{ROOT / 'repos' / r})" for r in sup_repos]
    
    content = f"""# Executive Hire Package: {orbit_id.upper()} Target Orbit

> **Target Orbit**: `{orbit_id}`  
> **Positioning**: Multi-domain Special-Projects Systems Engineer  
> **Primary Exhibit Mode**: Measured Code & Live Observables (No Employment Fiction)

---

## 1. Core Lead Repositories
{chr(10).join(lead_links) if lead_links else "None"}

## 2. Governance & Kernel Engines
{chr(10).join(gov_links) if gov_links else "None"}

## 3. Supporting Infrastructure
{chr(10).join(sup_links) if sup_links else "None"}

---

## 4. Live Verification Command
Run the primary hero test harness to verify observables:
```bash
python3 {ROOT}/showcase/demo_15min_run.py
```
"""
    out_file.write_text(content, encoding="utf-8")
    print(f"Generated: {out_file}")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Compile company-specific hire packages.")
    parser.add_argument("--orbit", type=str, default="all", help="Target orbit: spacex_sp, xai_colossus, nvidia, anthropic, microsoft, notion_ops, grok_operator, or all")
    args = parser.parse_args()
    
    morph_data = load_morph_map()
    targets = morph_data.get("targets", {})
    
    if args.orbit == "all":
        for oid, info in targets.items():
            generate_package(oid, info)
    elif args.orbit in targets:
        generate_package(args.orbit, targets[args.orbit])
    else:
        print(f"Unknown orbit: {args.orbit}. Available: {list(targets.keys())}")
        sys.exit(1)

if __name__ == "__main__":
    main()
