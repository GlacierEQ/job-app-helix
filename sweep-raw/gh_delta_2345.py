import json, urllib.request, urllib.error, re

BASE = "https://boards-api.greenhouse.io/v1/boards/{}/jobs"
# board: prior count from 2245 run
BOARDS = {
 "databricks":900,"scaleai":178,"reddit":155,"vercel":94,"afresh":12,"coinbase":230,
 "cribl":74,"figma":141,"stripe":732,"airtable":4,"asana":104,"dropbox":21,"duolingo":62,
 "instacart":125,"robinhood":156,"affirm":219,"boxinc":119,"fieldwire":27,"gitlab":232,
 "intercom":107,"xai":301,"togetherai":78,"coreweave":322,"assemblyai":15,"labelbox":7,
 "tavily":13,"lightmatter":63,"nebius":377,"lightningai":51,"magic":0,"warp":4,
 "openspace":6,"comet":3,"anthropic":674,"mongodb":396,"datadog":435,"elastic":372,
}
def get(b):
    try:
        r = urllib.request.urlopen(BASE.format(b), timeout=20)
        d = json.load(r)
        return d["jobs"]
    except Exception as e:
        return None
out = {}
changed = []
for b, prior in BOARDS.items():
    jobs = get(b)
    if jobs is None:
        out[b] = {"error": True}; continue
    n = len(jobs)
    out[b] = {"count": n, "delta": n - prior}
    if n != prior:
        changed.append((b, prior, n, jobs))
print("ERRORS:", [b for b,v in out.items() if "error" in v])
print("CHANGED:", [(b,p,n) for b,p,n,_ in changed])
# for changed boards, find newest jobs by id
FIT = re.compile(r"agent|forward.?deployed|applied ai|\bai engineer\b|\bml engineer\b|ai platform|deployed architect|solutions engineer|solutions architect|fde\b|agentic|customer engineer|member of technical|forward deployed", re.I)
for b, p, n, jobs in changed:
    print(f"\n=== {b}: {p} -> {n} ===")
    for j in sorted(jobs, key=lambda j: j["id"], reverse=True)[:12]:
        loc = j.get("location",{}).get("name","?")
        m = "FIT" if FIT.search(j["title"]) else "  "
        print(f"{m} id={j['id']} | {j['title']} | {loc}")
with open("gh_delta_2345.json","w") as f: json.dump(out, f)
