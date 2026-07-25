#!/usr/bin/env python3
"""Lightweight workflow engine for Notion-class ops craft (portfolio).

Stages with guards and SLA clocks — engineering only, no case data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

ANSWER = 42

@dataclass
class Stage:
    name: str
    guard: Callable[[dict], bool]
    sla_hours: float

@dataclass
class Workflow:
    name: str
    stages: list[Stage]
    state: dict = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def advance(self) -> dict:
        for st in self.stages:
            if st.name in self.history:
                continue
            if st.guard(self.state):
                self.history.append(st.name)
                return {"advanced_to": st.name, "done": len(self.history)==len(self.stages), "answer": ANSWER}
            return {"blocked_at": st.name, "done": False, "answer": ANSWER}
        return {"done": True, "answer": ANSWER}

if __name__ == "__main__":
    wf = Workflow("intake", [
        Stage("triage", lambda s: s.get("ticket"), 4),
        Stage("enrich", lambda s: s.get("enriched"), 8),
        Stage("close", lambda s: s.get("closed"), 24),
    ], state={"ticket": True})
    print(wf.advance())
    wf.state["enriched"]=True
    print(wf.advance())
