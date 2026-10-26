#!/usr/bin/env python3
"""cover.py — cover letter renderer for the resume-forge document family.

Same design system as the resumes (theme.py), same honesty contract:
the engine FAILS CLOSED on unapproved numbers. Any **bold** number in the
letter that isn't in the candidate's kit_numbers allowlist raises instead
of rendering. Add a number to kit_numbers only when he approves it.

Usage:
  python3 cover.py --letter scale-ai-fde        # -> out/Cover_Letter_ScaleAI_FDE.docx
  python3 cover.py --letter scale-ai-fde --pdf

Content: content/cover/<name>.yaml (see scale-ai-fde.yaml for the schema).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from theme import (BODY_SIZE, INK, MUTED, SMALL_SIZE, _para, add_header,
                   add_runs, setup_page)

HERE = Path(__file__).resolve().parent
CONTENT_DIR = HERE / "content"
COVER_DIR = CONTENT_DIR / "cover"
OUT_DIR = HERE / "out"

NUM_RE = re.compile(r"[\d,]+(?:/[\d,]+)?\+?")


class HonestyError(ValueError):
    """Raised when a letter claims a number outside the approved kit."""


def honesty_gate(text: str, kit_numbers: list[str], where: str) -> None:
    """Fail closed: every **bold** number must be on the allowlist."""
    for span in re.findall(r"\*\*(.+?)\*\*", text):
        for num in NUM_RE.findall(span):
            if num not in kit_numbers:
                raise HonestyError(
                    f"[{where}] unapproved number '{num}' in bold span "
                    f"'**{span}**' — add it to kit_numbers in _candidate.yaml "
                    f"only with his approval, or drop the bold."
                )


def load_letter(name: str) -> dict:
    data = yaml.safe_load((COVER_DIR / f"{name}.yaml").read_text())
    base_name = data.get("base", "_candidate.yaml")
    candidate = yaml.safe_load((CONTENT_DIR / base_name).read_text())
    return data, candidate


def build(name: str) -> Path:
    data, candidate = load_letter(name)
    kit = candidate["kit_numbers"]
    full_text = "\n".join(data["paragraphs"] + [data.get("fit", "")])
    honesty_gate(full_text, kit, name)

    doc = Document()
    setup_page(doc)

    header_data = {"name": candidate["name"], "contact": candidate["contact"]}
    add_header(doc, header_data)

    # Date
    dp = _para(doc, space_before=2, space_after=8)
    add_runs(dp, data["date"], size=SMALL_SIZE, color=MUTED)

    # Recipient block
    for line in data["target"]["block"]:
        rp = _para(doc, space_after=1)
        add_runs(rp, line, size=BODY_SIZE)

    # Salutation
    sp = _para(doc, space_before=8, space_after=6)
    add_runs(sp, data["salutation"], size=BODY_SIZE)

    # Body
    for para in data["paragraphs"]:
        bp = _para(doc, space_after=7)
        add_runs(bp, para, size=BODY_SIZE)

    # Closing + signature
    cp = _para(doc, space_before=6, space_after=2)
    add_runs(cp, data["closing"], size=BODY_SIZE)
    sig = _para(doc, space_after=1)
    add_runs(sig, candidate["name"], size=BODY_SIZE, bold=True)
    for line in candidate["contact"]:
        cl = _para(doc, space_after=0)
        add_runs(cl, line, size=SMALL_SIZE, color=MUTED)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{data['output']}.docx"
    doc.save(out)
    return out


def to_pdf(docx_path: Path) -> Path:
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf",
         "--outdir", str(OUT_DIR), str(docx_path)],
        check=True, capture_output=True, text=True)
    return docx_path.with_suffix(".pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--letter", required=True)
    ap.add_argument("--pdf", action="store_true")
    args = ap.parse_args()

    out = build(args.letter)
    print(f"DOCX: {out}")
    if args.pdf:
        print(f"PDF:  {to_pdf(out)}")


if __name__ == "__main__":
    sys.exit(main())
