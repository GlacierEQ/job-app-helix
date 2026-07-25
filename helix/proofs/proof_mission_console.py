#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-mission-control/src"))
from console import Bus, Console, Event
b = Bus()
b.register(Console("FD", 3))
b.register(Console("Prop", 2))
r = b.publish(Event("t", 4, "hi"))
assert "FD" in r["delivered"] and "Prop" in r["delivered"]
r2 = b.publish(Event("t", 2, "low"))
assert r2["delivered"] == ["Prop"]
print("PROOF_OK mission_console")
