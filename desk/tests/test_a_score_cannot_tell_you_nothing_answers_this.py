"""No cutoff on the pool's score separates "answered here" from "not on file".

WHY THIS TEST EXISTS RATHER THAN A CONSTANT. `pool.look` returns something for
almost any question, and `routing`'s docstring is right that a retrieval which
always answers is one whose answer means nothing. The obvious fix is a floor:
below score X, return nothing. `dec-coverage` -- the firm's *"say why silence is
silence"* -- appears to need one, because a mechanism that never goes silent has
nothing to explain.

SO IT WAS MEASURED BEFORE IT WAS BUILT, and it does not work. Nine questions
whose authority IS in the corpus against six nothing on file settles:

    answerable    top score   5.86 .. 20.17
    not on file   top score   5.41 .. 13.06

Five of the six unanswerable questions outscore the weakest answerable one.
*"The statement cycle closes on the 2nd, what is the opening balance at
1 January?"* -- which no tax authority anywhere addresses -- scores 13.06, above
six of the nine questions the corpus really can answer. There is no line to
draw.

WHAT THAT MEANS, AND IT IS THE USEFUL PART. A retrieval score measures how much
of the question's language appears in a passage. It is not evidence that the
passage ANSWERS the question, and no amount of tuning makes it into that. The
words *deposit*, *statement* and *balance* are all over a corpus about
bookkeeping records; a question built from them scores well whether or not
anything in it decides the matter.

So silence is not the retriever's to declare. **"Nothing on file answers this"
is established downstream** -- by the engine refusing, by a second reader saying
the paragraph does not carry the conclusion -- and that is exactly the shape the
firm has described from the start: it GOES AND LOOKS, conveys what it found and
how binding it is, and escalates what does not bind (`dec-books`). A threshold
here would be this module deciding, on a word count, something the whole engine
exists to decide properly.

THE NUMBERS BELOW ARE A MEASUREMENT, NOT A TARGET. They will move when the
corpus grows. What must not move is the CONCLUSION -- that the two populations
overlap -- so that is what is asserted, with a margin, rather than any score.
"""

from pathlib import Path

import pytest

import pool


CORPUS = Path(__file__).resolve().parent.parent / "corpus"

#: The authority is on file. The first six are Forge-Occam's own phrasings from
#: their field report of 9 September 2026; the last three are ordinary close
#: questions whose regulation the corpus holds.
ANSWERABLE = [
    "what supporting documents does the client have to keep?",
    "what supporting documents must be kept?",
    "recordkeeping for business expenses",
    "what receipts do we need to keep?",
    "supporting documents for a bank statement charge",
    "what kinds of records to keep for a bank account?",
    "hand tools bought for the trade - deducted or capitalized?",
    "beer at a taproom with a customer - is it deductible?",
    "mileage or actual expenses for the van?",
]

#: Nothing on file settles these. The first is `dec-kill`'s own question, and
#: the decision says so in as many words: nothing in the corpus decides whether
#: an unidentified deposit is revenue. The rest are bookkeeping mechanics that
#: no tax authority addresses.
NOT_ON_FILE = [
    "are unidentified deposits gross receipts?",
    "we do not know what was bought - can we deduct it?",
    "unlabelled deposits into the business account - are they all revenue?",
    "a cheque with no payee on the feed - how do we book it?",
    "the statement cycle closes on the 2nd, what is the opening balance at 1 January?",
    "the client took cash out of the ATM and we do not know what for",
]


@pytest.fixture(scope="module")
def held():
    return pool.assemble(CORPUS)


@pytest.fixture(scope="module")
def known(held):
    return pool.stats(held)


def _top(question, held, known) -> float:
    found = pool.look(question, held, limit=1, known=known)
    return found[0].score if found else 0.0


def test_no_cutoff_separates_the_two_populations(held, known):
    """The measurement, asserted as an overlap rather than as a number."""
    answerable = [_top(q, held, known) for q in ANSWERABLE]
    absent = [_top(q, held, known) for q in NOT_ON_FILE]

    assert min(answerable) > 0, "an answerable question returned nothing"
    over = [s for s in absent if s >= min(answerable)]
    assert over, (
        "the two populations have separated, which would mean a score floor "
        "COULD declare silence. That is a real change and a good one — but it "
        "makes this file's conclusion false, so read the docstring and decide "
        "deliberately rather than deleting the assertion"
    )
    assert len(over) >= len(absent) // 2, (
        f"only {len(over)} of {len(absent)} unanswerable questions outscore the "
        f"weakest answerable one; the overlap is narrowing and the design note "
        f"in this file should be revisited"
    )


def test_the_sharpest_single_case(held, known):
    """One question carries the whole argument, so it is asserted alone.

    *"The statement cycle closes on the 2nd, what is the opening balance at
    1 January?"* is a bookkeeping mechanics question. No tax authority anywhere
    in this corpus decides it. It nonetheless outscores most of the questions
    the corpus genuinely answers, because `statement`, `balance` and `closes`
    are everywhere in a record about keeping books.
    """
    mechanics = _top("the statement cycle closes on the 2nd, what is the "
                     "opening balance at 1 January?", held, known)
    beaten = [q for q in ANSWERABLE if _top(q, held, known) < mechanics]
    assert len(beaten) >= 3, (
        f"a question nothing on file answers outscores only {len(beaten)} of "
        f"the {len(ANSWERABLE)} it does; the overlap this file documents has "
        f"changed shape"
    )


def test_the_pool_does_not_secretly_have_a_floor(held, known):
    """`look` must keep returning what it found, however weak.

    If a floor is ever added it has to be a caller's decision made on evidence,
    visible at the call site — not a constant inside the retrieval that makes
    every downstream count wrong in a way nobody can see.
    """
    weak = pool.look("balance", held, limit=5, known=known)
    assert weak, "a single common word returned nothing; a floor has appeared"
    assert min(f.score for f in weak) > 0
