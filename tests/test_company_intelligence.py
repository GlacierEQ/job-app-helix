from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from job_app_helix.company_intelligence import EXPECTED_TRACK_IDS,build_packets,load_expanded_atlas,validate_atlas,validate_index
def test_exact_boundary():
 a=load_expanded_atlas(ROOT);assert tuple(r["company_id"] for r in a["records"])==EXPECTED_TRACK_IDS;assert validate_atlas(a)["silent_omissions"]==0
def test_memory_packets():
 a=load_expanded_atlas(ROOT);p,m=build_packets(a);assert len(p)==48 and len({x["memory_key"] for x in p})==48 and m["after"]<m["before"]
def test_gatling_and_index():
 r=validate_index(ROOT);assert r["status"]=="PASS" and r["gatling"]["specialist_tasks"]==384 and r["silent_omissions"]==0
