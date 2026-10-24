"""Every desk requires a second reader, and it is declared where the firm can see it.

THE FIRM, on the docket, 8 September 2026, asked which desks may not serve an
unjudged answer: *"The judge can look at it all I guess?"* — all seven, and a
hedge in it. So the requirement is DECLARED IN EACH DESK'S OWN SUBJECTS.md
rather than wired into `ask.py`: lifting it from any desk is one line of that
desk's file, and an answer with a question mark in it deserves the reversible
shape.

WHAT IT BUYS, AND IT IS EASY TO OVERSELL. Seven trials on the Forge established
the limit and two tests in
`test_a_second_reader_says_whether_the_paragraph_carries_it.py` pin it — the
identical quotation supports both verdicts:

    "the judge does not make a wrong answer impossible -- it makes a wrong
     answer ATTRIBUTABLE. Instead of 'nobody checked', the record now says WHO
     checked, WHAT they quoted, and that they said yes. A reviewer can disagree
     with a named reader holding a specific quotation. Nobody can disagree with
     'unchecked'."

WHAT IT COSTS, MEASURED HERE RATHER THAN ESTIMATED. `test_the_cost_is_measured`
counts the served answers on the recorded corpus that now need a second model
call, from the record, so the figure cannot go stale in prose.

AND THE CHECK IS WORTH NOTHING UNLESS THE SECOND READER IS GENUINELY SECOND.
One session playing both parts produces something that looks like a check and is
not, so `judging.read` RAISES when the answerer judges itself — and that raise
is exercised here on every desk rather than on one.
"""
from __future__ import annotations

import dataclasses
import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import judging                                              # noqa: E402
import record                                               # noqa: E402
# ALIASED: this module already has a `CORPUS = 98`, the recorded
# problem count, and the bare name would shadow it — or be shadowed,
# which is what happened: shutil.copytree was handed the integer.
from conftest import CORPUS as RECORD, a_judgment    # noqa: E402


def _desks():
    return [record.load(RECORD)]


def _answerable(desk):
    """A problem this desk actually serves, with the words behind it.

    POSITIVE PRECONDITION IN A HELPER. A desk whose every problem refuses would
    make each test below pass while exercising nothing, so this raises rather
    than returning None — an empty case is a broken fixture, not a green.
    """
    open_desk = dataclasses.replace(desk, judged=record.OPTIONAL)
    for p in desk.problems:
        out = engine.serve(engine.Answer(position=p.answer, citation=p.citation),
                           open_desk, question=p.facts)
        if isinstance(out, engine.Served) and out.passage.strip():
            return p, out.passage
    raise AssertionError(f"{desk.name} serves none of its own problems")


# ── the declaration ─────────────────────────────────────────────────────────

def test_every_desk_declares_it_in_its_own_file():
    """READ FROM THE SEVEN FILES, not from a constant. A desk that quietly
    stops declaring it goes red here rather than serving in silence."""
    for desk in _desks():
        assert desk.judged == record.REQUIRED, f"{desk.name} does not declare it"
        assert desk.needs_a_judge


def test_a_misspelt_declaration_refuses_rather_than_defaulting(tmp_path):
    """THE ONE WAY THIS DECLARATION CAN DO HARM. A desk whose line reads
    `Judged: requird` would serve unjudged while its own file says it does
    not — silently, and in the safe-looking direction."""
    d = tmp_path / "corpus"
    shutil.copytree(RECORD, d)
    f = d / "SUBJECTS.md"
    f.write_text(f.read_text(encoding="utf-8")
                 .replace("**Judged:** required", "**Judged:** requird"),
                 encoding="utf-8")
    with pytest.raises(record.RecordError) as e:
        record.load(d)
    assert "requird" in str(e.value)


def test_a_desk_with_no_line_at_all_is_optional(tmp_path):
    """The default is what every desk did before the firm decided, so adding
    the parser could not change an existing desk's behaviour on its own."""
    d = tmp_path / "corpus"
    shutil.copytree(RECORD, d)
    f = d / "SUBJECTS.md"
    text = f.read_text(encoding="utf-8")
    assert "**Judged:** required" in text, "the fixture is not what it claims"
    f.write_text(text.replace("**Judged:** required", ""), encoding="utf-8")
    assert record.load(d).judged == record.OPTIONAL
    assert not record.load(d).needs_a_judge


# ── the gate, on every desk ─────────────────────────────────────────────────

def test_no_desk_serves_an_unjudged_answer():
    for desk in _desks():
        p, _passage = _answerable(desk)
        out = ask.answer(p.facts,  position=p.answer,
                         citation=p.citation, corpus=RECORD, keep=False)
        assert isinstance(out, engine.Refusal), f"{desk.name} served unjudged"
        assert out.reason == "not_judged"
        assert out.desk == desk.name


def test_a_judged_answer_still_serves_on_every_desk():
    """THE OTHER HALF, and without it the test above is satisfied by a desk
    that refuses everything."""
    for desk in _desks():
        p, passage = _answerable(desk)
        out = ask.answer(p.facts,  position=p.answer,
                         citation=p.citation, corpus=RECORD, keep=False,
                         judged=a_judgment(passage))
        assert isinstance(out, engine.Served), (
            f"{desk.name} refused a judged answer: {getattr(out, 'detail', '')}")
        assert out.judged.stands
        assert out.judged.against == "this desk's stored passage"


def test_the_self_judgment_raise_is_exercised_on_every_desk():
    """C6 — the preparer does not become the verifier. One session playing both
    parts produces something that looks like a check and is not, and this is the
    load-bearing part of the whole feature."""
    for desk in _desks():
        p, passage = _answerable(desk)
        with pytest.raises(judging.JudgingError) as e:
            ask.answer(p.facts,  position=p.answer,
                       citation=p.citation, corpus=RECORD, keep=False,
                       model="the-answerer",
                       judged=a_judgment(passage, by="the-answerer"))
        assert "both answered and judged" in str(e.value), desk.name


# ── the cost, measured rather than estimated ───────────────────────────────

#: SERVED ANSWERS ON THE RECORDED CORPUS THAT NOW NEED A SECOND MODEL CALL.
#: The whole cost of the firm's decision, in one figure.
#:
#: MEASURED 8 SEPTEMBER 2026 at desk 0.14.0, over seven desks:
#:
#:     13 of 16   capitalization-and-de-minimis
#:      4 of  4   cash-and-bank
#:     16 of 16   fixed-assets
#:     15 of 16   meals-and-entertainment
#:     11 of 12   personal-or-business
#:     18 of 19   rewards-and-information-returns
#:     15 of 15   vehicle-expense
#:     92 of 98   TOTAL
#:
#: RE-MEASURED 10 SEPTEMBER 2026 over ONE CORPUS: **84 of 98**, and the eight
#: that moved are a GUARD TIGHTENING that the seven desks could not have
#: reached. Every one of them now refuses `authority_permits_choice`, with the
#: same sentence: *"is secondary authority, which is somebody's reading rather
#: than the rule — and this desk holds binding authority on this subject. Cite
#: the rule, or escalate."*
#:
#:      PH2   IRS Pub. 587, "Exceptions to Exclusive Use" — the basement
#:      RW1   Rev. Rul. 2005-28
#:      RW5   RW6   RW8   RW9
#:      VE13  VE15  IRS Pub. 463 (2025)
#:
#: WHAT THAT MEANS, AND IT IS THE ARGUMENT FOR ONE CORPUS RATHER THAN A COST OF
#: IT. Eight recorded answers rested on a publication — somebody's reading —
#: while the regulation that decides the same question sat on a different desk.
#: A question only ever reached one desk, so nothing could see that the binding
#: rule was one folder over, and the answer went out stamped as authority. It
#: is the same shape as `26 CFR 1.274-5T(a)` being stored at 1,466 characters
#: on meals and 125 on vehicle: not a merge problem, a thing the merge made
#: visible.
#:
#: THE FIRST NUMBER WRITTEN HERE WAS 85 AND THE EXPLANATION UNDER IT WAS WRONG.
#: It said merging unioned `answered_from`, so seven answers that were
#: off-source became on-source and stopped needing a second reader — a SAVING.
#: The arithmetic said otherwise the whole time: 85 is fewer served than 92, so
#: more answers were being refused, not fewer. The 85 itself came from a
#: migration bug (`tools/one_corpus.py` truncated every wrapped `Answered from`
#: line, so `capitalization-and-de-minimis`'s thirty-eight subjects arrived as
#: three). With that fixed the figure is 84, and none of the movement is about
#: `answered_from` at all.
#:
#: NARROWED 11 SEPTEMBER 2026 ON THE FIRM'S ANSWER: **97 of 98**.
#: `dec-guidance-narrow` — **"Narrow it."** The gate asks whether a binding
#: source is declared for the ground THIS GUIDE was cited for, rather than for
#: any subject the question touches. The eight come back, and five more with
#: them — TP1, TP2, TP3, M15, PH1 — which were refused even across seven desks.
#: `test_a_desk_can_answer_itself.py::test_the_guidance_half_is_marked_as_such`
#: names all thirteen and traces each to the cited source's own `Why:` row.
#:
#: ONE STILL REFUSES AND IT IS THE POINT. RW7's private letter ruling is refused
#: because § 1.61-1 is declared for gross income, which is what RW7 is about — a
#: rule on the same ground rather than a word the question happened to contain.
#: A narrowing that released RW7 too would have deleted the guard.
#:
#: 97 IS HIGHER THAN THE 92 THIS EVER WAS, and that is not the narrowing being
#: too loose: the two instruments rejected on the way here are recorded in
#: `engine._rule_reaches`, and the five past the eight are reported to the firm
#: rather than absorbed.
#:
#: NOT SILENTLY UPDATED. This test exists to make the figure move visibly, and
#: it did its job three times: the number caught the migration bug, the number
#: caught the wrong story told about the number, and the number is what says
#: this change went further than what was asked for.
COST = 97
CORPUS = 98


def test_the_cost_is_measured_and_does_not_go_stale():
    """A FIGURE IN PROSE GOES STALE SILENTLY, which is why it is recomputed.

    The issue asked for the cost to be "measured and written down". Written down
    alone would be a number somebody typed once; this counts it from the record
    every run, so the day a desk gains problems the figure moves or this goes
    red — and either is better than a stale claim about what the firm's decision
    costs them.
    """
    served = corpus = 0
    for desk in _desks():
        open_desk = dataclasses.replace(desk, judged=record.OPTIONAL)
        for p in desk.problems:
            corpus += 1
            out = engine.serve(
                engine.Answer(position=p.answer, citation=p.citation),
                open_desk, question=p.facts)
            served += isinstance(out, engine.Served)
    assert (served, corpus) == (COST, CORPUS), (
        f"the judge's cost moved: {served} of {corpus} served answers now need "
        f"a second model call, and the record above says {COST} of {CORPUS}. "
        f"Move the figure deliberately — it is what the firm's decision costs.")
