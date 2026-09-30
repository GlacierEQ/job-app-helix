from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_private_crystallization_receipt.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("private_crystallization_publisher", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_publish_creates_missing_private_receipt(monkeypatch) -> None:
    module = _load()
    calls = []

    def fake_request(token, method, url, body=None):
        calls.append((method, url, body))
        if method == "GET":
            return None
        return {"commit": {"sha": "new-commit"}}

    monkeypatch.setattr(module, "_request", fake_request)
    result = module.publish(
        token="secret",
        repository="GlacierEQ/monolith",
        destination="catalog/crystallization/tree-index.json",
        content=b'{"ok":true}\n',
    )

    assert result["commit_sha"] == "new-commit"
    assert result["updated_existing"] is False
    assert calls[0][0] == "GET"
    assert calls[1][0] == "PUT"
    assert "sha" not in calls[1][2]
    assert calls[1][2]["branch"] == "main"


def test_publish_updates_existing_receipt_with_blob_sha(monkeypatch) -> None:
    module = _load()
    calls = []

    def fake_request(token, method, url, body=None):
        calls.append((method, url, body))
        if method == "GET":
            return {"sha": "old-blob"}
        return {"commit": {"sha": "updated-commit"}}

    monkeypatch.setattr(module, "_request", fake_request)
    result = module.publish(
        token="secret",
        repository="GlacierEQ/monolith",
        destination="catalog/crystallization/tree-index.json",
        content=b'{"ok":true}\n',
    )

    assert result["updated_existing"] is True
    assert calls[1][2]["sha"] == "old-blob"


def test_destination_rejects_parent_traversal() -> None:
    module = _load()
    with pytest.raises(module.PublishError):
        module.publish(
            token="secret",
            repository="GlacierEQ/monolith",
            destination="../leak.json",
            content=b"{}",
        )


def test_token_and_repository_are_required() -> None:
    module = _load()
    with pytest.raises(module.PublishError, match="token required"):
        module.publish(
            token="",
            repository="GlacierEQ/monolith",
            destination="catalog/x.json",
            content=b"{}",
        )
    with pytest.raises(module.PublishError, match="owner/name"):
        module.publish(
            token="secret",
            repository="monolith",
            destination="catalog/x.json",
            content=b"{}",
        )
