# Library of Links → Genius Impact Loop

**Repos:** [GlacierEQ/library-of-links](https://github.com/GlacierEQ/library-of-links)  
**Laws:** `MAXIMIZE_KNOWLEDGE_QUALITY` → **`MAXIMIZE_IMPACT`**

## Loop

```text
weekly advanced tech (S/A primary sources)
        ↓
  impact_engine ranks + routes → mechanisms + estate leaves
        ↓
  Genius research loads impact_queue into advanced_context
        ↓
  invent → attack → rank → advance brief
        ↓
  land code on leaf; publish genius leaf back to domains/genius/
```

## Surfaces

| Path | Role |
|---|---|
| `IMPACT.md` | Human/agent action queue |
| `registry/impact_queue.json` | Machine-ranked actions |
| `registry/mechanism_map.json` | Knowledge → Genius mechanism ids |
| `registry/top_shelf.json` | Highest quality tech shelf |
| `digests/weekly/*` | ISO-week digests |

## Env

```bash
export GENIUS_LIBRARY_OF_LINKS_ROOT=~/.grok/work/library-of-links
export LIBRARY_OF_LINKS_ROOT=$GENIUS_LIBRARY_OF_LINKS_ROOT
```

## Commands

```bash
# Library side
python3 scripts/weekly_accumulate.py
python3 scripts/impact_engine.py
python3 scripts/impact_query.py --domain agents --limit 5
python3 scripts/impact_query.py --mech mcp_package_restore

# Genius side (consumes impact queue during research)
PYTHONPATH=src python scripts/genius_engine.py invent \
  --repository GlacierEQ/glaciereq-mcp-stack --markdown
```

Impact multiplies only when knowledge **routes into invent and land** — not when links sit idle.
