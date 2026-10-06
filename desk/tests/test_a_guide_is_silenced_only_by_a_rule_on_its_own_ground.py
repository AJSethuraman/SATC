"""`dec-guidance-narrow`, 11 September 2026 — the firm: **"Narrow it."**

THE GATE AND WHAT IT IS FOR. A non-binding source — an IRS publication, a
ruling, the Service's own plain-English page — may answer, marked as guidance
(`dec-guidance`, "Serve it, marked"). It may NOT answer where a rule covers the
same question, or a model could dodge a regulation by citing the summary of it.

WHAT BROKE. Over seven records the gate asked whether any binding source
answered any subject the question touched. A question reached one shelf, so that
was near enough. Merged into one corpus it is vocabulary coincidence:

    PH2   a basement used to store inventory   matched on `tools`
    VE13  business and personal use of a car   matched on `expense`
    RW9   a cash discount on an invoice        matched on `invoices`

Eight recorded answers stopped serving on that basis. This file holds the
narrowing that gives them back and the one case that must survive it.

TWO INSTRUMENTS WERE MEASURED AND REJECTED, and they are pinned below so nobody
spends the afternoon rediscovering them:

  - **The question's own words**, which is what broke.
  - **What the pool retrieves** — "does a binding passage come back for this
    question". Measured: TRUE for all 24 of the record's non-binding problems.
    That is the always-answering problem wearing a gate's clothes, and a gate
    that is true of everything is not a gate.

WHAT SHIPPED. The guide was cited for ground it declares. A rule silences it
only where a binding source declares that same ground. Read off `answered_from`,
which the firm wrote — no scoring, no ranking, nothing deciding what a passage
is about.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import engine                                                # noqa: E402
import pool                                                  # noqa: E402
import record                                                # noqa: E402
from conftest import CORPUS                                  # noqa: E402


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


def _source_of(desk, citation: str) -> str:
    return next(p.source_id for p in desk.passages if p.citation == citation)


def _guided(desk):
    """Every problem whose citation rests on a non-binding source."""
    out = []
    for p in desk.problems:
        src = desk.source(_source_of(desk, p.citation))
        if not src.binding:
            out.append((p, src))
    return out


# ── the narrowing, on the cases that named it ───────────────────────────────

@pytest.mark.parametrize("pid, coincidence", [
    ("PH2", "tools"),        # a basement storing inventory
    ("VE13", "expense"),     # business and personal use of a car
    ("RW9", "invoices"),     # a cash discount on an invoice
])
def test_a_word_the_question_happens_to_contain_no_longer_silences_a_guide(
        desk, pid, coincidence):
    """THE THREE THAT NAME THE DEFECT. Each still touches the coincidental word
    and a binding source still declares it — what changed is that the word is
    not what the GUIDE was cited for."""
    problem = next(p for p in desk.problems if p.id == pid)
    touches = engine._canon_touches()
    binding = {s.id for s in desk.sources if s.binding}

    assert any(touches(problem.facts, t) for t in desk.fires_on
               if t == coincidence), (
        f"{pid} no longer touches {coincidence!r}, so this proves nothing about "
        f"the coincidence it was written for")
    assert any(coincidence in terms for sid, terms in desk.answered_from.items()
               if sid in binding), (
        f"no binding source declares {coincidence!r} any more")

    assert not engine._rule_reaches(
        desk, problem.facts, _source_of(desk, problem.citation))


def test_the_one_that_must_still_refuse_still_refuses(desk):
    """RW7 IS THE TEST OF THE NARROWING, NOT A LEFTOVER.

    Its private letter ruling is refused because § 1.61-1 is declared for gross
    income and RW7 is about gross income — a rule on the same ground, not a word
    the question happened to contain. A narrowing that released RW7 too would
    have deleted the guard and called it narrowing.
    """
    problem = next(p for p in desk.problems if p.id == "RW7")
    assert engine._rule_reaches(
        desk, problem.facts, _source_of(desk, problem.citation))

    out = engine.serve(
        engine.Answer(position=problem.answer, citation=problem.citation),
        desk, question=problem.facts)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_permits_choice"


def test_no_named_guide_is_no_weaker_than_before(desk):
    """A caller that does not know which source is being cited gets the OLD
    test. Defaulting to the narrow answer there would silently widen what
    serves for every caller that never passed the argument."""
    problem = next(p for p in desk.problems if p.id == "PH2")
    assert engine._rule_reaches(desk, problem.facts) is True
    assert engine._rule_reaches(
        desk, problem.facts, _source_of(desk, problem.citation)) is False


def test_a_guide_declaring_nothing_here_still_refuses(desk):
    """Unable to tell is not clear. Where the guide answers none of what the
    question touches, nothing here can say what it is being cited FOR, and the
    direction to fail in is the one that asks the firm."""
    problem = next(p for p in desk.problems if p.id == "RW7")
    assert engine._rule_reaches(desk, problem.facts, "S-does-not-exist") is True


# ── the instrument that was rejected, kept so it is not reproposed ──────────

def test_retrieval_cannot_be_the_gate_because_it_is_true_of_everything(desk):
    """MEASURED, NOT ARGUED. "Does the question surface a binding passage" is
    the obvious narrowing and it is useless here: it holds for every single
    non-binding problem on the record. Pinned so the next session that thinks
    of it reads the measurement instead of spending the afternoon."""
    held = pool.assemble(CORPUS)
    known = pool.stats(held)
    binding = {s.id for s in desk.sources if s.binding}

    guided = _guided(desk)
    assert len(guided) == 24, f"{len(guided)} guided problems, not 24"

    surfaces = [p.id for p, _ in guided
                if any(f.held.source_id in binding
                       for f in pool.look(p.facts, held, known=known))]
    assert len(surfaces) == len(guided), (
        f"{len(surfaces)} of {len(guided)} now surface a binding passage, not "
        f"all of them. If that number has genuinely fallen, retrieval may be "
        f"worth another look as a gate — re-measure before trusting this line.")


# ── and the whole of it, counted ────────────────────────────────────────────

def test_thirteen_came_back_and_five_of_them_were_not_asked_for(desk):
    """THE PART THAT WENT PAST THE REQUEST, PINNED RATHER THAN ABSORBED.

    The firm asked for eight. Thirteen serve. The five extra were refused even
    across seven desks, and each is a guide the record admits precisely because
    no rule says the thing — traced in
    `test_a_desk_can_answer_itself.py::test_the_guidance_half_is_marked_as_such`.
    """
    asked_for = {"PH2", "RW1", "RW5", "RW6", "RW8", "RW9", "VE13", "VE15"}
    beyond = {"TP1", "TP2", "TP3", "M15", "PH1"}

    serving = set()
    for problem, _ in _guided(desk):
        out = engine.serve(
            engine.Answer(position=problem.answer, citation=problem.citation),
            desk, question=problem.facts, context=problem.context)
        if isinstance(out, engine.Served):
            serving.add(problem.id)

    assert asked_for <= serving, f"the firm asked for these: {asked_for - serving}"
    assert beyond <= serving, f"went past the request, but not on: {beyond - serving}"
    assert "RW7" not in serving


def test_the_caveat_says_what_was_actually_checked(desk):
    """IT SAID SOMETHING THE NARROWING MAKES FALSE. The caveat read *"No binding
    authority on this desk reaches the question"* — the gate's OLD test — and on
    TP1 a binding regulation does reach a question about the threshold; what it
    does not do is declare the word. An answer whose own caveat overstates what
    was checked is worse than one that refuses, because a reader cannot tell.
    """
    problem = next(p for p in desk.problems if p.id == "TP1")
    out = engine.serve(
        engine.Answer(position=problem.answer, citation=problem.citation),
        desk, question=problem.facts)
    assert isinstance(out, engine.Served) and not out.binding
    assert "declared to answer what this source answers here" in out.caveat
    assert "not the same as nothing binding existing" in out.caveat
    assert "No binding authority on this desk reaches" not in out.caveat
