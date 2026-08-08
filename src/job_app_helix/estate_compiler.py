from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "glaciereq.estate-compiler.v1"
LEGAL_TOKENS = (
    "1fdv", "1fda", "family-court", "family_court", "litigation", "docket",
    "legal-doc", "legal_doc", "court-record", "court_record", "case-1fd", "case_1fd",
)
BACKUP_PREFIXES = ("z-backup-", "backup-", "z_backup_", "backup_")
BACKUP_SUFFIXES = ("-backup", "_backup", "__backup", "-bak", "_bak")
ARCHIVE_SUFFIXES = ("-archive", "_archive", "__archive", "-archived", "_archived")
PRIVATE_SURFACES = {
    "PRIVATE_UNTIL_SANITIZED", "SANITIZED_CARD_ONLY", "EXCLUDED",
    "EXCLUDED_UNTIL_FIXED", "PUBLIC_AFTER_FIX",
}
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


@dataclass(frozen=True, slots=True)
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
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unnamed"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def load_census(payload: Mapping[str, Any]) -> tuple[Repo, ...]:
    if payload.get("state") != "VERIFIED_INVENTORY":
        raise ValueError("estate compiler requires a VERIFIED_INVENTORY census")
    rows = payload.get("repositories")
    if not isinstance(rows, list) or not rows:
        raise ValueError("census.repositories must be non-empty")
    repos: list[Repo] = []
    for i, row in enumerate(rows):
        raw = _mapping(row, f"census.repositories[{i}]")
        repository, rid = raw.get("repository"), raw.get("repository_id")
        visibility, branch = raw.get("visibility"), raw.get("default_branch")
        if not isinstance(repository, str) or "/" not in repository or not isinstance(rid, int):
            raise ValueError(f"invalid repository identity at census.repositories[{i}]")
        if visibility not in {"public", "private", "internal"}:
            raise ValueError(f"{repository}: invalid visibility")
        if not isinstance(branch, str) or not branch:
            raise ValueError(f"{repository}: missing default_branch")
        repos.append(Repo(
            repository=repository,
            repository_id=rid,
            visibility=visibility,
            default_branch=branch,
            archived=bool(raw.get("archived")),
            fork=bool(raw.get("fork")),
            classification=str(raw.get("classification") or "UNCLASSIFIED"),
        ))
    if len({r.repository for r in repos}) != len(repos) or len({r.repository_id for r in repos}) != len(repos):
        raise ValueError("census contains duplicate repository identity")
    if payload.get("repository_count") != len(repos):
        raise ValueError("census repository_count drift")
    if payload.get("native_repository_count") != sum(not r.fork for r in repos):
        raise ValueError("census native_repository_count drift")
    if payload.get("fork_repository_count") != sum(r.fork for r in repos):
        raise ValueError("census fork_repository_count drift")
    return tuple(repos)


def namespace(repo: Repo) -> Namespace:
    if repo.fork:
        return Namespace.FORK_REFERENCE
    lowered = repo.name.casefold()
    if repo.visibility != "public" and any(token in lowered for token in LEGAL_TOKENS):
        return Namespace.LEGAL_PRIVATE
    return Namespace.ENGINEERING


def lineage_key(name: str) -> str:
    value = name.casefold()
    for prefix in BACKUP_PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    for suffix in (*BACKUP_SUFFIXES, *ARCHIVE_SUFFIXES):
        if value.endswith(suffix):
            value = value[:-len(suffix)]
            break
    return re.sub(r"[-_.]+", "-", value).strip("-")


def _assertions(payload: Mapping[str, Any] | None) -> dict[str, tuple[Relation, str, tuple[str, ...]]]:
    if not payload:
        return {}
    rows = payload.get("relationships", [])
    if not isinstance(rows, list):
        raise ValueError("lineage.relationships must be a list")
    result: dict[str, tuple[Relation, str, tuple[str, ...]]] = {}
    for i, row in enumerate(rows):
        raw = _mapping(row, f"lineage.relationships[{i}]")
        repository, target = raw.get("repository"), raw.get("target")
        refs = raw.get("evidence_refs")
        try:
            relation = Relation(str(raw.get("relation")))
        except ValueError as exc:
            raise ValueError(f"invalid lineage relation at row {i}") from exc
        if not isinstance(repository, str) or not isinstance(target, str):
            raise ValueError(f"lineage row {i} requires repository and target")
        if not isinstance(refs, list) or not refs or not all(isinstance(x, str) and x for x in refs):
            raise ValueError(f"lineage row {i} requires evidence_refs")
        if repository in result:
            raise ValueError(f"duplicate lineage assertion: {repository}")
        result[repository] = relation, target, tuple(refs)
    return result


def _system_id(repository: str) -> str:
    return f"sys-{slug(repository.split('/', 1)[-1])}-{hashlib.sha256(repository.encode()).hexdigest()[:8]}"


def build_systems(
    repos: Sequence[Repo],
    assertions: Mapping[str, tuple[Relation, str, tuple[str, ...]]],
    flagships: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    by_full = {r.repository: r for r in repos}
    parent: dict[str, str] = {}
    edges: list[dict[str, Any]] = []
    engineering = [r for r in repos if namespace(r) is Namespace.ENGINEERING]

    for repo in engineering:
        explicit = assertions.get(repo.repository)
        if explicit:
            relation, target, refs = explicit
            if target not in by_full or namespace(by_full[target]) is not Namespace.ENGINEERING:
                raise ValueError(f"invalid cross-boundary lineage target: {repo.repository} -> {target}")
            parent[repo.repository] = target
            edges.append({"repository": repo.repository, "relation": relation.value, "target": target,
                          "confidence": "EXPLICIT_EVIDENCE", "evidence_refs": list(refs)})
            continue
        key = lineage_key(repo.name)
        siblings = [r for r in engineering if r.repository != repo.repository and lineage_key(r.name) == key]
        lowered = repo.name.casefold()
        historical = (
            lowered.startswith(BACKUP_PREFIXES) or lowered.endswith(BACKUP_SUFFIXES)
            or repo.archived or lowered.endswith(ARCHIVE_SUFFIXES)
        )
        if historical and siblings:
            viable = [r for r in siblings if not r.archived and not r.name.casefold().startswith(BACKUP_PREFIXES)]
            if viable:
                target = sorted(viable, key=lambda r: (len(r.name), r.name.casefold()))[0].repository
                relation = Relation.BACKUP_OF if (
                    lowered.startswith(BACKUP_PREFIXES) or lowered.endswith(BACKUP_SUFFIXES)
                ) else Relation.ARCHIVE_OF
                parent[repo.repository] = target
                edges.append({"repository": repo.repository, "relation": relation.value, "target": target,
                              "confidence": "STRUCTURAL_HIGH",
                              "evidence_refs": ["authenticated_census:name+archive_metadata"]})

    def root_of(repository: str) -> str:
        seen: set[str] = set()
        while repository in parent:
            if repository in seen:
                raise ValueError(f"lineage cycle detected at {repository}")
            seen.add(repository)
            repository = parent[repository]
        return repository

    unresolved: list[dict[str, Any]] = []
    grouped: dict[str, list[str]] = defaultdict(list)
    for repo in engineering:
        if repo.repository not in parent:
            grouped[lineage_key(repo.name)].append(repo.repository)
    for key, members in sorted(grouped.items()):
        if len(members) > 1:
            unresolved.append({
                "kind": "UNRESOLVED_LINEAGE_CANDIDATE", "lineage_key": key,
                "repositories": sorted(members),
                "reason": "Normalized identity overlaps without evidence sufficient for collapse.",
                "next_action": "Compare ancestry, source overlap, README identity, branch history, and unique patch value.",
            })

    flagship_by_repo = {}
    for row in (flagships or {}).get("flagships", []):
        if isinstance(row, dict) and isinstance(row.get("repository"), str):
            flagship_by_repo[row["repository"]] = row
    roots: dict[str, list[Repo]] = defaultdict(list)
    for repo in engineering:
        roots[root_of(repo.repository)].append(repo)

    systems, repo_to_system = [], {}
    unresolved_members = {repo for row in unresolved for repo in row["repositories"]}
    for root in sorted(roots):
        system_id, root_repo = _system_id(root), by_full[root]
        members = sorted(roots[root], key=lambda r: r.repository.casefold())
        for member in members:
            repo_to_system[member.repository] = system_id
        f = flagship_by_repo.get(root, {})
        systems.append({
            "system_id": system_id, "canonical_repository": root,
            "member_repositories": [r.repository for r in members],
            "historical_member_count": max(0, len(members) - 1),
            "visibility": root_repo.visibility, "archived": root_repo.archived,
            "flagship_level": f.get("level"), "flagship_state": f.get("state"),
            "public_surface": f.get("public_surface"), "role": f.get("role"),
            "evidence_summary": f.get("evidence"),
            "lineage_complete": root not in unresolved_members,
        })
    legal = [r for r in repos if namespace(r) is Namespace.LEGAL_PRIVATE]
    forks = [r for r in repos if namespace(r) is Namespace.FORK_REFERENCE]
    registry = {
        "schema": "glaciereq.canonical-system-registry.v1", "systems": systems,
        "lineage_edges": sorted(edges, key=lambda x: (x["target"], x["repository"])),
        "separate_namespaces": {
            "legal_private": {"repository_count": len(legal), "public_projection_allowed": False,
                              "repository_ids_digest": digest(sorted(r.repository_id for r in legal))},
            "fork_reference": {"repository_count": len(forks), "counts_as_native_accomplishment": False},
        },
        "unresolved_lineage": unresolved,
    }
    registry["content_hash"] = digest(registry)
    return registry, repo_to_system


def build_capabilities(systems: Mapping[str, Any], flagships: Mapping[str, Any] | None) -> dict[str, Any]:
    system_by_repo = {s["canonical_repository"]: s for s in systems["systems"]}
    donors: dict[str, dict[str, Any]] = {}
    for f in (flagships or {}).get("flagships", []):
        if not isinstance(f, dict) or f.get("repository") not in system_by_repo:
            continue
        system_id = system_by_repo[f["repository"]]["system_id"]
        text = " ".join(str(f.get(k) or "") for k in ("role", "evidence", "next_gate", "system_id")).casefold()
        capabilities = [cap for cap, pats in CAPABILITY_PATTERNS if any(p in text for p in pats)]
        if isinstance(f.get("role"), str) and f["role"].strip():
            capabilities.append(f"role-{slug(f['role'])}")
        for capability in set(capabilities):
            d = donors.setdefault(capability, {"systems": set(), "proof_refs": []})
            d["systems"].add(system_id)
            if isinstance(f.get("evidence"), str) and f["evidence"].strip():
                d["proof_refs"].append({"system_id": system_id, "source": "manifests/flagship_registry.json",
                                        "evidence": f["evidence"]})
    rows = []
    for capability in sorted(donors):
        d = donors[capability]
        ids = sorted(d["systems"])
        rows.append({"capability_id": capability, "donor_systems": ids,
                     "independent_donor_count": len(ids), "repeat_pattern": len(ids) >= 2,
                     "proof_refs": d["proof_refs"],
                     "verification_state": "EVIDENCE_BOUND" if d["proof_refs"] else "METADATA_ONLY"})
    registry = {"schema": "glaciereq.capability-donor-registry.v1", "capabilities": rows,
                "policy": {"multi_donor_claim_requires": 2, "metadata_inference_is_not_runtime_proof": True,
                           "legal_private_namespace_may_export_raw_records": False}}
    registry["content_hash"] = digest(registry)
    return registry


def _companies(index: Mapping[str, Any] | None, shards: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if index is None:
        return []
    required = index.get("required_company_tracks", [])
    if not isinstance(required, list):
        raise ValueError("required_company_tracks must be a list")
    result, seen = [], set()
    for shard in shards:
        defaults = shard.get("defaults", {})
        if not isinstance(defaults, dict):
            raise ValueError("company defaults must be an object")
        for row in shard.get("companies", []):
            raw = _mapping(row, "company")
            company = dict(defaults)
            company.update(raw)
            company_id = company.get("company_id")
            if not isinstance(company_id, str) or company_id in seen:
                raise ValueError(f"invalid or duplicate company_id: {company_id!r}")
            seen.add(company_id)
            result.append(company)
    missing = sorted(set(required) - seen)
    if missing:
        raise ValueError(f"missing company tracks: {missing}")
    return result


def _level(value: object) -> float:
    return float({"L0": 0, "L1": 20, "L2": 40, "L3": 60, "L4": 80, "L5": 100}.get(str(value), 0))


def _verification(state: object) -> float:
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


def _score(system: Mapping[str, Any], companies: int, capabilities: int,
           provenance: Iterable[str]) -> dict[str, Any]:
    p = set(provenance)
    originality = 80.0 if "ORIGINAL_CANDIDATE" in p else (55.0 if p else 45.0)
    depth = _level(system.get("flagship_level")) or (50.0 if system.get("role") else 0.0)
    values = {
        "originality": originality, "technical_depth": depth,
        "verification_strength": _verification(system.get("flagship_state")),
        "transferability": min(100.0, 30 + 20 * capabilities + 10 * max(0, companies - 1)),
        "target_company_relevance": min(100.0, 20 + 20 * companies),
    }
    return {"components": values, "total": round(sum(values.values()) / 5, 2)}


def _minimal_surface(rows: Sequence[Mapping[str, Any]], caps: Mapping[str, Sequence[str]],
                     scores: Mapping[str, Mapping[str, Any]], limit: int = 5) -> list[str]:
    remaining, selected = list(rows), []
    uncovered = {cap for row in remaining for cap in caps.get(str(row["system_id"]), ())}
    all_caps = set(uncovered)
    while remaining and len(selected) < limit:
        def key(row: Mapping[str, Any]) -> tuple[int, float, str]:
            sid = str(row["system_id"])
            return len(uncovered & set(caps.get(sid, ()))), float(scores[sid]["total"]), sid
        best = max(remaining, key=key)
        sid = str(best["system_id"])
        unique = uncovered & set(caps.get(sid, ()))
        if selected and all_caps and not unique:
            break
        selected.append(sid)
        uncovered -= unique
        remaining = [row for row in remaining if row["system_id"] != sid]
    return selected or [str(row["system_id"]) for row in list(rows)[:limit]]


def build_company_projections(
    systems: Mapping[str, Any], capabilities: Mapping[str, Any], repo_to_system: Mapping[str, str],
    index: Mapping[str, Any] | None, shards: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_id = {s["system_id"]: s for s in systems["systems"]}
    caps: dict[str, list[str]] = defaultdict(list)
    for row in capabilities["capabilities"]:
        for sid in row["donor_systems"]:
            caps[sid].append(row["capability_id"])
    companies = _companies(index, shards)
    mappings, company_ids, provenance = defaultdict(list), defaultdict(set), defaultdict(set)
    for company in companies:
        cid = company["company_id"]
        repos = company.get("repositories", [])
        if not isinstance(repos, list):
            raise ValueError(f"{cid}: repositories must be a list")
        for row in repos:
            if not isinstance(row, list) or len(row) != 6:
                raise ValueError(f"{cid}: repository row must have six columns")
            repository, level, state, visibility, scope, prov = row
            sid = repo_to_system.get(repository) if isinstance(repository, str) else None
            if not sid:
                continue
            mappings[cid].append({"system_id": sid, "source_repository": repository, "level": level,
                                  "promotion_state": state, "visibility": visibility,
                                  "inventory_scope": scope, "provenance_state": prov})
            company_ids[sid].add(cid)
            provenance[sid].add(str(prov))

    scores = {}
    for sid, system in by_id.items():
        score = _score(system, len(company_ids[sid]), len(set(caps[sid])), provenance[sid])
        public = (
            system.get("visibility") == "public"
            and system.get("public_surface") not in PRIVATE_SURFACES
            and "QUARANTIN" not in str(system.get("flagship_state") or "")
        )
        score["visibility_decision"] = "PUBLIC_ELIGIBLE" if public else "INTERNAL_OR_SANITIZED_ONLY"
        scores[sid] = score

    projections = []
    for company in companies:
        cid = company["company_id"]
        deduped: dict[str, dict[str, Any]] = {}
        for row in mappings[cid]:
            old = deduped.get(row["system_id"])
            if old is None or _level(row["level"]) > _level(old["level"]):
                deduped[row["system_id"]] = row
        ranked = sorted(deduped.values(), key=lambda row: (-scores[row["system_id"]]["total"], row["system_id"]))
        ids = [row["system_id"] for row in ranked]
        projections.append({
            "company_id": cid, "display_name": company.get("display_name", cid),
            "target_roles": company.get("target_roles", []),
            "operating_problem": company.get("gap_or_next_gate"),
            "operating_problem_source": "company_dossier.gap_or_next_gate",
            "recruiter_thesis": company.get("recruiter_thesis"),
            "canonical_systems": ids,
            "capabilities": sorted({cap for sid in ids for cap in caps[sid]}),
            "minimal_proof_surface": _minimal_surface(ranked, caps, scores),
            "projection_innovation": "bounded_greedy_capability_set_cover",
            "ranked_evidence": [{**row, "promotion_score": scores[row["system_id"]]["total"],
                                 "visibility_decision": scores[row["system_id"]]["visibility_decision"]}
                                for row in ranked],
            "non_affiliation": company.get("non_affiliation"),
        })
    registry = {
        "schema": "glaciereq.company-projection-registry.v1",
        "projections": projections,
        "promotion_scores": scores,
        "policy": {
            "score_axes": ["originality", "technical_depth", "verification_strength",
                           "transferability", "target_company_relevance"],
            "score_weights": "equal", "public_visibility_is_derived_separately": True,
            "company_projection_cannot_publish_legal_private_namespace": True,
            "company_surface_max_systems": 5,
        },
    }
    registry["content_hash"] = digest(registry)
    return registry


def build_experiments(shards: Sequence[Mapping[str, Any]], repo_to_system: Mapping[str, str]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    requirements = {
        ExperimentStage.DISTINCT_VALUE.value: ["unique_value_evidence"],
        ExperimentStage.TESTED.value: ["positive_count_test_receipt"],
        ExperimentStage.SYSTEM_COMPONENT.value: ["canonical_system_integration_receipt"],
        ExperimentStage.FLAGSHIP_DONOR.value: ["capability_proof", "promotion_score_gate"],
    }
    for shard in shards:
        defaults = shard.get("defaults", {}) if isinstance(shard.get("defaults", {}), dict) else {}
        for raw in shard.get("companies", []):
            if not isinstance(raw, dict):
                continue
            company = dict(defaults)
            company.update(raw)
            for row in company.get("repositories", []):
                if not isinstance(row, list) or len(row) != 6 or row[2] not in {"EXPERIMENT", "PRIVATE_EXPERIMENT"}:
                    continue
                repository = row[0]
                item = found.setdefault(repository, {
                    "repository": repository, "system_id": repo_to_system.get(repository),
                    "stage": ExperimentStage.EXPERIMENT.value, "company_tracks": [],
                    "promotion_requirements": requirements,
                })
                item["company_tracks"].append(company.get("company_id"))
    return sorted(found.values(), key=lambda row: row["repository"].casefold())


def compile_estate(
    census: Mapping[str, Any], *, flagships: Mapping[str, Any] | None = None,
    company_index: Mapping[str, Any] | None = None,
    company_shards: Sequence[Mapping[str, Any]] = (),
    lineage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repos = load_census(census)
    systems, repo_to_system = build_systems(repos, _assertions(lineage), flagships)
    capabilities = build_capabilities(systems, flagships)
    companies = build_company_projections(systems, capabilities, repo_to_system, company_index, company_shards)
    experiments = build_experiments(company_shards, repo_to_system)
    source_digest = digest({"census": census, "flagships": flagships, "company_index": company_index,
                            "company_shards": list(company_shards), "lineage": lineage})
    receipt = {
        "schema": "glaciereq.estate-compiler-receipt.v1",
        "status": "PASS_WITH_UNRESOLVED" if systems["unresolved_lineage"] else "PASS",
        "source_digest": source_digest,
        "counts": {
            "total_holdings": len(repos), "native_repositories": sum(not r.fork for r in repos),
            "engineering_native_repositories": sum(namespace(r) is Namespace.ENGINEERING for r in repos),
            "legal_private_repositories": sum(namespace(r) is Namespace.LEGAL_PRIVATE for r in repos),
            "fork_references": sum(r.fork for r in repos), "canonical_systems": len(systems["systems"]),
            "lineage_edges": len(systems["lineage_edges"]),
            "unresolved_lineage_candidates": len(systems["unresolved_lineage"]),
            "capabilities": len(capabilities["capabilities"]),
            "company_projections": len(companies["projections"]), "experiments": len(experiments),
        },
        "registry_hashes": {
            "canonical_system_registry": systems["content_hash"],
            "capability_donor_registry": capabilities["content_hash"],
            "company_projection_registry": companies["content_hash"],
        },
        "invariants": {
            "forks_not_counted_as_native_accomplishments": True,
            "legal_private_namespace_not_company_projectable": True,
            "ambiguous_lineage_not_silently_collapsed": True,
            "public_visibility_separate_from_promotion_score": True,
            "unsupported_capabilities_not_promoted_as_runtime_proof": True,
        },
    }
    bundle = {
        "schema": SCHEMA_VERSION, "source_digest": source_digest,
        "canonical_system_registry": systems, "capability_donor_registry": capabilities,
        "company_projection_registry": companies, "experiment_pipeline": experiments, "receipt": receipt,
    }
    bundle["content_hash"] = digest(bundle)
    return bundle


def public_safe_projection(bundle: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        row["system_id"] for row in bundle["canonical_system_registry"]["systems"]
        if row.get("visibility") == "public" and row.get("public_surface") not in PRIVATE_SURFACES
    }
    projections = []
    for row in bundle["company_projection_registry"]["projections"]:
        evidence = [item for item in row["ranked_evidence"]
                    if item["system_id"] in allowed and item["visibility_decision"] == "PUBLIC_ELIGIBLE"]
        projections.append({
            **{k: v for k, v in row.items() if k != "ranked_evidence"},
            "canonical_systems": [sid for sid in row["canonical_systems"] if sid in allowed],
            "minimal_proof_surface": [sid for sid in row["minimal_proof_surface"] if sid in allowed],
            "ranked_evidence": evidence,
        })
    return {
        "schema": "glaciereq.estate-public-projection.v1",
        "source_digest": bundle["source_digest"], "company_projections": projections,
        "boundary": "Private repository identities and the legal-private namespace are excluded.",
    }
