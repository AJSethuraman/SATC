"""A plain phrasing costs the asker the whole record, and the hole it files is
somebody else's problem.

MEASURED 11 SEPTEMBER 2026, ON ONE CORPUS. The same forklift, two ways:

    0 passages   "what do i do with it? we bought a forklift"
    8 passages   "we bought a forklift - is the invoice price deducted
                  or capitalized?"        (the firm's own $2,500 threshold
                                           among them)

THE CAUSE IS TWO WORDS AND IT IS EXACT. The first phrasing's only substantive
words are `bought` and `forklift`. Neither appears in any of the 785 stored
passages -- `purchase` is in 85 of them, `buy` in 11, `acquire` in 55. BM25
cannot bridge that and no retrieval can: `bought` is not a suffix away from
`buy`, and the regulations never say `forklift` because they say `equipment`
and `tangible property`.

WHAT THAT COST BEFORE THIS FILE. `consult_or_file` wrote the question into the
firm's queue of things the record cannot answer, reading *"nothing in the corpus
shares a word with this question"*. The firm reads that as a gap in their
authority and goes looking for a rule to admit. The rule is already on file.

WHAT IS DONE ABOUT IT, AND WHAT DELIBERATELY IS NOT. Both the page the doer
gets and the row the firm gets now NAME the asker's own words the record has
never seen. That is a lookup against `stats.idf`, which already counts every
word in the corpus -- a fact about the record, reported. Nothing proposes a
synonym, expands the question or rewrites it: `dec-kill` deleted a hand-written
word list, and a hand-written list of what a word means instead is the same
mechanism under a kinder name. The doer decides whether to say it differently.

AND THE LIST IS ALWAYS EXHAUSTIVE, WHICH IS A LIMIT AND IS SAID OUT LOUD. The
moment ONE word of a question is on file, some passage scores above zero and
nothing is filed at all -- so every filed hole has every word unseen, by
construction. The words therefore say which wording missed and say NOTHING
about whether a rule exists. A first draft of this claimed the gap "may be in
the wording rather than the authority" on every row, which is a guess with
evidence stapled to it. `test_the_list_is_exhaustive_by_construction` is why
that draft did not survive.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                   # noqa: E402
import pool                                                  # noqa: E402
import record                                                # noqa: E402
import unsupported                                           # noqa: E402
from conftest import CORPUS                                  # noqa: E402

PLAIN = "what do i do with it? we bought a forklift"
EXPLICIT = "we bought a forklift - is the invoice price deducted or capitalized?"


@pytest.fixture(scope="module")
def known():
    return pool.stats(pool.assemble(CORPUS))


# ── the finding itself, recomputed rather than quoted ───────────────────────

def test_the_plain_phrasing_still_costs_the_whole_record():
    """THE SYMPTOM, PINNED SO IT CANNOT IMPROVE SILENTLY. `dec-kill` was decided
    on this failure and did not fix it -- it made it worse, from one shelf of
    two to all of it. Going green with a smaller gap is the pool learning the
    plain phrasing, and then `relay.as_prompt`'s quoted numbers move too."""
    assert len(ask.looked(PLAIN, CORPUS)) == 0
    assert len(ask.looked(EXPLICIT, CORPUS)) == 8


def test_the_cause_is_two_words_and_not_the_scoring():
    """THE DIAGNOSIS, NOT THE SYMPTOM. Without this the fix reads as a guess at
    what went wrong. `purchase` is on file 85 times; the asker did not type it.
    """
    desk = record.load(CORPUS)

    def holding(word):
        return sum(1 for p in desk.passages if word in p.text.lower())

    assert holding("bought") == 0 and holding("forklift") == 0
    assert holding("purchase") > 50, (
        "the record no longer holds the rule under any wording, so this is a "
        "coverage gap now and not a vocabulary one -- which is a different "
        "finding and this file is about the other")


# ── what `unseen` is, and the two things it must never become ───────────────

def test_it_names_the_askers_own_words_and_only_those(known):
    assert pool.unseen(PLAIN, known) == ("bought", "forklift")
    for word in pool.unseen(PLAIN, known):
        assert word in pool.terms(PLAIN), (
            f"{word!r} is not in the question. This reports what the record "
            f"does not contain; the moment it returns a word the asker did not "
            f"type it is proposing, and proposing is the firm's.")


def test_it_proposes_no_synonym_however_obvious_one_is(known):
    """`purchase` is the word the authority uses, it is on file 85 times, and
    this must not say so. `dec-kill` deleted a hand-written list of what words
    mean; a list of what they mean INSTEAD is the same list."""
    out = pool.unseen(PLAIN, known)
    for tempting in ("purchase", "acquire", "equipment", "tangible", "buy"):
        assert tempting not in out


def test_a_question_the_record_has_every_word_for_names_nothing(known):
    """The other half: this must stay empty on ordinary questions, or it becomes
    a paragraph every page carries and nobody reads."""
    assert pool.unseen("what records are required for a purchase?", known) == ()


# ── and it reaches both of the people who need it ───────────────────────────

def test_the_page_the_doer_gets_says_which_words(known):
    page = ask.nothing_on_file(PLAIN, CORPUS)
    assert "`bought`" in page and "`forklift`" in page
    assert "nothing about whether a rule exists" in page, (
        "it named the words and let the reader infer the rule is probably "
        "there under other ones, which is a guess with evidence stapled to it")
    # and it still refuses to be read as a yes
    assert "This is not permission." in page


def test_the_row_the_firm_gets_says_which_words(tmp_path):
    """`tools/holes.py` reads this out. A firm told only "nothing shares a word"
    cannot tell a rule they have never written from a rule written in words the
    asker did not use, and would go admit a source they already have."""
    queue = tmp_path / "asked.md"
    _, filed = ask.consult_or_file(PLAIN, queue=queue, corpus=CORPUS)
    assert filed is not None, "it answered a question that reaches nothing"

    rows = unsupported.parse(queue.read_text(encoding="utf-8"))
    assert len(rows) == 1
    why = rows[0].working
    assert "bought" in why and "forklift" in why, (
        f"the row reads {why!r}, which is the same sentence on every hole and "
        f"cannot be sorted, compared or acted on")


def test_the_list_is_exhaustive_by_construction(known):
    """THE LIMIT OF THE WHOLE MECHANISM, PROVED RATHER THAN CONCEDED.

    One word on file means some passage scores above zero, so a question that
    reaches nothing has EVERY word unseen and there is no "some of your words
    missed" case to distinguish a wording gap from a coverage gap. Whoever
    wants that distinction has to build something this does not do, and the
    page and the row both say so rather than implying otherwise.
    """
    held = pool.assemble(CORPUS)
    for question in (PLAIN,
                     "how do we handle crypto staking rewards?",
                     "what is the firm's policy on purchase order limits?",
                     "are unidentified deposits gross receipts?"):
        hits = len(pool.look(question, held, known=known))
        every = pool.unseen(question, known) == pool.terms(question)
        assert (hits == 0) == every, (
            f"{question!r}: {hits} hits with "
            f"{'every' if every else 'not every'} word unseen. The invariant "
            f"the page's wording rests on has moved.")
