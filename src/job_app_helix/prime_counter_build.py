"""Build PSYSOC-X-calibrated, evidence-bounded counter-briefs for prime roles.

This adapter applies the verified PSYSOC-X child *calibration principles* to
recruiter, skeptical technical lead, and executive views. It does not claim the
broader AKOS PSYSOC-X stone is an implemented prediction runtime. No sends or
applications occur here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import urlparse


def _safe_url(value: object, *, prefix: str | None = None) -> str:
    if not isinstance(value, str):
        raise ValueError("proof link must be a string")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username:
        raise ValueError(f"proof link must be a public HTTPS URL: {value!r}")
    if prefix and not value.startswith(prefix):
        raise ValueError(f"implementation link outside approved source: {value!r}")
    return value


def _text(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing nonempty {key!r}")
    return value.strip()


def render_case(case: Mapping[str, object]) -> str:
    slug = _text(case, "slug")
    if not slug.replace("-", "").isalnum() or slug.lower() != slug:
        raise ValueError("slug must be lowercase letters, digits and hyphens")
    status = _text(case, "role_status")
    if status not in {"ACTIVE_OFFICIAL", "STALE_REVALIDATE"}:
        raise ValueError(f"unknown role status: {status}")
    role_url = _safe_url(case.get("role_url"))
    portfolio_url = _safe_url(case.get("portfolio_url"))
    raw_proofs = case.get("direct_proofs")
    if not isinstance(raw_proofs, list) or len(raw_proofs) < 2:
        raise ValueError(f"{slug}: at least two direct proof references required")
    proof_lines = []
    for proof in raw_proofs:
        if not isinstance(proof, Mapping):
            raise ValueError(f"{slug}: proof must be an object")
        claim = _text(proof, "mechanism")
        link = _safe_url(proof.get("source"), prefix="https://github.com/GlacierEQ/")
        proof_lines.append(f"| Direct implementation | {claim} | [Inspect source]({link}) |")

    employer = _text(case, "employer")
    role = _text(case, "role")
    return "\n".join(
        [
            f"# {employer} — {role}: Counter-brief",
            "",
            f"**Official role:** [{status}]({role_url}). This status is a dated readback, not continuous monitoring.",
            f"**Existing tailored exhibit:** [Portfolio and role-specific résumé]({portfolio_url}).",
            "",
            "## Recruiter: first 20 seconds",
            "",
            _text(case, "recruiter_hook"),
            "",
            "## Technical hiring manager: claim → mechanism → tradeoff",
            "",
            _text(case, "technical_argument"),
            "",
            "## Executive: delivery consequence",
            "",
            _text(case, "business_consequence"),
            "",
            "## Evidence boundaries",
            "",
            "| Classification | What can be said | Inspection |",
            "|---|---|---|",
            *proof_lines,
            f"| Transferable, not employer production experience | {_text(case, 'transferable')} | [Existing exhibit]({portfolio_url}) |",
            f"| Proposed, not yet deployed at employer | {_text(case, 'proposed')} | Discuss as an engineering plan only |",
            "",
            "## PSYSOC-X skepticism calibration",
            "",
            f"- **Potential objection (hypothesis, not an observed rejection reason):** {_text(case, 'objection_hypothesis')}",
            f"- **Counter-hypothesis:** {_text(case, 'counter_hypothesis')}",
            f"- **Likely technical challenge:** {_text(case, 'technical_challenge')}",
            f"- **Defensible response:** {_text(case, 'defensible_response')}",
            "",
            "## Conversion action and truth gate",
            "",
            f"- **Next move:** {_text(case, 'next_move')}",
            f"- **Unresolved constraint:** {_text(case, 'constraint')}",
            "- No application, send, employer acknowledgment, or interview is implied by this brief.",
            "- Calibration method: AKOS `infinity_stones/psysoc_x.py` child; parent stone remains a target architecture.",
        ]
    ) + "\n"


def build(manifest: Path, output_dir: Path) -> dict[str, object]:
    source = manifest.read_bytes()
    payload = json.loads(source)
    if not isinstance(payload, Mapping) or payload.get("schema") != "glaciereq.prime-counter-builds.v1":
        raise ValueError("invalid prime counter build schema")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 5:
        raise ValueError("expected exactly five prime cases")
    rendered: dict[str, str] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("prime case must be an object")
        slug = _text(case, "slug")
        if slug in rendered:
            raise ValueError(f"duplicate prime case: {slug}")
        rendered[slug] = render_case(case)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for slug, content in sorted(rendered.items()):
        target = output_dir / f"{slug}.md"
        target.write_text(content, encoding="utf-8")
        rows.append({"slug": slug, "file": target.name, "sha256": hashlib.sha256(content.encode()).hexdigest()})
    receipt: dict[str, object] = {
        "schema": "glaciereq.prime-counter-build-receipt.v1",
        "source_manifest": manifest.name,
        "manifest_sha256": hashlib.sha256(source).hexdigest(),
        "status": "BRIEFS_GENERATED_NOT_SENT",
        "cases": rows,
    }
    (output_dir / "BUILD_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile five evidence-checked prime counter-briefs")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(build(args.manifest, args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
