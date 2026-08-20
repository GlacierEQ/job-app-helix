#!/usr/bin/env python3
"""Audit live GitHub state against Helix portfolio declarations.

This is a read-only freshness layer, not a source-of-truth replacement. It
compares reference Helix declarations with observable GitHub metadata and the
current live-evidence registry, then emits a deterministic-shape receipt.

A repository-scoped Actions token cannot inspect sibling private repositories.
A 404 is therefore represented as UNOBSERVABLE unless Helix declares the
repository public. No private-state inference is made from a scoped 404.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone
UTC = timezone.utc
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RECRUITER_ELIGIBLE_STATES = {"PROMOTED", "REFERENCE_ONLY"}
PUBLIC_FLAGSHIP_SURFACES = {"PUBLIC", "PUBLIC_RECRUITER", "PUBLIC_PROMOTED"}
RETRYABLE_HTTP = {403, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
MAX_BACKOFF_SECONDS = 20.0


class AuditError(RuntimeError):
    """Raised when the audit itself cannot be trusted."""


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"missing required file: {display_path(path)}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid JSON in {display_path(path)}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"expected JSON object: {display_path(path)}")
    return value


def reference_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(reference_bytes(value)).hexdigest()


def parse_repository_identifier(repository: str) -> tuple[str, str]:
    parts = repository.split("/")
    if len(parts) != 2 or not all(parts):
        raise AuditError(
            "invalid repository identifier; expected owner/name: "
            f"{repository!r}"
        )
    return parts[0], parts[1]


def repository_api_path(repository: str) -> str:
    owner, name = parse_repository_identifier(repository)
    return f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}"


def commit_api_path(repository: str, branch: str) -> str:
    return (
        f"{repository_api_path(repository)}/commits/"
        f"{quote(branch, safe='')}"
    )


def normalize_company(
    shard: dict[str, Any],
    company: dict[str, Any],
) -> dict[str, Any]:
    defaults = shard.get("defaults", {})
    if not isinstance(defaults, dict):
        raise AuditError(
            f"{shard.get('group_id')}: defaults must be an object"
        )
    merged = dict(defaults)
    merged.update(company)
    return merged


def recruiter_eligible(level: str, state: str, visibility: str) -> bool:
    return (
        visibility == "public"
        and level != "L0"
        and state in RECRUITER_ELIGIBLE_STATES
    )


def compile_portfolio() -> dict[str, Any]:
    inventory = load_json(ROOT / "manifests" / "portfolio_repositories.json")
    workspace = inventory.get("workspace_repositories", [])
    if not isinstance(workspace, list) or not all(
        isinstance(value, str) and value for value in workspace
    ):
        raise AuditError(
            "portfolio_repositories.json has invalid workspace_repositories"
        )
    inventory_repositories = {f"GlacierEQ/{name}" for name in workspace}

    companies_index = load_json(ROOT / "manifests" / "company_dossiers.json")
    dossier_files = companies_index.get("dossier_files", [])
    if not isinstance(dossier_files, list) or not dossier_files:
        raise AuditError("company_dossiers.json has no dossier_files")

    declarations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    company_ids: set[str] = set()
    for relative in dossier_files:
        shard = load_json(ROOT / relative)
        companies = shard.get("companies", [])
        if not isinstance(companies, list):
            raise AuditError(f"{relative}: companies must be a list")
        for raw_company in companies:
            if not isinstance(raw_company, dict):
                raise AuditError(f"{relative}: company row must be an object")
            company = normalize_company(shard, raw_company)
            company_id = company.get("company_id")
            if not isinstance(company_id, str) or not company_id:
                raise AuditError(f"{relative}: company_id is required")
            company_ids.add(company_id)
            rows = company.get("repositories", [])
            if not isinstance(rows, list):
                raise AuditError(f"{company_id}: repositories must be a list")
            for row in rows:
                if not isinstance(row, list) or len(row) != 6:
                    raise AuditError(
                        f"{company_id}: invalid repository row {row!r}"
                    )
                (
                    repository,
                    level,
                    promotion_state,
                    visibility,
                    inventory_scope,
                    provenance,
                ) = row
                repository = str(repository)
                parse_repository_identifier(repository)
                declarations[repository].append(
                    {
                        "company_id": company_id,
                        "level": level,
                        "promotion_state": promotion_state,
                        "visibility": visibility,
                        "inventory_scope": inventory_scope,
                        "provenance_state": provenance,
                    }
                )

    flagship_doc = load_json(ROOT / "manifests" / "flagship_registry.json")
    flagships = flagship_doc.get("flagships", [])
    if not isinstance(flagships, list):
        raise AuditError("flagship_registry.json: flagships must be a list")

    evidence_doc = load_json(
        ROOT / "manifests" / "live_repository_evidence.json"
    )
    evidence_rows = evidence_doc.get("repositories", [])
    if not isinstance(evidence_rows, list):
        raise AuditError(
            "live_repository_evidence.json: repositories must be a list"
        )
    evidence_by_repository = {
        row["repository"]: row
        for row in evidence_rows
        if isinstance(row, dict) and isinstance(row.get("repository"), str)
    }

    external_doc = load_json(
        ROOT / "manifests" / "flagship_external_repositories.json"
    )
    external_repositories = external_doc.get(
        "verified_owner_estate_external_repositories",
        [],
    )
    if not isinstance(external_repositories, list):
        raise AuditError(
            "flagship_external_repositories.json has invalid repository list"
        )

    all_repositories = (
        set(declarations)
        | inventory_repositories
        | {str(value) for value in external_repositories}
    )
    all_repositories.update(
        row["repository"]
        for row in flagships
        if isinstance(row, dict) and isinstance(row.get("repository"), str)
    )
    for repository in all_repositories:
        parse_repository_identifier(repository)

    return {
        "inventory_total": inventory.get("total_repositories"),
        "inventory_repositories": inventory_repositories,
        "declarations": dict(declarations),
        "company_ids": company_ids,
        "flagships": flagships,
        "evidence_by_repository": evidence_by_repository,
        "all_repositories": sorted(all_repositories),
    }


def retry_delay(exc: HTTPError, attempt: int) -> float:
    retry_after = exc.headers.get("Retry-After")
    if retry_after:
        try:
            return min(MAX_BACKOFF_SECONDS, max(0.0, float(retry_after)))
        except ValueError:
            try:
                retry_time = parsedate_to_datetime(retry_after)
                delay = retry_time.timestamp() - time.time()
                return min(MAX_BACKOFF_SECONDS, max(0.0, delay))
            except (TypeError, ValueError, OverflowError):
                pass

    reset = exc.headers.get("X-RateLimit-Reset")
    if reset:
        try:
            delay = float(reset) - time.time()
            return min(MAX_BACKOFF_SECONDS, max(0.0, delay))
        except ValueError:
            pass

    return min(MAX_BACKOFF_SECONDS, float(2 ** (attempt - 1)))


def github_getter(token: str) -> Callable[[str], dict[str, Any]]:
    if not token:
        raise AuditError(
            "live audit requires GITHUB_TOKEN; use --fixture offline"
        )

    def get(path: str) -> dict[str, Any]:
        if not path.startswith("/repos/GlacierEQ/"):
            raise AuditError(f"disallowed GitHub API path: {path!r}")
        request = Request(
            f"https://api.github.com{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "GlacierEQ-Portfolio-Freshness-Audit/1.0",
            },
        )
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with urlopen(request, timeout=15) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise AuditError(
                        f"GitHub API returned non-object for {path}"
                    )
                return payload
            except HTTPError as exc:
                if exc.code == 404:
                    return {"_unobservable": True, "_http_status": 404}
                if exc.code in RETRYABLE_HTTP and attempt < MAX_ATTEMPTS:
                    time.sleep(retry_delay(exc, attempt))
                    continue
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                raise AuditError(
                    f"GitHub API {exc.code} for {path}: {detail}"
                ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt < MAX_ATTEMPTS:
                    time.sleep(min(MAX_BACKOFF_SECONDS, float(2 ** (attempt - 1))))
                    continue
                raise AuditError(
                    f"GitHub API transport failure for {path}: {exc}"
                ) from exc
            except json.JSONDecodeError as exc:
                raise AuditError(
                    f"GitHub API returned invalid JSON for {path}"
                ) from exc
        raise AuditError(f"GitHub API retry loop exhausted for {path}")

    return get


def fixture_getter(path: Path) -> Callable[[str], dict[str, Any]]:
    fixture = load_json(path)
    repositories = fixture.get("repositories")
    if not isinstance(repositories, dict):
        raise AuditError("fixture must contain a repositories object")

    def get(api_path: str) -> dict[str, Any]:
        parts = api_path.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "repos":
            raise AuditError(f"unsupported fixture API path: {api_path}")
        repository = f"{parts[1]}/{parts[2]}"
        row = repositories.get(repository)
        if row == "UNOBSERVABLE":
            return {"_unobservable": True, "_http_status": 404}
        if not isinstance(row, dict):
            raise AuditError(f"fixture is missing {repository}")
        if len(parts) == 3:
            visibility = row.get(
                "visibility",
                "private" if row.get("private") else "public",
            )
            return {
                "full_name": repository,
                "private": visibility == "private",
                "visibility": visibility,
                "archived": bool(row.get("archived", False)),
                "fork": bool(row.get("fork", False)),
                "default_branch": row.get("default_branch", "main"),
                "html_url": row.get(
                    "html_url",
                    f"https://github.com/{repository}",
                ),
                "pushed_at": row.get("pushed_at"),
            }
        if len(parts) >= 5 and parts[3] == "commits":
            return {"sha": row.get("head_sha")}
        raise AuditError(f"unsupported fixture API path: {api_path}")

    return get


def finding(
    code: str,
    severity: str,
    repository: str | None,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if repository:
        value["repository"] = repository
    value.update(details)
    return value


def declared_visibility(
    declarations: dict[str, list[dict[str, Any]]],
    repository: str,
) -> set[str]:
    return {
        str(row.get("visibility"))
        for row in declarations.get(repository, [])
    }


def audit(
    get: Callable[[str], dict[str, Any]],
    observed_at: str,
) -> dict[str, Any]:
    portfolio = compile_portfolio()
    declarations: dict[str, list[dict[str, Any]]] = portfolio[
        "declarations"
    ]
    flagships: list[dict[str, Any]] = portfolio["flagships"]
    evidence_by_repository: dict[str, dict[str, Any]] = portfolio[
        "evidence_by_repository"
    ]
    inventory_repositories: set[str] = portfolio[
        "inventory_repositories"
    ]

    findings: list[dict[str, Any]] = []
    metadata: dict[str, dict[str, Any]] = {}

    for repository in portfolio["all_repositories"]:
        repo = get(repository_api_path(repository))
        if repo.get("_unobservable"):
            declared = declared_visibility(declarations, repository)
            metadata[repository] = {
                "observable": False,
                "visibility": None,
            }
            if "public" in declared:
                findings.append(
                    finding(
                        "DECLARED_PUBLIC_REPOSITORY_UNOBSERVABLE",
                        "ERROR",
                        repository,
                        "Declared public repository was not observable.",
                    )
                )
            else:
                findings.append(
                    finding(
                        "PRIVATE_OR_SCOPED_REPOSITORY_UNOBSERVABLE",
                        "INFO",
                        repository,
                        (
                            "Repository metadata is not visible to this token; "
                            "no private visibility inference was made."
                        ),
                    )
                )
            continue
        metadata[repository] = {
            "observable": True,
            "visibility": "private" if repo.get("private") else "public",
            "archived": bool(repo.get("archived")),
            "fork": bool(repo.get("fork")),
            "default_branch": repo.get("default_branch"),
            "html_url": repo.get("html_url"),
            "pushed_at": repo.get("pushed_at"),
        }

    for repository, rows in sorted(declarations.items()):
        visibilities = declared_visibility(declarations, repository)
        if len(visibilities) > 1:
            findings.append(
                finding(
                    "DECLARATION_VISIBILITY_CONFLICT",
                    "ERROR",
                    repository,
                    (
                        "Repository has conflicting visibility declarations "
                        "across company dossiers."
                    ),
                    declared=sorted(visibilities),
                    company_ids=sorted(
                        {str(row.get("company_id")) for row in rows}
                    ),
                )
            )
        actual = metadata.get(repository, {}).get("visibility")
        if actual:
            for declared in sorted(visibilities):
                if declared != actual:
                    findings.append(
                        finding(
                            "LIVE_VISIBILITY_MISMATCH",
                            "ERROR",
                            repository,
                            (
                                "Helix declared visibility does not match "
                                "current GitHub visibility."
                            ),
                            declared=declared,
                            actual=actual,
                        )
                    )
        if metadata.get(repository, {}).get("archived") and any(
            row.get("inventory_scope") == "HELIX_ADMITTED"
            for row in rows
        ):
            findings.append(
                finding(
                    "ADMITTED_REPOSITORY_ARCHIVED",
                    "WARNING",
                    repository,
                    "An admitted repository is currently archived on GitHub.",
                )
            )

    flagship_results: list[dict[str, Any]] = []
    for row in flagships:
        if not isinstance(row, dict):
            continue
        repository = row.get("repository")
        if not isinstance(repository, str):
            continue
        meta = metadata.get(repository, {})
        actual_visibility = meta.get("visibility")
        state = str(row.get("state"))
        public_surface = str(row.get("public_surface"))
        evidence = evidence_by_repository.get(repository)
        evidence_state = "MISSING"
        evidence_head = None
        current_head = None
        head_matches = None

        if evidence is not None:
            evidence_state = str(evidence.get("state", "UNKNOWN"))
            evidence_head = evidence.get("observed_head_sha")
            default_branch = meta.get("default_branch")
            if (
                meta.get("observable")
                and isinstance(default_branch, str)
                and default_branch
            ):
                head = get(commit_api_path(repository, default_branch))
                if not head.get("_unobservable"):
                    current_head = head.get("sha")
                    head_matches = bool(
                        isinstance(evidence_head, str)
                        and isinstance(current_head, str)
                        and evidence_head == current_head
                    )
                    if head_matches is False:
                        findings.append(
                            finding(
                                "STALE_FLAGSHIP_LIVE_EVIDENCE",
                                "ERROR",
                                repository,
                                (
                                    "Flagship live-evidence receipt is not "
                                    "bound to the current default-branch head."
                                ),
                                observed_head=evidence_head,
                                current_head=current_head,
                                state=state,
                            )
                        )

        if (
            state in RECRUITER_ELIGIBLE_STATES
            and actual_visibility == "public"
            and evidence is None
        ):
            findings.append(
                finding(
                    "MISSING_FLAGSHIP_LIVE_EVIDENCE",
                    "WARNING",
                    repository,
                    (
                        "Recruiter-eligible public flagship has no "
                        "live-evidence registry row."
                    ),
                    state=state,
                    public_surface=public_surface,
                )
            )

        if (
            public_surface in PUBLIC_FLAGSHIP_SURFACES
            and actual_visibility == "private"
        ):
            findings.append(
                finding(
                    "AMBIGUOUS_PUBLIC_SURFACE_PRIVATE_SOURCE",
                    "WARNING",
                    repository,
                    (
                        "Presentation visibility and source-repository "
                        "visibility are conflated for this flagship."
                    ),
                    public_surface=public_surface,
                    source_visibility=actual_visibility,
                )
            )

        flagship_results.append(
            {
                "system_id": row.get("system_id"),
                "repository": repository,
                "state": state,
                "presentation_surface": public_surface,
                "source_visibility": actual_visibility,
                "metadata_observable": bool(meta.get("observable")),
                "live_evidence_state": evidence_state,
                "evidence_head": evidence_head,
                "current_head": current_head,
                "head_matches": head_matches,
            }
        )

    recruiter_eligible_repositories = sorted(
        repository
        for repository, rows in declarations.items()
        if any(
            recruiter_eligible(
                str(row.get("level")),
                str(row.get("promotion_state")),
                str(row.get("visibility")),
            )
            for row in rows
        )
    )
    recruiter_missing_evidence = sorted(
        repository
        for repository in recruiter_eligible_repositories
        if repository not in evidence_by_repository
    )

    def count(code: str) -> int:
        return sum(row["code"] == code for row in findings)

    stale_count = count("STALE_FLAGSHIP_LIVE_EVIDENCE")
    missing_flagship_count = count("MISSING_FLAGSHIP_LIVE_EVIDENCE")
    visibility_mismatch_count = count("LIVE_VISIBILITY_MISMATCH")
    public_unobservable_count = count(
        "DECLARED_PUBLIC_REPOSITORY_UNOBSERVABLE"
    )

    result = {
        "schema": "glaciereq.portfolio-live-freshness-receipt.v1",
        "observed_at": observed_at,
        "authority": "GlacierEQ/job-app-helix",
        "scope": "LIVE_GITHUB_METADATA_AND_CURRENT_EVIDENCE_COVERAGE",
        "mutation": "NONE",
        "portfolio": {
            "inventory_total": portfolio["inventory_total"],
            "inventory_children": len(inventory_repositories),
            "company_tracks": len(portfolio["company_ids"]),
            "dossier_repositories": len(declarations),
            "owner_estate_repositories_audited": len(
                portfolio["all_repositories"]
            ),
            "flagships": len(flagships),
            "live_evidence_rows": len(evidence_by_repository),
            "recruiter_eligible_dossier_repositories": len(
                recruiter_eligible_repositories
            ),
            "recruiter_eligible_missing_live_evidence": len(
                recruiter_missing_evidence
            ),
        },
        "freshness": {
            "visibility_mismatches": visibility_mismatch_count,
            "declared_public_unobservable": public_unobservable_count,
            "stale_flagship_evidence": stale_count,
            "missing_flagship_live_evidence": missing_flagship_count,
            "ambiguous_public_surface_private_source": count(
                "AMBIGUOUS_PUBLIC_SURFACE_PRIVATE_SOURCE"
            ),
            "all_recruiter_eligible_have_live_evidence": (
                not recruiter_missing_evidence
            ),
            "all_flagship_evidence_current": (
                not stale_count and not missing_flagship_count
            ),
            "declared_visibility_matches_live": (
                not visibility_mismatch_count
                and not public_unobservable_count
            ),
        },
        "recruiter_eligible_missing_live_evidence": (
            recruiter_missing_evidence
        ),
        "flagships": flagship_results,
        "findings": sorted(
            findings,
            key=lambda row: (
                {"ERROR": 0, "WARNING": 1, "INFO": 2}.get(
                    row["severity"],
                    3,
                ),
                row["code"],
                row.get("repository", ""),
            ),
        ),
        "truth_boundary": (
            "This receipt verifies observable GitHub metadata and evidence "
            "freshness only. A scoped 404 is never treated as proof that a "
            "private repository is absent. The receipt does not prove "
            "authorship, runtime correctness, deployment, hardware behavior, "
            "employer affiliation, or business impact."
        ),
    }
    result["receipt_sha256"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Offline GitHub metadata fixture",
    )
    parser.add_argument("--write-receipt", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 2 when ERROR findings exist",
    )
    args = parser.parse_args()

    try:
        if args.fixture:
            get = fixture_getter(args.fixture)
            observed_at = "FIXTURE"
        else:
            token = os.environ.get(
                "PORTFOLIO_AUDIT_GITHUB_TOKEN"
            ) or os.environ.get("GITHUB_TOKEN", "")
            get = github_getter(token)
            observed_at = (
                datetime.now(UTC)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
        receipt = audit(get, observed_at)
    except (AuditError, OSError, ValueError) as exc:
        print(f"portfolio live freshness: FAIL: {exc}", file=sys.stderr)
        return 1

    if args.write_receipt:
        output = args.write_receipt
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(reference_bytes(receipt))
        print(f"wrote {display_path(output)}")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    if args.strict and any(
        row["severity"] == "ERROR" for row in receipt["findings"]
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
