# Dynamic System Catalog Compatibility Boundary

## Purpose

Job-App Helix remains the build-time source authority for the hiring system. Some maintained internal artifacts retain the historical serialized word `flagship`, including the registry filename and selected compatibility readers. These identifiers are **schema-compatibility labels**, not a portfolio ceiling, public presentation boundary, or rule that limits the engineering estate.

## Contract

The registry is a dynamic collection. Every admission, evidence state, visibility decision, and promotion remains repository-specific. No active maintained validator may require an exact system count, a fixed public-system floor, or a fixed audience-view count as a condition for the system to be correct.

> Evidence controls what can be claimed about a record. It does not determine how many systems may exist, be discovered, be reviewed, or be represented through a future platform surface.

## Migration rule

New public projections, receipts, generated outputs, and user-facing APIs must use **system**, **systems catalog**, or **source-admitted system** terminology. A historical identifier may remain only where changing the serialized key would break an existing upstream compatibility contract; the code that reads it must project a dynamic system collection without a hard-coded count.
