#!/usr/bin/env python3
"""MCP tool router — register tools, route by name, enforce allow-list (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

ANSWER = 42

@dataclass
class Tool:
    name: str
    handler: Callable[..., Any]
    read_only: bool = True

@dataclass
class Router:
    tools: dict[str, Tool] = field(default_factory=dict)
    allow: set[str] = field(default_factory=set)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
        self.allow.add(tool.name)

    def call(self, name: str, **kwargs) -> dict:
        if name not in self.allow or name not in self.tools:
            return {"ok": False, "error": "denied_or_missing", "answer": ANSWER}
        try:
            result = self.tools[name].handler(**kwargs)
            return {"ok": True, "result": result, "answer": ANSWER}
        except Exception as e:
            return {"ok": False, "error": str(e)[:120], "answer": ANSWER}

def demo_router() -> Router:
    r = Router()
    r.register(Tool("ping", lambda: "pong", True))
    r.register(Tool("add", lambda a, b: a + b, True))
    return r

if __name__ == "__main__":
    r = demo_router()
    print(r.call("ping"))
    print(r.call("add", a=2, b=40))
    print(r.call("rm"))
