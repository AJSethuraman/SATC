"""A passage whose own first words say it applies somewhere else is marked.

`dec-scoped`, 14 September 2026 — the firm, on the eighth docket: **"Mark
them."** The card offered demoting them and they did not pick it.

THE INSTANCE, and it is the one they were shown. `26 CFR 1.263(a)-3(h)(3)(iv)`
is headed *"Definition of gross receipts"* and really does define the term. Its
first words are *"For purposes of applying paragraph (h)(3)(i) of this
section"* — the small-taxpayer safe harbour for **building improvements**. It is
a turnover threshold, borrowed for one narrow purpose.

Asked *are unidentified deposits gross receipts?* it is the pool's top hit, and
Pub. 583 — the authority that actually reaches the question — is fifth. An
answer resting on it served **primary, binding and wrong** in Forge-Desk's
deliberate trap on 0.27.0.

A CLASS, NOT AN INSTANCE. Measured here rather than asserted: see
`test_the_count_is_measured_and_does_not_go_stale`.

WHY MARKING AND NOT DEMOTING, which is the whole decision. Demoting is tuning a
ranking by taste, and `pool.py`'s own docstring is why that is not on the table:
*"THE POOL RANKS AND DOES NOT CHOOSE."* Reading a clause the drafter wrote is a
comparison — deterministic, re-runnable, and a wrong mark is a defect somebody
can point at rather than an opinion. `test_marking_a_passage_moves_nothing` is
what holds that line, because "and demote them a little" is the obvious next
commit and it is the one the firm declined.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import conftest                                             # noqa: E402
import engine                                               # noqa: E402
import pool                                                 # noqa: E402
from conftest import CORPUS                                 # noqa: E402


@pytest.fixture(scope="module")
def held():
    return pool.assemble(CORPUS)


#: THE SIX THE FIRM WAS SHOWN ON THE DOCKET, with the probe each was found by.
#: Not invented here: these are the rows on the card they answered.
SHOWN = [
    ("26 CFR 1.263(a)-3(h)(3)(iv)", "are unidentified deposits gross receipts?"),
    ("26 CFR 1.263(a)-1(f)(4)",
     "does the client have an applicable financial statement?"),
    ("26 CFR 1.263(a)-3(h)(3)(i)", "is this client a qualifying taxpayer?"),
    ("26 CFR 1.280F-6(a)(3)", "was the van employee use?"),
    ("26 CFR 1.263(a)-3(e)(3)(iii)(A)", "are the cables network assets?"),
    ("26 CFR 1.263(a)-3(e)(3)(ii)(A)", "is the paint booth plant property?"),
]


# ── the clause is read off the passage's own words ──────────────────────────

@pytest.mark.parametrize("citation,_probe", SHOWN)
def test_every_passage_the_firm_was_shown_is_marked(held, citation, _probe):
    entry = next((h for h in held if h.citation == citation), None)
    assert entry is not None, f"{citation} is no longer in the record"
    assert entry.scoped, (
        f"{citation} opens by scoping itself and carries no mark; this is one "
        f"of the six rows on the docket the firm answered")
    assert entry.scoped.lower().startswith("for purposes of")


def test_the_mark_is_the_drafters_words_and_not_a_description(held):
    entry = next(h for h in held if h.citation == "26 CFR 1.263(a)-3(h)(3)(iv)")
    assert entry.scoped == ("For purposes of applying paragraph (h)(3)(i) of "
                            "this section")
    assert entry.scoped in " ".join(entry.text.split()), (
        "the mark must be text the passage actually contains, or it is a "
        "summary and a reader cannot check it against the authority")


def test_a_definition_whose_clause_ends_in_a_colon_is_still_caught(held):
    """`1.280F-6(d)(2)(ii)(C)` opens *"Definitions. For purposes of this
    paragraph:"*. The first pattern ended on `.` or `,` and missed it — a
    self-scoping definition, which is the exact class this exists for."""
    entry = next(h for h in held
                 if h.citation == "26 CFR 1.280F-6(d)(2)(ii)(C)")
    assert entry.scoped == "For purposes of this paragraph"


def test_a_passage_that_does_not_scope_itself_carries_no_mark(held):
    """The other half. A mark on everything is a mark on nothing, and the
    reader stops seeing it."""
    plain = [h for h in held if not h.scoped]
    assert len(plain) > len(held) / 2, (
        "more than half the corpus is marked as scoped, which means the "
        "pattern is matching something other than a self-scoping clause")
    pub583 = [h for h in held if h.citation.startswith("IRS Pub. 583")]
    assert pub583 and not any(h.scoped for h in pub583), (
        "a plain-English publication is being marked as scoping itself")


def test_a_mid_sentence_cross_reference_is_not_a_scope():
    """THE DIFFERENCE THAT COST NINE PASSAGES, and it is a real one.

    `1.162-3(a)(3)` says *"...except as provided in paragraphs (d), (e), and
    (f) of this section, for purposes of paragraph (a)(1)..."* — a
    cross-reference INSIDE a rule, pointing at where a sub-clause applies. The
    passage is not announcing its own reach, and marking it would tell a reader
    the rule is narrower than it is.

    Measured against the looser test used on the docket: 36 passages contain
    such a phrase in their first 300 characters; 28 OPEN with one."""
    assert pool.scope_of(
        "(3) Except as provided in paragraphs (d), (e), and (f) of this "
        "section, for purposes of paragraph (a)(1) of this section, amounts "
        "paid to acquire are deducted.") == ""
    assert pool.scope_of(
        "Definition. For purposes of this paragraph (e), the term plant "
        "property means functionally interdependent machinery."
    ) == "For purposes of this paragraph (e)"


def test_nothing_in_an_empty_or_missing_passage(held):
    assert pool.scope_of("") == ""
    assert pool.scope_of(None) == ""
    licensed = [h for h in held if not h.text]
    assert all(not h.scoped for h in licensed), (
        "a citation held with no stored text cannot have been read")


# ── and it changes nothing about what comes back ────────────────────────────

def test_marking_a_passage_moves_nothing(held):
    """THE LINE THE FIRM DREW, and the reason this file exists at all.

    They were offered "Demote them" and declined it. So the mark must be
    provenance for the reader and must never reach the matching path — not as a
    score, not as a tie-break, not as a filter. If a later session adds "and
    push scoped definitions down a little", this goes red.
    """
    stats = pool.stats(held)
    stripped = tuple(
        __import__("dataclasses").replace(h, scoped="") for h in held)
    for _cite, probe in SHOWN:
        with_mark = pool.look(probe, held, limit=8, known=stats)
        without = pool.look(probe, stripped, limit=8, known=pool.stats(stripped))
        assert [f.held.citation for f in with_mark] == \
               [f.held.citation for f in without], (
            f"the order changed for {probe!r}; marking must not rank")
        assert [round(f.score, 9) for f in with_mark] == \
               [round(f.score, 9) for f in without], (
            f"a score changed for {probe!r}; marking must not score")


def test_the_scoped_definition_still_ranks_first(held):
    """Stated rather than left implied, because it is the uncomfortable half of
    the firm's answer: marking does NOT fix the ranking, and they knew that when
    they picked it. The defect is still there; the reader is now told."""
    top = pool.look("are unidentified deposits gross receipts?", held, limit=1)
    assert top[0].held.citation == "26 CFR 1.263(a)-3(h)(3)(iv)"
    assert top[0].held.scoped, "it ranks first and says nothing about its scope"


# ── it reaches the reader ───────────────────────────────────────────────────

def test_the_mark_is_printed_above_the_passage_in_a_served_answer():
    """RUN AND READ, not asserted off the dataclass. The mark exists to be seen
    by somebody about to rely on the wrong rule; a field nothing prints is a
    field that changed nothing.

    This is Forge-Desk's own trap from 0.27.0, which served `primary · binding`
    and wrong."""
    out = conftest.answer_judged(
        "are unidentified deposits gross receipts?",
        position="yes - unidentified deposits are gross receipts and are "
                 "booked to sales",
        citation="26 CFR 1.263(a)-3(h)(3)(iv)", keep=False)
    text = str(out)
    assert out.scoped, "the served answer does not carry the scope"
    mark = text.find("THIS PASSAGE SAYS IT APPLIES")
    body = text.find("THE AUTHORITY, in full:")
    assert mark > 0, "the scope is not printed to the reader"
    assert mark < body, (
        "the scope prints below the passage; a reader who has read 2,000 "
        "characters of definition has already decided what it is about")
    assert "PARAGRAPH (H)(3)(I)" in text, "the mark does not name what it scopes to"
    assert "nothing has checked" in text, (
        "the mark reads as a verdict; the engine has not looked at the facts "
        "and must not imply it has")


def test_an_unscoped_answer_prints_no_mark():
    """A caveat that appears on every answer is one nobody reads."""
    # CD1, a recorded problem answered with its own recorded citation. Chosen
    # because it SERVES: the first citation tried here refused on the guidance
    # gate, which would have made this pass for a reason that has nothing to do
    # with scoping.
    out = conftest.answer_judged(
        "Ten printers at $250, no financial statement",
        position="the de minimis safe harbor applies; the amount is not "
                 "capitalized",
        citation="26 CFR 1.263(a)-1(f)(1)(ii)", keep=False)
    assert isinstance(out, engine.Served), (
        "this must be a SERVED answer, or it proves nothing about what a "
        "served answer prints")
    assert not out.scoped
    assert "THIS PASSAGE SAYS IT APPLIES" not in str(out)


# ── the cost, measured rather than remembered ───────────────────────────────

#: HOW MANY PASSAGES OPEN BY SCOPING THEMSELVES. Measured 14 September 2026 at
#: desk 0.29.0, over 786 entries.
#:
#: THE DOCKET SAID 36 AND THIS SAYS 28, and the difference is not a correction
#: to hide. 36 counted a scoping phrase ANYWHERE in a passage's first 300
#: characters, which sweeps in thirteen mid-sentence cross-references — a rule
#: pointing at where one of its own sub-clauses applies, which is not the
#: passage announcing its reach. 28 is the narrower and right thing. All six
#: rows the firm was shown are inside it.
# FORTY-TWO SINCE 26 SEPTEMBER 2026: the five sections admitted after Sarcia
# pilot 3 carry fourteen paragraphs that open by scoping themselves -- up is
# the record gaining authority that borrows a term, which is what happened.
SCOPED = 42


def test_the_count_is_measured_and_does_not_go_stale(held):
    """A figure in prose goes stale silently, which is why it is recomputed."""
    marked = [h for h in held if h.scoped]
    assert len(marked) == SCOPED, (
        f"{len(marked)} of {len(held)} passages open by scoping themselves and "
        f"this file says {SCOPED}. Up is the record gaining authority that "
        f"borrows a term; down is a passage having been re-extracted, or the "
        f"pattern having narrowed.\n  "
        + "\n  ".join(sorted(h.citation for h in marked)))
