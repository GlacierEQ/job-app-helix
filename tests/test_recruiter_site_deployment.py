from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "scripts" / "build_recruiter_site.py"
SOURCE_COMMIT = "a" * 40


class LinkCollector(HTMLParser):
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


def _load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "build_recruiter_site",
        BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_recruiter_site_builds_from_canonical_candidate_records(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"

    builder.build(output, SOURCE_COMMIT)

    index = (output / "index.html").read_text(encoding="utf-8")
    assert "Casey Del Carpio Barton" in index
    assert "Applied AI Architect" in index
    assert "Forward-Deployed AI Engineer" in index
    assert "Agent Infrastructure Engineer" in index
    assert "94/94" in index
    assert "62/62" in index
    assert "CANDIDATE" in index
    assert "OBSERVE" in index and "RESUME" in index
    assert SOURCE_COMMIT in index
    assert f"/blob/{SOURCE_COMMIT}/" in index
    assert "package-mesh.json" in index
    assert "{{" not in index and "}}" not in index

    assert (output / "candidate-node.json").is_file()
    assert (output / "package-mesh.json").is_file()
    assert (output / "source-urls.json").is_file()


@pytest.mark.parametrize(
    "synthetic_contact",
    [
        "candidate@example.invalid",
        "(555) 123-4567",
        "+1 555.123.4567",
    ],
)
def test_public_surface_rejects_generic_contact_data(
    tmp_path: Path,
    synthetic_contact: str,
) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT)
    (output / "injected.json").write_text(
        json.dumps({"contact": synthetic_contact}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="contact data"):
        builder._assert_public_surface(output)


def test_deployment_manifest_hashes_every_payload(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT)

    manifest = json.loads(
        (output / "deployment-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "glaciereq.recruiter-pages-deployment.v1"
    assert manifest["source_commit"] == SOURCE_COMMIT
    assert manifest["entrypoint"] == "index.html"
    assert manifest["files"]

    recorded = {entry["path"]: entry for entry in manifest["files"]}
    actual = {
        path.relative_to(output).as_posix(): path
        for path in output.rglob("*")
        if path.is_file() and path.name != "deployment-manifest.json"
    }
    assert set(recorded) == set(actual)
    for relative, path in actual.items():
        assert recorded[relative]["bytes"] == path.stat().st_size
        assert recorded[relative]["sha256"] == _sha256(path)


def test_local_site_links_resolve_inside_deployment(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build(output, SOURCE_COMMIT)

    parser = LinkCollector()
    parser.feed((output / "index.html").read_text(encoding="utf-8"))
    local_links = [
        link
        for link in parser.links
        if not link.startswith(("#", "https://", "http://", "mailto:"))
    ]
    assert local_links
    missing = [link for link in local_links if not (output / link).is_file()]
    assert missing == []


def test_candidate_state_semantics_remain_distinct() -> None:
    candidate = json.loads(
        (ROOT / "hire_package" / "casey-barton" / "candidate_node.json").read_text(
            encoding="utf-8"
        )
    )
    ledger = json.loads(
        (ROOT / "hire_package" / "casey-barton" / "evidence_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    status = candidate["status"]
    assert "APEX GitHub App bridge activation" in status["blocked_scope"]
    assert "agent coordinator hosted multi-version promotion" in status["unverified_scope"]

    claims = {claim["id"]: claim for claim in ledger["claims"]}
    assert claims["akos_tests"]["state"] == "VERIFIED_TEST"
    assert claims["coordinator_tests"]["state"] == "CANDIDATE_TEST_PROOF"
    assert claims["runner_activation"]["state"] == "IMPLEMENTED_ACTIVATION_BLOCKED"
    assert claims["akos_tests"]["presentation"]["metric"] == "94/94"


def test_output_path_cannot_delete_repository_or_source_directories(tmp_path: Path) -> None:
    builder = _load_builder()

    for forbidden in (
        ROOT,
        ROOT.parent,
        ROOT / "site",
        ROOT / "hire_package" / "casey-barton" / "generated",
    ):
        with pytest.raises(SystemExit, match="output path|protected source"):
            builder.build(forbidden, SOURCE_COMMIT)

    safe = tmp_path / "site"
    builder.build(safe, SOURCE_COMMIT)
    assert (safe / "index.html").is_file()


def test_site_source_has_accessibility_and_security_baseline() -> None:
    template = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
    styles = (ROOT / "site" / "styles.css").read_text(encoding="utf-8")
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    assert 'class="skip-link"' in template
    assert 'id="main"' in template
    assert 'aria-label="Primary navigation"' in template
    assert 'role="tablist"' in template
    assert "Content-Security-Policy" in template
    assert "connect-src 'none'" in template
    assert "prefers-reduced-motion" in styles
    assert "aria-selected" in script
    assert "ArrowLeft" in script and "ArrowRight" in script
