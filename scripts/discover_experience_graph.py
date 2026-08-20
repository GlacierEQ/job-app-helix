from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENSUS = ROOT / "artifacts" / "owned-library-census.json"
DEFAULT_COMPANIES = ROOT / "manifests" / "company_dossiers.json"
DEFAULT_FLAGSHIPS = ROOT / "manifests" / "flagship_registry.json"
DEFAULT_POLICY = ROOT / "policies" / "experience_graph_policy.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "discovery" / "live-experience-graph.json"


class ExperienceGraphError(RuntimeError):
    pass


def reference_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(reference_json(value).encode("utf-8")).hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def repository_name(repository: str) -> str:
    return repository.split("/", maxsplit=1)[-1]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperienceGraphError(f"Unable to load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExperienceGraphError(f"Expected JSON object at {path}")
    return value


def load_company_catalog(root: Path, index: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    columns = index.get("repository_record_columns")
    shard_paths = index.get("dossier_files")
    if not isinstance(columns, list) or not all(isinstance(item, str) for item in columns):
        raise ExperienceGraphError("Company index has invalid repository columns")
    if not isinstance(shard_paths, list) or not all(isinstance(item, str) for item in shard_paths):
        raise ExperienceGraphError("Company index has invalid dossier files")
    companies: dict[str, dict[str, Any]] = {}
    repository_metadata: dict[str, dict[str, Any]] = {}
    for shard_path in shard_paths:
        shard = _load_json(root / shard_path)
        defaults = shard.get("defaults", {})
        records = shard.get("companies")
        if not isinstance(defaults, dict) or not isinstance(records, list):
            raise ExperienceGraphError(f"Invalid company shard: {shard_path}")
        for raw_company in records:
            if not isinstance(raw_company, dict):
                raise ExperienceGraphError(f"Invalid company record in {shard_path}")
            company = {**defaults, **raw_company}
            company_id = company.get("company_id")
            display_name = company.get("display_name")
            if not isinstance(company_id, str) or not isinstance(display_name, str):
                raise ExperienceGraphError(f"Company identity missing in {shard_path}")
            if company_id in companies:
                raise ExperienceGraphError(f"Duplicate company id: {company_id}")
            normalized_repositories: list[dict[str, Any]] = []
            repositories = company.get("repositories", [])
            if not isinstance(repositories, list):
                raise ExperienceGraphError(f"Invalid repositories for {company_id}")
            for raw_repository in repositories:
                if isinstance(raw_repository, list):
                    if len(raw_repository) != len(columns):
                        raise ExperienceGraphError(f"Repository column mismatch for {company_id}")
                    repository = dict(zip(columns, raw_repository, strict=True))
                elif isinstance(raw_repository, dict):
                    repository = dict(raw_repository)
                else:
                    raise ExperienceGraphError(f"Invalid repository record for {company_id}")
                full_name = repository.get("repository")
                if not isinstance(full_name, str):
                    raise ExperienceGraphError(f"Repository identity missing for {company_id}")
                repository["company_id"] = company_id
                existing = repository_metadata.get(full_name)
                if existing is not None and existing["company_id"] != company_id:
                    raise ExperienceGraphError(f"Repository mapped to multiple companies: {full_name}")
                repository_metadata[full_name] = repository
                normalized_repositories.append(repository)
            company["repositories"] = normalized_repositories
            company["source_shard"] = shard_path
            companies[company_id] = company
    return companies, repository_metadata


def _company_aliases(companies: dict[str, dict[str, Any]], policy: dict[str, Any]) -> dict[str, set[str]]:
    overrides = policy.get("company_alias_overrides", {})
    if not isinstance(overrides, dict):
        raise ExperienceGraphError("company_alias_overrides must be an object")
    aliases: dict[str, set[str]] = {}
    for company_id, company in companies.items():
        values = {normalize(company_id), normalize(str(company["display_name"]))}
        repository_prefixes = Counter(normalize(repository_name(item["repository"])).split("-", maxsplit=1)[0] for item in company["repositories"])
        values.update(prefix for prefix, count in repository_prefixes.items() if count >= 2)
        extra = overrides.get(company_id, [])
        if not isinstance(extra, list) or not all(isinstance(item, str) for item in extra):
            raise ExperienceGraphError(f"Invalid aliases for {company_id}")
        values.update(normalize(item) for item in extra)
        aliases[company_id] = {value for value in values if len(value) >= 3}
    return aliases


def _paradigm_catalog(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = policy.get("personal_paradigm_overrides", {})
    if not isinstance(raw, dict):
        raise ExperienceGraphError("personal_paradigm_overrides must be an object")
    paradigms: dict[str, dict[str, Any]] = {}
    for paradigm_id, value in raw.items():
        if not isinstance(value, dict):
            raise ExperienceGraphError(f"Invalid paradigm: {paradigm_id}")
        aliases = value.get("aliases")
        display_name = value.get("display_name")
        if not isinstance(display_name, str) or not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
            raise ExperienceGraphError(f"Invalid paradigm: {paradigm_id}")
        paradigms[paradigm_id] = {"paradigm_id": paradigm_id, "display_name": display_name, "aliases": sorted({normalize(item) for item in aliases}), "repositories": []}
    return paradigms


def _matches(name: str, alias: str) -> bool:
    return name == alias or name.startswith(f"{alias}-")


def _resolve_company(full_name: str, repository_metadata: dict[str, dict[str, Any]], aliases: dict[str, set[str]]) -> str | None:
    if full_name in repository_metadata:
        return str(repository_metadata[full_name]["company_id"])
    name = normalize(repository_name(full_name))
    matches = [(len(alias), company_id) for company_id, company_aliases in aliases.items() for alias in company_aliases if _matches(name, alias)]
    return max(matches)[1] if matches else None


def _resolve_paradigms(full_name: str, paradigms: dict[str, dict[str, Any]]) -> list[str]:
    name = normalize(repository_name(full_name))
    return sorted(paradigm_id for paradigm_id, paradigm in paradigms.items() if any(_matches(name, alias) for alias in paradigm["aliases"]))


def _family_prefix(name: str, generic_prefixes: set[str]) -> str | None:
    for token in normalize(name).split("-"):
        if len(token) >= 3 and token not in generic_prefixes and not token.isdigit():
            return token
    return None


def _public_node(node: dict[str, Any]) -> dict[str, Any] | None:
    if node["kind"] == "repository" and node.get("visibility") != "public":
        return None
    public = dict(node)
    if node["kind"] == "flagship" and node.get("public_surface") != "PUBLIC":
        public.pop("repository", None)
    return public


def build_experience_graph(*, census: dict[str, Any], companies: dict[str, dict[str, Any]], repository_metadata: dict[str, dict[str, Any]], flagships: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    repositories = census.get("repositories")
    if not isinstance(repositories, list):
        raise ExperienceGraphError("Census has no repositories list")
    company_aliases = _company_aliases(companies, policy)
    paradigms = _paradigm_catalog(policy)
    generic_prefixes = {normalize(value) for value in policy.get("generic_prefixes", [])}
    minimum_family_size = policy.get("minimum_family_size", 2)
    if not isinstance(minimum_family_size, int) or minimum_family_size < 2:
        raise ExperienceGraphError("minimum_family_size must be at least 2")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    family_members: dict[str, list[str]] = defaultdict(list)
    observed_by_company: dict[str, list[str]] = defaultdict(list)
    for company_id, company in sorted(companies.items()):
        nodes.append({"id": f"company:{company_id}", "kind": "company", "company_id": company_id, "label": company["display_name"], "track_state": company.get("track_state"), "non_affiliation": company.get("non_affiliation")})
    for paradigm_id, paradigm in sorted(paradigms.items()):
        nodes.append({"id": f"paradigm:{paradigm_id}", "kind": "paradigm", "paradigm_id": paradigm_id, "label": paradigm["display_name"], "state": "POLICY_CONFIRMED"})
    for record in repositories:
        if not isinstance(record, dict):
            raise ExperienceGraphError("Invalid census repository record")
        full_name = record.get("repository")
        visibility = record.get("visibility")
        if not isinstance(full_name, str) or visibility not in {"public", "private", "internal"}:
            raise ExperienceGraphError("Invalid census repository identity")
        evidence = repository_metadata.get(full_name, {})
        repo_id = f"repo:{full_name}"
        nodes.append({"id": repo_id, "kind": "repository", "repository": full_name, "visibility": visibility, "classification": record.get("classification"), "promotion_state": evidence.get("promotion_state", "UNCLASSIFIED"), "evidence_level": evidence.get("skill_innovation_level"), "provenance_state": evidence.get("provenance_state", "UNCLASSIFIED")})
        company_id = _resolve_company(full_name, repository_metadata, company_aliases)
        if company_id is not None:
            observed_by_company[company_id].append(full_name)
            edges.append({"source": repo_id, "target": f"company:{company_id}", "relationship": "addresses-company-challenge"})
        for paradigm_id in _resolve_paradigms(full_name, paradigms):
            paradigms[paradigm_id]["repositories"].append(full_name)
            edges.append({"source": repo_id, "target": f"paradigm:{paradigm_id}", "relationship": "expresses-paradigm"})
        prefix = _family_prefix(repository_name(full_name), generic_prefixes)
        if prefix is not None:
            family_members[prefix].append(full_name)
    flagship_records = flagships.get("flagships")
    if not isinstance(flagship_records, list):
        raise ExperienceGraphError("Flagship registry has no flagships list")
    compiled_flagships: list[dict[str, Any]] = []
    for flagship in flagship_records:
        if not isinstance(flagship, dict) or not isinstance(flagship.get("system_id"), str):
            raise ExperienceGraphError("Invalid flagship record")
        system_id = flagship["system_id"]
        compiled = {"system_id": system_id, "repository": flagship.get("repository"), "level": flagship.get("level"), "state": flagship.get("state"), "public_surface": flagship.get("public_surface"), "role": flagship.get("role")}
        compiled_flagships.append(compiled)
        nodes.append({"id": f"flagship:{system_id}", "kind": "flagship", **compiled})
        repository = flagship.get("repository")
        if isinstance(repository, str):
            edges.append({"source": f"flagship:{system_id}", "target": f"repo:{repository}", "relationship": "implemented-by"})
    company_output = []
    for company_id, company in sorted(companies.items()):
        observed = sorted(set(observed_by_company.get(company_id, [])))
        company_output.append({"company_id": company_id, "display_name": company["display_name"], "track_state": company.get("track_state"), "catalog_repository_count": len(company["repositories"]), "observed_repository_count": len(observed), "observed_repositories": observed, "non_affiliation": company.get("non_affiliation")})
    claimed_aliases = {alias for values in company_aliases.values() for alias in values} | {alias for paradigm in paradigms.values() for alias in paradigm["aliases"]}
    family_candidates = [{"family_id": prefix, "state": policy.get("unknown_family_policy", "DISCOVERED_UNCLASSIFIED_REVIEW_REQUIRED"), "repository_count": len(members), "repositories": sorted(members)} for prefix, members in sorted(family_members.items()) if len(members) >= minimum_family_size and prefix not in claimed_aliases]
    public_nodes = [public for node in nodes if (public := _public_node(node))]
    public_ids = {node["id"] for node in public_nodes}
    public_edges = [edge for edge in edges if edge["source"] in public_ids and edge["target"] in public_ids]
    source_digests = {"census": digest(census), "companies": digest(companies), "flagships": digest(flagships), "policy": digest(policy)}
    payload: dict[str, Any] = {"schema": "glaciereq.live-experience-graph.v1", "source_digests": source_digests, "truth_boundary": {"inventory_is_not_authorship": True, "inventory_is_not_runtime_proof": True, "company_mapping_does_not_imply_affiliation": True, "private_repository_names_omitted_from_public_graph": True, "unknown_families_require_review": True}, "counts": {"repositories": len(repositories), "companies": len(company_output), "flagships": len(compiled_flagships), "confirmed_paradigms": len(paradigms), "unclassified_family_candidates": len(family_candidates)}, "companies": company_output, "flagships": compiled_flagships, "paradigms": [{"paradigm_id": paradigm_id, "display_name": paradigm["display_name"], "repository_count": len(set(paradigm["repositories"])), "repositories": sorted(set(paradigm["repositories"]))} for paradigm_id, paradigm in sorted(paradigms.items())], "family_candidates": family_candidates, "graph": {"internal": {"nodes": nodes, "edges": edges}, "public": {"nodes": public_nodes, "edges": public_edges}}}
    payload["snapshot_id"] = digest(payload)
    return payload


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile company, flagship, and paradigm projections from live inventory")
    parser.add_argument("--census", type=Path, default=DEFAULT_CENSUS)
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    parser.add_argument("--flagships", type=Path, default=DEFAULT_FLAGSHIPS)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        census = _load_json(args.census.resolve())
        company_index = _load_json(args.companies.resolve())
        companies, repository_metadata = load_company_catalog(ROOT, company_index)
        flagships = _load_json(args.flagships.resolve())
        policy = _load_json(args.policy.resolve())
        graph = build_experience_graph(census=census, companies=companies, repository_metadata=repository_metadata, flagships=flagships, policy=policy)
        write_atomic(args.output.resolve(), graph)
    except ExperienceGraphError as exc:
        print(f"Experience graph discovery failed closed: {exc}")
        return 1
    print(f"Experience graph compiled: snapshot={graph['snapshot_id']} repositories={graph['counts']['repositories']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
