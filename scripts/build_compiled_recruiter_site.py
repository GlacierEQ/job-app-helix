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
BASE_BUILDER_PATH = ROOT / "scripts" / "build_recruiter_site.py"
COMPILER_CSS = ROOT / "site" / "compiler.css"
COMPILER_JS = ROOT / "site" / "compiler.js"
EXPECTED_SCHEMA = "glaciereq.public-portfolio-projection.v2"
FORBIDDEN_PUBLIC_KEYS = {
    "repository_count",
    "native_repository_count",
    "fork_repository_count",
    "private_repository_count",
    "unresolved_native_repository_count",
}
REQUIRED_BOUNDARIES = {
    "native_estate_cardinality_intentionally_not_published",
    "private_repository_identities_omitted",
    "restricted_namespaces_omitted",
    "projection_is_derived_not_hand_curated",
    "observed_pressure_and_inferred_bottleneck_are_distinct",
    "role_projection_is_capability_fit_not_employer_endorsement",
}
PREFERRED_COMPANIES = ("openai", "anthropic", "microsoft", "spacex")


class ProjectionError(RuntimeError):
    pass


def _load_base_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_recruiter_site_base",
        BASE_BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise ProjectionError(f"Unable to load canonical builder: {BASE_BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _load_projection(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"Unable to load public projection {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProjectionError("Public projection must be a JSON object")
    return payload


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_PUBLIC_KEYS:
                raise ProjectionError(f"Forbidden estate cardinality key at {path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")


def validate_public_projection(payload: dict[str, Any]) -> None:
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise ProjectionError(
            f"Expected {EXPECTED_SCHEMA}, got {payload.get('schema')!r}"
        )
    boundary = payload.get("truth_boundary")
    if not isinstance(boundary, dict):
        raise ProjectionError("Public projection has no truth boundary")
    missing = sorted(
        key for key in REQUIRED_BOUNDARIES if boundary.get(key) is not True
    )
    if missing:
        raise ProjectionError(
            f"Public projection truth boundary is not fail-closed: {missing}"
        )
    companies = payload.get("companies")
    systems = payload.get("systems")
    capabilities = payload.get("capabilities")
    if not isinstance(companies, list):
        raise ProjectionError("Public projection companies must be a list")
    if not isinstance(systems, list):
        raise ProjectionError("Public projection systems must be a list")
    if not isinstance(capabilities, list):
        raise ProjectionError("Public projection capabilities must be a list")
    _walk_forbidden(payload)


def _choose_default_company(payload: dict[str, Any]) -> dict[str, Any] | None:
    companies = [row for row in payload.get("companies", []) if isinstance(row, dict)]
    for company_id in PREFERRED_COMPANIES:
        for company in companies:
            if company.get("company_id") == company_id and company.get("systems"):
                return company
    return next((company for company in companies if company.get("systems")), None)


def _first_role(company: dict[str, Any] | None) -> str | None:
    if not company:
        return None
    roles = company.get("target_roles")
    if isinstance(roles, list):
        return next((str(role) for role in roles if isinstance(role, str) and role), None)
    return None


def _system_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row["system_id"]): row
        for row in payload.get("systems", [])
        if isinstance(row, dict) and isinstance(row.get("system_id"), str)
    }


def _company_system_map(company: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row["system_id"]): row
        for row in company.get("systems", [])
        if isinstance(row, dict) and isinstance(row.get("system_id"), str)
    }


def _fallback_system_ids(company: dict[str, Any], role: str | None) -> list[str]:
    if role:
        roles = company.get("role_projection")
        if isinstance(roles, dict):
            role_payload = roles.get(role)
            if isinstance(role_payload, dict):
                rows = role_payload.get("systems")
                if isinstance(rows, list):
                    result = [
                        str(row["system_id"])
                        for row in rows
                        if isinstance(row, dict) and isinstance(row.get("system_id"), str)
                    ]
                    if result:
                        return result
    audience = company.get("audience_projection")
    if isinstance(audience, dict):
        rows = audience.get("recruiter")
        if isinstance(rows, list):
            return [str(value) for value in rows if isinstance(value, str)]
    return []


def _escape(base: ModuleType, value: Any) -> str:
    return base._escape("" if value is None else value)


def _source_links(base: ModuleType, intelligence: dict[str, Any] | None) -> str:
    if not intelligence:
        return '<span class="compiler-empty">Source-backed company intelligence not loaded.</span>'
    sources = intelligence.get("official_sources")
    if not isinstance(sources, list) or not sources:
        return '<span class="compiler-empty">No public source reference available.</span>'
    items: list[str] = []
    for source in sources[:3]:
        if not isinstance(source, dict):
            continue
        title = _escape(base, source.get("title", "Official source"))
        url = _escape(base, source.get("url", ""))
        items.append(
            f'<a href="{url}" rel="noopener noreferrer">{title}</a>'
        )
    return "".join(items) or '<span class="compiler-empty">No public source reference available.</span>'


def _capability_chips(base: ModuleType, capabilities: list[str]) -> str:
    return "".join(
        f'<span class="capability-chip">{_escape(base, capability.replace("_", " "))}</span>'
        for capability in capabilities[:7]
    )


def _fallback_system_cards(
    base: ModuleType,
    payload: dict[str, Any],
    company: dict[str, Any],
    role: str | None,
) -> str:
    systems = _system_map(payload)
    company_systems = _company_system_map(company)
    ids = _fallback_system_ids(company, role)[:5]
    cards: list[str] = []
    role_payload: dict[str, Any] = {}
    if role and isinstance(company.get("role_projection"), dict):
        possible = company["role_projection"].get(role)
        role_payload = possible if isinstance(possible, dict) else {}
    role_fit = {
        row["system_id"]: row
        for row in role_payload.get("systems", [])
        if isinstance(row, dict) and isinstance(row.get("system_id"), str)
    }
    for system_id in ids:
        system = systems.get(system_id, {})
        company_system = company_systems.get(system_id, {})
        score = company_system.get("promotion_score")
        score_text = "Evidence incomplete"
        if isinstance(score, dict) and score.get("complete") is True:
            value = score.get("score")
            if isinstance(value, (int, float)):
                score_text = f"{value:.0f}/100 proof score"
        fit = role_fit.get(system_id, {}).get("fit_score")
        fit_text = (
            f"{float(fit):.0f}% role fit"
            if isinstance(fit, (int, float))
            else "Role fit pending"
        )
        repository = system.get("canonical_repository")
        link = ""
        if isinstance(repository, str) and repository.startswith("GlacierEQ/"):
            link = (
                f'<a class="text-link" href="https://github.com/{_escape(base, repository)}">'
                "Inspect canonical source →</a>"
            )
        capabilities = [
            value
            for value in company_system.get("capabilities", [])
            if isinstance(value, str)
        ]
        cards.append(
            '<article class="compiler-system-card">'
            f'<div class="compiler-system-metrics"><span>{_escape(base, fit_text)}</span>'
            f'<span>{_escape(base, score_text)}</span></div>'
            f'<h3>{_escape(base, system_id.replace("_", " "))}</h3>'
            f'<div class="capability-chips">{_capability_chips(base, capabilities)}</div>'
            f"{link}"
            "</article>"
        )
    if cards:
        return "".join(cards)
    return (
        '<article class="compiler-system-card compiler-system-empty">'
        "<h3>No public proof promoted for this route yet.</h3>"
        "<p>The compiler fails closed rather than filling the gap with an unsupported claim.</p>"
        "</article>"
    )


def _options(
    base: ModuleType,
    companies: list[dict[str, Any]],
    selected: str | None,
) -> str:
    return "".join(
        f'<option value="{_escape(base, company.get("company_id", ""))}"'
        f'{" selected" if company.get("company_id") == selected else ""}>'
        f'{_escape(base, company.get("display_name", company.get("company_id", "")))}</option>'
        for company in companies
        if isinstance(company.get("company_id"), str)
    )


def _role_options(
    base: ModuleType,
    company: dict[str, Any] | None,
    selected: str | None,
) -> str:
    if not company:
        return '<option value="">No role route</option>'
    roles = [role for role in company.get("target_roles", []) if isinstance(role, str)]
    if not roles:
        return '<option value="">No role route</option>'
    return "".join(
        f'<option value="{_escape(base, role)}"'
        f'{" selected" if role == selected else ""}>{_escape(base, role)}</option>'
        for role in roles
    )


def _compiler_section(base: ModuleType, payload: dict[str, Any]) -> str:
    companies = [row for row in payload.get("companies", []) if isinstance(row, dict)]
    default = _choose_default_company(payload)
    company_id = str(default.get("company_id")) if default else None
    role = _first_role(default)
    intelligence = default.get("intelligence") if default else None
    if not isinstance(intelligence, dict):
        intelligence = None
    pressure = (
        intelligence.get("observed_current_pressure")
        if intelligence
        else "Source-backed operating pressure has not been loaded for this route."
    )
    bottleneck = (
        intelligence.get("inferred_bottleneck")
        if intelligence
        else "No GlacierEQ bottleneck inference is promoted for this route."
    )
    application_move = (
        intelligence.get("application_move")
        if intelligence
        else default.get("recruiter_thesis") if default else "Select a company route."
    )
    claim_ceiling = default.get("claim_ceiling") if default else None
    freshness = intelligence.get("freshness_state") if intelligence else "NOT_LOADED"
    research_as_of = intelligence.get("research_as_of") if intelligence else None
    freshness_label = (
        freshness.replace("_", " ").title()
        if isinstance(freshness, str)
        else "Unknown"
    )
    if research_as_of:
        freshness_label = f"{freshness_label} · research snapshot {research_as_of}"

    return f'''
    <section class="section shell compiler-section" id="compiler" aria-labelledby="compiler-title">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Portfolio compiler</div>
          <h2 id="compiler-title">Route the evidence to the reviewer</h2>
        </div>
        <p>One evidence graph, projected by company, role, and review depth. Private estate identities and raw estate counts never enter this public surface.</p>
      </div>

      <div class="compiler-controls" aria-label="Projection controls">
        <label>
          <span>Company</span>
          <select id="compiler-company">{_options(base, companies, company_id)}</select>
        </label>
        <label>
          <span>Role</span>
          <select id="compiler-role">{_role_options(base, default, role)}</select>
        </label>
        <label>
          <span>Review depth</span>
          <select id="compiler-depth">
            <option value="recruiter" selected>Recruiter · fastest signal</option>
            <option value="company_reviewer">Company reviewer · targeted proof</option>
            <option value="senior_engineer">Senior engineer · deeper systems</option>
          </select>
        </label>
      </div>

      <div class="compiler-route-header">
        <div>
          <span class="compiler-kicker">Compiled route</span>
          <h3 id="compiler-route-title">{_escape(base, default.get("display_name") if default else "No company route")} · {_escape(base, role or "Role pending")}</h3>
        </div>
        <span class="compiler-freshness" id="compiler-freshness">{_escape(base, freshness_label)}</span>
      </div>

      <div class="compiler-intelligence-grid">
        <article class="compiler-intel-card observed">
          <span class="compiler-state">Observed · source-backed</span>
          <h3>Operating pressure</h3>
          <p id="compiler-pressure">{_escape(base, pressure)}</p>
          <div class="compiler-source-links" id="compiler-sources">{_source_links(base, intelligence)}</div>
        </article>
        <article class="compiler-intel-card inferred">
          <span class="compiler-state">GlacierEQ inference</span>
          <h3>Engineering bottleneck</h3>
          <p id="compiler-bottleneck">{_escape(base, bottleneck)}</p>
        </article>
        <article class="compiler-intel-card intervention">
          <span class="compiler-state">Transferable intervention</span>
          <h3>Application move</h3>
          <p id="compiler-intervention">{_escape(base, application_move)}</p>
        </article>
      </div>

      <div class="compiler-proof-heading">
        <div>
          <span class="compiler-kicker">Role-specific proof</span>
          <h3>Systems selected by capability fit and evidence</h3>
        </div>
        <p id="compiler-claim-ceiling">Claim ceiling: {_escape(base, claim_ceiling or "alignment only")}</p>
      </div>
      <div class="compiler-system-grid" id="compiler-systems">
        {_fallback_system_cards(base, payload, default or {{}}, role)}
      </div>

      <div class="compiler-contract">
        <strong>Truth contract.</strong>
        <span>Observed company pressure is source-backed. Bottlenecks and interventions are explicitly GlacierEQ inferences. Role fit is capability overlap, not affiliation, endorsement, or a hiring prediction.</span>
        <a class="text-link" href="estate-projection.json">Inspect machine projection →</a>
      </div>
    </section>
    '''


def _inject_assets(index: str) -> str:
    css_anchor = '<link rel="stylesheet" href="styles.css">'
    script_anchor = '<script src="app.js" defer></script>'
    if css_anchor not in index or script_anchor not in index:
        raise ProjectionError("Canonical recruiter template asset anchors changed")
    index = index.replace(
        css_anchor,
        css_anchor + '\n  <link rel="stylesheet" href="compiler.css">',
        1,
    )
    index = index.replace(
        script_anchor,
        script_anchor + '\n  <script src="compiler.js" defer></script>',
        1,
    )
    return index


def _inject_nav(index: str) -> str:
    anchor = '<a href="#package">Package</a>'
    if anchor not in index:
        raise ProjectionError("Canonical recruiter navigation anchor changed")
    return index.replace(
        anchor,
        '<a href="#compiler">Compiler</a>\n        ' + anchor,
        1,
    )


def _allow_same_origin_projection(index: str) -> str:
    old = "connect-src 'none'"
    if index.count(old) != 1:
        raise ProjectionError(
            "Canonical CSP no longer has one connect-src 'none' directive"
        )
    return index.replace(old, "connect-src 'self'", 1)


def build(
    output: Path,
    source_commit: str,
    public_projection: Path | None = None,
) -> None:
    base = _load_base_builder()
    base.build(output, source_commit)
    if public_projection is None:
        return

    payload = _load_projection(public_projection)
    validate_public_projection(payload)

    index_path = output / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = _allow_same_origin_projection(index)
    index = _inject_assets(index)
    index = _inject_nav(index)
    marker = "</main>"
    if marker not in index:
        raise ProjectionError("Canonical recruiter template has no </main> marker")
    index = index.replace(
        marker,
        _compiler_section(base, payload) + "\n  " + marker,
        1,
    )
    index_path.write_text(index, encoding="utf-8")

    shutil.copyfile(COMPILER_CSS, output / "compiler.css")
    shutil.copyfile(COMPILER_JS, output / "compiler.js")
    shutil.copyfile(public_projection, output / "estate-projection.json")

    base._assert_public_surface(output)
    base._write_manifest(output, source_commit)
    base._assert_public_surface(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recruiter presentation with an optional public estate projection"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "pages-site",
    )
    parser.add_argument("--source-commit", default="local-uncommitted")
    parser.add_argument("--public-projection", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build(
            args.output.resolve(),
            str(args.source_commit),
            args.public_projection.resolve() if args.public_projection else None,
        )
    except ProjectionError as exc:
        print(f"Compiled recruiter site failed closed: {exc}")
        return 1
    print(f"Compiled recruiter site built at {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
