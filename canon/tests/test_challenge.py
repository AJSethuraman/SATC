"""The record, and the challenge that reads it.

WHAT THESE TESTS HOLD, in one line each: nothing enters without a yes; nothing
is ever deleted; a retired conviction stops speaking and stays readable; a
collision is surfaced and never resolved; and SILENCE IS A RESULT.

THE FIXTURES ARE WRITTEN AS LITERAL MARKDOWN, the way a person or an editor
writes the file -- never assembled by `render` and fed back to `parse`. A
fixture built by the code under test proves only that the code agrees with
itself, which is the failure that survived mutation twice in this operation's
other repository inside a single week.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

import challenge as CH  # noqa: E402
import record as R  # noqa: E402


# ── a record, hand-written the way the file is written ────────────────────

HAND_WRITTEN = """# Convictions

---

## C1 · Working students pay less

**State:** held · **Recorded:** 2026-09-03 · **Applies:** SATC pricing

> *I just don't think it's right to fuck them over, basically.*
> — the firm, 3 September 2026

**Why:** A judgement about who the practice will make money from.

**Fires on:** student, discount, rate

---

## C2 · The practice has to cover its costs

**State:** held · **Recorded:** 2026-09-03 · **Applies:** SATC pricing

> *I want to be able to trust the results.*
> — the firm, 3 September 2026

**Why:** Generosity that closes the practice helps nobody.

**Fires on:** rate, sustainability, costs

---

## C3 · Something already abandoned

**State:** retired · **Recorded:** 2026-08-01 · **Applies:** SATC pricing

> *Charge everybody the same and be done with it.*
> — the firm, 1 August 2026

**Why:** Simplicity was worth more than fairness at the time.

**Fires on:** student, rate

**Retired:** 2026-09-03

**Retired because:** it turned out fairness was worth more.
"""


@pytest.fixture
def held():
    return R.parse_convictions(HAND_WRITTEN)


# ── reading the record ────────────────────────────────────────────────────

def test_a_hand_written_record_parses(held):
    assert [c.id for c in held] == ["C1", "C2", "C3"]
    assert held[0].quote.startswith("I just don't think")
    assert held[0].said_by == "the firm, 3 September 2026"


def test_the_attribution_does_not_swallow_the_entry(held):
    """THE FIRST REAL BUG THIS FILE CAUGHT. The quote may wrap over lines, so
    the pattern needs DOTALL -- and DOTALL made the attribution greedy too, so
    `said_by` absorbed the reason, the triggers and everything after them.
    Nothing failed: a parser that takes too much still returns an object."""
    for c in held:
        assert "\n" not in c.said_by
        assert "**" not in c.said_by
        assert len(c.said_by) < 60, c.said_by


def test_the_committed_record_round_trips():
    """`render(parse(x)) == x` for the real file, so a hand edit that breaks
    the shape fails here rather than being silently dropped by the parser.

    BOTH HALVES, and the second half is why this is worth restating: the
    declined section was added and this test kept passing on the convictions
    alone, which would have let the refusals be dropped on the next write with
    nothing noticing. A round-trip that covers part of a file is a round-trip
    that certifies the part nobody was going to lose.
    """
    text = R.CONVICTIONS.read_text(encoding="utf-8")
    assert R.render_convictions(R.parse_convictions(text),
                                R.parse_declined(text)) == text
    assert R.parse_declined(text), "the fixture stopped covering the declined half"


def test_an_unreadable_record_refuses_rather_than_returning_nothing():
    """A record that loses an entry quietly is worse than one that will not
    load. Empty is never an acceptable answer here."""
    with pytest.raises(R.RecordError):
        R.parse_convictions("# Convictions\n\nnothing here\n")


# ── slice 2 · nothing enters without a yes ────────────────────────────────

def _draft(cid="C9"):
    return R.Conviction(
        id=cid, title="A new belief", state=R.HELD, recorded="2026-09-03",
        applies="everything", quote="something the firm said",
        said_by="the firm", why="a reason", fires_on=("thing",))


def test_an_unconfirmed_conviction_is_not_recorded(held):
    with pytest.raises(R.RecordError, match="not confirmed"):
        R.add(held, _draft(), confirmed=False)


def test_a_confirmed_conviction_is_appended(held):
    after = R.add(held, _draft(), confirmed=True)
    assert [c.id for c in after] == ["C1", "C2", "C3", "C9"]
    assert after[:3] == held, "adding one rewrote the others"


def test_a_conviction_without_the_firms_words_is_refused(held):
    bare = R.Conviction(id="C9", title="t", state=R.HELD, recorded="2026-09-03",
                        applies="everything", quote="   ", said_by="the firm",
                        why="a reason")
    with pytest.raises(R.RecordError, match="no quotation"):
        R.add(held, bare, confirmed=True)


def test_an_id_is_never_reused(held):
    with pytest.raises(R.RecordError, match="already exists"):
        R.add(held, _draft("C1"), confirmed=True)


# ── slice 3 · retire, never delete ────────────────────────────────────────

def test_retiring_keeps_the_words_and_adds_the_reason(held):
    after = R.retire(held, "C1", because="the practice could not cover costs",
                     on="2026-12-01")
    gone = next(c for c in after if c.id == "C1")
    assert gone.state == R.RETIRED
    assert gone.quote == held[0].quote, "retiring altered what the firm said"
    assert gone.why == held[0].why
    assert gone.retired_on == "2026-12-01"
    assert "could not cover costs" in gone.retired_because
    assert len(after) == len(held), "retiring removed an entry"


def test_retiring_without_a_reason_is_refused(held):
    with pytest.raises(R.RecordError, match="needs a reason"):
        R.retire(held, "C1", because="   ")


def test_a_retired_conviction_never_fires(held):
    """C3 fires on `student` and `rate` and is retired. It must stay silent —
    that is the whole difference between retiring and deleting."""
    found = CH.candidates(held, CH.Decision(what="change the student rate",
                                            scope="SATC pricing"))
    assert "C3" not in [c.conviction.id for c in found]


def test_a_retired_conviction_is_still_readable(held):
    c3 = next(c for c in held if c.id == "C3")
    assert c3.quote.startswith("Charge everybody the same")
    assert c3.retired_because
    assert R.render_convictions([c3]).count("Retired because") == 1


# ── slice 4 · a collision is a finding ────────────────────────────────────

def test_two_convictions_on_one_decision_are_both_surfaced(held):
    found = CH.candidates(held, CH.Decision(what="change the rate we charge",
                                            scope="SATC pricing"))
    assert {c.conviction.id for c in found} == {"C1", "C2"}
    assert CH.conflicts(found), "the collision was not detected"


def test_a_collision_is_never_resolved(held):
    found = CH.candidates(held, CH.Decision(what="change the rate", scope="SATC pricing"))
    said = CH.report(found, CH.conflicts(found))
    assert "C1" in said and "C2" in said
    assert "Has the reason changed?" in said
    for weasel in ("I recommend", "you should", "the right answer",
                   "outweighs", "more important"):
        assert weasel.lower() not in said.lower(), f"it resolved it: {weasel!r}"


# ── silence is a result ───────────────────────────────────────────────────

def test_a_decision_touching_nothing_produces_nothing(held):
    found = CH.candidates(held, CH.Decision(what="rename a CSS class"))
    assert found == []
    assert CH.report(found, []) == "", "it spoke when it had nothing to say"


def test_a_word_inside_another_word_does_not_fire(held):
    """`rate` must not fire on `generate`. A challenge that arrives because one
    word contains another is the false positive that teaches somebody to stop
    reading them."""
    found = CH.candidates(held, CH.Decision(what="generate the demonstration"))
    assert found == []


def test_a_conviction_out_of_scope_does_not_fire(held):
    found = CH.candidates(held, CH.Decision(what="change the student rate",
                                            scope="credit-risk suite"))
    assert found == []


# ── slice 5 · hard gates ──────────────────────────────────────────────────

def test_a_named_moment_fires_and_says_whether_it_blocks(held):
    """`student discount` and not `student rate` on purpose: `rate` is a
    trigger on BOTH convictions, so it exercises the collision rather than the
    gate. A fixture that quietly tests something else is how a test comes to
    pass for the wrong reason."""
    found, force = CH.gate(held, CH.Decision(what="cut the student discount",
                                             scope="SATC pricing",
                                             moment="price-change"))
    assert [c.conviction.id for c in found] == ["C1"]
    assert force in ("advisory", "blocking")


def test_every_gate_starts_advisory():
    """The firm's own rule for the tenet linter: what a machine can check
    EXACTLY may block; what it can only guess at advises, and is promoted only
    after a full cycle with no false positive. Relevance is a guess."""
    assert set(CH.GATES.values()) == {"advisory"}


def test_an_unknown_moment_does_not_become_a_gate_by_accident(held):
    found, force = CH.gate(held, CH.Decision(what="cut the student discount",
                                             scope="SATC pricing",
                                             moment="something-invented"))
    assert force == "advisory"
    assert [c.conviction.id for c in found] == ["C1"]


# ── what a challenge says ─────────────────────────────────────────────────

def test_a_challenge_quotes_rather_than_paraphrases(held):
    found = CH.candidates(held, CH.Decision(what="raise the student rate",
                                            scope="SATC pricing"))
    said = found[0].say()
    assert held[0].quote in said, "it did not quote the firm"
    assert held[0].recorded in said
    assert said.rstrip().endswith("?"), "it did not end on the question"


# ── slice 6 · evidence accumulates ────────────────────────────────────────
#
# `add_evidence` shipped with slice 1 and was never tested -- the function
# existed, the guard did not. This is what makes the record COMPOUND rather
# than merely persist, so it is the last thing that should have gone unchecked.

HAND_WRITTEN_TENETS = """# Tenets

---

## S1 · Nothing is produced until something opens it

**Evidence: 1** *(SATC ×1)*

### SATC · 2026-08-27 · a commit

A harness said 190 documents were fine and every one was unreadable.

---

## S2 · A check must report its denominator

**Evidence: 0**
"""


@pytest.fixture
def tenets():
    return R.parse_tenets(HAND_WRITTEN_TENETS)


def test_a_bare_rule_is_visible_as_bare(tenets):
    """A rule with nothing under it does not belong in the file, so it has to
    be findable without reading every entry."""
    assert [t.id for t in tenets if t.bare] == ["S2"]


def test_evidence_appends_and_never_rewrites(tenets):
    before = tenets[0].evidence
    after = R.add_evidence(tenets, "S1", R.Evidence(
        project="canon", when="2026-09-03", citation="this session",
        detail="The round-trip check found a parser eating half a record."))
    got = next(t for t in after if t.id == "S1")
    assert got.evidence[:1] == before, "appending rewrote what was there"
    assert len(got.evidence) == 2
    assert got.evidence[-1].project == "canon"


def test_evidence_from_a_second_project_is_what_makes_it_a_law(tenets):
    """One citation is a local observation. Two, from two codebases, is the
    difference between a quirk and a rule -- and it should be countable
    without reading."""
    after = R.add_evidence(tenets, "S1", R.Evidence(
        project="credit-review-os", when="2026-10-01", citation="a commit",
        detail="It happened again somewhere else."))
    text = R.render_tenets(after)
    assert "**Evidence: 2**" in text
    assert "SATC ×1" in text and "credit-review-os ×1" in text


def test_adding_evidence_to_a_rule_that_is_not_there_refuses(tenets):
    with pytest.raises(R.RecordError, match="not in the record"):
        R.add_evidence(tenets, "S99", R.Evidence("x", "2026-01-01", "y", "z"))


# ── slice 8 · the migration ───────────────────────────────────────────────

def test_all_thirty_five_tenets_came_across():
    got = R.parse_tenets(R.TENETS.read_text(encoding="utf-8"))
    ids = [t.id for t in got]
    assert len(ids) == 35, f"{len(ids)} tenets, expected 35"
    assert ids == sorted(ids, key=lambda s: int(s[1:])), "out of order"
    assert "S31" in ids


def test_no_tenet_arrived_bare():
    """The migration's own rule, applied to itself: a rule with nothing under
    it does not belong in the file."""
    got = R.parse_tenets(R.TENETS.read_text(encoding="utf-8"))
    assert [t.id for t in got if t.bare] == []


def test_the_curated_entry_was_not_overwritten_by_the_bulk_move():
    """S31 carried two hand-written entries before the migration ran. A
    migration that flattens curation destroys the thing it was moving."""
    got = {t.id: t for t in R.parse_tenets(R.TENETS.read_text(encoding="utf-8"))}
    s31 = got["S31"]
    assert len(s31.evidence) == 2, f"S31 has {len(s31.evidence)} entries"
    assert all("mined from the whole history" not in e.citation for e in s31.evidence)


def test_the_tenets_file_round_trips():
    """Second real bug this check found: detail ran to the next heading and
    swallowed the `---` that divides tenets, so every write added a separator."""
    text = R.TENETS.read_text(encoding="utf-8")
    assert R.render_tenets(R.parse_tenets(text)) == text


def test_no_separator_was_carried_into_a_tenets_evidence():
    got = R.parse_tenets(R.TENETS.read_text(encoding="utf-8"))
    for t in got:
        for e in t.evidence:
            assert not e.detail.rstrip().endswith("---"), f"{t.id} carries a separator"


def test_a_pair_is_not_called_a_disagreement(held):
    """`conflicts` was the name, and the report said flatly "two things you
    believe are pulling against each other here". Nothing checks whether they
    pull against each other — all that is observed is that both were selected.

    The moment the record grew C1 and C4, which AGREE about student pricing,
    that sentence was simply false. A challenge the firm can see is false is
    the one that teaches them to skip the next.
    """
    found = CH.candidates(held, CH.Decision(what="change the rate", scope="SATC pricing"))
    said = CH.report(found, CH.both_bear_on(found))
    assert "both bear on this" in said
    assert "pulling against each other here" not in said
    assert "They may point the same way" in said


def test_the_two_convictions_that_agree_do_both_fire():
    """C1 and C4 on the real record: a decision about a student package brings
    both, and neither is reported as contradicting the other."""
    real = R.parse_convictions(R.CONVICTIONS.read_text(encoding="utf-8"))
    found = CH.candidates(real, CH.Decision(
        what="drop the college student package because it loses money",
        scope="SATC pricing"))
    assert {c.conviction.id for c in found} == {"C1", "C4"}
    said = CH.report(found, CH.both_bear_on(found))
    assert "may point the same way" in said
    assert "fine operating at a" in said, "C4 must be quoted, not paraphrased"


def test_the_old_name_still_resolves_to_the_same_function():
    """Renamed, not removed: callers exist and a silent AttributeError at the
    moment a challenge should fire is worse than a bad name."""
    assert CH.conflicts is CH.both_bear_on
