import json, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# GH board counts at 01:42 HST (2026-10-21 run snapshot)
GH_EXPECTED = {
 "databricks":899,"reddit":154,"vercel":94,"afresh":12,"cribl":74,"figma":142,
 "stripe":730,"airtable":4,"asana":104,"dropbox":21,"duolingo":62,"instacart":125,
 "robinhood":156,"affirm":219,"boxinc":119,"fieldwire":27,"gitlab":232,
 "intercom":107,"xai":302,"togetherai":78,"coreweave":322,"assemblyai":15,
 "labelbox":7,"tavily":13,"lightmatter":63,"nebius":378,"lightningai":51,
 "magic":0,"warp":4,"openspace":6,"comet":3,"anthropic":676,"datadog":436,
 "elastic":369,"scaleai":176,"mongodb":398,"coinbase":229,
}

print("=== GREENHOUSE board delta (01:42 -> 02:42 HST) ===")
for board, prev in sorted(GH_EXPECTED.items()):
    try:
        req = urllib.request.Request(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?per_page=500",
            headers=UA)
        jobs = json.load(urllib.request.urlopen(req, timeout=25)).get("jobs", [])
        n = len(jobs)
        flag = "" if n == prev else f"  *** CHANGED {prev}->{n}"
        print(f"{board}: {n}{flag}")
        if n != prev:
            for j in jobs[:25]:
                print(f"    - {j.get('title')} | {j.get('absolute_url')}")
    except Exception as e:
        print(f"{board}: FETCH FAIL {e}")
    if board == "scaleai" and n == prev:
        pass

print("\n=== ASHBY board resweep (vs ashby_snap_0142.json) ===")
ASHBY_BOARDS = ["runpod","crusoe","browserbase","firecrawl","steel","openrouter"]
try:
    snap = json.load(open("/home/hatch/workspace/job-app-helix/sweep-raw/ashby_snap_0142.json"))
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
        if removed:
            for i in removed:
                print(f"    - removed id {i}")
    except Exception as e:
        print(f"{org}: FETCH FAIL {e}")
json.dump(new_snap, open("/home/hatch/workspace/job-app-helix/sweep-raw/ashby_snap_0242.json","w"), indent=1)
print("\n=== shortlist verification: Drata + GH flagged reqs ===")
# Drata senior applied AI id 1846ef60 via Ashby posting API
try:
    req = urllib.request.Request("https://api.ashbyhq.com/posting-api/job-board/drata", headers=UA)
    jobs = {j["id"]: j for j in json.load(urllib.request.urlopen(req, timeout=30)).get("jobs", [])}
    j = jobs.get("1846ef60")
    if j:
        print("drata 1846ef60 LIVE:", j.get("title"), "| remote:", j.get("isRemote"), "| loc:", j.get("locationName"),
              "| comp:", j.get("compensationTierSummary") or "not stated", "| pub:", j.get("publishedAt"))
    else:
        print("drata 1846ef60: NOT FOUND (removed?)")
except Exception as e:
    print("drata: FETCH FAIL", e)
for board, ids in {"honeycomb":[5373987008,5452445008,5452584008],"samsara":[8024110,7858719]}.items():
    for i in ids:
        try:
            r = urllib.request.urlopen(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{i}", timeout=20)
            j = json.load(r)
            print(f"GH {board}/{i}: LIVE - {j.get('title')}")
        except Exception as e:
            print(f"GH {board}/{i}: GONE/FAIL {e}")
