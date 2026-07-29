#!/usr/bin/env python3
"""
APEX External Compute Delegation Engine — Distribute & Offload Workloads.

Offloads heavy compute tasks (AI model inference, matrix crunching, batch data processing)
to exterior sources (cloud endpoints, APIs, remote worker nodes) to preserve local device CPU/RAM.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union


class ExternalComputeDelegator:
    """Delegates heavy compute workloads to exterior services and cloud workers."""

    def __init__(
        self,
        default_exterior_endpoint: Optional[str] = None,
        complexity_threshold_flops: int = 1_000_000,
    ):
        self.default_endpoint = default_exterior_endpoint or "https://generativelanguage.googleapis.com"
        self.complexity_threshold = complexity_threshold_flops
        self.delegation_stats = {
            "tasks_delegated": 0,
            "tasks_local_fallback": 0,
            "total_bytes_offloaded": 0,
            "estimated_cpu_cycles_saved": 0,
        }

    def should_delegate(self, estimated_flops: int, payload_bytes: int) -> bool:
        """Determines if a task's compute intensity justifies external delegation."""
        return estimated_flops >= self.complexity_threshold or payload_bytes > 50_000

    def delegate_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        estimated_flops: int = 5_000_000,
        local_fallback_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        custom_endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Routes task to exterior compute node or falls back locally if unreachable."""
        start_time = time.perf_counter()
        payload_json = json.dumps(payload)
        payload_bytes = len(payload_json.encode("utf-8"))

        if not self.should_delegate(estimated_flops, payload_bytes):
            # Lightweight task: run locally
            return self._run_locally(task_name, payload, local_fallback_func, start_time)

        endpoint = custom_endpoint or self.default_endpoint

        # Attempt external compute request
        try:
            req = urllib.request.Request(
                endpoint,
                data=payload_json.encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "APEX-ExternalComputeEngine/1.0"},
                method="POST",
            )
            # Timeout rapidly to prevent local thread blocking
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))

            self.delegation_stats["tasks_delegated"] += 1
            self.delegation_stats["total_bytes_offloaded"] += payload_bytes
            self.delegation_stats["estimated_cpu_cycles_saved"] += estimated_flops

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "task_name": task_name,
                "execution_mode": "EXTERIOR_DELEGATED",
                "endpoint_used": endpoint,
                "status": "SUCCESS",
                "result": response_data,
                "offloaded_bytes": payload_bytes,
                "latency_ms": round(elapsed_ms, 3),
            }

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:
            # External source offline/unreachable: graceful local fallback
            self.delegation_stats["tasks_local_fallback"] += 1
            return self._run_locally(
                task_name,
                payload,
                local_fallback_func,
                start_time,
                fallback_reason=f"Exterior endpoint unavailable: {type(err).__name__}",
            )

    def _run_locally(
        self,
        task_name: str,
        payload: Dict[str, Any],
        fallback_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]],
        start_time: float,
        fallback_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the task locally as fallback or for lightweight workloads."""
        if fallback_func:
            result = fallback_func(payload)
        else:
            result = {"status": "LOCAL_COMPUTE_DONE", "echo_payload": payload}

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        output = {
            "task_name": task_name,
            "execution_mode": "LOCAL_FALLBACK" if fallback_reason else "LOCAL_LIGHTWEIGHT",
            "status": "SUCCESS",
            "result": result,
            "latency_ms": round(elapsed_ms, 3),
        }
        if fallback_reason:
            output["fallback_reason"] = fallback_reason
        return output

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns compute delegation telemetry and offloading metrics."""
        return {
            "status": "ACTIVE",
            "threshold_flops": self.complexity_threshold,
            "default_endpoint": self.default_endpoint,
            "stats": self.delegation_stats,
        }


if __name__ == "__main__":
    delegator = ExternalComputeDelegator()
    sample_res = delegator.delegate_task(
        task_name="sample_matrix_multiply",
        payload={"matrix_size": [1024, 1024]},
        estimated_flops=10_000_000,
        local_fallback_func=lambda p: {"matrix_result": "computed_locally"},
    )
    print("Delegation Result:\n", json.dumps(sample_res, indent=2))
    print("Telemetry:\n", json.dumps(delegator.get_telemetry(), indent=2))
