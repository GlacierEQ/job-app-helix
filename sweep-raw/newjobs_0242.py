import json, urllib.request, datetime
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
CUTOFF = datetime.datetime(2026,10,21,11,42,0, tzinfo=datetime.timezone.utc)  # 01:42 HST
def parse_dt(s):
    try: return datetime.datetime.fromisoformat(s)
    except: return None
CHANGED = ["anthropic","asana","figma"]  # count-changed GH boards this run
print("=== GH new postings since 01:42 HST (first_published > cutoff) ===")
for board in CHANGED:
    try:
        req = urllib.request.Request(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?per_page=500", headers=UA)
        jobs = json.load(urllib.request.urlopen(req, timeout=25)).get("jobs", [])
    except Exception as e:
        print(f"{board}: FAIL {e}"); continue
    fresh = [j for j in jobs if (parse_dt(j.get("first_published") or "") or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)) > CUTOFF]
    print(f"{board}: {len(jobs)} total, {len(fresh)} new since cutoff")
    for j in fresh:
        loc = j.get("location",{}).get("name")
        print(f"  NEW: {j.get('title')} | {loc} | first_pub={j.get('first_published')} | {j.get('absolute_url')}")
print("\n=== Ashby resweep: new jobs since 01:42 HST ===")
ASHBY = ["runpod","crusoe","browserbase","firecrawl","steel","openrouter"]
for org in ASHBY:
    try:
        req = urllib.request.Request(f"https://api.ashbyhq.com/posting-api/job-board/{org}", headers=UA)
        jobs = json.load(urllib.request.urlopen(req, timeout=30)).get("jobs", [])
    except Exception as e:
        print(f"{org}: FAIL {e}"); continue
    fresh = [j for j in jobs if (parse_dt(j.get("publishedAt") or "") or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)) > CUTOFF]
    print(f"{org}: {len(jobs)} total, {len(fresh)} new since cutoff")
    for j in fresh:
        print(f"  NEW: {j.get('title')} | remote={j.get('isRemote')} | {j.get('locationName')} | pub={j.get('publishedAt')}")
