import json, urllib.request, urllib.error, re
BASE = "https://boards-api.greenhouse.io/v1/boards/{}/jobs"
BOARDS = ["huggingface","sourcegraph","replit","sentry","hashicorp","confluent","snowflake",
          "temporalio","procore","servicetitan","glean","you","render","railway","neondatabase",
          "planetscale","flyio","dbtlabs","dagster","prefect","airbyte","fivetran","segment",
          "amplitude","mixpanel","launchdarkly","posthog","clickhouse","motherduck","clickup",
          "notion","linear","ramp","brex","mercury","deel","remote","gusto","rippling"]
FIT = re.compile(r"agent|forward.?deployed|applied ai|\bai engineer\b|\bml engineer\b|ai platform|deployed architect|solutions engineer|solutions architect|\bfde\b|agentic|customer ai|customer engineer|forward deployed|member of technical|ai solutions|sales engineer|technical account|applied scientist", re.I)
for b in BOARDS:
    try:
        r = urllib.request.urlopen(BASE.format(b), timeout=20)
        jobs = json.load(r)["jobs"]
        print(f"== {b}: {len(jobs)} jobs")
        for j in jobs:
            loc = j.get("location",{}).get("name","?")
            if FIT.search(j["title"]) and re.search(r"remote", loc, re.I):
                print(f"  [FIT-REMOTE] id={j['id']} | {j['title']} | {loc} | https://job-boards.greenhouse.io/{b}/jobs/{j['id']}")
            elif FIT.search(j["title"]):
                print(f"  [fit-onsite] id={j['id']} | {j['title']} | {loc}")
    except urllib.error.HTTPError as e:
        print(f"== {b}: HTTP {e.code}")
    except Exception as e:
        print(f"== {b}: ERR {type(e).__name__}")
