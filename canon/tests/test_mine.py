"""Mining the corpus: what it may decide, and what it may not.

THE THING THESE TESTS EXIST TO STOP is a module that reads eight thousand
words of somebody's writing and announces what they believe. Every guard here
is a wall between "surfaced a passage" and "decided a conviction":

  - the quote must be literally present in the passage it claims
  - the proposal is never written; the only exit is the confirmation
  - the run states its denominator, including what it could not read
  - the certain half and the guessed half are never one list

THE CORPUS FIXTURES ARE HAND-WRITTEN, in the shape the real files are written
in -- not produced by the reader under test. A fixture the code builds proves
the code agrees with itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import mine as M  # noqa: E402
import record as R  # noqa: E402


TURNS = """# The firm's own words

**3 turns.**

---

### 2026-08-21 02:49:16

One feature branch and one draft PR per batch. Never push to main: it
publishes to the live domain satcllp.com through Cloudflare Pages.

### 2026-08-21 03:31:36

[Image: original 270x2612, displayed at 207x2000.]

### 2026-08-25 15:21:55

ok so the estimate refused to build. that is fine, rerun it
"""

DECISIONS = """# Decisions, in the firm's own words

**2 decisions, 1 of them typed.**

---

### 2026-08-30 01:05:21  · TYPED

**Asked:** How do you want the website handled?

**Chose:** You shouldn't ever touch the website itself. That is another agents job.

### 2026-09-03 21:43:07

**Asked:** The REPO name — plain, searchable, ages well.

**Chose:** canon (Recommended)
"""


@pytest.fixture
def corpus():
    return M.read_turns(TURNS), M.read_decisions(DECISIONS)


@pytest.fixture
def convictions():
    return R.parse_convictions(R.CONVICTIONS.read_text(encoding="utf-8"))


# ── the denominator ───────────────────────────────────────────────────────

def test_the_run_says_what_it_examined_and_what_it_could_not_read(corpus):
    """S2. A mining run that surfaces nothing and says nothing is
    indistinguishable from one that never opened the files."""
    s = M.survey(*corpus)
    assert (s.turns, s.turns_without_words, s.decisions, s.typed) == (3, 1, 2, 1)
    said = s.say()
    assert "3 turn(s) and 2 interview answer(s)" in said
    assert "1 were screenshots with no text" in said
    assert "2026-08-21 to 2026-09-03" in said


def test_a_screenshot_is_counted_not_dropped(corpus):
    """Excluding it from the numerator AND the denominator hides it. It is
    counted as read-and-empty, which is a different fact from not existing."""
    turns, _ = corpus
    assert len(turns) == 3, "the image turn must survive parsing"

    image = next(p for p in turns if p.text.startswith("[Image:"))
    assert image.words == 6, "the placeholder does have words, and they are not the firm's"
    assert M.survey([image], []).words == 0, "so the count excludes them"
    assert M.survey([image], []).turns == 1, "and the denominator still sees it"


# ── certain and guessed are never one list ────────────────────────────────

def test_the_typed_answers_and_the_marker_hits_come_back_separately(corpus):
    """A tool that prints its guesses and its certainties in one column has
    taught you to distrust both."""
    certain, guessed = M.surfaced(*corpus)
    assert [p.when for p in certain] == ["2026-08-30 01:05:21"]
    assert all(p.typed for p in certain)
    assert [p.when for p, _ in guessed] == ["2026-08-21 02:49:16"]


def test_a_typed_answer_is_surfaced_without_needing_a_marker(corpus):
    """Rejecting the framing IS the signal. Requiring a marker on top of it
    would put the deterministic half behind the guessed half."""
    certain, _ = M.surfaced(*corpus)
    assert M.markers_in(certain[0].text) == ()


def test_the_report_labels_the_guessed_half_as_a_guess(corpus, convictions):
    s = M.survey(*corpus)
    text = M.report(*M.surfaced(*corpus), s, convictions)
    assert "no judgement in this list" in text
    assert "THIS HALF IS A GUESS" in text


# ── the matching rule ─────────────────────────────────────────────────────

def test_a_marker_does_not_fire_on_a_word_that_merely_contains_it(corpus):
    """`refuse` matched `refused` in four pasted terminal transcripts on the
    first real run -- four of the noisiest hits in a list whose only job is to
    be worth reading. One matching rule, shared with the challenge."""
    assert "refuse" in M.MARKERS
    assert M.markers_in("the estimate refused to build") == ()
    assert M.markers_in("i refuse to ship that") == ("refuse",)


def test_the_miner_and_the_challenge_use_the_same_matching_rule():
    """They were briefly written twice and disagreed for a day with nothing
    comparing them (S31). Named here so a second copy is a red test."""
    import challenge as CH
    assert CH.touches is R.touches
    assert M.touches is R.touches


def test_an_existing_conviction_is_flagged_not_filtered(corpus, convictions):
    """A passage touching C2 may be the reason behind it, or the first sign it
    is being contradicted. Hiding it decides something the reader should."""
    turns, _ = corpus
    push = next(p for p in turns if "Never push to main" in p.text)
    assert "C2" in M.already_said(convictions, push)
    _, guessed = M.surfaced(*corpus)
    assert push in [p for p, _ in guessed], "flagged, still surfaced"


# ── the quote is checked against the corpus ───────────────────────────────

def _draft(**kw):
    base = dict(id="C9", title="A title", state=R.HELD, recorded="2026-08-30",
                applies="everything", quote="another agents job",
                said_by="the firm, 30 August 2026", why="Because they said so.",
                fires_on=("website",))
    return R.Conviction(**{**base, **kw})


def test_a_quote_absent_from_the_passage_is_refused(corpus):
    """Paraphrase is the failure that burns the whole mechanism. Made
    impossible at construction, not warned about at review."""
    _, decisions = corpus
    passage = decisions[0]
    with pytest.raises(R.RecordError, match="not in the passage"):
        M.Proposal(draft=_draft(quote="the website is somebody else's problem"),
                   passage=passage)


def test_a_quote_present_in_the_passage_is_accepted(corpus):
    _, decisions = corpus
    p = M.Proposal(draft=_draft(), passage=decisions[0])
    assert p.draft.quote in p.passage.text


@pytest.mark.parametrize("field,expected", [
    ("quote", "paraphrase with extra steps"),
    ("why", "no reason"),
    ("recorded", "no date"),
])
def test_a_proposal_missing_what_makes_it_defensible_is_refused(
        corpus, field, expected):
    _, decisions = corpus
    with pytest.raises(R.RecordError, match=expected):
        M.Proposal(draft=_draft(**{field: "  "}), passage=decisions[0])


def test_the_ask_shows_the_exact_text_that_would_be_stored(corpus):
    """The firm can only agree to words they have seen. A summary of what will
    be written is not the thing being agreed to."""
    _, decisions = corpus
    said = M.Proposal(draft=_draft(), passage=decisions[0]).ask()
    for shown in ("C9", "A title", "2026-08-30", "everything",
                  "another agents job", "Because they said so.", "website"):
        assert shown in said, f"{shown!r} missing from the confirmation"
    assert "you typed this rather than picking" in said
    assert "Nothing is written until you say so." in said


# ── nothing here writes ───────────────────────────────────────────────────

def test_mining_cannot_reach_the_record_except_through_the_confirmation(corpus):
    """The whole point of the slice. A mined proposal goes through the same
    refusal an interactively drafted one does."""
    _, decisions = corpus
    proposal = M.Proposal(draft=_draft(), passage=decisions[0])
    with pytest.raises(R.RecordError, match="was not confirmed"):
        M.commit([], proposal, confirmed=False)
    assert [c.id for c in M.commit([], proposal, confirmed=True)] == ["C9"]


def test_commit_is_the_only_exit_from_the_miner():
    """A second write path is a second place for the confirmation to be
    forgotten, and it would be forgotten in the one nobody was looking at."""
    source = (CANON / "mine.py").read_text(encoding="utf-8")
    assert "write_text" not in source, "the miner does not write files"
    assert source.count("add(items") == 1, "one call into the record, no more"


def test_the_miner_never_reads_a_conviction_into_existence(corpus, convictions):
    """Running the whole report leaves the record exactly as it was."""
    before = R.CONVICTIONS.read_text(encoding="utf-8")
    M.report(*M.surfaced(*corpus), M.survey(*corpus), convictions)
    assert R.CONVICTIONS.read_text(encoding="utf-8") == before


# ── against the real corpus ───────────────────────────────────────────────

def test_the_corpus_headers_agree_with_what_the_miner_counts():
    """S31: a claim in one place, behaviour in another, nothing comparing them.

    The turns file claimed 7,965 words while promising 'nothing of the
    agent's' -- 300 of them were `[Image: ...]` placeholders the agent wrote.
    This test is the thing that compares them.
    """
    s = M.survey(*M.load_corpus())
    turns_text = M.TURNS_FILE.read_text(encoding="utf-8")
    decisions_text = M.DECISIONS_FILE.read_text(encoding="utf-8")

    turn_words = sum(p.words for p in M.read_turns(turns_text)
                     if not M._IMAGE_ONLY.match(p.text))
    decision_words = sum(p.words for p in M.read_decisions(decisions_text))

    assert f"**{s.turns} turns, {s.turns_without_words} of them a screenshot " \
           f"and nothing else, {turn_words:,} words.**" in turns_text
    assert f"**{s.decisions} decisions, {s.typed} of them typed, " \
           f"{decision_words} words**" in decisions_text


def test_every_typed_answer_in_the_real_corpus_is_surfaced():
    """Seventeen of forty-four. The deterministic half must be complete: a
    miner that drops one has quietly decided it was not interesting."""
    turns, decisions = M.load_corpus()
    certain, _ = M.surfaced(turns, decisions)
    assert len(certain) == 17
    assert len(certain) == sum(1 for p in decisions if p.typed)


def test_the_real_corpus_reports_a_denominator_that_adds_up():
    turns, decisions = M.load_corpus()
    s = M.survey(turns, decisions)
    assert s.turns == 173 and s.decisions == 44
    assert s.read == s.turns - s.turns_without_words + s.decisions
    assert s.first == "2026-08-21" and s.last == "2026-09-03"


def test_the_snippet_shows_the_marker_not_the_first_line():
    """Three real passages looked like noise on the first run because their
    first line was `ok so` or `NOW`.

    The first version of this test used a short passage, so a snippet starting
    at character zero still contained the marker and the assertion passed on a
    mutant that had put the bug straight back. The preamble here is longer than
    the window on purpose.
    """
    text = "ok so\n\n" + ("preamble that is not the point. " * 20) + \
           "i want the thing to be deterministic."
    snippet = M.around(text, "i want")
    assert "i want the thing to be deterministic." in snippet
    assert "ok so" not in snippet, "the useless first line must not be what is shown"
    assert snippet.startswith("…"), "and the reader is told the passage was cut"
