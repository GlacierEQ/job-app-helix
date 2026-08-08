from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SCHEMA = "glaciereq.external-company-bottleneck-atlas.v1"


def parse_company_intelligence(
    manifest: Mapping[str, Any],
    shards: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise ValueError(
            "external company-intelligence manifest schema is invalid"
        )
    refs = manifest.get("shards")
    count = manifest.get("record_count")
    if not isinstance(refs, list) or not isinstance(count, int):
        raise ValueError(
            "external company-intelligence manifest is incomplete"
        )
    boundary = manifest.get("inference_boundary")
    if not isinstance(boundary, str) or not boundary:
        raise ValueError(
            "external company intelligence requires an inference boundary"
        )

    output: dict[str, dict[str, Any]] = {}
    for index, ref in enumerate(refs):
        if (
            not isinstance(ref, dict)
            or not isinstance(ref.get("path"), str)
        ):
            raise ValueError(
                f"invalid intelligence shard reference at index {index}"
            )
        path = ref["path"]
        shard = shards.get(path)
        if not isinstance(shard, Mapping):
            raise ValueError(f"missing intelligence shard: {path}")
        records = shard.get("records")
        if not isinstance(records, list):
            raise ValueError(f"intelligence shard has no records: {path}")
        declared_count = ref.get("record_count")
        if (
            isinstance(declared_count, int)
            and declared_count != len(records)
        ):
            raise ValueError(
                f"intelligence shard count mismatch: {path}"
            )
        declared_sha = ref.get("shard_sha256")
        embedded_sha = shard.get("shard_sha256")
        if (
            isinstance(declared_sha, str)
            and isinstance(embedded_sha, str)
            and declared_sha != embedded_sha
        ):
            raise ValueError(
                f"intelligence shard digest mismatch: {path}"
            )

        for raw in records:
            if not isinstance(raw, dict):
                raise ValueError(
                    f"invalid company-intelligence row in {path}"
                )
            company_id = raw.get("company_id")
            if not isinstance(company_id, str) or not company_id:
                raise ValueError(
                    f"company-intelligence row has no company_id in {path}"
                )
            if company_id in output:
                raise ValueError(
                    f"duplicate company-intelligence row: {company_id}"
                )

            required_text = (
                "display_name",
                "observed_current_pressure",
                "inferred_bottleneck",
                "inferred_brick_wall",
                "application_move",
                "next_deep_dive",
            )
            for field in required_text:
                if (
                    not isinstance(raw.get(field), str)
                    or not raw[field].strip()
                ):
                    raise ValueError(f"{company_id} lacks {field}")

            leverage = raw.get("leverage")
            if not isinstance(leverage, dict):
                raise ValueError(f"{company_id} lacks leverage")
            for field in ("mechanism", "expected_impact"):
                if (
                    not isinstance(leverage.get(field), str)
                    or not leverage[field].strip()
                ):
                    raise ValueError(
                        f"{company_id} lacks leverage.{field}"
                    )

            sources = raw.get("official_sources")
            if not isinstance(sources, list) or not sources:
                raise ValueError(
                    f"{company_id} lacks official sources"
                )
            normalized_sources: list[dict[str, Any]] = []
            for source in sources:
                if not isinstance(source, dict):
                    raise ValueError(
                        f"{company_id} has invalid official source"
                    )
                url = source.get("url")
                source_sha = source.get("source_sha256")
                title = source.get("title")
                signal = source.get("observed_signal")
                if (
                    not isinstance(url, str)
                    or not url.startswith("https://")
                ):
                    raise ValueError(
                        f"{company_id} has invalid official source URL"
                    )
                if (
                    not isinstance(source_sha, str)
                    or SOURCE_SHA_RE.fullmatch(source_sha) is None
                ):
                    raise ValueError(
                        f"{company_id} has invalid official source hash"
                    )
                if not isinstance(title, str) or not title:
                    raise ValueError(
                        f"{company_id} has invalid official source title"
                    )
                if not isinstance(signal, str) or not signal:
                    raise ValueError(
                        f"{company_id} has invalid observed signal"
                    )
                normalized_sources.append(
                    {
                        "title": title,
                        "url": url,
                        "publisher": source.get("publisher"),
                        "source_sha256": source_sha,
                        "observed_signal": signal,
                    }
                )

            output[company_id] = {
                "research_as_of": manifest.get("research_as_of"),
                "freshness_state": manifest.get("freshness_state"),
                "observed_current_pressure": raw[
                    "observed_current_pressure"
                ],
                "inferred_bottleneck": raw["inferred_bottleneck"],
                "inferred_brick_wall": raw["inferred_brick_wall"],
                "leverage_mechanism": leverage["mechanism"],
                "expected_impact": leverage["expected_impact"],
                "application_move": raw["application_move"],
                "next_deep_dive": raw["next_deep_dive"],
                "official_sources": normalized_sources,
                "inference_boundary": boundary,
            }

    if len(output) != count:
        raise ValueError(
            f"company-intelligence count mismatch: {len(output)} != {count}"
        )
    excluded = manifest.get("excluded_company_ids", [])
    if (
        not isinstance(excluded, list)
        or not all(isinstance(item, str) for item in excluded)
    ):
        raise ValueError("excluded_company_ids must be strings")
    overlap = sorted(set(excluded) & set(output))
    if overlap:
        raise ValueError(
            "excluded company intelligence leaked into snapshot: "
            f"{overlap}"
        )
    return output
