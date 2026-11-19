"""Portable estate path resolution.

Every root is derived from the installed package location or from the process
working directory, and every root can be overridden with an environment
variable. Modules in this package must not hardcode machine-specific absolute
paths.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

MONOLITH_DIR_NAME = "monolith"
TOWER_DIR_NAME = "the-tower-of-babel"


def _resolve_repo_root() -> Path:
    candidate = PACKAGE_DIR.parents[1]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    return Path.cwd().resolve()


def _overridden(env_var: str, default: Path) -> Path:
    raw = os.environ.get(env_var)
    return Path(raw).expanduser() if raw else default


def helix_root() -> Path:
    return _overridden("JOB_APP_HELIX_ROOT", _resolve_repo_root())


def estate_root() -> Path:
    return _overridden("ESTATE_ROOT", helix_root().parent)


def monolith_root() -> Path:
    return _overridden("MONOLITH_ROOT", estate_root() / MONOLITH_DIR_NAME)


def tower_root() -> Path:
    return _overridden("TOWER_ROOT", estate_root() / TOWER_DIR_NAME)


def legal_spines_path() -> Path:
    return _overridden("LEGAL_SPINES_PATH", monolith_root() / "catalog" / "legal_spines")
