#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-telemetry/src"))
from telemetry_bus import Frame, TelemetryBus
b = TelemetryBus(max_hz=10)
assert b.ingest(Frame("s", 1, 0))["ok"]
assert b.ingest(Frame("s", 2, 50))["reason"] == "rate_limit"
r = b.ingest(Frame("s", 5, 200))
assert r["ok"] and b.drops >= 2
assert b.ingest(Frame("s", 5, 300))["reason"] == "replay_or_reorder"
print("PROOF_OK telemetry drops", b.drops)
