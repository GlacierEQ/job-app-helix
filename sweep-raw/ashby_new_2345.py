import json, urllib.request, urllib.error, re

BASE = "https://api.ashbyhq.com/posting-api/job-board/{}"
ORGS = ["groq","sambanova","replicate","fal","runpod","crusoe","browserbase","firecrawl",
        "browseruse","steel","retellai","hume","playai","augmentcode","factoryai","weightsandbiases",
        "jina","mistralai","ai21labs","inflection","youcom","phind","codeium","tabnine","augment",
        "augmentcode","openrouter","portkey","helicone","langfuse","argilla","cleanlab","snorkel",
        "scale","apppen","toloka","centaur"]
FIT = re.compile(r"agent|forward.?deployed|applied ai|\bai engineer\b|\bml engineer\b|ai platform|deployed architect|solutions engineer|solutions architect|\bfde\b|agentic|customer ai|customer engineer|forward deployed|member of technical|ai solutions|sales engineer|technical account", re.I)
results = {}
for org in ORGS:
    try:
        req = urllib.request.Request(BASE.format(org), headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        r = urllib.request.urlopen(req, timeout=20)
        d = json.load(r)
        jobs = d.get("jobs", [])
        results[org] = len(jobs)
        for j in jobs:
            loc = j.get("locationName","?") or "?"
            remote = bool(j.get("isRemote")) or re.search(r"remote", loc, re.I)
            if FIT.search(j.get("title","")) and remote:
                print(f"[FIT] {org} | id={j.get('id')} | {j.get('title')} | {loc} | remote={j.get('isRemote')} | pub={j.get('publishedAt')}")
            elif FIT.search(j.get("title","")):
                print(f"[onsite] {org} | id={j.get('id')} | {j.get('title')} | {loc}")
    except urllib.error.HTTPError as e:
        results[org] = f"HTTP {e.code}"
    except Exception as e:
        results[org] = f"ERR {type(e).__name__}"
print("\nCOUNTS:", json.dumps(results))
with open("ashby_new_2345.json","w") as f: json.dump(results, f)
