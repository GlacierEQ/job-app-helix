#!/usr/bin/env python3
"""
Unit tests for APEX External Compute Delegation Engine.
"""
import unittest
from apex_distributed_compute import ExternalComputeDelegator


class TestExternalComputeDelegator(unittest.TestCase):

    def setUp(self):
        self.delegator = ExternalComputeDelegator(complexity_threshold_flops=100_000)

    def test_should_delegate_thresholds(self):
        # Below threshold flops & payload size -> False
        self.assertFalse(self.delegator.should_delegate(estimated_flops=50_000, payload_bytes=1_000))

        # Above threshold flops -> True
        self.assertTrue(self.delegator.should_delegate(estimated_flops=200_000, payload_bytes=1_000))

        # Large payload bytes -> True
        self.assertTrue(self.delegator.should_delegate(estimated_flops=10_000, payload_bytes=60_000))

    def test_lightweight_task_runs_locally(self):
        res = self.delegator.delegate_task(
            task_name="lightweight_addition",
            payload={"a": 1, "b": 2},
            estimated_flops=10,
            local_fallback_func=lambda p: {"sum": p["a"] + p["b"]},
        )
        self.assertEqual(res["execution_mode"], "LOCAL_LIGHTWEIGHT")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["result"]["sum"], 3)

    def test_heavy_task_graceful_fallback(self):
        # External endpoint unreachable (invalid URL) -> falls back locally cleanly
        res = self.delegator.delegate_task(
            task_name="heavy_matrix",
            payload={"size": 500},
            estimated_flops=500_000,
            local_fallback_func=lambda p: {"status": "fallback_computed"},
            custom_endpoint="http://127.0.0.1:9999/non_existent_endpoint",
        )
        self.assertEqual(res["execution_mode"], "LOCAL_FALLBACK")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["result"]["status"], "fallback_computed")
        self.assertIn("fallback_reason", res)

    def test_telemetry_tracking(self):
        _ = self.delegator.delegate_task(
            task_name="heavy_task_1",
            payload={"data": "x" * 100},
            estimated_flops=500_000,
            custom_endpoint="http://127.0.0.1:9999/non_existent_endpoint",
        )
        telemetry = self.delegator.get_telemetry()
        self.assertEqual(telemetry["status"], "ACTIVE")
        self.assertEqual(telemetry["stats"]["tasks_local_fallback"], 1)


if __name__ == "__main__":
    unittest.main()
