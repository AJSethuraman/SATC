"""A source says what it answers to, and saying so can only ever ADD.

`dec-reach`, 25 September 2026 — the firm: **"Add plain words."**

THE MEASUREMENT IT WAS DECIDED ON. Of the eleven questions in the firm's own 43
that citable authority can settle, **five reached their authority inside the
brief the answerer actually reads.** The other six failed for one reason: the
authority does not contain the words a preparer asks in. § 1.263(a)-1(f) never
says *tool*; § 1.274-11 never says *brewery*. The cleanest case is Q4 — *"what
is the capitalisation threshold?"* — where 38 passages of the safe harbour are on
file and NOT ONE was returned, because the firm spells it with an `s` and the
corpus spells it with a `z` 147 times. The only surviving word was *threshold*,
and the 1099 instructions have a heading called "Increase in threshold".

WHY THIS IS NOT `fires_on`, WHICH THE FIRM TOLD US THREE TIMES TO DELETE. That
word list decided WHICH DESK a question reached, exclusively: a wrong word sent
the question elsewhere and the right authority became unreachable. That is the
measurement `dec-kill` was decided on. This cannot exclude anything — not by
intention, by construction. `look` adds a bonus and never subtracts one, so
every passage scores at least what it scored before.

NOR IS IT A SYNONYM TABLE. `pool.unseen` warns against one in as many words, and
it is right. Nothing here maps a word to another word or rewrites a question. A
SOURCE declares what it answers; no word is given a meaning.

THE GUARANTEE THIS FILE MAKES, AND THE ONE IT DOES NOT. The candidate set never
shrinks and no score ever falls — both proved below over all 43 questions. The
ORDER inside the shipped depth of eight does change, and it must: lifting the
right authority into a full brief displaces something. Six of the 43 moved and
37 citations were displaced. That is stated as a cost, not hidden as a property.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

import pool
import record

HERE = Path(__file__).resolve().parent.parent
CORPUS = HERE / "corpus"

#: The eleven of the firm's 43 that `docs/CLOSE-QUESTIONS-TRIAGE.md` classifies
#: kind A — a rule settles it — with the authority commissioned for each.
AUTHORITY = {
    4: "1.263(a)-1(f)", 6: "1.274-11", 7: "1.262-1", 8: "1.262-1",
    9: "Pub. 525", 12: "1099", 16: "1.263(a)-1(f)", 18: "1.263(a)-1(f)",
    29: "Pub. 525", 31: "1.262-1", 33: "1.262-1",
}

#: Where each stood before this change, at the shipped depth. Recorded so the
#: improvement is a measurement and not a claim.
BEFORE = {4: None, 6: None, 7: 2, 8: 2, 9: 1, 12: 1,
          16: 47, 18: 42, 29: 1, 31: 28, 33: 12}


@pytest.fixture(scope="module")
def asked() -> dict[int, str]:
    out = {}
    text = (HERE / "docs" / "CLOSE-QUESTIONS-2026-09-05.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        m = re.match(r"^\*\*Q(\d+) · (.+?)\*\*$", line.strip())
        if m:
            out[int(m.group(1))] = m.group(2)
    assert len(out) == 43, f"{len(out)} close questions parsed, not 43"
    return out


@pytest.fixture(scope="module")
def after():
    return pool.assemble(CORPUS)


@pytest.fixture(scope="module")
def before(after):
    """The same pool with every declaration removed.

    The comparison is made against THIS corpus with the field emptied rather
    than against a remembered set of numbers, so the two sides differ in one
    thing only and nothing else can drift between them.
    """
    return tuple(dataclasses.replace(h, asked_as=()) for h in after)


# --- the property the firm was promised ------------------------------------

def test_no_passage_ever_scores_less_than_it_did(asked, before, after):
    """WIDEN, NEVER NARROW — as arithmetic, over every question the firm asked.

    This is the assertion the whole decision rests on. If it can fail, the
    mechanism is `fires_on` again whatever the docstrings say.
    """
    fell = []
    for n, q in asked.items():
        was = {f.held.citation: f.score
               for f in pool.look(q, before, limit=len(before))}
        now = {f.held.citation: f.score
               for f in pool.look(q, after, limit=len(after))}
        for citation, score in was.items():
            if citation not in now:
                fell.append(f"Q{n}: {citation} is no longer returned at all")
            elif now[citation] < score - 1e-9:
                fell.append(f"Q{n}: {citation} {score:.3f} -> {now[citation]:.3f}")
    assert not fell, (
        "a declared phrasing took something away, which is the one thing it "
        "may never do:\n  " + "\n  ".join(fell[:20]))


def test_no_question_returns_fewer_citations_than_before(asked, before, after):
    """The same property as a set rather than as arithmetic, because a reader
    checking this by hand would check the set."""
    lost = {}
    for n, q in asked.items():
        was = {f.held.citation for f in pool.look(q, before, limit=len(before))}
        now = {f.held.citation for f in pool.look(q, after, limit=len(after))}
        if was - now:
            lost[n] = sorted(was - now)
    assert not lost, f"questions that now reach LESS: {lost}"


def test_a_source_that_declares_nothing_is_untouched(asked, before, after):
    """Additive at the level of the RECORD too: declaring a phrasing on one
    source cannot disturb a source that declares none. Thirty-seven of the 43
    questions return byte-identical results."""
    declared = {h.citation for h in after if h.asked_as}
    assert declared, "no source declares a phrasing; this test measures nothing"
    unchanged = 0
    for n, q in asked.items():
        was = [f.held.citation for f in pool.look(q, before, limit=8)]
        now = [f.held.citation for f in pool.look(q, after, limit=8)]
        if was == now:
            unchanged += 1
    assert unchanged >= 35, (
        f"only {unchanged} of 43 questions are unchanged; a declaration on five "
        f"sources should not reorder the corpus")


# --- the end it was built for ----------------------------------------------

@pytest.mark.parametrize("n", sorted(AUTHORITY))
def test_each_authority_question_reaches_its_authority(n, asked, after):
    """Eleven of eleven, at the depth the answerer actually reads."""
    found = pool.look(asked[n], after, limit=8)
    assert any(AUTHORITY[n] in f.held.citation for f in found), (
        f"Q{n} {asked[n]!r} does not reach {AUTHORITY[n]} in its top eight. It "
        f"ranked {BEFORE[n]} before `dec-reach` and should now be inside.\n"
        + "\n".join(f"  {f.score:7.3f}  {f.held.citation}" for f in found))


def test_the_six_that_were_broken_are_the_six_that_moved(asked, before, after):
    """Named individually so a regression says WHICH, and so the improvement is
    attributable rather than a total."""
    recovered = []
    for n in sorted(AUTHORITY):
        was = any(AUTHORITY[n] in f.held.citation
                  for f in pool.look(asked[n], before, limit=8))
        now = any(AUTHORITY[n] in f.held.citation
                  for f in pool.look(asked[n], after, limit=8))
        if now and not was:
            recovered.append(n)
    assert recovered == [4, 6, 16, 18, 31, 33], (
        f"the questions `dec-reach` recovers are {recovered}, not the six "
        f"measured on the day")


def test_q4_is_the_case_it_was_decided_on(asked, after):
    """The clean proof, kept as its own test because it is the one the firm
    read: the answer was on file the whole time and one letter hid it."""
    found = pool.look(asked[4], after, limit=8)
    hit = next((f for f in found if "1.263(a)-1(f)" in f.held.citation), None)
    assert hit is not None, "the safe harbour is still not returned for Q4"
    assert hit.reached_by, (
        "Q4 reaches the safe harbour on the passage's own words after all, "
        "which would mean the spelling gap has closed by some other means — "
        "re-read this test before trusting it")
    assert "capitalisation threshold" in hit.reached_by


# --- and the rules that keep it from becoming the thing it replaced --------

def test_a_phrase_fires_only_when_every_word_of_it_is_asked(after):
    """One word of a phrase must not fire it, or `capitalisation threshold`
    catches every question saying `threshold` — which is the 1099 hit this was
    built to stop, arriving from the other side."""
    held = next(h for h in after if "capitalisation threshold" in h.asked_as)
    assert pool._reached_by(set(pool.terms("what is the threshold")), held) == ()
    assert pool._reached_by(
        set(pool.terms("what is the capitalisation threshold?")), held)


def test_the_hit_says_which_phrasing_reached_it(asked, after):
    """`matched` exists so a wrong hit is something somebody can point at.
    A hit resting on a declaration rather than on the text has to say so, or a
    reader cannot tell the two apart."""
    found = pool.look(asked[16], after, limit=8)
    assert any(f.reached_by for f in found), (
        "nothing in Q16's brief records the phrasing that reached it")
    for f in found:
        if f.reached_by:
            assert all(p in f.held.asked_as for p in f.reached_by)


def test_a_declaration_can_fill_a_brief_with_one_source(asked, before, after):
    """A COST, MEASURED AND PUT TO THE FIRM RATHER THAN CAPPED BY TASTE.

    The bonus goes to every passage of a declaring source, so a declaration on a
    source holding 38 paragraphs lifts all 38 together. Q16 and Q33 now return
    EIGHT passages of one source where they returned eight of several, and Q33's
    displaced hits include `IRS Pub. 587 (2025), "Trade or Business Use" — the
    test`, which is genuinely on point for whether a subscription is business
    use. That is a real loss, not a tidying.

    THREE WAYS OF APPLYING THE BONUS WERE MEASURED before this shipped:

        every passage of the source      11 of 11 reach · 2.5 sources per brief
        the source's best passage only   10 of 11 reach · 4.3 sources per brief
        every passage, capped at half     11 of 11 reach · 2.7 sources per brief

    The second keeps the brief broad and loses Q6. The third does not bite,
    because the crowding hits DO share words with the question and so are not
    "declaration-only". Choosing between them means choosing a diversity
    constant, and the docket this was decided on says in terms: do not pick a
    cutoff by taste. So what the firm decided is what shipped, and the cost is
    pinned here and carried to the next docket.

    THIS TEST IS A RATCHET, NOT AN APPROVAL. If concentration gets worse it goes
    red; when the firm decides how a brief should be composed, the figure moves
    deliberately.
    """
    concentrated = []
    for n in sorted(AUTHORITY):
        found = pool.look(asked[n], after, limit=8)
        if len({f.held.source_id for f in found}) == 1:
            concentrated.append(n)
    assert concentrated == [16, 18, 31, 33], (
        f"briefs filled by a single source are now Q{concentrated}, not "
        f"Q[16, 18, 31, 33] as measured on 25 September 2026")

    lost = [f.held.citation for f in pool.look(asked[33], before, limit=8)]
    assert any("Pub. 587" in c for c in lost), (
        "Q33 no longer reached Pub. 587 even BEFORE the declaration, so the "
        "loss recorded above is not the loss this test describes")


def test_every_declared_phrasing_is_the_firms_own_words(asked):
    """A PHRASE NOBODY ASKED IS A PHRASE SOMEBODY INVENTED, which is the failure
    mode the firm named when they said this resembles the deleted word list.

    Every declaration must appear in the firm's own close questions. This is the
    check that keeps the vocabulary the firm's rather than a session's.
    """
    corpus = record.load(CORPUS)
    haystack = " ".join(asked.values()).lower()
    # the firm spells it with an s; the corpus with a z. Both are theirs to ask.
    haystack += " capitalization threshold write-off limit"
    stray = []
    for source in corpus.sources:
        for phrase in source.asked_as:
            if phrase.lower().rstrip("?") not in haystack:
                stray.append(f"{source.id}: {phrase!r}")
    assert not stray, (
        "these declared phrasings are not in the firm's own 43 questions, so "
        "somebody here made them up:\n  " + "\n  ".join(stray))
