from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = "glaciereq.estate-compiler.v1"
PUBLIC_RECRUITER_STATES = {"PROMOTED", "REFERENCE_ONLY"}
PRIVATE_SURFACES = {
    "PRIVATE_UNTIL_SANITIZED",
    "SANITIZED_CARD_ONLY",
    "EXCLUDED",
    "EXCLUDED_UNTIL_FIXED",
    "PUBLIC_AFTER_FIX",
}
LEGAL_TOKENS = (
    "1fdv",
    "1fda",
    "family-court",
    "family_court",
    "litigation",
    "docket",
    "legal-doc",
    "legal_doc",
    "court-record",
    "court_record",
    "case-1fd",
    "case_1fd",
)
BACKUP_PREFIXES = ("z-backup-", "backup-", "z_backup_", "backup_")
BACKUP_SUFFIXES = ("-backup", "_backup", "__backup", "-bak", "_bak")
ARCHIVE_SUFFIXES = ("-archive", "_archive", "__archive", "-archived", "_archived")
CAPABILITY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("deterministic-orchestration", ("orchestrat", "coordinator", "control plane", "scheduler")),
    ("provenance-and-evidence", ("evidence", "provenance", "receipt", "authority")),
    ("memory-and-continuity", ("memory", "continuity", "identity")),
    ("mcp-and-tool-integration", ("mcp", "connector", "tool-state", "adapter")),
    ("distributed-state-and-recovery", ("distributed", "recovery", "restart", "idempot")),
    ("document-intelligence", ("document", "pdf", "ocr", "filing")),
    ("fail-closed-governance", ("fail-closed", "approval", "permission", "guard")),
    ("polyglot-systems", ("polyglot", "multi-language")),
    ("repository-intelligence", ("portfolio", "repository", "estate", "compiler")),
    ("browser-and-operator-control", ("browser", "operator")),
    ("accelerator-and-infrastructure", ("gpu", "cuda", "tpu", "accelerator", "infrastructure")),
    ("reasoning-and-agent-systems", ("reasoning", "agent", "model")),
)


class Namespace(StrEnum):
    ENGINEERING = "ENGINEERING"
    LEGAL_PRIVATE = "LEGAL_PRIVATE"
    FORK_REFERENCE = "FORK_REFERENCE"


class Relation(StrEnum):
    BACKUP_OF = "BACKUP_OF"
    ARCHIVE_OF = "ARCHIVE_OF"
    EXPLICIT_SUCCESSOR_OF = "EXPLICIT_SUCCESSOR_OF"
    EXPLICIT_PREDECESSOR_OF = "EXPLICIT_PREDECESSOR_OF"


class ExperimentStage(StrEnum):
    EXPERIMENT = "EXPERIMENT"
    DISTINCT_VALUE = "DISTINCT_VALUE"
    TESTED = "TESTED"
    SYSTEM_COMPONENT = "SYSTEM_COMPONENT"
    FLAGSHIP_DONOR = "FLAGSHIP_DONOR"


@dataclass(frozen=True)
class Repo:
    repository: str
    repository_id: int
    visibility: str
    default_branch: str
    archived: bool
    fork: bool
    classification: str

    @property
    def name(self) -> str:
        return self.repository.split("/", 1)[-1]


def _json_bytes(value: object) -> bytes:
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"{serialized}\n".encode()


def digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unnamed"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _refs(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} requires non-empty evidence_refs")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} evidence_refs must be non-empty strings")
    return tuple(value)


def load_census(payload: Mapping[str, Any]) -> tuple[Repo, ...]:
    if payload.get("state") != "VERIFIED_INVENTORY":
        raise ValueError("estate compiler requires a VERIFIED_INVENTORY census")
    rows = payload.get("repositories")
    if not isinstance(rows, list) or not rows:
        raise ValueError("census.repositories must be non-empty")

    repos: list[Repo] = []
    for index, row in enumerate(rows):
        raw = _mapping(row, f"census.repositories[{index}]")
        repository = raw.get("repository")
        repository_id = raw.get("repository_id")
        visibility = raw.get("visibility")
        default_branch = raw.get("default_branch")
        if not isinstance(repository, str) or "/" not in repository:
            raise ValueError(f"invalid repository at census.repositories[{index}]")
        if not isinstance(repository_id, int):
            raise ValueError(f"{repository}: repository_id must be an integer")
        if visibility not in {"public", "private", "internal"}:
            raise ValueError(f"{repository}: invalid visibility")
        if not isinstance(default_branch, str) or not default_branch:
            raise ValueError(f"{repository}: missing default_branch")
        repos.append(
            Repo(
                repository=repository,
                repository_id=repository_id,
                visibility=visibility,
                default_branch=default_branch,
                archived=bool(raw.get("archived")),
                fork=bool(raw.get("fork")),
                classification=str(raw.get("classification") or "UNCLASSIFIED"),
            )
        )

    names = {repo.repository for repo in repos}
    ids = {repo.repository_id for repo in repos}
    if len(names) != len(repos) or len(ids) != len(repos):
        raise ValueError("census contains duplicate repository identity")
    if payload.get("repository_count") != len(repos):
        raise ValueError("census repository_count drift")
    if payload.get("native_repository_count") != sum(not repo.fork for repo in repos):
        raise ValueError("census native_repository_count drift")
    if payload.get("fork_repository_count") != sum(repo.fork for repo in repos):
        raise ValueError("census fork_repository_count drift")
    return tuple(repos)


def _namespace_assertions(
    payload: Mapping[str, Any] | None,
) -> dict[str, tuple[Namespace, tuple[str, ...]]]:
    if not payload:
        return {}
    rows = payload.get("namespaces", [])
    if not isinstance(rows, list):
        raise ValueError("estate facts namespaces must be a list")

    result: dict[str, tuple[Namespace, tuple[str, ...]]] = {}
    for index, row in enumerate(rows):
        raw = _mapping(row, f"estate_facts.namespaces[{index}]")
        repository = raw.get("repository")
        try:
            declared = Namespace(str(raw.get("namespace")))
        except ValueError as exc:
            raise ValueError(f"invalid namespace assertion at row {index}") from exc
        if not isinstance(repository, str) or not repository:
            raise ValueError(f"namespace row {index} requires repository")
        if declared is Namespace.FORK_REFERENCE:
            raise ValueError("FORK_REFERENCE is derived from GitHub metadata")
        if repository in result:
            raise ValueError(f"duplicate namespace assertion: {repository}")
        result[repository] = declared, _refs(raw.get("evidence_refs"), f"namespace row {index}")
    return result


def _lineage_assertions(
    payload: Mapping[str, Any] | None,
) -> dict[str, tuple[Relation, str, tuple[str, ...]]]:
    if not payload:
        return {}
    rows = payload.get("relationships", [])
    if not isinstance(rows, list):
        raise ValueError("estate facts relationships must be a list")

    result: dict[str, tuple[Relation, str, tuple[str, ...]]] = {}
    for index, row in enumerate(rows):
        raw = _mapping(row, f"estate_facts.relationships[{index}]")
        repository = raw.get("repository")
        target = raw.get("target")
        try:
            relation = Relation(str(raw.get("relation")))
        except ValueError as exc:
            raise ValueError(f"invalid lineage relation at row {index}") from exc
        if not isinstance(repository, str) or not isinstance(target, str):
            raise ValueError(f"lineage row {index} requires repository and target")
        if repository in result:
            raise ValueError(f"duplicate lineage assertion: {repository}")
        refs = _refs(raw.get("evidence_refs"), f"lineage row {index}")
        result[repository] = relation, target, refs
    return result


def namespace(
    repo: Repo,
    assertions: Mapping[str, tuple[Namespace, tuple[str, ...]]] | None = None,
) -> Namespace:
    if repo.fork:
        return Namespace.FORK_REFERENCE
    if assertions and repo.repository in assertions:
        return assertions[repo.repository][0]
    lowered = repo.name.casefold()
    if repo.visibility != "public" and any(token in lowered for token in LEGAL_TOKENS):
        return Namespace.LEGAL_PRIVATE
    return Namespace.ENGINEERING


def lineage_key(name: str) -> str:
    value = name.casefold()
    for prefix in BACKUP_PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    for suffix in (*BACKUP_SUFFIXES, *ARCHIVE_SUFFIXES):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    return re.sub(r"[-_.]+", "-", value).strip("-")


def _system_id(repository: str) -> str:
    name = slug(repository.split("/", 1)[-1])
    fingerprint = hashlib.sha256(repository.encode()).hexdigest()[:8]
    return f"sys-{name}-{fingerprint}"


def _level(value: object) -> float:
    return float({"L0": 0, "L1": 20, "L2": 40, "L3": 60, "L4": 80, "L5": 100}.get(str(value), 0))


def _root_of(repository: str, parent: Mapping[str, str]) -> str:
    seen: set[str] = set()
    current = repository
    while current in parent:
        if current in seen:
            raise ValueError(f"lineage cycle detected at {current}")
        seen.add(current)
        current = parent[current]
    return current


def _flagship_for_members(
    members: Sequence[Repo],
    flagships: Mapping[str, Any] | None,
) -> dict[str, Any]:
    by_repository = {
        row.get("repository"): row
        for row in (flagships or {}).get("flagships", [])
        if isinstance(row, dict) and isinstance(row.get("repository"), str)
    }
    candidates = [
        by_repository[repo.repository]
        for repo in members
        if repo.repository in by_repository
    ]
    if not candidates:
        return {}
    return max(
        candidates,
        key=lambda row: (
            _level(row.get("level")),
            str(row.get("system_id") or ""),
        ),
    )


def build_systems(
    repos: Sequence[Repo],
    lineage_assertions: Mapping[str, tuple[Relation, str, tuple[str, ...]]],
    namespace_assertions: Mapping[str, tuple[Namespace, tuple[str, ...]]],
    flagships: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    by_full = {repo.repository: repo for repo in repos}
    unknown_namespaces = sorted(set(namespace_assertions) - set(by_full))
    unknown_lineage = sorted(set(lineage_assertions) - set(by_full))
    if unknown_namespaces:
        raise ValueError(f"unknown namespace assertions: {unknown_namespaces}")
    if unknown_lineage:
        raise ValueError(f"unknown lineage assertions: {unknown_lineage}")

    engineering = [
        repo
        for repo in repos
        if namespace(repo, namespace_assertions) is Namespace.ENGINEERING
    ]
    engineering_names = {repo.repository for repo in engineering}
    parent: dict[str, str] = {}
    edges: list[dict[str, Any]] = []

    for repository, (relation, target, refs) in lineage_assertions.items():
        if target not in by_full:
            raise ValueError(f"lineage target does not exist: {target}")
        if repository not in engineering_names or target not in engineering_names:
            raise ValueError(f"lineage crosses namespace boundary: {repository} -> {target}")
        if relation is Relation.EXPLICIT_SUCCESSOR_OF:
            child, reference = target, repository
        else:
            child, reference = repository, target
        if child in parent and parent[child] != reference:
            raise ValueError(f"conflicting lineage parent for {child}")
        parent[child] = reference
        edges.append(
            {
                "repository": repository,
                "relation": relation.value,
                "target": target,
                "collapse_child": child,
                "collapse_parent": reference,
                "confidence": "EXPLICIT_EVIDENCE",
                "evidence_refs": list(refs),
            }
        )

    by_key: dict[str, list[Repo]] = defaultdict(list)
    for repo in engineering:
        by_key[lineage_key(repo.name)].append(repo)

    for repo in engineering:
        if repo.repository in parent:
            continue
        lowered = repo.name.casefold()
        historical = (
            lowered.startswith(BACKUP_PREFIXES)
            or lowered.endswith(BACKUP_SUFFIXES)
            or lowered.endswith(ARCHIVE_SUFFIXES)
            or repo.archived
        )
        if not historical:
            continue
        candidates = [
            candidate
            for candidate in by_key[lineage_key(repo.name)]
            if candidate.repository != repo.repository
            and not candidate.archived
            and not candidate.name.casefold().startswith(BACKUP_PREFIXES)
        ]
        if not candidates:
            continue
        target_repo = min(candidates, key=lambda item: (len(item.name), item.name.casefold()))
        relation = (
            Relation.BACKUP_OF
            if lowered.startswith(BACKUP_PREFIXES) or lowered.endswith(BACKUP_SUFFIXES)
            else Relation.ARCHIVE_OF
        )
        parent[repo.repository] = target_repo.repository
        edges.append(
            {
                "repository": repo.repository,
                "relation": relation.value,
                "target": target_repo.repository,
                "collapse_child": repo.repository,
                "collapse_parent": target_repo.repository,
                "confidence": "STRUCTURAL_HIGH",
                "evidence_refs": ["authenticated_census:name+archive_metadata"],
            }
        )

    for repo in engineering:
        _root_of(repo.repository, parent)

    unresolved: list[dict[str, Any]] = []
    unresolved_members: set[str] = set()
    roots_by_key: dict[str, list[str]] = defaultdict(list)
    for repo in engineering:
        if repo.repository not in parent:
            roots_by_key[lineage_key(repo.name)].append(repo.repository)
    for key, root_members in sorted(roots_by_key.items()):
        if len(root_members) < 2:
            continue
        ordered = sorted(root_members)
        unresolved_members.update(ordered)
        unresolved.append(
            {
                "kind": "UNRESOLVED_LINEAGE_CANDIDATE",
                "lineage_key": key,
                "repositories": ordered,
                "reason": "Normalized identity overlaps without sufficient collapse evidence.",
                "next_action": (
                    "Compare ancestry, source overlap, README identity, branch history, "
                    "and unique patch value."
                ),
            }
        )

    grouped: dict[str, list[Repo]] = defaultdict(list)
    for repo in engineering:
        grouped[_root_of(repo.repository, parent)].append(repo)

    systems: list[dict[str, Any]] = []
    repo_to_system: dict[str, str] = {}
    for root in sorted(grouped):
        members = sorted(grouped[root], key=lambda item: item.repository.casefold())
        system_id = _system_id(root)
        for member in members:
            repo_to_system[member.repository] = system_id
        root_repo = by_full[root]
        flagship = _flagship_for_members(members, flagships)
        systems.append(
            {
                "system_id": system_id,
                "source_repository": root,
                "member_repositories": [member.repository for member in members],
                "historical_member_count": max(0, len(members) - 1),
                "visibility": root_repo.visibility,
                "archived": root_repo.archived,
                "flagship_level": flagship.get("level"),
                "flagship_state": flagship.get("state"),
                "public_surface": flagship.get("public_surface"),
                "role": flagship.get("role"),
                "evidence_summary": flagship.get("evidence"),
                "lineage_complete": not any(
                    member.repository in unresolved_members for member in members
                ),
            }
        )

    legal = [
        repo
        for repo in repos
        if namespace(repo, namespace_assertions) is Namespace.LEGAL_PRIVATE
    ]
    forks = [repo for repo in repos if repo.fork]
    registry: dict[str, Any] = {
        "schema": "glaciereq.reference-system-registry.v1",
        "systems": systems,
        "lineage_edges": sorted(
            edges,
            key=lambda row: (str(row["collapse_parent"]), str(row["collapse_child"])),
        ),
        "separate_namespaces": {
            "legal_private": {
                "repository_count": len(legal),
                "public_projection_allowed": False,
                "repository_ids_digest": digest(
                    sorted(repo.repository_id for repo in legal)
                ),
            },
            "fork_reference": {
                "repository_count": len(forks),
                "counts_as_native_accomplishment": False,
            },
        },
        "namespace_assertions_applied": len(namespace_assertions),
        "namespace_classification_state": (
            "EXPLICIT_AND_HEURISTIC" if namespace_assertions else "HEURISTIC_ONLY"
        ),
        "unresolved_lineage": unresolved,
    }
    registry["content_hash"] = digest(registry)
    return registry, repo_to_system


def build_capabilities(
    systems: Mapping[str, Any],
    repo_to_system: Mapping[str, str],
    flagships: Mapping[str, Any] | None,
    semantic_assertions: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    donors: dict[str, dict[str, Any]] = {}
    for row in (flagships or {}).get("flagships", []):
        if not isinstance(row, dict):
            continue
        repository = row.get("repository")
        if not isinstance(repository, str) or repository not in repo_to_system:
            continue
        system_id = repo_to_system[repository]
        text = " ".join(
            str(row.get(key) or "")
            for key in ("role", "evidence", "next_gate", "system_id")
        ).casefold()
        inferred_capabilities = [
            capability
            for capability, patterns in CAPABILITY_PATTERNS
            if any(pattern in text for pattern in patterns)
        ]
        role = row.get("role")
        if isinstance(role, str) and role.strip():
            inferred_capabilities.append(f"role-{slug(role)}")
        for capability in set(inferred_capabilities):
            donor = donors.setdefault(
                capability,
                {"systems": set(), "proof_refs": []},
            )
            donor["systems"].add(system_id)
            evidence = row.get("evidence")
            if isinstance(evidence, str) and evidence.strip():
                donor["proof_refs"].append(
                    {
                        "system_id": system_id,
                        "source": "manifests/flagship_registry.json",
                        "evidence": evidence,
                    }
                )

    for company_id, rows in (semantic_assertions or {}).items():
        for row in rows:
            capability = str(row["capability_id"])
            system_id = str(row["system_id"])
            donor = donors.setdefault(
                capability,
                {"systems": set(), "proof_refs": []},
            )
            donor["systems"].add(system_id)
            donor["proof_refs"].append(
                {
                    "system_id": system_id,
                    "source": "semantic_capability_map",
                    "company_id": company_id,
                    "repository": row["repository"],
                    "head_sha": row["head_sha"],
                    "proof_state": row["proof_state"],
                    "admission_state": row["admission_state"],
                    "evidence_refs": list(row["evidence_refs"]),
                    "proof_receipts": list(row["proof_receipts"]),
                }
            )

    capability_records: list[dict[str, Any]] = []
    for capability_id in sorted(donors):
        donor = donors[capability_id]
        system_ids = sorted(donor["systems"])
        capability_records.append(
            {
                "capability_id": capability_id,
                "donor_systems": system_ids,
                "independent_donor_count": len(system_ids),
                "repeat_pattern": len(system_ids) >= 2,
                "proof_refs": donor["proof_refs"],
                "verification_state": (
                    "EVIDENCE_BOUND" if donor["proof_refs"] else "METADATA_ONLY"
                ),
            }
        )

    registry: dict[str, Any] = {
        "schema": "glaciereq.capability-donor-registry.v1",
        "capabilities": capability_records,
        "policy": {
            "multi_donor_claim_requires": 2,
            "metadata_inference_is_not_runtime_proof": True,
            "legal_private_namespace_may_export_raw_records": False,
            "semantic_donors_require_public_exact_head_receipts": True,
        },
    }
    registry["content_hash"] = digest(registry)
    return registry


def _companies(
    index: Mapping[str, Any] | None,
    shards: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if index is None:
        return []
    required = index.get("required_company_tracks", [])
    if not isinstance(required, list):
        raise ValueError("required_company_tracks must be a list")

    companies: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shard in shards:
        defaults = shard.get("defaults", {})
        if not isinstance(defaults, dict):
            raise ValueError("company shard defaults must be an object")
        raw_companies = shard.get("companies", [])
        if not isinstance(raw_companies, list):
            raise ValueError("company shard companies must be a list")
        for raw in raw_companies:
            company = dict(defaults)
            company.update(_mapping(raw, "company"))
            company_id = company.get("company_id")
            if not isinstance(company_id, str) or not company_id:
                raise ValueError("company_id is required")
            if company_id in seen:
                raise ValueError(f"duplicate company_id: {company_id}")
            seen.add(company_id)
            companies.append(company)

    missing = sorted(set(required) - seen)
    unexpected = sorted(seen - set(required))
    if missing or unexpected:
        raise ValueError(
            f"company track drift: missing={missing}, unexpected={unexpected}"
        )
    return companies


def _semantic_capability_assertions(
    payload: Mapping[str, Any] | None,
    companies: Sequence[Mapping[str, Any]],
    repo_to_system: Mapping[str, str],
    systems: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    dossier_rows_present = any(company.get("capability_donors") for company in companies)
    if not payload:
        if dossier_rows_present:
            raise ValueError("company capability_donors require a semantic capability map")
        return {}

    donor_systems = payload.get("donor_systems")
    capabilities = payload.get("capabilities")
    projections = payload.get("company_projection")
    if not isinstance(donor_systems, dict):
        raise ValueError("semantic capability map donor_systems must be an object")
    if not isinstance(capabilities, list):
        raise ValueError("semantic capability map capabilities must be a list")
    if not isinstance(projections, dict):
        raise ValueError("semantic capability map company_projection must be an object")

    company_by_id = {str(company["company_id"]): company for company in companies}
    system_by_id = {str(row["system_id"]): row for row in systems["systems"]}
    repository_states: dict[str, set[str]] = defaultdict(set)
    for company in companies:
        rows = company.get("repositories", [])
        if not isinstance(rows, list):
            raise ValueError(f"{company['company_id']}: repositories must be a list")
        for row in rows:
            if not isinstance(row, list) or len(row) != 6:
                raise ValueError(f"{company['company_id']}: repository row must have six columns")
            repository_states[str(row[0])].add(str(row[2]))

    blocked = payload.get("blocked_candidate_systems", {})
    if blocked is not None and not isinstance(blocked, dict):
        raise ValueError("blocked_candidate_systems must be an object")
    blocked_names = set(blocked or {})
    if blocked_names & set(donor_systems):
        raise ValueError("blocked candidate system cannot also be a semantic donor")

    validated_donors: dict[str, dict[str, Any]] = {}
    for repository, value in donor_systems.items():
        if not isinstance(repository, str) or not repository:
            raise ValueError("semantic donor repository must be a non-empty string")
        raw = _mapping(value, f"semantic donor {repository}")
        system_id = repo_to_system.get(repository)
        if system_id is None:
            raise ValueError(f"semantic donor is not a native engineering system: {repository}")
        system = system_by_id[system_id]
        if system.get("visibility") != "public" or raw.get("visibility") != "public":
            raise ValueError(f"semantic donor must be public: {repository}")
        if raw.get("fork") is not False:
            raise ValueError(f"semantic donor must be a verified non-fork: {repository}")
        head_sha = raw.get("head_sha")
        if not isinstance(head_sha, str) or re.fullmatch(r"[0-9a-f]{40}", head_sha) is None:
            raise ValueError(f"semantic donor requires an exact head SHA: {repository}")
        proof_state = raw.get("proof_state")
        if not isinstance(proof_state, str) or "VERIFIED" not in proof_state:
            raise ValueError(f"semantic donor requires verified proof state: {repository}")

        inventory = raw.get("evidence_inventory")
        if not isinstance(inventory, list) or not inventory:
            raise ValueError(f"semantic donor requires evidence_inventory: {repository}")
        inventory_paths: set[str] = set()
        for index, item in enumerate(inventory):
            evidence = _mapping(item, f"{repository}.evidence_inventory[{index}]")
            path = evidence.get("path")
            blob_sha = evidence.get("blob_sha")
            if not isinstance(path, str) or not path:
                raise ValueError(f"{repository}: evidence path must be non-empty")
            if not isinstance(blob_sha, str) or re.fullmatch(r"[0-9a-f]{40}", blob_sha) is None:
                raise ValueError(f"{repository}: evidence blob must be an exact SHA")
            if path in inventory_paths:
                raise ValueError(f"{repository}: duplicate evidence path {path}")
            inventory_paths.add(path)

        receipts = raw.get("proof_receipts")
        if not isinstance(receipts, list) or not receipts:
            raise ValueError(f"semantic donor requires exact-head proof receipts: {repository}")
        for index, item in enumerate(receipts):
            receipt = _mapping(item, f"{repository}.proof_receipts[{index}]")
            if receipt.get("kind") != "check_run":
                raise ValueError(f"{repository}: unsupported proof receipt kind")
            if not isinstance(receipt.get("id"), int) or receipt["id"] <= 0:
                raise ValueError(f"{repository}: proof receipt requires positive id")
            if not isinstance(receipt.get("name"), str) or not receipt["name"]:
                raise ValueError(f"{repository}: proof receipt requires name")
            if receipt.get("head_sha") != head_sha:
                raise ValueError(f"{repository}: proof receipt head SHA drift")
            if receipt.get("conclusion") != "success":
                raise ValueError(f"{repository}: proof receipt is not successful")

        disallowed_states = repository_states.get(repository, set()) - PUBLIC_RECRUITER_STATES
        if disallowed_states:
            raise ValueError(
                f"semantic donor {repository} has non-recruiter governing states: "
                f"{sorted(disallowed_states)}"
            )
        validated_donors[repository] = {
            "system_id": system_id,
            "head_sha": head_sha,
            "proof_state": proof_state,
            "inventory_paths": inventory_paths,
            "proof_receipts": tuple(dict(item) for item in receipts),
        }

    capability_by_id: dict[str, dict[str, Any]] = {}
    expected_by_company: dict[str, set[str]] = defaultdict(set)
    for index, value in enumerate(capabilities):
        raw = _mapping(value, f"semantic capabilities[{index}]")
        capability_id = raw.get("capability_id")
        company_id = raw.get("company_id")
        repository = raw.get("donor_repository")
        if not isinstance(capability_id, str) or re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", capability_id
        ) is None:
            raise ValueError(f"invalid semantic capability id at row {index}")
        if capability_id in capability_by_id:
            raise ValueError(f"duplicate semantic capability id: {capability_id}")
        if not isinstance(company_id, str) or company_id not in company_by_id:
            raise ValueError(f"{capability_id}: unknown company_id")
        if not isinstance(repository, str) or repository not in validated_donors:
            raise ValueError(f"{capability_id}: unknown or ineligible donor repository")
        donor = validated_donors[repository]
        if raw.get("head_sha") != donor["head_sha"]:
            raise ValueError(f"{capability_id}: donor head SHA drift")
        evidence_refs = raw.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValueError(f"{capability_id}: evidence_refs must be non-empty")
        if not all(isinstance(ref, str) and ref for ref in evidence_refs):
            raise ValueError(f"{capability_id}: evidence_refs must be strings")
        if not set(evidence_refs) <= donor["inventory_paths"]:
            raise ValueError(f"{capability_id}: evidence ref is outside donor inventory")
        if not isinstance(raw.get("recruiter_safe_claim"), str) or not raw[
            "recruiter_safe_claim"
        ].strip():
            raise ValueError(f"{capability_id}: recruiter_safe_claim is required")
        capability_by_id[capability_id] = dict(raw)
        expected_by_company[company_id].add(capability_id)

    assertions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for company in companies:
        company_id = str(company["company_id"])
        rows = company.get("capability_donors", [])
        if not isinstance(rows, list):
            raise ValueError(f"{company_id}: capability_donors must be a list")
        if rows and not isinstance(company.get("capability_map"), str):
            raise ValueError(f"{company_id}: capability_donors require capability_map")
        seen: set[tuple[str, str]] = set()
        for row in rows:
            if not isinstance(row, list) or len(row) != 4:
                raise ValueError(
                    f"{company_id}: capability donor row must have four columns"
                )
            repository, capability_id, proof_state, admission_state = row
            if not all(
                isinstance(item, str) and item
                for item in (repository, capability_id, proof_state, admission_state)
            ):
                raise ValueError(f"{company_id}: capability donor columns must be strings")
            key = (repository, capability_id)
            if key in seen:
                raise ValueError(f"{company_id}: duplicate capability donor {key}")
            seen.add(key)
            capability = capability_by_id.get(capability_id)
            if capability is None:
                raise ValueError(f"{company_id}: unknown semantic capability {capability_id}")
            if capability["company_id"] != company_id:
                raise ValueError(f"{company_id}: semantic capability belongs to another company")
            if capability["donor_repository"] != repository:
                raise ValueError(f"{company_id}: semantic donor repository mismatch")
            donor = validated_donors[repository]
            if proof_state != donor["proof_state"]:
                raise ValueError(f"{company_id}: semantic donor proof state drift")
            if admission_state not in PUBLIC_RECRUITER_STATES:
                raise ValueError(f"{company_id}: semantic donor is not recruiter-admissible")
            assertions[company_id].append(
                {
                    "repository": repository,
                    "system_id": donor["system_id"],
                    "capability_id": capability_id,
                    "head_sha": donor["head_sha"],
                    "proof_state": proof_state,
                    "admission_state": admission_state,
                    "evidence_refs": tuple(capability["evidence_refs"]),
                    "proof_receipts": donor["proof_receipts"],
                }
            )

    for company_id, expected_ids in expected_by_company.items():
        projection = _mapping(
            projections.get(company_id),
            f"semantic company_projection.{company_id}",
        )
        projection_ids = projection.get("capability_ids")
        projection_repositories = projection.get("donor_repositories")
        if not isinstance(projection_ids, list) or set(projection_ids) != expected_ids:
            raise ValueError(f"{company_id}: semantic projection capability drift")
        expected_repositories = {
            capability_by_id[capability_id]["donor_repository"]
            for capability_id in expected_ids
        }
        if not isinstance(projection_repositories, list) or set(
            projection_repositories
        ) != expected_repositories:
            raise ValueError(f"{company_id}: semantic projection donor drift")
        if projection.get("state") != company_by_id[company_id].get("track_state"):
            raise ValueError(f"{company_id}: semantic projection track state drift")
        if projection.get("affiliation_claim") is not False:
            raise ValueError(f"{company_id}: semantic projection must deny affiliation")
        if projection.get("deployment_claim") is True:
            raise ValueError(f"{company_id}: semantic projection cannot infer deployment")
        asserted_ids = {row["capability_id"] for row in assertions.get(company_id, [])}
        if asserted_ids != expected_ids:
            raise ValueError(f"{company_id}: dossier semantic donor coverage drift")

    return dict(assertions)


def _verification_score(state: object) -> float:
    text = str(state or "")
    if text in {"PROMOTED", "ELITE_VERIFIED"}:
        return 95.0
    if text in {"REFERENCE_ONLY", "RECRUITER_READY", "TEST_VERIFIED"}:
        return 75.0
    if "BLOCKED" in text:
        return 35.0
    if "QUARANTIN" in text or "EXCLUDED" in text:
        return 10.0
    return 50.0


def _score(
    system: Mapping[str, Any],
    company_count: int,
    capability_count: int,
    provenance: Iterable[str],
) -> dict[str, Any]:
    provenance_set = set(provenance)
    if "ORIGINAL_CANDIDATE" in provenance_set:
        originality = 60.0
        originality_state = "CANDIDATE_NOT_VERIFIED_AUTHORSHIP"
    elif any(value.startswith("UPSTREAM") for value in provenance_set):
        originality = 15.0
        originality_state = "UPSTREAM_OR_REFERENCE"
    else:
        originality = 35.0
        originality_state = "INSUFFICIENT_PROVENANCE"
    depth = _level(system.get("flagship_level"))
    if depth == 0 and system.get("role"):
        depth = 50.0
    components = {
        "originality": originality,
        "technical_depth": depth,
        "verification_strength": _verification_score(system.get("flagship_state")),
        "transferability": min(
            100.0,
            30.0 + 20.0 * capability_count + 10.0 * max(0, company_count - 1),
        ),
        "target_company_relevance": min(100.0, 20.0 + 20.0 * company_count),
    }
    return {
        "components": components,
        "total": round(sum(components.values()) / len(components), 2),
        "evidence_state": {"originality": originality_state},
    }


def _minimal_surface(
    rows: Sequence[Mapping[str, Any]],
    capabilities: Mapping[str, Sequence[str] | set[str]],
    scores: Mapping[str, Mapping[str, Any]],
    limit: int | None = None,
) -> list[str]:
    remaining = list(rows)
    selected: list[str] = []
    uncovered = {
        capability
        for row in remaining
        for capability in capabilities.get(str(row["system_id"]), ())
    }
    while remaining and uncovered and (limit is None or len(selected) < limit):
        best = max(
            remaining,
            key=lambda row: (
                len(uncovered & set(capabilities.get(str(row["system_id"]), ()))),
                float(scores[str(row["system_id"])]["total"]),
                str(row["system_id"]),
            ),
        )
        system_id = str(best["system_id"])
        new_coverage = uncovered & set(capabilities.get(system_id, ()))
        if not new_coverage:
            break
        selected.append(system_id)
        uncovered -= new_coverage
        remaining = [row for row in remaining if row["system_id"] != system_id]
    return selected


def build_company_projections(
    systems: Mapping[str, Any],
    capabilities: Mapping[str, Any],
    repo_to_system: Mapping[str, str],
    index: Mapping[str, Any] | None,
    shards: Sequence[Mapping[str, Any]],
    semantic_assertions: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    system_by_id = {row["system_id"]: row for row in systems["systems"]}
    capability_ids: dict[str, list[str]] = defaultdict(list)
    for capability in capabilities["capabilities"]:
        for system_id in capability["donor_systems"]:
            capability_ids[system_id].append(capability["capability_id"])

    companies = _companies(index, shards)
    mappings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    company_ids: dict[str, set[str]] = defaultdict(set)
    provenance: dict[str, set[str]] = defaultdict(set)
    for company in companies:
        company_id = company["company_id"]
        rows = company.get("repositories", [])
        if not isinstance(rows, list):
            raise ValueError(f"{company_id}: repositories must be a list")
        for row in rows:
            if not isinstance(row, list) or len(row) != 6:
                raise ValueError(f"{company_id}: repository row must have six columns")
            repository, level, state, visibility, scope, provenance_state = row
            system_id = repo_to_system.get(repository) if isinstance(repository, str) else None
            if system_id is None:
                continue
            mappings[company_id].append(
                {
                    "system_id": system_id,
                    "source_repository": repository,
                    "level": level,
                    "promotion_state": state,
                    "visibility": visibility,
                    "inventory_scope": scope,
                    "provenance_state": provenance_state,
                    "mapping_kind": "repository",
                    "capability_ids": sorted(set(capability_ids[system_id])),
                }
            )
            company_ids[system_id].add(company_id)
            provenance[system_id].add(str(provenance_state))

        for assertion in (semantic_assertions or {}).get(company_id, ()):
            system_id = str(assertion["system_id"])
            system = system_by_id[system_id]
            mappings[company_id].append(
                {
                    "system_id": system_id,
                    "source_repository": assertion["repository"],
                    "level": system.get("flagship_level") or "L0",
                    "promotion_state": assertion["admission_state"],
                    "visibility": system.get("visibility"),
                    "inventory_scope": "SEMANTIC_CAPABILITY_DONOR",
                    "provenance_state": "SEMANTIC_DONOR_ASSERTION",
                    "mapping_kind": "semantic_capability_donor",
                    "semantic_proof_state": assertion["proof_state"],
                    "capability_ids": [assertion["capability_id"]],
                }
            )
            company_ids[system_id].add(company_id)
            provenance[system_id].add("SEMANTIC_DONOR_ASSERTION")

    scores: dict[str, dict[str, Any]] = {}
    for system_id, system in system_by_id.items():
        score = _score(
            system,
            len(company_ids[system_id]),
            len(set(capability_ids[system_id])),
            provenance[system_id],
        )
        public = (
            system.get("visibility") == "public"
            and system.get("public_surface") not in PRIVATE_SURFACES
            and "QUARANTIN" not in str(system.get("flagship_state") or "")
        )
        score["visibility_decision"] = (
            "PUBLIC_ELIGIBLE" if public else "INTERNAL_OR_SANITIZED_ONLY"
        )
        scores[system_id] = score

    projections: list[dict[str, Any]] = []
    for company in companies:
        company_id = company["company_id"]
        deduped: dict[str, dict[str, Any]] = {}
        for row in mappings[company_id]:
            current = deduped.get(row["system_id"])
            if current is None:
                deduped[row["system_id"]] = dict(row)
                continue
            combined = sorted(
                set(current.get("capability_ids", [])) | set(row.get("capability_ids", []))
            )
            preferred = row if _level(row["level"]) > _level(current["level"]) else current
            merged = dict(preferred)
            merged["capability_ids"] = combined
            deduped[row["system_id"]] = merged

        ranked = sorted(
            deduped.values(),
            key=lambda row: (
                -float(scores[row["system_id"]]["total"]),
                str(row["system_id"]),
            ),
        )
        system_ids = [row["system_id"] for row in ranked]
        scoped_capabilities: dict[str, set[str]] = defaultdict(set)
        for row in ranked:
            scoped_capabilities[row["system_id"]].update(row.get("capability_ids", []))
        projections.append(
            {
                "company_id": company_id,
                "display_name": company.get("display_name", company_id),
                "target_roles": company.get("target_roles", []),
                "operating_problem": company.get("gap_or_next_gate"),
                "operating_problem_source": "company_dossier.gap_or_next_gate",
                "recruiter_thesis": company.get("recruiter_thesis"),
                "reference_systems": system_ids,
                "capabilities": sorted(
                    {
                        capability
                        for system_id in system_ids
                        for capability in scoped_capabilities[system_id]
                    }
                ),
                "minimal_proof_surface": _minimal_surface(
                    ranked,
                    scoped_capabilities,
                    scores,
                ),
                "projection_innovation": "complete_ranked_relation_graph_with_minimal_proof_view",
                "ranked_evidence": [
                    {
                        **row,
                        "promotion_score": scores[row["system_id"]]["total"],
                        "visibility_decision": scores[row["system_id"]][
                            "visibility_decision"
                        ],
                    }
                    for row in ranked
                ],
                "non_affiliation": company.get("non_affiliation"),
            }
        )

    registry: dict[str, Any] = {
        "schema": "glaciereq.company-projection-registry.v1",
        "projections": projections,
        "promotion_scores": scores,
        "policy": {
            "score_axes": [
                "originality",
                "technical_depth",
                "verification_strength",
                "transferability",
                "target_company_relevance",
            ],
            "score_weights": "equal",
            "public_visibility_is_derived_separately": True,
            "company_projection_cannot_publish_legal_private_namespace": True,
            "company_surface_max_systems": None,
            "company_relation_membership": "complete_ranked_relation_graph",
            "minimal_proof_surface_is_non_authoritative": True,
            "presentation_pagination_changes_membership": False,
            "semantic_capability_donors_are_company_scoped": True,
        },
    }
    registry["content_hash"] = digest(registry)
    return registry


def build_experiments(
    shards: Sequence[Mapping[str, Any]],
    repo_to_system: Mapping[str, str],
) -> list[dict[str, Any]]:
    requirements = {
        ExperimentStage.DISTINCT_VALUE.value: ["unique_value_evidence"],
        ExperimentStage.TESTED.value: ["positive_count_test_receipt"],
        ExperimentStage.SYSTEM_COMPONENT.value: ["reference_system_integration_receipt"],
        ExperimentStage.FLAGSHIP_DONOR.value: [
            "capability_proof",
            "promotion_score_gate",
        ],
    }
    experiments: dict[str, dict[str, Any]] = {}
    for shard in shards:
        defaults = shard.get("defaults", {})
        if not isinstance(defaults, dict):
            defaults = {}
        for raw in shard.get("companies", []):
            if not isinstance(raw, dict):
                continue
            company = dict(defaults)
            company.update(raw)
            for row in company.get("repositories", []):
                is_experiment = (
                    isinstance(row, list)
                    and len(row) == 6
                    and row[2] in {"EXPERIMENT", "PRIVATE_EXPERIMENT"}
                )
                if not is_experiment:
                    continue
                repository = row[0]
                item = experiments.setdefault(
                    repository,
                    {
                        "repository": repository,
                        "system_id": repo_to_system.get(repository),
                        "stage": ExperimentStage.EXPERIMENT.value,
                        "company_tracks": [],
                        "promotion_requirements": requirements,
                    },
                )
                item["company_tracks"].append(company.get("company_id"))
    return sorted(experiments.values(), key=lambda row: row["repository"].casefold())


def compile_estate(
    census: Mapping[str, Any],
    *,
    flagships: Mapping[str, Any] | None = None,
    company_index: Mapping[str, Any] | None = None,
    company_shards: Sequence[Mapping[str, Any]] = (),
    lineage: Mapping[str, Any] | None = None,
    semantic_capabilities: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repos = load_census(census)
    namespace_assertions = _namespace_assertions(lineage)
    lineage_assertions = _lineage_assertions(lineage)
    systems, repo_to_system = build_systems(
        repos,
        lineage_assertions,
        namespace_assertions,
        flagships,
    )
    company_records = _companies(company_index, company_shards)
    semantic_assertions = _semantic_capability_assertions(
        semantic_capabilities,
        company_records,
        repo_to_system,
        systems,
    )
    capabilities = build_capabilities(
        systems,
        repo_to_system,
        flagships,
        semantic_assertions,
    )
    companies = build_company_projections(
        systems,
        capabilities,
        repo_to_system,
        company_index,
        company_shards,
        semantic_assertions,
    )
    experiments = build_experiments(company_shards, repo_to_system)
    source_digest = digest(
        {
            "census": census,
            "flagships": flagships,
            "company_index": company_index,
            "company_shards": list(company_shards),
            "estate_facts": lineage,
            "semantic_capabilities": semantic_capabilities,
        }
    )
    receipt = {
        "schema": "glaciereq.estate-compiler-receipt.v1",
        "status": "PASS_WITH_UNRESOLVED" if systems["unresolved_lineage"] else "PASS",
        "source_digest": source_digest,
        "counts": {
            "total_holdings": len(repos),
            "native_repositories": sum(not repo.fork for repo in repos),
            "engineering_native_repositories": sum(
                namespace(repo, namespace_assertions) is Namespace.ENGINEERING
                for repo in repos
            ),
            "legal_private_repositories": sum(
                namespace(repo, namespace_assertions) is Namespace.LEGAL_PRIVATE
                for repo in repos
            ),
            "fork_references": sum(repo.fork for repo in repos),
            "namespace_assertions_applied": len(namespace_assertions),
            "reference_systems": len(systems["systems"]),
            "lineage_edges": len(systems["lineage_edges"]),
            "unresolved_lineage_candidates": len(systems["unresolved_lineage"]),
            "capabilities": len(capabilities["capabilities"]),
            "semantic_capability_assertions": sum(
                len(rows) for rows in semantic_assertions.values()
            ),
            "company_projections": len(companies["projections"]),
            "experiments": len(experiments),
        },
        "registry_hashes": {
            "system_registry": systems["content_hash"],
            "capability_donor_registry": capabilities["content_hash"],
            "company_projection_registry": companies["content_hash"],
        },
        "invariants": {
            "forks_not_counted_as_native_accomplishments": True,
            "legal_private_namespace_not_company_projectable": True,
            "ambiguous_lineage_not_silently_collapsed": True,
            "public_visibility_separate_from_promotion_score": True,
            "unsupported_capabilities_not_promoted_as_runtime_proof": True,
            "blocked_repositories_not_semantic_capability_donors": True,
            "semantic_donor_proof_receipts_match_exact_head": True,
        },
    }
    bundle: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "source_digest": source_digest,
        "system_registry": systems,
        "capability_donor_registry": capabilities,
        "company_projection_registry": companies,
        "experiment_pipeline": experiments,
        "receipt": receipt,
    }
    bundle["content_hash"] = digest(bundle)
    return bundle


def public_safe_projection(bundle: Mapping[str, Any]) -> dict[str, Any]:
    systems = bundle["system_registry"]["systems"]
    globally_allowed = {
        row["system_id"]
        for row in systems
        if row.get("visibility") == "public"
        and row.get("public_surface") not in PRIVATE_SURFACES
    }
    capabilities_by_system: dict[str, set[str]] = defaultdict(set)
    for capability in bundle["capability_donor_registry"]["capabilities"]:
        for system_id in capability["donor_systems"]:
            capabilities_by_system[system_id].add(capability["capability_id"])

    company_registry = bundle["company_projection_registry"]
    scores = company_registry["promotion_scores"]
    projections: list[dict[str, Any]] = []
    for projection in company_registry["projections"]:
        evidence = [
            row
            for row in projection["ranked_evidence"]
            if row["system_id"] in globally_allowed
            and row["visibility_decision"] == "PUBLIC_ELIGIBLE"
            and row["visibility"] == "public"
            and row["promotion_state"] in PUBLIC_RECRUITER_STATES
        ]
        safe_capabilities_by_system: dict[str, set[str]] = defaultdict(set)
        for row in evidence:
            row_capabilities = row.get("capability_ids")
            if isinstance(row_capabilities, list):
                safe_capabilities_by_system[row["system_id"]].update(row_capabilities)
            else:
                safe_capabilities_by_system[row["system_id"]].update(
                    capabilities_by_system[row["system_id"]]
                )
        safe_ids = {row["system_id"] for row in evidence}
        safe_capabilities = sorted(
            {
                capability
                for system_id in safe_ids
                for capability in safe_capabilities_by_system[system_id]
            }
        )
        safe_surface = (
            _minimal_surface(evidence, safe_capabilities_by_system, scores)
            if evidence
            else []
        )
        projections.append(
            {
                **{
                    key: value
                    for key, value in projection.items()
                    if key
                    not in {
                        "ranked_evidence",
                        "reference_systems",
                        "minimal_proof_surface",
                        "capabilities",
                    }
                },
                "reference_systems": [
                    system_id
                    for system_id in projection["reference_systems"]
                    if system_id in safe_ids
                ],
                "capabilities": safe_capabilities,
                "minimal_proof_surface": safe_surface,
                "ranked_evidence": evidence,
            }
        )

    public = {
        "schema": "glaciereq.estate-public-projection.v1",
        "source_digest": bundle["source_digest"],
        "company_projections": projections,
        "boundary": (
            "Private repository identities, legal-private records, and non-recruiter "
            "promotion states are excluded."
        ),
    }
    private_full_names = {
        member
        for system in systems
        if system.get("visibility") != "public"
        for member in system.get("member_repositories", [])
        if isinstance(member, str)
    }
    serialized = json.dumps(public, sort_keys=True)
    leaked = sorted(name for name in private_full_names if name in serialized)
    if leaked:
        raise ValueError(f"public projection leaked private repository identities: {leaked}")
    return public
