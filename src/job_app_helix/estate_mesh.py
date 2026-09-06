from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class EvidenceLevel(StrEnum):
    INVENTORY = "INVENTORY"
    DOCUMENTATION = "DOCUMENTATION"
    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    BUILD = "BUILD"
    TEST = "TEST"
    INTEGRATION = "INTEGRATION"
    DEPLOYMENT = "DEPLOYMENT"


@dataclass(frozen=True, slots=True)
class RepoRecord:
    full_name: str
    provider_id: str | None = None
    default_branch: str = "main"
    visibility: str = "public"
    description: str = ""
    topics: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    archived: bool = False
    fork: bool = False
    source_sha: str | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.INVENTORY
    evidence_refs: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        return self.full_name.rsplit("/", 1)[-1]


@dataclass(frozen=True, slots=True)
class Company:
    slug: str
    name: str
    aliases: tuple[str, ...] = ()
    target_roles: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    explicit_repo_names: tuple[str, ...] = ()

    def tokens(self) -> set[str]:
        values = (self.name, self.slug, *self.aliases, *self.keywords)
        return {
            token.lower()
            for value in values
            for token in value.replace("/", " ").replace("-", " ").split()
            if token
        }


@dataclass(frozen=True, slots=True)
class RepoRelation:
    company_slug: str
    repo_full_name: str
    relation: str
    reasons: tuple[str, ...]
    evidence_level: EvidenceLevel
    evidence_refs: tuple[str, ...] = ()


@dataclass(slots=True)
class CompanyProjection:
    company: Company
    relations: list[RepoRelation] = field(default_factory=list)

    @property
    def repo_count(self) -> int:
        return len({relation.repo_full_name for relation in self.relations})


class MeshInvariantError(ValueError):
    pass


class JobEstateMesh:
    """Source-exhaustive estate graph with evidence-bound company projections.

    Operational APIs may paginate, but callers must exhaust the provider
    continuation signal before marking a census complete. No top-N, max-repo,
    max-company, fixed-family, or fixed-estate-size value defines membership.
    """

    def __init__(self, repos: Iterable[RepoRecord], companies: Iterable[Company]):
        repo_list = list(repos)
        company_list = list(companies)
        self.repos = {repo.full_name: repo for repo in repo_list}
        self.companies = {company.slug: company for company in company_list}
        if len(self.repos) != len(repo_list):
            raise MeshInvariantError("duplicate repository identity")
        if len(self.companies) != len(company_list):
            raise MeshInvariantError("duplicate company identity")
        self._relations: dict[str, dict[str, RepoRelation]] = {
            slug: {} for slug in self.companies
        }

    def attach_all(self) -> None:
        for company in self.companies.values():
            for repo in self.repos.values():
                relation = self._infer_relation(company, repo)
                if relation is not None:
                    self._relations[company.slug][repo.full_name] = relation

    def _infer_relation(self, company: Company, repo: RepoRecord) -> RepoRelation | None:
        haystack = " ".join(
            (repo.full_name, repo.description, *repo.topics, *repo.languages)
        ).lower()
        reasons: list[str] = []
        explicit = (
            repo.full_name in company.explicit_repo_names
            or repo.slug in company.explicit_repo_names
        )
        if explicit:
            reasons.append("explicit company-to-repository mapping")

        matched = sorted(
            token for token in company.tokens()
            if len(token) >= 3 and token in haystack
        )
        if matched:
            reasons.append("company/role relevance tokens: " + ", ".join(matched))

        capability_tokens = {
            "ai", "agent", "gpu", "infrastructure", "platform", "distributed",
            "mcp", "kubernetes", "cloud", "inference", "training", "retrieval",
            "search", "security", "compiler", "orchestration", "reliability",
            "network", "data", "memory", "reasoning",
        }
        shared = sorted(
            capability_tokens.intersection(company.tokens()).intersection(
                {token for token in capability_tokens if token in haystack}
            )
        )
        if shared:
            reasons.append("shared capability domains: " + ", ".join(shared))

        if not reasons:
            return None

        return RepoRelation(
            company_slug=company.slug,
            repo_full_name=repo.full_name,
            relation="DIRECT_TARGET" if explicit else "CAPABILITY_RELEVANCE",
            reasons=tuple(reasons),
            evidence_level=repo.evidence_level,
            evidence_refs=repo.evidence_refs,
        )

    def add_relation(self, relation: RepoRelation) -> None:
        if relation.company_slug not in self.companies:
            raise MeshInvariantError(f"unknown company: {relation.company_slug}")
        if relation.repo_full_name not in self.repos:
            raise MeshInvariantError(f"unknown repository: {relation.repo_full_name}")
        self._relations[relation.company_slug][relation.repo_full_name] = relation

    def projection(self, company_slug: str) -> CompanyProjection:
        if company_slug not in self.companies:
            raise MeshInvariantError(f"unknown company: {company_slug}")
        return CompanyProjection(
            company=self.companies[company_slug],
            relations=sorted(
                self._relations[company_slug].values(),
                key=lambda item: item.repo_full_name.lower(),
            ),
        )

    def unassigned_repos(self) -> list[RepoRecord]:
        assigned = {name for relations in self._relations.values() for name in relations}
        return sorted(
            (repo for name, repo in self.repos.items() if name not in assigned),
            key=lambda repo: repo.full_name.lower(),
        )

    def validate(self, *, source_exhausted: bool | None = None) -> dict[str, object]:
        dangling = [
            asdict(relation)
            for relations in self._relations.values()
            for relation in relations.values()
            if relation.repo_full_name not in self.repos
            or relation.company_slug not in self.companies
        ]
        return {
            "valid": not dangling,
            "repo_count": len(self.repos),
            "company_count": len(self.companies),
            "relation_count": sum(len(items) for items in self._relations.values()),
            "unassigned_repo_count": len(self.unassigned_repos()),
            "dangling_relations": dangling,
            "source_exhausted": source_exhausted,
            "fixed_size_gate_present": False,
        }

    def export(self, *, source_exhausted: bool | None = None) -> dict[str, object]:
        return {
            "schema": "glaciereq.job-estate-mesh.v2",
            "policy": {
                "membership": "source-exhaustive",
                "fixed_top_n": None,
                "fixed_repo_cap": None,
                "fixed_company_cap": None,
                "fixed_relation_cap": None,
                "counts_are": "observations, never admission limits",
                "presentation_pagination_changes_membership": False,
                "evidence_boundary": (
                    "relevance never implies employment, affiliation, proprietary "
                    "access, deployment, endorsement, or production outcome"
                ),
            },
            "estate": [
                asdict(repo)
                for repo in sorted(
                    self.repos.values(), key=lambda item: item.full_name.lower()
                )
            ],
            "companies": {
                slug: {
                    "company": asdict(self.companies[slug]),
                    "relations": [
                        asdict(relation)
                        for relation in self.projection(slug).relations
                    ],
                }
                for slug in sorted(self.companies)
            },
            "unassigned_repositories": [asdict(repo) for repo in self.unassigned_repos()],
            "validation": self.validate(source_exhausted=source_exhausted),
        }


def _repo(record: Mapping[str, object]) -> RepoRecord:
    return RepoRecord(
        full_name=str(record["full_name"]),
        provider_id=None if record.get("provider_id") is None else str(record["provider_id"]),
        default_branch=str(record.get("default_branch", "main")),
        visibility=str(record.get("visibility", "public")),
        description=str(record.get("description", "")),
        topics=tuple(map(str, record.get("topics", ()))),
        languages=tuple(map(str, record.get("languages", ()))),
        archived=bool(record.get("archived", False)),
        fork=bool(record.get("fork", False)),
        source_sha=None if record.get("source_sha") is None else str(record["source_sha"]),
        evidence_level=EvidenceLevel(str(record.get("evidence_level", "INVENTORY"))),
        evidence_refs=tuple(map(str, record.get("evidence_refs", ()))),
    )


def _company(record: Mapping[str, object]) -> Company:
    return Company(
        slug=str(record["slug"]),
        name=str(record["name"]),
        aliases=tuple(map(str, record.get("aliases", ()))),
        target_roles=tuple(map(str, record.get("target_roles", ()))),
        keywords=tuple(map(str, record.get("keywords", ()))),
        explicit_repo_names=tuple(map(str, record.get("explicit_repo_names", ()))),
    )


def compile_payload(payload: Mapping[str, object]) -> dict[str, object]:
    mesh = JobEstateMesh(
        [_repo(item) for item in payload.get("repositories", [])],
        [_company(item) for item in payload.get("companies", [])],
    )
    mesh.attach_all()
    return mesh.export(source_exhausted=payload.get("source_exhausted"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile an uncapped GlacierEQ job-estate/company mesh."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    rendered = json.dumps(
        compile_payload(payload), indent=2, sort_keys=True, default=str
    ) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
