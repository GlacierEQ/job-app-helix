#!/usr/bin/env python3
"""Capture a deterministic GlacierEQ trajectory checkpoint.

The capture records authenticated owned-repository inventory and exact default-branch
heads from GitHub plus content hashes for the Helix authority surfaces that encode the
other trajectory dimensions. Historical reconstruction is deliberately separate from
contemporary capture: this tool never pretends current GitHub state existed in the past.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_PATH = ROOT / "machine" / "trajectory" / "2026_schedule.json"
HST = ZoneInfo("Pacific/Honolulu")
GRAPHQL_URL = "https://api.github.com/graphql"

DIMENSION_SCOPES: dict[str, tuple[str, ...]] = {
    "genealogy": ("manifests", "schemas/estate"),
    "capability_ontology": ("manifests", "excellence"),
    "original_intent": ("README.md", "docs", "strategy.md", "goals.md"),
    "development_target": ("machine/target-contract.json", "strategy.md", "goals.md"),
    "implementation": ("src", "helix", "scripts"),
    "verification": ("tests", "receipts", "audits", "ci_audit_portfolio.py"),
    "deployment_public_projection": ("site", "showcase", "vercel.json", ".github/workflows/pages.yml"),
    "job_application_evolution": ("hire_package", "docs", "status"),
    "company_coverage": ("manifests", "status"),
    "company_specific_inventions": ("excellence", "showcase", "observations"),
    "control_plane_topology": (".github/workflows", "schemas", "manifests"),
    "receipts": ("receipts",),
    "blockers": ("status", "audits"),
    "experiments": ("observations",),
}


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def scheduled_entry(schedule: dict, date_text: str) -> tuple[int, dict]:
    for index, entry in enumerate(schedule["checkpoints"]):
        if entry["date"] == date_text:
            return index, entry
    raise SystemExit(f"{date_text} is not a canonical 2026 trajectory checkpoint")


def files_for_scope(scope: tuple[str, ...]) -> list[Path]:
    found: set[Path] = set()
    for relative in scope:
        candidate = ROOT / relative
        if candidate.is_file():
            found.add(candidate)
        elif candidate.is_dir():
            for path in candidate.rglob("*"):
                if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                    found.add(path)
    return sorted(found, key=lambda p: p.relative_to(ROOT).as_posix())


def scope_state(scope: tuple[str, ...], global_hashes: dict[str, str]) -> dict:
    rows = []
    for path in files_for_scope(scope):
        rel = path.relative_to(ROOT).as_posix()
        digest = sha256_file(path)
        global_hashes[rel] = digest
        rows.append({"path": rel, "sha256": digest, "bytes": path.stat().st_size})
    tree_payload = [{"path": row["path"], "sha256": row["sha256"]} for row in rows]
    return {
        "sources": list(scope),
        "file_count": len(rows),
        "tree_sha256": sha256_bytes(canonical_json(tree_payload)),
    }


def graphql(token: str, query: str, variables: dict) -> dict:
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=canonical_json({"query": query, "variables": variables}),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "GlacierEQ-Trajectory-Lattice/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub GraphQL HTTP {exc.code}: {body[:500]}") from exc
    if payload.get("errors"):
        raise SystemExit(f"GitHub GraphQL error: {payload['errors']}")
    return payload["data"]


def fetch_owned_repositories(token: str, owner: str) -> list[dict]:
    query = """
    query($owner: String!, $cursor: String) {
      user(login: $owner) {
        repositories(
          first: 100,
          after: $cursor,
          ownerAffiliations: OWNER,
          orderBy: {field: NAME, direction: ASC}
        ) {
          pageInfo { hasNextPage endCursor }
          nodes {
            nameWithOwner
            visibility
            isArchived
            isFork
            createdAt
            updatedAt
            defaultBranchRef {
              name
              target { ... on Commit { oid committedDate } }
            }
          }
        }
      }
    }
    """
    cursor = None
    repositories: list[dict] = []
    while True:
        data = graphql(token, query, {"owner": owner, "cursor": cursor})
        user = data.get("user")
        if user is None:
            raise SystemExit(f"GitHub owner not visible to token: {owner}")
        connection = user["repositories"]
        repositories.extend(connection["nodes"])
        if not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]
    return repositories


def repository_state(repositories: list[dict]) -> tuple[dict, list[dict]]:
    visibility: dict[str, int] = {}
    archived = 0
    forks = 0
    heads: list[dict] = []
    for repo in repositories:
        vis = repo["visibility"].lower()
        visibility[vis] = visibility.get(vis, 0) + 1
        archived += int(repo["isArchived"])
        forks += int(repo["isFork"])
        branch = repo.get("defaultBranchRef")
        heads.append(
            {
                "repository": repo["nameWithOwner"],
                "default_branch": branch["name"] if branch else None,
                "head_sha": branch["target"]["oid"] if branch and branch.get("target") else None,
                "head_committed_at": branch["target"].get("committedDate") if branch and branch.get("target") else None,
                "visibility": vis,
                "archived": bool(repo["isArchived"]),
                "fork": bool(repo["isFork"]),
                "created_at": repo["createdAt"],
                "updated_at": repo["updatedAt"],
            }
        )
    heads.sort(key=lambda row: row["repository"].lower())
    inventory = {
        "owned_repository_count": len(repositories),
        "visibility_counts": dict(sorted(visibility.items())),
        "archived_count": archived,
        "active_count": len(repositories) - archived,
        "fork_count": forks,
        "native_count": len(repositories) - forks,
    }
    return inventory, heads


def compute_delta(current: dict, previous: dict | None, previous_expected: str | None) -> dict:
    if previous is None:
        return {
            "status": "previous_checkpoint_not_materialized",
            "previous_checkpoint_expected": previous_expected,
            "previous_checkpoint": None,
            "repository_count_delta": None,
            "repositories_added": [],
            "repositories_removed": [],
            "canonical_head_changes": [],
            "dimension_changes": [],
        }

    current_heads = {row["repository"]: row["head_sha"] for row in current["state"]["canonical_heads"]}
    previous_heads = {row["repository"]: row["head_sha"] for row in previous["state"]["canonical_heads"]}
    current_names = set(current_heads)
    previous_names = set(previous_heads)
    head_changes = [
        {"repository": name, "before": previous_heads[name], "after": current_heads[name]}
        for name in sorted(current_names & previous_names)
        if current_heads[name] != previous_heads[name]
    ]
    current_dimensions = current["state"]["dimensions"]
    previous_dimensions = previous["state"]["dimensions"]
    dimension_changes = [
        name
        for name in sorted(set(current_dimensions) | set(previous_dimensions))
        if current_dimensions.get(name, {}).get("tree_sha256")
        != previous_dimensions.get(name, {}).get("tree_sha256")
    ]
    return {
        "status": "computed",
        "previous_checkpoint_expected": previous_expected,
        "previous_checkpoint": previous.get("date"),
        "repository_count_delta": current["state"]["repository_inventory"]["owned_repository_count"]
        - previous["state"]["repository_inventory"]["owned_repository_count"],
        "repositories_added": sorted(current_names - previous_names),
        "repositories_removed": sorted(previous_names - current_names),
        "canonical_head_changes": head_changes,
        "dimension_changes": dimension_changes,
    }


def build_checkpoint(date_text: str, token: str, owner: str, previous: dict | None) -> dict:
    schedule = read_json(SCHEDULE_PATH)
    index, entry = scheduled_entry(schedule, date_text)
    now_hst = datetime.now(HST)
    today_hst = now_hst.date().isoformat()
    if entry["capture_kind"] == "contemporary" and today_hst != date_text:
        raise SystemExit(
            f"contemporary checkpoint {date_text} must be captured on that HST date; current HST date is {today_hst}"
        )
    if entry["capture_kind"] == "historical_reconstruction":
        raise SystemExit(
            "historical checkpoints require the reconstruction pipeline; current-state capture cannot be backdated"
        )

    repositories = fetch_owned_repositories(token, owner)
    inventory, heads = repository_state(repositories)
    source_hashes: dict[str, str] = {}
    dimensions = {
        name: scope_state(scope, source_hashes)
        for name, scope in DIMENSION_SCOPES.items()
    }
    schedule_sha = sha256_file(SCHEDULE_PATH)
    source_hashes[SCHEDULE_PATH.relative_to(ROOT).as_posix()] = schedule_sha
    previous_expected = schedule["checkpoints"][index - 1]["date"] if index else None

    checkpoint = {
        "schema": "glaciereq.trajectory-checkpoint.v1",
        "date": date_text,
        "timezone": schedule["timezone"],
        "captured_at_hst": now_hst.isoformat(timespec="seconds"),
        "capture_kind": entry["capture_kind"],
        "phase": entry["phase"],
        "resolution": entry["resolution"],
        "authority": {
            "repository": schedule["authority"]["repository"],
            "schedule_path": schedule["authority"]["path"],
            "schedule_sha256": schedule_sha,
            "github_owner": owner,
        },
        "state": {
            "repository_inventory": inventory,
            "canonical_heads": heads,
            "dimensions": dimensions,
            "source_hashes": dict(sorted(source_hashes.items())),
        },
        "delta": {},
    }
    checkpoint["delta"] = compute_delta(checkpoint, previous, previous_expected)
    body_without_receipt = canonical_json(checkpoint)
    checkpoint["receipt"] = {
        "hash_algorithm": "sha256",
        "checkpoint_sha256": sha256_bytes(body_without_receipt),
    }
    return checkpoint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Canonical checkpoint date YYYY-MM-DD")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--owner", default="GlacierEQ")
    parser.add_argument("--token-env", default="GLACIEREQ_ESTATE_TOKEN")
    args = parser.parse_args()

    token = os.environ.get(args.token_env, "").strip()
    if not token:
        raise SystemExit(f"required private-estate authority token missing: {args.token_env}")
    previous = read_json(args.previous) if args.previous and args.previous.exists() else None
    checkpoint = build_checkpoint(args.date, token, args.owner, previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"checkpoint_sha256={checkpoint['receipt']['checkpoint_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
