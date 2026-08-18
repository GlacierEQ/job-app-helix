from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_app_helix.company_intelligence import (
    CompanyIntelligence,
    CompanySignal,
)
from job_app_helix.company_intelligence_acquisition import (
    AcquisitionPlan,
    FetchedSource,
    SourceSpec,
    acquire_company_intelligence,
    load_acquisition_plan,
)
from job_app_helix.company_intelligence_refresh import refresh_company_intelligence


NOW = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)


def _html_source(spec: SourceSpec) -> FetchedSource:
    del spec
    return FetchedSource(
        requested_url="https://www.example.com/company/news",
        final_url="https://www.example.com/company/news",
        status=200,
        content_type="text/html; charset=utf-8",
        body=(
            b"<html><body><h1>Engineering update</h1>"
            b"<p>We are investing in reliable agent infrastructure and observability.</p>"
            b"<script>fake hiring compiler kernel accelerator</script>"
            b"<p>Our research teams are hiring engineers for evaluation systems.</p>"
            b"</body></html>"
        ),
        fetched_at="2026-08-18T09:55:00Z",
        etag='"abc"',
    )


def test_html_acquisition_is_attributable_filtered_and_content_addressed() -> None:
    plan = AcquisitionPlan(
        schema="glaciereq.company-intelligence-acquisition-plan.v1",
        company_id="example",
        company="Example",
        max_age_days=45,
        sources=(
            SourceSpec(
                kind="engineering",
                source_url="https://www.example.com/company/news",
                allowed_domains=("example.com",),
                include_patterns=(r"agent infrastructure", r"evaluation systems"),
                extractor="html",
                source_title="Example engineering update",
                max_statements=4,
            ),
        ),
    )

    result = acquire_company_intelligence(plan, transport=_html_source, now=lambda: NOW)

    statements = [signal.statement for signal in result.intelligence.signals]
    assert len(statements) == 2
    assert any("reliable agent infrastructure" in statement for statement in statements)
    assert any("hiring engineers for evaluation systems" in statement for statement in statements)
    assert all("compiler kernel accelerator" not in statement for statement in statements)
    assert result.sources[0].content_sha256
    assert result.sources[0].extracted_statement_count == 2
    assert len(result.receipt_sha256) == 64


def test_json_paths_limit_acquisition_to_explicit_source_fields() -> None:
    spec = SourceSpec(
        kind="investment",
        source_url="https://api.example.com/updates/latest",
        allowed_domains=("example.com",),
        include_patterns=(r"compute",),
        extractor="json",
        json_paths=("/official/summary",),
        source_title="Official update API",
    )
    plan = AcquisitionPlan(
        schema="glaciereq.company-intelligence-acquisition-plan.v1",
        company_id="example",
        company="Example",
        max_age_days=45,
        sources=(spec,),
    )

    def transport(_: SourceSpec) -> FetchedSource:
        payload = {
            "official": {"summary": "We expanded compute capacity for model training."},
            "untrusted": {"summary": "We secretly acquired a competitor for compute."},
        }
        return FetchedSource(
            requested_url=spec.source_url,
            final_url=spec.source_url,
            status=200,
            content_type="application/json",
            body=json.dumps(payload).encode(),
            fetched_at="2026-08-18T09:57:00Z",
        )

    result = acquire_company_intelligence(plan, transport=transport, now=lambda: NOW)

    assert len(result.intelligence.signals) == 1
    assert "expanded compute capacity" in result.intelligence.signals[0].statement
    assert "competitor" not in result.intelligence.signals[0].statement


def test_transport_cannot_smuggle_redirected_unapproved_domain() -> None:
    spec = SourceSpec(
        kind="hiring",
        source_url="https://jobs.example.com/engineering",
        allowed_domains=("example.com",),
        include_patterns=(r"hiring",),
        extractor="text",
    )
    plan = AcquisitionPlan(
        schema="glaciereq.company-intelligence-acquisition-plan.v1",
        company_id="example",
        company="Example",
        max_age_days=45,
        sources=(spec,),
    )

    def hostile_transport(_: SourceSpec) -> FetchedSource:
        return FetchedSource(
            requested_url=spec.source_url,
            final_url="https://attacker.invalid/copied-page",
            status=200,
            content_type="text/plain",
            body=b"We are hiring platform engineers for agent systems.",
            fetched_at="2026-08-18T09:58:00Z",
        )

    with pytest.raises(ValueError, match="outside allowed_domains"):
        acquire_company_intelligence(plan, transport=hostile_transport, now=lambda: NOW)


def test_acquired_snapshot_composes_directly_with_refresh_without_losing_fresh_state() -> None:
    current = CompanyIntelligence(
        schema="glaciereq.company-intelligence.v1",
        company_id="example",
        company="Example",
        collected_at="2026-08-17T10:00:00Z",
        max_age_days=45,
        signals=(
            CompanySignal(
                kind="value",
                statement="We prioritize reliable systems and careful deployment.",
                source_url="https://www.example.com/values",
                observed_at="2026-08-17T09:00:00Z",
                source_title="Values",
            ),
        ),
    )
    spec = SourceSpec(
        kind="engineering",
        source_url="https://www.example.com/company/news",
        allowed_domains=("example.com",),
        include_patterns=(r"agent infrastructure",),
        extractor="html",
    )
    plan = AcquisitionPlan(
        schema="glaciereq.company-intelligence-acquisition-plan.v1",
        company_id="example",
        company="Example",
        max_age_days=45,
        sources=(spec,),
    )

    acquired = acquire_company_intelligence(plan, transport=_html_source, now=lambda: NOW)
    refreshed = refresh_company_intelligence(current, acquired.intelligence, now=NOW)

    assert len(refreshed.intelligence.signals) == 2
    assert {signal.kind for signal in refreshed.intelligence.signals} == {"engineering", "value"}
    assert refreshed.receipt.added_count == 1
    assert refreshed.receipt.stale_retired_count == 0


def test_plan_loader_rejects_source_outside_declared_domain(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(
        json.dumps(
            {
                "company_id": "example",
                "company": "Example",
                "sources": [
                    {
                        "kind": "product",
                        "source_url": "https://attacker.invalid/product",
                        "allowed_domains": ["example.com"],
                        "include_patterns": ["launch"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="outside allowed_domains"):
        load_acquisition_plan(path)
