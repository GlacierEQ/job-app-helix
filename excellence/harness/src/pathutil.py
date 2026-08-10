"""Add excellence repo src dirs to sys.path."""
from __future__ import annotations
import sys
from pathlib import Path

REPOS = Path.home() / "job-app" / "repos"

def add_repo(name: str) -> Path:
    src = REPOS / name / "src"
    if not src.is_dir():
        raise FileNotFoundError(src)
    p = str(src.resolve())
    if p not in sys.path:
        sys.path.insert(0, p)
    return src
