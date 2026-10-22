import json, urllib.request, urllib.error, re

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
ASHBY_ORGS = ["perplexity","harvey","cursor","windsurf","cognition","vapi","cartesia",
 "decagon","sierra","delphi","characterai","ideogram","runway","luma","suno","udio",
 "krea","adept","raycast","superhuman","shortwave","granola","clay","vanta","drata"]
GH_BOARDS = ["doordash","faire","rippling","grafana","honeycomb","pagerduty","checkr",
 "lattice","verkada","samsara","flexport","okta","crowdstrike","zscaler","servicenow","workable"]
FIT = re.compile(r"agent|forward.?deployed|applied ai|\bai engineer\b|\bml engineer\b|ai platform|deployed architect|solutions engineer|solutions architect|\bfde\b|agentic|customer ai|customer engineer|forward deployed|member of technical|ai solutions|sales engineer|technical account", re.I)

print("--- ASHBY new batch ---")
for org in ASHBY_ORGS:
    try:
        req = urllib.request.Request(f"https://api.ashbyhq.com/posting-api/job-board/{org}", headers=UA)
        r = urllib.request.urlopen(req, timeout=20)
        jobs = json.load(r).get("jobs", [])
        hits = 0
        for j in jobs:
            loc = j.get("locationName","?") or "?"
            remote = bool(j.get("isRemote")) or re.search(r"remote", loc, re.I)
            if FIT.search(j.get("title","")):
                hits += 1
                tag = "FIT-remote" if remote else "FIT-onsite"
                print(f"[{tag}] {org} | id={j.get('id')} | {j.get('title')} | {loc}")
        print(f"{org}: {len(jobs)} jobs, {hits} FIT")
    except urllib.error.HTTPError as e:
        print(f"{org}: HTTP {e.code}")
    except Exception as e:
        print(f"{org}: ERR {type(e).__name__}")

print("\n--- GREENHOUSE new batch ---")
for b in GH_BOARDS:
    try:
        r = urllib.request.urlopen(f"https://boards-api.greenhouse.io/v1/boards/{b}/jobs", timeout=20)
        jobs = json.load(r)["jobs"]
        hits = 0
        for j in jobs:
            loc = j.get("location",{}).get("name","?")
            remote = re.search(r"remote", loc, re.I)
            if FIT.search(j["title"]):
                hits += 1
                tag = "FIT-remote" if remote else "FIT-onsite"
                print(f"[{tag}] {b} | id={j['id']} | {j['title']} | {loc}")
        print(f"{b}: {len(jobs)} jobs, {hits} FIT")
    except urllib.error.HTTPError as e:
        print(f"{b}: HTTP {e.code}")
    except Exception as e:
        print(f"{b}: ERR {type(e).__name__}")
