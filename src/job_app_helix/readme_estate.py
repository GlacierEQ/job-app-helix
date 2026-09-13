from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import yaml

START_MARKER = "<!-- glacier-eq-protocol:start -->"
END_MARKER = "<!-- glacier-eq-protocol:end -->"
SCHEMA = "glacier-eq.readme.machine-mesh/v1"
GENERATOR = "GlacierEQ/job-app-helix"
GENERATOR_CONTRACT = "estate-machine-v1"
MONOLITH = "GlacierEQ/monolith"


class EstateReadmeError(ValueError):
    """Raised when a README machine contract cannot be safely adopted or generated."""


class ReadmeAction(StrEnum):
    ADOPT = "ADOPT"
    CREATE_README = "CREATE_README"
    INSERT_BLOCK = "INSERT_BLOCK"
    NO_CHANGE = "NO_CHANGE"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    ARCHIVED_READ_ONLY = "ARCHIVED_READ_ONLY"


@dataclass(frozen=True, slots=True)
class ClassificationEvidence:
    primary_home: str | None = None
    evidence_path: str | None = None
    evidence_blob_sha: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class ReadmePlan:
    repository: str
    action: ReadmeAction
    reason: str
    readme: str | None = None
    contract: Mapping[str, Any] | None = None


def extract_machine_block(readme: str) -> str | None:
    starts = readme.count(START_MARKER)
    ends = readme.count(END_MARKER)
    if starts == 0 and ends == 0:
        return None
    if starts != 1 or ends != 1:
        raise EstateReadmeError(
            f"expected exactly one machine block; starts={starts} ends={ends}"
        )
    start = readme.index(START_MARKER) + len(START_MARKER)
    end = readme.index(END_MARKER, start)
    enclosed = readme[start:end]
    match = re.search(r"```(?:yaml|yml)\s*\n(.*?)\n```", enclosed, re.DOTALL)
    if match is None:
        raise EstateReadmeError("machine block must contain one fenced YAML payload")
    return match.group(1).strip()


def parse_machine_contract(
    readme: str,
    *,
    expected_repository: str | None = None,
) -> dict[str, Any] | None:
    payload = extract_machine_block(readme)
    if payload is None:
        return None
    parsed = yaml.safe_load(payload)
    if not isinstance(parsed, dict):
        raise EstateReadmeError("machine block payload must be a mapping")
    if parsed.get("schema") != SCHEMA:
        raise EstateReadmeError(
            f"unsupported schema {parsed.get('schema')!r}; expected {SCHEMA!r}"
        )
    repository = parsed.get("repository")
    machine = parsed.get("machine")
    if not isinstance(repository, dict):
        raise EstateReadmeError("repository mapping is required")
    if not isinstance(machine, dict):
        raise EstateReadmeError("machine mapping is required")
    repository_id = repository.get("id")
    if not isinstance(repository_id, str) or "/" not in repository_id:
        raise EstateReadmeError("repository.id must be an owner/repository identity")
    if expected_repository is not None and repository_id != expected_repository:
        raise EstateReadmeError(
            f"repository identity mismatch: manifest={repository_id!r} "
            f"expected={expected_repository!r}"
        )
    kind = machine.get("repository_kind")
    if not isinstance(kind, str) or not kind.strip():
        raise EstateReadmeError("machine.repository_kind is required")
    return parsed


def repository_kind_from_primary_home(primary_home: str | None) -> str:
    if not primary_home:
        return "migration-residue"
    if primary_home.startswith("REALITY_SOURCE."):
        return "source-or-tool-system"
    if primary_home.startswith("MIND_CAPABILITY."):
        return "reusable-capability"
    if primary_home.startswith("CAPITAL_A."):
        return "acting-runtime-or-agent"
    return "classified-estate-resource"


def mesh_coordinates(primary_home: str | None) -> tuple[str, str]:
    if not primary_home:
        return "migration-residue", "unresolved-primary-home"
    pieces = [part for part in primary_home.split(".") if part]
    branch = pieces[0].lower().replace("_", "-")
    subcategory = "-".join(pieces[1:]).lower().replace("_", "-") or "root"
    return branch, subcategory


_ENTRYPOINT_RULES: tuple[tuple[str, str, str], ...] = (
    ("pyproject.toml", "package-contract", "inspect-before-use"),
    ("package.json", "package-contract", "inspect-before-use"),
    ("Cargo.toml", "package-contract", "inspect-before-use"),
    ("go.mod", "package-contract", "inspect-before-use"),
    ("Dockerfile", "container-contract", "inspect-before-build"),
    ("docker-compose.yml", "container-orchestration", "inspect-before-use"),
    ("compose.yml", "container-orchestration", "inspect-before-use"),
    ("src", "source-area", "inspect-before-use"),
    ("scripts", "script-area", "inspect-before-use"),
    ("tests", "test-area", "run-before-reliance"),
    ("machine", "machine-contract-area", "read-first"),
    ("docs", "documentation-area", "read-as-context"),
    ("GENIUS.yaml", "capability-contract", "read-first"),
    ("ROLE.yaml", "role-contract", "read-first"),
    ("MESH.yaml", "mesh-contract", "read-first"),
    ("INDEX.md", "navigation-document", "read-first"),
)


def infer_entrypoints(root_paths: Iterable[str]) -> list[dict[str, str]]:
    normalized = {path.rstrip("/") for path in root_paths}
    return [
        {"kind": kind, "path": path, "policy": policy}
        for path, kind, policy in _ENTRYPOINT_RULES
        if path in normalized
    ]


def _canonical_without_digest(contract: Mapping[str, Any]) -> bytes:
    clone = json.loads(json.dumps(contract))
    provenance = clone.get("provenance")
    if isinstance(provenance, dict):
        provenance.pop("contract_digest", None)
    return json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")


def bind_contract_digest(contract: Mapping[str, Any]) -> dict[str, Any]:
    clone: dict[str, Any] = json.loads(json.dumps(contract))
    provenance = clone.setdefault("provenance", {})
    if not isinstance(provenance, dict):
        raise EstateReadmeError("provenance must be a mapping")
    provenance["contract_digest"] = hashlib.sha256(_canonical_without_digest(clone)).hexdigest()
    return clone


def build_generated_contract(
    *,
    repository: str,
    default_branch: str,
    root_paths: Iterable[str],
    classification: ClassificationEvidence = ClassificationEvidence(),
    repository_url: str | None = None,
    fork: bool = False,
) -> dict[str, Any]:
    branch, subcategory = mesh_coordinates(classification.primary_home)
    repository_url = repository_url or f"https://github.com/{repository}"
    contract: dict[str, Any] = {
        "schema": SCHEMA,
        "repository": {
            "id": repository,
            "url": repository_url,
            "readme_contract": GENERATOR_CONTRACT,
            "default_branch": default_branch,
        },
        "machine": {
            "repository_kind": (
                "fork-or-derived-source"
                if fork
                else repository_kind_from_primary_home(classification.primary_home)
            ),
            "public_api": "inspect-declared-entrypoints",
            "protocol_files": [],
            "entrypoints": infer_entrypoints(root_paths),
        },
        "mesh": {
            "primary_home": classification.primary_home,
            "branch": branch,
            "subcategory": subcategory,
            "routing": [
                {
                    "relation": "estate-map",
                    "target": MONOLITH,
                    "url": f"https://github.com/{MONOLITH}",
                }
            ],
            "boundaries": [
                "routing-does-not-transfer-source-code-evidence-deployment-or-lifecycle-authority",
                "generated-contract-is-a-source-index-not-a-runtime-or-provider-receipt",
                "implementation-and-provider-state-require-independent-evidence",
            ],
        },
        "provenance": {
            "generated_by": GENERATOR,
            "generator_contract": GENERATOR_CONTRACT,
            "classification_source": MONOLITH if classification.primary_home else None,
            "classification_evidence_path": classification.evidence_path,
            "classification_evidence_blob_sha": classification.evidence_blob_sha,
            "classification_status": classification.status,
        },
    }
    return bind_contract_digest(contract)


def render_machine_block(contract: Mapping[str, Any]) -> str:
    bound = bind_contract_digest(contract)
    payload = yaml.safe_dump(
        bound,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip()
    return "\n".join(
        [
            "### Machine–Mesh Protocol Manifest",
            "",
            START_MARKER,
            "```yaml",
            payload,
            "```",
            END_MARKER,
        ]
    )


def append_missing_block(readme: str, block: str) -> str:
    if START_MARKER in readme or END_MARKER in readme:
        raise EstateReadmeError("refusing to overwrite an existing machine block")
    base = readme.rstrip()
    if not base:
        return block.rstrip() + "\n"
    return f"{base}\n\n{block.rstrip()}\n"


def minimal_readme(repository: str, block: str) -> str:
    slug = repository.rsplit("/", 1)[-1]
    return (
        f"# {slug}\n\n"
        "Repository-local source remains authoritative. The machine contract below is an "
        "estate routing/index surface and does not promote runtime or provider state.\n\n"
        f"{block.rstrip()}\n"
    )


def plan_readme(
    *,
    repository: str,
    current_readme: str | None,
    default_branch: str,
    root_paths: Iterable[str],
    classification: ClassificationEvidence = ClassificationEvidence(),
    repository_url: str | None = None,
    archived: bool = False,
    fork: bool = False,
) -> ReadmePlan:
    if current_readme is not None:
        try:
            existing = parse_machine_contract(
                current_readme,
                expected_repository=repository,
            )
        except (EstateReadmeError, yaml.YAMLError) as exc:
            return ReadmePlan(
                repository=repository,
                action=ReadmeAction.REPAIR_REQUIRED,
                reason=str(exc),
            )
        if existing is not None:
            return ReadmePlan(
                repository=repository,
                action=(ReadmeAction.ARCHIVED_READ_ONLY if archived else ReadmeAction.ADOPT),
                reason="valid existing machine contract preserved",
                readme=current_readme,
                contract=existing,
            )

    contract = build_generated_contract(
        repository=repository,
        default_branch=default_branch,
        root_paths=root_paths,
        classification=classification,
        repository_url=repository_url,
        fork=fork,
    )
    block = render_machine_block(contract)
    if archived:
        return ReadmePlan(
            repository=repository,
            action=ReadmeAction.ARCHIVED_READ_ONLY,
            reason="archived repository cannot be mutated; generated contract retained in rollout plan",
            contract=contract,
        )
    if current_readme is None:
        return ReadmePlan(
            repository=repository,
            action=ReadmeAction.CREATE_README,
            reason="README missing; create minimal source-preserving README",
            readme=minimal_readme(repository, block),
            contract=contract,
        )
    return ReadmePlan(
        repository=repository,
        action=ReadmeAction.INSERT_BLOCK,
        reason="README exists without universal machine contract",
        readme=append_missing_block(current_readme, block),
        contract=contract,
    )
