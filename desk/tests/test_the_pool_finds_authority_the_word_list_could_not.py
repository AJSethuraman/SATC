"""The pool answers `dec-kill`, and the desk's name is not how it finds anything.

    `dec-kill`, 8 September 2026 -- "Kill the desks; one pool." Decided on a
    measurement: the deposits question written six ways reached no desk three
    times and the WRONG desk twice. Forge-Occam: "The word that saved me was
    'bank'."

    `dec-order`, 9 September -- "Build the pool beside the desks; switch on
    evidence." A destination, not an immediate demolition.

EVERY QUESTION IN THIS FILE WAS ACTUALLY ASKED. They are Forge-Occam's, verbatim
from their field report of 9 September, and `dec-kill`'s own. Not one is
invented, and that is the point: the previous test in this repository built from
imagined phrasings widened the vocabulary by nineteen words to satisfy sentences
nobody had ever typed, and six plain bookkeeping questions started being
answered out of tax law as a result.

WHAT IS ASSERTED AND WHAT IS DELIBERATELY NOT. Asserted: the authority Occam's
own desk said it needed is reachable without the word that saved them, and the
matching never reads a desk name. NOT asserted: that the pool beats the word
list by some number. That comparison belongs in `tools/pool_vs_routing.py`,
where it is printed with its denominator and can be re-run, rather than frozen
into a test that would then have to be edited every time a source is added.
"""

from pathlib import Path

import pytest

import pool
import routing


DESKS = Path(__file__).resolve().parent.parent / "desks"

#: The authority `personal-or-business` reported it wanted, escalating
#: `authority_absent` after two independent judges refused two different
#: citations. It sits on `cash-and-bank`, and its recordkeeping guidance is not
#: bank-specific -- it is the general rule for substantiating a business expense.
PUB_583 = "IRS Pub. 583"


@pytest.fixture(scope="module")
def held():
    return pool.assemble(DESKS)


@pytest.fixture(scope="module")
def known(held):
    return pool.stats(held)


@pytest.mark.parametrize("question", [
    # Occam's five phrasings for the substantiation question. Under the word
    # list, two reached nothing at all and two reached the wrong desk.
    "what supporting documents does the client have to keep?",
    "what supporting documents must be kept?",
    "recordkeeping for business expenses",
    # And the two that did work for them, so a regression is visible here too.
    "supporting documents for a bank statement charge",
    "what kinds of records to keep for a bank account?",
])
def test_the_authority_is_reachable_without_the_word_that_saved_them(
        question, held, known):
    found = pool.look(question, held, limit=3, known=known)
    assert found, f"{question!r} returned nothing"
    assert any(f.held.citation.startswith(PUB_583) for f in found), (
        f"{question!r} did not place {PUB_583} in its top three; got "
        f"{[f.held.citation for f in found]}"
    )


def test_the_word_list_could_not_reach_it(held, known):
    """The measured contrast, pinned so it is not claimed from memory.

    This asserts the OLD mechanism's failure rather than the new one's success,
    because that failure is what `dec-kill` was decided on. It dies with
    `routing` and is expected to -- at which point this test goes with it.
    """
    question = "what supporting documents does the client have to keep?"
    registry = routing.registry(DESKS)
    assert not routing.route(question, registry), (
        "the word list now reaches a desk for this question; if that is a "
        "deliberate widening, this test and dec-kill's evidence both need "
        "revisiting rather than this line being deleted"
    )
    assert pool.look(question, held, limit=3, known=known)


def test_the_pool_never_matches_on_a_desk_name(held, known):
    """Checked by mutation, not by reading the code.

    `read_from` is provenance -- which folder a record was read from, kept so a
    hole can be reported somewhere. If any of it leaked into the matching, the
    desks would still be deciding what a question reaches, wearing a new name.
    So every `read_from` is replaced with a value that shares nothing with the
    real ones, and the results must be identical.
    """
    question = "what supporting documents does the client have to keep?"
    before = pool.look(question, held, limit=8, known=known)

    scrambled = tuple(
        pool.Held(citation=h.citation, kind=h.kind, text=h.text,
                  source_id=h.source_id, tier=h.tier, url=h.url,
                  read_from=f"zzzz-{i}", positions=h.positions)
        for i, h in enumerate(held)
    )
    after = pool.look(question, scrambled, limit=8, known=pool.stats(scrambled))

    assert [(f.held.citation, round(f.score, 9)) for f in before] == \
           [(f.held.citation, round(f.score, 9)) for f in after], (
        "renaming every desk folder changed what the pool returned, so a desk "
        "name is still deciding what a question reaches"
    )


def test_a_question_sharing_nothing_returns_nothing(held, known):
    """Silence is still a result. A retrieval that always answers is one whose
    answer means nothing -- `routing`'s docstring is right about that and
    killing the word list does not change it."""
    assert pool.look("zzzqwx vvbbnn", held, limit=3, known=known) == ()
    assert pool.look("", held, limit=3, known=known) == ()
    assert pool.look("the of and to", held, limit=3, known=known) == ()


def test_the_same_question_gives_the_same_order_every_time(held, known):
    """No model decides this, so nothing about it may vary between runs."""
    question = "what records must be kept for a business expense?"
    once = pool.look(question, held, limit=8, known=known)
    twice = pool.look(question, held, limit=8, known=known)
    assert [f.held.citation for f in once] == [f.held.citation for f in twice]
    assert [f.score for f in once] == [f.score for f in twice]


def test_every_hit_can_show_the_words_it_matched_on(held, known):
    """Earn the claim: a score with nothing under it is a number a reader has to
    take on trust, and the whole point of killing the word list was that a wrong
    hit should be something somebody can point at."""
    for found in pool.look("what receipts do we need to keep?", held,
                           limit=5, known=known):
        assert found.matched, f"{found.held.citation} scored with no words shown"
        text = pool.terms(found.held.text)
        for word in found.matched:
            assert word in text, (
                f"{found.held.citation} claims to have matched {word!r}, which "
                "is not in its text"
            )


def test_the_pool_holds_the_positions_with_the_citation(held):
    """`dec-kill`: what survives is stored against the CITATION rather than the
    desk. A ratified position is, for a source whose licence forbids storing the
    text at all, the pool's entire knowledge of that citation."""
    with_positions = [h for h in held if h.positions]
    assert with_positions, "no ratified position survived into the pool"
    for entry in with_positions:
        for position in entry.positions:
            assert position.citation == entry.citation
            assert not getattr(position, "proposed", False), (
                "a proposal sitting in a pull request is not the firm's word "
                "and must not be in the pool"
            )
