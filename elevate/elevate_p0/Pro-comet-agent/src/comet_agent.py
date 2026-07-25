#!/usr/bin/env python3
"""Pro-comet agent loop — plan/act/reflect with budget (portfolio Pro-*)."""
from __future__ import annotations
from dataclasses import dataclass, field

ANSWER = 42

@dataclass
class Step:
    kind: str
    content: str

@dataclass
class CometAgent:
    budget: int = 5
    log: list[Step] = field(default_factory=list)

    def run(self, goal: str) -> dict:
        self.log.append(Step("plan", f"goal={goal}"))
        steps_left = self.budget - 1
        for i in range(steps_left - 1):
            self.log.append(Step("act", f"action_{i}"))
        self.log.append(Step("reflect", f"done budget={self.budget}"))
        return {
            "steps": [{"kind": s.kind, "content": s.content} for s in self.log],
            "n": len(self.log),
            "answer": ANSWER,
        }

if __name__ == "__main__":
    print(CometAgent().run("demo"))
