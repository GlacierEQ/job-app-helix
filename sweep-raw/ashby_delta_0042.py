import json, urllib.request, urllib.error, re, os

BASE = "https://api.ashbyhq.com/posting-api/job-board/{}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
LIVE = ["runpod","crusoe","browserbase","firecrawl","steel","openrouter"]
SNAP = "ashby_snap_0042.json"
FIT = re.compile(r"agent|forward.?deployed|applied ai|\bai engineer\b|\bml engineer\b|ai platform|deployed architect|solutions engineer|solutions architect|\bfde\b|agentic|customer ai|customer engineer|forward deployed|member of technical|ai solutions|sales engineer|technical account", re.I)
prior = {}
if os.path.exists(SNAP):
    prior = json.load(open(SNAP))
snap = {}
for org in LIVE:
    try:
        req = urllib.request.Request(BASE.format(org), headers=UA)
        r = urllib.request.urlopen(req, timeout=30)
        d = json.load(r)
        jobs = d.get("jobs", [])
        snap[org] = {j.get("id"): j.get("title") for j in jobs}
        old = prior.get(org, {})
        new_ids = [i for i in snap[org] if i not in old]
        print(f"{org}: {len(jobs)} jobs ({len(new_ids)} new)")
        for j in jobs:
            loc = j.get("locationName","?") or "?"
            remote = bool(j.get("isRemote")) or re.search(r"remote", loc, re.I)
            if FIT.search(j.get("title","")) and (remote or j.get("id") in new_ids):
                tag = "NEW" if j.get("id") in new_ids else "   "
                print(f"  [{tag}] {org} | id={j.get('id')} | {j.get('title')} | {loc} | remote={j.get('isRemote')}")
    except urllib.error.HTTPError as e:
        print(f"{org}: HTTP {e.code}")
    except Exception as e:
        print(f"{org}: ERR {type(e).__name__}")
with open(SNAP,"w") as f: json.dump(snap, f)
