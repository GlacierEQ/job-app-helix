#!/usr/bin/env python3
"""Job-app double helix runner — two spirals, same star, mutual acceleration.

Piston = loop. Spiral = output→input succession. Helix = two spirals co-aimed.

Usage:
  python3 jobapp_helix_spiral.py list
  python3 jobapp_helix_spiral.py run --pair flight
  python3 jobapp_helix_spiral.py run --all
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
REPOS = HOME / "job-app" / "repos"
REGISTRY = HOME / "job-app" / "helix_registry.json"
STATE = HOME / "GlacierEQ_Swarm" / "state"
OUT = STATE / "jobapp_helix_last.json"
BUS = HOME / "GlacierEQ_Swarm" / "automations" / "tsunami_memory_bus.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


# ─── pistons (local loops) ───────────────────────────────────────────


def piston_orbital_leo() -> dict[str, Any]:
    """Alpha piston: LEO circular orbit truth."""
    sys.path.insert(0, str(REPOS / "spacex-orbital-mechanics" / "src"))
    from alpha.kepler import MU_EARTH, R_EARTH, OrbitalElements, coe_to_state, vis_viva

    a = R_EARTH + 400_000.0
    el = OrbitalElements(a=a, e=0.0, i=0.9, raan=0.2, argp=0.0, ta=0.0)
    sv = coe_to_state(el)
    v = vis_viva(sv.radius, a)
    return {
        "piston": "orbital_leo",
        "spiral": "alpha",
        "altitude_m": 400_000.0,
        "a_m": a,
        "radius_m": sv.radius,
        "speed_m_s": sv.speed,
        "vis_viva_m_s": v,
        "period_s": el.period,
        "inclination_rad": el.i,
        "status": "NOMINAL",
    }


def piston_telemetry_from_orbit(orbit: dict) -> dict[str, Any]:
    """Bridge piston: publish orbit-derived frames on the bus (output→input)."""
    sys.path.insert(0, str(REPOS / "spacex-telemetry" / "src"))
    from telemetry_bus import Frame, TelemetryBus

    bus = TelemetryBus(max_hz=1000.0)
    # seq from quantized speed; t_ms from period slice
    speed = float(orbit.get("speed_m_s") or 0)
    period = float(orbit.get("period_s") or 1)
    frames = []
    for i in range(1, 6):
        t_ms = int((period / 100.0) * i)
        seq = i
        r = bus.ingest(Frame("gnc.orbit", seq, t_ms))
        frames.append(r)
    return {
        "piston": "telemetry_bus",
        "spiral": "bridge",
        "accepted": bus.accepted,
        "drops": bus.drops,
        "frames_ok": sum(1 for f in frames if f.get("ok")),
        "stats": bus.stats(),
        "fed_from": orbit.get("piston"),
        "status": "NOMINAL" if bus.accepted >= 4 else "DEGRADED",
    }


def piston_mission_console_from_bus(bus_out: dict, orbit: dict) -> dict[str, Any]:
    """Omega piston: console events from bus + orbit pressure."""
    sys.path.insert(0, str(REPOS / "spacex-mission-control" / "src"))
    from console import Bus, Console, Event

    b = Bus()
    b.register(Console("FD", 3))
    b.register(Console("GNC", 2))
    b.register(Console("PR", 5))

    drops = int(bus_out.get("drops") or 0)
    speed = float(orbit.get("speed_m_s") or 0)
    # severity from ops evidence (Omega accelerates on Alpha numbers)
    sev = 2
    msg = f"orbit v={speed:.1f} m/s frames_ok={bus_out.get('frames_ok')}"
    if drops > 0:
        sev = 4
        msg = f"TELEMETRY GAPS drops={drops} — {msg}"
    if speed > 7800:
        sev = max(sev, 3)

    pub = b.publish(Event("helix.flight", sev, msg))
    return {
        "piston": "mission_console",
        "spiral": "omega",
        "severity": sev,
        "published": pub,
        "fed_from": [bus_out.get("piston"), orbit.get("piston")],
        "status": "ALERT" if sev >= 4 else "NOMINAL",
    }


def piston_thermal_assess() -> dict[str, Any]:
    import importlib.util

    path = REPOS / "xai-colossus-cooling" / "connectors" / "cooling-plant" / "thermal_reality.py"
    spec = importlib.util.spec_from_file_location("thermal_reality", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["thermal_reality"] = mod
    spec.loader.exec_module(mod)
    r = mod.assess_loop(
        it_load_mw=1.2,
        flow_lpm=8000.0,
        inlet_c=25.0,
        outlet_c=32.0,
        cooling_electrical_mw=0.15,
        throttle_margin_mw=0.05,
    )
    r["piston"] = "thermal_assess"
    r["spiral"] = "alpha"
    return r


def piston_integrity_from_thermal(thermal: dict) -> dict[str, Any]:
    """Omega: integrity stance from thermal handoff (mutual acceleration)."""
    integrity = REPOS / "xai-colossus-cooling" / ".integrity"
    has = integrity.is_dir()
    status = thermal.get("status", "UNKNOWN")
    # Omega spiral: if thermal critical, integrity watch is mandatory
    escalate = status in ("CRITICAL", "THROTTLE_RISK")
    return {
        "piston": "fleet_integrity",
        "spiral": "omega",
        "integrity_dir": str(integrity),
        "integrity_present": has,
        "thermal_status": status,
        "heat_margin_mw": thermal.get("heat_margin_mw"),
        "action": "WATCHDOG_REQUIRED" if escalate or not has else "BASELINE_OK",
        "fed_from": thermal.get("piston"),
        "status": "NOMINAL" if has and not escalate else "ATTENTION",
    }


def piston_kv_prune() -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "openai-reasoning-kv-sentinel" / "src"))
    from reasoning_kv_sentinel import ReasoningKVSentinel

    s = ReasoningKVSentinel(max_cache_tokens=64, entropy_threshold=0.35, keep_tail=5)
    tokens = []
    for i in range(80):
        if i % 2 == 0:
            tokens.append({"id": i, "probs": [0.95, 0.05], "is_anchor": i % 10 == 0})
        else:
            tokens.append({"id": i, "probs": [0.5, 0.5], "is_anchor": False})
    retained, metrics = s.prune_reasoning_trajectory(tokens)
    return {
        "piston": "kv_prune",
        "spiral": "alpha",
        "metrics": metrics,
        "retained": len(retained),
        "status": metrics.get("status", "NOMINAL"),
    }


def piston_tasklets_from_kv(kv: dict) -> dict[str, Any]:
    """Omega: schedule recovery tasklets from KV pressure (output→input)."""
    sys.path.insert(0, str(REPOS / "tasklet-micro-agent-engine" / "src"))
    from tasklet_micro_agent_engine import TaskletMicroAgentEngine

    eng = TaskletMicroAgentEngine(max_concurrent_tasklets=8)
    evicted = int((kv.get("metrics") or {}).get("evicted_tokens") or 0)
    # more pressure → higher priority (lower number) recovery work
    priority = 1 if evicted > 20 else 10
    r1 = eng.spawn_tasklet("kv_compact", {"evicted": evicted}, priority=priority)
    r2 = eng.spawn_tasklet("resume_reason", {"retained": kv.get("retained")}, priority=priority + 5)
    nxt = eng.next_tasklet()
    return {
        "piston": "tasklet_schedule",
        "spiral": "omega",
        "spawned": [r1, r2],
        "next": nxt,
        "efficiency": eng.efficiency(),
        "fed_from": kv.get("piston"),
        "status": "NOMINAL" if r1.get("ok") else "REJECTED",
    }


def piston_tpu_mesh() -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "deepmind-tpu-mesh-optimizer" / "src"))
    from tpu_mesh_optimizer import TPUMeshRingOptimizer

    opt = TPUMeshRingOptimizer(tpu_slices=64, ici_bandwidth_gbps=4800.0)
    r = opt.optimize_ring_attention(sequence_length=65536)
    r["piston"] = "tpu_mesh"
    r["spiral"] = "alpha"
    return r


def piston_gate_from_mesh(mesh: dict) -> dict[str, Any]:
    """Omega meta-ops: proof spiral consumes mesh metrics."""
    hide = float(mesh.get("ici_hide_percent") or mesh.get("latency_hidden_percent") or 0)
    ok = hide >= 0 and mesh.get("status") in (
        "OPTIMAL_ASYNC_SHARDED",
        "ICI_BOUND",
        "OPTIMAL_ASYNC",
    )
    return {
        "piston": "hire_proof",
        "spiral": "omega",
        "mesh_status": mesh.get("status"),
        "ici_hide_percent": hide,
        "proof": "ACCEPT" if ok else "REJECT",
        "fed_from": mesh.get("piston"),
        "status": "NOMINAL" if ok else "FAIL",
    }


# ─── spirals (succession) ────────────────────────────────────────────


def spiral_run(pistons: list) -> dict[str, Any]:
    """Run pistons in series: each output is next input (partial)."""
    chain = []
    prev: dict[str, Any] | None = None
    t0 = time.perf_counter()
    for fn in pistons:
        if prev is None:
            out = fn() if fn.__code__.co_argcount == 0 else fn({})
        else:
            # call with prior envelope(s)
            n = fn.__code__.co_argcount
            if n == 0:
                out = fn()
            elif n == 1:
                out = fn(prev)
            else:
                # multi-arg pistons get last + accumulated
                out = fn(prev, chain[0] if chain else prev)
        chain.append(out)
        prev = out
    return {
        "chain": chain,
        "steps": len(chain),
        "seconds": round(time.perf_counter() - t0, 4),
        "final": prev,
    }


def run_flight() -> dict[str, Any]:
    """Double helix: Alpha orbital + bridge telemetry + Omega console; then back-pressure note."""
    # Alpha spiral start
    orbit = piston_orbital_leo()
    # Bridge (shared medium)
    bus = piston_telemetry_from_orbit(orbit)
    # Omega spiral
    console = piston_mission_console_from_bus(bus, orbit)
    # Mutual acceleration: Omega severity feeds Alpha refinement hint
    refine = {
        "piston": "alpha_refine_hint",
        "spiral": "alpha",
        "hint": (
            "increase_keep_alive_hz"
            if console.get("severity", 0) >= 4
            else "hold_profile"
        ),
        "fed_from": console.get("piston"),
        "accelerates": "orbital_truth",
    }
    return {
        "pair": "flight",
        "star": "Flight awareness",
        "alpha_spiral": [orbit],
        "bridge": [bus],
        "omega_spiral": [console],
        "mutual_acceleration": [refine],
        "ok": all(
            x.get("status") in ("NOMINAL", "ALERT", "DEGRADED", "ATTENTION")
            for x in (orbit, bus, console)
        ),
    }


def run_colossus_thermal() -> dict[str, Any]:
    thermal = piston_thermal_assess()
    integ = piston_integrity_from_thermal(thermal)
    # mutual: integrity ATTENTION → alpha should re-assess with more flow (hint)
    accel = {
        "piston": "alpha_flow_hint",
        "spiral": "alpha",
        "hint_flow_lpm_delta": 500 if integ.get("status") != "NOMINAL" else 0,
        "fed_from": integ.get("piston"),
    }
    return {
        "pair": "colossus_thermal",
        "star": "Colossus survival",
        "alpha_spiral": [thermal],
        "omega_spiral": [integ],
        "mutual_acceleration": [accel],
        "ok": thermal.get("status") == "NOMINAL",
    }


def run_reasoning_pressure() -> dict[str, Any]:
    kv = piston_kv_prune()
    tasks = piston_tasklets_from_kv(kv)
    # mutual: tasklet accept_rate feeds alpha threshold hint
    eff = tasks.get("efficiency") or {}
    accel = {
        "piston": "alpha_entropy_hint",
        "spiral": "alpha",
        "hint_entropy_threshold_delta": -0.05 if eff.get("rejected", 0) else 0.0,
        "fed_from": tasks.get("piston"),
    }
    return {
        "pair": "reasoning_pressure",
        "star": "Reasoning under pressure",
        "alpha_spiral": [kv],
        "omega_spiral": [tasks],
        "mutual_acceleration": [accel],
        "ok": kv.get("status") == "NOMINAL" and tasks.get("status") == "NOMINAL",
    }


def run_mesh_proof() -> dict[str, Any]:
    mesh = piston_tpu_mesh()
    gate = piston_gate_from_mesh(mesh)
    accel = {
        "piston": "alpha_slice_hint",
        "spiral": "alpha",
        "hint": "raise_bw" if mesh.get("status") == "ICI_BOUND" else "hold",
        "fed_from": gate.get("piston"),
    }
    return {
        "pair": "mesh_proof",
        "star": "Hire-grade proof",
        "alpha_spiral": [mesh],
        "omega_spiral": [gate],
        "mutual_acceleration": [accel],
        "ok": gate.get("proof") == "ACCEPT",
    }


# ─── deeper pairs: prop / ground / energy / agents ───────────────────


def piston_prop_health(sample: dict | None = None) -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "spacex-propulsion-monitor" / "src"))
    from prop_health import Sample, health

    sample = sample or {"chamber_p_pct": 0.97, "mr_error": 0.03, "vibe_g": 4.0}
    h = health(
        Sample(
            chamber_p_pct=float(sample["chamber_p_pct"]),
            mr_error=float(sample["mr_error"]),
            vibe_g=float(sample["vibe_g"]),
        )
    )
    return {
        "piston": "prop_health",
        "spiral": "alpha",
        "health": h.get("health"),
        "status": h.get("status"),
        "sample": sample,
    }


def piston_telemetry_from_prop(prop: dict) -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "spacex-telemetry" / "src"))
    from telemetry_bus import Frame, TelemetryBus

    bus = TelemetryBus(max_hz=100.0)
    status = prop.get("status", "GREEN")
    # RED → inject gap pattern (seq jump)
    r1 = bus.ingest(Frame("prop.chamber", 1, 0))
    if status == "RED":
        r2 = bus.ingest(Frame("prop.chamber", 5, 50))  # gap
    else:
        r2 = bus.ingest(Frame("prop.chamber", 2, 20))
    return {
        "piston": "telemetry_prop_bridge",
        "spiral": "bridge",
        "accepted": bus.accepted,
        "drops": bus.drops,
        "frames": [r1, r2],
        "fed_from": prop.get("piston"),
        "status": "DEGRADED" if bus.drops else "NOMINAL",
    }


def piston_launch_from_prop(prop: dict, bus: dict | None = None) -> dict[str, Any]:
    """Omega: prop health + bus gaps drive holds on the sequencer."""
    sys.path.insert(0, str(REPOS / "spacex-launch-sequencer" / "src"))
    from sequencer import Sequencer

    seq = Sequencer()
    seq.advance()  # T-CHECKS
    holds = []
    if prop.get("status") in ("RED", "YELLOW"):
        holds.append(f"prop_{prop.get('status')}")
        seq.hold(f"prop_{prop.get('status')}")
    if bus and bus.get("drops", 0) > 0:
        holds.append("telemetry_gaps")
        seq.hold("telemetry_gaps")
    adv = seq.advance()
    return {
        "piston": "launch_sequencer",
        "spiral": "omega",
        "stage": seq.stage,
        "holds": list(seq.holds),
        "advance": adv,
        "fed_from": [prop.get("piston"), (bus or {}).get("piston")],
        "status": "HOLD" if seq.holds else "GO_PATH",
    }


def run_spacex_propulsion() -> dict[str, Any]:
    prop = piston_prop_health()
    bus = piston_telemetry_from_prop(prop)
    launch = piston_launch_from_prop(prop, bus)
    # mutual: holds → alpha should derate chamber (hint)
    accel = {
        "piston": "alpha_prop_hint",
        "spiral": "alpha",
        "hint": "derate_chamber" if launch.get("holds") else "hold_throttle",
        "hint_chamber_p_pct": 0.9 if launch.get("holds") else 0.97,
        "fed_from": launch.get("piston"),
    }
    # second alpha stroke with refined sample (spiral succession)
    refined = piston_prop_health(
        {
            "chamber_p_pct": accel["hint_chamber_p_pct"],
            "mr_error": 0.02,
            "vibe_g": 3.0,
        }
    )
    refined["piston"] = "prop_health_refined"
    return {
        "pair": "spacex_propulsion",
        "star": "Propulsion awareness",
        "alpha_spiral": [prop, refined],
        "bridge": [bus],
        "omega_spiral": [launch],
        "mutual_acceleration": [accel],
        "ok": prop.get("status") in ("GREEN", "YELLOW", "RED") and refined.get("status") == "GREEN",
    }


def piston_ground_plan(need_mbps: float = 55.0) -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "spacex-ground-network" / "src"))
    from ground_net import Station, plan

    stations = [
        Station("AUS", True, 14.0, 45.0),
        Station("HAW", True, 11.0, 25.0),
        Station("AK", False, 20.0, 80.0),
        Station("EU", True, 9.5, 20.0),
    ]
    p = plan(stations, need_mbps)
    return {
        "piston": "ground_plan",
        "spiral": "alpha",
        "need_mbps": need_mbps,
        "plan": p,
        "status": "NOMINAL" if p.get("ok") else "CAPACITY_SHORT",
    }


def piston_mesh_route_from_ground(ground: dict) -> dict[str, Any]:
    """Omega: build mesh graph weighted by ground plan success."""
    sys.path.insert(0, str(REPOS / "spacex-satellite-mesh" / "src"))
    from mesh_route import shortest_path

    ok = (ground.get("plan") or {}).get("ok", False)
    # if ground short, inflate ISL costs (harder mesh)
    w = 1.0 if ok else 3.0
    graph = {
        "S1": {"S2": w, "S3": 2.0 * w},
        "S2": {"S1": w, "S4": 1.5 * w},
        "S3": {"S1": 2.0 * w, "S4": w},
        "S4": {"S2": 1.5 * w, "S3": w, "GND": 0.5 if ok else 4.0},
        "GND": {},
    }
    path = shortest_path(graph, "S1", "GND")
    return {
        "piston": "satellite_mesh_route",
        "spiral": "omega",
        "path": path,
        "fed_from": ground.get("piston"),
        "status": "NOMINAL" if path.get("ok") else "NO_PATH",
    }


def run_spacex_ground() -> dict[str, Any]:
    ground = piston_ground_plan(55.0)
    mesh = piston_mesh_route_from_ground(ground)
    # mutual: mesh cost high → alpha should request more ground mbps / stations
    cost = (mesh.get("path") or {}).get("cost") or 0
    accel = {
        "piston": "alpha_ground_hint",
        "spiral": "alpha",
        "hint_need_mbps_delta": 20 if cost > 5 else 0,
        "fed_from": mesh.get("piston"),
    }
    ground2 = piston_ground_plan(55.0 + accel["hint_need_mbps_delta"])
    ground2["piston"] = "ground_plan_refined"
    mesh2 = piston_mesh_route_from_ground(ground2)
    mesh2["piston"] = "satellite_mesh_route_refined"
    return {
        "pair": "spacex_ground",
        "star": "Ground network truth",
        "alpha_spiral": [ground, ground2],
        "omega_spiral": [mesh, mesh2],
        "mutual_acceleration": [accel],
        "ok": ground2.get("status") == "NOMINAL" and mesh2.get("status") == "NOMINAL",
    }


def piston_energy_load() -> dict[str, Any]:
    """Alpha: Megapack-aware energy envelope (constants from colossus-energy)."""
    sys.path.insert(0, str(REPOS / "xai-colossus-energy"))
    try:
        from megapack_buffer.megapack_model import (
            DEFAULT_CAPACITY_MWH,
            DEFAULT_MAX_DISCHARGE_MW,
            CRITICAL_SOC_PCT,
        )
    except Exception:
        DEFAULT_CAPACITY_MWH, DEFAULT_MAX_DISCHARGE_MW, CRITICAL_SOC_PCT = 560.0, 140.0, 15.0

    # Zone-scale IT heat load for thermal handoff (not full campus 1.5GW)
    it_load_mw = 2.5
    grid_util_pct = 91.0
    soc_pct = 62.0
    discharge_needed = grid_util_pct >= 90.0
    campus_it_mw = 1500.0  # campus context only
    return {
        "piston": "energy_load",
        "spiral": "alpha",
        "it_load_mw": it_load_mw,
        "campus_it_mw": campus_it_mw,
        "grid_util_pct": grid_util_pct,
        "soc_pct": soc_pct,
        "megapack_capacity_mwh": DEFAULT_CAPACITY_MWH,
        "max_discharge_mw": DEFAULT_MAX_DISCHARGE_MW,
        "critical_soc_pct": CRITICAL_SOC_PCT,
        "discharge_armed": discharge_needed and soc_pct > CRITICAL_SOC_PCT,
        "status": "STRESSED" if discharge_needed else "NOMINAL",
    }


def piston_thermal_from_energy(energy: dict) -> dict[str, Any]:
    """Omega cooling spiral fed by IT load from energy (output→input)."""
    import importlib.util

    path = REPOS / "xai-colossus-cooling" / "connectors" / "cooling-plant" / "thermal_reality.py"
    spec = importlib.util.spec_from_file_location("thermal_reality", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["thermal_reality"] = mod
    spec.loader.exec_module(mod)

    it = float(energy.get("it_load_mw") or 1.0)
    # cooling electrical ~ fraction of IT; high flow for MW-class zone
    cool_e = 0.12 * it if energy.get("discharge_armed") else 0.08 * it
    # size flow so Q≈mcpΔT can clear IT (approx: need ~ m = Q/(cp ΔT))
    flow_lpm = max(20000.0, it * 15000.0)
    r = mod.assess_loop(
        it_load_mw=it,
        flow_lpm=flow_lpm,
        inlet_c=24.0,
        outlet_c=31.0,
        cooling_electrical_mw=cool_e,
        throttle_margin_mw=0.05,
    )
    r["piston"] = "thermal_from_energy"
    r["spiral"] = "omega"
    r["fed_from"] = energy.get("piston")
    return r


def run_colossus_energy() -> dict[str, Any]:
    energy = piston_energy_load()
    thermal = piston_thermal_from_energy(energy)
    # mutual: thermal margin thin → alpha should shed IT load / delay train job
    margin = float(thermal.get("heat_margin_mw") or 0)
    accel = {
        "piston": "alpha_energy_hint",
        "spiral": "alpha",
        "hint_shed_mw": 10.0 if margin < 5.0 else 0.0,
        "fed_from": thermal.get("piston"),
    }
    energy2 = dict(energy)
    energy2["it_load_mw"] = max(0.5, energy["it_load_mw"] - accel["hint_shed_mw"])
    energy2["piston"] = "energy_load_refined"
    energy2["status"] = "NOMINAL" if energy2["it_load_mw"] <= 3.0 else energy["status"]
    thermal2 = piston_thermal_from_energy(energy2)
    thermal2["piston"] = "thermal_from_energy_refined"
    return {
        "pair": "colossus_energy",
        "star": "Energy + cooling co-aim",
        "alpha_spiral": [energy, energy2],
        "omega_spiral": [thermal, thermal2],
        "mutual_acceleration": [accel],
        "ok": thermal2.get("status") == "NOMINAL",
    }


def piston_agent_coord() -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "anthropic-agent-coordinator" / "src"))
    from agent_coordinator import Agent, AgentCoordinator, Task

    c = AgentCoordinator()
    c.register_agent(Agent("a1", ["code", "review"], 0.2, 1.0, 0.9))
    c.register_agent(Agent("a2", ["research", "write"], 0.5, 1.0, 0.8))
    c.register_agent(Agent("a3", ["code", "test"], 0.1, 1.0, 0.95))
    t = Task("t1", ["code", "test"], priority=1, estimated_load=0.3)
    assigned = c.assign_task(t)
    return {
        "piston": "agent_coord",
        "spiral": "alpha",
        "assigned_to": assigned,
        "agents": list(c.agents.keys()),
        "status": "NOMINAL" if assigned else "UNASSIGNED",
    }


def piston_tasklets_from_coord(coord: dict) -> dict[str, Any]:
    sys.path.insert(0, str(REPOS / "tasklet-micro-agent-engine" / "src"))
    from tasklet_micro_agent_engine import TaskletMicroAgentEngine

    eng = TaskletMicroAgentEngine(max_concurrent_tasklets=4)
    aid = coord.get("assigned_to") or "fallback"
    r = eng.spawn_tasklet(
        f"run_{aid}",
        {"from_coord": True, "agent": aid},
        priority=1 if coord.get("status") == "NOMINAL" else 50,
    )
    return {
        "piston": "tasklet_from_coord",
        "spiral": "omega",
        "spawn": r,
        "efficiency": eng.efficiency(),
        "fed_from": coord.get("piston"),
        "status": "NOMINAL" if r.get("ok") else "REJECTED",
    }


def run_agent_platform() -> dict[str, Any]:
    coord = piston_agent_coord()
    tasks = piston_tasklets_from_coord(coord)
    accel = {
        "piston": "alpha_coord_hint",
        "spiral": "alpha",
        "hint": "register_more_capacity" if tasks.get("status") != "NOMINAL" else "hold",
        "fed_from": tasks.get("piston"),
    }
    return {
        "pair": "agent_platform",
        "star": "Agent platform",
        "alpha_spiral": [coord],
        "omega_spiral": [tasks],
        "mutual_acceleration": [accel],
        "ok": coord.get("status") == "NOMINAL" and tasks.get("status") == "NOMINAL",
    }


def run_launch_campaign() -> dict[str, Any]:
    """Multi-star meta-spiral: flight + prop + ground → one launch campaign star.

    Three stars (flight awareness, propulsion, ground) are co-aimed at
    **campaign go/no-go**. Each sub-spiral's output is the next campaign input.
    """
    # ── Star 1: flight awareness ─────────────────────────────────────
    flight = run_flight()
    # ── Star 2: propulsion (feeds holds) ─────────────────────────────
    prop = run_spacex_propulsion()
    # ── Star 3: ground/mesh (feeds link readiness) ───────────────────
    ground = run_spacex_ground()

    # Campaign spiral: successive go/no-go pistons from each star's final state
    flight_ok = bool(flight.get("ok"))
    prop_ok = bool(prop.get("ok"))
    ground_ok = bool(ground.get("ok"))

    prop_holds = []
    for node in prop.get("omega_spiral") or []:
        prop_holds.extend(node.get("holds") or [])

    ground_final = (ground.get("omega_spiral") or [{}])[-1]
    mesh_ok = ground_final.get("status") == "NOMINAL"

    flight_sev = 0
    for node in flight.get("omega_spiral") or []:
        flight_sev = max(flight_sev, int(node.get("severity") or 0))

    # Meta-piston: campaign decision (every output is next input)
    reasons = []
    if not flight_ok or flight_sev >= 4:
        reasons.append("flight_or_telemetry")
    if not prop_ok or prop_holds:
        reasons.append("propulsion_holds:" + ",".join(prop_holds or ["non_green"]))
    if not ground_ok or not mesh_ok:
        reasons.append("ground_or_mesh")

    go = not reasons
    decision = {
        "piston": "campaign_go_nogo",
        "spiral": "meta",
        "decision": "GO" if go else "NO-GO",
        "reasons": reasons,
        "inputs": {
            "flight_ok": flight_ok,
            "flight_severity": flight_sev,
            "prop_ok": prop_ok,
            "prop_holds": prop_holds,
            "ground_ok": ground_ok,
            "mesh_status": ground_final.get("status"),
        },
        "status": "GO" if go else "NO-GO",
    }

    # Mutual acceleration across stars: NO-GO → refine each sub-spiral once more
    refinements = []
    if not go:
        if "propulsion" in " ".join(reasons):
            refinements.append(
                piston_prop_health(
                    {"chamber_p_pct": 0.99, "mr_error": 0.01, "vibe_g": 2.0}
                )
            )
            refinements[-1]["piston"] = "campaign_prop_refine"
        if "ground" in " ".join(reasons) or "mesh" in " ".join(reasons):
            g2 = piston_ground_plan(80.0)
            g2["piston"] = "campaign_ground_refine"
            m2 = piston_mesh_route_from_ground(g2)
            m2["piston"] = "campaign_mesh_refine"
            refinements.extend([g2, m2])
        if "flight" in " ".join(reasons):
            refinements.append(
                {
                    "piston": "campaign_flight_refine_hint",
                    "hint": "increase_keep_alive_hz",
                    "fed_from": "campaign_go_nogo",
                }
            )

    # Final campaign re-score after refinements (second meta stroke)
    if refinements:
        # re-check prop if refined
        prop_status = prop.get("ok")
        for r in refinements:
            if r.get("piston") == "campaign_prop_refine":
                prop_status = r.get("status") == "GREEN"
        mesh_status = mesh_ok
        for r in refinements:
            if r.get("piston") == "campaign_mesh_refine":
                mesh_status = r.get("status") == "NOMINAL"
        go2 = prop_status and mesh_status and flight_ok
        decision_final = {
            "piston": "campaign_go_nogo_final",
            "spiral": "meta",
            "decision": "GO" if go2 else "NO-GO",
            "prior": decision["decision"],
            "refinements": len(refinements),
            "status": "GO" if go2 else "NO-GO",
        }
    else:
        decision_final = dict(decision)
        decision_final["piston"] = "campaign_go_nogo_final"
        go2 = go

    return {
        "pair": "launch_campaign",
        "star": "Launch campaign go/no-go (multi-star meta-spiral)",
        "meta_star": "campaign",
        "sub_stars": {
            "flight": flight.get("star"),
            "propulsion": prop.get("star"),
            "ground": ground.get("star"),
        },
        "alpha_spiral": [
            {"sub": "flight", "summary": flight.get("ok")},
            {"sub": "propulsion", "summary": prop.get("ok")},
            {"sub": "ground", "summary": ground.get("ok")},
        ],
        "omega_spiral": [decision, decision_final],
        "bridge": [],
        "sub_results": {
            "flight": {
                "ok": flight.get("ok"),
                "seconds": flight.get("seconds"),
            },
            "propulsion": {
                "ok": prop.get("ok"),
                "holds": prop_holds,
                "seconds": prop.get("seconds"),
            },
            "ground": {
                "ok": ground.get("ok"),
                "mesh": ground_final.get("status"),
                "seconds": ground.get("seconds"),
            },
        },
        "mutual_acceleration": refinements,
        "campaign_decision": decision_final.get("decision"),
        "ok": go2,
    }


RUNNERS = {
    "flight": run_flight,
    "colossus_thermal": run_colossus_thermal,
    "reasoning_pressure": run_reasoning_pressure,
    "mesh_proof": run_mesh_proof,
    "spacex_propulsion": run_spacex_propulsion,
    "spacex_ground": run_spacex_ground,
    "colossus_energy": run_colossus_energy,
    "agent_platform": run_agent_platform,
    "launch_campaign": run_launch_campaign,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Job-app double helix spiral runner")
    ap.add_argument("cmd", choices=["list", "run"])
    ap.add_argument("--pair", choices=list(RUNNERS.keys()), default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    reg = load_registry()
    if args.cmd == "list":
        print(json.dumps({"law": reg.get("law"), "pairs": reg.get("pairs")}, indent=2))
        return 0

    ids = list(RUNNERS.keys()) if args.all or not args.pair else [args.pair]
    results = []
    for pid in ids:
        t0 = time.perf_counter()
        try:
            r = RUNNERS[pid]()
            r["seconds"] = round(time.perf_counter() - t0, 4)
            results.append(r)
        except Exception as e:
            results.append({"pair": pid, "ok": False, "error": str(e)[:300]})

    report = {
        "ts": utc_now(),
        "protocol": "job-app double helix — two spirals, same star, mutual acceleration",
        "law": reg.get("law"),
        "ok": all(r.get("ok") for r in results),
        "pairs_run": len(results),
        "results": results,
        "registry": str(REGISTRY),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if BUS.is_file():
        import subprocess

        subprocess.run(
            [
                sys.executable,
                str(BUS),
                "write",
                f"Job-app helix run {report['ts']}: ok={report['ok']} pairs={ids}",
                "--tags",
                "helix,job-app,forge",
                "--key",
                "jobapp-helix-last",
            ],
            capture_output=True,
            timeout=30,
        )

    print(
        json.dumps(
            {
                "ok": report["ok"],
                "pairs": [
                    {
                        "id": r.get("pair"),
                        "ok": r.get("ok"),
                        "star": r.get("star"),
                        "seconds": r.get("seconds"),
                    }
                    for r in results
                ],
                "ptr": str(OUT),
            },
            indent=2,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
