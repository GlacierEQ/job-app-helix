import json, urllib.request, datetime
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
CUTOFF = datetime.datetime(2026,10,21,12,42,0, tzinfo=datetime.timezone.utc)  # 02:42 HST
def parse_dt(s):
    try: return datetime.datetime.fromisoformat(s)
    except: return None

# GH board counts at 02:42 HST (2026-10-21 run snapshot)
GH_EXPECTED = {
 "databricks":899,"reddit":154,"vercel":94,"afresh":12,"cribl":74,"figma":141,
 "stripe":730,"airtable":4,"asana":105,"dropbox":21,"duolingo":62,"instacart":125,
 "robinhood":156,"affirm":219,"boxinc":119,"fieldwire":27,"gitlab":232,
 "intercom":107,"xai":302,"togetherai":79,"coreweave":322,"assemblyai":15,
 "labelbox":7,"tavily":13,"lightmatter":63,"nebius":378,"lightningai":51,
 "magic":0,"warp":4,"openspace":6,"comet":3,"anthropic":675,"datadog":436,
 "elastic":369,"scaleai":176,"mongodb":398,"coinbase":229,
}

print("=== GREENHOUSE board delta (02:42 -> 03:42 HST) ===")
changed_boards = []
for board, prev in sorted(GH_EXPECTED.items()):
    try:
        req = urllib.request.Request(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?per_page=500",
            headers=UA)
        jobs = json.load(urllib.request.urlopen(req, timeout=25)).get("jobs", [])
        n = len(jobs)
        if n != prev:
            changed_boards.append((board, jobs))
            print(f"{board}: {n}  *** CHANGED {prev}->{n}")
        else:
            print(f"{board}: {n}")
    except Exception as e:
        print(f"{board}: FETCH FAIL {e}")

print("\n=== GH new postings since 02:42 HST (first_published > cutoff) ===")
for board, jobs in changed_boards:
    fresh = [j for j in jobs if (parse_dt(j.get("first_published") or "") or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)) > CUTOFF]
    print(f"{board}: {len(jobs)} total, {len(fresh)} new since cutoff")
    for j in fresh:
        loc = j.get("location",{}).get("name")
        print(f"  NEW: {j.get('title')} | {loc} | first_pub={j.get('first_published')} | {j.get('absolute_url')}")

print("\n=== ASHBY board resweep (vs ashby_snap_0242.json) ===")
ASHBY_BOARDS = ["runpod","crusoe","browserbase","firecrawl","steel","openrouter"]
try:
    snap = json.load(open("/home/hatch/workspace/job-app-helix/sweep-raw/ashby_snap_0242.json"))
except Exception as e:
    snap = {}; print("snapshot load fail:", e)
new_snap = {}
for org in ASHBY_BOARDS:
    try:
        req = urllib.request.Request(f"https://api.ashbyhq.com/posting-api/job-board/{org}", headers=UA)
        jobs = json.load(urllib.request.urlopen(req, timeout=30)).get("jobs", [])
        ids = sorted(j["id"] for j in jobs)
        new_snap[org] = ids
        old = snap.get(org, [])
        added = [i for i in ids if i not in old]
        removed = [i for i in old if i not in ids]
        print(f"{org}: {len(ids)} (prev {len(old)}) added={len(added)} removed={len(removed)}")
        if added:
            by_id = {j["id"]: j for j in jobs}
            for i in added:
                j = by_id[i]
                print(f"    + {j.get('title')} | remote={j.get('isRemote')} | {j.get('locationName')} | {j.get('publishedAt')}")
    except Exception as e:
        print(f"{org}: FETCH FAIL {e}")
json.dump(new_snap, open("/home/hatch/workspace/job-app-helix/sweep-raw/ashby_snap_0342.json","w"), indent=1)

print("\n=== his-word queue liveness re-check ===")
for org, iid, label in [("drata","1846ef60","Drata Senior Applied AI Eng 2")]:
    try:
        req = urllib.request.Request(f"https://api.ashbyhq.com/posting-api/job-board/{org}", headers=UA)
        jobs = {j["id"]: j for j in json.load(urllib.request.urlopen(req, timeout=30)).get("jobs", [])}
        j = jobs.get(iid)
        print(label, ":", ("LIVE - "+j.get("title")) if j else "NOT FOUND")
    except Exception as e:
        print(label, ": FETCH FAIL", e)
for board, ids in {"honeycomb":[5373987008,5452445008,5452584008],"samsara":[8024110,7858719]}.items():
    for i in ids:
        try:
            r = urllib.request.urlopen(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{i}", timeout=20)
            j = json.load(r)
            print(f"GH {board}/{i}: LIVE - {j.get('title')}")
        except Exception as e:
            print(f"GH {board}/{i}: GONE/FAIL {e}")
