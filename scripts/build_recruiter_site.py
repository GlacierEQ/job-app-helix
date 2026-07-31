from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site"
CANDIDATE_ROOT = ROOT / "hire_package" / "casey-barton"
REPO_URL = "https://github.com/GlacierEQ/job-app-helix"
CANONICAL_SPIRAL = [
    "OBSERVE",
    "RECOVER",
    "PLAN",
    "ROUTE",
    "ACT",
    "VERIFY",
    "PERSIST",
    "RESUME",
]
RELATION_ENUM = {
    "GOVERNED_BY",
    "ORCHESTRATES",
    "VERIFIES",
    "PROVIDES_CAPABILITY",
    "CONSUMES",
    "EXTENDS",
    "PERSISTS_RECEIPTS_TO",
    "EXECUTES_THROUGH",
}
FORBIDDEN_PUBLIC_PATTERNS = (
    re.compile(r"\b808[-.\s]?936[-.\s]?5654\b"),
    re.compile(r"glacier\.equilibrium@gmail\.com", re.IGNORECASE),
)

ROLE_COPY = {
    "Applied AI Architect": {
        "summary": (
            "Designs the application, governance, and verification layers that turn "
            "model capability into durable operating systems."
        ),
        "signals": [
            "agent orchestration",
            "MCP and tool boundaries",
            "evidence architecture",
        ],
    },
    "Forward-Deployed AI Engineer": {
        "summary": (
            "Translates ambiguous operator needs into bounded implementations, "
            "measurable acceptance criteria, and resumable delivery paths."
        ),
        "signals": [
            "discovery under ambiguity",
            "integration ownership",
            "operator-facing delivery",
        ],
    },
    "Agent Infrastructure Engineer": {
        "summary": (
            "Builds deterministic scheduling, permissions, receipts, context routing, "
            "and failure semantics around probabilistic agents."
        ),
        "signals": [
            "typed coordination",
            "least-privilege execution",
            "observability and provenance",
        ],
    },
}

PROOF_PRESENTATION = {
    "helix_inventory": ("66", "Exact portfolio boundary", "VERIFIED"),
    "akos_tests": ("94/94", "AKOS tests passed", "VERIFIED"),
    "mesh_rollout": ("21", "README Mesh nodes", "VERIFIED"),
    "coordinator_tests": ("62/62", "Coordinator candidate tests", "CANDIDATE"),
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to load JSON contract {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected object at {path}")
    return payload


def _timestamp_is_aware(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _list_items(values: list[str]) -> str:
    if not values:
        return "<li>None recorded.</li>"
    return "".join(f"<li>{_escape(value)}</li>" for value in values)


def _status_badges(claims: dict[str, dict[str, Any]]) -> str:
    cards: list[str] = []
    for claim_id in (
        "helix_inventory",
        "akos_tests",
        "mesh_rollout",
        "coordinator_tests",
    ):
        if claim_id not in claims:
            raise SystemExit(f"Missing status claim: {claim_id}")
        metric, label, state = PROOF_PRESENTATION[claim_id]
        cards.append(
            '<div class="status-badge">'
            f"<strong>{_escape(metric)}</strong>"
            f"<span>{_escape(label)} · {_escape(state)}</span>"
            "</div>"
        )
    return "".join(cards)


def _evidence_href(claim_id: str, claim: dict[str, Any]) -> str:
    evidence = str(claim.get("evidence", ""))
    if evidence.startswith("https://"):
        return evidence
    if claim_id == "helix_inventory":
        return f"{REPO_URL}/blob/main/manifests/portfolio_repositories.json"
    if claim_id == "mesh_rollout":
        return f"{REPO_URL}/blob/main/docs/README_MESH_ROLLOUT_2026-07-28.md"
    if claim_id == "coordinator_tests":
        return "coordinator-candidate-receipt.json"
    raise SystemExit(f"No deploy-safe evidence route for {claim_id}: {evidence}")


def _proof_cards(claims: dict[str, dict[str, Any]]) -> str:
    rendered: list[str] = []
    for claim_id in (
        "helix_inventory",
        "akos_tests",
        "mesh_rollout",
        "coordinator_tests",
    ):
        claim = claims[claim_id]
        metric, label, state = PROOF_PRESENTATION[claim_id]
        state_class = "candidate" if state == "CANDIDATE" else ""
        rendered.append(
            '<article class="card proof-card">'
            f'<span class="state {state_class}">{_escape(state)}</span>'
            f'<div class="metric">{_escape(metric)}</div>'
            f'<h3>{_escape(label)}</h3>'
            f'<p>{_escape(claim["claim"])}</p>'
            f'<a href="{_escape(_evidence_href(claim_id, claim))}">'
            "Inspect evidence →</a>"
            "</article>"
        )
    return "".join(rendered)


def _role_cards(roles: list[str]) -> str:
    cards: list[str] = []
    for role in roles:
        if role not in ROLE_COPY:
            raise SystemExit(f"Primary role has no presentation contract: {role}")
        copy = ROLE_COPY[role]
        signals = "".join(
            f"<li>{_escape(signal)}</li>" for signal in copy["signals"]
        )
        cards.append(
            '<article class="card role-card">'
            f"<h3>{_escape(role)}</h3>"
            f"<p>{_escape(copy['summary'])}</p>"
            f"<ul>{signals}</ul>"
            "</article>"
        )
    return "".join(cards)


def _spiral_steps(stages: list[dict[str, Any]]) -> str:
    ordered = [str(stage.get("name", "")) for stage in stages]
    if ordered != CANONICAL_SPIRAL:
        raise SystemExit(f"Spiral contract drift: {ordered}")
    return "".join(
        "<li>"
        f"<strong>{_escape(stage['name'])}</strong>"
        f"<span>{_escape(stage['output'])}</span>"
        "</li>"
        for stage in stages
    )


def _validate_contracts(
    candidate: dict[str, Any],
    ledger: dict[str, Any],
    spiral: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    status = candidate.get("status")
    if not isinstance(status, dict):
        raise SystemExit("candidate status must be an object")
    if not _timestamp_is_aware(str(status.get("verified_at", ""))):
        raise SystemExit("candidate verified_at must be timezone-aware")
    if not _timestamp_is_aware(str(ledger.get("generated_at", ""))):
        raise SystemExit("evidence ledger generated_at must be timezone-aware")

    roles = candidate.get("primary_role_variants")
    if not isinstance(roles, list) or not roles:
        raise SystemExit("candidate must declare primary role variants")
    unknown_roles = sorted(set(str(role) for role in roles) - set(ROLE_COPY))
    if unknown_roles:
        raise SystemExit(f"unroutable primary role variants: {unknown_roles}")

    relationships = candidate.get("relationships")
    if not isinstance(relationships, list):
        raise SystemExit("candidate relationships must be a list")
    for relation in relationships:
        if not isinstance(relation, dict):
            raise SystemExit(f"unsupported relationship: {relation}")
        if relation.get("relation") not in RELATION_ENUM:
            raise SystemExit(f"unsupported relationship: {relation}")

    stages = spiral.get("stages")
    if not isinstance(stages, list):
        raise SystemExit("application spiral stages must be a list")
    stage_names = [
        stage.get("name") for stage in stages if isinstance(stage, dict)
    ]
    if stage_names != CANONICAL_SPIRAL:
        raise SystemExit("application spiral does not match canonical stage order")

    claims = ledger.get("claims")
    if not isinstance(claims, list):
        raise SystemExit("evidence ledger claims must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            raise SystemExit(f"invalid evidence claim: {claim}")
        claim_id = claim.get("id")
        if not isinstance(claim_id, str):
            raise SystemExit(f"invalid evidence claim: {claim}")
        by_id[claim_id] = claim
    missing = sorted(set(PROOF_PRESENTATION) - set(by_id))
    if missing:
        raise SystemExit(f"missing recruiter proof claims: {missing}")

    if by_id["akos_tests"].get("state") != "VERIFIED_TEST":
        raise SystemExit("AKOS proof must remain VERIFIED_TEST")
    if not by_id["akos_tests"].get("source_commit"):
        raise SystemExit("AKOS proof must pin a source commit")
    if by_id["coordinator_tests"].get("state") != "CANDIDATE_TEST_PROOF":
        raise SystemExit("coordinator proof must remain candidate evidence")

    return by_id


def _copy_public_sources(output: Path) -> None:
    copies = {
        SITE_SOURCE / "styles.css": output / "styles.css",
        SITE_SOURCE / "app.js": output / "app.js",
        CANDIDATE_ROOT / "EXECUTIVE_RESUME.md": output / "executive-resume.md",
        CANDIDATE_ROOT / "TECHNICAL_PORTFOLIO_BRIEF.md": (
            output / "technical-portfolio-brief.md"
        ),
        CANDIDATE_ROOT / "CLAIM_REGISTER.md": output / "claim-register.md",
        CANDIDATE_ROOT / "candidate_node.json": output / "candidate-node.json",
        CANDIDATE_ROOT / "application_spiral.json": (
            output / "application-spiral.json"
        ),
        CANDIDATE_ROOT / "evidence_ledger.json": output / "evidence-ledger.json",
        CANDIDATE_ROOT / "coordinator_candidate_receipt.json": (
            output / "coordinator-candidate-receipt.json"
        ),
        ROOT / "RECRUITER_EXECUTIVE_SUMMARY.md": (
            output / "recruiter-executive-summary.md"
        ),
    }
    for source, destination in copies.items():
        if source.is_symlink():
            raise SystemExit(f"Refusing symbolic-link source: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (output / ".nojekyll").write_text("", encoding="utf-8")


def _assert_public_surface(output: Path) -> None:
    allowed_suffixes = {".html", ".css", ".js", ".md", ".json", ""}
    for path in output.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"Deployed surface contains symbolic link: {path}")
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed_suffixes:
            raise SystemExit(f"Unexpected deployed file type: {path}")
        text = path.read_text(encoding="utf-8")
        if "{{" in text or "}}" in text:
            raise SystemExit(f"Unresolved template placeholder in {path}")
        for pattern in FORBIDDEN_PUBLIC_PATTERNS:
            if pattern.search(text):
                raise SystemExit(f"Direct recruiter PII leaked into {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(output: Path, source_commit: str) -> None:
    files = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "deployment-manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    manifest = {
        "schema": "glaciereq.recruiter-pages-deployment.v1",
        "source_repository": "GlacierEQ/job-app-helix",
        "source_branch": "main",
        "source_commit": source_commit,
        "entrypoint": "index.html",
        "candidate_surface": "hire_package/casey-barton",
        "files": files,
    }
    (output / "deployment-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build(output: Path, source_commit: str) -> None:
    candidate = _load_json(CANDIDATE_ROOT / "candidate_node.json")
    ledger = _load_json(CANDIDATE_ROOT / "evidence_ledger.json")
    spiral = _load_json(CANDIDATE_ROOT / "application_spiral.json")
    claims = _validate_contracts(candidate, ledger, spiral)

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    status = candidate["status"]
    roles = [str(role) for role in candidate["primary_role_variants"]]
    template = (SITE_SOURCE / "template.html").read_text(encoding="utf-8")
    replacements = {
        "{{CANDIDATE}}": _escape(candidate["candidate"]),
        "{{PRIMARY_ROLE}}": _escape(" · ".join(roles)),
        "{{STATUS_BADGES}}": _status_badges(claims),
        "{{PROOF_CARDS}}": _proof_cards(claims),
        "{{ROLE_CARDS}}": _role_cards(roles),
        "{{SPIRAL_STEPS}}": _spiral_steps(spiral["stages"]),
        "{{VERIFIED_LIST}}": _list_items(
            list(status.get("verified_scope", []))
        ),
        "{{BLOCKED_LIST}}": _list_items(
            list(status.get("blocked_scope", []))
        ),
        "{{UNVERIFIED_LIST}}": _list_items(
            list(status.get("unverified_scope", []))
        ),
        "{{SOURCE_COMMIT}}": _escape(source_commit),
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    (output / "index.html").write_text(rendered, encoding="utf-8")

    _copy_public_sources(output)
    _assert_public_surface(output)
    _write_manifest(output, source_commit)
    _assert_public_surface(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the canonical recruiter GitHub Pages surface"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "pages-site",
        help="Output directory",
    )
    parser.add_argument(
        "--source-commit",
        default=os.environ.get("GITHUB_SHA", "local-uncommitted"),
        help="Immutable source commit recorded in deployment-manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build(args.output.resolve(), str(args.source_commit))
    print(f"Recruiter site built at {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
