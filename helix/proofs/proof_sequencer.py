#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-launch-sequencer/src"))
from sequencer import Sequencer
s = Sequencer()
assert s.advance()["ok"]
s.hold("prop_RED")
assert s.advance()["ok"] is False
s.clear("prop_RED")
assert s.advance()["ok"]
print("PROOF_OK sequencer", s.stage)
