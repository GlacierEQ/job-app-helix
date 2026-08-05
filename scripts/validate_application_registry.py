#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def fail(m): raise SystemExit(f"APPLICATION REGISTRY: FAIL: {m}")
idx=load(ROOT/"manifests/company_dossiers.json")
flag=load(ROOT/"manifests/flagship_registry.json")
inv=load(ROOT/"manifests/portfolio_repositories.json")
companies=[]
for rel in idx["dossier_files"]:
    shard=load(ROOT/rel)
    companies.extend(shard["companies"])
ids=[c["company_id"] for c in companies]
if len(ids)!=len(set(ids)): fail("duplicate company_id")
if set(ids)!=set(idx["required_company_tracks"]): fail("company-track coverage mismatch")
levels=set(idx["level_definitions"])
mapped={}
cols=idx["repository_record_columns"]
for c in companies:
    seen=set()
    for row in c["repositories"]:
        if len(row)!=len(cols): fail(f"bad row width in {c['company_id']}")
        r=dict(zip(cols,row))
        if r["repository"] in seen: fail(f"duplicate repo in {c['company_id']}")
        seen.add(r["repository"])
        if not r["repository"].startswith("GlacierEQ/"): fail(f"foreign owner {r['repository']}")
        if r["skill_innovation_level"] not in levels: fail(f"bad level {r['repository']}")
        n=r["repository"].split("/",1)[1]
        if n in inv["workspace_repositories"]:
            mapped.setdefault(n,[]).append(c["company_id"])
expected=set(inv["workspace_repositories"])
if set(mapped)!=expected: fail(f"Helix mismatch missing={sorted(expected-set(mapped))}")
if any(len(v)!=1 for v in mapped.values()): fail("Helix child mapped more than once")
fids=[f["system_id"] for f in flag["flagships"]]
if set(fids)!=set(flag["required_named_flagships"]): fail("flagship coverage mismatch")
if len(fids)!=len(set(fids)): fail("duplicate flagship")
if "job_app_helix" not in fids: fail("Helix root missing")
for f in flag["flagships"]:
    if f["level"] not in levels: fail(f"bad flagship level {f['system_id']}")
print(json.dumps({"status":"PASS","helix_children_mapped":len(expected),"helix_children_exactly_once":True,"company_tracks":len(ids),"named_flagships":len(fids),"zero_direct_omission_gate":True},sort_keys=True))
