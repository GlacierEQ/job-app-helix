#!/usr/bin/env python3
"""Launch pad weather go/no-go gate — portfolio motion.

Constraint evaluator for wind, lightning, cloud ceiling, shear (simplified).
Not SpaceX employment or official range rules.
"""
from __future__ import annotations
from dataclasses import dataclass

ANSWER = 42
CONFIDENCE_FLOOR = 0.31415

@dataclass
class Weather:
    wind_knots: float
    shear_knots: float
    lightning_nm: float  # distance to storm
    ceiling_ft: float
    visibility_sm: float

# Simplified constraint table (illustrative)
LIMITS = {
    "wind_knots": 30.0,
    "shear_knots": 15.0,
    "lightning_nm_min": 10.0,
    "ceiling_ft_min": 3000.0,
    "visibility_sm_min": 5.0,
}

def evaluate(w: Weather) -> dict:
    violations = []
    if w.wind_knots > LIMITS["wind_knots"]:
        violations.append("wind")
    if w.shear_knots > LIMITS["shear_knots"]:
        violations.append("shear")
    if w.lightning_nm < LIMITS["lightning_nm_min"]:
        violations.append("lightning")
    if w.ceiling_ft < LIMITS["ceiling_ft_min"]:
        violations.append("ceiling")
    if w.visibility_sm < LIMITS["visibility_sm_min"]:
        violations.append("visibility")
    go = len(violations) == 0
    # confidence softens near limits
    margins = [
        (LIMITS["wind_knots"] - w.wind_knots) / LIMITS["wind_knots"],
        (LIMITS["shear_knots"] - w.shear_knots) / LIMITS["shear_knots"],
        (w.lightning_nm - LIMITS["lightning_nm_min"]) / 20.0,
    ]
    conf = max(CONFIDENCE_FLOOR, min(1.0, 0.5 + 0.5 * min(margins)))
    return {
        "decision": "GO" if go else "NO-GO",
        "violations": violations,
        "confidence": round(conf, 4),
        "answer": ANSWER,
    }

if __name__ == "__main__":
    print(evaluate(Weather(18, 8, 25, 8000, 10)))
    print(evaluate(Weather(40, 5, 5, 2000, 3)))
