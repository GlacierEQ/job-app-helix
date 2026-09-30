#!/usr/bin/env python3
"""Proof: kind normalize + expert skill index preservation.

Covers:
  1. What Was Done session history → kind=note; index byKind matches.
  2. Distinct Comprehensive Expert Skills rows (same title, different content)
     are never title-collapsed — all appear in latestEntries and skillRules.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "helix" / "automations" / "brainsync_kind_normalize.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True)


def main() -> int:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mem = root / "memory.jsonl"
        idx = root / "index.json"
        proj = root / "project.json"
        proj.write_text(
            json.dumps(
                {
                    "key": "test",
                    "name": "test",
                    "rootPath": str(root),
                    "reference": "",
                    "createdAt": "2026-01-01T00:00:00.000Z",
                    "updatedAt": "2026-01-01T00:00:00.000Z",
                }
            ),
            encoding="utf-8",
        )
        # Seed mixed kinds + distinct same-title expert skills at low priority
        # so a naive top-N rank would drop domain rows without pinning.
        skill_title = "📚 Comprehensive Expert Skills (READ THESE)"
        rows = [
            {
                "id": "a1",
                "kind": "rule",
                "title": "What Was Done",
                "content": "What Was Done\nGit Commit: foo",
                "source": ".agent-mem/last-session.md",
                "createdAt": "2026-07-27T06:26:00.791Z",
                "updatedAt": "2026-07-27T06:26:00.791Z",
                "priority": 5,
                "projectPath": str(root),
            },
            {
                "id": "a2",
                "kind": "note",
                "title": "What Was Done",
                "content": "What Was Done\nGit Commit: bar",
                "source": ".agent-mem/last-session.md",
                "createdAt": "2026-07-27T06:26:00.800Z",
                "updatedAt": "2026-07-27T06:26:00.800Z",
                "priority": 2,
                "projectPath": str(root),
            },
            {
                "id": "b1",
                "kind": "rule",
                "title": "🔴 CRITICAL — DO NOT IGNORE",
                "content": "real rule",
                "source": ".windsurfrules",
                "createdAt": "2026-07-25T12:44:28.095Z",
                "updatedAt": "2026-07-25T12:44:28.095Z",
                "priority": 8,
                "projectPath": str(root),
            },
            # Header + 4 domain skills (same title/source/time; distinct content/id)
            {
                "id": "skill-header",
                "kind": "rule",
                "title": skill_title,
                "content": (
                    f"{skill_title}\n"
                    "> **CRITICAL:** read SKILL.md for each domain"
                ),
                "source": ".brainsync/agent-rules.md",
                "createdAt": "2026-07-25T20:05:38.837Z",
                "updatedAt": "2026-07-25T20:05:38.837Z",
                "priority": 8,
                "projectPath": str(root),
            },
            {
                "id": "skill-config",
                "kind": "rule",
                "title": skill_title,
                "content": f"{skill_title}\n**config**: Read `.agent/skills/auto/config/SKILL.md`",
                "source": ".brainsync/agent-rules.md",
                "createdAt": "2026-07-25T20:05:38.837Z",
                "updatedAt": "2026-07-25T20:05:38.837Z",
                "priority": 5,
                "projectPath": str(root),
            },
            {
                "id": "skill-project",
                "kind": "rule",
                "title": skill_title,
                "content": (
                    f"{skill_title}\n"
                    "**project**: Read `.agent/skills/auto/project/SKILL.md`"
                ),
                "source": ".brainsync/agent-rules.md",
                "createdAt": "2026-07-25T20:05:38.837Z",
                "updatedAt": "2026-07-25T20:05:38.837Z",
                "priority": 5,
                "projectPath": str(root),
            },
            {
                "id": "skill-python",
                "kind": "rule",
                "title": skill_title,
                "content": f"{skill_title}\n**python**: Read `.agent/skills/auto/python/SKILL.md`",
                "source": ".brainsync/agent-rules.md",
                "createdAt": "2026-07-25T20:05:38.837Z",
                "updatedAt": "2026-07-25T20:05:38.837Z",
                "priority": 5,
                "projectPath": str(root),
            },
            {
                "id": "skill-typescript",
                "kind": "rule",
                "title": skill_title,
                "content": (
                    f"{skill_title}\n"
                    "**typescript**: Read `.agent/skills/auto/typescript/SKILL.md`"
                ),
                "source": ".brainsync/agent-rules.md",
                "createdAt": "2026-07-25T20:05:38.837Z",
                "updatedAt": "2026-07-25T20:05:38.837Z",
                "priority": 5,
                "projectPath": str(root),
            },
        ]
        # Flood priority-5 noise so domain skills would fall outside LATEST_N=20
        # without pinning (header alone would remain via priority 8).
        for i in range(25):
            rows.append(
                {
                    "id": f"noise-{i}",
                    "kind": "rule",
                    "title": f"Noise rule {i}",
                    "content": f"noise {i}",
                    "source": "noise.md",
                    "createdAt": f"2026-07-26T12:00:{i:02d}.000Z",
                    "updatedAt": f"2026-07-26T12:00:{i:02d}.000Z",
                    "priority": 5,
                    "projectPath": str(root),
                }
            )

        mem.write_text(
            "\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n",
            encoding="utf-8",
        )

        # check should fail before apply (What Was Done as rule)
        r = _run([sys.executable, str(SCRIPT), "check", "--memory", str(mem), "--index", str(idx)])
        assert r.returncode != 0, "check should fail on mixed kinds"

        r = _run(
            [
                sys.executable,
                str(SCRIPT),
                "apply",
                "--memory",
                str(mem),
                "--index",
                str(idx),
                "--project",
                str(proj),
                "--skip-context",
            ]
        )
        assert r.returncode == 0, r.stdout + r.stderr

        entries = [
            json.loads(ln)
            for ln in mem.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        wwd = [e for e in entries if e.get("title") == "What Was Done"]
        assert len(wwd) == 2
        assert all(e["kind"] == "note" for e in wwd), wwd
        # elevated rule priority clamped
        a1 = next(e for e in wwd if e["id"] == "a1")
        assert a1["priority"] == 2, a1

        # real rules untouched
        crit = next(e for e in entries if e["id"] == "b1")
        assert crit["kind"] == "rule" and crit["priority"] == 8

        index = json.loads(idx.read_text(encoding="utf-8"))
        from collections import Counter

        expected = dict(Counter(e["kind"] for e in entries))
        assert index["byKind"] == expected, (index["byKind"], expected)
        assert index["totalEntries"] == len(entries)
        for le in index["latestEntries"]:
            if le.get("title") == "What Was Done":
                assert le["kind"] == "note"

        # --- Expert skill preservation (the regression this audit fixes) ---
        skill_ids = {
            "skill-header",
            "skill-config",
            "skill-project",
            "skill-python",
            "skill-typescript",
        }
        latest_ids = {le["id"] for le in index["latestEntries"]}
        missing = skill_ids - latest_ids
        assert not missing, f"skill ids missing from latestEntries: {missing}"

        assert "skillRules" in index, "index must expose skillRules for consumers"
        rule_ids = {r["id"] for r in index["skillRules"]}
        assert rule_ids == skill_ids, (rule_ids, skill_ids)

        domains = {r.get("domain") for r in index["skillRules"] if r.get("domain")}
        assert domains == {"config", "project", "python", "typescript"}, domains

        by_domain = {r["domain"]: r for r in index["skillRules"] if r.get("domain")}
        assert by_domain["config"]["skillPath"] == ".agent/skills/auto/config/SKILL.md"
        assert by_domain["python"]["role"] == "domain"
        headers = [r for r in index["skillRules"] if r.get("role") == "header"]
        assert len(headers) == 1 and headers[0]["id"] == "skill-header"

        # Titles in index must be single-line (no raw newlines that break JSON)
        for le in index["latestEntries"]:
            title = le.get("title")
            if isinstance(title, str):
                assert "\n" not in title and "\r" not in title, title

        r = _run([sys.executable, str(SCRIPT), "check", "--memory", str(mem), "--index", str(idx)])
        assert r.returncode == 0, r.stdout + r.stderr

    print(
        "PROOF_OK brainsync_kind_normalize "
        "What Was Done → note + skillRules preserve config/project/python/typescript"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
