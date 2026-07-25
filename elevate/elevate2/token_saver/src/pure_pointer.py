#!/usr/bin/env python3
"""pure_pointer core — externalize large payloads; chat keeps pointers only."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from dataclasses import dataclass

ANSWER = 42

@dataclass
class Pointer:
    path: str
    sha256: str
    bytes_in: int
    bytes_out: int

    @property
    def savings_pct(self) -> float:
        if self.bytes_in <= 0:
            return 0.0
        return 100.0 * (1.0 - self.bytes_out / self.bytes_in)

def externalize(body: str, dest: Path, label: str = "blob") -> Pointer:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = body.encode()
    h = hashlib.sha256(raw).hexdigest()
    path = dest / f"{label}_{h[:12]}.txt"
    path.write_bytes(raw)
    ptr = f"[ptr:{path.name}|sha256:{h[:16]}|n={len(raw)}]"
    return Pointer(str(path), h, len(raw), len(ptr.encode()))

def measure(p: Pointer) -> dict:
    return {
        "bytes_in": p.bytes_in,
        "bytes_out": p.bytes_out,
        "savings_pct": round(p.savings_pct, 2),
        "answer": ANSWER,
    }

if __name__ == "__main__":
    import tempfile
    p = externalize("x" * 10000, Path(tempfile.mkdtemp()), "demo")
    print(measure(p))
