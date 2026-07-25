#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/tasklet-micro-agent-engine/src"))
from tasklet_micro_agent_engine import TaskletMicroAgentEngine
e = TaskletMicroAgentEngine(max_concurrent_tasklets=2)
assert e.spawn_tasklet("hi", {}, priority=1)["ok"]
assert e.spawn_tasklet("mid", {}, priority=5)["ok"]
assert not e.spawn_tasklet("nope", {})["ok"]
assert e.next_tasklet()["tasklet_id"] == "hi"
e.suspend_tasklet("mid")
assert e.resume_tasklet("mid")["ok"]
print("PROOF_OK tasklet")
