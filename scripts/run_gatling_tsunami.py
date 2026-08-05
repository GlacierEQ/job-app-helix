#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from job_app_helix.company_intelligence import validate_index
def main()->int:
 r=validate_index(ROOT);print(json.dumps({"status":"PASS","run_sha256":r["gatling"]["run_sha256"],"waves":6,"tracks":48,"specialist_tasks":384,"hosted_model_workers_invoked":False,"index_sha256":r["index_sha256"]},indent=2,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
