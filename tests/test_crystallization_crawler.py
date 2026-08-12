from __future__ import annotations

import base64
import urllib.parse

from job_app_helix.crystallization_crawler import (
    Repository,
    crawl_estate,
    crawl_repository,
    enumerate_tree,
    list_accessible_repositories,
)


class FakeApi:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, path):
        self.calls.append(path)
        value = self.responses[path]
        if isinstance(value, Exception):
            raise value
        return value


def _blob(text: str):
    return {
        "encoding": "base64",
        "content": base64.b64encode(text.encode()).decode(),
    }


def _repo(name="GlacierEQ/demo", **overrides):
    values = {
        "position": 0,
        "repository": name,
        "repository_id": 1,
        "default_branch": "main",
        "visibility": "private",
        "archived": False,
        "fork": False,
        "can_push": True,
        "can_admin": True,
        "parent": None,
    }
    values.update(overrides)
    return Repository(**values)


def _repo_item(full_name: str, ident: int):
    return {
        "full_name": full_name,
        "id": ident,
        "default_branch": "main",
        "visibility": "private",
        "archived": False,
        "fork": False,
        "permissions": {"push": True, "admin": ident == 1},
    }


def test_accessible_census_includes_owner_org_and_collaborator_pages() -> None:
    query1 = urllib.parse.urlencode(
        {
            "affiliation": "owner,collaborator,organization_member",
            "visibility": "all",
            "sort": "full_name",
            "direction": "asc",
            "per_page": 2,
            "page": 1,
        }
    )
    query2 = query1[:-1] + "2"
    api = FakeApi(
        {
            f"/user/repos?{query1}": [
                _repo_item("GlacierEQ/a", 1),
                _repo_item("hchscasey/b", 2),
            ],
            f"/user/repos?{query2}": [_repo_item("other/c", 3)],
        }
    )

    repositories = list_accessible_repositories(api, per_page=2)

    assert [repo.repository for repo in repositories] == [
        "GlacierEQ/a",
        "hchscasey/b",
        "other/c",
    ]
    assert repositories[0].can_admin is True
    assert repositories[1].can_push is True


def test_all_text_crawl_accounts_every_blob_and_detects_scaffold() -> None:
    tree_path = "/repos/GlacierEQ/demo/git/trees/main?recursive=1"
    api = FakeApi(
        {
            tree_path: {
                "sha": "root",
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "r", "size": 22},
                    {"path": "src/app.py", "type": "blob", "sha": "p", "size": 90},
                    {"path": "image.png", "type": "blob", "sha": "b", "size": 200},
                ],
            },
            "/repos/GlacierEQ/demo/git/blobs/r": _blob("# Demo\nA real program.\n"),
            "/repos/GlacierEQ/demo/git/blobs/p": _blob(
                '"""SCAFFOLD STUB"""\n\ndef run():\n    return "scaffold_allow"\n'
            ),
        }
    )

    result = crawl_repository(api, _repo(), content_mode="all-text")

    assert result["file_count"] == 3
    assert result["all_files_accounted"] is True
    assert result["text_inspected_count"] == 2
    assert result["binary_or_unknown_accounted_count"] == 1
    assert result["requested_text_complete"] is True
    assert result["status"] == "INCOMPLETE"
    assert result["function_definition_count"] == 1
    assert result["readme_headings"] == ["Demo"]
    assert result["scaffold_findings"][0]["path"] == "src/app.py"
    assert {item["path"] for item in result["files"]} == {
        "README.md",
        "src/app.py",
        "image.png",
    }


def test_recursive_tree_truncation_falls_back_to_explicit_subtrees() -> None:
    api = FakeApi(
        {
            "/repos/GlacierEQ/demo/git/trees/main?recursive=1": {
                "sha": "root",
                "truncated": True,
                "tree": [{"path": "README.md", "type": "blob", "sha": "r", "size": 5}],
            },
            "/repos/GlacierEQ/demo/git/trees/main": {
                "sha": "root",
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "r", "size": 5},
                    {"path": "src", "type": "tree", "sha": "srcsha"},
                ],
            },
            "/repos/GlacierEQ/demo/git/trees/root": {
                "sha": "root",
                "truncated": False,
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": "r", "size": 5},
                    {"path": "src", "type": "tree", "sha": "srcsha"},
                ],
            },
            "/repos/GlacierEQ/demo/git/trees/srcsha": {
                "sha": "srcsha",
                "truncated": False,
                "tree": [{"path": "app.py", "type": "blob", "sha": "p", "size": 8}],
            },
        }
    )

    entries, receipt = enumerate_tree(api, _repo())

    assert receipt["strategy"] == "explicit_subtree_walk"
    assert receipt["recursive_response_truncated"] is True
    assert receipt["visited_tree_count"] == 2
    assert [entry["path"] for entry in entries] == ["README.md", "src", "src/app.py"]


def test_oversized_text_is_accounted_but_blocks_semantic_completion() -> None:
    api = FakeApi(
        {
            "/repos/GlacierEQ/demo/git/trees/main?recursive=1": {
                "sha": "root",
                "truncated": False,
                "tree": [
                    {"path": "huge.py", "type": "blob", "sha": "h", "size": 2_000_000}
                ],
            }
        }
    )

    result = crawl_repository(api, _repo(), content_mode="all-text", max_text_bytes=1000)

    assert result["file_count"] == 1
    assert result["oversized_text_count"] == 1
    assert result["unresolved_content_count"] == 1
    assert result["files"][0]["content_state"] == "ACCOUNTED_OVERSIZED_TEXT"
    assert result["status"] == "INCOMPLETE"


def test_tree_only_mode_never_claims_semantic_completion() -> None:
    api = FakeApi(
        {
            "/repos/GlacierEQ/demo/git/trees/main?recursive=1": {
                "sha": "root",
                "truncated": False,
                "tree": [{"path": "README.md", "type": "blob", "sha": "r", "size": 10}],
            }
        }
    )

    receipt = crawl_estate(api, [_repo()], content_mode="tree-only", workers=1)

    assert receipt["all_repository_trees_complete"] is True
    assert receipt["semantic_text_inspection_complete"] is False
    assert receipt["file_accounted_count"] == 1


def test_complete_all_text_shard_can_prove_its_selected_input() -> None:
    api = FakeApi(
        {
            "/repos/GlacierEQ/demo/git/trees/main?recursive=1": {
                "sha": "root",
                "truncated": False,
                "tree": [{"path": "app.py", "type": "blob", "sha": "p", "size": 30}],
            },
            "/repos/GlacierEQ/demo/git/blobs/p": _blob("def run():\n    return 1\n"),
        }
    )

    receipt = crawl_estate(api, [_repo()], content_mode="all-text", workers=1)

    assert receipt["repository_failure_count"] == 0
    assert receipt["all_repository_trees_complete"] is True
    assert receipt["semantic_text_inspection_complete"] is True
    assert receipt["unresolved_content_count"] == 0
    assert receipt["repositories"][0]["status"] == "SOURCE_INSPECTED_NEEDS_PURPOSE_ADJUDICATION"


def test_repository_failure_is_preserved_in_estate_receipt() -> None:
    api = FakeApi(
        {
            "/repos/GlacierEQ/demo/git/trees/main?recursive=1": RuntimeError("boom")
        }
    )

    receipt = crawl_estate(api, [_repo()], content_mode="tree-only", workers=1)

    assert receipt["repository_crawled_count"] == 0
    assert receipt["repository_failure_count"] == 1
    assert receipt["all_repository_trees_complete"] is False
    assert receipt["failures"][0]["repository"] == "GlacierEQ/demo"
