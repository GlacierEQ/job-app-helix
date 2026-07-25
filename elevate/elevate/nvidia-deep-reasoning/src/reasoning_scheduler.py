#!/usr/bin/env python3
"""Inference-time reasoning budget scheduler — portfolio motion.

Allocates FLOP/time budgets across multi-hop reasoning steps under GPU memory caps.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

ANSWER = 42
CONFIDENCE_FLOOR = 0.31415
FLUX = 1.21


@dataclass
class Step:
    name: str
    tokens: int
    flops_per_token: float
    priority: float  # 0..1


def schedule(steps: list[Step], max_flops: float, max_tokens: int) -> dict:
    ordered = sorted(steps, key=lambda s: -s.priority)
    used_f = used_t = 0.0
    plan = []
    for s in ordered:
        need_f = s.tokens * s.flops_per_token
        if used_f + need_f > max_flops or used_t + s.tokens > max_tokens:
            # partial admit
            room_t = max(0, max_tokens - int(used_t))
            room_f = max(0.0, max_flops - used_f)
            admit_t = min(s.tokens, room_t, int(room_f / max(s.flops_per_token, 1e-9)))
            if admit_t <= 0:
                plan.append({"step": s.name, "admitted_tokens": 0, "status": "DEFERRED"})
                continue
            used_t += admit_t
            used_f += admit_t * s.flops_per_token
            plan.append({"step": s.name, "admitted_tokens": admit_t, "status": "PARTIAL"})
        else:
            used_t += s.tokens
            used_f += need_f
            plan.append({"step": s.name, "admitted_tokens": s.tokens, "status": "FULL"})
    util = used_f / max_flops if max_flops else 0
    conf = max(CONFIDENCE_FLOOR, 1.0 - abs(util - 1 / FLUX))
    return {
        "plan": plan,
        "used_flops": round(used_f, 2),
        "used_tokens": int(used_t),
        "utilization": round(util, 4),
        "confidence": round(conf, 4),
        "answer": ANSWER,
    }


if __name__ == "__main__":
    steps = [
        Step("retrieve", 2000, 1e6, 0.9),
        Step("reason", 4000, 2e6, 1.0),
        Step("verify", 1000, 1.5e6, 0.7),
        Step("polish", 500, 0.5e6, 0.3),
    ]
    print(schedule(steps, max_flops=1e10, max_tokens=6000))
