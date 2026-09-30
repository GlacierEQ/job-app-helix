#!/usr/bin/env python3
"""Reconstruct a bounded historical GlacierEQ trajectory checkpoint.

This executor deliberately separates proof from inference. GitHub can prove the latest
commit on the current default-branch lineage at a historical cutoff for repositories
that still exist and remain visible to the authenticated owner token. It cannot prove
that current repository metadata was identical at that cutoff, and it cannot discover
repositories deleted before reconstruction. Those gaps are emitted as unresolved
rather than silently converted into history.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_PATH = ROOT / "machine" / "trajectory" / "2026_schedule.json"
HST = ZoneInfo("Pacific/Honolulu")
GRAPHQL_URL = "https://api.github.com/graphql"
API_ROOT = "https://api.github.com"
SOURCE_BOUND_OWNER = "GlacierEQ"
AUTHORITY_REPO = "GlacierEQ/job-app-helix"
CHECKPOINT_SCHEMA = "glaciereq.trajectory-checkpoint.v1"
HST_CLOCK_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$")

DIMENSION_SCOPES: dict[str, tuple[str, ...]] = {
    "genealogy": ("manifests", "schemas/estate"),
    "capability_ontology": ("manifests", "excellence"),
    "original_intent": ("README.md", "docs", "strategy.md", "goals.md"),
    "development_target": (
        "machine/target-contract.json",
        "strategy.md",
        "goals.md",
    ),
    "implementation": ("src", "helix", "scripts"),
    "verification": ("tests", "receipts", "audits", "ci_audit_portfolio.py"),
    "deployment_public_projection": (
        "site",
        "showcase",
        "vercel.json",
        ".github/workflows/pages.yml",
    ),
    "job_application_evolution": ("hire_package", "docs", "status"),
    "company_coverage": ("manifests", "status"),
    "company_specific_inventions": ("excellence", "showcase", "observations"),
    "control_plane_topology": (".github/workflows", "schemas", "manifests"),
    "receipts": ("receipts",),
    "blockers": ("status", "audits"),
    "experiments": ("observations",),
}


def reference_json(value: object) -> bytes:
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return text.encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GlacierEQ-Trajectory-Reconstruction/1.0",
    }


def request_json(
    url: str,
    token: str,
    *,
    data: bytes | None = None,
) -> dict:
    headers = api_headers(token)
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"GitHub API HTTP {exc.code} for {url}: {body[:600]}"
        ) from exc


def graphql(token: str, query: str, variables: dict) -> dict:
    payload = request_json(
        GRAPHQL_URL,
        token,
        data=reference_json({"query": query, "variables": variables}),
    )
    if payload.get("errors"):
        raise SystemExit(f"GitHub GraphQL error: {payload['errors']}")
    return payload["data"]


def scheduled_historical_entry(schedule: dict, date_text: str) -> tuple[int, dict]:
    for index, entry in enumerate(schedule["checkpoints"]):
        if entry["date"] != date_text:
            continue
        if entry["capture_kind"] != "historical_reconstruction":
            raise SystemExit(
                f"{date_text} is contemporary and cannot be reconstructed historically"
            )
        return index, entry
    raise SystemExit(f"{date_text} is not a reference 2026 trajectory checkpoint")


def cutoff_iso(date_text: str, clock_text: str) -> str:
    if not HST_CLOCK_RE.fullmatch(clock_text):
        raise SystemExit(
            "cutoff time must be exact HST wall time HH:MM:SS with no offset "
            "or fractional seconds"
        )
    clock = time.fromisoformat(clock_text)
    local = datetime.combine(
        datetime.fromisoformat(date_text).date(),
        clock,
        tzinfo=HST,
    )
    return local.isoformat(timespec="seconds")


def fetch_survivor_history(token: str, until_iso: str) -> list[dict]:
    query = """
    query($owner: String!, $cursor: String, $until: GitTimestamp!) {
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
              target {
                ... on Commit {
                  history(first: 1, until: $until) {
                    nodes { oid committedDate }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    cursor = None
    repositories: list[dict] = []
    while True:
        data = graphql(
            token,
            query,
            {
                "owner": SOURCE_BOUND_OWNER,
                "cursor": cursor,
                "until": until_iso,
            },
        )
        user = data.get("user")
        if user is None:
            raise SystemExit(
                f"GitHub owner not visible to token: {SOURCE_BOUND_OWNER}"
            )
        connection = user["repositories"]
        repositories.extend(connection["nodes"])
        if not connection["pageInfo"]["hasNextPage"]:
            break
        cursor = connection["pageInfo"]["endCursor"]
    return repositories


def created_on_or_before(created_at: str, cutoff: datetime) -> bool:
    return datetime.fromisoformat(created_at.replace("Z", "+00:00")) <= cutoff


def reconstruct_survivor_heads(
    repositories: list[dict],
    cutoff: datetime,
) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    not_yet_created: list[str] = []
    for repo in repositories:
        name = repo["nameWithOwner"]
        if not created_on_or_before(repo["createdAt"], cutoff):
            not_yet_created.append(name)
            continue
        branch = repo.get("defaultBranchRef")
        history_nodes = []
        if branch and branch.get("target"):
            history_nodes = branch["target"]["history"]["nodes"]
        historical = history_nodes[0] if history_nodes else None
        rows.append(
            {
                "repository": name,
                "default_branch": branch["name"] if branch else None,
                "head_sha": historical["oid"] if historical else None,
                "head_committed_at": (
                    historical["committedDate"] if historical else None
                ),
                "visibility": repo["visibility"].lower(),
                "archived": bool(repo["isArchived"]),
                "fork": bool(repo["isFork"]),
                "created_at": repo["createdAt"],
                "updated_at": repo["updatedAt"],
                "evidence_class": "bounded_current_default_branch_lineage",
                "branch_semantics": (
                    "current default-branch name; historical commit is exact on "
                    "that surviving lineage at or before cutoff"
                ),
                "metadata_semantics": (
                    "visibility/archive/fork/name reflect current survivor metadata, "
                    "not asserted historical metadata"
                ),
            }
        )
    rows.sort(key=lambda item: item["repository"].lower())
    not_yet_created.sort(key=str.lower)
    return rows, not_yet_created


def bounded_inventory(heads: list[dict]) -> dict:
    current_visibility: dict[str, int] = {}
    for row in heads:
        visibility = row["visibility"]
        current_visibility[visibility] = current_visibility.get(visibility, 0) + 1
    return {
        "owned_repository_count": None,
        "visibility_counts": dict(sorted(current_visibility.items())),
        "archived_count": None,
        "active_count": None,
        "fork_count": None,
        "native_count": None,
        "bounded_survivor_repository_count": len(heads),
        "inventory_semantics": "bounded_current_survivors_at_cutoff",
        "visibility_semantics": "current_visibility_of_surviving_repositories",
        "exact_historical_repository_count_known": False,
        "deleted_or_transferred_repository_gap_resolved": False,
    }


def authority_head(heads: list[dict]) -> str | None:
    for row in heads:
        if row["repository"] == AUTHORITY_REPO:
            return row["head_sha"]
    return None


def get_commit_tree_sha(token: str, commit_sha: str) -> str:
    owner, repo = AUTHORITY_REPO.split("/", 1)
    url = f"{API_ROOT}/repos/{owner}/{repo}/git/commits/{commit_sha}"
    payload = request_json(url, token)
    return payload["tree"]["sha"]


def get_recursive_tree(token: str, tree_sha: str) -> list[dict]:
    owner, repo = AUTHORITY_REPO.split("/", 1)
    encoded = urllib.parse.quote(tree_sha, safe="")
    url = f"{API_ROOT}/repos/{owner}/{repo}/git/trees/{encoded}?recursive=1"
    payload = request_json(url, token)
    if payload.get("truncated"):
        raise SystemExit("authority Git tree response was truncated; refusing partial hash")
    return payload["tree"]


def path_matches(path: str, source: str) -> bool:
    source = source.rstrip("/")
    return path == source or path.startswith(f"{source}/")


def selected_blob_rows(tree: list[dict]) -> list[dict]:
    sources = {source for scope in DIMENSION_SCOPES.values() for source in scope}
    rows = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item["path"]
        if any(path_matches(path, source) for source in sources):
            rows.append(item)
    return sorted(rows, key=lambda item: item["path"])


def get_blob_bytes(token: str, blob_sha: str) -> bytes:
    owner, repo = AUTHORITY_REPO.split("/", 1)
    encoded = urllib.parse.quote(blob_sha, safe="")
    url = f"{API_ROOT}/repos/{owner}/{repo}/git/blobs/{encoded}"
    payload = request_json(url, token)
    if payload.get("encoding") != "base64":
        raise SystemExit(f"unexpected blob encoding for {blob_sha}")
    return base64.b64decode(payload["content"], validate=False)


def reconstruct_dimensions(
    token: str,
    authority_commit: str,
) -> tuple[dict, dict[str, str]]:
    tree_sha = get_commit_tree_sha(token, authority_commit)
    tree = get_recursive_tree(token, tree_sha)
    rows = selected_blob_rows(tree)
    digest_by_blob: dict[str, str] = {}
    source_hashes: dict[str, str] = {}
    for row in rows:
        blob_sha = row["sha"]
        digest = digest_by_blob.get(blob_sha)
        if digest is None:
            digest = sha256_bytes(get_blob_bytes(token, blob_sha))
            digest_by_blob[blob_sha] = digest
        source_hashes[row["path"]] = digest

    dimensions: dict[str, dict] = {}
    for name, scope in DIMENSION_SCOPES.items():
        matching = [
            {"path": path, "sha256": digest}
            for path, digest in source_hashes.items()
            if any(path_matches(path, source) for source in scope)
        ]
        matching.sort(key=lambda item: item["path"])
        dimensions[name] = {
            "sources": list(scope),
            "file_count": len(matching),
            "tree_sha256": sha256_bytes(reference_json(matching)),
            "evidence_class": "exact_authority_git_tree_at_cutoff",
            "authority_commit": authority_commit,
            "authority_tree": tree_sha,
        }
    return dimensions, dict(sorted(source_hashes.items()))


def unresolved_dimensions() -> tuple[dict, dict[str, str]]:
    dimensions: dict[str, dict] = {}
    for name, scope in DIMENSION_SCOPES.items():
        unresolved = {
            "dimension": name,
            "status": "authority_not_yet_created_at_cutoff",
        }
        dimensions[name] = {
            "sources": list(scope),
            "file_count": 0,
            "tree_sha256": sha256_bytes(reference_json(unresolved)),
            "evidence_class": "unresolved_authority_not_yet_created",
            "authority_commit": None,
            "authority_tree": None,
        }
    return dimensions, {}


def dimension_delta(
    current_dimensions: dict,
    previous_dimensions: dict,
) -> tuple[list[str], list[dict]]:
    changes: list[str] = []
    transitions: list[dict] = []
    names = sorted(set(current_dimensions) | set(previous_dimensions))
    for name in names:
        current = current_dimensions.get(name, {})
        previous = previous_dimensions.get(name, {})
        current_class = current.get("evidence_class")
        previous_class = previous.get("evidence_class")
        if current_class != previous_class:
            transitions.append(
                {
                    "dimension": name,
                    "before": previous_class,
                    "after": current_class,
                }
            )
            continue
        if current_class != "exact_authority_git_tree_at_cutoff":
            continue
        if current.get("tree_sha256") != previous.get("tree_sha256"):
            changes.append(name)
    return changes, transitions


def checkpoint_receipt_payload(checkpoint: dict) -> dict:
    payload = dict(checkpoint)
    payload.pop("receipt", None)
    return payload


def validate_previous_checkpoint(
    previous: dict | None,
    previous_expected: str | None,
) -> None:
    if previous is None:
        return
    if previous_expected is None:
        raise SystemExit("first checkpoint cannot accept a previous checkpoint")
    if previous.get("schema") != CHECKPOINT_SCHEMA:
        raise SystemExit("previous checkpoint schema mismatch")
    if previous.get("date") != previous_expected:
        raise SystemExit(
            "previous checkpoint date mismatch: "
            f"expected={previous_expected} actual={previous.get('date')}"
        )
    receipt = previous.get("receipt")
    if not isinstance(receipt, dict) or receipt.get("hash_algorithm") != "sha256":
        raise SystemExit("previous checkpoint receipt missing or unsupported")
    claimed = receipt.get("checkpoint_sha256")
    calculated = sha256_bytes(reference_json(checkpoint_receipt_payload(previous)))
    if claimed != calculated:
        raise SystemExit("previous checkpoint receipt mismatch")
    state = previous.get("state")
    if not isinstance(state, dict):
        raise SystemExit("previous checkpoint state missing")
    if not isinstance(state.get("source_heads"), list):
        raise SystemExit("previous checkpoint source_heads missing")
    if not isinstance(state.get("dimensions"), dict):
        raise SystemExit("previous checkpoint dimensions missing")


def bounded_delta(
    current: dict,
    previous: dict | None,
    previous_expected: str | None,
) -> dict:
    validate_previous_checkpoint(previous, previous_expected)
    if previous is None:
        return {
            "status": "previous_checkpoint_not_materialized",
            "previous_checkpoint_expected": previous_expected,
            "previous_checkpoint": None,
            "repository_count_delta": None,
            "repositories_added": [],
            "repositories_removed": [],
            "source_head_changes": [],
            "dimension_changes": [],
            "dimension_evidence_transitions": [],
            "delta_semantics": "not_computed_without_previous_materialization",
        }

    current_heads = {
        row["repository"]: row["head_sha"]
        for row in current["state"]["source_heads"]
    }
    previous_heads = {
        row["repository"]: row["head_sha"]
        for row in previous["state"]["source_heads"]
    }
    common = set(current_heads) & set(previous_heads)
    changes = [
        {
            "repository": name,
            "before": previous_heads[name],
            "after": current_heads[name],
        }
        for name in sorted(common)
        if current_heads[name] != previous_heads[name]
    ]
    dimension_changes, evidence_transitions = dimension_delta(
        current["state"]["dimensions"],
        previous["state"]["dimensions"],
    )
    return {
        "status": "bounded_historical_reconstruction",
        "previous_checkpoint_expected": previous_expected,
        "previous_checkpoint": previous.get("date"),
        "repository_count_delta": None,
        "repositories_added": sorted(set(current_heads) - set(previous_heads)),
        "repositories_removed": sorted(set(previous_heads) - set(current_heads)),
        "source_head_changes": changes,
        "dimension_changes": dimension_changes,
        "dimension_evidence_transitions": evidence_transitions,
        "delta_semantics": (
            "repository set/head delta is bounded to repositories still visible to "
            "the authenticated owner; dimension changes require exact authority-tree "
            "evidence on both checkpoints, while evidence-class changes are separate"
        ),
    }


def build_checkpoint(
    date_text: str,
    token: str,
    previous: dict | None,
    clock_text: str,
) -> dict:
    schedule = read_json(SCHEDULE_PATH)
    index, entry = scheduled_historical_entry(schedule, date_text)
    cutoff_text = cutoff_iso(date_text, clock_text)
    cutoff = datetime.fromisoformat(cutoff_text)
    repositories = fetch_survivor_history(token, cutoff_text)
    heads, not_yet_created = reconstruct_survivor_heads(repositories, cutoff)
    inventory = bounded_inventory(heads)
    authority_commit = authority_head(heads)

    if authority_commit:
        authority_commit_status = "resolved"
        authority_tree_evidence_class = "exact_git_tree_at_cutoff"
        dimensions, source_hashes = reconstruct_dimensions(token, authority_commit)
    elif AUTHORITY_REPO in not_yet_created:
        authority_commit_status = "not_yet_created_at_cutoff"
        authority_tree_evidence_class = "unresolved_authority_not_yet_created"
        dimensions, source_hashes = unresolved_dimensions()
    else:
        raise SystemExit(
            f"{AUTHORITY_REPO} is neither a cutoff survivor nor a known post-cutoff "
            "repository; refusing to guess authority provenance"
        )

    previous_expected = schedule["checkpoints"][index - 1]["date"] if index else None
    validate_previous_checkpoint(previous, previous_expected)
    limitations = [
        "repositories deleted or transferred away before reconstruction may be "
        "absent from authenticated current-owner enumeration",
        "repository names and default-branch names are current survivor metadata "
        "and are not asserted to be historical names",
        "visibility, archive, and fork flags are current survivor metadata",
        "historical commit SHA is exact only on the surviving current "
        "default-branch lineage",
    ]
    if authority_commit_status == "not_yet_created_at_cutoff":
        limitations.append(
            "Helix did not yet exist at this cutoff; Helix-scoped dimensions remain "
            "explicitly unresolved pending corroboration from predecessor sources"
        )

    checkpoint = {
        "schema": CHECKPOINT_SCHEMA,
        "date": date_text,
        "timezone": schedule["timezone"],
        "captured_at_hst": datetime.now(HST).isoformat(timespec="seconds"),
        "capture_kind": "historical_reconstruction",
        "phase": entry["phase"],
        "resolution": entry["resolution"],
        "authority": {
            "repository": schedule["authority"]["repository"],
            "schedule_path": schedule["authority"]["path"],
            "schedule_sha256": hashlib.sha256(
                SCHEDULE_PATH.read_bytes()
            ).hexdigest(),
            "schedule_semantics": "current_reconstruction_contract_not_historical_state",
            "github_owner": SOURCE_BOUND_OWNER,
        },
        "state": {
            "repository_inventory": inventory,
            "source_heads": heads,
            "dimensions": dimensions,
            "source_hashes": source_hashes,
        },
        "delta": {},
        "reconstruction": {
            "cutoff_hst": cutoff_text,
            "cutoff_semantics": "end_of_checkpoint_date_hst_by_default",
            "estate_evidence_class": "bounded_current_survivors",
            "authority_tree_evidence_class": authority_tree_evidence_class,
            "authority_commit_status": authority_commit_status,
            "current_repository_count_observed": len(repositories),
            "survivors_created_by_cutoff": len(heads),
            "current_survivors_created_after_cutoff": not_yet_created,
            "limitations": limitations,
        },
    }
    checkpoint["delta"] = bounded_delta(
        checkpoint,
        previous,
        previous_expected,
    )
    checkpoint["receipt"] = {
        "hash_algorithm": "sha256",
        "checkpoint_sha256": sha256_bytes(reference_json(checkpoint)),
    }
    return checkpoint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--cutoff-time-hst", default="23:59:59")
    parser.add_argument("--token-env", default="GLACIEREQ_ESTATE_TOKEN")
    args = parser.parse_args()

    token = os.environ.get(args.token_env, "").strip()
    if not token:
        raise SystemExit(
            f"required private-estate authority token missing: {args.token_env}"
        )
    if args.previous and not args.previous.exists():
        raise SystemExit(f"previous checkpoint does not exist: {args.previous}")
    previous = read_json(args.previous) if args.previous else None
    checkpoint = build_checkpoint(
        args.date,
        token,
        previous,
        args.cutoff_time_hst,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    print(f"checkpoint_sha256={checkpoint['receipt']['checkpoint_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
