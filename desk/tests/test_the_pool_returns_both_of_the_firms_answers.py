"""Where the firm answered one passage twice, the pool returns both, together.

`dec-pair`, 14 September 2026 — the firm, on the eighth docket: **"Pair them."**

THE INCIDENT IS 7 SEPTEMBER AND THE RANKING STILL REPRODUCES IT. Asked *a
deposit was made on the last day of the month and is not on the bank statement
yet — do we make an entry in the books?*, this pool returns the firm's **wrong**
answer at rank 1 (33.6, *an entry in the books*) and the **right** one at rank 2
(22.0, *a reconciling item, no entry in the books*). A reader who takes the top
hit gets the documented wrong answer, in the firm's own words, marked binding —
which is precisely what the session on 7 September did.

WHAT FORGE-DESK REPORTED, AND WHAT IS ACTUALLY TRUE. Their Finding 1 said
*"nothing in the pool has an `alongside` to fire on"* and asked whether it was
dead code. It is not. An answer SERVED through the engine carries both positions
and both passages in full, under a block in capitals saying the firm has answered
this passage more than once. It works by matching the citation STEM on the
record, not by reading the pool, which is why it was invisible from where they
stood.

SO THE EXPOSURE IS NARROWER THAN REPORTED AND IT IS REAL: a caller that reads
`pool.look` directly and takes rank 1 never reaches the engine, and gets one of
two opposite answers with nothing saying the other exists.

THE STEM IS THE FIRM'S OWN MARK. `POSITIONS.md`: *"A position carries one
answer, and one citation admits one position. The publication states what the
statement did not yet include and, separately, what the books are updated for;
those have opposite answers, so they are cited and answered apart."* Two ratified
positions sharing a stem is the firm saying *this passage carries more than one
answer*. That is the only case this fires on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import pool                                                 # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

CITE = 'IRS Pub. 583 (12/2024), "Reconciling the checking account"'
BOOKS = f"{CITE} — what the books are updated for"
STATEMENT = f"{CITE} — what the statement did not yet include"

#: THE QUESTION FROM THE INCIDENT, verbatim.
DEPOSIT = ("a deposit was made on the last day of the month and is not on the "
           "bank statement yet - do we make an entry in the books?")

#: THE PHRASING THAT MADE THIS WORSE THAN IT LOOKED. It is one of the three
#: published in `POOL-VS-ROUTING-2026-09-10.md` as evidence the pool fixed the
#: word list — and it returns the WRONG HALF of this pair at rank 1. The
#: headline proof of the pool's biggest win contains an instance of its sharpest
#: defect.
HEADLINE = "how do we treat deposits with no source recorded?"


@pytest.fixture(scope="module")
def held():
    return pool.assemble(CORPUS)


@pytest.fixture(scope="module")
def stats(held):
    return pool.stats(held)


# ── the premise ─────────────────────────────────────────────────────────────

def test_the_firm_still_holds_two_opposite_answers_on_one_passage():
    """If this is ever rewritten, every test in this file must be re-read."""
    desk = record.load(CORPUS)
    rat = {p.citation: p.position for p in desk.positions if not p.proposed}
    assert rat[BOOKS] == "an entry in the books"
    assert rat[STATEMENT] == "a reconciling item, no entry in the books"


def test_exactly_one_pair_fires_in_this_corpus():
    """Measured rather than assumed. A stem-match that fired on dozens would be
    matching paragraph numbering, not the firm's qualifier."""
    desk = record.load(CORPUS)
    stems = {}
    for p in desk.positions:
        if not p.proposed:
            stems.setdefault(record._stem(p.citation), []).append(p.citation)
    pairs = {k: v for k, v in stems.items() if len(v) > 1}
    assert len(pairs) == 1 and set(next(iter(pairs.values()))) == {BOOKS,
                                                                  STATEMENT}


# ── the pairing ─────────────────────────────────────────────────────────────

def test_both_answers_come_back_on_the_incident_question(held, stats):
    got = pool.look(DEPOSIT, held, limit=8, known=stats)
    cites = [f.held.citation for f in got]
    assert BOOKS in cites and STATEMENT in cites
    assert abs(cites.index(BOOKS) - cites.index(STATEMENT)) == 1, (
        "the firm's two opposite answers are not adjacent; a reader scanning "
        "the list can take one without meeting the other")


def test_the_sibling_is_pulled_up_past_a_hit_it_did_not_outrank(held, stats):
    """THE CASE THAT PROVES THIS DOES SOMETHING. On the incident question the
    two happened to be adjacent already, so pairing changed nothing and a test
    written only on that question would pass with the feature deleted.

    On the headline phrasing they are not: the right half scores BELOW a third
    hit and would otherwise be read past."""
    got = pool.look(HEADLINE, held, limit=6, known=stats)
    cites = [f.held.citation for f in got]
    assert cites.index(STATEMENT) == cites.index(BOOKS) + 1
    sibling = got[cites.index(STATEMENT)]
    outranked = [f for f in got[cites.index(STATEMENT) + 1:]
                 if f.score > sibling.score]
    assert outranked, (
        "nothing here scored above the sibling, so this question no longer "
        "exercises the case; find one that does rather than deleting the test")


def test_the_sibling_says_it_is_here_because_of_its_partner(held, stats):
    """A sibling placed by adjacency alone reads as having scored, with its own
    lower score printed right beside it looking like the reason."""
    got = pool.look(HEADLINE, held, limit=6, known=stats)
    sib = next(f for f in got if f.held.citation == STATEMENT)
    assert sib.paired_with == BOOKS
    assert all(f.paired_with == "" for f in got
               if f.held.citation != STATEMENT), (
        "something earned its own place and is marked as paired")


def test_the_scores_are_untouched(held, stats):
    """Pairing moves; it must never rescore. A sibling whose score was lifted to
    justify its position would be the engine inventing a measurement."""
    got = pool.look(HEADLINE, held, limit=6, known=stats)
    sib = next(f for f in got if f.held.citation == STATEMENT)
    plain = {h.citation: h for h in held}
    assert sib.held is plain[STATEMENT] or sib.held == plain[STATEMENT]
    assert sib.score < next(f.score for f in got
                            if f.held.citation == BOOKS), (
        "the sibling's score was raised to match its new position")


# ── and what it must not do ─────────────────────────────────────────────────

def test_pairing_reorders_only_the_sibling(held, stats):
    """Everything that is not half of a pair keeps the order it earned."""
    got = pool.look(HEADLINE, held, limit=8, known=stats)
    rest = [f.held.citation for f in got if f.held.citation != STATEMENT]
    assert rest == sorted(
        rest, key=lambda c: (-next(f.score for f in got
                                   if f.held.citation == c), c)), (
        "pairing disturbed the order of hits that are not siblings")


def test_a_sibling_the_question_never_reached_is_not_invented(held):
    """The sibling has to be in the pool's OWN results to be moved. Injecting a
    passage nothing matched would be the retrieval answering a question it was
    not asked — and on this pair it would attach a bank-reconciliation rule to
    anything that mentioned Pub. 583."""
    got = pool.look("what is a qualifying taxpayer?", held, limit=8)
    assert all(f.held.citation not in (BOOKS, STATEMENT) for f in got), (
        "a citation nothing matched was pulled into the results")


def test_a_citation_with_no_ratified_position_is_never_paired(held, stats):
    """The firm's qualifier is what this fires on. A stem shared by two stored
    PASSAGES with no position on them is ordinary paragraph numbering."""
    got = pool.look("what records are required for a charge with only a "
                    "vendor name?", held, limit=8, known=stats)
    for f in got:
        if f.paired_with:
            assert f.held.positions, (
                f"{f.held.citation} was paired and carries no ratified "
                f"position; the firm's mark is the only thing that pairs")


def test_nothing_is_dropped_or_duplicated(held, stats):
    for probe in (DEPOSIT, HEADLINE, "is the paint booth plant property?",
                  "mileage or actual expenses for the van?"):
        got = pool.look(probe, held, limit=8, known=stats)
        cites = [f.held.citation for f in got]
        assert len(cites) == len(set(cites)), f"{probe!r} returned a duplicate"
        assert len(cites) <= 8


def test_silence_is_still_silence(held):
    """A question sharing no substantive word with anything returns nothing —
    pairing must not give it a foothold."""
    assert pool.look("translate hello into Portuguese", held) == ()
