#!/usr/bin/env python3
"""Compile Mega-Skills public manifest and 29 inspectable static pyramid routes from pinned source."""
from __future__ import annotations
import argparse, hashlib, html, json, subprocess, sys
from pathlib import Path

SOURCE_COMMIT='4166e09b86c257ba02e32fc20a65b0f63b8e46f7'
GRAPH_SHA256='0dcb93440657c27233121ca78a916463a8f4f9796f87c4a9ff1cb388d6966e84'
PUBLIC_SCHEMA='glaciereq.public-mega-skills.v2'
BASE='https://casey-barton-glaciereq.vercel.app'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def esc(x): return html.escape('' if x is None else str(x), quote=True)
def first(v, default='source-bound validation contract'):
    if isinstance(v,list) and v: return v[0]
    if isinstance(v,str) and v: return v
    return default

def verify_source(root:Path):
    gp=root/'registry/mega-skill-pyramids.json'
    if digest(gp)!=GRAPH_SHA256: raise ValueError('graph sha256 does not match pinned source')
    if (root/'.git').exists():
        head=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        if head!=SOURCE_COMMIT: raise ValueError(f'source HEAD {head} != pinned {SOURCE_COMMIT}')
    g=load(gp)
    if g['counts']['mega_pyramids']!=29 or g['counts']['unresolved_owned_references']!=0 or g['counts']['compound_cycles']!=0: raise ValueError('canonical graph validity/count invariant failed')
    return g

def label_from_key(k): return k.split(':',1)[1].replace('-',' ').title()

def build_model(source:Path):
    graph=verify_source(source)
    skills=load(source/'registry/skills.json')['entries']; combos=load(source/'registry/combo-skills.json')['entries']; megas=load(source/'registry/mega-skills.json')['entries']; external=load(source/'registry/external-skills.json')['entries']
    S={x['id']:x for x in skills}; C={x['id']:x for x in combos}; M={x['id']:x for x in megas}; X={x['id']:x for x in external}
    roots={row[1]:row for row in graph['mega_roots']}; cnodes={row[1]:row for row in graph['compound_nodes']}
    if set(roots)!=set(M): raise ValueError('Mega root registry mismatch')
    return graph,S,C,M,X,roots,cnodes

def child_model(typed, required, parent_combo, member_index, S,C,X):
    prefix,node_id=typed.split(':',1); member=C[parent_combo]['members'][member_index]; role=member.get('role','Source-bound child role')
    if prefix=='a':
        x=S[node_id]; return {'type':'atomic','key':typed,'id':node_id,'name':x.get('display_name',label_from_key(typed)),'maturity':x.get('maturity'),'required':bool(required),'role':role,'artifact':first(x.get('output_contract'),'Atomic output contract'),'validation':first(x.get('local_validation'))}
    if prefix=='x':
        x=X[node_id]; return {'type':'external','key':typed,'id':node_id,'name':x.get('display_name',label_from_key(typed)),'maturity':'external','required':bool(required),'role':role,'artifact':'External capability output','validation':'Pinned external version '+str(x.get('installed_version_id','unspecified'))}
    return {'type':'compound','key':typed,'id':node_id,'name':C[node_id].get('display_name',label_from_key(typed)),'maturity':C[node_id].get('maturity'),'required':bool(required),'role':role}

def expand_compound(cid,S,C,X,cnodes,stack=()):
    if cid in stack: raise ValueError('cycle during public expansion: '+' -> '.join(stack+(cid,)))
    row=cnodes[cid]; c=C[cid]; children=[]
    for idx,(typed,required) in enumerate(row[2]):
        ch=child_model(typed,required,cid,idx,S,C,X)
        if ch['type']=='compound': ch['branch']=expand_compound(ch['id'],S,C,X,cnodes,stack+(cid,))
        children.append(ch)
    return {'type':'compound','id':cid,'name':c.get('display_name',cid),'maturity':c.get('maturity'),'artifact':c.get('compounding',{}).get('compound_artifact'),'validation':first(c.get('integration',{}).get('quality_gates')),'ready_when':first(c.get('compounding',{}).get('next_layer_ready_when')),'children':children}

def root_manifest(graph,M):
    rows=[]
    for rid in sorted(M):
        m=M[rid]; rows.append({'id':rid,'name':m.get('display_name',rid),'maturity':m.get('maturity'),'mission_output':m.get('mission_output'),'route':f'/mega-skills/{rid}/','required_compounds':len(m.get('required_combos',[])),'conditional_compounds':len(m.get('conditional_combos',[]))})
    return {'schema':PUBLIC_SCHEMA,'source':{'repository':'GlacierEQ/mega-skills','commit':SOURCE_COMMIT,'graph_sha256':GRAPH_SHA256},'counts':graph['counts'],'claim_boundary':'Repository-declared Skill composition and validation contracts; not runtime execution, production adoption, deployment success, or external endorsement.','mega_skills':rows}

def render_child(ch,depth=0):
    req='required' if ch.get('required') else 'optional'
    if ch['type']=='compound':
        branch=ch['branch']; inner=''.join(render_child(x,depth+1) for x in branch['children'])
        return f'<details class="skill-branch" open><summary><span class="kind kind-compound">Compound</span> <b>{esc(branch["name"])}</b> <span class="state">{esc(branch["maturity"])}</span></summary><div class="branch-body"><p>{req} · artifact <code>{esc(branch.get("artifact"))}</code> · validation <code>integration.quality_gates</code></p>{inner}</div></details>'
    kind='External' if ch['type']=='external' else 'Atomic'; css='kind-external' if ch['type']=='external' else 'kind-atomic'
    return f'<div class="skill-leaf"><span class="kind {css}">{kind}</span> <b>{esc(ch["name"])}</b> <span class="state">{esc(ch["maturity"])}</span><br><code>{esc(ch["key"])}</code><br><span>{req} · artifact <code>{esc(ch.get("artifact"))}</code> · validation <code>{"installed_version_id" if ch["type"]=="external" else "local_validation"}</code></span></div>'

def render_root_branch(branch,relation):
    inner=''.join(render_child(x,1) for x in branch['children'])
    return f'<details class="root-branch" open><summary><span class="kind kind-compound">{relation} Compound</span> <b>{esc(branch["name"])}</b> <span class="state">{esc(branch["maturity"])}</span></summary><div class="branch-body"><p>artifact <code>{esc(branch.get("artifact"))}</code> · validation <code>integration.quality_gates</code></p>{inner}</div></details>'

def render_page(m,required,conditional):
    rid=m['id']; name=m.get('display_name',rid); maturity=m.get('maturity'); output=m.get('mission_output'); human=m.get('firewall',{}).get('human_control'); canonical=f'{BASE}/mega-skills/{rid}/'; req=''.join(render_root_branch(b,'Required') for b in required); cond=''.join(render_root_branch(b,'Conditional') for b in conditional)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="description" content="Inspectable Skill pyramid for {esc(name)}."><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><title>{esc(name)} · Mega-Skill Pyramid</title><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css"><link rel="stylesheet" href="/assets/site.systems.css"><link rel="stylesheet" href="/assets/site.complete.css"><link rel="stylesheet" href="/assets/mega-skills.css"></head><body><a class="skip" href="#main">Skip to content</a><div class="signal-bar"><div class="shell signal-inner"><span class="signal-live">MEGA-SKILL · {esc(maturity).upper()}</span><span>pinned source {SOURCE_COMMIT[:12]}</span></div></div><header class="site-header"><div class="shell nav"><a class="brand" href="/"><span class="mark">CB</span><span><strong>CASEY BARTON</strong><small>FORWARD-DEPLOYED AI ARCHITECT</small></span></a><nav class="links"><a href="/mega-skills/">Mega-Skills</a><a href="/hire/">Hire</a><a href="/resume/">Résumé</a><a href="/master/">Technical</a></nav></div></header><main id="main"><section class="mega-detail-hero"><div class="shell"><p class="eyebrow">MEGA APEX · COMPLETE WORKFLOW / PIPELINE</p><h1>{esc(name)}</h1><p class="lede">A real Skill pyramid: Compound workflow Skills recursively resolve to proper Atomic or external Skill leaves.</p><p><b>Maturity:</b> {esc(maturity)} · <b>Mission artifact:</b> <code>{esc(output)}</code> · <b>Human control:</b> {esc(human)}</p><p><b>Exact Skill ID:</b> <code>{esc(rid)}</code></p></div></section><section class="mega-pyramid"><div class="shell"><section class="apex-card"><span class="kind kind-mega">Mega Skill</span><h2>{esc(name)}</h2><p>artifact <code>{esc(output)}</code> · validation <code>firewall.required_evidence</code></p></section><h2>Required branches</h2>{req}<h2>Conditional branches</h2>{cond}</div></section><section class="claim-boundary"><div class="shell"><h2>Claim boundary</h2><p>Repository-declared composition, artifacts, maturity labels, and validation contracts at <code>GlacierEQ/mega-skills@{SOURCE_COMMIT[:12]}</code>. This page does not by itself claim runtime execution, production adoption, deployment success, or external endorsement.</p><p><a href="/mega-skills/">← All Mega-Skills</a> · <a href="/data/mega-skills.json">Machine manifest</a></p></div></section></main></body></html>'''

def css_text():
    return '.mega-detail-hero{padding:72px 0 48px}.mega-detail-hero h1{max-width:1050px}.mega-pyramid{padding:56px 0}.apex-card,.root-branch,.skill-branch,.skill-leaf,.claim-boundary{border:1px solid var(--line,#22313b);border-radius:16px;background:rgba(255,255,255,.025)}.apex-card,.root-branch{padding:22px;margin:16px 0}.skill-branch{margin:12px 0}.skill-branch summary,.root-branch summary{cursor:pointer;padding:15px 17px}.branch-body{padding:0 17px 17px;border-top:1px solid var(--line,#22313b)}.skill-leaf{padding:14px 16px;margin:10px 0 10px 18px}.kind{display:inline-block;font:700 11px/1 ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;border:1px solid currentColor;border-radius:999px;padding:6px 8px;margin-right:8px}.kind-mega{color:#7af0b4}.kind-compound{color:#9da8ff}.kind-atomic{color:#6ee7ff}.kind-external{color:#ffd166}.state{font:700 11px ui-monospace,monospace;color:var(--muted,#98adbc);text-transform:uppercase}.claim-boundary{margin:20px auto 64px;padding:32px;max-width:1100px}@media(max-width:700px){.skill-leaf{margin-left:0}.mega-detail-hero{padding-top:48px}}\n'

def compile_all(source:Path,out_root:Path):
    graph,S,C,M,X,roots,cnodes=build_model(source); site=out_root/'site-v15'; (site/'data').mkdir(parents=True,exist_ok=True); (site/'assets').mkdir(parents=True,exist_ok=True)
    manifest=root_manifest(graph,M); manifest_bytes=(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n').encode(); (site/'data/mega-skills.json').write_bytes(manifest_bytes); (site/'assets/mega-skills.css').write_text(css_text(),encoding='utf-8'); routes=[]
    for rid in sorted(M):
        m=M[rid]; required=[expand_compound(cid,S,C,X,cnodes) for cid in m.get('required_combos',[])]; conditional=[expand_compound(cid,S,C,X,cnodes) for cid in m.get('conditional_combos',[])]; p=site/'mega-skills'/rid/'index.html'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(render_page(m,required,conditional),encoding='utf-8'); routes.append('/mega-skills/'+rid+'/')
    h=hashlib.sha256()
    for rel in ['data/mega-skills.json','assets/mega-skills.css']+[f'mega-skills/{rid}/index.html' for rid in sorted(M)]: h.update(rel.encode()+b'\0'+(site/rel).read_bytes()+b'\0')
    return {'schema':'job-app-helix.mega-skills-projection-receipt.v2','source_commit':SOURCE_COMMIT,'source_graph_sha256':GRAPH_SHA256,'public_schema':PUBLIC_SCHEMA,'route_count':29,'routes':routes,'root_manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'aggregate_projection_sha256':h.hexdigest()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mega-skills-root',type=Path,required=True); ap.add_argument('--job-application-root',type=Path,required=True); ap.add_argument('--receipt',type=Path); args=ap.parse_args()
    try: r=compile_all(args.mega_skills_root,args.job_application_root)
    except Exception as e: print(f'ERROR: {e}',file=sys.stderr); return 1
    if args.receipt: args.receipt.parent.mkdir(parents=True,exist_ok=True); args.receipt.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
