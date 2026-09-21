"""Deterministic deep-internal discovery for crystallization crawl receipts.

This module does not infer runtime behavior from names. It classifies every
accounted repository path into structural groups and path-derived semantic
signals so hidden capability surfaces (for example harnesses buried outside
conventional test directories) remain discoverable.

Repository-native source remains authoritative for implementation semantics.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import PurePosixPath
from typing import Any

SCHEMA = "glaciereq.crystallization-internal-discovery.v1"

# Multi-label taxonomy. A path may legitimately participate in several classes.
# These are discovery/routing signals, never implementation or runtime proof.
ROLE_RULES: tuple[tuple[str, str, str, frozenset[str]], ...] = (
    ("verification", "harnesses", "verification_harness", frozenset({"harness", "harnesses", "testbed", "rig"})),
    ("verification", "evaluation", "evaluation", frozenset({"eval", "evals", "evaluation", "evaluator", "judge", "grading"})),
    ("verification", "benchmarks", "benchmark", frozenset({"benchmark", "benchmarks", "bench"})),
    ("verification", "replay", "replay", frozenset({"replay", "replays"})),
    ("verification", "fuzzing", "fuzzing", frozenset({"fuzz", "fuzzer", "fuzzing"})),
    ("verification", "chaos_faults", "chaos_testing", frozenset({"chaos", "fault", "faults", "faultinject"})),
    ("verification", "simulation", "simulation", frozenset({"simulation", "simulator", "simulations"})),
    ("agentic", "agents_workers", "agent_runtime", frozenset({"agent", "agents", "worker", "workers", "swarm", "orchestrator", "orchestration"})),
    ("agentic", "skills_capabilities", "skill_capability", frozenset({"skill", "skills", "capability", "capabilities"})),
    ("orchestration", "pipelines_workflows", "pipeline_workflow", frozenset({"pipeline", "pipelines", "workflow", "workflows", "automation", "automations", "scheduler", "schedule"})),
    ("integration", "mcp", "mcp_surface", frozenset({"mcp"})),
    ("integration", "connectors_bridges", "connector_bridge", frozenset({"connector", "connectors", "integration", "integrations", "bridge", "bridges", "gateway"})),
    ("integration", "adapters_providers", "adapter_provider", frozenset({"adapter", "adapters", "provider", "providers"})),
    ("integration", "apis_rpc", "api_rpc", frozenset({"api", "apis", "graphql", "rpc", "jsonrpc", "grpc"})),
    ("integration", "tools", "tool_surface", frozenset({"tool", "tools", "tooling"})),
    ("cognition", "prompts", "prompt", frozenset({"prompt", "prompts", "systemprompt"})),
    ("cognition", "templates", "template", frozenset({"template", "templates"})),
    ("cognition", "policies_rules", "policy_rule", frozenset({"policy", "policies", "rule", "rules", "guardrail", "guardrails"})),
    ("cognition", "memory_context", "memory_context", frozenset({"memory", "memories", "context", "contexts", "vector", "vectors", "embedding", "embeddings"})),
    ("cognition", "research_retrieval", "research_retrieval", frozenset({"research", "retrieval", "retrieve", "rag", "knowledge"})),
    ("reality", "evidence_provenance", "evidence_provenance", frozenset({"evidence", "provenance", "receipt", "receipts", "ledger", "ledgers", "trace", "traces"})),
    ("reality", "schemas_contracts", "schema_contract", frozenset({"schema", "schemas", "contract", "contracts", "manifest", "manifests", "registry", "registries"})),
    ("reality", "data_datasets", "data_dataset", frozenset({"data", "dataset", "datasets", "corpus", "corpora"})),
    ("persistence", "databases_migrations", "database_migration", frozenset({"db", "database", "databases", "sql", "migration", "migrations", "supabase", "postgres", "postgresql", "sqlite"})),
    ("runtime", "services_servers", "service_server", frozenset({"service", "services", "server", "servers", "daemon", "runtime", "runtimes"})),
    ("runtime", "cli_commands", "cli_command", frozenset({"cli", "command", "commands", "bin"})),
    ("product", "ui_dashboards", "ui_dashboard", frozenset({"ui", "frontend", "dashboard", "dashboards", "webapp"})),
    ("operations", "deployment_infrastructure", "deployment_infrastructure", frozenset({"deploy", "deployment", "deployments", "infra", "infrastructure", "terraform", "docker", "kubernetes", "k8s", "helm"})),
    ("operations", "observability", "observability", frozenset({"observability", "telemetry", "metric", "metrics", "logging", "monitor", "monitoring"})),
    ("security", "security_identity", "security_identity", frozenset({"security", "auth", "oauth", "permission", "permissions", "secret", "secrets", "identity"})),
    ("domain", "legal_case", "legal_case", frozenset({"legal", "case", "cases", "docket", "dockets", "litigation"})),
    ("documents", "document_processing", "document_processing", frozenset({"document", "documents", "pdf", "transcript", "transcripts", "transcription"})),
)

HIGH_VALUE_ROLES = frozenset(
    {
        "verification_harness",
        "evaluation",
        "benchmark",
        "replay",
        "fuzzing",
        "chaos_testing",
        "simulation",
        "agent_runtime",
        "skill_capability",
        "pipeline_workflow",
        "mcp_surface",
        "connector_bridge",
        "adapter_provider",
        "api_rpc",
        "tool_surface",
        "prompt",
        "memory_context",
        "evidence_provenance",
        "schema_contract",
        "database_migration",
        "service_server",
        "deployment_infrastructure",
        "observability",
        "security_identity",
        "legal_case",
    }
)

CONVENTIONAL_HIGH_VALUE_ROOTS = frozenset(
    {
        "test",
        "tests",
        "testing",
        "eval",
        "evals",
        "evaluation",
        "evaluations",
        "benchmark",
        "benchmarks",
        "harness",
        "harnesses",
        "skills",
        "agents",
        "tools",
        "scripts",
        "workflows",
        ".github",
    }
)

ROLE_STRUCTURE_HINTS: dict[str, tuple[str, ...]] = {
    "verification_harness": ("MIND_CAPABILITY",),
    "evaluation": ("MIND_CAPABILITY",),
    "benchmark": ("MIND_CAPABILITY",),
    "replay": ("MIND_CAPABILITY",),
    "fuzzing": ("MIND_CAPABILITY",),
    "chaos_testing": ("MIND_CAPABILITY",),
    "simulation": ("MIND_CAPABILITY",),
    "skill_capability": ("MIND_CAPABILITY",),
    "pipeline_workflow": ("MIND_CAPABILITY",),
    "prompt": ("MIND_CAPABILITY",),
    "template": ("MIND_CAPABILITY",),
    "policy_rule": ("MIND_CAPABILITY",),
    "research_retrieval": ("MIND_CAPABILITY",),
    "agent_runtime": ("CAPITAL_A",),
    "service_server": ("CAPITAL_A",),
    "cli_command": ("CAPITAL_A",),
    "mcp_surface": ("REALITY_SOURCE",),
    "connector_bridge": ("REALITY_SOURCE",),
    "adapter_provider": ("REALITY_SOURCE",),
    "api_rpc": ("REALITY_SOURCE",),
    "tool_surface": ("REALITY_SOURCE",),
    "memory_context": ("REALITY_SOURCE", "MIND_CAPABILITY"),
    "evidence_provenance": ("REALITY_SOURCE",),
    "schema_contract": ("REALITY_SOURCE", "MIND_CAPABILITY"),
    "data_dataset": ("REALITY_SOURCE",),
    "database_migration": ("REALITY_SOURCE",),
    "legal_case": ("MATTER_MISSION",),
}

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _path_tokens(path: str) -> set[str]:
    expanded = _CAMEL_BOUNDARY.sub(" ", path)
    tokens = {part for part in _TOKEN_SPLIT.split(expanded.casefold()) if part}
    # Preserve full normalized segments as additional signals.
    for part in PurePosixPath(path).parts:
        normalized = _TOKEN_SPLIT.sub("", part.casefold())
        if normalized:
            tokens.add(normalized)
    return tokens


def _classification_records(tokens: set[str]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for category, subcategory, role, terms in ROLE_RULES:
        if not tokens.intersection(terms):
            continue
        key = (category, subcategory, role)
        if key in seen:
            continue
        seen.add(key)
        matches.append(
            {
                "category": category,
                "subcategory": subcategory,
                "role": role,
            }
        )
    return matches


def classify_path(path: str, *, surface_flags: list[str] | None = None) -> dict[str, Any]:
    """Classify one repository path without promoting name signals to behavior proof."""
    pure = PurePosixPath(path)
    parts = pure.parts
    tokens = _path_tokens(path)
    classifications = _classification_records(tokens)
    roles = [item["role"] for item in classifications]
    structures = sorted(
        {
            structure
            for role in roles
            for structure in ROLE_STRUCTURE_HINTS.get(role, ())
        }
    )
    parent = pure.parent.as_posix()
    if parent == ".":
        parent = "__root__"
    top_level = parts[0] if len(parts) > 1 else "__root__"
    high_value = bool(HIGH_VALUE_ROLES.intersection(roles))
    unusual_high_value = bool(
        high_value
        and top_level.casefold() not in CONVENTIONAL_HIGH_VALUE_ROOTS
    )
    return {
        "path": path,
        "parent_group": parent,
        "top_level_group": top_level,
        "path_depth": len(parts),
        "classifications": classifications,
        "semantic_roles": sorted(set(roles)),
        "architecture_structure_hints": structures,
        "surface_flags": sorted(set(surface_flags or [])),
        "high_value_discovery": high_value,
        "unusual_high_value_location": unusual_high_value,
    }


def _group_inventory(classified_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    direct: Counter[str] = Counter()
    descendants: Counter[str] = Counter()
    for item in classified_files:
        pure = PurePosixPath(item["path"])
        parent_parts = pure.parts[:-1]
        direct_parent = "/".join(parent_parts) if parent_parts else "__root__"
        direct[direct_parent] += 1
        if not parent_parts:
            descendants["__root__"] += 1
            continue
        descendants["__root__"] += 1
        for depth in range(1, len(parent_parts) + 1):
            descendants["/".join(parent_parts[:depth])] += 1

    groups = []
    for path in sorted(set(direct) | set(descendants), key=lambda value: (value.count("/"), value.casefold())):
        depth = 0 if path == "__root__" else path.count("/") + 1
        groups.append(
            {
                "path": path,
                "depth": depth,
                "direct_file_count": direct[path],
                "descendant_file_count": descendants[path],
            }
        )
    return groups


def build_repository_inventory(repository: dict[str, Any]) -> dict[str, Any]:
    files = repository.get("files")
    if not isinstance(files, list):
        files = []

    classified_files: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    subcategory_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    structure_counts: Counter[str] = Counter()
    top_level_counts: Counter[str] = Counter()
    harness_paths: list[str] = []
    high_value_paths: list[dict[str, Any]] = []
    unusual_high_value_paths: list[dict[str, Any]] = []

    for raw in files:
        if not isinstance(raw, dict):
            continue
        path = raw.get("path")
        if not isinstance(path, str) or not path:
            continue
        classified = classify_path(
            path,
            surface_flags=raw.get("surface_flags")
            if isinstance(raw.get("surface_flags"), list)
            else [],
        )
        classified["blob_sha"] = raw.get("blob_sha")
        classified["content_state"] = raw.get("content_state")
        classified_files.append(classified)
        top_level_counts[classified["top_level_group"]] += 1

        for record in classified["classifications"]:
            category_counts[record["category"]] += 1
            subcategory_counts[f"{record['category']}.{record['subcategory']}"] += 1
            role_counts[record["role"]] += 1
        for structure in classified["architecture_structure_hints"]:
            structure_counts[structure] += 1

        if "verification_harness" in classified["semantic_roles"]:
            harness_paths.append(path)
        if classified["high_value_discovery"]:
            value = {
                "path": path,
                "roles": classified["semantic_roles"],
                "group": classified["parent_group"],
                "structure_hints": classified["architecture_structure_hints"],
            }
            high_value_paths.append(value)
            if classified["unusual_high_value_location"]:
                unusual_high_value_paths.append(value)

    groups = _group_inventory(classified_files)
    declared_file_count = repository.get("file_count")
    if not isinstance(declared_file_count, int) or declared_file_count < 0:
        declared_file_count = len(classified_files)
    all_accounted = bool(repository.get("all_files_accounted"))
    structural_complete = all_accounted and len(classified_files) == declared_file_count
    semantic_unclassified = sum(
        1 for item in classified_files if not item["semantic_roles"]
    )

    return {
        "schema": SCHEMA,
        "repository": repository.get("repository"),
        "position": repository.get("position"),
        "classification_basis": "COMPLETE_GIT_TREE_PATHS_PLUS_EXISTING_SURFACE_FLAGS",
        "proof_boundary": {
            "path_classification_is_discovery_not_behavior_proof": True,
            "architecture_structure_values_are_routing_hints_not_primary_placement": True,
            "repository_native_source_remains_implementation_authority": True,
        },
        "structural_discovery_complete": structural_complete,
        "declared_file_count": declared_file_count,
        "classified_path_count": len(classified_files),
        "semantic_unclassified_file_count": semantic_unclassified,
        "group_count": len(groups),
        "max_path_depth": max(
            (item["path_depth"] for item in classified_files),
            default=0,
        ),
        "top_level_groups": [
            {"group": group, "file_count": count}
            for group, count in sorted(
                top_level_counts.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ],
        "category_counts": dict(sorted(category_counts.items())),
        "subcategory_counts": dict(sorted(subcategory_counts.items())),
        "semantic_role_counts": dict(sorted(role_counts.items())),
        "architecture_structure_hint_counts": dict(sorted(structure_counts.items())),
        "harness_count": len(harness_paths),
        "harness_paths": sorted(harness_paths, key=str.casefold),
        "high_value_internal_count": len(high_value_paths),
        "high_value_internal_paths": sorted(
            high_value_paths,
            key=lambda item: item["path"].casefold(),
        ),
        "unusual_high_value_count": len(unusual_high_value_paths),
        "unusual_high_value_paths": sorted(
            unusual_high_value_paths,
            key=lambda item: item["path"].casefold(),
        ),
        "groups": groups,
        "files": classified_files,
    }


def summarize_repository(
    repository: dict[str, Any],
    *,
    path_limit: int = 64,
    group_limit: int = 64,
) -> dict[str, Any]:
    """Return the compact Monolith projection while preserving a complete private inventory."""
    inventory = build_repository_inventory(repository)
    high_value = inventory["high_value_internal_paths"]
    unusual = inventory["unusual_high_value_paths"]
    groups = inventory["groups"]
    harnesses = inventory["harness_paths"]
    return {
        "schema": SCHEMA,
        "classification_basis": inventory["classification_basis"],
        "structural_discovery_complete": inventory["structural_discovery_complete"],
        "classified_path_count": inventory["classified_path_count"],
        "semantic_unclassified_file_count": inventory["semantic_unclassified_file_count"],
        "group_count": inventory["group_count"],
        "max_path_depth": inventory["max_path_depth"],
        "top_level_groups": inventory["top_level_groups"],
        "category_counts": inventory["category_counts"],
        "subcategory_counts": inventory["subcategory_counts"],
        "semantic_role_counts": inventory["semantic_role_counts"],
        "architecture_structure_hint_counts": inventory["architecture_structure_hint_counts"],
        "harness_count": inventory["harness_count"],
        "harness_paths": harnesses[:path_limit],
        "harness_paths_truncated": len(harnesses) > path_limit,
        "high_value_internal_count": inventory["high_value_internal_count"],
        "high_value_internal_paths": high_value[:path_limit],
        "high_value_internal_paths_truncated": len(high_value) > path_limit,
        "unusual_high_value_count": inventory["unusual_high_value_count"],
        "unusual_high_value_paths": unusual[:path_limit],
        "unusual_high_value_paths_truncated": len(unusual) > path_limit,
        "group_hierarchy": groups[:group_limit],
        "group_hierarchy_truncated": len(groups) > group_limit,
        "complete_private_inventory": "private crystallization internal-inventory artifact",
        "proof_boundary": inventory["proof_boundary"],
    }


def build_estate_internal_inventory(receipt: dict[str, Any]) -> dict[str, Any]:
    repositories = receipt.get("repositories")
    if not isinstance(repositories, list):
        raise ValueError("crawl receipt repositories must be a list")
    inventories = [
        build_repository_inventory(repo)
        for repo in repositories
        if isinstance(repo, dict)
    ]
    complete = bool(inventories) and all(
        item["structural_discovery_complete"] for item in inventories
    )
    return {
        "schema": SCHEMA,
        "source_schema": receipt.get("schema"),
        "source_receipt_digest": receipt.get("receipt_digest"),
        "accessible_repository_count": receipt.get("accessible_repository_count"),
        "selected_repository_count": receipt.get("selected_repository_count"),
        "selection_start": receipt.get("selection_start"),
        "selection_limit": receipt.get("selection_limit"),
        "hourly_shard_index": receipt.get("hourly_shard_index"),
        "repository_inventory_count": len(inventories),
        "structural_discovery_complete_for_selected_repositories": complete,
        "repositories": inventories,
        "proof_boundary": {
            "all_paths_are_accounted_when_structural_discovery_complete_is_true": True,
            "path_labels_do_not_establish_runtime_or_behavior": True,
            "deep_source_semantics_still_require_source_or_runtime_inspection": True,
        },
    }
