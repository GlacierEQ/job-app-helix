import json, urllib.request, urllib.error, datetime, re, os

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
CUTOFF = datetime.datetime(2026,10,21,18,42,0, tzinfo=datetime.timezone.utc)  # 08:42 HST
def parse_dt(s):
    try:
        d = datetime.datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except: return None

# GH board counts at 08:42 HST (2026-10-21 sweep actuals)
GH_EXPECTED = {
 "databricks":898,"reddit":153,"vercel":95,"afresh":12,"cribl":79,"figma":139,
 "stripe":728,"airtable":4,"asana":105,"dropbox":23,"duolingo":61,"instacart":125,
 "robinhood":153,"affirm":224,"boxinc":116,"fieldwire":28,"gitlab":230,
 "intercom":106,"xai":300,"togetherai":79,"coreweave":322,"assemblyai":15,
 "labelbox":7,"tavily":13,"lightmatter":62,"nebius":382,"lightningai":51,
 "magic":0,"warp":4,"openspace":6,"comet":3,"anthropic":674,"datadog":437,
 "elastic":371,"scaleai":175,"mongodb":397,"coinbase":228,
}
FIT = re.compile(r"agent|forward.?deployed|applied ai|\bai engineer\b|\bml engineer\b|ai platform|deployed architect|solutions engineer|solutions architect|\bfde\b|agentic|customer ai|customer engineer|member of technical|forward deployed|ai solutions|sales engineer|technical account", re.I)

print("=== GREENHOUSE board delta (08:42 -> 09:42 HST) ===")
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

print("\n=== GH new postings since 08:42 HST (first_published > cutoff) ===")
for board, jobs in changed_boards:
    fresh = [j for j in jobs if (parse_dt(j.get("first_published") or "") or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)) > CUTOFF]
    print(f"{board}: {len(jobs)} total, {len(fresh)} new since cutoff")
    for j in fresh:
        loc = j.get("location",{}).get("name","?")
        m = "FIT" if FIT.search(j.get("title","")) else "   "
        print(f"  {m} id={j['id']} | {j['title']} | {loc} | first_published={j.get('first_published')}")

print("\n=== ASHBY resweep vs ashby_snap_0842.json ===")
BASE = "https://api.ashbyhq.com/posting-api/job-board/{}"
LIVE = ["runpod","crusoe","browserbase","firecrawl","steel","openrouter"]
prior = json.load(open("ashby_snap_0842.json")) if os.path.exists("ashby_snap_0842.json") else {}
snap = {}
for org in LIVE:
    try:
        req = urllib.request.Request(BASE.format(org), headers=UA)
        d = json.load(urllib.request.urlopen(req, timeout=30))
        jobs = d.get("jobs", [])
        snap[org] = {j.get("id"): j.get("title") for j in jobs}
        old = prior.get(org, {})
        new_ids = [i for i in snap[org] if i not in old]
        removed = [i for i in old if i not in snap[org]]
        print(f"{org}: {len(jobs)} jobs ({len(new_ids)} new, {len(removed)} removed)")
        for i in new_ids:
            print(f"  [NEW] id={i} | {snap[org][i]}")
        for i in removed:
            print(f"  [GONE] id={i} | {old[i]}")
        for j in jobs:
            loc = j.get("locationName","?") or "?"
            if j.get("id") in new_ids and FIT.search(j.get("title","")):
                print(f"  [NEWFIT] {org} | {j.get('title')} | {loc} | remote={j.get('isRemote')}")
    except Exception as e:
        print(f"{org}: ERR {type(e).__name__} {e}")
with open("ashby_snap_0942.json","w") as f: json.dump(snap, f)
print("\nsnapshot saved: ashby_snap_0942.json")
