"""Fail-closed contracts for the 48-track Bottleneck Atlas."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
EXPECTED_TRACK_IDS=('openai','anthropic','google_deepmind','xai','microsoft','aws','spacex','nvidia','apple','meta','tesla','notion','deepseek','kimi','qwen','opera','tasklet','robotics','perplexity','manus','lovable','openclaw','palantir','anduril','scale_ai','mistral','cohere','databricks','snowflake','ibm','intel','amd','qualcomm','oracle','salesforce','adobe','cloudflare','vercel','hugging_face','groq','cerebras','coreweave','waymo','zoox','blue_origin','rocket_lab','nasa','glaciereq_core')
LENSES=(('S1','official_source','observed_current_pressure'),('S2','systems_bottleneck','inferred_bottleneck'),('S3','brick_wall','inferred_brick_wall'),('S4','repository_evidence','leverage'),('S5','leverage_architecture','leverage'),('S6','impact','leverage'),('S7','application_strategy','application_move'),('S8','truth_presentation','inference_boundary'))
class IntelligenceValidationError(ValueError): pass
def canonical_json(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)
def sha256(v:Any)->str:return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def load_json(path:str|Path)->dict[str,Any]:
 with Path(path).open(encoding='utf-8') as f:v=json.load(f)
 if not isinstance(v,dict):raise IntelligenceValidationError(f'{path}: expected object')
 return v

def load_expanded_atlas(root:str|Path,manifest_path:str='manifests/application_intelligence/company_bottleneck_atlas.json')->dict[str,Any]:
 root=Path(root); manifest=load_json(root/manifest_path)
 expected=sha256({k:v for k,v in manifest.items() if k!='manifest_sha256'})
 if manifest.get('manifest_sha256')!=expected:raise IntelligenceValidationError('atlas manifest hash')
 defaults=manifest['defaults']; records=[]
 for shard_ref in manifest['shards']:
  shard=load_json(root/shard_ref['path'])
  shard_expected=sha256({k:v for k,v in shard.items() if k!='shard_sha256'})
  if shard.get('shard_sha256')!=shard_expected or shard_expected!=shard_ref['shard_sha256']:raise IntelligenceValidationError(f"{shard_ref['category_id']}: shard hash")
  for raw in shard['records']:
   rec=dict(raw); rec['as_of']=defaults['as_of']; rec['research_state']=defaults['research_state']; rec['inference_boundary']=defaults['inference_boundary']; rec['confidence']=defaults['confidence']; rec['non_affiliation']=defaults['non_affiliation']
   rec['official_sources']=[dict(defaults['source_defaults'],**s) for s in raw['official_sources']]
   records.append(rec)
 atlas={'schema':manifest['schema'],'version':manifest['version'],'generated_at':manifest['generated_at'],'authority':manifest['authority'],'branch':manifest['branch'],'research_scope':manifest['research_scope'],'category_order':manifest['category_order'],'records':records}
 atlas['atlas_sha256']=sha256(atlas)
 if atlas['atlas_sha256']!=manifest['expanded_atlas_sha256']:raise IntelligenceValidationError('expanded atlas hash')
 return atlas

def validate_atlas(atlas:dict[str,Any])->dict[str,Any]:
 records=atlas.get('records'); ids=tuple(r.get('company_id') for r in records or [])
 if ids!=EXPECTED_TRACK_IDS:raise IntelligenceValidationError(f'exact 48-track order mismatch ({len(ids)})')
 source_count=0
 for r in records:
  for s in r['official_sources']:
   if s.get('source_sha256')!=sha256({k:v for k,v in s.items() if k!='source_sha256'}):raise IntelligenceValidationError(f"{r['company_id']}: source hash")
   if s.get('official') is not True:raise IntelligenceValidationError(f"{r['company_id']}: unofficial source")
   source_count+=1
  if r.get('record_sha256')!=sha256({k:v for k,v in r.items() if k!='record_sha256'}):raise IntelligenceValidationError(f"{r['company_id']}: record hash")
  if 'not a statement confirmed' not in r['inference_boundary'] or 'No affiliation' not in r['non_affiliation']:raise IntelligenceValidationError(f"{r['company_id']}: truth boundary")
 return {'status':'PASS','track_count':48,'source_count':source_count,'silent_omissions':0,'atlas_sha256':atlas['atlas_sha256']}

def build_packets(atlas:dict[str,Any])->tuple[list[dict[str,Any]],dict[str,Any]]:
 packets=[];before=after=0
 for r in atlas['records']:
  p={'schema':'glaciereq.unified-memory.company-intelligence-packet.v1','memory_key':f"helix/company/{r['company_id']}/bottleneck-v1",'company_id':r['company_id'],'display_name':r['display_name'],'category_id':r['category_id'],'as_of':r['as_of'],'state':r['research_state'],'decision':{'pressure':r['observed_current_pressure'],'bottleneck':r['inferred_bottleneck'],'brick_wall':r['inferred_brick_wall'],'leverage':r['leverage']['mechanism'],'impact':r['leverage']['expected_impact'],'application_move':r['application_move'],'next_gate':r['next_deep_dive']},'source_hashes':[s['source_sha256'] for s in r['official_sources']],'record_sha256':r['record_sha256'],'truth':'OBSERVED_SOURCE_PLUS_GLACIEREQ_INFERENCE'}
  p['packet_sha256']=sha256({k:v for k,v in p.items() if k!='packet_sha256'});packets.append(p);before+=len(canonical_json(r).encode());after+=len(canonical_json(p).encode())
 return packets,{'before':before,'after':after,'saved':before-after,'reduction_ratio':round((before-after)/before,6)}

def build_expanded_run(atlas:dict[str,Any],topology:dict[str,Any],compact:dict[str,Any])->dict[str,Any]:
 run={'schema':compact['schema'],'run_id':compact['run_id'],'generated_at':compact['generated_at'],'execution_mode':compact['execution_mode'],'truth_boundary':compact['truth_boundary'],'topology_sha256':topology['topology_sha256'],'atlas_sha256':atlas['atlas_sha256'],'wave_count':6,'tracks_per_wave':8,'track_count':48,'specialist_task_count':384,'integration_count':48,'silent_omissions':0,'status':'FIRST_PASS_COMPLETE','waves':[]}
 for wi in range(6):
  ints=[]
  for r in atlas['records'][wi*8:(wi+1)*8]:
   receipts=[]
   for sid,lens,field in LENSES:
    val=r[field]
    if sid=='S4':val={'systems':val['glaciereq_systems']}
    elif sid=='S5':val={'mechanism':val['mechanism']}
    elif sid=='S6':val={'expected_impact':val['expected_impact'],'impact_class':val['impact_class']}
    receipts.append({'specialist_id':sid,'lens':lens,'input_record_sha256':r['record_sha256'],'output_sha256':sha256({'company_id':r['company_id'],'lens':lens,'payload':val})})
   integ={'company_id':r['company_id'],'display_name':r['display_name'],'lens_count':8,'lens_receipts':receipts,'integrated_record_sha256':r['record_sha256'],'integration_status':'COMPLETE'};integ['integration_sha256']=sha256({k:v for k,v in integ.items() if k!='integration_sha256'});ints.append(integ)
  wave={'wave':wi+1,'track_count':8,'tracks':[x['company_id'] for x in ints],'integrations':ints,'status':'COMPLETE'};wave['wave_sha256']=sha256({k:v for k,v in wave.items() if k!='wave_sha256'});run['waves'].append(wave)
 run['run_sha256']=sha256({k:v for k,v in run.items() if k!='run_sha256'})
 return run

def validate_index(root:str|Path)->dict[str,Any]:
 root=Path(root);index=load_json(root/'manifests/company_intelligence.json');atlas=load_expanded_atlas(root,index['files']['atlas']);top=load_json(root/index['files']['diamond_topology']);compact=load_json(root/index['files']['gatling_receipt']);measurement=load_json(root/index['files']['token_saver_measurement'])
 if top.get('topology_sha256')!=sha256({k:v for k,v in top.items() if k!='topology_sha256'}):raise IntelligenceValidationError('topology hash')
 a=validate_atlas(atlas);packets,m=build_packets(atlas);run=build_expanded_run(atlas,top,compact)
 if run['run_sha256']!=compact['expanded_run_sha256']:raise IntelligenceValidationError('expanded run hash')
 if tuple(i for w in run['waves'] for i in w['tracks'])!=EXPECTED_TRACK_IDS:raise IntelligenceValidationError('gatling order')
 if m['before']!=measurement['canonical_bytes_before'] or m['after']!=measurement['canonical_bytes_after']:raise IntelligenceValidationError('token measurement')
 if index.get('index_sha256')!=sha256({k:v for k,v in index.items() if k!='index_sha256'}):raise IntelligenceValidationError('index hash')
 return {'status':'PASS','atlas':a,'memory':{'status':'PASS','packet_count':len(packets)},'gatling':{'status':'PASS','waves':6,'tracks':48,'specialist_tasks':384,'run_sha256':run['run_sha256']},'measurement':{'status':'PASS',**m},'silent_omissions':0,'index_sha256':index['index_sha256']}
