from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from google.protobuf import json_format, text_format

from . import readme_mesh_pb2

BEGIN_MARKER = "<!-- README-MESH:BEGIN -->"
END_MARKER = "<!-- README-MESH:END -->"
REQUIRED_AUDIENCES = {
    readme_mesh_pb2.RECRUITER,
    readme_mesh_pb2.EXPERT,
    readme_mesh_pb2.AI_AGENT,
}
AUDIENCE_HEADINGS = {
    readme_mesh_pb2.RECRUITER: "For recruiters and non-specialists",
    readme_mesh_pb2.EXPERT: "For senior engineers and domain experts",
    readme_mesh_pb2.AI_AGENT: "For AI systems and toolchains",
}
RELATION_LABELS = {
    readme_mesh_pb2.ORCHESTRATES: "orchestrates",
    readme_mesh_pb2.VERIFIES: "verifies",
    readme_mesh_pb2.PROVIDES_CAPABILITY: "provides capability to",
    readme_mesh_pb2.CONSUMES: "consumes",
    readme_mesh_pb2.EXTENDS: "extends",
    # Retained in the enum only for v1 protobuf wire compatibility. Active mesh
    # validation rejects it before any binary/ProtoJSON projection can be emitted.
    readme_mesh_pb2.GOVERNED_BY: "legacy relation forbidden in active projection",
    readme_mesh_pb2.PERSISTS_RECEIPTS_TO: "persists receipts to",
    readme_mesh_pb2.EXECUTES_THROUGH: "executes through",
}
LEGACY_NON_AUTHORITATIVE_RELATIONS = {readme_mesh_pb2.GOVERNED_BY}
FORBIDDEN_PORTFOLIO_TERMS = (
    "1fdv-",
    "1fda-",
    "family court",
    "casebrain",
    "docket",
    "tro",
    "order for protection",
)


class ReadmeMeshError(ValueError):
    """Raised when the README mesh violates its public evidence contract."""


@dataclass(frozen=True)
class MeshArtifacts:
    binary: bytes
    protojson: str
    textproto: str
    sha256: str


def load_mesh(path: Path) -> readme_mesh_pb2.ReadmeMesh:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mesh = readme_mesh_pb2.ReadmeMesh()
    json_format.ParseDict(payload, mesh, ignore_unknown_fields=False)
    validate_mesh(mesh)
    return mesh


def validate_mesh(mesh: readme_mesh_pb2.ReadmeMesh) -> None:
    if not mesh.schema_version.strip():
        raise ReadmeMeshError("schema_version is required")
    if not mesh.canonical_repo.strip():
        raise ReadmeMeshError("legacy v1 mesh root is required for wire compatibility")

    repositories: dict[str, readme_mesh_pb2.RepositoryNode] = {}
    for node in mesh.repositories:
        repository = node.repository.strip()
        if not repository or "/" not in repository:
            raise ReadmeMeshError(f"invalid repository identity: {repository!r}")
        if repository in repositories:
            raise ReadmeMeshError(f"duplicate repository: {repository}")
        repositories[repository] = node
        _validate_node(node)

    if mesh.canonical_repo not in repositories:
        raise ReadmeMeshError(
            f"legacy v1 mesh root {mesh.canonical_repo!r} is not declared as a repository"
        )

    seen_edges: set[tuple[str, str, int]] = set()
    for edge in mesh.edges:
        if edge.source not in repositories:
            raise ReadmeMeshError(f"edge source is not declared: {edge.source}")
        if edge.target not in repositories:
            raise ReadmeMeshError(f"edge target is not declared: {edge.target}")
        if edge.relation not in RELATION_LABELS:
            raise ReadmeMeshError(
                f"edge {edge.source} -> {edge.target} has unspecified relation"
            )
        if edge.relation in LEGACY_NON_AUTHORITATIVE_RELATIONS:
            raise ReadmeMeshError(
                f"edge {edge.source} -> {edge.target} uses retired GOVERNED_BY; "
                "migrate it to a functional verification/composition relation"
            )
        identity = (edge.source, edge.target, edge.relation)
        if identity in seen_edges:
            raise ReadmeMeshError(f"duplicate edge: {identity}")
        seen_edges.add(identity)
        if not edge.value.strip():
            raise ReadmeMeshError(f"edge {identity} requires a value statement")

    serialized = text_format.MessageToString(mesh).lower()
    found = [
        term
        for term in FORBIDDEN_PORTFOLIO_TERMS
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", serialized)
    ]
    if found:
        raise ReadmeMeshError(
            "public README mesh contains excluded legal/case vocabulary: "
            + ", ".join(found)
        )


def _validate_node(node: readme_mesh_pb2.RepositoryNode) -> None:
    required_strings = {
        "display_name": node.display_name,
        "one_line_purpose": node.one_line_purpose,
        "innovation": node.innovation,
        "evolution": node.evolution,
        "readme_url": node.readme_url,
        "default_branch": node.default_branch,
    }
    missing = [name for name, value in required_strings.items() if not value.strip()]
    if missing:
        raise ReadmeMeshError(
            f"{node.repository} is missing required fields: {', '.join(missing)}"
        )
    if not node.public_portfolio_eligible:
        raise ReadmeMeshError(
            f"{node.repository} is not marked public_portfolio_eligible"
        )
    if not node.capabilities:
        raise ReadmeMeshError(f"{node.repository} requires at least one capability")

    audiences = {section.audience for section in node.sections}
    missing_audiences = REQUIRED_AUDIENCES - audiences
    duplicate_audiences = len(node.sections) != len(audiences)
    if missing_audiences or duplicate_audiences:
        names = [readme_mesh_pb2.Audience.Name(value) for value in missing_audiences]
        raise ReadmeMeshError(
            f"{node.repository} must declare exactly one section per audience; "
            f"missing={names}, duplicate={duplicate_audiences}"
        )

    for section in node.sections:
        if not section.title.strip() or not section.summary.strip():
            raise ReadmeMeshError(
                f"{node.repository} has an incomplete "
                f"{readme_mesh_pb2.Audience.Name(section.audience)} section"
            )
        if not section.highlights:
            raise ReadmeMeshError(
                f"{node.repository} audience section {section.title!r} has no highlights"
            )
        if not section.evidence:
            raise ReadmeMeshError(
                f"{node.repository} audience section {section.title!r} has no evidence"
            )
        for evidence in section.evidence:
            complete = (
                evidence.label.strip()
                and evidence.path.strip()
                and evidence.claim.strip()
            )
            if not complete:
                raise ReadmeMeshError(
                    f"{node.repository} contains incomplete evidence in {section.title!r}"
                )


def build_artifacts(mesh: readme_mesh_pb2.ReadmeMesh) -> MeshArtifacts:
    validate_mesh(mesh)
    binary = mesh.SerializeToString(deterministic=True)
    protojson = json_format.MessageToJson(
        mesh,
        preserving_proto_field_name=True,
        indent=2,
        sort_keys=True,
    )
    textproto = text_format.MessageToString(mesh, as_utf8=True)
    return MeshArtifacts(
        binary=binary,
        protojson=protojson,
        textproto=textproto,
        sha256=hashlib.sha256(binary).hexdigest(),
    )


def write_artifacts(mesh: readme_mesh_pb2.ReadmeMesh, output_dir: Path) -> MeshArtifacts:
    artifacts = build_artifacts(mesh)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "readme_mesh.pb").write_bytes(artifacts.binary)
    (output_dir / "readme_mesh.proto.json").write_text(
        artifacts.protojson + "\n", encoding="utf-8"
    )
    (output_dir / "readme_mesh.textproto").write_text(
        artifacts.textproto, encoding="utf-8"
    )
    (output_dir / "readme_mesh.sha256").write_text(
        f"{artifacts.sha256}  readme_mesh.pb\n", encoding="utf-8"
    )
    return artifacts


def repository_index(
    mesh: readme_mesh_pb2.ReadmeMesh,
) -> Mapping[str, readme_mesh_pb2.RepositoryNode]:
    return {node.repository: node for node in mesh.repositories}


def render_repository_block(
    mesh: readme_mesh_pb2.ReadmeMesh,
    repository: str,
) -> str:
    validate_mesh(mesh)
    nodes = repository_index(mesh)
    try:
        node = nodes[repository]
    except KeyError as exc:
        raise ReadmeMeshError(f"repository is not present in mesh: {repository}") from exc

    lines = [
        BEGIN_MARKER,
        "## Three-audience project map",
        "",
        (
            "This section is generated from the versioned legacy "
            "[README Mesh Protobuf contract]"
            "(https://github.com/GlacierEQ/job-app-helix/blob/main/proto/readme_mesh.proto). "
            "It is a public evidence projection, not a project-direction authority."
        ),
        "",
    ]

    sections = sorted(node.sections, key=lambda section: section.audience)
    for section in sections:
        heading = AUDIENCE_HEADINGS[section.audience]
        lines.extend(
            [
                f"### {heading}",
                "",
                f"**{section.title}.** {section.summary}",
                "",
            ]
        )
        lines.extend(f"- {highlight}" for highlight in section.highlights)
        lines.extend(["", "**Evidence**"])
        lines.extend(
            f"- [{evidence.label}]({evidence.path}) — {evidence.claim}"
            for evidence in section.evidence
        )
        lines.append("")

    lines.extend(
        [
            "### Repository mesh",
            "",
            "| Relationship | Connected repository | Combined value |",
            "|---|---|---|",
        ]
    )
    connected = [
        edge
        for edge in mesh.edges
        if edge.source == repository or edge.target == repository
    ]
    connected.sort(key=lambda edge: (edge.source, edge.target, edge.relation))
    for edge in connected:
        if edge.source == repository:
            other = edge.target
            relationship = RELATION_LABELS[edge.relation]
        else:
            other = edge.source
            relationship = f"receives: {RELATION_LABELS[edge.relation]}"
        other_node = nodes[other]
        lines.append(
            f"| {relationship} | [{other}]({other_node.readme_url}) | {edge.value} |"
        )

    lines.extend(
        [
            "",
            "### Machine-readable contract",
            "",
            "- Legacy Protobuf package: `glaciereq.readme.v1`",
            f"- Mesh schema version: `{mesh.schema_version}`",
            (
                "- Legacy public mesh projection: [`manifests/readme_mesh.json`]"
                "(https://github.com/GlacierEQ/job-app-helix/blob/main/"
                "manifests/readme_mesh.json)"
            ),
            "- APEX project contract: [`schemas/readme_apex.schema.json`]"
            "(https://github.com/GlacierEQ/job-app-helix/blob/main/"
            "schemas/readme_apex.schema.json)",
            "- Binary/ProtoJSON build: "
            "`python -m job_app_helix.readme_mesh_cli build`",
            f"- Repository identity: `{node.repository}`",
            "",
            "```protobuf",
            f'repository: "{node.repository}"',
            f'display_name: "{_escape_proto(node.display_name)}"',
            f'one_line_purpose: "{_escape_proto(node.one_line_purpose)}"',
            "```",
            END_MARKER,
        ]
    )
    return "\n".join(lines)


def apply_block(readme: str, block: str) -> str:
    if BEGIN_MARKER in readme or END_MARKER in readme:
        if readme.count(BEGIN_MARKER) != 1 or readme.count(END_MARKER) != 1:
            raise ReadmeMeshError("README contains malformed README Mesh markers")
        before, remainder = readme.split(BEGIN_MARKER, maxsplit=1)
        _, after = remainder.split(END_MARKER, maxsplit=1)
        before = before.rstrip()
        after = after.lstrip("\n")
        rendered = f"{before}\n\n{block}" if before else block
        if after:
            rendered += f"\n\n{after.rstrip()}"
        return rendered.rstrip() + "\n"

    lines = readme.splitlines()
    insertion_index = _find_insertion_index(lines)
    before = "\n".join(lines[:insertion_index]).rstrip()
    after = "\n".join(lines[insertion_index:]).lstrip()
    if before and after:
        return f"{before}\n\n{block}\n\n{after}\n"
    if before:
        return f"{before}\n\n{block}\n"
    return f"{block}\n\n{after}\n"


def _find_insertion_index(lines: list[str]) -> int:
    if not lines:
        return 0
    index = 1 if lines[0].startswith("# ") else 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("[![") or stripped.startswith("!["):
            index += 1
            continue
        if stripped.startswith(">") or stripped.startswith("**"):
            index += 1
            continue
        break
    return index


def render_all_blocks(
    mesh: readme_mesh_pb2.ReadmeMesh,
) -> Iterable[tuple[str, str]]:
    for node in mesh.repositories:
        yield node.repository, render_repository_block(mesh, node.repository)


def _escape_proto(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
