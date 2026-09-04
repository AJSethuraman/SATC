"""canon, installed in a repository that has nothing to do with SATC.

WHY THIS FILE EXISTS. The README claims canon "installs itself into every
project" and that no import, path or assumption reaches outside `canon/`. Until
this ran, that was a design claim and nothing compared it to the code — which is
the one bug shape this repository is about (S31). A claim about portability is
exactly the kind that stays true right up until the day somebody needs it.

WHAT IT ACTUALLY DOES, rather than approximates. It copies the tree into a
fresh git repository in a temporary directory, with a different name, no SATC
parent, no shared virtualenv path and no inherited `sys.path`, and runs the
record, the challenge, the miner and the adopter there as a SUBPROCESS with
`cwd` set to that copy. Importing the already-imported modules would prove
nothing: they are resolved from this checkout and would keep working from a
directory that had been deleted.

WHAT IT DOES NOT PROVE, said plainly. That a Claude Code harness elsewhere
loads the plugin. Nothing here reaches a harness. It proves the record loads,
the challenge fires, the guards hold and the tests pass with no SATC anywhere
above them — which is the half that is this repository's to keep true.

The other half WAS observed by hand on 4 September 2026 and is not covered
here: canon installed from a marketplace at user scope, and a session started
in an unrelated git repository saw `canon:bassy`, `canon:how-we-work`,
`canon:canon-mine` and `canon:canon-adopt`, read `CONVICTIONS.md`, and
challenged a push-to-main by quoting C2 back verbatim. Observed once, by a
person, is a weaker thing than a test, and it is recorded as such.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]

# Everything that is not the record itself. A copy carrying `.git` would be a
# checkout of SATC wearing another name, which is the failure this is about.
LEAVE_BEHIND = {".git", "__pycache__", ".pytest_cache"}


def _install(into: Path) -> Path:
    """Copy canon into a fresh repository with no relationship to SATC."""
    home = into / "unrelated-project"
    home.mkdir(parents=True)
    subprocess.run(["git", "-C", str(home), "init", "-q", "-b", "main"], check=True)
    (home / "README.md").write_text("# unrelated-project\n\nNothing to do with "
                                    "accounting.\n", encoding="utf-8")

    plugin = home / "vendor" / "canon"
    shutil.copytree(CANON, plugin,
                    ignore=shutil.ignore_patterns(*LEAVE_BEHIND))
    assert not (plugin / ".git").exists(), "the copy carried SATC's history"
    subprocess.run(["git", "-C", str(home), "add", "-A"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(home), "-c", "user.email=t@example.com",
                    "-c", "user.name=T", "commit", "-q", "-m",
                    "Adopt canon"], check=True, capture_output=True)
    return plugin


def _run(plugin: Path, code: str) -> subprocess.CompletedProcess:
    """Run code inside the installed copy, with nothing of this checkout on
    the path. `-I` isolates: no user site-packages, no inherited PYTHONPATH,
    no cwd surprises beyond the one we set deliberately."""
    return subprocess.run([sys.executable, "-I", "-c", code], cwd=plugin,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(plugin)})


@pytest.fixture(scope="module")
def installed(tmp_path_factory) -> Path:
    return _install(tmp_path_factory.mktemp("elsewhere"))


def test_the_record_loads_with_no_satc_anywhere_above_it(installed):
    got = _run(installed, "import sys; sys.path.insert(0, '.');"
                          "import record;"
                          "c, t = record.load();"
                          "print(len(c), len(t))")
    assert got.returncode == 0, got.stderr
    convictions, tenets = got.stdout.split()
    assert int(tenets) == 35 and int(convictions) >= 2


def test_no_path_in_the_copy_points_back_at_this_checkout(installed):
    """A single absolute path back to the original checkout would make the copy
    a puppet of it, and nothing would notice until the original moved.

    The path is built rather than written here on purpose: spelled out as a
    literal, this docstring is itself copied into the installation and the test
    catches its own prose. That is the check working, and it is still a useless
    finding to hand somebody.
    """
    home_of = str(CANON.parent)
    for path in sorted(installed.rglob("*")):
        if not path.is_file() or any(p in LEAVE_BEHIND for p in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert str(CANON) not in text, f"{path.name} points back at the original"
        assert home_of not in text, \
            f"{path.name} carries an absolute path to the original's parent"


def test_the_challenge_fires_where_it_was_installed(installed):
    """The whole mechanism, exercised somewhere else: a decision that touches a
    conviction produces one, quoting the firm."""
    got = _run(installed, "import sys; sys.path.insert(0, '.');"
                          "import record, challenge;"
                          "c, _ = record.load();"
                          "d = challenge.Decision(what='push this straight to main');"
                          "found = challenge.candidates(c, d);"
                          "print(challenge.report(found, challenge.conflicts(found)))")
    assert got.returncode == 0, got.stderr
    assert "C2" in got.stdout
    assert "Never push to main" in got.stdout, "it did not quote the firm"


def test_silence_still_falls_out_where_it_was_installed(installed):
    got = _run(installed, "import sys; sys.path.insert(0, '.');"
                          "import record, challenge;"
                          "c, _ = record.load();"
                          "d = challenge.Decision(what='rename a local variable');"
                          "found = challenge.candidates(c, d);"
                          "print(repr(challenge.report(found, [])))")
    assert got.returncode == 0, got.stderr
    assert got.stdout.strip() == "''", "it spoke about a decision touching nothing"


def test_the_guards_still_refuse_where_it_was_installed(installed):
    """Portability that carried the code but not the refusals would be worse
    than none: an installed copy that records without a yes is a copy that
    quietly does the one thing the record exists to prevent."""
    got = _run(installed, "import sys; sys.path.insert(0, '.');"
                          "import record;"
                          "c, _ = record.load();"
                          "\ntry:\n"
                          "    record.add(c, c[0], confirmed=False)\n"
                          "    print('WROTE WITHOUT A YES')\n"
                          "except record.RecordError as e:\n"
                          "    print('refused')")
    assert got.returncode == 0, got.stderr
    assert got.stdout.strip() == "refused"


def test_the_no_client_data_check_runs_where_it_was_installed(installed):
    got = _run(installed, "import sys; sys.path.insert(0, '.');"
                          "import check_record; raise SystemExit(check_record.main())")
    assert got.returncode == 0, got.stdout + got.stderr
    assert "Nothing that must not be here" in got.stdout
    assert "file(s)" in got.stdout, "it reported no denominator"


def test_adoption_reads_the_host_repository_it_was_installed_into(installed):
    """The point of installing: canon reads the project it now lives in."""
    got = _run(installed, "import sys; sys.path.insert(0, '.');"
                          "import adopt;"
                          "r = adopt.read_repo('..');"
                          "print(r.project, len(r.commits))")
    assert got.returncode == 0, got.stderr
    project, commits = got.stdout.split()
    assert project == "unrelated-project", "it adopted the wrong repository"
    assert int(commits) == 1


def test_the_whole_suite_passes_where_it_was_installed(installed):
    """The strongest form of the claim, and the slowest — so it is one test
    rather than a fixture every other test pays for."""
    got = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests",
                          "--ignore=tests/test_installed_elsewhere.py"],
                         cwd=installed, capture_output=True, text=True)
    assert got.returncode == 0, got.stdout[-3000:]
    assert " passed" in got.stdout
