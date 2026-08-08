from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build_recruiter_site.py"
CSS = ROOT / "site" / "compiler.css"
JS = ROOT / "site" / "compiler.js"
EXPECTED_SCHEMA = "glaciereq.estate-public-projection.v2"
FORBIDDEN_KEYS = {
    "repository_count",
    "native_repository_count",
    "fork_repository_count",
    "private_repository_count",
    "legal_private_repositories",
    "canonical_accomplishments",
}
REQUIRED_BOUNDARY = {
    "private_repository_identities_omitted",
    "legal_private_records_omitted",
    "support_only_systems_omitted_from_accomplishment_projection",
    "experiment_systems_omitted_from_accomplishment_projection",
    "unresolved_lineage_omitted_from_accomplishment_projection",
    "native_estate_cardinality_intentionally_not_published",
    "observed_pressure_and_inferred_bottleneck_are_distinct",
    "role_projection_is_capability_fit_not_employer_endorsement",
}
PREFERRED = ("openai", "anthropic", "microsoft", "spacex")


class ProjectionError(RuntimeError):
    pass


def _base() -> ModuleType:
    spec = importlib.util.spec_from_file_location("recruiter_base", BASE)
    if spec is None or spec.loader is None:
        raise ProjectionError(f"Unable to load {BASE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"Unable to load public projection: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionError("Public projection must be an object")
    return value


def _walk(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise ProjectionError(f"Forbidden estate cardinality at {path}.{key}")
            _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, f"{path}[{index}]")


def validate_public_projection(value: dict[str, Any]) -> None:
    if value.get("schema") != EXPECTED_SCHEMA:
        raise ProjectionError(f"Expected {EXPECTED_SCHEMA}")
    boundary = value.get("boundary")
    if not isinstance(boundary, dict):
        raise ProjectionError("Public projection has no structured boundary")
    missing = sorted(key for key in REQUIRED_BOUNDARY if boundary.get(key) is not True)
    if missing:
        raise ProjectionError(f"Public projection boundary failed closed: {missing}")
    if not isinstance(value.get("company_projections"), list):
        raise ProjectionError("company_projections must be a list")
    _walk(value)


def _escape(base: ModuleType, value: Any) -> str:
    return base._escape("" if value is None else value)


def _default_company(payload: dict[str, Any]) -> dict[str, Any] | None:
    companies = [row for row in payload["company_projections"] if isinstance(row, dict)]
    for company_id in PREFERRED:
        match = next((row for row in companies if row.get("company_id") == company_id and row.get("ranked_evidence")), None)
        if match:
            return match
    return next((row for row in companies if row.get("ranked_evidence")), companies[0] if companies else None)


def _source_links(base: ModuleType, company: dict[str, Any]) -> str:
    sources = company.get("official_sources")
    if not isinstance(sources, list) or not sources:
        return '<span class="compiler-empty">Source-backed company intelligence not loaded.</span>'
    links = []
    for source in sources[:3]:
        if not isinstance(source, dict) or not isinstance(source.get("url"), str):
            continue
        links.append(
            '<a rel="noopener noreferrer" href="{}">{}</a>'.format(
                _escape(base, source["url"]),
                _escape(base, source.get("title", "Official source")),
            )
        )
    return "".join(links)


def _system_cards(base: ModuleType, company: dict[str, Any], role: str | None) -> str:
    rows = [row for row in company.get("ranked_evidence", []) if isinstance(row, dict)]
    allowed = set(company.get("audience_projection", {}).get("recruiter", []))
    role_rows = company.get("role_projection", {}).get(role, {}).get("systems", []) if role else []
    fit = {row["system_id"]: row for row in role_rows if isinstance(row, dict) and isinstance(row.get("system_id"), str)}
    ordered_ids = [row["system_id"] for row in role_rows if row.get("system_id") in allowed]
    if not ordered_ids:
        ordered_ids = [row["system_id"] for row in rows if row.get("system_id") in allowed]
    by_id = {row.get("system_id"): row for row in rows}
    cards = []
    for system_id in ordered_ids[:5]:
        row = by_id.get(system_id, {})
        score = row.get("promotion_score")
        score_text = f"{float(score):.0f}/100 proof score" if isinstance(score, (int, float)) else "Evidence incomplete"
        fit_score = fit.get(system_id, {}).get("fit_score")
        fit_text = f"{float(fit_score):.0f}% role fit" if isinstance(fit_score, (int, float)) else "Role fit pending"
        chips = "".join(
            f'<span class="capability-chip">{_escape(base, cap.replace("-", " "))}</span>'
            for cap in row.get("capabilities", [])[:7]
            if isinstance(cap, str)
        )
        repository = row.get("source_repository")
        link = ""
        if isinstance(repository, str) and repository.startswith("GlacierEQ/"):
            link = f'<a class="text-link" href="https://github.com/{_escape(base, repository)}">Inspect source →</a>'
        cards.append(
            '<article class="compiler-system-card">'
            f'<div class="compiler-system-metrics"><span>{_escape(base, fit_text)}</span><span>{_escape(base, score_text)}</span></div>'
            f'<h3>{_escape(base, str(system_id).replace("-", " "))}</h3>'
            f'<div class="capability-chips">{chips}</div>{link}</article>'
        )
    if cards:
        return "".join(cards)
    return (
        '<article class="compiler-system-card compiler-system-empty">'
        '<h3>No public proof promoted for this route yet.</h3>'
        '<p>The compiler fails closed rather than filling the gap with an unsupported claim.</p>'
        '</article>'
    )


def _section(base: ModuleType, payload: dict[str, Any]) -> str:
    companies = [row for row in payload["company_projections"] if isinstance(row, dict)]
    company = _default_company(payload)
    company_id = company.get("company_id") if company else None
    roles = [role for role in (company or {}).get("target_roles", []) if isinstance(role, str)]
    role = roles[0] if roles else None
    company_options = "".join(
        '<option value="{}"{}>{}</option>'.format(
            _escape(base, row.get("company_id")),
            " selected" if row.get("company_id") == company_id else "",
            _escape(base, row.get("display_name", row.get("company_id"))),
        )
        for row in companies
    )
    role_options = "".join(
        '<option value="{}"{}>{}</option>'.format(
            _escape(base, item), " selected" if item == role else "", _escape(base, item)
        )
        for item in roles
    ) or '<option value="">No role route</option>'
    observed = (company or {}).get("observed_operating_pressure") or "Source-backed operating pressure has not been loaded for this route."
    inferred = (company or {}).get("inferred_bottleneck") or "No GlacierEQ bottleneck inference is promoted for this route."
    move = (company or {}).get("application_move") or (company or {}).get("recruiter_thesis") or "Select a company route."
    freshness = (company or {}).get("freshness_state") or "NOT_LOADED"
    research = (company or {}).get("research_as_of")
    freshness_text = freshness.replace("_", " ").title()
    if research:
        freshness_text += f" · research snapshot {research}"
    return f'''
    <section class="section shell compiler-section" id="compiler" aria-labelledby="compiler-title">
      <div class="section-heading"><div><div class="eyebrow">Portfolio compiler</div><h2 id="compiler-title">Route the evidence to the reviewer</h2></div><p>One canonical evidence graph, projected by company, role, and review depth. Private identities and raw estate counts stay internal.</p></div>
      <div class="compiler-controls">
        <label><span>Company</span><select id="compiler-company">{company_options}</select></label>
        <label><span>Role</span><select id="compiler-role">{role_options}</select></label>
        <label><span>Review depth</span><select id="compiler-depth"><option value="recruiter">Recruiter</option><option value="company_reviewer">Company reviewer</option><option value="senior_engineer">Senior engineer</option></select></label>
      </div>
      <div class="compiler-route-header"><div><span class="compiler-kicker">Compiled route</span><h3 id="compiler-route-title">{_escape(base, (company or {}).get("display_name", "No route"))} · {_escape(base, role or "Role pending")}</h3></div><span class="compiler-freshness" id="compiler-freshness">{_escape(base, freshness_text)}</span></div>
      <div class="compiler-intelligence-grid">
        <article class="compiler-intel-card observed"><span class="compiler-state">Observed · source-backed</span><h3>Operating pressure</h3><p id="compiler-pressure">{_escape(base, observed)}</p><div class="compiler-source-links" id="compiler-sources">{_source_links(base, company or {})}</div></article>
        <article class="compiler-intel-card inferred"><span class="compiler-state">GlacierEQ inference</span><h3>Engineering bottleneck</h3><p id="compiler-bottleneck">{_escape(base, inferred)}</p></article>
        <article class="compiler-intel-card intervention"><span class="compiler-state">Transferable intervention</span><h3>Application move</h3><p id="compiler-intervention">{_escape(base, move)}</p></article>
      </div>
      <div class="compiler-proof-heading"><div><span class="compiler-kicker">Role-specific proof</span><h3>Systems selected by capability fit and evidence</h3></div><p id="compiler-problem-boundary">Dossier gate: {_escape(base, (company or {}).get("dossier_next_gate", "not loaded"))}</p></div>
      <div class="compiler-system-grid" id="compiler-systems">{_system_cards(base, company or {}, role)}</div>
      <div class="compiler-contract"><strong>Truth contract.</strong><span>Observed pressure is source-backed. Bottlenecks and interventions are GlacierEQ inferences. Role fit is capability overlap, not affiliation, endorsement, or a hiring prediction.</span><a class="text-link" href="estate-projection.json">Inspect machine projection →</a></div>
    </section>
    '''


def build(output: Path, source_commit: str, public_projection: Path | None = None) -> None:
    base = _base()
    base.build(output, source_commit)
    if public_projection is None:
        return
    payload = _load(public_projection)
    validate_public_projection(payload)
    index_path = output / "index.html"
    index = index_path.read_text(encoding="utf-8")
    if index.count("connect-src 'none'") != 1:
        raise ProjectionError("Canonical CSP same-origin boundary changed")
    index = index.replace("connect-src 'none'", "connect-src 'self'", 1)
    index = index.replace('<link rel="stylesheet" href="styles.css">', '<link rel="stylesheet" href="styles.css">\n  <link rel="stylesheet" href="compiler.css">', 1)
    index = index.replace('<script src="app.js" defer></script>', '<script src="app.js" defer></script>\n  <script src="compiler.js" defer></script>', 1)
    index = index.replace('<a href="#package">Package</a>', '<a href="#compiler">Compiler</a>\n        <a href="#package">Package</a>', 1)
    if "</main>" not in index:
        raise ProjectionError("Canonical recruiter template has no </main>")
    index = index.replace("</main>", _section(base, payload) + "\n  </main>", 1)
    index_path.write_text(index, encoding="utf-8")
    shutil.copyfile(CSS, output / "compiler.css")
    shutil.copyfile(JS, output / "compiler.js")
    shutil.copyfile(public_projection, output / "estate-projection.json")
    base._assert_public_surface(output)
    base._write_manifest(output, source_commit)
    base._assert_public_surface(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build recruiter site with optional public estate projection")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/pages-site")
    parser.add_argument("--source-commit", default="local-uncommitted")
    parser.add_argument("--public-projection", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build(args.output.resolve(), str(args.source_commit), args.public_projection.resolve() if args.public_projection else None)
    except ProjectionError as exc:
        print(f"Compiled recruiter site failed closed: {exc}")
        return 1
    print(f"Compiled recruiter site built at {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
