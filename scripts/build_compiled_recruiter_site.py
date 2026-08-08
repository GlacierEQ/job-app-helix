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


class ProjectionError(RuntimeError):
    pass


def _load_base() -> ModuleType:
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


def _load_projection(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectionError(
            f"Unable to load public projection: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ProjectionError("Public projection must be an object")
    return value


def _walk(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise ProjectionError(
                    f"Forbidden estate cardinality at {path}.{key}"
                )
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
    missing = sorted(
        key
        for key in REQUIRED_BOUNDARY
        if boundary.get(key) is not True
    )
    if missing:
        raise ProjectionError(
            f"Public projection boundary failed closed: {missing}"
        )
    if not isinstance(value.get("company_projections"), list):
        raise ProjectionError("company_projections must be a list")
    _walk(value)


def _section() -> str:
    return """
    <section class="section shell compiler-section" id="compiler"
             aria-labelledby="compiler-title">
      <div class="section-heading">
        <div>
          <div class="eyebrow">Portfolio compiler</div>
          <h2 id="compiler-title">Route the evidence to the reviewer</h2>
        </div>
        <p>One canonical evidence graph, projected by company, role, and
        review depth. Private identities and raw estate counts stay internal.</p>
      </div>
      <div class="compiler-controls">
        <label>
          <span>Company</span><select id="compiler-company"></select>
        </label>
        <label>
          <span>Role</span><select id="compiler-role"></select>
        </label>
        <label>
          <span>Review depth</span>
          <select id="compiler-depth">
            <option value="recruiter">Recruiter</option>
            <option value="company_reviewer">Company reviewer</option>
            <option value="senior_engineer">Senior engineer</option>
          </select>
        </label>
      </div>
      <div class="compiler-route-header">
        <div>
          <span class="compiler-kicker">Compiled route</span>
          <h3 id="compiler-route-title">Public projection loading</h3>
        </div>
        <span class="compiler-freshness" id="compiler-freshness">
          Validated public data
        </span>
      </div>
      <div class="compiler-intelligence-grid">
        <article class="compiler-intel-card observed">
          <span class="compiler-state">Observed · source-backed</span>
          <h3>Operating pressure</h3>
          <p id="compiler-pressure">Select a company route.</p>
          <div class="compiler-source-links" id="compiler-sources"></div>
        </article>
        <article class="compiler-intel-card inferred">
          <span class="compiler-state">GlacierEQ inference</span>
          <h3>Engineering bottleneck</h3>
          <p id="compiler-bottleneck">No inference loaded.</p>
        </article>
        <article class="compiler-intel-card intervention">
          <span class="compiler-state">Transferable intervention</span>
          <h3>Application move</h3>
          <p id="compiler-intervention">No intervention loaded.</p>
        </article>
      </div>
      <div class="compiler-proof-heading">
        <div>
          <span class="compiler-kicker">Role-specific proof</span>
          <h3>Systems selected by capability fit and evidence</h3>
        </div>
        <p id="compiler-problem-boundary">
          Dossier gate: projection loading
        </p>
      </div>
      <div class="compiler-system-grid" id="compiler-systems">
        <article class="compiler-system-card compiler-system-empty">
          <h3>Loading validated public proof.</h3>
          <p>The rest of the recruiter presentation remains usable without
          this layer.</p>
        </article>
      </div>
      <div class="compiler-contract">
        <strong>Truth contract.</strong>
        <span>Observed pressure is source-backed. Bottlenecks and interventions
        are GlacierEQ inferences. Role fit is capability overlap—not
        affiliation, endorsement, or a hiring prediction.</span>
        <a class="text-link" href="estate-projection.json">
          Inspect machine projection →
        </a>
      </div>
    </section>
    """


def _inject(index: str) -> str:
    replacements = (
        (
            "connect-src 'none'",
            "connect-src 'self'",
        ),
        (
            '<link rel="stylesheet" href="styles.css">',
            '<link rel="stylesheet" href="styles.css">\n'
            '  <link rel="stylesheet" href="compiler.css">',
        ),
        (
            '<script src="app.js" defer></script>',
            '<script src="app.js" defer></script>\n'
            '  <script src="compiler.js" defer></script>',
        ),
        (
            '<a href="#package">Package</a>',
            '<a href="#compiler">Compiler</a>\n'
            '        <a href="#package">Package</a>',
        ),
    )
    for old, new in replacements:
        if index.count(old) != 1:
            raise ProjectionError(
                f"Canonical recruiter anchor changed: {old}"
            )
        index = index.replace(old, new, 1)
    if "</main>" not in index:
        raise ProjectionError(
            "Canonical recruiter template has no </main>"
        )
    return index.replace(
        "</main>",
        _section() + "\n  </main>",
        1,
    )


def build(
    output: Path,
    source_commit: str,
    public_projection: Path | None = None,
) -> None:
    base = _load_base()
    base.build(output, source_commit)
    if public_projection is None:
        return
    payload = _load_projection(public_projection)
    validate_public_projection(payload)
    index_path = output / "index.html"
    index_path.write_text(
        _inject(index_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    shutil.copyfile(CSS, output / "compiler.css")
    shutil.copyfile(JS, output / "compiler.js")
    shutil.copyfile(
        public_projection,
        output / "estate-projection.json",
    )
    base._assert_public_surface(output)
    base._write_manifest(output, source_commit)
    base._assert_public_surface(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build recruiter site with optional public estate projection"
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/pages-site",
    )
    parser.add_argument(
        "--source-commit",
        default="local-uncommitted",
    )
    parser.add_argument("--public-projection", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build(
            args.output.resolve(),
            str(args.source_commit),
            (
                args.public_projection.resolve()
                if args.public_projection
                else None
            ),
        )
    except ProjectionError as exc:
        print(f"Compiled recruiter site failed closed: {exc}")
        return 1
    print(
        "Compiled recruiter site built at "
        f"{args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
