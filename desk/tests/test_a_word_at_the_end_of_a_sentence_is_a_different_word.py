"""A KNOWN DEFECT, PINNED ON PURPOSE, WITH WHAT IT COSTS AND WHAT FIXING IT
WOULD MOVE. It is not fixed here, and the reason is on the docket.

`pool._WORD` is `[a-z0-9][a-z0-9.\\-/§]*`. The `.`, `-` and `/` are inside it so
a citation survives tokenising whole -- `1.263(a)-3`, `Pub. 583`, `1099-K`. They
are allowed at the END of a token too, and nothing is a full stop at its close.
So a word that ends a sentence is indexed as a different word from the same word
in the middle of one.

IRS Pub. 525's own section opens *"Rewards. If you receive a reward for
providing information..."*. The pool holds `rewards.`; a question types
`rewards`; it reaches that section never. `how do we handle crypto staking
rewards?` comes back with NOTHING, and `ask.consult_or_file` files it to the
firm as a hole in their authority. They hold the section. It is named after the
word.

WHY IT IS STILL HERE. Stripping the trailing punctuation is two lines and it is
plainly right. It also REORDERS WHICH AUTHORITY IS SERVED on fourteen of
nineteen real questions, and costs one commissioned pairing outright -- both
measured below. The firm has an open decision (`dec-guidance-narrow`) about
which authority gets served, and moving the retrieval underneath a question they
are in the middle of answering is not a fix, it is the ground shifting. So the
defect is pinned the way the routing defects were pinned before `dec-kill`: the
measurement lives here, it is re-run every suite, and the firm's answer is one
line in `pool.terms`.

THE MEASUREMENT IS RE-RUN, NEVER QUOTED. Every figure in this file is computed
against the shipped corpus, so it cannot go stale in the direction that flatters
the defect.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import pool                                                  # noqa: E402
from conftest import CORPUS                                  # noqa: E402

#: What a fix would be, in full. Kept here rather than in `pool` so there is
#: exactly one definition of "the fix" and the numbers below are that fix's.
TRAILING = "./-"


def _fixed(text: str) -> tuple[str, ...]:
    out = []
    for match in pool._WORD.finditer(text):
        word = match.group(0).lower()
        if word in pool.STOPWORDS:
            continue
        word = word.rstrip(TRAILING)
        if word and word not in pool.STOPWORDS:
            out.append(word)
    return tuple(out)


class _Pool:
    """A pool built and SEARCHED under one tokeniser.

    `pool.look` calls `terms` on the question and on every passage at search
    time, so swapping the tokeniser only while building gives a fixed index
    searched with the shipped tokeniser — which is neither arrangement and
    silently answers like the shipped one. The first version of this file did
    exactly that and reported that the fix changed nothing.
    """

    def __init__(self, fn):
        self.fn = fn
        self.held = self._as(lambda: pool.assemble(CORPUS))
        self.stats = self._as(lambda: pool.stats(self.held))

    def _as(self, run):
        was, pool.terms = pool.terms, self.fn
        try:
            return run()
        finally:
            pool.terms = was

    def look(self, question, **kw):
        return self._as(
            lambda: pool.look(question, self.held, known=self.stats, **kw))


@pytest.fixture(scope="module")
def both():
    """`(as shipped, as fixed)`, each built and searched under its own rules."""
    return _Pool(pool.terms), _Pool(_fixed)


# ── the defect is real and it is not theoretical ────────────────────────────

def test_the_word_a_section_is_named_after_cannot_be_typed(both):
    """Pub. 525's `Rewards` section, reached by nobody who asks about rewards."""
    shipped, fixed = (p.stats for p in both)
    assert "rewards." in shipped.idf, (
        "the corpus no longer holds a token with a trailing stop here; either "
        "the extraction changed or this was fixed. Check the docket matter "
        "before deleting this file.")
    assert "rewards" not in shipped.idf
    assert "rewards" in fixed.idf and "rewards." not in fixed.idf


def test_a_real_question_reaches_nothing_because_of_it(both):
    shipped, fixed = both
    q = "how do we handle crypto staking rewards?"
    assert len(shipped.look(q)) == 0, (
        "it reaches something now — which is good news, and the docket matter "
        "and `ask.nothing_on_file`'s example both have to move with it")
    assert len(fixed.look(q)) >= 1


def test_how_many_words_of_the_corpus_are_unreachable(both):
    """THE SIZE OF IT, COUNTED. A defect described and not counted is one
    nobody can weigh against its fix."""
    shipped = both[0].stats
    punctuated = [w for w in shipped.idf if w.rstrip(TRAILING) != w]
    lone = [w for w in punctuated if w.rstrip(TRAILING)
            and w.rstrip(TRAILING) not in shipped.idf]
    assert len(shipped.idf) > 4000
    assert len(punctuated) > 700, (
        f"{len(punctuated)} punctuated tokens; this said 814 on 11 September "
        f"2026 and a large fall means the extraction changed")
    assert len(lone) > 100, (
        f"{len(lone)} words exist ONLY in their punctuated form and can be "
        f"reached by no question at all; this said 128 on 11 September 2026")


# ── and what fixing it would move, so the firm decides on numbers ───────────

def _asked() -> dict[int, str]:
    """The close's own questions, read the way `test_close_questions` reads
    them — not rephrased, and not a second copy of the list."""
    import test_close_questions as close
    return close._asked()


def test_the_fix_reorders_most_real_questions(both):
    """FOURTEEN OF NINETEEN CHANGED WHAT CAME BACK AND NONE CHANGED HOW MANY.
    That is the whole argument for putting this to the firm rather than shipping
    it: it is not a defect fix nobody would notice, it is most answers."""
    shipped, fixed = both
    from test_a_question_nothing_classifies_fails_closed import WORKING

    questions = list(WORKING) + [
        "what do i do with it? we bought a forklift",
        "we bought a forklift - is the invoice price deducted or capitalized?",
        "how do we handle crypto staking rewards?",
        "are unidentified deposits gross receipts?"]

    moved = 0
    for q in questions:
        a = tuple(f.held.citation for f in shipped.look(q))
        b = tuple(f.held.citation for f in fixed.look(q))
        if a != b:
            moved += 1
    assert len(questions) == 19
    assert moved >= 12, (
        f"{moved} of 19 questions change; this said 14 on 11 September 2026. A "
        f"much smaller number means the fix is cheaper than the docket says.")


def test_the_fix_costs_one_commissioned_pairing(both):
    """AND THE PRICE, NAMED. Q18 — *"Does a hardware-store purchase ever become
    an asset?"* — is commissioned against the capitalization rule and reaches
    `1.162-3(h) Example 6` at rank six today. Under the fix, Pub. 583's
    "Supporting Documents" enters at the top and pushes it past the shipped
    depth of eight. `test_close_questions` would go from 15 of 16 to 14.

    NOT ARGUED AWAY. Pub. 583 is arguably a fair hit for a question whose own
    words end *"a bank feed has none"* — and deciding that would be this session
    marking its own paper, which is the rule that file already applies to Q31.
    """
    import test_close_questions as close
    shipped, fixed = both
    question = _asked()[18]
    wanted = close.HELD[close.COMMISSIONED[18]]

    def reaches(built):
        return any(f.held.citation.startswith(p)
                   for f in built.look(question, limit=8) for p in wanted)

    assert reaches(shipped), "Q18 no longer reaches it as shipped either"
    assert not reaches(fixed), (
        "the fix no longer costs Q18 — good news, and the docket matter's "
        "recommendation should change with it")
