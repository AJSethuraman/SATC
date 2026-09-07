"""Adopting a repository canon has never seen.

WHAT THESE TESTS HOLD:

  - the reading says how much history it could NOT see, not just what it read
  - a candidate's rule text is the commit's own subject, never a generalisation
  - the pinned tier is a fact about a commit; the guessed tier is labelled
  - an identity card CANNOT grow a file inventory, a count, a status or a
    "currently" — one test per drift shape, and a card that grows one goes red
  - adoption writes nothing

THE FIXTURE IS A REAL GIT REPOSITORY, built commit by commit the way a person
builds one. A fixture that fed hand-made `Commit` objects to the reader would
prove the parser agrees with itself and would have missed the record-separator
bug that blew up on the first real repo this was pointed at.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import adopt as A  # noqa: E402
import record as R  # noqa: E402


def _run(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def _commit(repo: Path, subject: str, files: dict[str, str]) -> None:
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    _run(repo, "add", "-A")
    _run(repo, "-c", "user.email=t@example.com", "-c", "user.name=T",
         "commit", "-m", subject)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A small repository with one of each shape of commit."""
    r = tmp_path / "widget-monitor"
    r.mkdir()
    _run(r, "init", "-q", "-b", "main")

    _commit(r, "Add the widget monitor", {
        "README.md": "# widget-monitor\n\nWatches widgets.\n",
        "widget.py": "def count():\n    return 0\n"})
    # pinned: a test and a source file in the same commit
    _commit(r, "A widget with no readings counted as zero", {
        "widget.py": "def count():\n    return None\n",
        "tests/test_widget.py": "def test_none():\n    assert True\n"})
    # guessed: a fix-word in the subject, no test alongside
    _commit(r, "Fix the stale cache header", {
        "widget.py": "def count():\n    return None  # cached\n"})
    # neither: no test, no fix-word
    _commit(r, "Document the deployment", {"DEPLOY.md": "Push to prod.\n"})
    # a test-only commit, which is NOT a pinned mistake
    _commit(r, "More coverage for the counter", {
        "tests/test_widget.py": "def test_none():\n    assert True\n\n"
                                "def test_more():\n    assert True\n"})
    return r


# ── the denominator ───────────────────────────────────────────────────────

def test_the_reading_says_how_much_it_read_and_of_what(repo):
    got = A.read_repo(repo)
    assert len(got.commits) == 5 and got.reachable == 5
    assert "5 of 5 commit(s) read" in got.say()


def test_history_this_branch_cannot_see_is_reported_not_ignored(repo):
    """The first real repository this was pointed at reported one commit,
    honestly — and nineteen were reachable from other refs, because the project
    had arrived as a squashed merge. A silent denominator of one would have
    made a thorough-looking report out of a single line."""
    _run(repo, "checkout", "-q", "-b", "side")
    _commit(repo, "Something only on the side branch", {"side.py": "x = 1\n"})
    _run(repo, "checkout", "-q", "main")

    got = A.read_repo(repo)
    assert len(got.commits) == 5 and got.reachable == 6
    assert any("reachable only from other branches" in u for u in got.unread)


def test_the_reading_says_what_it_did_not_examine(repo):
    got = A.read_repo(repo)
    joined = " ".join(got.unread)
    assert "never behaviour" in joined, "it must say it did not read the code"
    assert "whether any test in this repository actually passes" in joined
    assert "NOT examined" in got.say()


def test_a_subdirectory_can_be_adopted_as_its_own_project(repo):
    """The nine analytics projects live as folders in one monorepo."""
    _commit(repo, "Add a sub-project", {"sub/thing.py": "y = 2\n"})
    got = A.read_repo(repo, within="sub")
    assert got.project == "sub"
    assert [c.subject for c in got.commits] == ["Add a sub-project"]


# ── the two tiers ─────────────────────────────────────────────────────────

def test_a_commit_touching_a_test_and_a_source_file_is_the_certain_tier(repo):
    pinned, _ = A.candidate_tenets(A.read_repo(repo))
    assert [c.rule for c in pinned] == ["A widget with no readings counted as zero"]
    assert all(c.certain for c in pinned)


def test_a_test_only_commit_is_not_a_pinned_mistake(repo):
    """Adding coverage is not evidence that something was wrong. Counting it
    as such inflates the certain tier, which is the one that has no caveat."""
    got = A.read_repo(repo)
    coverage = next(c for c in got.commits if c.subject.startswith("More coverage"))
    assert not coverage.pinned
    assert all(A._TEST_PATH.search(p) for p in coverage.paths)


def test_the_fix_word_tier_is_separate_and_marked_a_guess(repo):
    got = A.read_repo(repo)
    pinned, guessed = A.candidate_tenets(got)
    assert [c.rule for c in guessed] == ["Fix the stale cache header"]
    assert all(not c.certain for c in guessed)
    assert "THIS HALF IS A GUESS" in A.report(got, pinned, guessed)


def test_a_commit_that_is_neither_appears_in_neither_list(repo):
    pinned, guessed = A.candidate_tenets(A.read_repo(repo))
    everything = [c.rule for c in pinned + guessed]
    assert "Document the deployment" not in everything


def test_a_fix_word_does_not_fire_on_a_word_containing_it(repo):
    """`fix` must not match `prefix`, by the one matching rule."""
    _commit(repo, "Rename the prefix on the metric names", {"m.py": "z = 3\n"})
    got = A.read_repo(repo)
    renamed = next(c for c in got.commits if "prefix" in c.subject)
    assert renamed.fix_words == ()


def test_the_candidate_rule_is_the_commits_own_subject_never_a_summary(repo):
    """Generalising is the step that turns 'this repo fixed a thing' into
    'this repo proves a law', and it belongs to a person."""
    got = A.read_repo(repo)
    subjects = {c.subject for c in got.commits}
    pinned, guessed = A.candidate_tenets(got)
    for candidate in pinned + guessed:
        assert candidate.rule in subjects, "the rule text was rewritten"


def test_a_candidate_carries_a_citation_a_reader_can_go_and_check(repo):
    pinned, _ = A.candidate_tenets(A.read_repo(repo))
    ev = pinned[0].as_evidence("widget-monitor")
    assert ev.citation.startswith("commit ")
    assert pinned[0].commit.sha in ev.citation
    assert ev.when == pinned[0].commit.when


def test_the_report_refuses_to_call_any_of_it_a_tenet(repo):
    got = A.read_repo(repo)
    assert "None of the above is a tenet" in A.report(got, *A.candidate_tenets(got))


# ── the card cannot grow what rots ────────────────────────────────────────

GOOD = dict(project="widget-monitor",
            what_it_is="A monitor for widget readings.",
            what_it_is_for="Telling an operator when a widget stops reporting.",
            stack="Python, SQLite",
            where_it_lives="Its own folder in the monorepo.")


def test_a_card_that_says_what_the_project_is_is_accepted():
    card = A.Card(**GOOD)
    assert "widget-monitor" in card.render()
    assert "none recorded" in card.render(), "no convictions is stated, not implied"


@pytest.mark.parametrize("value,shape", [
    ("A monitor with 1,249 tests behind it.", "a count of things in the repo"),
    ("A monitor whose suite is passing.", "a pass/fail status"),
    ("A monitor that currently reads three feeds.", "a statement about right now"),
    ("A monitor. TODO: add the alerting.", "a work-in-progress marker"),
    ("A monitor built around widget.py and alerts.py.", "a file inventory"),
    ("A monitor, at v0.1.0.", "a version number"),
])
def test_a_card_refuses_anything_that_rots(value, shape):
    """One test per drift shape. A card that grows any of them goes red.

    These are not stylistic objections. Each is true the day it is written and
    quietly false a week later — and a card that has been wrong once is still
    consulted, which is what makes it worse than no card.
    """
    with pytest.raises(R.RecordError, match=shape.split()[1]):
        A.Card(**{**GOOD, "what_it_is": value})


def test_every_text_field_is_checked_not_just_the_first():
    """The guard was nearly written over `what_it_is` alone, which is the
    field a person fills in carefully. The rot arrives in the others."""
    for field in A.Card.TEXT:
        with pytest.raises(R.RecordError, match="currently"):
            A.Card(**{**GOOD, field: "It currently does the thing."})


def test_a_blank_field_is_refused():
    with pytest.raises(R.RecordError, match="is empty"):
        A.Card(**{**GOOD, "stack": "   "})


def test_the_card_has_no_field_for_status_or_structure():
    """PREVENT, DON'T DETECT. The text guard catches drift in a sentence; the
    absence of a field is what stops a card being GIVEN a status in the first
    place. Named here so adding one is a deliberate act with a red test."""
    fields = set(A.Card.__dataclass_fields__)
    assert fields == {"project", "what_it_is", "what_it_is_for", "stack",
                      "where_it_lives", "convictions"}


def test_the_convictions_on_a_card_come_from_the_record(repo):
    convictions = R.parse_convictions(R.CONVICTIONS.read_text(encoding="utf-8"))
    applies = A.convictions_for(convictions, "publishes a live pricing page")
    assert "C2" in applies, "a project that publishes is bound by C2"
    assert A.convictions_for(convictions, "reads widget telemetry") == ()


# ── adoption writes nothing ───────────────────────────────────────────────

def test_adoption_writes_nothing_anywhere(repo):
    before = {p: p.read_bytes() for p in sorted(repo.rglob("*"))
              if p.is_file() and ".git" not in p.parts}
    record_before = R.CONVICTIONS.read_text(encoding="utf-8")

    got = A.read_repo(repo)
    A.report(got, *A.candidate_tenets(got))
    A.Card(**GOOD).render()

    after = {p: p.read_bytes() for p in sorted(repo.rglob("*"))
             if p.is_file() and ".git" not in p.parts}
    assert after == before, "adoption touched the repository it was reading"
    assert R.CONVICTIONS.read_text(encoding="utf-8") == record_before


def test_the_adopter_has_no_write_path():
    source = (CANON / "adopt.py").read_text(encoding="utf-8")
    assert "write_text" not in source and "open(" not in source
    assert "record.add" not in source and "\nfrom record import" in source


def test_a_repository_that_is_not_one_says_so(tmp_path):
    """Not a crash, and not a silent empty reading — either would be read as
    'this project has no history'."""
    with pytest.raises(R.RecordError, match="git said no"):
        A.read_repo(tmp_path)


def test_a_signal_that_fires_on_almost_everything_says_so(repo):
    """S4. The first real repository this was run against was built test-first,
    so 14 of 17 commits changed a test alongside source — the normal case
    there, not a finding. A tool that flags four-fifths of everything and calls
    it a shortlist has destroyed belief in the part that was true.
    """
    for n in range(6):
        _commit(repo, f"Slice {n}: build the thing", {
            f"m{n}.py": f"v = {n}\n", f"tests/test_m{n}.py": "assert True\n"})
    got = A.read_repo(repo)
    assert got.pinned_share > 0.5
    assert "built test-first" in got.say()
    assert "not as a shortlist" in got.say()


def test_a_repository_with_ordinary_history_gets_no_such_note(repo):
    got = A.read_repo(repo)
    assert got.pinned_share <= 0.5
    assert "built test-first" not in got.say()
