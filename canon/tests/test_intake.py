"""Taking findings off a branch, and taking nothing else.

THE PROPERTY THESE TESTS EXIST TO HOLD is the one that makes an adversarial
pass safe to run at all: exactly one path crosses over, and everything else on
the branch — including a rewritten source module — is never read and cannot
land. A rule somebody follows would hold until the first busy day. This is the
check that it is not a rule.

THE FIXTURE IS A REAL BRANCH IN A REAL REPOSITORY, built the way the far side
would build one: a findings file plus the scratch it was told it may write.
Feeding `take()` a hand-made result would prove the reporter agrees with itself
and would never exercise the checkout, which is where the whole guarantee lives.
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
    out = subprocess.run(["git", "-C", str(repo), *args],
                         capture_output=True, text=True, check=True)
    return out.stdout


@pytest.fixture
def elsewhere(tmp_path, monkeypatch):
    """A repository with a main branch and an adversarial branch off it."""
    repo = tmp_path / "somewhere"
    (repo / "canon" / "findings").mkdir(parents=True)
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    (repo / "canon" / "record.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@e.com", "-c", "user.name=T",
         "commit", "-q", "-m", "main")
    _git(repo, "branch", "-q", "origin/main")      # stand-in for the remote ref

    _git(repo, "checkout", "-q", "-b", "codex/pass")
    (repo / "canon" / "findings" / "test_findings.py").write_text(
        REPRODUCES, encoding="utf-8")
    (repo / "canon" / "scratch_harness.py").write_text(SCRATCH, encoding="utf-8")
    (repo / "canon" / "record.py").write_text("VALUE = 999  # rewritten\n",
                                              encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=t@e.com", "-c", "user.name=T",
         "commit", "-q", "-m", "findings plus scratch")
    _git(repo, "checkout", "-q", "main")

    monkeypatch.setattr(I, "HERE", repo / "canon")
    monkeypatch.setattr(I, "LANDS_AT",
                        repo / "canon" / "findings" / "test_findings.py")
    def run_here(*args):
        out = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True)
        if out.returncode != 0:
            raise I.IntakeError(out.stderr.strip()[:300] or " ".join(args))
        return out.stdout

    monkeypatch.setattr(I, "_git", run_here)
    return repo


# ── only one path crosses ─────────────────────────────────────────────────

def test_a_rewritten_source_file_on_the_branch_does_not_land(elsewhere):
    """The guarantee. The branch rewrote `record.py`; taking the findings must
    leave the working tree's copy exactly as it was.

    This is why the far side can be told to write whatever code it needs: the
    branch is a sandbox, not a contribution, and that is a property of this
    script rather than a promise it extracted from anybody.
    """
    before = (elsewhere / "canon" / "record.py").read_text(encoding="utf-8")
    I.take("codex/pass", base="origin/main")
    after = (elsewhere / "canon" / "record.py").read_text(encoding="utf-8")
    assert after == before == "VALUE = 1\n"


def test_the_scratch_the_far_side_wrote_does_not_land(elsewhere):
    I.take("codex/pass", base="origin/main")
    assert not (elsewhere / "canon" / "scratch_harness.py").exists()


def test_the_path_that_crosses_is_fixed_rather_than_chosen():
    """Hardcoded, not an argument — an argument is a thing somebody widens in a
    hurry, and the first time it is widened is the time nobody checks what came
    with it. Named here so widening it is a deliberate act with a red test."""
    assert I.FINDINGS == "canon/findings/test_findings.py"
    import inspect
    assert "def take(branch: str, base: str = \"origin/main\")" in \
        inspect.getsource(I.take), "take() grew a path argument"


# ── what it reports ───────────────────────────────────────────────────────

def test_a_red_test_is_a_finding_and_a_green_one_is_not(elsewhere):
    got = I.take("codex/pass", base="origin/main")
    assert got.findings == 1
    assert got.not_findings == 1
    assert got.examined == 2


def test_what_else_the_branch_touched_is_listed_but_never_read(elsewhere):
    """Visibility, not prevention. What a branch did outside its lane says
    whether to trust it with a bigger job — it is not itself a danger."""
    got = I.take("codex/pass", base="origin/main")
    assert "canon/scratch_harness.py" in got.ignored
    assert "canon/record.py" in got.ignored
    assert I.FINDINGS not in got.ignored
    said = got.say()
    assert "NOT taken" in said and "canon/record.py" in said


def test_an_empty_findings_file_says_so_in_words(elsewhere):
    """S2. `0 findings` reads as a clean bill of health; `the file held no
    tests` is a different fact, and only one means what a reader takes it to."""
    path = elsewhere / "canon" / "findings" / "test_findings.py"
    _git(elsewhere, "checkout", "-q", "codex/pass")
    path.write_text("# nothing here\n", encoding="utf-8")
    _git(elsewhere, "add", "-A")
    _git(elsewhere, "-c", "user.email=t@e.com", "-c", "user.name=T",
         "commit", "-q", "-m", "empty")
    _git(elsewhere, "checkout", "-q", "main")

    got = I.take("codex/pass", base="origin/main")
    assert got.examined == 0
    assert "held no tests at all" in got.say()
    assert "not the same as nothing being wrong" in got.say()


def test_a_branch_with_no_findings_file_is_refused_with_a_reason(elsewhere):
    """Not a crash and not an empty result — either would read as 'the pass
    found nothing' when what happened is that it delivered nowhere."""
    _git(elsewhere, "branch", "-q", "codex/empty", "main")
    with pytest.raises(I.IntakeError, match="carries no"):
        I.take("codex/empty", base="origin/main")


# ── the findings stay out of the suite ────────────────────────────────────

def test_the_findings_directory_is_not_collected_by_the_suite():
    """A red test in `tests/` would make the suite red, and every later run
    would report a failure that is a finding rather than a regression. After
    two days nobody reads either."""
    assert I.LANDS_AT.parent.name == "findings"
    assert I.LANDS_AT.parent != CANON / "tests"
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=CANON, capture_output=True, text=True)
    assert "findings/" not in collected.stdout


def test_the_intake_never_writes_to_the_record():
    source = (CANON / "intake.py").read_text(encoding="utf-8")
    assert "write_text" not in source
    assert "CONVICTIONS" not in source and "TENETS" not in source
