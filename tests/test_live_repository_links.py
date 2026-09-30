from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_live_repository_links.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_live_repository_links", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_repository_link_contract_is_synchronized() -> None:
    validator = _load_validator()
    assert validator.validate() == []


def test_live_link_manifest_matches_inventory_exactly() -> None:
    validator = _load_validator()
    inventory = validator._load(validator.INVENTORY)
    links = validator._load(validator.LIVE_LINKS)

    assert set(inventory["workspace_repositories"]) == set(links["repositories"])
    assert inventory["total_repositories"] == len(links["repositories"]) + 1


def test_helix_forbids_copied_repository_payloads() -> None:
    validator = _load_validator()
    links = validator._load(validator.LIVE_LINKS)

    assert links["source_code_copying_into_helix_forbidden"] is True
    assert links["link_mode"] == "live_apex_repository"
    assert "copied_source_tree" in links["forbidden_projection_payloads"]
    assert "manually_duplicated_readme" in links["forbidden_projection_payloads"]
