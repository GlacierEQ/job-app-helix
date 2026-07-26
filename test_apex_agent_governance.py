"""Test suite for APEX Agent Governance Matrix."""
import unittest
from apex_agent_governance_matrix import APEXAgentGovernanceMatrix

class TestAPEXAgentGovernanceMatrix(unittest.TestCase):

    def test_governance_audit(self):
        matrix = APEXAgentGovernanceMatrix()
        audit = matrix.audit_agent_fleet()
        
        self.assertEqual(audit["matrix_status"], "EXCELLENCE_VERIFIED")
        self.assertTrue(audit["total_nodes_audited"] >= 60)
        self.assertTrue(audit["sidecar_mesh_coverage"] > 90.0)

    def test_double_helix_validation(self):
        matrix = APEXAgentGovernanceMatrix()
        helix = matrix.execute_double_helix_validation()
        
        self.assertEqual(helix["helix_status"], "ALPHA_OMEGA_SYNCHRONIZED")
        self.assertEqual(helix["strand_alpha"], "DOMAIN_TRUTH_ENGINE")

if __name__ == "__main__":
    unittest.main()
