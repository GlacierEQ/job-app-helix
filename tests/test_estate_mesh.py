from job_app_helix.estate_mesh import (
    Company,
    EvidenceLevel,
    JobEstateMesh,
    RepoRecord,
    RepoRelation,
)


def test_large_estate_is_not_truncated():
    repos = [
        RepoRecord(full_name=f"GlacierEQ/repo-{i}", description="AI agent infrastructure")
        for i in range(5000)
    ]
    companies = [
        Company(slug="xai", name="xAI", keywords=("ai", "agent", "infrastructure"))
    ]
    mesh = JobEstateMesh(repos, companies)
    mesh.attach_all()
    exported = mesh.export(source_exhausted=True)
    assert exported["validation"]["repo_count"] == 5000
    assert exported["companies"]["xai"]["relations"]
    assert exported["policy"]["fixed_repo_cap"] is None
    assert exported["validation"]["fixed_size_gate_present"] is False


def test_unassigned_repo_is_retained_not_dropped():
    repos = [
        RepoRecord(
            full_name="GlacierEQ/obscure-marine-tool",
            description="marine biology utility",
        )
    ]
    mesh = JobEstateMesh(
        repos,
        [Company(slug="xai", name="xAI", keywords=("gpu", "infrastructure"))],
    )
    mesh.attach_all()
    exported = mesh.export()
    assert exported["validation"]["repo_count"] == 1
    assert exported["validation"]["unassigned_repo_count"] == 1
    assert exported["unassigned_repositories"][0]["full_name"] == repos[0].full_name


def test_explicit_relation_survives_without_keyword_match():
    repo = RepoRecord(
        full_name="GlacierEQ/odd-name",
        evidence_level=EvidenceLevel.TEST,
        evidence_refs=("sha:abc",),
    )
    company = Company(slug="coreweave", name="CoreWeave")
    mesh = JobEstateMesh([repo], [company])
    mesh.add_relation(
        RepoRelation(
            "coreweave",
            repo.full_name,
            "DIRECT_TARGET",
            ("verified mapping",),
            EvidenceLevel.TEST,
            ("sha:abc",),
        )
    )
    projection = mesh.projection("coreweave")
    assert projection.repo_count == 1
    assert projection.relations[0].evidence_level is EvidenceLevel.TEST


def test_company_count_can_grow_without_test_rewrite():
    repos = [RepoRecord(full_name="GlacierEQ/agent-core", description="agent ai mcp reasoning")]
    companies = [
        Company(slug=f"c{i}", name=f"Company {i}", keywords=("agent",))
        for i in range(250)
    ]
    mesh = JobEstateMesh(repos, companies)
    mesh.attach_all()
    assert mesh.validate()["company_count"] == 250
    assert mesh.validate()["relation_count"] == 250


def test_duplicate_repo_identity_fails_loudly():
    try:
        JobEstateMesh(
            [RepoRecord(full_name="GlacierEQ/same"), RepoRecord(full_name="GlacierEQ/same")],
            [],
        )
    except ValueError as exc:
        assert "duplicate repository identity" in str(exc)
    else:
        raise AssertionError("duplicate repository identity must fail")
