#!/usr/bin/env python3
"""
Enterprise Flagship CI Matrix
=============================
Queries the GitHub API to prove that our Ascended Flagships
have passing CI/CD (GitHub Actions). Generates an artifact
for the recruiter site.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path


def get_latest_workflow_status(repo_full_name: str, token: str) -> str:
    url = f"https://api.github.com/repos/{repo_full_name}/actions/runs?per_page=1"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Job-App-Helix-Matrix-Compiler"
    })
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            runs = data.get("workflow_runs", [])
            if not runs:
                return "NO_CI"
            status = runs[0].get("status")
            conclusion = runs[0].get("conclusion")
            if status == "in_progress" or status == "queued":
                return "RUNNING"
            return str(conclusion).upper()
    except urllib.error.URLError:
        return "ERROR"
    except Exception:
        return "UNKNOWN"

def main():
    token_path = Path("/root/.secrets/github_pat")
    if not token_path.exists():
        print("No github_pat found!")
        return
    token = token_path.read_text().strip()
    
    census_path = Path("state/owned-library-census.json")
    if not census_path.exists():
        print("No census found!")
        return
        
    data = json.loads(census_path.read_text())
    repos = data.get("repositories", [])
    
    # Filter to newly ascended domains (where name contains specific keywords or flagships)
    targets = []
    for r in repos:
        name = r.get("repository", "").lower()
        if "spacex" in name or "xai" in name or "openai" in name or "apex" in name or "nexus" in name or "colossus" in name:
            targets.append(r)
            
    # We don't want to rate limit ourselves, so just take top 30
    targets = targets[:30]
    
    print(f"Querying CI status for {len(targets)} flagships...")
    
    results = []
    for r in targets:
        full_name = r["repository"]
        status = get_latest_workflow_status(full_name, token)
        results.append({"repository": full_name, "ci_status": status})
        print(f"  {full_name} -> {status}")
        
    out_path = Path("artifacts/flagship-ci-matrix.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps({"schema": "glaciereq.ci-matrix.v1", "results": results}, indent=2))
    print(f"Matrix written to {out_path}")

if __name__ == "__main__":
    main()
