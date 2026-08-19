# SpaceX Neighbor Threads — Source Review Notes

**Review method:** Static source and behavioral-contract inspection only. No repository test suites, package installs, project scripts, or operational commands were executed in this review. Each finding is tied to the revision recorded in `next_review_target_register.tsv`.

## `GlacierEQ/spacex-hold-reason-compiler`

At commit `e7b928f9b713ac6e7652ac3b3b12df84e8880ec1`, `src/hold_compiler.py` implements a local deterministic explanation compiler over caller-supplied `HoldResidual` values. It validates tokens and severities, retains the highest severity per `(subsystem, code)` pair, merges equal-severity details in sorted order, orders the resulting residuals by severity and a local subsystem-priority map, and emits structured machine/human brief fields plus SHA-256 policy and result fingerprints. `tests/test_hold_compiler.py` encodes the empty input, deterministic equal-severity deduplication, severity and priority ordering, unknown-subsystem retention, invalid-input rejection, and fingerprint-stability behavior.

The README and module are explicit that the compiler explains supplied residuals only. It does not authenticate inputs, decide safety, clear holds, command hardware, or provide flight/go-no-go authority. Local priority and owner labels are repository-defined policy fixtures, not a claim about an external operational process.

**Card assessment:** `directly_supported` for deterministic local hold-residual explanation and stable machine/human brief construction. The assessment does not establish real operational authority, integration, or input authenticity.

## `GlacierEQ/spacex-mission-thread-quorum`

At commit `705d19b886be694d4a2b362abe246b932d88d9f7`, `src/quorum.py` implements a local configured-subsystem vote aggregator. Votes must be valid, belong to the configured set, and strictly advance their per-subsystem decision time. Evaluation treats missing, stale, and future votes as incomplete; turns a `NO_GO` vote at or beyond the configured severity threshold into a local hold; returns a local `NO_GO` for lower-severity `NO_GO`; and treats `ABSTAIN` as incomplete. Result receipts bind the active vote views, policy fingerprint, evaluation time, and state into a SHA-256 digest. `tests/test_quorum.py` encodes those conditions, including stale/future handling, causal replacement refusal, receipt integrity, policy changes, and non-finite-time rejection.

The module explicitly rejects any claim to authenticate voters, command hardware, decide real flight safety, or issue or clear an operational launch hold.

**Card assessment:** `directly_supported` for deterministic local vote freshness, aggregation, and receipt construction. The assessment does not establish voter authenticity, real operational authority, or integration with any launch system.

## `GlacierEQ/spacex-pad-weather-gate`

At commit `74e6e69d1e3c61b284b0b6917ba2b7a14a148f41`, `src/weather_gate.py` implements a deterministic local evaluator over synthetic wind, shear, lightning-distance, ceiling, and visibility values. It rejects non-finite and negative observations, evaluates five illustrative threshold fixtures in fixed order, produces `PASS` or `BLOCK`, and returns a bounded minimum-margin score with a named evidence state. `tests/test_public_truth.py` encodes the evidence token, independence language, fixture status, absence of forecast or real-time polling claims, bounded non-probability margin behavior, and preserved target-state separation.

The repository describes its numeric limits as illustrative fixtures. It does not claim official launch criteria, real sensors, real-time acquisition, forecasting, optimization, safety certification, or launch authority.

**Card assessment:** `directly_supported` for deterministic local evaluation of supplied synthetic environmental observations against illustrative fixtures. The assessment does not establish weather forecasting, sensor integration, or real safety decision authority.

## `GlacierEQ/spacex-telemetry`

At commit `87857ceca59201aa0da668395f226be77cde75db`, `src/telemetry_lab_cli.py` builds a deterministic repository-local demo receipt. The source feeds synthetic binary frames through the local decoder/controller, deliberately introduces a sequence gap, sends a corrupted CRC frame to a separate decoder, creates a local threshold alert, performs a local Protobuf round trip, and records zero external inputs and zero external actions before hashing the receipt. `tests/test_installable_telemetry_lab.py` encodes expected receipt values: three decoded frames, one gap, one dropped frame, CRC rejection of the corrupted frame, one warning alert, Protobuf payload round trip, zero external inputs/actions, and a 64-character receipt digest.

The README identifies the work as synthetic local telemetry code and rejects claims about private telemetry, external wire formats, live ingestion, performance, operational timestamps, live agent queries, deployment, or mission authority.

**Card assessment:** `directly_supported` for a deterministic synthetic telemetry-codec laboratory demonstration with integrity rejection, gap accounting, local threshold alerting, local serialization, and a receipt that records no external inputs or actions. It does not establish live telemetry, protocol compatibility, performance, or mission integration.
