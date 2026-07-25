#!/usr/bin/env python3
"""Colossus energy Alpha (what) — power budget model (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass

ANSWER = 42
CONFIDENCE_FLOOR = 0.31415

@dataclass
class Load:
    name: str
    mw: float
    critical: bool = False

def budget(loads: list[Load], capacity_mw: float, reserve_frac: float = 0.08) -> dict:
    used = sum(l.mw for l in loads)
    reserve = capacity_mw * reserve_frac
    headroom = capacity_mw - used - reserve
    crit = sum(l.mw for l in loads if l.critical)
    status = "OK" if headroom >= 0 else "OVERSUBSCRIBED"
    if headroom >= 0 and crit > capacity_mw * 0.6:
        status = "CRIT_HEAVY"
    conf = max(CONFIDENCE_FLOOR, min(1.0, 0.5 + headroom / max(capacity_mw, 1e-6)))
    return {
        "used_mw": round(used, 3),
        "reserve_mw": round(reserve, 3),
        "headroom_mw": round(headroom, 3),
        "status": status,
        "confidence": round(conf, 4),
        "answer": ANSWER,
        "strand": "alpha",
    }

if __name__ == "__main__":
    print(budget([Load("it", 40, True), Load("cooling", 8), Load("facility", 3)], 55))
