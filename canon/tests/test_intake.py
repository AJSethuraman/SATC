"""Taking findings off a branch, and taking nothing else.

THE PROPERTY THESE TESTS EXIST TO HOLD is the one that makes an adversarial
pass safe to run at all: exactly one path crosses over, and everything else on
the branch — including a rewritten source module — is never read and cannot
land. A rule somebody follows would hold until the first busy day. This is the
check that it is not a rule.

THE FIXTURE IS A REAL BRANCH IN A REAL REPOSITORY, built the way the far side
would build one: a findings file plus the scratch it was told it may write, on
a branch reached through a REMOTE, because a fresh clone that has never seen
that branch locally is the workflow this script is for and was the one it got
wrong.

FIVE OF THESE EXIST BECAUSE THE FIRST VERSION SHIPPED THEM ALL. An adversarial
review of the pull request that introduced this script found every one, which
is either an embarrassment or the argument for the mechanism, and it is
recorded here as both. Each has a test named for what it does rather than for
the bug, so the tests read as behaviour and the incident stays in the docstring.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import intake as I  # noqa: E402


REPRODUCES = '''
def test_this_one_is_a_finding():
    """Asserts something the code does not do."""
    assert 1 == 2


def test_this_one_is_not():
    """Asserts something the code already does."""
    assert 1 == 1
'''

SCRATCH = "# the far side's own harness, which must never cross\nBROKEN = True\n"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@e.com", "-c", "user.name=T",
         "commit", "-q", "-m", message)


@pytest.fixture
def elsewhere(tmp_path):
    """A bare 'remote' with the adversarial branch, and a clone that has never
    seen it — which is the situation the script is actually used in."""
    upstream = tmp_path / "upstream"
    (upstream / "canon").mkdir(parents=True)
    _git(tmp_path, "init", "-q", "-b", "main", str(upstream))
    (upstream / "canon" / "record.py").write_text("VALUE = 1\n", encoding="utf-8")
    _commit(upstream, "main")

    _git(upstream, "checkout", "-q", "-b", "codex/pass")
    (upstream / "canon" / "findings").mkdir(parents=True, exist_ok=True)
    (upstream / "canon" / "findings" / "test_findings.py").write_text(
        REPRODUCES, encoding="utf-8")
    (upstream / "canon" / "scratch_harness.py").write_text(SCRATCH, encoding="utf-8")
    (upstream / "canon" / "record.py").write_text("VALUE = 999  # rewritten\n",
                                                  encoding="utf-8")
    _commit(upstream, "findings plus scratch")
    _git(upstream, "checkout", "-q", "main")

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--single-branch", "--branch", "main",
         str(upstream), str(clone))
    return clone


def _take(clone: Path, branch: str = "codex/pass") -> I.Result:
    return I.take(branch, base="origin/main", root=clone)


# ── the repository is the one you are standing in ─────────────────────────

def test_the_repository_is_found_from_the_working_directory(elsewhere):
    """Not from this file's location. Installed as a plugin the script lives
    in a versioned cache directory that is not a repository at all, and the
    skill documents running it from exactly there — so deriving the repo from
    the script's own path made the documented invocation fail outright."""
    assert I.repo_root(elsewhere) == elsewhere
    assert I.repo_root(elsewhere / "canon") == elsewhere


def test_somewhere_that_is_not_a_repository_says_so(tmp_path):
    with pytest.raises(I.IntakeError, match="not inside a git repository"):
        I.repo_root(tmp_path)


# ── a branch that exists only on the remote ───────────────────────────────

def test_a_branch_the_clone_has_never_seen_is_taken(elsewhere):
    """The primary workflow, and the one the first version rejected. `git
    fetch origin <branch>` alone writes only FETCH_HEAD, so the plain name
    resolved to nothing and every delivery made the normal way was refused."""
    assert "codex/pass" not in _git(elsewhere, "branch", "--list")
    got = _take(elsewhere)
    assert got.examined == 2


def test_a_branch_that_exists_nowhere_is_refused_by_name(elsewhere):
    with pytest.raises(I.IntakeError, match="no branch named"):
        _take(elsewhere, "codex/never-pushed")


# ── only one path crosses, and it is not staged ───────────────────────────

def test_a_rewritten_source_file_on_the_branch_does_not_land(elsewhere):
    """The guarantee. The branch rewrote `record.py`; taking the findings must
    leave the working tree's copy exactly as it was.

    This is why the far side can be told to write whatever code it needs: the
    branch is a sandbox, not a contribution, and that is a property of this
    script rather than a promise extracted from anybody."""
    before = (elsewhere / "canon" / "record.py").read_text(encoding="utf-8")
    _take(elsewhere)
    assert (elsewhere / "canon" / "record.py").read_text(encoding="utf-8") \
        == before == "VALUE = 1\n"


def test_the_scratch_the_far_side_wrote_does_not_land(elsewhere):
    _take(elsewhere)
    assert not (elsewhere / "canon" / "scratch_harness.py").exists()


def test_the_findings_file_is_not_left_staged(elsewhere):
    """`git checkout <ref> -- <path>` updates the index as well as the working
    tree, so the supposedly ephemeral, gitignored findings file was left as a
    staged addition and would have gone into the next commit without anybody
    adding it. Writing the blob out directly cannot stage anything."""
    got = _take(elsewhere)
    assert got.landed_at.is_file()
    staged = _git(elsewhere, "diff", "--cached", "--name-only")
    assert staged.strip() == "", f"the intake staged something: {staged!r}"


def test_the_path_that_crosses_is_fixed_rather_than_chosen():
    """Hardcoded, not an argument — an argument is a thing somebody widens in a
    hurry, and the first time it is widened is the time nobody checks what came
    with it."""
    assert I.FINDINGS == "canon/findings/test_findings.py"
    import inspect
    assert "path" not in inspect.signature(I.take).parameters, \
        "take() grew a path argument"


# ── a runner that never ran must not report a result ──────────────────────

def test_a_pytest_that_could_not_run_is_not_an_empty_result(elsewhere, monkeypatch):
    """With the return code ignored, a missing pytest produced no summary,
    every count read zero, and the script said the file held no tests — which
    reads as a clean pass over an empty delivery. It is neither."""
    real = subprocess.run

    def broken(cmd, *a, **kw):
        # MATCH THE INVOCATION, NOT THE STRING. Written as "pytest in str(c)"
        # this caught every git call too, because pytest's own tmp_path is
        # under a directory called `pytest-of-root` -- and the test then failed
        # for a reason that had nothing to do with what it was testing.
        if list(cmd[1:3]) == ["-m", "pytest"]:
            return subprocess.CompletedProcess(cmd, 4, "", "No module named pytest")
        return real(cmd, *a, **kw)

    monkeypatch.setattr(subprocess, "run", broken)
    with pytest.raises(I.IntakeError, match="without producing a result"):
        _take(elsewhere)


def test_the_exit_codes_that_are_results_are_named():
    """0 all passed, 1 some failed, 5 nothing collected. Everything else means
    pytest did not get far enough to have an answer."""
    assert I.RAN == {0, 1, 5}


# ── what it reports ───────────────────────────────────────────────────────

def test_a_red_test_is_a_finding_and_a_green_one_is_not(elsewhere):
    got = _take(elsewhere)
    assert got.findings == 1 and got.not_findings == 1 and got.examined == 2


def test_the_count_comes_from_the_summary_line_not_the_whole_output():
    """A failing test whose assertion message contained "99 passed" was counted
    as ninety-nine passing tests. The summary is the line pytest writes as its
    answer; everything above it is working."""
    noisy = ("F\n=== FAILURES ===\n"
             "E   AssertionError: the report claimed 99 passed, 4 failed\n"
             "=== short test summary info ===\n"
             "1 failed, 2 passed in 0.31s\n")
    assert I._tally(noisy, "passed") == 2
    assert I._tally(noisy, "failed") == 1


def test_what_else_the_branch_touched_is_listed_but_never_read(elsewhere):
    """Visibility, not prevention. What a branch did outside its lane says
    whether to trust it with a bigger job — it is not itself a danger."""
    got = _take(elsewhere)
    assert "canon/scratch_harness.py" in got.ignored
    assert "canon/record.py" in got.ignored
    assert I.FINDINGS not in got.ignored
    assert "NOT taken" in got.say() and "canon/record.py" in got.say()


def test_an_empty_findings_file_says_so_in_words(elsewhere):
    """S2. `0 findings` reads as a clean bill of health; `the file held no
    tests` is a different fact, and only one means what a reader takes it to."""
    upstream = elsewhere.parent / "upstream"
    _git(upstream, "checkout", "-q", "codex/pass")
    (upstream / "canon" / "findings" / "test_findings.py").write_text(
        "# nothing here\n", encoding="utf-8")
    _commit(upstream, "empty")
    _git(upstream, "checkout", "-q", "main")

    got = _take(elsewhere)
    assert got.examined == 0
    assert "held no tests at all" in got.say()
    assert "not the same as nothing being wrong" in got.say()


def test_a_branch_with_no_findings_file_is_refused_with_a_reason(elsewhere):
    """Not a crash and not an empty result — either would read as 'the pass
    found nothing' when what happened is that it delivered nowhere."""
    upstream = elsewhere.parent / "upstream"
    _git(upstream, "branch", "-q", "codex/bare", "main")
    with pytest.raises(I.IntakeError, match="carries no"):
        _take(elsewhere, "codex/bare")


# ── the findings stay out of the suite ────────────────────────────────────

def test_the_findings_directory_is_not_collected_by_the_suite():
    """A red test in `tests/` would make the suite red, and every later run
    would report a failure that is a finding rather than a regression. After
    two days nobody reads either."""
    assert I.FINDINGS.split("/")[1] == "findings"
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=CANON, capture_output=True, text=True)
    assert "findings/" not in collected.stdout


def test_the_intake_writes_only_the_findings_file():
    """It writes one file, and that file is the one that crosses."""
    source = (CANON / "intake.py").read_text(encoding="utf-8")
    assert source.count("write_text") == 1
    assert "lands_at.write_text" in source
    assert "CONVICTIONS" not in source and "TENETS" not in source
