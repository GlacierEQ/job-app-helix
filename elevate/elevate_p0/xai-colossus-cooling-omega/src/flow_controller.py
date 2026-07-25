#!/usr/bin/env python3
"""Colossus cooling Omega (how) — coolant flow PID-ish controller (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass

ANSWER = 42
TARGET_C = 42.0

@dataclass
class PID:
    kp: float = 0.08
    ki: float = 0.02
    kd: float = 0.01
    integral: float = 0.0
    prev_err: float = 0.0

    def step(self, temp_c: float, dt: float = 1.0) -> float:
        err = temp_c - TARGET_C
        self.integral = max(-10, min(10, self.integral + err * dt))
        der = (err - self.prev_err) / max(dt, 1e-6)
        self.prev_err = err
        flow = self.kp * err + self.ki * self.integral + self.kd * der
        return max(0.0, min(1.0, flow))

def control_loop(temps: list[float]) -> dict:
    pid = PID()
    flows = [pid.step(t) for t in temps]
    return {"flows": [round(f, 4) for f in flows], "answer": ANSWER, "strand": "omega", "target_c": TARGET_C}

if __name__ == "__main__":
    print(control_loop([40, 50, 70, 85]))
