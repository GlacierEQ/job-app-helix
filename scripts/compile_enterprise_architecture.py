#!/usr/bin/env python3
"""
Enterprise Architecture Synthesizer
===================================
Reads the census and generates a massive, interconnected Mermaid.js
infrastructure graph showing how the flagships and constellations
wire together across the enterprise.
"""
import json
from pathlib import Path


def generate_mermaid(repos: list[dict]) -> str:
    lines = ["graph TD", "  %% Enterprise Architecture Graph"]
    
    # Domains
    clusters = {
        "xAI / Compute": [],
        "SpaceX / Orbital": [],
        "OpenAI / Inference": [],
        "Autonomous Vehicles": [],
        "Enterprise SaaS": [],
        "Defense / Assured": [],
        "Core Flagships": []
    }
    
    for r in repos:
        name = r["repository"].split("/")[-1].lower()
        if "spacex" in name:
            clusters["SpaceX / Orbital"].append(name)
        elif "xai" in name or "colossus" in name:
            clusters["xAI / Compute"].append(name)
        elif "openai" in name:
            clusters["OpenAI / Inference"].append(name)
        elif any(c in name for c in ["waymo", "zoox", "tesla"]):
            clusters["Autonomous Vehicles"].append(name)
        elif any(c in name for c in ["palantir", "databricks", "snowflake"]):
            clusters["Enterprise SaaS"].append(name)
        elif any(c in name for c in ["nasa", "lockheed", "anduril"]):
            clusters["Defense / Assured"].append(name)
        elif any(f in name for f in ["mastermind", "monolith", "genius", "nexus"]):
            clusters["Core Flagships"].append(name)

    # Output subgraphs
    for cluster_name, nodes in clusters.items():
        if not nodes:
            continue
        safe_cluster = cluster_name.replace(" / ", "_").replace(" ", "")
        lines.append(f"\n  subgraph {safe_cluster}[\"{cluster_name}\"]")
        for node in nodes[:20]:  # limit to 20 per cluster to avoid massive rendering issues
            lines.append(f"    {node}(\"{node}\")")
        lines.append("  end")

    # Wire them up with hypothetical connections
    lines.append("\n  %% Integration Lines")
    if clusters["Core Flagships"] and clusters["xAI / Compute"]:
        lines.append(f"  {clusters['Core Flagships'][0]} -->|Orchestrates| {clusters['xAI / Compute'][0]}")
    if clusters["xAI / Compute"] and clusters["OpenAI / Inference"]:
        lines.append(f"  {clusters['xAI / Compute'][0]} -->|Provides KV Cache| {clusters['OpenAI / Inference'][0]}")
    if clusters["SpaceX / Orbital"] and clusters["Core Flagships"]:
        lines.append(f"  {clusters['SpaceX / Orbital'][0]} -->|Telemetry Sink| {clusters['Core Flagships'][0]}")
    if clusters["Autonomous Vehicles"] and clusters["xAI / Compute"]:
        lines.append(f"  {clusters['Autonomous Vehicles'][0]} -->|Model Training| {clusters['xAI / Compute'][0]}")
    if clusters["Enterprise SaaS"] and clusters["Defense / Assured"]:
        lines.append(f"  {clusters['Enterprise SaaS'][0]} -->|Audit Lineage| {clusters['Defense / Assured'][0]}")

    return "\n".join(lines)


def main():
    census_path = Path("state/owned-library-census.json")
    if not census_path.exists():
        print("No census found!")
        return
        
    data = json.loads(census_path.read_text())
    repos = data.get("repositories", [])
    
    mermaid_code = generate_mermaid(repos)
    
    out_path = Path("artifacts/ENTERPRISE_ARCHITECTURE_MAP.md")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(f"# Global Enterprise Architecture\n\n```mermaid\n{mermaid_code}\n```\n")
    print(f"Architecture Map written to {out_path}")

if __name__ == "__main__":
    main()
