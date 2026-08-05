"""Fail-closed contracts for the 48-track Bottleneck Atlas."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_TRACK_IDS = (
    "openai",
    "anthropic",
    "google_deepmind",
    "xai",
    "microsoft",
    "aws",
    "spacex",
    "nvidia",
    "apple",
    "meta",
    "tesla",
    "notion",
    "deepseek",
    "kimi",
    "qwen",
    "opera",
    "tasklet",
    "robotics",
    "perplexity",
    "manus",
    "lovable",
    "openclaw",
    "palantir",
    "anduril",
    "scale_ai",
    "mistral",
    "cohere",
    "databricks",
    "snowflake",
    "ibm",
    "intel",
    "amd",
    "qualcomm",
    "oracle",
    "salesforce",
    "adobe",
    "cloudflare",
    "vercel",
    "hugging_face",
    "groq",
    "cerebras",
    "coreweave",
    "waymo",
    "zoox",
    "blue_origin",
    "rocket_lab",
    "nasa",
    "glaciereq_core",
)

LENSES = (
    ("S1", "official_source", "observed_current_pressure"),
    ("S2", "systems_bottleneck", "inferred_bottleneck"),
    ("S3", "brick_wall", "inferred_brick_wall"),
    ("S4", "repository_evidence", "leverage"),
    ("S5", "leverage_architecture", "leverage"),
    ("S6", "impact", "leverage"),
    ("S7", "application_strategy", "application_move"),
    ("S8", "truth_presentation", "inference_boundary"),
)


class IntelligenceValidationError(ValueError):
    """Raised when the company-intelligence plane violates a hard contract."""


def canonical_json(value: Any) -> str:
    """Serialize a value deterministically for hashing and byte measurement."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def sha256(value: Any) -> str:
    """Return the SHA-256 of a value's canonical UTF-8 JSON representation."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON object and reject non-object roots."""

    resolved = Path(path)
    with resolved.open(encoding="utf-8") as file_handle:
        value = json.load(file_handle)

    if not isinstance(value, dict):
        raise IntelligenceValidationError(f"{resolved}: expected object")
    return value


def load_expanded_atlas(
    root: str | Path,
    manifest_path: str = (
        "manifests/application_intelligence/company_bottleneck_atlas.json"
    ),
) -> dict[str, Any]:
    """Expand the sharded atlas and verify every manifest and shard hash."""

    root_path = Path(root)
    manifest = load_json(root_path / manifest_path)
    expected_manifest_hash = sha256(_without_hash(manifest, "manifest_sha256"))
    if manifest.get("manifest_sha256") != expected_manifest_hash:
        raise IntelligenceValidationError("atlas manifest hash")

    defaults = manifest["defaults"]
    records: list[dict[str, Any]] = []

    for shard_reference in manifest["shards"]:
        shard = load_json(root_path / shard_reference["path"])
        expected_shard_hash = sha256(_without_hash(shard, "shard_sha256"))
        if (
            shard.get("shard_sha256") != expected_shard_hash
            or expected_shard_hash != shard_reference["shard_sha256"]
        ):
            category_id = shard_reference["category_id"]
            raise IntelligenceValidationError(f"{category_id}: shard hash")

        for raw_record in shard["records"]:
            record = dict(raw_record)
            record["as_of"] = defaults["as_of"]
            record["research_state"] = defaults["research_state"]
            record["inference_boundary"] = defaults["inference_boundary"]
            record["confidence"] = defaults["confidence"]
            record["non_affiliation"] = defaults["non_affiliation"]
            record["official_sources"] = [
                {**defaults["source_defaults"], **source}
                for source in raw_record["official_sources"]
            ]
            records.append(record)

    atlas: dict[str, Any] = {
        "schema": manifest["schema"],
        "version": manifest["version"],
        "generated_at": manifest["generated_at"],
        "authority": manifest["authority"],
        "branch": manifest["branch"],
        "research_scope": manifest["research_scope"],
        "category_order": manifest["category_order"],
        "records": records,
    }
    atlas["atlas_sha256"] = sha256(atlas)
    if atlas["atlas_sha256"] != manifest["expanded_atlas_sha256"]:
        raise IntelligenceValidationError("expanded atlas hash")
    return atlas


def validate_atlas(atlas: dict[str, Any]) -> dict[str, Any]:
    """Validate exact coverage, source integrity, record integrity, and truth limits."""

    records = atlas.get("records")
    ids = tuple(record.get("company_id") for record in records or [])
    if ids != EXPECTED_TRACK_IDS:
        raise IntelligenceValidationError(
            f"exact 48-track order mismatch ({len(ids)})"
        )

    source_count = 0
    for record in records:
        company_id = record["company_id"]
        for source in record["official_sources"]:
            expected_source_hash = sha256(_without_hash(source, "source_sha256"))
            if source.get("source_sha256") != expected_source_hash:
                raise IntelligenceValidationError(f"{company_id}: source hash")
            if source.get("official") is not True:
                raise IntelligenceValidationError(f"{company_id}: unofficial source")
            source_count += 1

        expected_record_hash = sha256(_without_hash(record, "record_sha256"))
        if record.get("record_sha256") != expected_record_hash:
            raise IntelligenceValidationError(f"{company_id}: record hash")

        inference_is_bounded = (
            "not a statement confirmed" in record["inference_boundary"]
        )
        affiliation_is_bounded = "No affiliation" in record["non_affiliation"]
        if not inference_is_bounded or not affiliation_is_bounded:
            raise IntelligenceValidationError(f"{company_id}: truth boundary")

    return {
        "status": "PASS",
        "track_count": 48,
        "source_count": source_count,
        "silent_omissions": 0,
        "atlas_sha256": atlas["atlas_sha256"],
    }


def build_packets(
    atlas: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build compact Unified Memory packets and exact byte measurements."""

    packets: list[dict[str, Any]] = []
    before = 0
    after = 0

    for record in atlas["records"]:
        packet: dict[str, Any] = {
            "schema": "glaciereq.unified-memory.company-intelligence-packet.v1",
            "memory_key": (
                f"helix/company/{record['company_id']}/bottleneck-v1"
            ),
            "company_id": record["company_id"],
            "display_name": record["display_name"],
            "category_id": record["category_id"],
            "as_of": record["as_of"],
            "state": record["research_state"],
            "decision": {
                "pressure": record["observed_current_pressure"],
                "bottleneck": record["inferred_bottleneck"],
                "brick_wall": record["inferred_brick_wall"],
                "leverage": record["leverage"]["mechanism"],
                "impact": record["leverage"]["expected_impact"],
                "application_move": record["application_move"],
                "next_gate": record["next_deep_dive"],
            },
            "source_hashes": [
                source["source_sha256"]
                for source in record["official_sources"]
            ],
            "record_sha256": record["record_sha256"],
            "truth": "OBSERVED_SOURCE_PLUS_GLACIEREQ_INFERENCE",
        }
        packet["packet_sha256"] = sha256(
            _without_hash(packet, "packet_sha256")
        )
        packets.append(packet)
        before += len(canonical_json(record).encode("utf-8"))
        after += len(canonical_json(packet).encode("utf-8"))

    saved = before - after
    return packets, {
        "before": before,
        "after": after,
        "saved": saved,
        "reduction_ratio": round(saved / before, 6),
    }


def _lens_payload(
    specialist_id: str,
    field_value: Any,
) -> Any:
    if specialist_id == "S4":
        return {"systems": field_value["glaciereq_systems"]}
    if specialist_id == "S5":
        return {"mechanism": field_value["mechanism"]}
    if specialist_id == "S6":
        return {
            "expected_impact": field_value["expected_impact"],
            "impact_class": field_value["impact_class"],
        }
    return field_value


def build_expanded_run(
    atlas: dict[str, Any],
    topology: dict[str, Any],
    compact: dict[str, Any],
) -> dict[str, Any]:
    """Build the deterministic six-wave Gatling Tsunami execution receipt."""

    run: dict[str, Any] = {
        "schema": compact["schema"],
        "run_id": compact["run_id"],
        "generated_at": compact["generated_at"],
        "execution_mode": compact["execution_mode"],
        "truth_boundary": compact["truth_boundary"],
        "topology_sha256": topology["topology_sha256"],
        "atlas_sha256": atlas["atlas_sha256"],
        "wave_count": 6,
        "tracks_per_wave": 8,
        "track_count": 48,
        "specialist_task_count": 384,
        "integration_count": 48,
        "silent_omissions": 0,
        "status": "FIRST_PASS_COMPLETE",
        "waves": [],
    }

    for wave_index in range(6):
        integrations: list[dict[str, Any]] = []
        start = wave_index * 8
        stop = (wave_index + 1) * 8

        for record in atlas["records"][start:stop]:
            receipts: list[dict[str, Any]] = []
            for specialist_id, lens, field in LENSES:
                payload = _lens_payload(specialist_id, record[field])
                receipts.append(
                    {
                        "specialist_id": specialist_id,
                        "lens": lens,
                        "input_record_sha256": record["record_sha256"],
                        "output_sha256": sha256(
                            {
                                "company_id": record["company_id"],
                                "lens": lens,
                                "payload": payload,
                            }
                        ),
                    }
                )

            integration: dict[str, Any] = {
                "company_id": record["company_id"],
                "display_name": record["display_name"],
                "lens_count": 8,
                "lens_receipts": receipts,
                "integrated_record_sha256": record["record_sha256"],
                "integration_status": "COMPLETE",
            }
            integration["integration_sha256"] = sha256(
                _without_hash(integration, "integration_sha256")
            )
            integrations.append(integration)

        wave: dict[str, Any] = {
            "wave": wave_index + 1,
            "track_count": 8,
            "tracks": [item["company_id"] for item in integrations],
            "integrations": integrations,
            "status": "COMPLETE",
        }
        wave["wave_sha256"] = sha256(_without_hash(wave, "wave_sha256"))
        run["waves"].append(wave)

    run["run_sha256"] = sha256(_without_hash(run, "run_sha256"))
    return run


def validate_index(root: str | Path) -> dict[str, Any]:
    """Validate the canonical index and every referenced intelligence contract."""

    root_path = Path(root)
    index = load_json(root_path / "manifests/company_intelligence.json")
    atlas = load_expanded_atlas(root_path, index["files"]["atlas"])
    topology = load_json(root_path / index["files"]["diamond_topology"])
    compact_run = load_json(root_path / index["files"]["gatling_receipt"])
    measurement = load_json(
        root_path / index["files"]["token_saver_measurement"]
    )

    expected_topology_hash = sha256(
        _without_hash(topology, "topology_sha256")
    )
    if topology.get("topology_sha256") != expected_topology_hash:
        raise IntelligenceValidationError("topology hash")

    atlas_result = validate_atlas(atlas)
    packets, measured = build_packets(atlas)
    expanded_run = build_expanded_run(atlas, topology, compact_run)

    if expanded_run["run_sha256"] != compact_run["expanded_run_sha256"]:
        raise IntelligenceValidationError("expanded run hash")

    gatling_order = tuple(
        company_id
        for wave in expanded_run["waves"]
        for company_id in wave["tracks"]
    )
    if gatling_order != EXPECTED_TRACK_IDS:
        raise IntelligenceValidationError("gatling order")

    if (
        measured["before"] != measurement["canonical_bytes_before"]
        or measured["after"] != measurement["canonical_bytes_after"]
    ):
        raise IntelligenceValidationError("token measurement")

    expected_index_hash = sha256(_without_hash(index, "index_sha256"))
    if index.get("index_sha256") != expected_index_hash:
        raise IntelligenceValidationError("index hash")

    return {
        "status": "PASS",
        "atlas": atlas_result,
        "memory": {
            "status": "PASS",
            "packet_count": len(packets),
        },
        "gatling": {
            "status": "PASS",
            "waves": 6,
            "tracks": 48,
            "specialist_tasks": 384,
            "run_sha256": expanded_run["run_sha256"],
        },
        "measurement": {
            "status": "PASS",
            **measured,
        },
        "silent_omissions": 0,
        "index_sha256": index["index_sha256"],
    }
