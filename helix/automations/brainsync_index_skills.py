#!/usr/bin/env python3
"""Audit / repair BrainSync index.json skill coverage.

BrainSync writes `.brainsync/index.json` with a capped `latestEntries` preview
(historically ~20 items). Multiple memory rows can share the same title
(e.g. "📚 Comprehensive Expert Skills") while carrying distinct content
(**config** / **project** / **python** / **typescript**). Title-only dedupe or
a fixed window can drop those distinct skill rules from the preview.

Source of truth (in priority order):
  1. `.brainsync/memory.jsonl` — full observation log (by id + content)
  2. `.agent/skills/auto/skills-manifest.json` + domain SKILL.md files
  3. `.brainsync/agent-rules.md` Expert Skills section
  4. `.brainsync/index.json` `latestEntries` — non-authoritative preview only

Consumers MUST NOT assume:
  - `latestEntries` contains every skill domain
  - same title ⇒ duplicate / safe to drop
  - stable ordering across regenerations

Usage:
  python3 helix/automations/brainsync_index_skills.py audit
  python3 helix/automations/brainsync_index_skills.py repair
  python3 helix/automations/brainsync_index_skills.py catalog
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BRAINSYNC = REPO_ROOT / ".brainsync"
MEMORY_PATH = BRAINSYNC / "memory.jsonl"
INDEX_PATH = BRAINSYNC / "index.json"
AGENT_RULES = BRAINSYNC / "agent-rules.md"
SKILLS_MANIFEST = REPO_ROOT / ".agent" / "skills" / "auto" / "skills-manifest.json"
SKILLS_AUTO = REPO_ROOT / ".agent" / "skills" / "auto"

EXPECTED_DOMAINS = ("config", "project", "python", "typescript")
EXPERT_SKILLS_TITLE = "📚 Comprehensive Expert Skills (READ THESE)"
DOMAIN_RE = re.compile(
    r"\*\*(config|project|python|typescript)\*\*",
    re.IGNORECASE,
)
# Keep preview useful but large enough for pinned skills + recent noise.
DEFAULT_LATEST_CAP = 32
PIN_TITLE_PREFIXES = (
    EXPERT_SKILLS_TITLE,
    "🔴 CRITICAL — DO NOT IGNORE",
    "🏛️ CORE ARCHITECTURE",
    "Intellectual Property & Architecture Rules",
)


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    kind: str
    title: str
    source: str
    created_at: str
    project_path: str
    content: str
    raw: dict[str, Any]

    @property
    def domain(self) -> str | None:
        m = DOMAIN_RE.search(self.content or "")
        return m.group(1).lower() if m else None

    @property
    def is_expert_skill(self) -> bool:
        return EXPERT_SKILLS_TITLE in (self.title or "") or (
            "Expert Skills" in (self.title or "") and "SKILL.md" in (self.content or "")
        )

    def index_stub(self) -> dict[str, str]:
        # Collapse control/newline whitespace so index.json titles stay single-line.
        title = " ".join((self.title or "").split())
        return {
            "id": self.id,
            "kind": self.kind or "rule",
            "title": title,
            "source": self.source,
            "createdAt": self.created_at,
            "projectPath": self.project_path,
        }

    def skill_rule_row(self) -> dict[str, Any]:
        """Explicit consumer surface for expert skills (never title-collapsed)."""
        domain = self.domain
        skill_path = None
        m = re.search(
            r"\*\*[^*]+\*\*\s*:\s*Read\s+`([^`]+)`",
            self.content or "",
            re.IGNORECASE,
        )
        if m:
            skill_path = m.group(1).strip()
        preview = " ".join((self.content or "").split())[:160]
        return {
            "id": self.id,
            "kind": self.kind or "rule",
            "title": " ".join((self.title or "").split()),
            "source": self.source,
            "createdAt": self.created_at,
            "projectPath": self.project_path,
            "domain": domain,
            "skillPath": skill_path,
            "contentPreview": preview,
            "role": "domain" if domain else "header",
        }


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def load_memory(path: Path = MEMORY_PATH) -> list[MemoryEntry]:
    if not path.is_file():
        return []
    out: list[MemoryEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append(
            MemoryEntry(
                id=str(raw.get("id") or ""),
                kind=str(raw.get("kind") or "note"),
                title=str(raw.get("title") or ""),
                source=str(raw.get("source") or ""),
                created_at=str(raw.get("createdAt") or raw.get("created_at") or ""),
                project_path=str(raw.get("projectPath") or raw.get("project_path") or ""),
                content=str(raw.get("content") or ""),
                raw=raw,
            )
        )
    return out


def load_index(path: Path = INDEX_PATH) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"), strict=False)
    except json.JSONDecodeError as exc:
        print(f"WARN: index.json invalid JSON ({exc}); treating as missing", file=sys.stderr)
        return None


def skill_entries(memory: list[MemoryEntry]) -> list[MemoryEntry]:
    skills = [e for e in memory if e.is_expert_skill]
    # Stable: header (no domain) first, then domains in EXPECTED order, then rest
    domain_rank = {d: i for i, d in enumerate(EXPECTED_DOMAINS)}

    def sort_key(e: MemoryEntry) -> tuple[int, int, str]:
        if e.domain is None and "CRITICAL" in e.content:
            return (0, 0, e.id)
        if e.domain is None:
            return (0, 1, e.id)
        return (1, domain_rank.get(e.domain, 99), e.id)

    return sorted(skills, key=sort_key)


def domains_from_memory(memory: list[MemoryEntry]) -> set[str]:
    return {e.domain for e in skill_entries(memory) if e.domain}


def domains_from_manifest(path: Path = SKILLS_MANIFEST) -> set[str]:
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict):
        return set()
    return {
        str(k).lower() for k, v in data.items() if isinstance(v, dict) and v.get("enabled", True)
    }


def domains_from_skill_files(root: Path = SKILLS_AUTO) -> set[str]:
    if not root.is_dir():
        return set()
    found: set[str] = set()
    for domain in EXPECTED_DOMAINS:
        if (root / domain / "SKILL.md").is_file():
            found.add(domain)
    return found


def domains_from_agent_rules(path: Path = AGENT_RULES) -> set[str]:
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8")
    return {m.group(1).lower() for m in DOMAIN_RE.finditer(text)}


def domains_from_latest(index: dict[str, Any] | None, memory: list[MemoryEntry]) -> set[str]:
    if not index:
        return set()
    by_id = {e.id: e for e in memory}
    latest = index.get("latestEntries") or []
    found: set[str] = set()
    for stub in latest:
        if not isinstance(stub, dict):
            continue
        eid = str(stub.get("id") or "")
        mem = by_id.get(eid)
        if mem and mem.domain:
            found.add(mem.domain)
            continue
        title = str(stub.get("title") or "")
        # Preview stubs omit content — cannot recover domain without memory
        if EXPERT_SKILLS_TITLE in title and not mem:
            continue
    return found


def title_only_dupes(entries: list[MemoryEntry]) -> list[tuple[str, int, int]]:
    """Return (title, count, distinct_content_hashes) for titles with multi content."""
    by_title: dict[str, list[str]] = {}
    for e in entries:
        by_title.setdefault(e.title, []).append(e.content)
    report: list[tuple[str, int, int]] = []
    for title, contents in by_title.items():
        uniq = len({c for c in contents})
        if len(contents) > 1 and uniq > 1:
            report.append((title, len(contents), uniq))
    report.sort(key=lambda x: (-x[2], -x[1], x[0]))
    return report


def cmd_catalog(args: argparse.Namespace) -> int:
    memory = load_memory()
    skills = skill_entries(memory)
    catalog = {
        "generatedAt": utc_now(),
        "sourceOfTruth": [
            str(MEMORY_PATH.relative_to(REPO_ROOT)),
            str(SKILLS_MANIFEST.relative_to(REPO_ROOT)),
            str(SKILLS_AUTO.relative_to(REPO_ROOT)),
        ],
        "consumerRules": [
            "Do not dedupe by title alone — content may differ under the same title.",
            "Prefer index.json skillRules[] when present (domain + skillPath + id).",
            "Do not require skill domains only from latestEntries title counts.",
            "Authoritative: memory.jsonl content, skills-manifest, or SKILL.md paths.",
        ],
        "expectedDomains": list(EXPECTED_DOMAINS),
        "memorySkillEntries": [
            {
                "id": e.id,
                "domain": e.domain,
                "title": e.title,
                "contentPreview": (e.content or "").replace("\n", " ")[:160],
                "source": e.source,
            }
            for e in skills
        ],
        "domains": {
            "memory": sorted(domains_from_memory(memory)),
            "manifest": sorted(domains_from_manifest()),
            "skillFiles": sorted(domains_from_skill_files()),
            "agentRules": sorted(domains_from_agent_rules()),
            "indexLatestEntries": sorted(domains_from_latest(load_index(), memory)),
        },
    }
    text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    memory = load_memory()
    index = load_index()
    skills = skill_entries(memory)

    mem_domains = domains_from_memory(memory)
    man_domains = domains_from_manifest()
    file_domains = domains_from_skill_files()
    rules_domains = domains_from_agent_rules()
    latest_domains = domains_from_latest(index, memory)

    expected = set(EXPECTED_DOMAINS)
    hard_ok = True
    soft_warnings: list[str] = []
    hard_errors: list[str] = []

    # Hard: memory + on-disk skill files must cover expected domains
    if memory and not expected.issubset(mem_domains | rules_domains):
        missing = sorted(expected - (mem_domains | rules_domains))
        hard_errors.append(f"memory/agent-rules missing skill domains: {missing}")
        hard_ok = False
    if not expected.issubset(file_domains | man_domains):
        missing = sorted(expected - (file_domains | man_domains))
        # Skill files are the real executable surface
        if not expected.issubset(file_domains):
            hard_errors.append(f"SKILL.md files missing domains: {missing}")
            hard_ok = False
        else:
            soft_warnings.append(
                f"skills-manifest incomplete (files ok): missing {sorted(expected - man_domains)}"
            )

    # Soft: latestEntries is a preview — report gaps but do not fail audit unless --strict-index
    missing_latest = sorted(expected - latest_domains)
    if missing_latest:
        msg = (
            f"index.json latestEntries missing skill domains {missing_latest} "
            f"(present in memory: {sorted(mem_domains)}; this is expected under a capped preview)"
        )
        if args.strict_index:
            hard_errors.append(msg)
            hard_ok = False
        else:
            soft_warnings.append(msg)

    # If skillRules is present, it must list every memory expert-skill id + domains.
    if index is not None and "skillRules" in index:
        skill_rules = index.get("skillRules") or []
        rule_ids = {str(r.get("id") or "") for r in skill_rules if isinstance(r, dict)}
        mem_ids = {e.id for e in skills if e.id}
        if mem_ids - rule_ids:
            hard_errors.append(f"skillRules missing memory skill ids: {sorted(mem_ids - rule_ids)}")
            hard_ok = False
        rule_domains = {
            str(r.get("domain")).lower()
            for r in skill_rules
            if isinstance(r, dict) and r.get("domain")
        }
        if not expected.issubset(rule_domains | mem_domains):
            # skillRules should carry domains even when latestEntries is thin
            missing = sorted(expected - rule_domains)
            if missing and mem_domains:
                hard_errors.append(f"skillRules missing domains: {missing}")
                hard_ok = False

    # Skill entry inventory
    print("brainsync_index_skills audit")
    print(f"  memory entries: {len(memory)}")
    print(f"  expert-skill rows: {len(skills)} (ids: {[e.id for e in skills]})")
    print(f"  domains memory:     {sorted(mem_domains)}")
    print(f"  domains manifest:   {sorted(man_domains)}")
    print(f"  domains skill files:{sorted(file_domains)}")
    print(f"  domains agent-rules:{sorted(rules_domains)}")
    print(f"  domains index latest:{sorted(latest_domains)}")
    if index:
        latest = index.get("latestEntries") or []
        print(f"  index totalEntries: {index.get('totalEntries')} latestEntries: {len(latest)}")
        titles = Counter(str(e.get("title") or "") for e in latest if isinstance(e, dict))
        multi = [(t, n) for t, n in titles.items() if n > 1]
        if multi:
            print("  latestEntries multi-title groups (not necessarily duplicates):")
            for t, n in sorted(multi, key=lambda x: -x[1])[:8]:
                print(f"    {n}x {t[:70]}")

    same_title = title_only_dupes(memory)
    if same_title:
        print("  memory titles with DISTINCT content (title-only dedupe is unsafe):")
        for title, count, uniq in same_title[:10]:
            print(f"    {count} rows / {uniq} contents — {title[:70]}")

    for w in soft_warnings:
        print(f"  WARN: {w}")
    for e in hard_errors:
        print(f"  ERROR: {e}", file=sys.stderr)

    if hard_ok:
        print(
            "  RESULT: OK — skill domains preserved; consumers must not rely on latestEntries alone"
        )
        return 0
    print("  RESULT: FAIL", file=sys.stderr)
    return 1


def rebuild_latest_entries(
    memory: list[MemoryEntry],
    existing_index: dict[str, Any] | None,
    cap: int = DEFAULT_LATEST_CAP,
) -> list[dict[str, str]]:
    """Build latestEntries that pins distinct skill rows and fills with recent others."""
    skills = skill_entries(memory)
    pinned_ids = {e.id for e in skills}

    # Also pin critical same-title-distinct groups that tooling often surfaces
    for e in memory:
        if any(e.title.startswith(p) or e.title == p for p in PIN_TITLE_PREFIXES):
            pinned_ids.add(e.id)

    by_id = {e.id: e for e in memory if e.id}
    pinned = [by_id[i] for i in pinned_ids if i in by_id]

    # Prefer existing latest order for non-pinned, then recency
    existing_order: list[str] = []
    if existing_index:
        for stub in existing_index.get("latestEntries") or []:
            if isinstance(stub, dict) and stub.get("id"):
                existing_order.append(str(stub["id"]))

    def recency_key(e: MemoryEntry) -> str:
        return e.created_at or ""

    # Sort pinned: skills first (domain order), then other pins by recency desc
    skill_ids = {e.id for e in skills}
    pinned_skills = [e for e in pinned if e.id in skill_ids]
    pinned_other = sorted(
        [e for e in pinned if e.id not in skill_ids],
        key=recency_key,
        reverse=True,
    )
    # Keep skill order from skill_entries()
    pinned_ordered = pinned_skills + pinned_other

    remaining_cap = max(0, cap - len(pinned_ordered))
    used = {e.id for e in pinned_ordered}
    fillers: list[MemoryEntry] = []

    # Walk prior latest order first (stability), then rest by recency
    for eid in existing_order:
        if remaining_cap <= 0:
            break
        if eid in used or eid not in by_id:
            continue
        fillers.append(by_id[eid])
        used.add(eid)
        remaining_cap -= 1

    if remaining_cap > 0:
        rest = sorted(
            [e for e in memory if e.id not in used],
            key=recency_key,
            reverse=True,
        )
        for e in rest:
            if remaining_cap <= 0:
                break
            fillers.append(e)
            used.add(e.id)
            remaining_cap -= 1

    # Layout: critical pin header skill → fillers → remaining skill domain rows
    # matches historical BrainSync shape (header early, domain rows present)
    header = [e for e in pinned_skills if e.domain is None]
    domains = [e for e in pinned_skills if e.domain is not None]
    other_pins = pinned_other
    combined = header + other_pins + fillers + domains

    # De-dupe by id preserving order
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for e in combined:
        if not e.id or e.id in seen:
            continue
        seen.add(e.id)
        out.append(e.index_stub())
        if len(out) >= cap:
            # Ensure all skill domain stubs still included even if over soft layout
            break

    # Guarantee every skill id is present even if cap would truncate
    out_ids = {s["id"] for s in out}
    for e in pinned_skills:
        if e.id not in out_ids:
            out.append(e.index_stub())
            out_ids.add(e.id)
    return out


def rebuild_index(
    memory: list[MemoryEntry], existing: dict[str, Any] | None, cap: int
) -> dict[str, Any]:
    by_kind: Counter[str] = Counter()
    for e in memory:
        by_kind[e.kind or "note"] += 1

    project = (existing or {}).get("project") or {}
    if not project and memory:
        # minimal project block from first entry path
        project = {
            "key": "",
            "name": REPO_ROOT.name,
            "rootPath": str(REPO_ROOT),
            "reference": "",
            "createdAt": "",
            "updatedAt": utc_now(),
        }

    skills = skill_entries(memory)
    return {
        "v": int((existing or {}).get("v") or 1),
        "project": project,
        "updatedAt": utc_now(),
        "totalEntries": len(memory),
        "byKind": dict(sorted(by_kind.items())),
        "latestEntries": rebuild_latest_entries(memory, existing, cap=cap),
        # Explicit skill surface — prefer over title-matching latestEntries.
        "skillRules": [e.skill_rule_row() for e in skills],
    }


def cmd_repair(args: argparse.Namespace) -> int:
    memory = load_memory()
    if not memory:
        print("repair: no memory.jsonl — nothing to do", file=sys.stderr)
        return 1
    existing = load_index()
    cap = int(args.cap)
    new_index = rebuild_index(memory, existing, cap=cap)

    skills = skill_entries(memory)
    latest_ids = {e["id"] for e in new_index["latestEntries"]}
    missing = [e.id for e in skills if e.id not in latest_ids]
    if missing:
        print(f"repair: internal error — skills still missing: {missing}", file=sys.stderr)
        return 1

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        INDEX_PATH.write_text(
            json.dumps(new_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"repair: wrote {INDEX_PATH.relative_to(REPO_ROOT)}")
    else:
        print("repair: dry-run (no write)")

    print(
        f"  totalEntries={new_index['totalEntries']} "
        f"latestEntries={len(new_index['latestEntries'])} cap={cap}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="Verify skill domains survive indexing/preview")
    a.add_argument(
        "--strict-index",
        action="store_true",
        help="Fail if latestEntries omits any expected skill domain",
    )
    a.set_defaults(func=cmd_audit)

    r = sub.add_parser("repair", help="Rewrite index.json latestEntries pinning distinct skills")
    r.add_argument(
        "--cap",
        type=int,
        default=DEFAULT_LATEST_CAP,
        help=f"latestEntries size (default {DEFAULT_LATEST_CAP})",
    )
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(func=cmd_repair)

    c = sub.add_parser("catalog", help="Emit skill catalog JSON for consumers")
    c.add_argument("--out", type=str, default="", help="Write path (default stdout)")
    c.set_defaults(func=cmd_catalog)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
