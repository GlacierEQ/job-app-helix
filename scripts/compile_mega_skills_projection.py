#!/usr/bin/env python3
"""Compile the Job Application Mega-Skills projection from a pinned canonical source."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCK_PATH=ROOT/'manifests/mega_skills_source_lock.json'
DEFAULT_OUT=ROOT/'generated/mega-skills-public-projection.json'

def load(path:Path): return json.loads(path.read_text(encoding='utf-8'))
def sha256(path:Path): return hashlib.sha256(path.read_bytes()).hexdigest()
def first(value): return value[0] if isinstance(value,list) and value else value if isinstance(value,str) else ''

def verify_checkout(source:Path,lock:dict):
    graph=source/lock['source_graph']
    if not graph.is_file(): raise ValueError(f'missing canonical graph: {graph}')
    if sha256(graph)!=lock['source_graph_sha256']: raise ValueError('canonical graph SHA-256 does not match pinned source lock')
    if (source/'.git').exists():
        head=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        if head!=lock['source_commit']: raise ValueError(f'source checkout {head} != pinned {lock["source_commit"]}')
    graph_data=load(graph)
    if graph_data.get('counts')!=lock['canonical_counts']: raise ValueError('canonical graph counts drift from source lock')
    if len(graph_data.get('mega_roots',[]))!=29: raise ValueError('canonical graph must expose 29 Mega roots')
    return graph_data

def compile_bundle(source:Path,lock:dict):
    graph=verify_checkout(source,lock)
    skills=load(source/'registry/skills.json')['entries']; combos=load(source/'registry/combo-skills.json')['entries']; megas=load(source/'registry/mega-skills.json')['entries']; external=load(source/'registry/external-skills.json')['entries']
    skb={x['id']:x for x in skills}; exb={x['id']:x for x in external}
    prefixes={'skill':'a','compound-skill':'c','external-skill':'x'}
    mega_rows=[]
    for m in megas:
        mega_rows.append([m['id'],m.get('display_name',m['id']),m.get('maturity'),m.get('version'),m.get('mission_output'),m.get('required_combos',[]),m.get('conditional_combos',[]),first(m.get('firewall',{}).get('required_evidence',[])),m.get('firewall',{}).get('human_control')])
    compound_rows=[]
    for c in combos:
        members=[[prefixes[m.get('kind','skill')]+':'+m['id'],1 if m.get('required') else 0,m.get('role','')] for m in c.get('members',[])]
        compound_rows.append([c['id'],c.get('display_name',c['id']),c.get('maturity'),c.get('compounding',{}).get('compound_artifact'),first(c.get('integration',{}).get('quality_gates',[])),members])
    leaf_rows=[]
    for typed in graph.get('leaf_keys',[]):
        kind,node_id=typed.split(':',1)
        if kind=='a':
            x=skb[node_id]; leaf_rows.append([typed,x.get('display_name',node_id),x.get('maturity'),first(x.get('output_contract')),first(x.get('local_validation'))])
        elif kind=='x':
            x=exb[node_id]; leaf_rows.append([typed,x.get('display_name',node_id),'external','External capability output',x.get('installed_version_id')])
        else: raise ValueError(f'non-leaf typed key in leaf_keys: {typed}')
    bundle={
      'schema':lock['public_schema'],
      'source':{'repository':lock['source_repository'],'commit':lock['source_commit'],'graph_blob':lock['source_graph_blob_sha'],'graph_sha256':lock['source_graph_sha256']},
      'counts':graph['counts'],
      'claim_boundary':'This projection describes repository-declared Skill composition and validation contracts. It does not by itself claim runtime execution, production adoption, deployment success, or external endorsement.',
      'tuple_contract':{'megas':'[id,name,maturity,version,mission_output,required_compound_ids,conditional_compound_ids,validation_evidence,human_control]','compounds':'[id,name,maturity,artifact,validation,members] member=[typed_key,required,role]','leaves':'[typed_key,name,maturity,artifact,validation]'},
      'megas':mega_rows,'compounds':compound_rows,'leaves':leaf_rows,'shared':graph.get('shared_lineage',{})}
    if len(bundle['megas'])!=29 or len({x[0] for x in bundle['megas']})!=29: raise ValueError('public bundle Mega roots must be 29 unique IDs')
    return bundle

def encoded(bundle): return (json.dumps(bundle,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mega-skills-root',type=Path); ap.add_argument('--out',type=Path,default=DEFAULT_OUT); ap.add_argument('--check',action='store_true'); ap.add_argument('--verify-bundle',type=Path); args=ap.parse_args()
    lock=load(LOCK_PATH)
    if args.verify_bundle:
        if not args.verify_bundle.is_file(): print('missing generated public bundle',file=sys.stderr); return 1
        data=args.verify_bundle.read_bytes(); digest=hashlib.sha256(data).hexdigest(); bundle=json.loads(data)
        tests=[bundle.get('schema')==lock['public_schema'],bundle.get('source',{}).get('commit')==lock['source_commit'],bundle.get('source',{}).get('graph_sha256')==lock['source_graph_sha256'],bundle.get('counts')==lock['canonical_counts'],len(bundle.get('megas',[]))==29,len({x[0] for x in bundle.get('megas',[])})==29,digest==lock['expected_generated_bundle_sha256']]
        if not all(tests): print(json.dumps({'ok':False,'sha256':digest,'tests':tests},indent=2),file=sys.stderr); return 1
        print(json.dumps({'ok':True,'mode':'verify-bundle','sha256':digest,'source_commit':lock['source_commit'],'mega_routes':29},indent=2)); return 0
    if not args.mega_skills_root: print('--mega-skills-root is required when compiling',file=sys.stderr); return 2
    try: bundle=compile_bundle(args.mega_skills_root.resolve(),lock)
    except (OSError,ValueError,subprocess.CalledProcessError) as e: print(f'ERROR: {e}',file=sys.stderr); return 1
    payload=encoded(bundle); digest=hashlib.sha256(payload).hexdigest()
    if digest!=lock['expected_generated_bundle_sha256']: print(f'ERROR: generated bundle {digest} != locked {lock["expected_generated_bundle_sha256"]}',file=sys.stderr); return 1
    if args.check:
        if not args.out.is_file() or args.out.read_bytes()!=payload: print('ERROR: generated public projection drift',file=sys.stderr); return 1
    else:
        args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_bytes(payload)
    print(json.dumps({'ok':True,'mode':'check' if args.check else 'write','source_commit':lock['source_commit'],'bundle_sha256':digest,'mega_routes':29},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
