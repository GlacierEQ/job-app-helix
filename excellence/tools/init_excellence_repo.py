#!/usr/bin/env python3
"""Scaffold an excellence-grade company repo (contract + src + tests + ceiling).

Usage:
  python3 init_excellence_repo.py --name my-repo --company palantir \\
      --title "Ontology Fence" --pain "Silent writebacks without lineage"
"""
from __future__ import annotations

import argparse
from pathlib import Path

CEILING = """## Claim ceiling (independent reference)

Independent GlacierEQ reference only. No company affiliation, employment, deployment,
endorsement, or proprietary access is claimed. Names label public problem spaces.
"""

TEMPLATE_SRC = '''"""{title} — excellence seed.

Fail closed. Emit receipts. No magic numbers without names.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


def digest(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Receipt:
    ok: bool
    reason: str | None
    payload: dict

    def fingerprint(self) -> str:
        return digest({{"ok": self.ok, "reason": self.reason, "payload": self.payload}})


def run(example_input: dict) -> Receipt:
    """Replace with real domain logic."""
    if not example_input:
        return Receipt(False, "EMPTY_INPUT", {{}})
    return Receipt(True, None, {{"echo": example_input}})
'''

TEMPLATE_TEST = '''from __future__ import annotations

import unittest

from src.core import run


class CoreTests(unittest.TestCase):
    def test_empty_refuses(self) -> None:
        r = run({})
        self.assertFalse(r.ok)

    def test_happy(self) -> None:
        r = run({"x": 1})
        self.assertTrue(r.ok)
        self.assertEqual(len(r.fingerprint()), 64)


if __name__ == "__main__":
    unittest.main()
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--pain", required=True)
    ap.add_argument("--root", default=str(Path.home() / "job-app" / "repos"))
    args = ap.parse_args()
    root = Path(args.root) / args.name
    if root.exists():
        print("exists:", root)
        return 1
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "src" / "__init__.py").write_text(f'"""{args.title}."""\n')
    (root / "src" / "core.py").write_text(TEMPLATE_SRC.format(title=args.title))
    (root / "tests" / "test_core.py").write_text(TEMPLATE_TEST)
    (root / "ISSUE_CONTRACT.md").write_text(
        f"# ISSUE CONTRACT\n\n## Company lens\n{args.company}\n\n## Pain\n{args.pain}\n\n"
        "## Success\n- Fail closed\n- Receipt fingerprint\n- Tests green\n"
    )
    (root / "README.md").write_text(
        f"# {args.title}\n\n**Company lens:** {args.company}\n\n**Pain:** {args.pain}\n\n"
        f"{CEILING}\n\n```bash\npython3 -m unittest discover -s tests -v\n```\n"
    )
    print("created", root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
