"""A worked example is labelled, and a brief is never examples alone.

`dec-examples`, 14 September 2026 — the firm, on the eighth docket: **"Label and
never examples-only."** Both halves, and the second is the one that protects the
answer.

WHAT AN EXAMPLE IS. A fact pattern the regulation prints to show a rule applied
— **somebody else's facts**. They are narrative and concrete, so they share more
words with a bookkeeper's sentence than an abstract rule does, and the pool
ranks them accordingly: examples are **260 of 786** entries and take **7 of 12**
top slots on real working questions, about twice their share.

NOTHING IN THE ENGINE KNOWS THIS CLIENT'S PAINT BOOTH IS NOT EXAMPLE 11'S PAINT
BOOTH, and nothing can — that needs the facts. So it is said rather than
decided, the same trade `passage`, `alongside` and `scoped` all make.

WHY THE LABEL ALONE IS NOT ENOUGH. An example read BESIDE its rule is the
drafter showing the rule applied. An example read INSTEAD of its rule is a
confident wrong answer waiting to happen: the answerer has a conclusion about
somebody else's facts and nothing to test it against. The label says whose facts
those are; it does not supply the rule.

THE SCORING BRIEF IS UNTOUCHED AND MUST STAY THAT WAY. `brief_for_grading`
prints no example at all, because six of these records draw their PROBLEMS from
the worked examples of the regulation they store — print them to something being
scored and the corpus carries its own answer key.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import pool                                                 # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

LABEL = "A worked example — another taxpayer's facts, not this client's."

#: A QUESTION WHOSE WHOLE BRIEF WOULD OTHERWISE BE WORKED EXAMPLES, found by
#: measuring rather than invented — see `EXAMPLES_ONLY` below. It is a recorded
#: problem, so the corpus's own answer key says what it is about.
ONLY_EXAMPLES = "A contractor paid by cheque"


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


@pytest.fixture(scope="module")
def held():
    return pool.assemble(CORPUS)


# ── the label ───────────────────────────────────────────────────────────────

def test_a_worked_example_says_whose_facts_it_is(desk, held):
    example = next(h for h in held if h.kind == record.EXAMPLE)
    one = desk.narrowed_to([example.citation])
    text = ask.brief("does this rule apply to us?", one)
    assert LABEL in text, "an example is printed with nothing marking it"
    assert text.index(LABEL) < text.index(example.text[:40]), (
        "the label prints after the example; a reader who has read the fact "
        "pattern has already mapped it onto their own client")


def test_the_label_says_what_to_do_about_it(desk, held):
    """A label that names a problem and not a remedy is a warning nobody can
    act on."""
    example = next(h for h in held if h.kind == record.EXAMPLE)
    text = ask.brief("x", desk.narrowed_to([example.citation]))
    assert "Answer from the rule" in text
    assert "say which" in text, (
        "an answerer permitted to cite an example is not told to say why it "
        "matches, which is the only thing that makes citing one checkable")


def test_a_rule_is_not_labelled_as_somebody_elses_facts(desk, held):
    rule = next(h for h in held if h.kind == record.RULE and h.text)
    text = ask.brief("x", desk.narrowed_to([rule.citation]))
    assert LABEL not in text, (
        "a rule is marked as another taxpayer's facts; a label on everything "
        "is a label on nothing")


def test_the_scoring_brief_still_withholds_every_example(desk, held):
    """Untouched by this change, and pinned beside it: the label makes examples
    safer to read, not safe to score against."""
    cites = [h.citation for h in held[:40]]
    graded = ask.brief_for_grading("x", desk.narrowed_to(cites))
    assert LABEL not in graded
    for h in held[:40]:
        if h.kind == record.EXAMPLE and h.text:
            assert h.text[:60] not in graded, (
                f"{h.citation} is printed to something being scored")


# ── never examples-only ─────────────────────────────────────────────────────

def test_a_brief_that_would_be_examples_alone_gets_a_rule():
    text = ask.consult(ONLY_EXAMPLES, CORPUS)
    assert "Every other passage this question reached is a worked example" \
        in text, "no rule was added to a brief that is otherwise all examples"


def test_the_added_rule_says_why_it_is_there():
    """MEASURED, AND IT IS THE REASON THIS NOTICE EXISTS. On the six questions
    in 113 where a brief would otherwise be examples alone, the rule pulled in
    scores as low as 3.2 — and on this one it is a MEALS rule, under a question
    about a contractor paid by cheque.

    That is the honest top-ranked rule and it is not about the question. Adding
    it silently would present it as the authority. A score cutoff would be
    picking a number by taste, which is what this retrieval was built not to do.
    So it says why it is here."""
    text = ask.consult(ONLY_EXAMPLES, CORPUS)
    assert "It may not be the right rule" in text
    assert "the record may simply not hold a rule that does" in text, (
        "the notice does not offer the reading that matters — that this is a "
        "coverage hole rather than an answer")


def test_the_rule_is_added_and_nothing_is_removed(held):
    """The alternative was dropping examples until a rule appeared, which
    throws away the most on-point thing the pool found on a question where the
    closest authority genuinely IS a fact pattern."""
    found = ask.looked(ONLY_EXAMPLES, CORPUS, limit=8)
    widened = ask.with_a_rule(ONLY_EXAMPLES, found, CORPUS)
    assert len(widened) == len(found) + 1
    assert [f.held.citation for f in widened[:-1]] == \
           [f.held.citation for f in found], "an example was dropped or moved"
    assert widened[-1].held.kind == record.RULE


def test_the_rule_comes_from_this_questions_own_ranking(held):
    """Looked for DEEPER, never wider. A rule chosen by any means other than the
    score already computed would be the retrieval answering a question it was
    not asked."""
    found = ask.looked(ONLY_EXAMPLES, CORPUS, limit=8)
    added = ask.with_a_rule(ONLY_EXAMPLES, found, CORPUS)[-1]
    whole = pool.look(ONLY_EXAMPLES, held, limit=len(held))
    rules = [f for f in whole if f.held.kind == record.RULE]
    assert added.held.citation == rules[0].held.citation, (
        "the rule added is not the highest-ranked rule this question reached")


def test_a_brief_that_already_holds_a_rule_is_untouched():
    """It must not append a second rule to a brief that has one, or every brief
    grows a tail nobody asked for."""
    q = "is the paint booth plant property?"
    found = ask.looked(q, CORPUS, limit=8)
    assert any(f.held.kind == record.RULE for f in found), "premise moved"
    assert ask.with_a_rule(q, found, CORPUS) == found
    assert "Every other passage this question reached" not in ask.consult(q,
                                                                          CORPUS)


def test_a_rule_that_does_not_exist_is_not_invented(held, monkeypatch):
    """Where the pool holds no rule sharing a word with the question, the brief
    is examples only and nothing is appended.

    THE FIRST VERSION OF THIS TEST PROVED NOTHING. It ended
    `assert ... == record.EXAMPLE or True`, which is true whatever happens — a
    hedge written because the shipped corpus has no such question and the
    fixture was awkward to build. A test that cannot fail is not a test, so the
    awkward fixture is built: a pool of examples ONLY, with the search pointed
    at it.
    """
    only_examples = tuple(h for h in held if h.kind == record.EXAMPLE)
    assert only_examples, "the corpus holds no worked examples"
    monkeypatch.setattr(
        ask, "_corpus",
        lambda where: (record.load(CORPUS), only_examples,
                       pool.stats(only_examples)))

    found = pool.look("was the roof replaced?", only_examples, limit=8,
                      known=pool.stats(only_examples))
    assert found and all(f.held.kind == record.EXAMPLE for f in found), (
        "the fixture is not examples-only")
    assert ask.with_a_rule("was the roof replaced?", found, CORPUS) == found, (
        "a rule was appended from a pool that holds none — the only way to do "
        "that is to have gone somewhere other than this question's own ranking")


def test_nothing_comes_back_for_nothing():
    assert ask.with_a_rule("x", (), CORPUS) == ()


# ── the cost, measured on the whole denominator ─────────────────────────────

#: HOW MANY QUESTIONS WOULD GET A BRIEF OF WORKED EXAMPLES AND NOTHING ELSE, at
#: the default of eight hits, over the fifteen working questions plus all 98
#: recorded problems. Measured 14 September 2026 at desk 0.32.0.
#:
#: IT IS SMALL AT EIGHT AND LARGE WHEN THE BRIEF IS SHORTER: 6 of 113 at eight,
#: 13 at five, 25 at three. Recorded because the first four questions tried by
#: hand were all fine, and a check built on those would have shipped a guard
#: that never fires while reading as though it did.
# THREE SINCE 26 SEPTEMBER 2026, down from six: admitting §§ 1.6001-1, 1.164-1,
# 1.461-1, 1.263(a)-4 and 1.163-8T gave three of those questions a rule to reach.
EXAMPLES_ONLY = 3
ASKED = 113


def test_the_count_is_measured_and_does_not_go_stale(desk, held):
    stats = pool.stats(held)
    working = [
        "what records are required for a charge with only a vendor name?",
        "charge on the bank statement with no receipt or invoice - what "
        "records are required?",
        "we do not know what was bought - can we deduct it?",
        "the client took cash out of the ATM and we do not know what for",
        "is a payment to a credit card we have no statement for a business "
        "cost?",
        "unlabelled deposits into the business account - are they all revenue?",
        "the owner paid the company card from a personal account, what is that?",
        "a cheque with no payee on the feed - how do we book it?",
        "hand tools bought for the trade - deducted or capitalized?",
        "beer at a taproom with a customer - is it deductible?",
        "mileage or actual expenses for the van?",
        "cash back on the business card - income?",
        "what supporting documents does the client have to keep?",
        "the statement cycle closes on the 2nd, what is the opening balance at "
        "1 January?",
        "groceries on the business card - business or personal?",
    ]
    asked = working + [p.title for p in desk.problems]
    assert len(asked) == ASKED
    bare = [q for q in asked
            if (f := pool.look(q, held, limit=8, known=stats))
            and all(x.held.kind == record.EXAMPLE for x in f)]
    assert len(bare) == EXAMPLES_ONLY, (
        f"{len(bare)} of {ASKED} questions reach worked examples and nothing "
        f"else; this file says {EXAMPLES_ONLY}. Down is the record gaining a "
        f"rule those questions reach. Up is a rule having been removed, or "
        f"examples having been added around one.\n  " + "\n  ".join(bare))
    for q in bare:
        assert "Every other passage this question reached" in ask.consult(
            q, CORPUS), f"{q!r} still gets a brief of examples alone"
