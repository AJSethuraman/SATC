"""The add-ons (OC-34): what is missing, installing it, and what the window and
`cube` do meanwhile. Nothing is really installed: the look-up and pip are faked.

These live apart from test_launcher.py because that file imports the workbook
code, which needs the add-ons; everything here must run without them."""

import importlib.machinery
import importlib.metadata
import importlib.util
import os
import site
import subprocess
import sys
import time
from pathlib import Path

import pytest

from origination_cube import cli, deps, launcher

SRC = str(Path(__file__).resolve().parents[1] / "src")
REAL_FIND = importlib.util.find_spec
PROXY = ("WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection "
         "broken by 'ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 407 Proxy "
         "Authentication Required'))': /simple/numpy/\n"
         "ERROR: Could not find a version that satisfies the requirement numpy (from versions: none)\n"
         "ERROR: No matching distribution found for numpy\n")


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch, tmp_path):
    """No test here may touch the real sys.path or the real per-account folder."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(site, "getusersitepackages", lambda: str(tmp_path / "user-site"))


def only_missing(monkeypatch, *mods):
    """find_spec as if exactly these add-ons were absent and the rest present,
    whatever this machine has. Returns the set, so a fake pip can 'install' them."""
    gone = set(mods)
    ours = {mod for mod, _ in deps.NEEDED.values()}

    def fake(name, *a, **k):
        if name in gone:
            return None
        if name in ours:
            return importlib.machinery.ModuleSpec(name, None)
        return REAL_FIND(name, *a, **k)
    monkeypatch.setattr(importlib.util, "find_spec", fake)
    return gone


def fake_pip(monkeypatch, rc, said, then=None):
    """pip exits with `rc` and says `said`; `then()` is what it did (an add-on appearing, say)."""
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        if then:
            then()
        return subprocess.CompletedProcess(argv, rc, stdout=said, stderr="")
    monkeypatch.setattr(subprocess, "run", run)
    return calls


def fresh(code):
    """Run `code` in a new Python, so nothing this test process imported counts."""
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": SRC})


# ---- what is missing -------------------------------------------------------

def test_missing_names_each_add_on_by_its_pip_name(monkeypatch):
    only_missing(monkeypatch, "yaml")
    assert deps.missing() == ["PyYAML"]
    only_missing(monkeypatch, "numpy", "openpyxl", "yaml")
    assert deps.missing() == ["numpy", "openpyxl", "PyYAML"]
    only_missing(monkeypatch)
    assert deps.missing() == []


def test_the_launcher_opens_without_the_add_ons():
    """Blocked outright, the launcher still imports, says all three are missing, and keeps Run off."""
    r = fresh("import sys\n"
              "for m in ('numpy', 'openpyxl', 'yaml'): sys.modules[m] = None\n"
              "from origination_cube import launcher\n"
              "g = launcher.AddOns()\n"
              "print(g.missing, g.states()['setup'], g.states()['run'])")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "['numpy', 'openpyxl', 'PyYAML'] disabled disabled"


def test_checking_loads_none_of_them():
    r = fresh("import sys\n"
              "from origination_cube import launcher\n"
              "launcher.AddOns()\n"
              "print([m for m in ('numpy', 'openpyxl', 'yaml') if m in sys.modules])")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[]"


def test_too_old_counts_as_missing_and_says_so(monkeypatch):
    only_missing(monkeypatch)
    have = importlib.metadata.version("openpyxl")
    monkeypatch.setattr(deps, "minimums", lambda: {"openpyxl": "99.0"})
    assert deps.missing() == ["openpyxl"]
    assert f"the copy here is {have} and it needs 99.0 or later" in deps.message(["openpyxl"])


def test_every_add_on_the_project_declares_is_checked():
    text = (Path(SRC).parent / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("dependencies = [", 1)[1].split("]", 1)[0]
    declared = {line.split('"')[1].split(">")[0].split("=")[0].strip()
                for line in block.splitlines() if '"' in line}
    assert declared and declared <= set(deps.NEEDED)
    assert deps.minimums()["openpyxl"] == "3.1" and deps.minimums()["PyYAML"] == "6.0"


def test_the_line_says_what_is_missing_and_what_for(monkeypatch):
    only_missing(monkeypatch, "numpy")
    assert deps.message(["numpy"]) == ("The cube needs an add-on this computer doesn't have yet: "
                                       "numpy (for the statistics).")
    two = deps.message(["numpy", "openpyxl"])
    assert two.startswith("The cube needs add-ons") and "numpy (for the statistics) and openpyxl (" in two


# ---- installing ------------------------------------------------------------

def test_install_runs_pip_for_this_python(monkeypatch):
    gone = only_missing(monkeypatch, "numpy")
    calls = fake_pip(monkeypatch, 0, "Successfully installed numpy-2.1.0\n", then=gone.clear)
    ok, said = deps.install(["numpy"])
    assert ok and "Successfully installed" in said
    argv = calls[0]
    assert argv[:4] == [deps.python_exe(), "-m", "pip", "install"] and argv[-2:] == ["--upgrade", "numpy"]
    assert ("--user" in argv) == deps._per_user()
    assert "--no-input" in argv            # a proxy asking for a password can't hang it


def test_install_is_only_ok_when_the_check_after_finds_everything(monkeypatch):
    """pip said it worked, but numpy still can't be found: that is not ok."""
    only_missing(monkeypatch, "numpy")
    fake_pip(monkeypatch, 0, "Successfully installed numpy-2.1.0\n")
    ok, said = deps.install(["numpy"])
    assert not ok and "still can't find numpy" in said


def test_a_blocked_install_comes_back_as_words(monkeypatch):
    only_missing(monkeypatch, "numpy")
    fake_pip(monkeypatch, 1, PROXY)
    ok, said = deps.install(["numpy"])
    assert not ok and "407 Proxy Authentication Required" in said


def test_install_never_raises(monkeypatch):
    only_missing(monkeypatch, "numpy")

    def cannot_start(argv, **kw):
        raise FileNotFoundError(2, "No such file or directory", argv[0])
    monkeypatch.setattr(subprocess, "run", cannot_start)
    ok, said = deps.install(["numpy"])
    assert not ok and said.startswith("The installer couldn't start")

    def hangs(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw["timeout"])
    monkeypatch.setattr(subprocess, "run", hangs)
    ok, said = deps.install(["numpy"], timeout=120)
    assert not ok and said.startswith("The installer was still going after 2 minutes")


def test_a_first_install_is_seen_without_a_restart(monkeypatch, tmp_path):
    """The first per-account install creates the folder it lands in, which Python
    only looks in if it was there at start-up. The window must look there itself."""
    user = tmp_path / "user-site"
    monkeypatch.setattr(site, "ENABLE_USER_SITE", True)

    def fake(name, *a, **k):
        if name == "numpy":
            return importlib.machinery.ModuleSpec(name, None) if str(user) in sys.path else None
        if name in ("openpyxl", "yaml"):
            return importlib.machinery.ModuleSpec(name, None)
        return REAL_FIND(name, *a, **k)
    monkeypatch.setattr(importlib.util, "find_spec", fake)
    fake_pip(monkeypatch, 0, "Successfully installed numpy-2.1.0\n", then=lambda: user.mkdir())
    assert deps.missing() == ["numpy"]
    assert deps.install(["numpy"])[0] and str(user) in sys.path


def test_the_note_for_it_names_the_python_and_the_add_ons(monkeypatch, tmp_path):
    note = deps.ask_it(["numpy", "openpyxl", "PyYAML"])
    assert note.startswith(f"Please install these Python add-ons for {deps.python_exe()}")
    assert ": numpy, openpyxl, PyYAML." in note
    assert note.endswith(deps.command_text(["numpy", "openpyxl", "PyYAML"]))
    assert "-m pip install" in note and "numpy openpyxl PyYAML" in note
    assert deps.ask_it(["numpy"]).startswith("Please install this Python add-on for ")
    # Double-clicked, the launcher runs under pythonw.exe, which prints nothing: IT gets python.exe.
    folder = tmp_path / "Python 312"
    folder.mkdir()
    (folder / "python.exe").write_text("")
    monkeypatch.setattr(sys, "executable", str(folder / "pythonw.exe"))
    assert deps.python_exe() == str(folder / "python.exe")
    assert deps.command_text(["numpy"]).startswith(f'"{folder / "python.exe"}" -m pip install')


# ---- the window, without the window -----------------------------------------

def test_set_up_and_run_wait_while_an_add_on_is_missing(monkeypatch):
    gone = only_missing(monkeypatch, "numpy")
    gate = launcher.AddOns()
    assert gate.states() == {"setup": "disabled", "run": "disabled", "open": "normal", "install": "normal"}
    assert gate.headline() == deps.message(["numpy"])
    names = gate.start()
    assert names == ["numpy"] and gate.states()["install"] == "disabled" and gate.states()["run"] == "disabled"
    assert gate.lines()[0].startswith("Installing numpy... 0:0")
    fake_pip(monkeypatch, 0, "Successfully installed numpy-2.1.0\n", then=gone.clear)
    gate.finish(*deps.install(names))
    assert gate.states() == {"setup": "normal", "run": "normal", "open": "normal", "install": "disabled"}
    assert gate.headline() == ""
    assert gate.lines()[0] == "Installed numpy. Everything the cube needs is here."
    assert gate.lines()[2:] == launcher.START


def test_a_failed_install_shows_pip_and_the_note_for_it(monkeypatch):
    only_missing(monkeypatch, "numpy")
    gate = launcher.AddOns()
    fake_pip(monkeypatch, 1, PROXY)
    gate.finish(*deps.install(gate.start()))
    assert gate.states()["run"] == "disabled" and gate.states()["install"] == "normal"   # it can be tried again
    assert gate.headline() == ("Couldn't install numpy from here. "
                               "Press Copy for IT and send them the note below.")
    lines = gate.lines()
    assert lines[0] == deps.ask_it(["numpy"])
    assert "What the installer said last:" in lines
    assert lines[-1].strip() == "ERROR: No matching distribution found for numpy"
    assert any("407 Proxy Authentication Required" in ln for ln in lines)


def test_nothing_missing_is_the_usual_window(monkeypatch):
    only_missing(monkeypatch)
    gate = launcher.AddOns()
    assert gate.states()["run"] == "normal" and gate.headline() == "" and gate.lines() == launcher.START


# ---- the command line ------------------------------------------------------

def test_cube_says_what_is_missing_and_stops(monkeypatch, capsys, tmp_path):
    only_missing(monkeypatch, "numpy")
    assert cli.main(["synth", "--out", str(tmp_path / "x")]) == 2
    err = capsys.readouterr().err
    assert deps.message(["numpy"]) in err and deps.command_text(["numpy"]) in err
    assert not (tmp_path / "x").exists()


def test_cube_without_an_add_on_is_not_a_traceback(tmp_path):
    r = fresh("import sys\n"
              "sys.modules['yaml'] = None\n"
              "from origination_cube import cli\n"
              f"sys.exit(cli.main(['synth', '--out', {str(tmp_path / 'x')!r}]))")
    assert r.returncode == 2 and "Traceback" not in r.stderr
    assert "PyYAML (for its settings files)" in r.stderr and "-m pip install" in r.stderr


# ---- the real window, where there is a display --------------------------------

def _window():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display to open a window on")
    root.withdraw()
    return root


def _wait(root, gate):
    for _ in range(100):
        root.update()
        if not gate.installing:
            return
        time.sleep(0.05)
    raise AssertionError("the install never finished")


def test_the_window_keeps_run_off_until_the_install_works(monkeypatch, tmp_path):
    root = _window()
    try:
        monkeypatch.setattr(launcher, "PREFS", tmp_path / "launcher.json")
        gone = only_missing(monkeypatch, "numpy")
        w = launcher.build(root)
        root.update()
        assert str(w["run"].cget("state")) == "disabled" and str(w["setup"].cget("state")) == "disabled"
        assert w["headline"].cget("text") == deps.message(["numpy"])
        assert w["copy"].winfo_manager() == ""           # nothing to copy until an install fails
        fake_pip(monkeypatch, 1, PROXY)
        w["install"].invoke()
        _wait(root, w["gate"])
        assert str(w["run"].cget("state")) == "disabled" and w["copy"].winfo_manager() == "pack"
        assert str(w["install"].cget("text")) == "Try again"
        w["copy"].invoke()
        assert root.clipboard_get() == deps.ask_it(["numpy"])
        fake_pip(monkeypatch, 0, "Successfully installed numpy-2.1.0\n", then=gone.clear)
        w["install"].invoke()
        _wait(root, w["gate"])
        assert str(w["run"].cget("state")) == "normal" and str(w["setup"].cget("state")) == "normal"
        assert w["headline"].master.winfo_manager() == ""   # the add-on row is gone
        assert w["status"].get("1.0", "end").startswith("Installed numpy.")
    finally:
        root.destroy()
