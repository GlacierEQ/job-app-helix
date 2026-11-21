"""Single source of truth for the package version.

The installed distribution metadata is authoritative; a source checkout falls
back to the repository ``pyproject.toml``. No module hardcodes a second
version literal.
"""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

DISTRIBUTION = "job-app-helix"
UNKNOWN = "0.0.0+unknown"


def _from_pyproject() -> str | None:
    path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not path.is_file():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if isinstance(version, str) and version:
        return version
    return None


def detect_version() -> str:
    try:
        return importlib.metadata.version(DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return _from_pyproject() or UNKNOWN


__version__ = detect_version()
