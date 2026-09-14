from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from . import readme_mesh_pb2
from .readme_mesh import RELATION_LABELS, ReadmeMeshError, repository_index, validate_mesh

BEGIN_MARKER = "<!-- README-FOUR-DEPTH:BEGIN -->"
END_MARKER = "<!-- README-FOUR-DEPTH:END -->"


@dataclass(frozen=True, slots=True)
class LayerTitles:
    recruiter: str
    master: str
    machine: str
    mesh: str


@dataclass(frozen=True, slots=True)
class PresentationWeight:
    recruiter_highlights: int
    recruiter_evidence: int
    master_highlights: int | None
    master_evidence: int | None


def _capability_text(node: readme_mesh_pb2.RepositoryNode) -> str:
    return " ".join(node.capabilities).lower()


def choose_titles(node: readme_mesh_pb2.RepositoryNode) -> LayerTitles:
    """Choose informative, project-native headings without altering source facts."""

    name = node.display_name.strip() or node.repository.rsplit("/", 1)[-1]
    caps = _capability_text(node)

    if any(term in caps for term in ("verification", "evidence", "proof", "receipt")):
        recruiter = "Proof You Can Actually Open"
        master = "Where the Claim Meets the Workbench"
    elif any(term in caps for term in ("orchestration", "control plane", "control", "workflow")):
        recruiter = "Make the Moving Parts Behave"
        master = "Inside the Control Loop"
    elif any(term in caps for term in ("memory", "continuity", "persistence")):
        recruiter = "Remember Without Rewriting History"
        master = "What Persistence Has to Prove"
    elif any(term in caps for term in ("governance", "policy", "authority")):
        recruiter = "Rules That Actually Run"
        master = "Where Policy Becomes Execution"
    elif any(term in caps for term in ("agent", "assistant", "autonomy")):
        recruiter = "An Agent With a Job, Not a Costume"
        master = "Inside the Decision Loop"
    elif any(term in caps for term in ("data", "source", "dataset", "record")):
        recruiter = "The Source Beneath the System"
        master = "How the Record Stays Trustworthy"
    elif any(term in caps for term in ("browser", "web", "navigation")):
        recruiter = "From Page to Proof"
        master = "What the Browser Is Allowed to Do"
    elif any(term in caps for term in ("security", "auth", "identity", "provenance")):
        recruiter = "Trust Has to Come From Somewhere"
        master = "The Boundary Is the Architecture"
    else:
        recruiter = f"{name}: What Changes When It Works"
        master = f"Inside {name}: The Decisions That Matter"

    return LayerTitles(
        recruiter=recruiter,
        master=master,
        machine=f"{name}, Without the Guesswork",
        mesh=f"Where {name} Compounds",
    )


def choose_weight(node: readme_mesh_pb2.RepositoryNode) -> PresentationWeight:
    """Approximate PSYSOC-X progressive disclosure from evidence density."""

    evidence_count = max((len(section.evidence) for section in node.sections), default=0)
    capability_count = len(node.capabilities)
    complexity = evidence_count + capability_count

    if complexity <= 4:
        return PresentationWeight(2, 1, None, None)
    if complexity <= 8:
        return PresentationWeight(3, 2, None, None)
    return PresentationWeight(3, 3, None, None)


def _section(
    node: readme_mesh_pb2.RepositoryNode,
    audience: int,
) -> readme_mesh_pb2.AudienceSection:
    for section in node.sections:
        if section.audience == audience:
            return section
    raise ReadmeMeshError(
        f"{node.repository} has no {readme_mesh_pb2.Audience.Name(audience)} section"
    )


def _render_evidence(
    evidence: Iterable[readme_mesh_pb2.EvidenceReference],
) -> list[str]:
    rows = list(evidence)
    if not rows:
        return []
    lines = ["", "**Open the proof**", ""]
    lines.extend(
        f"- [{item.label}]({item.path}) — {item.claim}"
        for item in rows
    )
    return lines


def _slice(values: Iterable, limit: int | None):
    rows = list(values)
    return rows if limit is None else rows[:limit]


def render_four_depth_block(
    mesh: readme_mesh_pb2.ReadmeMesh,
    repository: str,
    *,
    license_path: str = "LICENSE",
    license_name: str = "GlacierEQ Proprietary Copyright License and Enforcement Notice v1.1",
) -> str:
    """Render Recruiter -> Master -> Machine -> Mesh from one validated graph."""

    validate_mesh(mesh)
    nodes = repository_index(mesh)
    try:
        node = nodes[repository]
    except KeyError as exc:
        raise ReadmeMeshError(f"repository is not present in mesh: {repository}") from exc

    recruiter = _section(node, readme_mesh_pb2.RECRUITER)
    master = _section(node, readme_mesh_pb2.EXPERT)
    machine = _section(node, readme_mesh_pb2.AI_AGENT)
    titles = choose_titles(node)
    weight = choose_weight(node)

    lines: list[str] = [
        BEGIN_MARKER,
        f"## Four Ways Into {node.display_name}",
        "",
        (
            "One factual system, four useful depths. Read until you have what you need; "
            "every layer is designed to be a truthful stopping point."
        ),
        "",
        f"## 01 · RECRUITER — {titles.recruiter}",
        "",
        "*Recruiter / normal-person lens · what it does, why it matters, and what to open next*",
        "",
        recruiter.summary,
        "",
    ]
    lines.extend(f"- {item}" for item in _slice(recruiter.highlights, weight.recruiter_highlights))
    lines.extend(_render_evidence(_slice(recruiter.evidence, weight.recruiter_evidence)))

    lines.extend(
        [
            "",
            f"## 02 · MASTER — {titles.master}",
            "",
            "*Masters-of-the-trade lens · architecture, mechanism, tradeoffs, failure behavior, and proof*",
            "",
            master.summary,
            "",
        ]
    )
    lines.extend(f"- {item}" for item in _slice(master.highlights, weight.master_highlights))
    lines.extend(_render_evidence(_slice(master.evidence, weight.master_evidence)))

    lines.extend(
        [
            "",
            f"## 03 · MACHINE — {titles.machine}",
            "",
            "*Machine lens · deterministic identity, entrypoints, evidence, authority, and integration*",
            "",
            machine.summary,
            "",
        ]
    )
    lines.extend(f"- {item}" for item in machine.highlights)
    lines.extend(_render_evidence(machine.evidence))
    lines.extend(
        [
            "",
            "```yaml",
            "schema: glaciereq.readme.four-depth/v1",
            f"repository: {node.repository}",
            f"display_name: {node.display_name}",
            f"default_branch: {node.default_branch}",
            f"legacy_mesh_schema: {mesh.schema_version}",
            "layers:",
            "  - recruiter",
            "  - master",
            "  - machine",
            "  - mesh",
            "license:",
            f"  name: {license_name}",
            f"  path: {license_path}",
            "  status: ALL_RIGHTS_RESERVED_TITLE_17",
            "  federal_basis:",
            "    - 17 U.S.C. § 102",
            "    - 17 U.S.C. § 106",
            "    - 17 U.S.C. §§ 501-505",
            "    - 17 U.S.C. §§ 411-412",
            "    - 17 U.S.C. § 401(d)",
            "presentation_authority:",
            "  capability: stone-psysoc-x",
            "  repository: GlacierEQ/AKOS",
            "  manifest: stones/psysoc-x/stone.json",
            "truth_invariant: presentation_may_change_truth_may_not",
            "```",
        ]
    )

    lines.extend(
        [
            "",
            f"## 04 · MESH — {titles.mesh}",
            "",
            "*Mesh lens · typed relationships, combined value, lineage, and boundaries*",
            "",
            "| Relationship | Connected repository | What becomes stronger together |",
            "|---|---|---|",
        ]
    )
    connected = [
        edge
        for edge in mesh.edges
        if edge.source == repository or edge.target == repository
    ]
    connected.sort(key=lambda edge: (edge.source, edge.target, edge.relation))
    if connected:
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
    else:
        lines.append("| — | — | No typed mesh relationship is asserted yet. |")

    lines.extend(
        [
            "",
            "Copyright © 2026 Casey Del Carpio Barton / GlacierEQ. "
            "**All rights reserved under U.S. copyright law.** Unauthorized exercise "
            "of GlacierEQ's exclusive rights may constitute infringement under "
            "17 U.S.C. § 501. See "
            f"[`{license_path}`]({license_path}).",
            "",
            END_MARKER,
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
