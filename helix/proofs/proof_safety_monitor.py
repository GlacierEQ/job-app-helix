#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/anthropic-safety-monitor/src"))
from safety_monitor import ToolCall, evaluate
assert evaluate(ToolCall("bash", "ls"))["decision"] == "allow"
assert evaluate(ToolCall("bash", "rm -rf /"))["decision"] == "deny"
assert evaluate(ToolCall("bash", "git push --force origin main"))["decision"] == "confirm"
print("PROOF_OK safety_monitor")
