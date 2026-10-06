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
    src.write_text(good, encoding="utf-8")
    st = src.stat()
    # the trap, built by hand: the mutant's bytecode, stamped with the restored file's own second and size
    src.write_text(bad, encoding="utf-8")
    os.utime(src, (st.st_atime, st.st_mtime))
    py_compile.compile(str(src), cfile=importlib.util.cache_from_source(str(src)))
    src.write_text(good, encoding="utf-8")
    os.utime(src, (st.st_atime, st.st_mtime))
    assert _answer(tmp_path) == "False"       # Python serves the mutant: this is what the checker must prevent
    tool._drop_cache(str(src))
    assert _answer(tmp_path) == "True"


def test_the_checker_never_writes_bytecode_from_a_mutant():
    tool = _tool()
    assert tool.ENV.get("PYTHONDONTWRITEBYTECODE") == "1"
    text = TOOL.read_text(encoding="utf-8")
    assert text.count("_drop_cache(f)") == 2 and "env=ENV" in text


def test_every_planted_bug_still_finds_the_line_it_plants_into(monkeypatch):
    """Found 26 Sep 2026: a fix rewrote a line one mutation planted into, and CI's mutation run died on its
    assert sixty mutations in, with the other hundred never run. A stranded entry reads red here instead."""
    monkeypatch.chdir(TOOL.parents[1])
    tool = _tool()
    stranded = [n for n, f, old, _new, _sel in tool.muts if Path(f).read_text(encoding="utf-8").count(old) != 1]
    assert stranded == []
    assert len({n for n, *_ in tool.muts}) > 150


def test_the_ci_shards_put_back_every_bug_exactly_once():
    """CI splits the planted bugs over four jobs so none runs into GitHub's time limit; together they
    must still put every bug back, and none twice."""
    tool = _tool()
    names = [m[0] for m in tool.muts]
    got = [m[0] for k in range(4) for m in tool.shard(tool.muts, f"{k}/4")]
    assert sorted(got) == sorted(names) and len(got) == len(names)
    assert tool.shard(tool.muts, None) == tool.muts


def test_a_run_that_prints_nothing_still_gets_its_verdict(tmp_path, monkeypatch, capsys):
    """Found 26 Sep 2026: pytest printed nothing to stdout (the run was killed), main() crashed on an empty
    list, and the crash hid whether the planted bug had been caught. The verdict prints, with stderr's last line.
    Since review on 29 Sep 2026 that verdict is NOT CHECKED: a killed run shows no test failing on the bug."""
    tool = _tool()
    f = tmp_path / "m.py"
    f.write_text("x = 1\n", encoding="utf-8")
    tool.muts = [("a bug", str(f), "x = 1", "x = 2", "anything")]

    class Silent:
        returncode, stdout, stderr = 1, "", "Killed\n"
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: Silent())
    assert tool.main() == 1
    assert "NOT CHECKED a bug | Killed" in capsys.readouterr().out
    assert f.read_text(encoding="utf-8") == "x = 1\n"                      # and the file is put back


# Found in review, 29 Sep 2026: the checker counted any pytest exit but 0 or 5 as CAUGHT. On a machine where pytest
# could not write its temp folder, every tmp_path test ERRORED, and every planted bug those tests guard read as
# caught though no test had failed on it.

def test_only_a_failed_test_is_a_catch():
    v = _tool().verdict
    assert v(1, "1 failed, 3 passed, 440 deselected in 2.10s") == "CAUGHT"
    assert v(1, "2 failed, 1 error in 0.50s") == "CAUGHT"
    assert v(0, "4 passed, 440 deselected in 1.00s") == "MISSED"
    assert v(0, "1 passed, 2 skipped, 440 deselected in 1.00s") == "MISSED"
    assert v(0, "1 skipped, 821 deselected in 9.19s") == "NOT CHECKED"   # LibreOffice absent: nothing ran
    assert v(1, "4 errors in 0.30s") == "ERRORS"                     # settled by a run without the bug
    assert v(2, "1 error in 0.20s") == "ERRORS"                      # a collection error
    assert v(5, "440 deselected in 0.10s") == "NOT CHECKED"          # the selector matched nothing
    assert v(1, "Killed") == "NOT CHECKED"
    assert v(3, "INTERNALERROR> boom") == "NOT CHECKED"
    assert v(4, "ERROR: usage") == "NOT CHECKED"


def _runs(tool, monkeypatch, answers):
    """pytest faked: each call gets the next (exit code, stdout), and records whether the bug was in the file."""
    seen = []

    def run(*a, **k):
        code, out = answers[len(seen)]
        seen.append(Path(tool.muts[0][1]).read_text(encoding="utf-8"))

        class R:
            returncode, stdout, stderr = code, out, ""
        return R()
    monkeypatch.setattr(tool.subprocess, "run", run)
    return seen


def test_errors_that_the_file_without_the_bug_also_gives_are_not_a_catch(tmp_path, monkeypatch, capsys):
    tool = _tool()
    f = tmp_path / "m.py"
    f.write_text("x = 1\n", encoding="utf-8")
    tool.muts = [("a bug", str(f), "x = 1", "x = 2", "anything")]
    seen = _runs(tool, monkeypatch, [(1, "3 errors in 0.40s"), (1, "3 errors in 0.40s")])   # WinError 5 both times
    assert tool.main() == 1
    assert capsys.readouterr().out.startswith("NOT CHECKED a bug | 3 errors")
    assert seen == ["x = 2\n", "x = 1\n"]                   # the second run was on the file as it is


def test_errors_only_the_bug_causes_are_a_catch(tmp_path, monkeypatch, capsys):
    tool = _tool()
    f = tmp_path / "m.py"
    f.write_text("x = 1\n", encoding="utf-8")
    tool.muts = [("a bug", str(f), "x = 1", "x = 2", "anything")]
    _runs(tool, monkeypatch, [(2, "1 error in 0.20s"), (0, "3 passed in 0.40s")])
    assert tool.main() == 0
    assert capsys.readouterr().out.startswith("CAUGHT a bug | 1 error")


def test_a_run_aimed_at_some_files_puts_back_only_theirs_and_refuses_a_file_with_none():
    tool = _tool()
    got = tool.only(tool.muts, ["src/pocketbook/kgroups.py"])
    assert got and all(m[1] == "src/pocketbook/kgroups.py" for m in got)
    assert len(got) == sum(m[1] == "src/pocketbook/kgroups.py" for m in tool.muts)
    import pytest
    with pytest.raises(SystemExit, match="no planted bug is in src/pocketbook/nothing.py"):
        tool.only(tool.muts, ["src/pocketbook/nothing.py"])
