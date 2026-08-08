from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import EstateCompilerError, load_json

SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SCHEMA = "glaciereq.external-company-bottleneck-atlas.v1"


def load_external_company_intelligence(
    root: Path,
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise EstateCompilerError("External company-intelligence manifest schema is invalid")
    shards = manifest.get("shards")
    record_count = manifest.get("record_count")
    if not isinstance(shards, list) or not isinstance(record_count, int):
        raise EstateCompilerError("External company-intelligence manifest is incomplete")

    inference_boundary = manifest.get("inference_boundary")
    if not isinstance(inference_boundary, str) or not inference_boundary:
        raise EstateCompilerError("External company intelligence requires an inference boundary")

    output: dict[str, dict[str, Any]] = {}
    for shard_ref in shards:
        if not isinstance(shard_ref, dict) or not isinstance(shard_ref.get("path"), str):
            raise EstateCompilerError("External company-intelligence shard reference is invalid")
        shard = load_json((root / shard_ref["path"]).resolve())
        records = shard.get("records")
        if not isinstance(records, list):
            raise EstateCompilerError(f"Company-intelligence shard has no records: {shard_ref['path']}")
        declared = shard_ref.get("record_count")
        if isinstance(declared, int) and declared != len(records):
            raise EstateCompilerError(
                f"Company-intelligence shard count mismatch: {shard_ref['path']}"
            )
        for record in records:
            if not isinstance(record, dict):
                raise EstateCompilerError("Company-intelligence record must be an object")
            company_id = record.get("company_id")
            if not isinstance(company_id, str) or not company_id:
                raise EstateCompilerError("Company-intelligence record has no company_id")
            if company_id in output:
                raise EstateCompilerError(f"Duplicate company-intelligence record: {company_id}")
            for field in (
                "display_name",
                "observed_current_pressure",
                "inferred_bottleneck",
                "inferred_brick_wall",
                "application_move",
                "next_deep_dive",
            ):
                if not isinstance(record.get(field), str) or not record[field].strip():
                    raise EstateCompilerError(
                        f"Company-intelligence record {company_id} lacks {field}"
                    )
            leverage = record.get("leverage")
            if not isinstance(leverage, dict):
                raise EstateCompilerError(
                    f"Company-intelligence record {company_id} lacks leverage"
                )
            for field in ("mechanism", "expected_impact"):
                if not isinstance(leverage.get(field), str) or not leverage[field].strip():
                    raise EstateCompilerError(
                        f"Company-intelligence record {company_id} lacks leverage.{field}"
                    )
            sources = record.get("official_sources")
            if not isinstance(sources, list) or not sources:
                raise EstateCompilerError(
                    f"Company-intelligence record {company_id} lacks official sources"
                )
            public_sources: list[dict[str, Any]] = []
            for source in sources:
                if not isinstance(source, dict):
                    raise EstateCompilerError(
                        f"Company-intelligence source for {company_id} is invalid"
                    )
                url = source.get("url")
                sha = source.get("source_sha256")
                title = source.get("title")
                signal = source.get("observed_signal")
                if not isinstance(url, str) or not url.startswith("https://"):
                    raise EstateCompilerError(
                        f"Company-intelligence source URL is invalid: {company_id}"
                    )
                if not isinstance(sha, str) or SOURCE_SHA_RE.fullmatch(sha) is None:
                    raise EstateCompilerError(
                        f"Company-intelligence source hash is invalid: {company_id}"
                    )
                if not isinstance(title, str) or not title:
                    raise EstateCompilerError(
                        f"Company-intelligence source title is invalid: {company_id}"
                    )
                if not isinstance(signal, str) or not signal:
                    raise EstateCompilerError(
                        f"Company-intelligence observed signal is invalid: {company_id}"
                    )
                public_sources.append(
                    {
                        "title": title,
                        "url": url,
                        "source_sha256": sha,
                        "observed_signal": signal,
                        "publisher": source.get("publisher"),
                    }
                )
            output[company_id] = {
                "research_as_of": manifest.get("research_as_of"),
                "freshness_state": manifest.get("freshness_state"),
                "observed_current_pressure": record["observed_current_pressure"],
                "inferred_bottleneck": record["inferred_bottleneck"],
                "inferred_brick_wall": record["inferred_brick_wall"],
                "leverage_mechanism": leverage["mechanism"],
                "expected_impact": leverage["expected_impact"],
                "application_move": record["application_move"],
                "next_deep_dive": record["next_deep_dive"],
                "official_sources": public_sources,
                "inference_boundary": inference_boundary,
            }

    if len(output) != record_count:
        raise EstateCompilerError(
            f"External company-intelligence count mismatch: {len(output)} != {record_count}"
        )
    excluded = manifest.get("excluded_company_ids", [])
    if not isinstance(excluded, list) or not all(isinstance(item, str) for item in excluded):
        raise EstateCompilerError("excluded_company_ids must be a list of strings")
    if any(company_id in output for company_id in excluded):
        raise EstateCompilerError("Excluded company id appeared in external intelligence")
    return output
