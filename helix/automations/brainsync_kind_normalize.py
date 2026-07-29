#!/usr/bin/env python3
"""Normalize BrainSync memory kinds + rebuild index.

Problem
  Session history titled "What Was Done" was written as both kind=rule and
  kind=note. Consumers that filter by kind (index byKind, Critical Rules vs
  Project Notes sections) miss or mis-rank those entries.

  Expert skill rules share one section title ("Comprehensive Expert Skills")
  but are distinct by content (config / project / python / typescript). A
  naive title-dedupe or top-N truncation drops domain rows and breaks tooling
  that expects every skill rule to remain addressable from the index.

Canonical mapping
  title == "What Was Done"  →  kind: note
  (session history is episodic project notes, not durable agent rules)

Also rebuilds .brainsync/index.json:
  totalEntries, byKind, latestEntries (priority desc, createdAt desc),
  skillRules (all distinct expert-skill entries, never title-collapsed).

Consumer contract
  - Do not assume latestEntries length or ordering for skill domains.
  - Query skillRules (or memory.jsonl content/tags) for expert skills.
  - latestEntries still includes every skillRules id so legacy readers that
    only scan latestEntries keep seeing distinct skill rows.

Usage:
  python3 helix/automations/brainsync_kind_normalize.py check
  python3 helix/automations/brainsync_kind_normalize.py apply
  python3 helix/automations/brainsync_kind_normalize.py apply --memory .brainsync/memory.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MEMORY = REPO_ROOT / ".brainsync" / "memory.jsonl"
DEFAULT_INDEX = REPO_ROOT / ".brainsync" / "index.json"
DEFAULT_PROJECT = REPO_ROOT / ".brainsync" / "project.json"

# Titles that must always be notes (session / episodic history).
CANONICAL_NOTE_TITLES = frozenset(
    {
        "What Was Done",
        "Last Session Summary",
    }
)

# When reclassifying a rule→note for session titles, drop inflated rule priority
# so latestEntries stays dominated by real rules/decisions.
NOTE_PRIORITY_CAP = 2

LATEST_N = 20

# Shared section title for pre-compiled expert skill rulebooks (distinct by content).
EXPERT_SKILLS_TITLE_MARKER = "Comprehensive Expert Skills"

# **domain**: Read `path/to/SKILL.md`
_SKILL_DOMAIN_RE = re.compile(
    r"\*\*(?P<domain>[^*]+)\*\*\s*:\s*Read\s+`(?P<path>[^`]+)`",
    re.IGNORECASE,
)

# Generated markdown consumers that embed "Kind: <kind>" lines.
CONTEXT_GLOBS = (
    ".brainsync/generated-context.md",
    ".brainsync/shadows/**/*.md",
    "AGENTS.md",
    "GEMINI.md",
    "CLAUDE.md",
    "AGENT.md",
    ".cursor/active-context.md",
    ".windsurf/rules/brainsync.md",
    ".kiro/steering/brainsync.md",
    ".agents/rules/brainsyncory.md",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.is_file():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # strict=False: tolerate legacy control chars inside content fields
        entries.append(json.loads(line, strict=False))
    return entries


def write_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in entries)
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def is_session_history_title(title: str | None) -> bool:
    if not title:
        return False
    t = title.strip()
    if t in CANONICAL_NOTE_TITLES:
        return True
    # Tolerate leading emoji / numbering noise
    for canon in CANONICAL_NOTE_TITLES:
        if t.endswith(canon) or t == canon:
            return True
    return False


def is_expert_skill_entry(entry: dict[str, Any]) -> bool:
    """True for Comprehensive Expert Skills rows (header or domain SKILL.md pointers)."""
    title = entry.get("title")
    return isinstance(title, str) and EXPERT_SKILLS_TITLE_MARKER in title


def sanitize_index_title(title: Any) -> Any:
    """Collapse newlines/control whitespace so index.json stays valid single-line titles."""
    if not isinstance(title, str):
        return title
    return " ".join(title.split())


def extract_skill_domain(content: str | None) -> str | None:
    if not content:
        return None
    m = _SKILL_DOMAIN_RE.search(content)
    if m:
        return m.group("domain").strip().lower()
    return None


def extract_skill_path(content: str | None) -> str | None:
    """Return domain SKILL.md path only when a **domain**: Read `...` line exists.

    Header prose often mentions bare `SKILL.md`; do not treat that as a path.
    """
    if not content:
        return None
    m = _SKILL_DOMAIN_RE.search(content)
    if m:
        return m.group("path").strip()
    return None


def content_preview(content: str | None, limit: int = 160) -> str:
    if not content:
        return ""
    # Prefer the first non-title substance line
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return ""
    body = lines[0]
    for ln in lines[1:]:
        if EXPERT_SKILLS_TITLE_MARKER in ln:
            continue
        body = ln
        break
    if len(body) > limit:
        return body[: limit - 1] + "…"
    return body


def normalize_entry(entry: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return (entry, changed)."""
    title = entry.get("title")
    if not is_session_history_title(title if isinstance(title, str) else None):
        return entry, False

    changed = False
    out = dict(entry)

    if out.get("kind") != "note":
        out["kind"] = "note"
        changed = True

    try:
        prio = int(out.get("priority") or 0)
    except (TypeError, ValueError):
        prio = 0
    if prio > NOTE_PRIORITY_CAP:
        out["priority"] = NOTE_PRIORITY_CAP
        changed = True

    if changed:
        out["updatedAt"] = utc_now_iso()
        meta = dict(out.get("metadata") or {})
        meta["kindNormalized"] = "what-was-done→note"
        out["metadata"] = meta

    return out, changed


def normalize_entries(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    out: list[dict[str, Any]] = []
    n_changed = 0
    for e in entries:
        ne, ch = normalize_entry(e)
        out.append(ne)
        if ch:
            n_changed += 1
    return out, n_changed


def violations(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bad: list[dict[str, Any]] = []
    for e in entries:
        title = e.get("title")
        if not is_session_history_title(title if isinstance(title, str) else None):
            continue
        if e.get("kind") != "note":
            bad.append(
                {
                    "id": e.get("id"),
                    "title": title,
                    "kind": e.get("kind"),
                    "priority": e.get("priority"),
                }
            )
    return bad


def _priority(entry: dict[str, Any]) -> int:
    p = entry.get("priority")
    if isinstance(p, bool):
        return int(p)
    if isinstance(p, (int, float)):
        return int(p)
    if isinstance(p, str) and p.lstrip("-").isdigit():
        return int(p)
    return 0


def _rank_key(entry: dict[str, Any]) -> tuple[int, str, str]:
    # priority desc, createdAt desc, id asc for stability
    return (_priority(entry), str(entry.get("createdAt") or ""), str(entry.get("id") or ""))


def latest_entry_row(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("id"),
        "kind": entry.get("kind"),
        "title": sanitize_index_title(entry.get("title")),
        "source": entry.get("source"),
        "createdAt": entry.get("createdAt"),
        "projectPath": entry.get("projectPath"),
    }


def skill_rule_row(entry: dict[str, Any]) -> dict[str, Any]:
    content = entry.get("content") if isinstance(entry.get("content"), str) else ""
    domain = extract_skill_domain(content)
    skill_path = extract_skill_path(content)
    row: dict[str, Any] = {
        "id": entry.get("id"),
        "kind": entry.get("kind"),
        "title": sanitize_index_title(entry.get("title")),
        "source": entry.get("source"),
        "createdAt": entry.get("createdAt"),
        "projectPath": entry.get("projectPath"),
        "domain": domain,
        "skillPath": skill_path,
        "contentPreview": content_preview(content),
        "role": "domain" if domain else "header",
    }
    return row


def collect_expert_skill_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """All distinct expert-skill memory rows (by id). Never collapse same title."""
    by_id: dict[str, dict[str, Any]] = {}
    for e in entries:
        if not is_expert_skill_entry(e):
            continue
        eid = str(e.get("id") or "")
        if not eid:
            # Fall back to hash/content so undated rows still surface
            eid = str(e.get("hash") or content_preview(str(e.get("content") or ""), 64) or id(e))
        by_id[eid] = e
    # Header (no domain) first, then domains alpha, then remaining by rank
    def skill_sort_key(e: dict[str, Any]) -> tuple[int, str, tuple[int, str, str]]:
        content = e.get("content") if isinstance(e.get("content"), str) else ""
        domain = extract_skill_domain(content) or ""
        is_header = 0 if not domain else 1
        return (is_header, domain, _rank_key(e))

    return sorted(by_id.values(), key=skill_sort_key)


def select_latest_entries(
    entries: list[dict[str, Any]],
    n: int = LATEST_N,
) -> list[dict[str, Any]]:
    """Top-N by priority, with every distinct expert-skill row pinned in.

    Same-title skill domains (config/project/python/typescript) are distinct
    by id/content and must not be title-deduped or truncated out of the window.
    """
    ranked = sorted(entries, key=_rank_key, reverse=True)
    skills = collect_expert_skill_entries(entries)
    skill_ids = {str(e.get("id") or "") for e in skills}

    # Always surface all distinct skill rows (contract over cap), then fill to n
    # unique ids from non-skill ranked entries. Memory may contain duplicate ids
    # (mirrored path noise); collapse to first ranked occurrence.
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _push(e: dict[str, Any]) -> None:
        eid = str(e.get("id") or "")
        if not eid or eid in seen:
            return
        ordered.append(e)
        seen.add(eid)

    for e in skills:
        _push(e)

    if not skills:
        for e in ranked:
            _push(e)
            if len(ordered) >= n:
                break
        return ordered

    for e in ranked:
        eid = str(e.get("id") or "")
        if eid in skill_ids:
            continue
        _push(e)
        # Fill only up to n once skills are reserved; if skills alone exceed n,
        # keep every skill (len may be > n).
        if len(ordered) >= max(n, len(skills)):
            break

    # Re-order by rank while preserving membership
    selected_ids = set(seen)
    reordered: list[dict[str, Any]] = []
    re_seen: set[str] = set()
    for e in ranked:
        eid = str(e.get("id") or "")
        if eid not in selected_ids or eid in re_seen:
            continue
        reordered.append(e)
        re_seen.add(eid)
    for e in skills:
        eid = str(e.get("id") or "")
        if eid and eid not in re_seen:
            reordered.append(e)
            re_seen.add(eid)
    return reordered


def build_index(
    entries: list[dict[str, Any]],
    project: dict[str, Any] | None,
) -> dict[str, Any]:
    by_kind = dict(Counter(str(e.get("kind") or "unknown") for e in entries))
    skill_entries = collect_expert_skill_entries(entries)
    latest_src = select_latest_entries(entries, LATEST_N)
    latest = [latest_entry_row(e) for e in latest_src]
    skill_rules = [skill_rule_row(e) for e in skill_entries]
    return {
        "v": 1,
        "project": project
        or {
            "key": "",
            "name": "",
            "rootPath": str(REPO_ROOT),
            "canonical": "",
            "createdAt": "",
            "updatedAt": "",
        },
        "updatedAt": utc_now_iso(),
        "totalEntries": len(entries),
        "byKind": by_kind,
        "latestEntries": latest,
        # Explicit skill surface — consumers should prefer this over title-matching
        # latestEntries when resolving config/project/python/typescript rulebooks.
        "skillRules": skill_rules,
    }


def _is_session_history_heading(line: str) -> bool:
    """True only for list/heading rows that *title* a What Was Done entry.

    Avoid bare content lines (the body also starts with "What Was Done"), which
    would otherwise rewrite the *next* entry's Kind: metadata.
    """
    stripped = line.lstrip()
    # "8. What Was Done (.agent-mem/last-session.md)"
    if re.match(r"^\d+\.\s+What Was Done\b", stripped):
        return True
    # "- What Was Done (...)" / "* What Was Done"
    if re.match(r"^[-*]\s+What Was Done\b", stripped):
        return True
    # Markdown headings
    if re.match(r"^#{1,6}\s+What Was Done\b", stripped):
        return True
    # Last Session Summary (same family)
    if re.match(r"^\d+\.\s+Last Session Summary\b", stripped):
        return True
    if re.match(r"^[-*]\s+Last Session Summary\b", stripped):
        return True
    if re.match(r"^#{1,6}\s+Last Session Summary\b", stripped):
        return True
    return False


def patch_context_kind_labels(root: Path = REPO_ROOT) -> int:
    """Fix 'Kind: rule' → 'Kind: note' for What Was Done blocks in generated md."""
    changed_files = 0
    targets: list[Path] = []
    for pattern in CONTEXT_GLOBS:
        if "**" in pattern:
            base, _, _ = pattern.partition("/**")
            base_path = root / base
            if base_path.is_dir():
                targets.extend(p for p in base_path.rglob("*.md") if p.is_file())
        else:
            p = root / pattern
            if p.is_file():
                targets.append(p)

    # de-dupe
    seen: set[Path] = set()
    for path in targets:
        if path in seen:
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        lines = text.splitlines(keepends=True)
        new_lines: list[str] = []
        i = 0
        file_changed = False
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            if _is_session_history_heading(line):
                j = i + 1
                while j < len(lines) and j <= i + 4:
                    if lines[j].lstrip().startswith("Kind:"):
                        old = lines[j]
                        patched = old
                        for wrong in ("rule", "decision", "lesson"):
                            patched = patched.replace(f"Kind: {wrong}", "Kind: note", 1)
                            if patched != old:
                                break
                        if patched != old:
                            new_lines.append(patched)
                            file_changed = True
                            i = j  # skip original kind line (i+=1 below)
                        break
                    j += 1
            i += 1

        if file_changed:
            path.write_text("".join(new_lines), encoding="utf-8")
            changed_files += 1
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            print(f"patched context: {rel}")
    return changed_files


def cmd_check(args: argparse.Namespace) -> int:
    memory = Path(args.memory).resolve() if args.memory else DEFAULT_MEMORY
    entries = load_jsonl(memory)
    bad = violations(entries)
    by_kind = Counter(str(e.get("kind") or "unknown") for e in entries)
    wwd = [e for e in entries if is_session_history_title(e.get("title") if isinstance(e.get("title"), str) else None)]
    wwd_kinds = Counter(str(e.get("kind") or "unknown") for e in wwd)

    skills = collect_expert_skill_entries(entries)
    skill_domains = sorted(
        {
            d
            for e in skills
            if (
                d := extract_skill_domain(
                    e.get("content") if isinstance(e.get("content"), str) else ""
                )
            )
        }
    )

    print(f"memory: {memory}")
    print(f"entries: {len(entries)} byKind={dict(by_kind)}")
    print(f"session-history titles: {len(wwd)} kinds={dict(wwd_kinds)}")
    print(
        f"expert-skill entries: {len(skills)} "
        f"domains={skill_domains or ['(header-only or none)']}"
    )

    if bad:
        print(f"FAIL: {len(bad)} session-history entry(ies) not kind=note:", file=sys.stderr)
        for b in bad[:20]:
            print(f"  id={b['id']} kind={b['kind']} priority={b['priority']} title={b['title']}", file=sys.stderr)
        print(
            "\nFix:\n  python3 helix/automations/brainsync_kind_normalize.py apply",
            file=sys.stderr,
        )
        return 1

    # index consistency if present
    index_path = Path(args.index).resolve() if args.index else DEFAULT_INDEX
    if index_path.is_file():
        try:
            idx = json.loads(index_path.read_text(encoding="utf-8"), strict=False)
        except json.JSONDecodeError as exc:
            print(
                f"FAIL: index.json is not valid JSON ({exc}). Rebuild with apply.",
                file=sys.stderr,
            )
            return 1
        expected = dict(Counter(str(e.get("kind") or "unknown") for e in entries))
        actual = idx.get("byKind") or {}
        if dict(actual) != expected:
            print(
                f"FAIL: index byKind mismatch\n  index={actual}\n  memory={expected}",
                file=sys.stderr,
            )
            return 1
        if int(idx.get("totalEntries") or -1) != len(entries):
            print(
                f"FAIL: index totalEntries={idx.get('totalEntries')} memory={len(entries)}",
                file=sys.stderr,
            )
            return 1
        # No What Was Done as rule in latestEntries
        for le in idx.get("latestEntries") or []:
            if is_session_history_title(le.get("title") if isinstance(le.get("title"), str) else None):
                if le.get("kind") != "note":
                    print(
                        f"FAIL: latestEntries has session history as kind={le.get('kind')}: {le.get('id')}",
                        file=sys.stderr,
                    )
                    return 1

        # Distinct expert skills must remain addressable (no title-collapse).
        skill_ids_mem = {str(e.get("id") or "") for e in skills if e.get("id")}
        latest = idx.get("latestEntries") or []
        latest_ids = {str(le.get("id") or "") for le in latest}
        missing_latest = sorted(skill_ids_mem - latest_ids)
        if missing_latest:
            print(
                "FAIL: expert skill id(s) missing from latestEntries "
                f"(title-collapse or top-N truncation?): {missing_latest}",
                file=sys.stderr,
            )
            return 1

        skill_rules = idx.get("skillRules")
        if skill_rules is None:
            print(
                "FAIL: index missing skillRules[] — consumers need the explicit skill surface. "
                "Rebuild with apply.",
                file=sys.stderr,
            )
            return 1
        skill_rule_ids = {str(r.get("id") or "") for r in skill_rules if r.get("id")}
        if skill_rule_ids != skill_ids_mem:
            print(
                "FAIL: skillRules ids do not match memory expert skills\n"
                f"  index={sorted(skill_rule_ids)}\n  memory={sorted(skill_ids_mem)}",
                file=sys.stderr,
            )
            return 1
        # Domain rows must keep distinct domains (config/project/python/typescript).
        domains_idx = sorted(
            {str(r.get("domain")) for r in skill_rules if r.get("domain")}
        )
        if domains_idx != skill_domains:
            print(
                "FAIL: skillRules domains mismatch\n"
                f"  index={domains_idx}\n  memory={skill_domains}",
                file=sys.stderr,
            )
            return 1

    print(
        "brainsync_kind_normalize: OK — kinds consistent; "
        f"expert skills preserved ({len(skills)} in latestEntries + skillRules)"
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    memory = Path(args.memory).resolve() if args.memory else DEFAULT_MEMORY
    index_path = Path(args.index).resolve() if args.index else DEFAULT_INDEX
    project_path = Path(args.project).resolve() if args.project else DEFAULT_PROJECT

    entries = load_jsonl(memory)
    normalized, n_changed = normalize_entries(entries)
    write_jsonl(memory, normalized)

    project = None
    if project_path.is_file():
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            project = None

    index = build_index(normalized, project)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ctx_n = 0
    if not args.skip_context:
        ctx_n = patch_context_kind_labels(REPO_ROOT)

    by_kind = index["byKind"]
    n_skills = len(index.get("skillRules") or [])
    print(
        f"brainsync_kind_normalize: apply done — "
        f"entries={len(normalized)} changed={n_changed} "
        f"byKind={by_kind} skillRules={n_skills} "
        f"latestEntries={len(index.get('latestEntries') or [])} "
        f"context_files={ctx_n}"
    )
    # re-check
    args.memory = str(memory)
    args.index = str(index_path)
    return cmd_check(args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--memory", help="Path to memory.jsonl")
    common.add_argument("--index", help="Path to index.json")
    common.add_argument("--project", help="Path to project.json")

    p_check = sub.add_parser("check", parents=[common], help="Fail if kinds inconsistent")
    p_check.set_defaults(func=cmd_check)

    p_apply = sub.add_parser("apply", parents=[common], help="Normalize kinds + rebuild index")
    p_apply.add_argument(
        "--skip-context",
        action="store_true",
        help="Do not patch Kind: labels in generated markdown consumers",
    )
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
