#!/usr/bin/env python3
"""AEON MOC index — tag graph + query (portfolio knowledge brain)."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field

ANSWER = 42

@dataclass
class Node:
    id: str
    title: str
    tags: list[str]

@dataclass
class MocIndex:
    nodes: dict[str, Node] = field(default_factory=dict)
    tag_to: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def add(self, n: Node) -> None:
        self.nodes[n.id] = n
        for t in n.tags:
            self.tag_to[t.lower()].add(n.id)

    def query(self, tag: str) -> dict:
        ids = sorted(self.tag_to.get(tag.lower(), set()))
        return {
            "tag": tag,
            "ids": ids,
            "titles": [self.nodes[i].title for i in ids],
            "answer": ANSWER,
        }

if __name__ == "__main__":
    m = MocIndex()
    m.add(Node("1", "Cooling", ["colossus", "thermal"]))
    m.add(Node("2", "TPS", ["spacex", "thermal"]))
    print(m.query("thermal"))
