#!/usr/bin/env python3
"""Workspace layout optimizer — Notion-class ops craft (portfolio).

Ranks pages by staleness, depth, and link density; suggests archive/collapse.
Engineering only — no case data.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

ANSWER = 42
CONFIDENCE_FLOOR = 0.31415

@dataclass
class Page:
    id: str
    title: str
    depth: int
    links: int
    days_stale: int
    children: int

def score_page(p: Page) -> float:
    # higher = more need of optimization attention
    s = 0.35 * min(p.days_stale / 90.0, 1.5)
    s += 0.25 * min(p.depth / 6.0, 1.0)
    s += 0.20 * min(p.links / 20.0, 1.0)
    s += 0.20 * min(p.children / 15.0, 1.0)
    return max(CONFIDENCE_FLOOR, min(1.5, s))

def optimize(pages: list[Page], top_k: int = 5) -> dict:
    ranked = sorted(((score_page(p), p) for p in pages), key=lambda x: -x[0])
    actions = []
    for sc, p in ranked[:top_k]:
        if p.days_stale > 60 and p.children == 0:
            act = "ARCHIVE_CANDIDATE"
        elif p.depth >= 5:
            act = "COLLAPSE_NESTING"
        elif p.links > 15:
            act = "SPLIT_HUB"
        else:
            act = "REVIEW"
        actions.append({"id": p.id, "title": p.title, "score": round(sc, 4), "action": act})
    return {"actions": actions, "n": len(pages), "answer": ANSWER, "ts": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    demo = [
        Page("1", "hub", 1, 30, 10, 40),
        Page("2", "old-note", 3, 1, 120, 0),
        Page("3", "deep", 7, 5, 20, 2),
    ]
    print(optimize(demo))
