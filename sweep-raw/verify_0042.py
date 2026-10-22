import json, urllib.request, re, html

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
def strip(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()

ASHBY_TARGETS = {
 "harvey": ["01da8934-d3e3-4ebb-beb9-681b3c24fb9c","ebf00b72-4693-4894-b540-5f82a60fdbdc",
   "f47e1925-2a89-4264-8a1b-09cd9215f4dd","d00dc18e-862b-4391-a3f1-5cd49c07f8e7",
   "04eb457b-e985-4e3b-9635-0a2b867ada97","fc038666-be6f-4365-be8d-fb46e520473d",
   "523ecfb5-63ed-4ca6-801e-bad3ab441e76","43c6e218-ea85-4519-b2fe-dd188ff3234f4",
   "fb3ecf9e-9379-4839-817c-f620a3e6034d","576271e5-a578-40de-8706-b8d932b5788c"],
 "perplexity": ["7755eb0a-0f51-4286-b75e-591e44c741bc","2c6ae16b-d03e-4e33-9d32-362c5388e956",
   "9cec9b33-06f2-4ba1-8c9e-20a598361ca2","daafcaba-cc39-487a-b941-d7a407753788",
   "0190699f-010b-44f2-8399-278899fef018","60deb376-51b5-46c6-9e17-55377a5ef34e"],
 "vapi": ["0d4f1420-2590-4a38-aac4-3efda12eadb0","250ac759-97a6-46b8-ad7c-9bb4f223dd26"],
 "cursor": ["cda9256f-e820-4f0a-9e77-e44c61295e1d"],
 "decagon": ["7df0a996-5a9f-496f-9f8b-c302983765b2","2351ca53-b7fd-4835-b967-4ae2b976b5b4",
   "6431a6f9-2ebe-4b68-beb6-200b42aeeca8","78745829-74ee-41cb-836c-480ca7bf9edc"],
 "drata": ["1846ef60"],
 "sierra": ["787c1efd-2327-46e7-9335-59a20ad4be18"],
 "suno": ["70bb2a0c-b32d-41ad-9848-158edd5e9bac"],
}
GH_TARGETS = {"honeycomb": [5373987008, 5452445008, 5452584008],
              "samsara": [8024110, 7858719]}

for org, ids in ASHBY_TARGETS.items():
    try:
        req = urllib.request.Request(f"https://api.ashbyhq.com/posting-api/job-board/{org}", headers=UA)
        jobs = {j["id"]: j for j in json.load(urllib.request.urlopen(req, timeout=30)).get("jobs", [])}
    except Exception as e:
        print(f"== {org}: FETCH FAIL {e}"); continue
    for i in ids:
        j = jobs.get(i)
        if not j:
            print(f"== {org}/{i}: NOT FOUND (removed?)"); continue
        print(f"\n===== {org} | {j.get('title')} =====")
        print("id:", i)
        print("location:", j.get("locationName"), "| remote:", j.get("isRemote"))
        print("published:", j.get("publishedAt"))
        print("comp:", j.get("compensationTierSummary") or "not stated")
        print("dept:", j.get("departmentName"), "| employment:", j.get("employmentType"))
        print("url: https://jobs.ashbyhq.com/{}/{}".format(org, i))
        print("DESC:", strip(j.get("descriptionHtml") or j.get("descriptionPlain"))[:2200])

for board, ids in GH_TARGETS.items():
    for i in ids:
        try:
            r = urllib.request.urlopen(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{i}", timeout=20)
            j = json.load(r)
        except Exception as e:
            print(f"\n===== GH {board}/{i}: FETCH FAIL {e}"); continue
        print(f"\n===== GH {board} | {j.get('title')} =====")
        print("id:", i)
        locs = j.get("offices") or []
        print("offices:", [o.get("name") for o in locs], "| location name:", j.get("location",{}).get("name"))
        md = {m.get("name"): m.get("value") for m in (j.get("metadata") or [])}
        print("pay:", md.get("Pay Range") or md.get("pay-range") or "not stated")
        print("url:", j.get("absolute_url"))
        print("DESC:", strip(j.get("description"))[:2200])
