#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from job_app_helix.company_intelligence import IntelligenceValidationError, validate_index

def main()->int:
    parser=argparse.ArgumentParser(description='Validate the 48-track company intelligence plane.')
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try: result=validate_index(args.root)
    except (OSError,ValueError,json.JSONDecodeError,IntelligenceValidationError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},indent=2)); return 1
    text=json.dumps(result,indent=2,sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text+'\n',encoding='utf-8')
    print(text); return 0
if __name__=='__main__': raise SystemExit(main())
