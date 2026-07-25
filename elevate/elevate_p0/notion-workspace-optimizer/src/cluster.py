#!/usr/bin/env python3
"""Cluster related pages by title tokens for workspace simplification."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass

ANSWER = 42

@dataclass
class PageRef:
    id: str
    title: str

def cluster(pages: list[PageRef], min_size: int = 2) -> dict:
    buckets: dict[str, list[str]] = defaultdict(list)
    for p in pages:
        token = (p.title.split("-")[0] if p.title else "misc").lower()
        buckets[token].append(p.id)
    groups = {k: v for k, v in buckets.items() if len(v) >= min_size}
    return {
        "clusters": groups,
        "singleton_n": sum(1 for v in buckets.values() if len(v) < min_size),
        "answer": ANSWER,
    }

if __name__ == "__main__":
    print(cluster([PageRef("1","ops-a"), PageRef("2","ops-b"), PageRef("3","misc")]))
