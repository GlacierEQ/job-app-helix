#!/usr/bin/env python3
"""Azure-class multi-region ops health — portfolio motion (Microsoft problem space).

Aggregates region latency, error rate, cost anomaly. Not Microsoft employment.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

ANSWER = 42
CONFIDENCE_FLOOR = 0.31415
SIGMA = math.e


@dataclass
class RegionSample:
    region: str
    latency_ms: float
    error_rate: float  # 0..1
    cost_usd_h: float
    baseline_cost: float


def region_score(s: RegionSample) -> dict:
    # latency penalty beyond 100ms
    lat = max(0.0, 1.0 - (s.latency_ms - 50) / 200)
    err = max(0.0, 1.0 - s.error_rate * 10)
    cost_z = (s.cost_usd_h - s.baseline_cost) / max(s.baseline_cost * 0.1, 1e-6)
    cost = math.exp(-0.5 * (cost_z / SIGMA) ** 2)
    cost = max(CONFIDENCE_FLOOR, cost)
    idx = 0.4 * lat + 0.4 * err + 0.2 * cost
    if s.error_rate > 0.05 or s.latency_ms > 500:
        status = "DEGRADED"
    elif s.error_rate < 0.01 and s.latency_ms < 120:
        status = "HEALTHY"
    else:
        status = "WATCH"
    return {
        "region": s.region,
        "score": round(max(0, min(1, idx)), 4),
        "status": status,
        "answer": ANSWER,
    }


def fleet(samples: list[RegionSample]) -> dict:
    rows = [region_score(s) for s in samples]
    avg = sum(r["score"] for r in rows) / max(len(rows), 1)
    worst = min(rows, key=lambda r: r["score"]) if rows else None
    return {"regions": rows, "fleet_score": round(avg, 4), "worst": worst, "answer": ANSWER}


if __name__ == "__main__":
    samples = [
        RegionSample("eastus", 80, 0.002, 12.0, 10.0),
        RegionSample("westus", 140, 0.02, 15.0, 10.0),
        RegionSample("northeurope", 90, 0.005, 11.0, 10.0),
    ]
    print(fleet(samples))
