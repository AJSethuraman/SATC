"""`dec-fullstop`, 11 September 2026 — the firm: **"Fix it after Matter 2."**

THE DEFECT, NOW FIXED. `pool._WORD` is `[a-z0-9][a-z0-9.\\-/§]*`. The `.`, `-`
and `/` are inside it so a citation survives tokenising whole — `1.263(a)-3`,
`Pub. 583`, `1099-K`. They were allowed at the END of a token too, and nothing
is a full stop at its close, so a word finishing a sentence was indexed as a
different word from the same word in the middle of one.

IRS Pub. 525's own section opens *"Rewards. If you receive a reward for
providing information..."*. The pool held `rewards.`; a question typed
`rewards`; it reached that section never, and `ask.consult_or_file` filed the
question to the firm as a hole in authority they hold, in a section named after
the word.

THE ANSWER WAS AN ORDERING, NOT A YES. The firm did not say fix it or leave it:
they said fix it AFTER the guidance gate was narrowed, because both changes move
which authority is served and measuring the second against the first's corpus is
how a figure gets quoted that was never true of anything. The narrowing landed
first and the interaction was then measured rather than assumed — 97 of 98
served either way, so there was none. The precaution was right and the answer
was no.

WHY THIS FILE IS STILL HERE NOW THAT IT IS FIXED. Because the fix cost
something, and a cost paid once and then forgotten is a cost nobody can weigh if
the question comes back. Every figure below is recomputed against the shipped
corpus and against the old tokeniser, held side by side.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import pool                                                  # noqa: E402
from conftest import CORPUS                                  # noqa: E402


def _unfixed(text: str) -> tuple[str, ...]:
    """The tokeniser as it stood until 11 September 2026. Kept here rather than
    described, so the comparisons below are against the real thing."""
    return tuple(w.group(0).lower() for w in pool._WORD.finditer(text)
                 if w.group(0).lower() not in pool.STOPWORDS)


class _Pool:
    """A pool built and SEARCHED under one tokeniser.

    `pool.look` calls `terms` on the question and on every passage at search
    time, so swapping the tokeniser only while building gives an index of one
    shape searched with the other — which is neither arrangement and silently
    answers like the shipped one. The first version of this file did exactly
    that and reported that the change made no difference.
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
    """`(as shipped, as it was)`, each built and searched under its own rules."""
    return _Pool(pool.terms), _Pool(_unfixed)


# ── the fix is applied, and it is the tokeniser and nothing more ────────────

def test_a_word_is_the_same_word_wherever_it_sits_in_a_sentence():
    assert pool.terms("Rewards. If you receive a reward") == (
        "rewards", "receive", "reward")


def test_punctuation_inside_a_word_still_survives():
    """The `.`, `-` and `/` are in `_WORD` for a reason, and stripping at the
    END must not become stripping in the middle.

    `1.263(a)-3` does NOT survive whole and never did — `(` is not in `_WORD`,
    so it has always split at the paren into `1.263` and `3`. That is a separate
    thing and is not what this change touched; asserting otherwise here would
    have made this file claim a fix it does not contain.
    """
    got = pool.terms("See 26 CFR 1.263(a)-3 and Pub. 583 and the 1099-K.")
    assert "1.263" in got          # internal dot kept
    assert "1099-k" in got         # internal hyphen kept, trailing stop gone
    assert "pub" in got            # `Pub.` loses its dot, and so does a query's
    assert "12/2024" in pool.terms("IRS Pub. 583 (12/2024)")


def test_it_is_not_a_stemmer_and_must_not_become_one():
    """`bought` still does not reach `buy`. Undoing a tokenising accident is
    not deciding that two different words mean the same thing, and that second
    thing is the word list `dec-kill` deleted."""
    assert pool.terms("we bought a forklift") == ("bought", "forklift")


def test_the_word_a_section_is_named_after_can_now_be_typed(both):
    shipped, was = (p.stats for p in both)
    assert "rewards" in shipped.idf and "rewards." not in shipped.idf
    assert "rewards." in was.idf and "rewards" not in was.idf, (
        "the corpus no longer holds a sentence-final `rewards`, so this proves "
        "nothing about the defect it was written for — check the extraction")


def test_the_question_that_reached_nothing_now_reaches_it(both):
    shipped, was = both
    q = "how do we handle crypto staking rewards?"
    assert len(was.look(q)) == 0
    hits = shipped.look(q)
    assert hits, "the fix no longer recovers the case it was measured on"
    assert any("Pub. 525" in f.held.citation for f in hits)


# ── what it recovered, counted ──────────────────────────────────────────────

def test_how_many_words_it_gave_back(both):
    """A fix described and not counted is one nobody can weigh against its
    cost."""
    shipped, was = (p.stats for p in both)
    punctuated = [w for w in was.idf if w.rstrip(pool._TRAILING) != w]
    lone = [w for w in punctuated if w.rstrip(pool._TRAILING)
            and w.rstrip(pool._TRAILING) not in was.idf]

    assert len(punctuated) > 700, (
        f"{len(punctuated)} punctuated tokens before the fix; this said 814 on "
        f"11 September 2026 and a large fall means the extraction changed")
    assert len(lone) > 100, (
        f"{len(lone)} words were reachable by no question at all; this said "
        f"128 on 11 September 2026")
    # and none of them survives
    assert not [w for w in shipped.idf if w.rstrip(pool._TRAILING) != w]
    assert len(shipped.idf) < len(was.idf), (
        "the vocabulary did not shrink, so the duplicate forms did not collapse")


# ── and what it cost, which is why this file outlives the fix ───────────────

def _asked() -> dict[int, str]:
    """The close's own questions, read the way `test_close_questions` reads
    them — not rephrased, and not a second copy of the list."""
    import test_close_questions as close
    return close._asked()


def test_it_reordered_most_real_questions(both):
    """FOURTEEN OF NINETEEN CHANGED WHAT CAME BACK AND NONE CHANGED HOW MANY.
    That is why this went to the firm rather than shipping as a tidy-up."""
    shipped, was = both
    from test_a_question_nothing_classifies_fails_closed import WORKING

    questions = list(WORKING) + [
        "what do i do with it? we bought a forklift",
        "we bought a forklift - is the invoice price deducted or capitalized?",
        "how do we handle crypto staking rewards?",
        "are unidentified deposits gross receipts?"]

    moved = sum(
        1 for q in questions
        if tuple(f.held.citation for f in shipped.look(q))
        != tuple(f.held.citation for f in was.look(q)))
    assert len(questions) == 19
    assert moved >= 12, (
        f"{moved} of 19 questions moved; this said 14 on 11 September 2026. A "
        f"much smaller number means the fix cost less than the record says.")


def test_the_price_was_one_commissioned_pairing_and_it_is_named(both):
    """THE COST, PAID AND RECORDED. Q18 — *"Does a hardware-store purchase ever
    become an asset?"* — is commissioned against the capitalization rule and
    reached § 1.162-3(h) Example 6 at rank six. Pub. 583's "Supporting
    Documents" now enters at the top and pushes it past the shipped depth of
    eight, so `test_close_questions` reads 14 of 16 rather than 15.

    NOT ARGUED AWAY. Pub. 583 is arguably a fair hit for a question whose own
    words end *"a bank feed has none"* — and deciding that would be this session
    marking its own paper, which is the rule that file already applies to Q31.
    """
    import test_close_questions as close
    shipped, was = both
    question = _asked()[18]
    wanted = close.HELD[close.COMMISSIONED[18]]

    def reaches(built):
        return any(f.held.citation.startswith(p)
                   for f in built.look(question, limit=8) for p in wanted)

    assert reaches(was), "Q18 did not reach it before either"
    assert not reaches(shipped), (
        "Q18 reaches its commissioned authority again — good news, and "
        "`test_close_questions.UNREACHED` has to lose 18 with it")
    assert 18 in close.UNREACHED
