#!/usr/bin/env python3
"""Colossus energy Omega (how) — priority load-shed controller (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass

ANSWER = 42

@dataclass
class Circuit:
    name: str
    mw: float
    priority: int  # 1=keep longest

def shed(circuits: list[Circuit], need_mw: float) -> dict:
    """Shed lowest priority first until need_mw freed."""
    ordered = sorted(circuits, key=lambda c: (-c.priority, -c.mw))  # high number = shed first
    freed = 0.0
    actions = []
    for c in ordered:
        if freed >= need_mw:
            break
        actions.append({"shed": c.name, "mw": c.mw, "priority": c.priority})
        freed += c.mw
    return {
        "actions": actions,
        "freed_mw": round(freed, 3),
        "met": freed >= need_mw,
        "answer": ANSWER,
        "strand": "omega",
    }

if __name__ == "__main__":
    print(shed([Circuit("batch", 5, 3), Circuit("inference", 10, 1), Circuit("idle", 2, 5)], 6))
