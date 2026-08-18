from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_operations import JobOpening
from job_app_helix.opening_watch import (
    OpeningWatchTarget,
    execute_opening_watch,
    load_watch_manifest,
)


def _opening(url: str, *, title: str) -> JobOpening:
    return JobOpening(
        opening_id=f"opening-{url.rsplit('/', 1)[-1]}",
        company="Anthropic",
        title=title,
        description="Build reliable AI systems with Python and observability.",
        location="Remote",
        requirements=("Python", "observability"),
        preferred=("distributed systems",),
        source="url",
        source_url=url,
        metadata={"source_kind": "job-posting"},
        digest=f"fixture:{url}:{title}",
    )


def test_watch_batches_new_unchanged_and_changed_openings(tmp_path: Path) -> None:
    one = "https://www.anthropic.com/careers/jobs/one"
    two = "https://www.anthropic.com/careers/jobs/two"
    targets = (OpeningWatchTarget(one, "one"), OpeningWatchTarget(two, "two"))
    state = tmp_path / "state"

    first = execute_opening_watch(
        targets,
        state_dir=state,
        fetcher=lambda url: _opening(url, title="AI Systems Engineer"),
    )
    second = execute_opening_watch(
        targets,
        state_dir=state,
        fetcher=lambda url: _opening(
            url,
            title="Senior AI Systems Engineer" if url == two else "AI Systems Engineer",
        ),
    )

    assert first.new_count == 2
    assert first.changed_count == 0
    assert second.unchanged_count == 1
    assert second.changed_count == 1
    changed = next(item for item in second.items if item.status == "CHANGED")
    assert changed.url == two
    assert changed.changed_fields == ("title",)
    assert len(second.receipt_sha256) == 64

    events = (state / "OPENING_CHANGE_EVENTS.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(events) == 4
    receipt = json.loads((state / "OPENING_WATCH_RECEIPT.json").read_text(encoding="utf-8"))
    assert receipt["changed_count"] == 1
    assert receipt["unchanged_count"] == 1


def test_watch_isolates_one_failed_opening_without_stalling_set(tmp_path: Path) -> None:
    good = "https://www.anthropic.com/careers/jobs/good"
    bad = "https://www.anthropic.com/careers/jobs/bad"

    def fetch(url: str) -> JobOpening:
        if url == bad:
            raise RuntimeError("posting unavailable")
        return _opening(url, title="AI Systems Engineer")

    result = execute_opening_watch(
        (OpeningWatchTarget(bad), OpeningWatchTarget(good)),
        state_dir=tmp_path / "state",
        fetcher=fetch,
    )

    assert result.successful_count == 1
    assert result.failed_count == 1
    assert result.new_count == 1
    failed = next(item for item in result.items if item.status == "FAILED_ISOLATED")
    assert "posting unavailable" in (failed.error or "")
    assert next(item for item in result.items if item.url == good).status == "NEW"


def test_watch_rejects_duplicate_urls_before_mutation(tmp_path: Path) -> None:
    url = "https://www.anthropic.com/careers/jobs/duplicate"
    try:
        execute_opening_watch(
            (OpeningWatchTarget(url), OpeningWatchTarget(url)),
            state_dir=tmp_path / "state",
            fetcher=lambda value: _opening(value, title="AI Systems Engineer"),
        )
    except ValueError as exc:
        assert "unique URLs" in str(exc)
    else:
        raise AssertionError("duplicate watch URLs must be rejected")
    assert not (tmp_path / "state").exists()


def test_watch_manifest_loads_labels_and_urls(tmp_path: Path) -> None:
    manifest = tmp_path / "watch.json"
    manifest.write_text(
        json.dumps(
            {
                "openings": [
                    {
                        "url": "https://www.anthropic.com/careers/jobs/123",
                        "label": "frontier-systems",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    targets = load_watch_manifest(manifest)
    assert targets == (
        OpeningWatchTarget(
            "https://www.anthropic.com/careers/jobs/123",
            "frontier-systems",
        ),
    )
