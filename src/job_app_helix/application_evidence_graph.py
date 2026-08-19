"""Project the live experience graph into recruiter/application evidence.

The experience graph knows which public repositories address a target company's
challenge space. This runtime turns those relationships into a deterministic evidence
bundle without upgrading inventory into authorship, runtime proof, or affiliation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

GRAPH_SCHEMA = "glaciereq.live-experience-graph.v1"
BUNDLE_SCHEMA = "glaciereq.application-evidence-graph.v1"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class ApplicationEvidence:
    rank: int
    repository: str
    company_id: str
    evidence_level: str | None
    promotion_state: str
    provenance_state: str
    flagship_systems: tuple[str, ...]
    paradigms: tuple[str, ...]
    score: float
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ApplicationEvidenceBundle:
    schema: str
    target_company_id: str
    target_company: str
    experience_graph_snapshot_id: str
    evidence_count: int
    evidence: tuple[ApplicationEvidence, ...]
    truth_boundary: Mapping[str, bool]
    receipt_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "target_company_id": self.target_company_id,
            "target_company": self.target_company,
            "experience_graph_snapshot_id": self.experience_graph_snapshot_id,
            "evidence_count": self.evidence_count,
            "evidence": [row.as_dict() for row in self.evidence],
            "truth_boundary": dict(self.truth_boundary),
            "receipt_sha256": self.receipt_sha256,
        }


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_graph(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema") != GRAPH_SCHEMA:
        raise ValueError(f"experience graph must use schema {GRAPH_SCHEMA}")
    snapshot_id = payload.get("snapshot_id")
    if not isinstance(snapshot_id, str) or _SHA256.fullmatch(snapshot_id) is None:
        raise ValueError("experience graph has invalid snapshot_id")
    boundary = payload.get("truth_boundary")
    if not isinstance(boundary, Mapping):
        raise ValueError("experience graph requires truth_boundary")
    required_boundaries = (
        "inventory_is_not_authorship",
        "inventory_is_not_runtime_proof",
        "company_mapping_does_not_imply_affiliation",
        "private_repository_names_omitted_from_public_graph",
    )
    if any(boundary.get(key) is not True for key in required_boundaries):
        raise ValueError("experience graph truth boundary is not safe for application projection")
    graph = payload.get("graph")
    if not isinstance(graph, Mapping) or not isinstance(graph.get("public"), Mapping):
        raise ValueError("experience graph requires a public projection")
    return payload


def _resolve_company(payload: Mapping[str, object], company: str) -> tuple[str, str]:
    normalized = company.casefold().strip()
    matches: list[tuple[str, str]] = []
    rows = payload.get("companies")
    if not isinstance(rows, list):
        raise ValueError("experience graph requires companies")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        company_id = row.get("company_id")
        display_name = row.get("display_name")
        if not isinstance(company_id, str) or not isinstance(display_name, str):
            continue
        if normalized in {company_id.casefold(), display_name.casefold()}:
            matches.append((company_id, display_name))
    if len(matches) != 1:
        raise ValueError(f"target company must resolve exactly once: {company!r}")
    return matches[0]


def _public_graph(
    payload: Mapping[str, object],
) -> tuple[list[Mapping[str, object]], list[Mapping[str, object]]]:
    graph = payload.get("graph")
    if not isinstance(graph, Mapping):
        raise ValueError("experience graph requires graph")
    public = graph.get("public")
    if not isinstance(public, Mapping):
        raise ValueError("experience graph requires public graph")
    nodes = public.get("nodes")
    edges = public.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("public experience graph requires nodes and edges")
    clean_nodes = [row for row in nodes if isinstance(row, Mapping)]
    clean_edges = [row for row in edges if isinstance(row, Mapping)]
    return clean_nodes, clean_edges


def _state_score(value: object, *, provenance: bool = False) -> tuple[float, str | None]:
    text = str(value or "UNCLASSIFIED").upper()
    if provenance:
        weights = {
            "VERIFIED": 18.0,
            "PROVEN": 18.0,
            "ATTRIBUTABLE": 14.0,
            "SOURCE_BOUND": 14.0,
        }
    else:
        weights = {
            "VERIFIED": 20.0,
            "PROMOTED": 16.0,
            "PROVEN": 20.0,
            "READY": 12.0,
        }
    for token, score in weights.items():
        if token in text:
            return score, token.lower().replace("_", "-")
    return 0.0, None


def _evidence_level_score(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).upper()
    numeric = re.search(r"(?:LEVEL|L)[-_ ]?(\d+)", text)
    if numeric:
        return min(20.0, float(numeric.group(1)) * 4.0)
    if any(token in text for token in ("EXECUTABLE", "RUNTIME", "PROVEN")):
        return 16.0
    if any(token in text for token in ("IMPLEMENTED", "WORKING")):
        return 12.0
    return 4.0


def build_application_evidence_bundle(
    payload: Mapping[str, object],
    *,
    company: str,
    limit: int | None = None,
) -> ApplicationEvidenceBundle:
    """Rank public company-linked repositories without inventing stronger claims."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided")
    company_id, display_name = _resolve_company(payload, company)
    nodes, edges = _public_graph(payload)
    by_id = {str(node.get("id")): node for node in nodes if node.get("id")}
    company_node = f"company:{company_id}"

    linked_repo_ids = {
        str(edge.get("source"))
        for edge in edges
        if edge.get("target") == company_node
        and edge.get("relationship") == "addresses-company-challenge"
    }
    flagship_by_repo: dict[str, list[str]] = {}
    paradigms_by_repo: dict[str, list[str]] = {}
    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        relationship = edge.get("relationship")
        if relationship == "implemented-by" and target in linked_repo_ids:
            node = by_id.get(source, {})
            system_id = node.get("system_id") if isinstance(node, Mapping) else None
            if isinstance(system_id, str):
                flagship_by_repo.setdefault(target, []).append(system_id)
        elif relationship == "expresses-paradigm" and source in linked_repo_ids:
            node = by_id.get(target, {})
            paradigm_id = node.get("paradigm_id") if isinstance(node, Mapping) else None
            if isinstance(paradigm_id, str):
                paradigms_by_repo.setdefault(source, []).append(paradigm_id)

    scored: list[tuple[float, str, Mapping[str, object], tuple[str, ...]]] = []
    for repo_id in sorted(linked_repo_ids):
        node = by_id.get(repo_id)
        if node is None or node.get("kind") != "repository":
            continue
        if node.get("visibility") != "public":
            raise ValueError("private repository escaped public experience graph")
        repository = node.get("repository")
        if not isinstance(repository, str):
            raise ValueError(f"public repository node missing identity: {repo_id}")
        score = 50.0
        reasons = ["direct-company-challenge-link", "public-repository"]
        promotion_score, promotion_reason = _state_score(node.get("promotion_state"))
        provenance_score, provenance_reason = _state_score(
            node.get("provenance_state"), provenance=True
        )
        evidence_score = _evidence_level_score(node.get("evidence_level"))
        score += promotion_score + provenance_score + evidence_score
        if promotion_reason:
            reasons.append(f"promotion:{promotion_reason}")
        if provenance_reason:
            reasons.append(f"provenance:{provenance_reason}")
        flagships = tuple(sorted(set(flagship_by_repo.get(repo_id, []))))
        if flagships:
            score += min(12.0, 6.0 * len(flagships))
            reasons.append("public-flagship-implementation")
        scored.append((round(min(score, 100.0), 4), repository, node, tuple(reasons)))

    scored.sort(key=lambda row: (-row[0], row[1].casefold()))
    if limit is not None:
        scored = scored[:limit]
    evidence = tuple(
        ApplicationEvidence(
            rank=index,
            repository=repository,
            company_id=company_id,
            evidence_level=(
                str(node["evidence_level"]) if node.get("evidence_level") is not None else None
            ),
            promotion_state=str(node.get("promotion_state", "UNCLASSIFIED")),
            provenance_state=str(node.get("provenance_state", "UNCLASSIFIED")),
            flagship_systems=tuple(sorted(set(flagship_by_repo.get(f"repo:{repository}", [])))),
            paradigms=tuple(sorted(set(paradigms_by_repo.get(f"repo:{repository}", [])))),
            score=score,
            reasons=reasons,
        )
        for index, (score, repository, node, reasons) in enumerate(scored, start=1)
    )

    truth_boundary = {
        "inventory_is_not_authorship": True,
        "inventory_is_not_runtime_proof": True,
        "company_mapping_does_not_imply_affiliation": True,
        "only_public_repository_identity_emitted": True,
        "projection_is_evidence_selection_not_claim_generation": True,
    }
    base: dict[str, object] = {
        "schema": BUNDLE_SCHEMA,
        "target_company_id": company_id,
        "target_company": display_name,
        "experience_graph_snapshot_id": payload["snapshot_id"],
        "evidence_count": len(evidence),
        "evidence": [row.as_dict() for row in evidence],
        "truth_boundary": truth_boundary,
    }
    receipt = _canonical_sha256(base)
    return ApplicationEvidenceBundle(
        schema=BUNDLE_SCHEMA,
        target_company_id=company_id,
        target_company=display_name,
        experience_graph_snapshot_id=str(payload["snapshot_id"]),
        evidence_count=len(evidence),
        evidence=evidence,
        truth_boundary=truth_boundary,
        receipt_sha256=receipt,
    )


def execute_application_evidence_projection(
    graph_path: Path,
    *,
    company: str,
    output: Path | None = None,
    limit: int | None = None,
) -> ApplicationEvidenceBundle:
    bundle = build_application_evidence_bundle(
        _load_graph(graph_path),
        company=company,
        limit=limit,
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        rendered = json.dumps(bundle.as_dict(), indent=2, sort_keys=True) + "\n"
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(output)
    return bundle


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-application-evidence",
        description="Rank public experience-graph evidence for a target company.",
    )
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    result = execute_application_evidence_projection(
        args.graph,
        company=args.company,
        output=args.output,
        limit=args.limit,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.evidence_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
