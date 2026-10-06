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
from conftest import CORPUS                                  # noqa: E402


def _ceiling(desk):
    """Grade every problem with its own recorded answer and citation."""
    return [engine.grade(engine.Answer(position=p.answer, citation=p.citation),
                         p, desk)
            for p in desk.problems]


def _desks():
    for d in [CORPUS]:
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


def test_the_rewards_desk_grades_eighteen_and_escalates_one():
    """The measurement the firm's docket turned on — and it moved the same day.

    IT WAS TEN AND NINE THIS MORNING. Nine of nineteen rest on secondary or
    tertiary authority, because no primary authority on card rewards exists, and
    the engine refused a confident answer on non-binding authority before any
    conclusion was compared. That read as the desk saying accurately that this
    was the firm's call. It also meant nine problems no brain was ever tested
    on: they could only escalate, and an escalation reads as a success here.

    The firm answered "Serve it, marked" on the fourth docket, so where no rule
    reaches, guidance now answers with `binding=False` and a caveat. Eight of
    the nine become gradeable. THE NINTH DOES NOT, and it is the interesting
    one: RW7 rests on the private letter ruling, and this desk holds § 1.61-1 —
    binding authority declared for gross income, which is what RW7 is about. A
    rule reaches it, so the ruling may not be served in the rule's place.

    THE TWO HALVES ARE STILL NOT ONE NUMBER. What separates them is no longer
    the outcome but the caveat, and `test_the_guidance_half_is_marked_as_such`
    is what holds that apart.

    ONE CORPUS TOOK FIVE OF THE EIGHT BACK ON 10 SEPTEMBER AND THE FIRM GAVE
    THEM BACK ON THE 11th. For one day this read 13 correct and 6 escalated:
    RW1, RW5, RW6, RW8 and RW9 joined RW7, all refused with *"this desk holds
    binding authority on this subject."* Nothing about those answers had
    changed — what changed is what that sentence was true of, because a corpus
    holding seven desks' regulations holds a binding rule on very nearly every
    subject.

    `dec-guidance-narrow`, 11 September 2026 — the firm: **"Narrow it."** The
    gate now asks whether a binding source is declared for the ground THIS
    GUIDE was cited for, and the five come back. It is 18 and 1 again.

    RW7 IS STILL THE ONE, AND THAT IS THE TEST OF THE NARROWING RATHER THAN A
    LEFTOVER. Its ruling is refused because § 1.61-1 is declared for gross
    income, which is what RW7 is about — a rule on the same ground, not a word
    the question happened to contain. If a narrowing had released RW7 too it
    would have deleted the guard rather than narrowed it.
    """
    desk = record.load(CORPUS)
    # THE REWARDS PROBLEMS, NAMED BY THEIR OWN IDS. This graded a desk directory
    # until `dec-kill`; the corpus holds all 98, and the measurement the firm's
    # docket turned on is about these nineteen.
    rewards = [p for p in desk.problems if p.id.startswith(("RW", "IR"))]
    assert len(rewards) == 19, f"{len(rewards)} rewards problems, not 19"
    counts = engine.tally(
        [engine.grade(engine.Answer(position=p.answer, citation=p.citation),
                      p, desk) for p in rewards])
    assert counts == {"wrongly_absorbed": 0, "correct": 18,
                      "wrong_caught": 0, "escalated": 1}, counts


def test_the_guidance_half_is_marked_as_such():
    """Serving them was the change; serving them SILENTLY was never on offer.

    The docket's option was "Let guidance answer, marked as guidance", and the
    mark is the whole of what the firm bought. This counts how many answers on
    the whole record leave under a caveat, so the number can only move
    deliberately — and reports it per desk, because a desk whose guidance half
    quietly became binding would be invisible in a total."""
    desk = record.load(CORPUS)
    marked = []
    for p in desk.problems:
        out = engine.serve(
            engine.Answer(position=p.answer, citation=p.citation),
            desk, question=p.facts, context=p.context)
        if isinstance(out, engine.Served) and not out.binding:
            assert out.caveat, f"{p.id} is unmarked and uncaveated"
            marked.append(p.id)
    # FOURTEEN ACROSS SEVEN DESKS -> SIX ON ONE CORPUS -> NINETEEN NARROWED,
    # and the last step goes PAST where it started, which is the part to read
    # rather than the part to round off.
    #
    # The firm asked for eight back (`dec-guidance-narrow`, "Narrow it"). The
    # narrowing returns thirteen, because five of them -- TP1, TP2, TP3, M15,
    # PH1 -- were refused even on the seven-desk record, where a binding source
    # inside their own desk declared a word their question happened to contain.
    # Each of the five is traceable to the cited source's own `Why:` row, which
    # is the firm's recorded reason for admitting it:
    #
    #   TP1-3  S3 is on file because it "states the CURRENT de minimis ceiling"
    #          -- the number § 1.263(a)-1(f)'s own text does not carry.
    #   M15    S13 is on file because it states "the rule that a group taking
    #          turns picking up each other's checks" which the regulations do
    #          not.
    #   PH1    Pub. 587 on exclusive use; § 280A is not on this record at all.
    #
    # So each is a guide admitted precisely because no rule says the thing, and
    # refusing them was the gate firing on vocabulary. NOT ARGUED AWAY: the
    # five going past the eight is reported to the firm rather than absorbed,
    # because "narrow it" asked for eight and this is thirteen.
    #
    # The ids are listed rather than counted so that a guidance answer quietly
    # becoming binding is visible here rather than hidden in a total.
    assert marked == ["TP1", "TP2", "TP3", "M15", "PH1", "PH2", "PH3", "PH4",
                      "RW1", "RW2", "RW3", "RW4", "RW5", "RW6", "RW8", "RW9",
                      "VE13", "VE14", "VE15"], marked
