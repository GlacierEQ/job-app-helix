from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build_recruiter_site.py"
CSS = ROOT / "site" / "compiler.css"
JS = ROOT / "site" / "compiler.js"
PROOF_CSS = ROOT / "site" / "capability_proof_lens.css"
PROOF_JS = ROOT / "site" / "capability_proof_lens.js"
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
    "semantic_capability_proof_is_exact_head_and_public_only",
}
PUBLIC_ADMISSION_STATES = {"PROMOTED", "REFERENCE_ONLY"}


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


def _assert_no_template_markers(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if "{{" in key or "}}" in key:
                raise ProjectionError(
                    f"Unresolved template marker in JSON key {path}.{key}"
                )
            _assert_no_template_markers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_template_markers(child, f"{path}[{index}]")
    elif isinstance(value, str) and ("{{" in value or "}}" in value):
        raise ProjectionError(
            f"Unresolved template marker in JSON string at {path}"
        )


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


def _is_safe_repo_path(value: object) -> bool:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return False
    normalized = value.replace("\\", "/")
    return all(segment not in {"", ".", ".."} for segment in normalized.split("/"))


def _validate_capability_proofs(company: dict[str, Any], path: str) -> None:
    ranked_evidence = company.get("ranked_evidence", [])
    if not isinstance(ranked_evidence, list):
        raise ProjectionError(f"{path}.ranked_evidence must be a list")
    public_evidence_pairs = {
        (row.get("system_id"), row.get("source_repository"))
        for row in ranked_evidence
        if isinstance(row, dict)
        and row.get("visibility") == "public"
        and row.get("visibility_decision") == "PUBLIC_ELIGIBLE"
        and row.get("promotion_state") in PUBLIC_ADMISSION_STATES
        and isinstance(row.get("system_id"), str)
        and isinstance(row.get("source_repository"), str)
    }

    proofs = company.get("capability_proofs", [])
    if not isinstance(proofs, list):
        raise ProjectionError(f"{path}.capability_proofs must be a list")
    seen: set[tuple[str, str]] = set()
    for index, value in enumerate(proofs):
        proof_path = f"{path}.capability_proofs[{index}]"
        if not isinstance(value, dict):
            raise ProjectionError(f"{proof_path} must be an object")
        capability_id = value.get("capability_id")
        system_id = value.get("system_id")
        repository = value.get("source_repository")
        head_sha = value.get("head_sha")
        proof_state = value.get("proof_state")
        admission_state = value.get("admission_state")
        if not isinstance(capability_id, str) or not capability_id:
            raise ProjectionError(f"{proof_path}.capability_id is required")
        if not isinstance(system_id, str) or not system_id:
            raise ProjectionError(f"{proof_path}.system_id is required")
        if not isinstance(repository, str) or not repository.startswith("GlacierEQ/"):
            raise ProjectionError(f"{proof_path}.source_repository is not public-safe")
        if (system_id, repository) not in public_evidence_pairs:
            raise ProjectionError(f"{proof_path} does not match public ranked_evidence")
        if not isinstance(head_sha, str) or re.fullmatch(r"[0-9a-f]{40}", head_sha) is None:
            raise ProjectionError(f"{proof_path}.head_sha must be exact")
        if not isinstance(proof_state, str) or "VERIFIED" not in proof_state:
            raise ProjectionError(f"{proof_path}.proof_state is not verified")
        if admission_state not in PUBLIC_ADMISSION_STATES:
            raise ProjectionError(f"{proof_path}.admission_state is not public")
        key = (capability_id, system_id)
        if key in seen:
            raise ProjectionError(f"duplicate public capability proof: {key}")
        seen.add(key)

        evidence_refs = value.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ProjectionError(f"{proof_path}.evidence_refs must be non-empty")
        if not all(_is_safe_repo_path(ref) for ref in evidence_refs):
            raise ProjectionError(f"{proof_path}.evidence_refs are unsafe")

        receipts = value.get("proof_receipts")
        if not isinstance(receipts, list) or not receipts:
            raise ProjectionError(f"{proof_path}.proof_receipts must be non-empty")
        for receipt_index, receipt in enumerate(receipts):
            receipt_path = f"{proof_path}.proof_receipts[{receipt_index}]"
            if not isinstance(receipt, dict):
                raise ProjectionError(f"{receipt_path} must be an object")
            if receipt.get("kind") != "check_run":
                raise ProjectionError(f"{receipt_path}.kind is unsupported")
            receipt_id = receipt.get("id")
            if not isinstance(receipt_id, int) or receipt_id <= 0:
                raise ProjectionError(f"{receipt_path}.id must be positive")
            if not isinstance(receipt.get("name"), str) or not receipt["name"]:
                raise ProjectionError(f"{receipt_path}.name is required")
            if receipt.get("head_sha") != head_sha:
                raise ProjectionError(f"{receipt_path}.head_sha drifted")
            if receipt.get("conclusion") != "success":
                raise ProjectionError(f"{receipt_path} is not successful")


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
    companies = value.get("company_projections")
    if not isinstance(companies, list):
        raise ProjectionError("company_projections must be a list")
    for index, company in enumerate(companies):
        if not isinstance(company, dict):
            raise ProjectionError(f"company_projections[{index}] must be an object")
        _validate_capability_proofs(company, f"$.company_projections[{index}]")
    _walk(value)
    _assert_no_template_markers(value)


def _assert_compiled_surface(output: Path) -> None:
    allowed_suffixes = {".html", ".css", ".js", ".json", ""}
    for path in output.rglob("*"):
        if path.is_symlink():
            raise ProjectionError(
                f"Deployed surface contains symbolic link: {path}"
            )
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed_suffixes:
            raise ProjectionError(f"Unexpected deployed file type: {path}")
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ProjectionError(
                    f"Invalid deployed JSON in {path}: {exc}"
                ) from exc
            _assert_no_template_markers(value, f"${path.name}")
        elif "{{" in text or "}}" in text:
            raise ProjectionError(
                f"Unresolved template placeholder in {path}"
            )


def _section() -> str:
    return """
    <section class="section compiler-stage" id="compiler"
             aria-labelledby="compiler-title">
      <div class="shell compiler-section">
        <div class="compiler-masthead">
          <div>
            <div class="eyebrow">Application intelligence compiler</div>
            <h2 id="compiler-title">Start with the company problem. Compile the proof.</h2>
          </div>
          <p>Helix projects one canonical evidence graph into the smallest proof
          surface that matters for a specific company, role, and reviewer—without
          exposing private identities or raw estate cardinality.</p>
        </div>

        <div class="compiler-workbench" aria-label="Application compiler controls">
          <div class="compiler-controls">
            <label>
              <span>Target company</span>
              <select id="compiler-company" aria-label="Target company"></select>
            </label>
            <label>
              <span>Target role</span>
              <select id="compiler-role" aria-label="Target role"></select>
            </label>
            <label>
              <span>Review depth</span>
              <select id="compiler-depth" aria-label="Review depth">
                <option value="recruiter">Recruiter · signal</option>
                <option value="company_reviewer">Company reviewer · intervention</option>
                <option value="senior_engineer">Senior engineer · diligence</option>
              </select>
            </label>
          </div>
          <div class="compiler-route-actions">
            <span class="compiler-freshness" id="compiler-freshness">
              Validated public projection
            </span>
            <a class="button button-quiet compiler-route-link"
               id="compiler-route-link" href="#compiler">Share this route</a>
          </div>
        </div>

        <div class="compiler-route-header" aria-live="polite">
          <div>
            <span class="compiler-kicker">Compiled application route</span>
            <h3 id="compiler-route-title">Public projection loading</h3>
          </div>
          <p id="compiler-route-summary">
            Selecting the strongest public evidence path for this reviewer.
          </p>
        </div>

        <ol class="compiler-chain" aria-label="Company problem to proof compilation chain">
          <li>
            <span class="compiler-chain-index">01</span>
            <span class="compiler-chain-label">Operating pressure</span>
            <strong id="compiler-chain-pressure">Source-backed signal</strong>
          </li>
          <li>
            <span class="compiler-chain-index">02</span>
            <span class="compiler-chain-label">Capability route</span>
            <strong id="compiler-chain-capability">Role-fit capabilities</strong>
          </li>
          <li>
            <span class="compiler-chain-index">03</span>
            <span class="compiler-chain-label">Canonical systems</span>
            <strong id="compiler-chain-systems">Promoted proof only</strong>
          </li>
          <li>
            <span class="compiler-chain-index">04</span>
            <span class="compiler-chain-label">Evidence surface</span>
            <strong id="compiler-chain-proof">Fail-closed verification</strong>
          </li>
        </ol>

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

        <div class="compiler-capability-panel">
          <div>
            <span class="compiler-kicker">Capability donor route</span>
            <h3>What the selected systems repeatedly prove</h3>
          </div>
          <div class="compiler-capabilities" id="compiler-capabilities">
            <span class="capability-chip">Capability projection loading</span>
          </div>
        </div>

        <div class="capability-proof-lens" aria-labelledby="capability-proof-title">
          <div class="capability-proof-heading">
            <div>
              <span class="compiler-kicker">Capability proof lens</span>
              <h3 id="capability-proof-title">Inspect why a semantic donor is admissible</h3>
            </div>
            <p id="compiler-capability-proof-summary">
              Exact-head capability proof packets load only for admitted public donors.
            </p>
          </div>
          <div class="capability-proof-grid" id="compiler-capability-proofs" aria-live="polite">
            <article class="capability-proof-card capability-proof-empty">
              <span class="compiler-card-kicker">Proof packet</span>
              <h4>Waiting for a validated company route.</h4>
            </article>
          </div>
        </div>

        <div class="compiler-proof-heading">
          <div>
            <span class="compiler-kicker">Role-specific proof surface</span>
            <h3>Canonical systems selected by fit and verification strength</h3>
          </div>
          <p id="compiler-problem-boundary">
            Dossier gate: projection loading
          </p>
        </div>
        <div class="compiler-system-grid" id="compiler-systems" aria-live="polite">
          <article class="compiler-system-card compiler-system-empty">
            <h3>Loading validated public proof.</h3>
            <p>The rest of the recruiter presentation remains usable if this
            projection is unavailable.</p>
          </article>
        </div>

        <div class="compiler-contract">
          <strong>Truth contract.</strong>
          <span>Observed pressure is source-backed. Bottlenecks and interventions
          are explicitly labeled GlacierEQ inferences. Role fit is capability
          overlap—not affiliation, endorsement, or a hiring prediction.</span>
          <a class="text-link" href="estate-projection.json">
            Inspect machine projection →
          </a>
        </div>
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
            '  <link rel="stylesheet" href="compiler.css">\n'
            '  <link rel="stylesheet" href="capability_proof_lens.css">',
        ),
        (
            '<script src="app.js" defer></script>',
            '<script src="app.js" defer></script>\n'
            '  <script src="compiler.js" defer></script>\n'
            '  <script src="capability_proof_lens.js" defer></script>',
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

    package_anchor = '    <section class="section shell" id="package"'
    if index.count(package_anchor) != 1:
        raise ProjectionError(
            "Canonical recruiter package anchor changed"
        )
    return index.replace(
        package_anchor,
        _section() + "\n" + package_anchor,
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
    shutil.copyfile(PROOF_CSS, output / "capability_proof_lens.css")
    shutil.copyfile(PROOF_JS, output / "capability_proof_lens.js")
    shutil.copyfile(
        public_projection,
        output / "estate-projection.json",
    )
    _assert_compiled_surface(output)
    base._write_manifest(output, source_commit)
    _assert_compiled_surface(output)


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
