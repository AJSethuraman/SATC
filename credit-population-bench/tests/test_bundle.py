"""Seam 3 — the pure-ASCII bundle rebuilds the workbook in an empty folder.

Proves the emailable transmission path (TEMPLATE_CONTRACT.md §11): the bundle is
pure ASCII, and running it in a fresh directory with only pandas + openpyxl on
the path reproduces the demo workbook byte-identically to the in-process build,
with the shared core vendored inside (no external import).
"""

import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent.parent


def test_bundle_is_pure_ascii():
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_bundle", _HERE / "make_bundle.py")
    mb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mb)
    script = mb.make_bundle()
    script.encode("ascii")   # raises if any non-ASCII byte slipped in
    assert "_PAYLOAD" in script and "build_demo_bytes" in script


def test_bundle_rebuilds_workbook_byte_identical(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_bundle", _HERE / "make_bundle.py")
    mb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mb)

    builder = tmp_path / "build_population_bench.py"
    builder.write_text(mb.make_bundle(), encoding="ascii")

    # Run it in an empty cwd with a CLEAN sys.path (no repo packages leaking in)
    # so it must rely on its own vendored sources + pandas/openpyxl only.
    proc = subprocess.run(
        [sys.executable, str(builder)],
        cwd=tmp_path, capture_output=True, text=True,
        env={"PYTHONPATH": "", "PATH": __import__("os").environ.get("PATH", "")},
    )
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / "population_bench_demo.xlsx"
    assert out.exists()
    for extra in ("runner.py", "requirements.txt", "macro.bas"):
        assert (tmp_path / extra).exists()

    # Byte-identical to the in-process demo build.
    from popbench.cli import build_demo_bytes
    assert out.read_bytes() == build_demo_bytes()


@pytest.mark.parametrize("name", ["macro.bas", "runner.py", "requirements.txt"])
def test_bundle_emits_ascii_sidecars(tmp_path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_bundle", _HERE / "make_bundle.py")
    mb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mb)
    builder = tmp_path / "build_population_bench.py"
    builder.write_text(mb.make_bundle(), encoding="ascii")
    subprocess.run([sys.executable, str(builder)], cwd=tmp_path,
                   capture_output=True, text=True,
                   env={"PYTHONPATH": "", "PATH": __import__("os").environ.get("PATH", "")})
    (tmp_path / name).read_text(encoding="ascii")   # raises if non-ASCII
