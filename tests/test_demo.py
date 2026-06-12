import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytest.importorskip("mcp", reason="demo requires the mcp SDK (pip install -e '.[demo]')")


def test_launch_demo_runs_end_to_end():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "demo" / "run_demo.py")],
        capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VALID" in proc.stdout
    assert "INVALID" in proc.stdout  # the tampered copies must fail
    assert "deny-unapproved-payments" in proc.stdout
