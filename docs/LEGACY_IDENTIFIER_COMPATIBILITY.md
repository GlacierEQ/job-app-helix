# Dynamic System Catalog Compatibility Boundary

## Purpose

Job-App Helix remains the build-time source authority for the hiring system. Some maintained internal artifacts retain the historical serialized word `flagship`, including the registry filename and selected compatibility readers. These identifiers are **schema-compatibility labels**, not a portfolio ceiling, public presentation boundary, or rule that limits the engineering estate.

## Contract

The registry is a dynamic collection. Every admission, evidence state, visibility decision, and promotion remains repository-specific. No active maintained validator may require an exact system count, a fixed public-system floor, or a fixed audience-view count as a condition for the system to be correct.

> Evidence controls what can be claimed about a record. It does not determine how many systems may exist, be discovered, be reviewed, or be represented through a future platform surface.

## Migration rule

New public projections, receipts, generated outputs, and user-facing APIs must use **system**, **systems catalog**, or **source-admitted system** terminology. A historical identifier may remain only where changing the serialized key would break an existing upstream compatibility contract; the code that reads it must project a dynamic system collection without a hard-coded count.

## Governed compatibility ledger

The following maintained paths are the complete current compatibility surface for the serialized registry label. They operate behind the build-time authority boundary and must not emit that label into a public recruiter, résumé, master, mesh, atlas, machine, receipt, or API projection.

| Maintained path group | Compatibility responsibility |
|---|---|
| `manifests/flagship_registry.json` and `manifests/flagship_external_repositories.json` | Preserve the existing serialized registry and external-reference shapes while catalog entries remain dynamically admitted records. |
| `src/job_app_helix/estate_compiler.py`, `scripts/compile_estate_graph.py`, and `scripts/discover_experience_graph.py` | Read the compatibility schema to compile system and capability evidence; their outputs remain dynamic. |
| `scripts/audit_live_portfolio_freshness.py`, `scripts/validate_application_registry.py`, and `scripts/validate_portfolio_root_truth.py` | Audit and validate evidence, inventory relationships, and source integrity without exact catalog or inventory totals. |
| `tests/test_application_registry.py`, `tests/test_estate_capability_discovery.py`, `tests/test_estate_compiler.py`, `tests/test_estate_intelligence.py`, `tests/test_experience_graph_discovery.py`, `tests/test_live_portfolio_freshness.py`, and `tests/test_portfolio_root_truth.py` | Preserve compatibility coverage while asserting dynamic relationships and evidence conditions rather than a portfolio ceiling. |

`tests/test_legacy_identifier_compatibility.py` enforces this ledger and verifies that the active registry validator reports a dynamic `named_systems` result without static inventory-size assertions.
