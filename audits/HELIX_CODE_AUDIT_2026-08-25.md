# Job-App Helix — Code & Contract Audit

**Date:** 2026-08-25
**Commit:** `cc4cfb9` (working tree clean; all findings reproducible at HEAD)
**Version:** 0.3.0
**Environment:** Python 3.11 via `uv sync --frozen --extra dev`, Linux

---

## Executive summary

The core engine is in good shape: 677 tests pass, lint is clean, both machine
contract checks pass, and the security-sensitive surfaces (bounded execution,
restoration, submission integrity) are genuinely fail-closed. The audit found
no secrets, no shell-injection surface, and no fabricated evidence states.

However, the repository's own standard is "evidence-bound, no theater," and by
that standard three findings are significant:

1. The README's documented mypy gate is **red (51 errors)** and CI never runs it.
2. A CLI flag (`transition --external-reference`) **cannot succeed** — every use errors.
3. The committed integrity manifest `helix/.integrity/file_hashes.json`
   **fails its own hash verification** for 4 of 5 files.

| Area | Result |
|---|---|
| ruff (documented scope) | PASS |
| mypy `src/job_app_helix/` | **FAIL — 51 errors, 12 files** |
| pytest | PASS — 677 passed in ~14s |
| `check_proto_contract.py` | PASS |
| `check_public_surface.py` | PASS — 834 tracked files |
| `portfolio_cli validate` | PASS — 66 repos, VALID |
| Secrets scan | Clean |
| Entry points (`job-app-helix*`) | All importable and respond to `--help` |

---

## Findings

### H1. Documented verify gate is red: mypy fails with 51 errors; CI does not enforce it — HIGH

README "Install and verify" lists `python -m mypy src/job_app_helix/`. At HEAD
this reports **51 errors in 12 files**. `.github/workflows/ci.yml` runs ruff,
pytest, portfolio/mesh/proto/surface checks — but **never mypy**, so the gate
is documented but unenforced.

Error clusters (full list via `mypy src/job_app_helix/`):

- `estate_compiler.py` (13): `target` bound as `str` in the lineage loop at
  :325 then rebound as `Repo` at :374 — shadowing that cascades through the
  system-grouping block (:380–447); plus a genuine duplicate definition of
  `capabilities` (:506 vs :553). Runtime behavior appears correct today
  (tests pass), but this is exactly the kind of type confusion the truth model
  warns about.
- `repo_excellence_evolution.py` (12): narrowing failures after the
  `all(isinstance(item, Mapping))` guard at :190 — runtime-safe (raises first),
  cosmetic typing debt.
- `restoration_cli.py` (9): real Federated-vs-Symbol packet/receipt type
  confusion at :175–198. Worth a functional review, not just annotation fixes.
- `worker_science.py`, `live_evidence_adapter.py` (4): missing jsonschema stubs
  — add `types-jsonschema` to dev deps or a mypy override.

Recommended fix path: make CI run the same mypy command the README promises;
fix `estate_compiler`/`restoration_cli` properly rather than widening the
existing `ignore_errors` overrides.

### H2. `job-app-helix transition --external-reference <ref>` can never succeed — MEDIUM

- CLI advertises and forwards the flag: `src/job_app_helix/cli.py:217`, `:520`.
- Store rejects any non-None value unconditionally:
  `src/job_app_helix/application_operations.py:768-771`.

Reproduced:

```
$ job-app-helix transition app-x READY --external-reference ref123 --db t.db
job-app-helix: external_reference may not mutate application lifecycle state
```

The guard's intent (an external reference must not itself promote lifecycle
state) is sound, but the result is a dead advertised feature. Either accept the
reference as metadata-only (write an event / set the column without changing
status), or remove the flag from the CLI.

### H3. Committed integrity manifest fails its own verification — MEDIUM

`helix/.integrity/file_hashes.json` declares SHA-256 for 5 files under
`helix/`. Verified against the clean working tree:

```
ok=1  drift=4  of 5
DRIFT proofs/proof_brainsync_kind_normalize.py
DRIFT automations/brainsync_kind_normalize.py
DRIFT automations/brainsync_index_skills.py
DRIFT automations/brainsync_path_sanitize.py
```

Both manifest and drifted files are committed together at HEAD, so the binding
was stale when committed. An evidence-bound system whose integrity receipt is
permanently red undermines the posture it exists to prove. Regenerate hashes on
every change to `helix/**` (CI step or pre-commit hook).

### L1. `helix/` automation surface lives outside CI and tests — LOW

`helix/automations/*.py` target `.brainsync/` and `.agent/skills/` paths that do
not exist in this repository (operator-machine tooling committed in-repo).
Proofs exist (`helix/proofs/*.py`) but nothing in CI lints or runs them, and
ruff's CI scope excludes `helix/` entirely. Either wire the proofs into CI or
mark the directory clearly as environment-specific tooling.

### L2. `apply_packet` has a partial-failure window without rollback — LOW

`src/job_app_helix/restoration_executor.py:125-170` mutates packet paths one
action at a time; backups are captured per-action into an in-memory dict that is
only returned on full success. A failure on action N leaves actions 1..N-1
applied with no automatic restore and no receipt. The caller owns the Git
branch, so exposure is limited, but capturing all backups before the first
write (or auto-invoking `rollback()` on exception) would close the window.

### L3. Stale historical docs present themselves as audits — LOW

`AUDIT_REPORT.md` still claims "12/12 tests", "mypy 0 errors", "v0.2.0" from
2026-07-28; current reality is 677 tests, 51 mypy errors, v0.3.0. It reads as a
dated snapshot but carries no visible "historical" banner. Recommend a header
note or moving it under `audits/`.

### I1. Security posture review — INFO (positive)

- No secret patterns in tracked source; no `shell=True`, `eval`, `exec`,
  `pickle`, or TLS-verification disabling anywhere in `src/`.
- Subprocess use is argv-list based with explicit cwd/env and timeouts
  (`portfolio_execution.py:96-199`).
- Mutating workspace commands are blocked before execution unless explicitly
  authorized (`portfolio_execution.py:105-118`) — verified by design and tests.
- SQLite access is fully parameterized; artifact manifests are hash-bound;
  external submission requires exact artifact-set digest + per-artifact match
  (`submission_integrity.py:130-179`).
- Minor notes: `ingest_job_opening_url` fetches arbitrary http(s) URLs with no
  host restrictions (acceptable for local operator tooling; add an allowlist if
  ever server-exposed), and `extract_test_count` takes the **max** regex match,
  which a noisy build log could inflate (acceptable given positive-count intent).

---

## What was verified as sound

- Application lifecycle state machine is fail-closed: no SUBMITTED state exists;
  legacy statuses map conservatively; response events record reality while
  transitions stay guarded (`application_operations.py:54-77, 759-835`).
- `atomic_write_json` uses temp-file + fsync + `os.replace` correctly.
- Zero-test exits are demoted to UNVERIFIED when a positive count is required
  (`portfolio_execution.py:176-183`), matching the documented failure semantics.
- Restoration refuses to overwrite existing targets without explicit
  `allow_replace`, binds packets to one donor+target revision, and re-verifies
  donor bytes at apply time.
- Portfolio contract validates cleanly across all 66 admitted repositories.
- All six console entry points resolve and respond.

## Recommended order of work

1. Add mypy to CI and burn down the 51 errors (start with `restoration_cli.py`
   and `estate_compiler.py` — they carry semantic risk, not just annotations).
2. Fix or remove `--external-reference`.
3. Regenerate `helix/.integrity/file_hashes.json` and add a freshness check.
4. Sweep stale docs (`AUDIT_REPORT.md`) into dated-history framing.
