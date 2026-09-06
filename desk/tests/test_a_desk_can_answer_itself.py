"""A desk handed its own recorded answers must not refuse them.

THE CEILING, AND WHY IT NEEDS A TEST OF ITS OWN. Every other measurement here is
of a model: how often a brain reaches the right conclusion, how often it cites
something that holds. This one takes the brain out. It answers each problem with
that problem's OWN recorded conclusion and OWN recorded citation -- a perfect
answerer, which no model will be -- and asks whether the engine lets it through.

Anything that is not `correct` or `escalated` in that run is the RECORD's fault
and nothing else's. A model cannot do better than this, so a defect here is a
ceiling on every score the desk will ever report, and it is invisible in the
scoreboard: a desk whose record refuses its own answers reports `wrong_caught`,
which reads as the engine working.

IT EXISTS BECAUSE A RATIFIED POSITION OUTRANKS THE REGULATION UNDER IT. On
6 September 2026 the rewards desk's two worked examples were pointed at the rule
they name, § 1.6041-1(a)(1)(iv) -- and the firm had ratified POS2 on that exact
paragraph. `authority_for` returns the position, `_check` compares the answer to
it verbatim, and both problems would have refused as
`contradicts_ratified_position`: the desk refusing the regulation for disagreeing
with the firm's summary of it. Nothing in the suite would have said so. The fix
was to reword POS2 to the paragraph's own sentence and move its second rule to
POS3, on the paragraph that rule turns on -- and this test is what holds that
apart from a plausible-looking edit that quietly puts it back.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import engine                                               # noqa: E402
import record                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402


def _ceiling(desk):
    """Grade every problem with its own recorded answer and citation."""
    return [engine.grade(engine.Answer(position=p.answer, citation=p.citation),
                         p, desk)
            for p in desk.problems]


def _desks():
    for d in sorted(DESKS.iterdir()):
        if (d / "SOURCES.md").is_file():
            yield record.load(d)


def test_no_desk_refuses_its_own_recorded_answer():
    """The whole population, not a sample. A perfect answerer can only land in
    `correct` or `escalated`; anything else is the record contradicting itself."""
    broken = []
    for desk in _desks():
        for r in _ceiling(desk):
            if r.outcome in (engine.Outcome.CORRECT, engine.Outcome.ESCALATED):
                continue
            broken.append(f"{desk.name}/{r.problem_id}: {r.outcome.value} "
                          f"({r.reason}) — {r.detail}")
    assert not broken, (
        "these problems are refused when answered with their OWN recorded "
        "conclusion and citation, so no model can ever score them:\n  "
        + "\n  ".join(broken))


def test_a_ratified_position_does_not_refuse_the_rule_it_rests_on():
    """The specific trap, named rather than left to the sweep above.

    Where a problem's citation carries a ratified position, that position is what
    `serve()` hands back -- so the position's wording and the problem's recorded
    answer have to be the same sentence. They are two files edited by different
    people for different reasons, and nothing else compares them."""
    checked = 0
    for desk in _desks():
        for problem in desk.problems:
            ruling = desk.position(problem.citation)
            if ruling is None:
                continue
            checked += 1
            assert engine._same(ruling.position, problem.answer), (
                f"{desk.name}/{problem.id} is scored against "
                f"{problem.answer!r}, but {ruling.id} is ratified on the same "
                f"citation and is served verbatim as {ruling.position!r}. The "
                f"problem would refuse as contradicts_ratified_position")
    # THE DENOMINATOR, because a sweep that matched nothing would pass silently
    # and this test would be a decoration.
    #
    # SIX, AND I GUESSED TWO. Written expecting only the rewards desk's IR4 and
    # IR5 -- the pair this test was built for -- it went red naming four more:
    # cash-and-bank CB1-CB4, on positions the firm ratified on 5 September 2026.
    # They match, and have all along. So the arrangement this test exists to
    # guard was already load-bearing on a second desk before anyone wrote it
    # down, which is a better argument for the test than the case that prompted
    # it. The denominator is the only reason that was ever discovered.
    assert checked == 6, (
        f"{checked} problems sit on a ratified position's citation, not 6. If "
        f"that moved deliberately, say so here — a zero makes this test vacuous")


def test_the_rewards_desk_scores_ten_and_escalates_nine():
    """The measurement the firm's docket turned on, kept where it can rot loudly.

    Nine of nineteen rest on secondary or tertiary authority because no primary
    authority on card rewards exists, so they escalate before any conclusion is
    compared -- the desk saying accurately that this is the firm's call. The ten
    information-return problems rest on the Code and on Treasury regulations and
    grade normally. Reading the two halves as one number hides the difference
    that is the whole point of the desk."""
    desk = record.load(DESKS / "rewards-and-information-returns")
    counts = engine.tally(_ceiling(desk))
    assert counts == {"wrongly_absorbed": 0, "correct": 10,
                      "wrong_caught": 0, "escalated": 9}, counts
