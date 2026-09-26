"""The checker that checks the checker (tools/mutation_check.py) must never let
a planted bug outlive its own run.

Found 26 Sep 2026: a clean checkout read one test red. Python validates a
cached .pyc against the source's size and its mtime in whole seconds; a
mutation that keeps the file's size ("< 2" -> "< 1"), written and then
restored inside the same second, left the mutant's bytecode in __pycache__,
and the next run executed it."""

import importlib.util
import os
import py_compile
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "mutation_check.py"


def _tool():
    spec = importlib.util.spec_from_file_location("mutation_check", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)              # the loop is behind a main guard, so importing runs nothing
    return mod


def _answer(d: Path) -> str:
    out = subprocess.run([sys.executable, "-c", "import m; print(m.f())"], cwd=d, capture_output=True, text=True,
                         env={k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"})
    return out.stdout.strip()


def test_a_same_size_mutant_restored_within_a_second_leaves_no_bytecode(tmp_path):
    tool = _tool()
    src = tmp_path / "m.py"
    good, bad = "def f():\n    return 1 < 2\n", "def f():\n    return 1 < 1\n"      # the same size
    src.write_text(good)
    st = src.stat()
    # the trap, built by hand: the mutant's bytecode, stamped with the restored file's own second and size
    src.write_text(bad)
    os.utime(src, (st.st_atime, st.st_mtime))
    py_compile.compile(str(src), cfile=importlib.util.cache_from_source(str(src)))
    src.write_text(good)
    os.utime(src, (st.st_atime, st.st_mtime))
    assert _answer(tmp_path) == "False"       # Python serves the mutant: this is what the checker must prevent
    tool._drop_cache(str(src))
    assert _answer(tmp_path) == "True"


def test_the_checker_never_writes_bytecode_from_a_mutant():
    tool = _tool()
    assert tool.ENV.get("PYTHONDONTWRITEBYTECODE") == "1"
    text = TOOL.read_text()
    assert text.count("_drop_cache(f)") == 2 and "env=ENV" in text
