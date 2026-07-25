#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-orbital-mechanics/src"))
from alpha.kepler import R_EARTH, OrbitalElements, coe_to_state, vis_viva
a = R_EARTH + 400_000.0
el = OrbitalElements(a=a, e=0.0, i=0.5, raan=0.1, argp=0.0, ta=0.0)
sv = coe_to_state(el)
v = vis_viva(sv.radius, a)
assert abs(sv.speed - v) < 1e-3
assert el.period > 5000  # LEO ~90min
print("PROOF_OK orbital v", round(sv.speed, 2), "period", round(el.period, 1))
