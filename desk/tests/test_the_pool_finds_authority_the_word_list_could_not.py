"""The pool answers `dec-kill`, and the desk's name is not how it finds anything.

    `dec-kill`, 8 September 2026 -- "Kill the desks; one pool." Decided on a
    measurement: the deposits question written six ways reached no desk three
    times and the WRONG desk twice. Forge-Occam: "The word that saved me was
    'bank'."

    `dec-order`, 9 September -- "Build the pool beside the desks; switch on
    evidence." THE SENTENCE THAT FOLLOWED IT IN THE LOG -- "so `dec-kill` is a
    decided destination and not an immediate demolition" -- was this session's
    and not the firm's, and it worked as a three-day reprieve for the word list.
    Withdrawn 10 September: *"I said to delete them. I've said to multiple
    times."* The desks are gone.

EVERY QUESTION IN THIS FILE WAS ACTUALLY ASKED. They are Forge-Occam's, verbatim
from their field report of 9 September, and `dec-kill`'s own. Not one is
invented, and that is the point: the previous test in this repository built from
imagined phrasings widened the vocabulary by nineteen words to satisfy sentences
nobody had ever typed, and six plain bookkeeping questions started being
answered out of tax law as a result.

WHAT IS ASSERTED AND WHAT IS DELIBERATELY NOT. Asserted: the authority Occam's
own desk said it needed is reachable without the word that saved them, and the
matching never reads a desk name. NOT asserted: that the pool beats the word
list by some number. That comparison was printed by `tools/pool_vs_routing.py`
with its denominator; it went with the word list, because half of a comparison
cannot be re-run. What is frozen instead is the finding it produced, in
`docs/POOL-VS-ROUTING-2026-09-10.md`, and a frozen finding is honest where a
frozen assertion would be a test nobody can fail.
"""

from pathlib import Path

import pytest

import pool

CORPUS = Path(__file__).resolve().parent.parent / "corpus"

#: The authority `personal-or-business` reported it wanted, escalating
#: `authority_absent` after two independent judges refused two different
#: citations. It sits on `cash-and-bank`, and its recordkeeping guidance is not
#: bank-specific -- it is the general rule for substantiating a business expense.
PUB_583 = "IRS Pub. 583"


@pytest.fixture(scope="module")
def held():
    return pool.assemble(CORPUS)


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


#: THE CONTRAST THIS FILE WAS NAMED FOR, AND IT IS NO LONGER A TEST.
#: `test_the_word_list_could_not_reach_it` asserted the OLD mechanism's failure
#: -- `routing.route("what supporting documents does the client have to keep?")`
#: reached no desk at all -- because that failure is what `dec-kill` was decided
#: on. Its own docstring said it "dies with `routing` and is expected to". It
#: did, on 10 September 2026. The measurement is in
#: `docs/POOL-VS-ROUTING-2026-09-10.md` with its denominator; nothing here
#: pretends to re-run it.


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
    answer means nothing -- `routing`'s docstring was right about that, and
    killing the word list did not change it. IT IS ALSO NOT YET SOLVED: nothing
    here claims the pool is silent on a question it merely cannot answer, only
    on one it shares no words with. See
    `test_a_score_cannot_tell_you_nothing_answers_this.py`."""
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
