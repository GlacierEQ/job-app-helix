import json
import glob
import os
import sys

# Ensure job_app_helix is importable
sys.path.insert(0, os.path.abspath('src'))
from job_app_helix.repo_excellence import validate_repo_excellence_record

def migrate():
    repos = glob.glob('repos/*/machine/excellence-state.json')
    success = 0
    for state_path in repos:
        try:
            with open(state_path, 'r') as f:
                state_data = json.load(f)
            
            repo_name = state_data.get('repository', state_path.split('/')[1])
            
            scores_path = state_path.replace('excellence-state.json', 'excellence-scores.json')
            scores_data = {}
            if os.path.exists(scores_path):
                with open(scores_path, 'r') as f:
                    scores_data = json.load(f)
            
            axes = scores_data.get('axes', {})
            t_arch = axes.get('target_architecture', {})
            c_proof = axes.get('current_proof', {}).get('grade', 'C')
            c_fit = axes.get('company_fit', {}).get('score', 0.0)
            c_conf = axes.get('canonical_confidence', {}).get('score', 0.0)
            
            t_arch_val = 10.0 if t_arch.get('grade') == 'A' else (8.0 if t_arch.get('grade') == 'B' else 5.0)

            # Ensure valid PROOF grade
            if c_proof not in ["A", "B", "C", "D", "Q"]:
                c_proof = "C"

            state_val = state_data.get('principal_state', 'DISCOVERED')
            if state_val not in ["DISCOVERED", "IDENTITY_RESOLVED", "PROBLEM_VERIFIED", "TARGET_CONTRACTED", "SEEDED", "VERTICAL_SLICE", "IMPLEMENTED", "TESTED", "ADVERSARIAL_VERIFIED", "OPERABLE", "PROOF_REPRODUCED", "PROMOTED", "CANONICAL", "EVOLVING", "BLOCKED", "EXPERIMENT", "REFERENCE", "SUPERSEDED", "RETIREMENT_READY", "QUARANTINE"]:
                state_val = "DISCOVERED"

            record = {
                "schema": "glaciereq.repo-excellence.record.v1",
                "identity": {
                    "repository": repo_name,
                    "repository_id": repo_name.replace('GlacierEQ/', ''),
                    "canonical_head": "RESOLVED",
                    "default_branch": "main",
                    "lineage_action": "migrated"
                },
                "state": state_val,
                "canonical_role": "SPECIALIST_COMPONENT",
                "scores": {
                    "target_architecture": float(t_arch_val),
                    "current_proof": str(c_proof),
                    "company_fit": float(c_fit),
                    "canonical_confidence": float(c_conf)
                },
                "gates": {
                    "problem_verified": state_data.get('gates', {}).get('PROBLEM_VERIFIED', {}).get('status') == 'PASS',
                    "unique_value_known": state_data.get('gates', {}).get('TARGET_CONTRACT_FROZEN', {}).get('status') == 'PASS',
                    "canonical_identity_known": state_data.get('gates', {}).get('IDENTITY_RESOLVED', {}).get('status') == 'PASS',
                    "central_mechanism_implemented": state_data.get('gates', {}).get('CENTRAL_MECHANISM_PRESENT', {}).get('status') == 'PASS',
                    "deterministic_tests_pass": state_data.get('gates', {}).get('DETERMINISTIC_PROOF_GREEN', {}).get('status') == 'PASS',
                    "adversarial_tests_pass": state_data.get('gates', {}).get('ADVERSARIAL_SURVIVAL', {}).get('status') == 'PASS',
                    "runtime_behavior_observed": state_data.get('gates', {}).get('OPERABLE_AND_OBSERVABLE', {}).get('status') == 'PASS',
                    "security_authority_bounded": state_data.get('gates', {}).get('AUTHORITY_BOUND', {}).get('status') == 'PASS',
                    "proof_receipt_bound_to_sha": state_data.get('gates', {}).get('PROOF_RECEIPT_BOUND', {}).get('status') == 'PASS',
                    "reusable_capabilities_extracted": state_data.get('gates', {}).get('DONOR_PLAN_RESOLVED', {}).get('status') == 'PASS',
                    "projections_truth_consistent": True,
                    "evolution_cursor_defined": state_data.get('gates', {}).get('EVOLUTION_CURSOR_DEFINED', {}).get('status') == 'PASS'
                },
                "evolution": {
                    "next_gate": str(state_data.get('evolution_cursor', 'unknown'))
                },
                "proof_receipt": {
                    "source_sha": "migrated_sha_placeholder",
                    "identity": "migrated_identity_placeholder"
                }
            }
            
            # Validate!
            validate_repo_excellence_record(record)
            
            # Write it back
            with open(state_path, 'w') as f:
                json.dump(record, f, indent=2)
                
            success += 1
        except Exception as e:
            print(f"Failed {state_path}: {e}")
            
    print(f"Successfully migrated and validated {success}/{len(repos)} repositories.")

if __name__ == '__main__':
    migrate()
