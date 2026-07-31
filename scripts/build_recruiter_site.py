from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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
PROOF_IDS = (
    "helix_inventory",
    "akos_tests",
    "mesh_rollout",
    "coordinator_tests",
)
EXPECTED_DISPLAY_STATES = {
    "VERIFIED_BOUNDARY": "VERIFIED",
    "VERIFIED_TEST": "VERIFIED",
    "VERIFIED_DOCUMENTATION": "VERIFIED",
    "CANDIDATE_TEST_PROOF": "CANDIDATE",
}
EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<![0-9A-Fa-f])(?:\+?1[\s().-]*)?(?:\(\d{3}\)|\d{3})"
    r"[\s.-]*\d{3}[\s.-]*\d{4}(?![0-9A-Fa-f])"
)
SOURCE_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")

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


class LocalLinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attribute = {"a": "href", "link": "href", "script": "src"}.get(tag)
        if attribute is None:
            return
        for key, value in attrs:
            if key == attribute and value:
                self.links.append(value)


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


def _presentation(claim: dict[str, Any]) -> tuple[str, str, str]:
    presentation = claim.get("presentation")
    if not isinstance(presentation, dict):
        raise SystemExit(f"Claim {claim.get('id')} has no presentation contract")
    values = (
        presentation.get("metric"),
        presentation.get("label"),
        presentation.get("display_state"),
    )
    if not all(isinstance(value, str) and value for value in values):
        raise SystemExit(f"Claim {claim.get('id')} has invalid presentation values")
    metric, label, display_state = values
    expected = EXPECTED_DISPLAY_STATES.get(str(claim.get("state")))
    if display_state != expected:
        raise SystemExit(
            f"Claim {claim.get('id')} presentation state {display_state} "
            f"does not match evidence state {claim.get('state')}"
        )
    if metric not in str(claim.get("claim", "")):
        raise SystemExit(
            f"Claim {claim.get('id')} metric {metric} is absent from its claim text"
        )
    return metric, label, display_state


def _status_badges(claims: dict[str, dict[str, Any]]) -> str:
    cards: list[str] = []
    for claim_id in PROOF_IDS:
        claim = claims[claim_id]
        metric, label, state = _presentation(claim)
        cards.append(
            '<div class="status-badge">'
            f"<strong>{_escape(metric)}</strong>"
            f"<span>{_escape(label)} · {_escape(state)}</span>"
            "</div>"
        )
    return "".join(cards)


def _source_url(source_commit: str, path: str) -> str:
    return f"{REPO_URL}/blob/{source_commit}/{path}"


def _evidence_href(
    claim_id: str,
    claim: dict[str, Any],
    source_commit: str,
) -> str:
    evidence = str(claim.get("evidence", ""))
    if evidence.startswith("https://"):
        return evidence
    if claim_id == "helix_inventory":
        return _source_url(source_commit, "manifests/portfolio_repositories.json")
    if claim_id == "mesh_rollout":
        return _source_url(
            source_commit,
            "docs/README_MESH_ROLLOUT_2026-07-28.md",
        )
    if claim_id == "coordinator_tests":
        return "coordinator-candidate-receipt.json"
    raise SystemExit(f"No deploy-safe evidence route for {claim_id}: {evidence}")


def _proof_cards(
    claims: dict[str, dict[str, Any]],
    source_commit: str,
) -> str:
    rendered: list[str] = []
    for claim_id in PROOF_IDS:
        claim = claims[claim_id]
        metric, label, state = _presentation(claim)
        state_class = "candidate" if state == "CANDIDATE" else ""
        evidence_href = _evidence_href(claim_id, claim, source_commit)
        rendered.append(
            '<article class="card proof-card">'
            f'<span class="state {state_class}">{_escape(state)}</span>'
            f'<div class="metric">{_escape(metric)}</div>'
            f'<h3>{_escape(label)}</h3>'
            f'<p>{_escape(claim["claim"])}</p>'
            f'<a href="{_escape(evidence_href)}">Inspect evidence →</a>'
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
    missing = sorted(set((*PROOF_IDS, "runner_activation")) - set(by_id))
    if missing:
        raise SystemExit(f"missing recruiter proof claims: {missing}")

    if by_id["akos_tests"].get("state") != "VERIFIED_TEST":
        raise SystemExit("AKOS proof must remain VERIFIED_TEST")
    if not by_id["akos_tests"].get("source_commit"):
        raise SystemExit("AKOS proof must pin a source commit")
    if by_id["coordinator_tests"].get("state") != "CANDIDATE_TEST_PROOF":
        raise SystemExit("coordinator proof must remain candidate evidence")
    runner_state = by_id["runner_activation"].get("state")
    if runner_state != "IMPLEMENTED_ACTIVATION_BLOCKED":
        raise SystemExit("APEX runner activation must remain explicitly blocked")

    for claim_id in PROOF_IDS:
        _presentation(by_id[claim_id])
    return by_id


def _validate_output_path(output: Path) -> None:
    resolved = output.resolve()
    protected = (
        ROOT,
        SITE_SOURCE,
        CANDIDATE_ROOT,
        ROOT / "src",
        ROOT / "scripts",
        ROOT / "tests",
    )
    for path in protected:
        protected_path = path.resolve()
        if resolved == protected_path:
            raise SystemExit(f"Refusing destructive output path: {resolved}")
        if protected_path.is_relative_to(resolved):
            raise SystemExit(f"Output path contains protected source: {resolved}")
        if resolved.is_relative_to(protected_path) and protected_path != ROOT:
            raise SystemExit(f"Output path is inside protected source: {resolved}")


def _copy_public_sources(output: Path) -> None:
    copies = {
        SITE_SOURCE / "styles.css": output / "styles.css",
        SITE_SOURCE / "app.js": output / "app.js",
        CANDIDATE_ROOT / "candidate_node.json": output / "candidate-node.json",
        CANDIDATE_ROOT / "application_spiral.json": output / "application-spiral.json",
        CANDIDATE_ROOT / "evidence_ledger.json": output / "evidence-ledger.json",
        CANDIDATE_ROOT / "package_mesh.json": output / "package-mesh.json",
        CANDIDATE_ROOT / "coordinator_candidate_receipt.json": (
            output / "coordinator-candidate-receipt.json"
        ),
    }
    for source, destination in copies.items():
        if source.is_symlink():
            raise SystemExit(f"Refusing symbolic-link source: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (output / ".nojekyll").write_text("", encoding="utf-8")


def _write_source_urls(output: Path, source_commit: str) -> None:
    payload = {
        "schema": "glaciereq.recruiter-source-urls.v1",
        "source_commit": source_commit,
        "executive_resume": _source_url(
            source_commit,
            "hire_package/casey-barton/EXECUTIVE_RESUME.md",
        ),
        "technical_portfolio_brief": _source_url(
            source_commit,
            "hire_package/casey-barton/TECHNICAL_PORTFOLIO_BRIEF.md",
        ),
        "claim_register": _source_url(
            source_commit,
            "hire_package/casey-barton/CLAIM_REGISTER.md",
        ),
        "deployment_contract": _source_url(
            source_commit,
            "docs/RECRUITER_SITE_DEPLOYMENT.md",
        ),
    }
    (output / "source-urls.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _local_target(output: Path, link: str) -> Path | None:
    parsed = urlsplit(link)
    if parsed.scheme or parsed.netloc or link.startswith("#"):
        return None
    relative = parsed.path
    if not relative:
        return None
    target = (output / relative).resolve()
    if not target.is_relative_to(output.resolve()):
        raise SystemExit(f"Local link escapes deployment root: {link}")
    return target


def _validate_local_links(output: Path) -> None:
    parser = LocalLinkCollector()
    parser.feed((output / "index.html").read_text(encoding="utf-8"))
    missing: list[str] = []
    for link in parser.links:
        target = _local_target(output, link)
        if target is not None and not target.is_file():
            missing.append(link)
    if missing:
        raise SystemExit(f"Deployed site has broken local links: {sorted(missing)}")


def _assert_public_surface(output: Path) -> None:
    allowed_suffixes = {".html", ".css", ".js", ".json", ""}
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
        if path.name != "deployment-manifest.json" and (
            EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text)
        ):
            raise SystemExit(f"Direct recruiter contact data leaked into {path}")
    _validate_local_links(output)


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
    _validate_output_path(output)
    if (
        source_commit != "local-uncommitted"
        and SOURCE_COMMIT_PATTERN.fullmatch(source_commit) is None
    ):
        raise SystemExit("source commit must be a 40-character lowercase SHA")

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
    resume_url = _source_url(
        source_commit,
        "hire_package/casey-barton/EXECUTIVE_RESUME.md",
    )
    brief_url = _source_url(
        source_commit,
        "hire_package/casey-barton/TECHNICAL_PORTFOLIO_BRIEF.md",
    )
    replacements = {
        "{{CANDIDATE}}": _escape(candidate["candidate"]),
        "{{PRIMARY_ROLE}}": _escape(" · ".join(roles)),
        "{{STATUS_BADGES}}": _status_badges(claims),
        "{{PROOF_CARDS}}": _proof_cards(claims, source_commit),
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
        "executive-resume.md": _escape(resume_url),
        "technical-portfolio-brief.md": _escape(brief_url),
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    machine_anchor = (
        '<a class="text-link" href="candidate-node.json">Open machine path →</a>'
    )
    machine_links = (
        machine_anchor
        + '\n          <a class="text-link" href="package-mesh.json">'
        + "Open package mesh →</a>"
    )
    rendered = rendered.replace(machine_anchor, machine_links)
    (output / "index.html").write_text(rendered, encoding="utf-8")

    _copy_public_sources(output)
    _write_source_urls(output, source_commit)
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
