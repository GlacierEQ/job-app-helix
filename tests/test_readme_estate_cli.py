from __future__ import annotations

from job_app_helix.readme_estate_cli import (
    extract_legacy_repository_ids,
    extract_library_repository_ids,
)


def test_legacy_census_reads_only_domain_repository_arrays() -> None:
    payload = {
        "functional_heads": {
            "legal": {
                "name": "Legal Case Operations",
                "kind": "VIRTUAL_HEAD",
                "mission": "This sentence must never become a repository id.",
                "subcategories": {
                    "TECH": {
                        "domains": {
                            "LEGAL": ["DOCKETS", "GlacierEQ/CourtClerk"],
                            "EMPTY": [],
                        }
                    },
                    "DATA": {"domains": {"LEGAL": ["CASE-LAW-ARSENAL"]}},
                },
                "_total_repos": 3,
            }
        }
    }
    assert extract_legacy_repository_ids(payload, "GlacierEQ") == {
        "GlacierEQ/DOCKETS",
        "GlacierEQ/CourtClerk",
        "GlacierEQ/CASE-LAW-ARSENAL",
    }


def test_legacy_census_ignores_malformed_non_list_domains() -> None:
    payload = {
        "functional_heads": {
            "x": {
                "subcategories": {
                    "TECH": {
                        "domains": {
                            "BAD_STRING": "not-a-repository-array",
                            "BAD_OBJECT": {"repo": "also-not-a-domain-array"},
                        }
                    }
                }
            }
        }
    }
    assert extract_legacy_repository_ids(payload, "GlacierEQ") == set()


def test_library_census_accepts_qualified_and_unqualified_names() -> None:
    payload = {
        "entries": [
            {"name": "monolith"},
            {"full_name": "GlacierEQ/mega-skills"},
            {"repository": "job-app-helix"},
            {"description": "not an identity"},
        ]
    }
    assert extract_library_repository_ids(payload, "GlacierEQ") == {
        "GlacierEQ/monolith",
        "GlacierEQ/mega-skills",
        "GlacierEQ/job-app-helix",
    }
