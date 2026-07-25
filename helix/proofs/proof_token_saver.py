#!/usr/bin/env python3
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/token_saver/src"))
from pure_pointer import externalize
body = "x" * 50000
with tempfile.TemporaryDirectory() as d:
    ptr = externalize(body, Path(d), "ctx")
    assert ptr.bytes_out < ptr.bytes_in
    assert ptr.savings_pct > 90
    assert Path(ptr.path).exists()
print("PROOF_OK token_saver savings", round(ptr.savings_pct, 1))
