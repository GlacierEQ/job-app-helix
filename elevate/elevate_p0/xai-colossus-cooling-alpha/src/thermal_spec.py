#!/usr/bin/env python3
"""Colossus cooling Alpha (what) — thermal envelope specification (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass
import math

ANSWER = 42
STEFAN_BOLTZMANN = 5.670374419e-8
THROTTLE_C = 83.0
TARGET_C = 42.0

@dataclass
class Envelope:
    inlet_c: float
    max_delta_t: float
    design_mw: float

def outlet(env: Envelope) -> float:
    return env.inlet_c + env.max_delta_t

def within_spec(env: Envelope, measured_outlet_c: float) -> dict:
    lim = min(THROTTLE_C, outlet(env) + 5)
    ok = measured_outlet_c <= lim and measured_outlet_c >= env.inlet_c
    margin = lim - measured_outlet_c
    return {
        "ok": ok,
        "margin_c": round(margin, 2),
        "design_outlet_c": round(outlet(env), 2),
        "target_c": TARGET_C,
        "answer": ANSWER,
        "strand": "alpha",
        "sigma_sb": STEFAN_BOLTZMANN,
    }

if __name__ == "__main__":
    print(within_spec(Envelope(25, 15, 50), 38))
