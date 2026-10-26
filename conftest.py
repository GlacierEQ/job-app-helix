"""Pytest bootstrap: make the repository root importable.

One test module imports the legacy implementation as
``scripts.legacy.apex_distributed_compute``. That import resolves only when
the repository root is on ``sys.path``. ``python -m pytest`` puts the working
directory on ``sys.path`` implicitly, but the bare ``pytest`` entry point
used by CI does not, so collection failed there with
``ModuleNotFoundError: No module named 'scripts'``. Inserting the root here
makes both launchers behave the same.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
