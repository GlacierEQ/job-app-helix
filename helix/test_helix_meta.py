#!/usr/bin/env python3
"""
Unit test for job-app-helix-meta repository.
Validates APEX Highway Engine integration & Helix registry schema.
"""
import unittest
import json
from pathlib import Path
from apex_highway import APEXHighwayEngine

class TestHelixMeta(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent

    def test_helix_registry_exists(self):
        registry_file = self.root / "helix_registry.json"
        self.assertTrue(registry_file.exists(), "helix_registry.json must exist")
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        self.assertIn("law", data)
        self.assertIn("pairs", data)

    def test_highway_engine_health(self):
        engine = APEXHighwayEngine(root_dir=self.root.parent)
        health = engine.scan_mesh_health()
        self.assertIn("mesh_status", health)
        self.assertGreater(health["total_nodes_discovered"], 0)

if __name__ == "__main__":
    unittest.main()
