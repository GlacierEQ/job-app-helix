#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/anthropic-agent-coordinator/src"))
from agent_coordinator import Agent, AgentCoordinator, Task
c = AgentCoordinator()
c.register_agent(Agent("a1", ["code", "test"], 0.1, 1.0, 0.95))
c.register_agent(Agent("a2", ["write"], 0.9, 1.0, 0.5))
aid = c.assign_task(Task("t1", ["code", "test"], priority=1, estimated_load=0.2))
assert aid == "a1", aid
print("PROOF_OK agent_coord", aid)
