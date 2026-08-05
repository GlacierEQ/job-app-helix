"""Regression tests for the 48-track company-intelligence plane."""

from pathlib import Path

from job_app_helix.company_intelligence import (
    EXPECTED_TRACK_IDS,
    build_packets,
    load_expanded_atlas,
    validate_atlas,
    validate_index,
)

ROOT = Path(__file__).resolve().parents[1]


def test_exact_boundary() -> None:
    atlas = load_expanded_atlas(ROOT)
    company_ids = tuple(record["company_id"] for record in atlas["records"])
    assert company_ids == EXPECTED_TRACK_IDS
    assert validate_atlas(atlas)["silent_omissions"] == 0


def test_memory_packets() -> None:
    atlas = load_expanded_atlas(ROOT)
    packets, measurement = build_packets(atlas)
    memory_keys = {packet["memory_key"] for packet in packets}
    assert len(packets) == 48
    assert len(memory_keys) == 48
    assert measurement["after"] < measurement["before"]


def test_gatling_and_index() -> None:
    result = validate_index(ROOT)
    assert result["status"] == "PASS"
    assert result["gatling"]["specialist_tasks"] == 384
    assert result["silent_omissions"] == 0
