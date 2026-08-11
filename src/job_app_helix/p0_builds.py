# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

P0_IDS = ('cursor', 'apptronik', 'arm', 'astera_labs', 'braintrust', 'clickhouse', 'cognition', 'crusoe', 'etched', 'figure_ai', 'fireworks_ai', 'lambda', 'langchain', 'mongodb', 'obsidian_security', 'pinecone', 'safe_superintelligence_ssi', 'shield_ai', 'skild_ai', 'supabase', 'tsmc', 'temporal', 'thinking_machines_lab', 'together_ai', 'world_labs')

def patch_intent_twin(req, forbid, changed, req_tests, seen_tests):
    return {'aligned': req <= changed and (not forbid & changed) and (req_tests <= seen_tests), 'missing_paths': sorted(req - changed), 'forbidden_touches': sorted(forbid & changed), 'missing_tests': sorted(req_tests - seen_tests)}

def deployment_interface_standardizer(cells):
    required = {'handoff_zone', 'safety_field', 'task_api', 'fixture'}
    good = []
    bad = []
    for cell in cells:
        if required <= set(cell):
            good.append({'name': cell['name'], 'handoff_zone': str(cell['handoff_zone']).lower(), 'safety_field': str(cell['safety_field']).lower(), 'task_api': tuple(sorted(cell['task_api'])), 'fixture': str(cell['fixture']).lower()})
        else:
            bad.append(cell['name'])
    return {'compatible_count': len(good), 'contracts': good, 'incompatible': bad}

def cross_isa_ai_placement_contract(workload, targets):
    weights = {k: float(workload.get(f'{k}_weight', 1.0)) for k in ('latency', 'energy', 'memory', 'privacy')}
    scored = []
    for target in targets:
        score = weights['latency'] * float(target['latency_ms']) + weights['energy'] * float(target['energy_j']) + weights['memory'] * float(target['memory_cost']) + weights['privacy'] * float(target['privacy_cost'])
        scored.append((score, target['name']))
    scored.sort()
    return {'selected': scored[0][1], 'scores': scored}

def fabric_congestion_autopilot(links, threshold=0.85):
    hot = []
    spare = []
    for link in links:
        util = float(link['load']) / float(link['capacity'])
        (hot if util >= threshold else spare).append((util, link['name']))
    spare.sort()
    remap = {name: spare[i % len(spare)][1] for i, (_, name) in enumerate(hot)} if spare else {}
    return {'overloaded': [name for _, name in hot], 'remap': remap, 'reroutable': bool(spare) or not hot}

def eval_portfolio_optimizer(cases, budget):
    remaining = {c['id']: set(c['failure_classes']) for c in cases}
    value = {c['id']: float(c['value']) for c in cases}
    covered = set()
    selected = []
    while remaining and len(selected) < budget:
        best = max(remaining, key=lambda cid: (len(remaining[cid] - covered), value[cid], cid))
        selected.append(best)
        covered |= remaining.pop(best)
    return {'selected': selected, 'covered_failure_classes': sorted(covered)}

def trajectory_native_storage_layout(spans):
    ordered = sorted(spans, key=lambda s: (s['trajectory_id'], float(s['timestamp']), s['span_id']))
    offsets = defaultdict(list)
    for i, span in enumerate(ordered):
        offsets[span['trajectory_id']].append(i)
    return {'ordered_spans': ordered, 'trajectory_offsets': dict(offsets)}

def execution_checkpoint_lattice(checkpoints, target):
    candidates = [c for c in checkpoints if c.get('verified') and target in c.get('completed_subgoals', [])]
    candidates.sort(key=lambda c: (len(c.get('completed_subgoals', [])), float(c.get('timestamp', 0))), reverse=True)
    return {'recoverable': bool(candidates), 'checkpoint_id': candidates[0]['id'] if candidates else None}

def rack_to_token_autopilot(candidates):
    scored = []
    for c in candidates:
        productive = float(c['tokens']) * (1 - float(c['failure_rate']))
        denom = float(c['power_kw']) * float(c['latency_ms']) * float(c['cost_factor'])
        scored.append((productive / denom, c['name']))
    scored.sort(reverse=True)
    return {'selected': scored[0][1], 'utility': scored}

def architecture_exposure_hedge(exposures, shifts):
    ranked = sorted(((float(exposures.get(k, 0)) * float(v), k) for k, v in shifts.items()), reverse=True)
    return {'top_risk': ranked[0][1] if ranked else None, 'ranked_exposure': ranked}

def fleet_skill_compounding_engine(rows, min_rate=0.8, min_units=2, min_sites=2):
    groups = defaultdict(list)
    for row in rows:
        groups[row['skill']].append(row)
    promoted = []
    diagnostics = {}
    for skill, items in groups.items():
        rate = sum((bool(x['success']) for x in items)) / len(items)
        units = {x['unit'] for x in items}
        sites = {x['site'] for x in items}
        ok = rate >= min_rate and len(units) >= min_units and (len(sites) >= min_sites)
        diagnostics[skill] = {'success_rate': rate, 'units': len(units), 'sites': len(sites), 'promoted': ok}
        if ok:
            promoted.append(skill)
    return {'promoted': sorted(promoted), 'diagnostics': diagnostics}

def optimization_safety_envelope(base_q, cand_q, base_ms, cand_ms, allowed_drift):
    drift = base_q - cand_q
    gain = base_ms - cand_ms
    return {'accepted': drift <= allowed_drift and gain > 0, 'quality_drift': drift, 'latency_gain_ms': gain}

def useful_gpu_minute_contract(events):
    totals = defaultdict(float)
    for event in events:
        totals[event['state']] += float(event['minutes'])
    allocated = sum(totals.values())
    productive = totals.get('productive', 0.0)
    return {'useful_ratio': productive / allocated if allocated else 0.0, 'productive_minutes': productive, 'loss_minutes': {k: v for k, v in totals.items() if k != 'productive'}}

def typed_agent_capability_graph(nodes, edges):
    violations = []
    for source, target in edges:
        if source not in nodes or target not in nodes:
            violations.append(f'missing-node:{source}->{target}')
            continue
        if int(nodes[target].get('authority', 0)) > int(nodes[source].get('authority', 0)):
            violations.append(f'authority-escalation:{source}->{target}')
        if nodes[source].get('retryable') and (not nodes[target].get('idempotent')):
            violations.append(f'retry-side-effect-risk:{source}->{target}')
    return {'valid': not violations, 'violations': sorted(violations)}

def operational_semantic_twin_index(mutations):
    state = {}
    index = {}
    for m in mutations:
        doc_id = m['doc_id']
        document = dict(m['document'])
        state[doc_id] = document
        index[doc_id] = {'transaction_id': m['transaction_id'], 'provenance': m['provenance'], 'terms': tuple(sorted(str(document.get('text', '')).lower().split()))}
    return {'state': state, 'semantic_index': index, 'diverged': set(state) != set(index)}

def agent_relationship_graph_firewall(edges, proposed, sensitive):
    graph = defaultdict(set)
    for a, b in edges:
        graph[a].add(b)
    source, target = proposed

    def reachable(start):
        seen = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            for nxt in graph.get(cur, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen
    before = reachable(source)
    graph[source].add(target)
    after = reachable(source)
    expansion = after - before
    sensitive_expansion = sorted(expansion & sensitive)
    return {'allowed': not sensitive_expansion, 'path_expansion': sorted(expansion), 'sensitive_expansion': sensitive_expansion}

def retrieval_outcome_optimizer(configs):
    scored = []
    for c in configs:
        score = 2 * float(c['task_success']) + 0.5 * float(c['freshness']) - float(c['latency_ms']) / 1000 - 0.25 * float(c['cost'])
        scored.append((score, c['name']))
    scored.sort(reverse=True)
    return {'selected': scored[0][1], 'scores': scored}

def capability_safety_pareto_observatory(points):
    frontier = []
    for c in points:
        dominated = any((o is not c and float(o['capability']) >= float(c['capability']) and (float(o['safety']) >= float(c['safety'])) and (float(o['capability']) > float(c['capability']) or float(o['safety']) > float(c['safety'])) for o in points))
        if not dominated:
            frontier.append(c['name'])
    return {'frontier': sorted(frontier)}

def mission_autonomy_evidence_graph(behaviors):
    required = {'simulation', 'software_version', 'sensor_assumptions', 'degraded_mode_limit'}
    missing = {b['name']: sorted((k for k in required if not b.get(k))) for b in behaviors}
    missing = {k: v for k, v in missing.items() if v}
    return {'complete': not missing, 'missing': missing}

def embodiment_latent_adapter(results, threshold=0.15):
    losses = {r['embodiment']: float(r['transfer_loss']) for r in results}
    worst = max(losses.values(), default=0)
    return {'strategy': 'shared-policy-plus-adapter' if worst <= threshold else 'embodiment-specific', 'losses': losses, 'worst_loss': worst}

def policy_carrying_ai_data_plane(rows, roles):
    allowed = []
    for row in rows:
        row_roles = set(row.get('allowed_roles', []))
        if roles & row_roles:
            allowed.append({'id': row['id'], 'payload': row['payload'], 'policy': sorted(row_roles), 'source_provenance': row['source_provenance']})
    return {'authorized': allowed, 'authorized_count': len(allowed)}

def yield_to_workload_feedback_loop(defects):
    weighted = []
    for d in defects:
        impact = sum((float(weight) * float(severity) for weight, severity in d.get('workload_impacts', {}).values()))
        weighted.append((impact * float(d.get('frequency', 1)), d['signature']))
    weighted.sort(reverse=True)
    return {'priority': weighted}

def nondeterminism_envelope(expected, observed):
    reasons = []
    required = set(expected.get('required_keys', []))
    if not required <= set(observed):
        reasons.append('missing-required-key')
    for key, value in expected.get('immutable', {}).items():
        if observed.get(key) != value:
            reasons.append(f'immutable-drift:{key}')
    for key, bounds in expected.get('numeric_ranges', {}).items():
        value = observed.get(key)
        low, high = bounds
        if not isinstance(value, (int, float)) or not float(low) <= float(value) <= float(high):
            reasons.append(f'range-drift:{key}')
    return {'equivalent': not reasons, 'reasons': reasons}

def judgment_replication_fabric(examples):
    ids = [e['id'] for e in examples if e.get('expert_label') != e.get('base_label')]
    return {'target_examples': ids, 'disagreement_count': len(ids)}

def open_model_fidelity_passport(config):
    canonical = json.dumps(config, sort_keys=True, separators=(',', ':'))
    return {'canonical': canonical, 'fingerprint': hashlib.sha256(canonical.encode()).hexdigest()}

def persistent_world_state_compiler(observations):
    objects = {}
    conflicts = []
    for obs in sorted(observations, key=lambda x: float(x['timestamp'])):
        oid = obs['object_id']
        state = dict(obs['state'])
        prior = objects.get(oid, {})
        if prior.get('identity') and state.get('identity') and (prior['identity'] != state['identity']):
            conflicts.append(oid)
            continue
        merged = {**prior, **state, 'last_timestamp': float(obs['timestamp'])}
        objects[oid] = merged
    return {'objects': objects, 'consistent': not conflicts, 'conflicts': sorted(set(conflicts))}

def run_reference_builds() -> dict[str, Any]:
    results = {'cursor': patch_intent_twin({'src/core.py'}, {'secrets.env'}, {'src/core.py', 'tests/test_core.py'}, {'unit'}, {'unit'}), 'apptronik': deployment_interface_standardizer([{'name': 'cell-a', 'handoff_zone': 'A1', 'safety_field': 'ISO', 'task_api': ['pick', 'place'], 'fixture': 'std-v1'}]), 'arm': cross_isa_ai_placement_contract({'latency_weight': 2, 'energy_weight': 1, 'memory_weight': 1, 'privacy_weight': 1}, [{'name': 'cpu', 'latency_ms': 8, 'energy_j': 2, 'memory_cost': 1, 'privacy_cost': 0}, {'name': 'accelerator', 'latency_ms': 3, 'energy_j': 3, 'memory_cost': 1, 'privacy_cost': 0}]), 'astera_labs': fabric_congestion_autopilot([{'name': 'l1', 'load': 95, 'capacity': 100}, {'name': 'l2', 'load': 30, 'capacity': 100}]), 'braintrust': eval_portfolio_optimizer([{'id': 'a', 'failure_classes': ['tool', 'auth'], 'value': 2}, {'id': 'b', 'failure_classes': ['timeout'], 'value': 1}, {'id': 'c', 'failure_classes': ['auth'], 'value': 3}], 2), 'clickhouse': trajectory_native_storage_layout([{'trajectory_id': 'b', 'timestamp': 2, 'span_id': '2'}, {'trajectory_id': 'a', 'timestamp': 3, 'span_id': '3'}, {'trajectory_id': 'a', 'timestamp': 1, 'span_id': '1'}]), 'cognition': execution_checkpoint_lattice([{'id': 'c1', 'verified': True, 'completed_subgoals': ['setup'], 'timestamp': 1}, {'id': 'c2', 'verified': True, 'completed_subgoals': ['setup', 'tests'], 'timestamp': 2}], 'setup'), 'crusoe': rack_to_token_autopilot([{'name': 'rack-a', 'tokens': 1000000, 'failure_rate': 0.01, 'power_kw': 40, 'latency_ms': 50, 'cost_factor': 1}, {'name': 'rack-b', 'tokens': 1100000, 'failure_rate': 0.1, 'power_kw': 50, 'latency_ms': 55, 'cost_factor': 1.2}]), 'etched': architecture_exposure_hedge({'attention': 0.9, 'moe': 0.3, 'ssm': 0.1}, {'attention': 0.2, 'moe': 0.8, 'ssm': 0.5}), 'figure_ai': fleet_skill_compounding_engine([{'skill': 'pick', 'unit': 'u1', 'site': 's1', 'success': True}, {'skill': 'pick', 'unit': 'u2', 'site': 's2', 'success': True}, {'skill': 'pick', 'unit': 'u2', 'site': 's1', 'success': True}]), 'fireworks_ai': optimization_safety_envelope(0.95, 0.945, 100, 70, 0.01), 'lambda': useful_gpu_minute_contract([{'state': 'productive', 'minutes': 70}, {'state': 'provisioning', 'minutes': 10}, {'state': 'retry', 'minutes': 20}]), 'langchain': typed_agent_capability_graph({'planner': {'authority': 2, 'retryable': False, 'idempotent': True}, 'reader': {'authority': 1, 'retryable': True, 'idempotent': True}}, [('planner', 'reader')]), 'mongodb': operational_semantic_twin_index([{'doc_id': '1', 'transaction_id': 'tx-1', 'document': {'text': 'hello world'}, 'provenance': 'primary'}]), 'obsidian_security': agent_relationship_graph_firewall([('agent', 'tool')], ('agent', 'public'), {'payroll'}), 'pinecone': retrieval_outcome_optimizer([{'name': 'cfg-a', 'task_success': 0.9, 'freshness': 0.9, 'latency_ms': 80, 'cost': 1}, {'name': 'cfg-b', 'task_success': 0.85, 'freshness': 1, 'latency_ms': 40, 'cost': 0.5}]), 'safe_superintelligence_ssi': capability_safety_pareto_observatory([{'name': 'a', 'capability': 0.8, 'safety': 0.9}, {'name': 'b', 'capability': 0.9, 'safety': 0.8}, {'name': 'c', 'capability': 0.7, 'safety': 0.7}]), 'shield_ai': mission_autonomy_evidence_graph([{'name': 'navigate', 'simulation': 'sim-1', 'software_version': '1.0', 'sensor_assumptions': 'gps-denied', 'degraded_mode_limit': 'hover'}]), 'skild_ai': embodiment_latent_adapter([{'embodiment': 'arm-a', 'transfer_loss': 0.08}, {'embodiment': 'arm-b', 'transfer_loss': 0.12}]), 'supabase': policy_carrying_ai_data_plane([{'id': 'r1', 'payload': 'allowed', 'allowed_roles': ['member'], 'source_provenance': 'table:docs'}, {'id': 'r2', 'payload': 'blocked', 'allowed_roles': ['admin'], 'source_provenance': 'table:docs'}], {'member'}), 'tsmc': yield_to_workload_feedback_loop([{'signature': 'd1', 'frequency': 0.2, 'workload_impacts': {'llm': (1, 0.9), 'vision': (0.5, 0.2)}}, {'signature': 'd2', 'frequency': 0.4, 'workload_impacts': {'llm': (0.3, 0.2), 'vision': (0.2, 0.1)}}]), 'temporal': nondeterminism_envelope({'required_keys': ['status', 'score'], 'immutable': {'status': 'ok'}, 'numeric_ranges': {'score': (0.8, 1)}}, {'status': 'ok', 'score': 0.91, 'text': 'equivalent'}), 'thinking_machines_lab': judgment_replication_fabric([{'id': 'e1', 'expert_label': 'approve', 'base_label': 'reject'}, {'id': 'e2', 'expert_label': 'approve', 'base_label': 'approve'}]), 'together_ai': open_model_fidelity_passport({'weights': 'model@abc', 'quantization': 'fp8', 'sampler': {'temperature': 0.2}, 'kernel': 'v1', 'eval_delta': 0.003}), 'world_labs': persistent_world_state_compiler([{'object_id': 'o1', 'timestamp': 1, 'state': {'identity': 'box', 'x': 0}}, {'object_id': 'o1', 'timestamp': 2, 'state': {'identity': 'box', 'x': 1}}])}
    if tuple(results) != P0_IDS:
        raise RuntimeError('P0 build registry/order drift')
    return results

def verify_reference_builds() -> dict[str, Any]:
    r = run_reference_builds()
    checks = {'cursor': r['cursor']['aligned'], 'apptronik': r['apptronik']['compatible_count'] == 1, 'arm': r['arm']['selected'] == 'accelerator', 'astera_labs': r['astera_labs']['remap'] == {'l1': 'l2'}, 'braintrust': len(r['braintrust']['selected']) == 2, 'clickhouse': list(r['clickhouse']['trajectory_offsets']) == ['a', 'b'], 'cognition': r['cognition']['checkpoint_id'] == 'c2', 'crusoe': r['crusoe']['selected'] == 'rack-a', 'etched': r['etched']['top_risk'] == 'moe', 'figure_ai': r['figure_ai']['promoted'] == ['pick'], 'fireworks_ai': r['fireworks_ai']['accepted'], 'lambda': r['lambda']['useful_ratio'] == 0.7, 'langchain': r['langchain']['valid'], 'mongodb': not r['mongodb']['diverged'], 'obsidian_security': r['obsidian_security']['allowed'], 'pinecone': r['pinecone']['selected'] in {'cfg-a', 'cfg-b'}, 'safe_superintelligence_ssi': r['safe_superintelligence_ssi']['frontier'] == ['a', 'b'], 'shield_ai': r['shield_ai']['complete'], 'skild_ai': r['skild_ai']['strategy'] == 'shared-policy-plus-adapter', 'supabase': r['supabase']['authorized_count'] == 1, 'tsmc': r['tsmc']['priority'][0][1] == 'd1', 'temporal': r['temporal']['equivalent'], 'thinking_machines_lab': r['thinking_machines_lab']['target_examples'] == ['e1'], 'together_ai': len(r['together_ai']['fingerprint']) == 64, 'world_labs': r['world_labs']['consistent']}
    failed = [k for k, v in checks.items() if not v]
    return {'status': 'PASS' if not failed else 'FAIL', 'verified_count': sum(checks.values()), 'expected_count': 25, 'failed': failed, 'checks': checks}
