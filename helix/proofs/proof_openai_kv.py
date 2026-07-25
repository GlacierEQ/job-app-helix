#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/openai-reasoning-kv-sentinel/src"))
from reasoning_kv_sentinel import ReasoningKVSentinel, ZeroOverheadSchemaDispatcher

s = ReasoningKVSentinel(max_cache_tokens=30, entropy_threshold=0.35, keep_tail=3)
tokens = []
for i in range(60):
    if i % 10 == 0:
        tokens.append({"id": i, "probs": [0.99, 0.01], "is_anchor": True})
    elif i % 2 == 0:
        tokens.append({"id": i, "probs": [0.99, 0.01], "is_anchor": False})
    else:
        tokens.append({"id": i, "probs": [0.5, 0.5], "is_anchor": False})
ret, m = s.prune_reasoning_trajectory(tokens)
anchor_ids = {t["id"] for t in tokens if t.get("is_anchor")}
ret_ids = {t["id"] for t in ret}
assert anchor_ids.issubset(ret_ids), "anchors lost"
assert m["retained_tokens"] < len(tokens), "no prune"
assert len(ret) <= 30, "soft cap failed"
d = ZeroOverheadSchemaDispatcher([{
    "name": "x",
    "parameters": {"required": ["a"], "properties": {"a": {"type": "integer"}}},
}])
assert d.dispatch_tool_call("x", {"a": 1})["ok"]
assert not d.dispatch_tool_call("x", {"a": "no"})["ok"]
print("PROOF_OK openai-kv", m["retained_tokens"], "retained")
