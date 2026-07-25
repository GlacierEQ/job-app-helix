"""Test suite for APEX Highway Engine & Inter-Orbit Event Routing."""
import unittest
from apex_highway import APEXHighwayEngine

class TestAPEXHighwayEngine(unittest.TestCase):

    def test_mesh_discovery_and_health(self):
        engine = APEXHighwayEngine()
        health = engine.scan_mesh_health()
        
        self.assertEqual(health["mesh_status"], "OPERATIONAL")
        self.assertTrue(health["healthy_nodes"] > 0)
        self.assertEqual(health["mesh_coverage_percent"], 100.0)

    def test_inter_orbit_event_routing(self):
        engine = APEXHighwayEngine()
        res = engine.route_inter_orbit_event(
            source_orbit="SpaceX_Aerospace",
            target_orbit="xAI_Colossus_Compute",
            event_payload={"thermal_margin_c": 14.2}
        )

        self.assertEqual(res["transmission_status"], "DELIVERED_HIGHWAY")
        self.assertTrue(res["event_id"].startswith("APEX-EVT-"))

if __name__ == "__main__":
    unittest.main()
