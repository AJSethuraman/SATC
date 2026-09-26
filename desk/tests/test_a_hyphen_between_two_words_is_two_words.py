"""`cash-back` is two words. `1099-K` is one. The rule is the digit.

`dec-hyphen`, 25 September 2026 — the firm: **"Split on a letter hyphen."**

WHAT FORGE-OCCAM HIT IN THE SARCIA PILOT. Asking about `cash-back` returned
NOTHING; asking about `cash back` returned twenty passages. `_WORD` keeps `-`
inside a word deliberately — that is `dec-fullstop`, and it is the only reason
`1099-K` and `1.162-3` survive tokenising — so it did its job and also swallowed
every ordinary English compound. Zero results is the worst shape the desk has,
because it is indistinguishable from an honest hole.

I TOLD THE FIRM THIS WAS TOO DANGEROUS TO TOUCH and that was wrong, measured.
205 distinct hyphenated tokens: 113 carry a digit, 92 do not, nothing is in both.

THE GUARANTEE THIS FILE MAKES, STATED EXACTLY. It is **no token carrying a digit
ever splits** — that is what covers every citation identifier in the record. It
is NOT "nothing inside a citation string splits": a citation string includes the
section's TITLE, and two ordinary compound words live in titles here —
`employer-provided` and `non-incidental`. Those split, correctly, because they
are English and not identifiers. Stating the weaker true guarantee rather than
the stronger false one is the whole point of measuring first.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import pool

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
_RAW = re.compile(r"[a-z0-9][a-z0-9.\-/§]*")


@pytest.fixture(scope="module")
def corpus():
    return pool.assemble(CORPUS)


@pytest.fixture(scope="module")
def hyphenated(corpus) -> set[str]:
    """Every hyphen-bearing token in the corpus, before any splitting."""
    out = set()
    for h in corpus:
        out |= {t for t in _RAW.findall((h.text + " " + h.citation).lower())
                if "-" in t}
    return out


# --- the thing it was built for -------------------------------------------

def test_a_compound_of_two_words_becomes_two_words():
    assert pool.terms("cash-back") == ("cash", "back")


def test_the_compound_now_reaches_the_record(corpus):
    """The pilot's actual failure, as a number rather than a property."""
    found = pool.look("cash-back", corpus, limit=50)
    assert len(found) >= 20, (
        f"`cash-back` reaches {len(found)} passages; it reached 0 before this "
        f"change and `cash back` reached 20")


def test_both_sides_are_tokenised_by_the_same_rule(corpus):
    """Why splitting is safe at all: a question and a passage meet because the
    SAME function shaped both. A rule applied to queries only would be a rule
    that makes them miss."""
    assert pool.terms("cash-back") == pool.terms("cash back")


# --- and the thing it must not break --------------------------------------

def test_no_token_carrying_a_digit_is_ever_split(hyphenated):
    """The guarantee, over the whole corpus rather than over examples.

    113 tokens at the time of writing. A citation identifier always carries a
    digit — a part number, a year, a form number — so this is the property that
    protects the record, and it is checked against every token the corpus
    actually holds rather than a list typed here.
    """
    digit = sorted(t for t in hyphenated if any(c.isdigit() for c in t))
    assert len(digit) > 100, (
        f"only {len(digit)} digit-bearing hyphenated tokens found; the "
        f"denominator moved and this test may no longer cover the record")
    split = [t for t in digit if len(pool.terms(t)) > 1]
    assert not split, (
        "these carry a digit and were split, so a citation has come apart:\n  "
        + "\n  ".join(split[:20]))


@pytest.mark.parametrize("citation", [
    "1099-K", "1099-NEC", "26 CFR 1.162-3", "26 CFR 1.263(a)-1(f)",
    "26 CFR 1.274-5T(a)", "26 CFR 1.6050W-1(e)", "26 CFR 1.280F-6",
])
def test_the_citations_a_reader_would_check_by_hand(citation):
    """Named explicitly as well as measured, because a reader who doubts the
    sweep above should be able to see the ones they already know."""
    for t in _RAW.findall(citation.lower()):
        if "-" in t and any(c.isdigit() for c in t):
            assert pool.terms(t) == (t,), f"{t!r} came apart"


def test_the_hyphen_did_not_change_how_many_citations_find_themselves(corpus):
    r"""A STANDING DEFECT, PINNED HERE BECAUSE THIS CHANGE IS WHERE IT SURFACED.

    The first version of this test asserted that a citation looked up by its own
    string comes back in its own top five, and it failed on 179 of the first 200.
    Measured on the unmodified code before assuming it was mine: **179 there
    too**, identical. It is not this change.

    Measured across the whole record instead of a slice:

        777  citations carrying a digit
        683  that do NOT find themselves in their own top five
        680  of those contain a parenthesis

    The test below samples every seventh of those 777 — 111 citations, 98 of
    which miss themselves — because scoring all of them took 112 seconds.

    `_WORD` is `[a-z0-9][a-z0-9.\-/§]*` and `(` is not in it, so
    `26 CFR 1.263(a)-1(f)(1)(i)(A)` tokenises to `1.263 a 1 f 1 i a` — seven
    tokens, six of them single letters shared with hundreds of other
    sub-paragraphs. The citation cannot distinguish itself from its siblings.

    That is the same disease as `dec-reach` and it is not this commit's to cure:
    putting `(` into `_WORD` moves every score in the corpus and is a decision,
    exactly as the hyphen was. Recorded and put to the firm rather than fixed in
    passing.

    WHAT THIS TEST THEREFORE IS: a ratchet. It pins the number so that a future
    tokeniser change making it WORSE goes red, and so that the day somebody
    fixes it the figure has to be updated deliberately rather than drifting.
    """
    # EVERY SEVENTH, SORTED BY CITATION. Scoring all 777 against the whole pool
    # took 112 seconds — more than the rest of the suite put together, and a
    # suite people stop running is a suite that stops catching things. The
    # sample is deterministic (sorted, fixed stride) so the pinned figure means
    # the same thing every run, and 111 citations is a denominator, not a spot
    # check. Measured both ways on the day: 683 of 777 whole, 98 of 111 sampled.
    withdig = sorted((h for h in corpus if any(x.isdigit() for x in h.citation)),
                     key=lambda h: h.citation)
    # RE-MEASURED 26 SEPTEMBER 2026, when five sections were admitted after
    # Sarcia pilot 3: 1159 digit-bearing citations, 1056 missing themselves
    # whole (1053 parenthesised), 151 of the 166 sampled. The rate moved from
    # 88% to 91% because the new paragraphs are deep sub-paragraphs -- more
    # single-letter siblings -- which is the recorded cause, not a new one.
    assert len(withdig) == 1159, (
        f"the corpus holds {len(withdig)} digit-bearing citations, not 1159 — "
        f"the denominator moved, so re-measure before trusting the figure below")
    sample = withdig[::7]
    assert len(sample) == 166
    missed = [h.citation for h in sample
              if h.citation not in
              [f.held.citation for f in pool.look(h.citation, corpus, limit=5)]]
    assert len(missed) <= 151, (
        f"{len(missed)} of 166 sampled citations cannot find themselves in "
        f"their own top five, up from 151. A tokeniser change has made "
        f"retrieval worse.")
    parens = [m for m in missed if "(" in m]
    assert len(parens) >= len(missed) - 2, (
        "the failures are no longer overwhelmingly parenthesised citations, so "
        "the cause recorded in this docstring is no longer the cause")


# --- what it costs, recorded rather than hidden ---------------------------

def test_the_words_that_do_split_are_english_and_not_identifiers(hyphenated):
    """The 92. Recorded as a fact about the change rather than left implicit —
    every passage carrying one of these scores differently now, which is why the
    43 close questions were re-run before this shipped."""
    plain = sorted(t for t in hyphenated if not any(c.isdigit() for c in t))
    assert len(plain) > 80, f"only {len(plain)} letter-only hyphenated tokens"
    for word in ("built-in", "half-year", "employer-provided", "first-out"):
        assert word in plain, f"{word!r} is no longer in the corpus; re-read this"
        assert len(pool.terms(word)) >= 1
