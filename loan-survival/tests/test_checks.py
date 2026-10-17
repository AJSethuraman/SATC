"""pytest front door for the two check scripts, so CI runs them with the rest of the repo.

A skipped window check is not a passed one: when CI is set, a SKIP line fails the test.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _run(script, wrap=()):
    r = subprocess.run([*wrap, sys.executable, str(HERE / script)], capture_output=True, text=True, timeout=1500)
    return r, r.stdout + r.stderr


def test_validate_math():
    r, out = _run("validate.py")
    assert r.returncode == 0 and "ALL PASSED" in out, out[-2000:]


def test_gui_check():
    wrap = ()
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        wrap = ("xvfb-run", "-a")
    r, out = _run("gui_check.py", wrap)
    assert r.returncode == 0 and "ALL PASSED" in out, out[-2000:]
    if os.environ.get("CI"):
        assert "[SKIP]" not in out, "the window part did not run in CI:\n" + out[-1000:]
