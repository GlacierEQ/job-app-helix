"""Add excellence repo src dirs to sys.path."""
from __future__ import annotations

import os
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("AGENT_WORKSPACE", Path.home() / "Workspace")).expanduser()


def _resolve_repos() -> Path:
    """Canonical estate root first; the retired ``~/job-app/repos`` second."""
    override = os.environ.get("ELITE_REPOS")
    if override:
        return Path(override).expanduser()
    for candidate in (WORKSPACE / "job-app" / "repos", WORKSPACE / "projects", WORKSPACE):
        if candidate.is_dir():
            return candidate
    return WORKSPACE / "job-app" / "repos"


REPOS = _resolve_repos()

def add_repo(name: str) -> Path:
    src = REPOS / name / "src"
    if not src.is_dir():
        raise FileNotFoundError(src)
    p = str(src.resolve())
    if p not in sys.path:
        sys.path.insert(0, p)
    return src
