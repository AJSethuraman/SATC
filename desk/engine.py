"""The engine: verify a citation, then grade. Both jobs, one piece of code.

THE ONE RULE. An answer with no resolvable citation never counts as correct.
This is enforced here rather than asked for in a prompt, because the difference
was measured: the same policy written as skill prose was obeyed "100%, 4%, 0% of
runs"; at the API choke point it "is obeyed always, from every path"
(`docs/LOCAL-LLM-PATTERN.md`, rule 6).

WHY THE SCOREBOARD AND THE GATE ARE THE SAME CODE. C9 -- one mechanism, not two
beside each other. Verification is what converts an answer that would have shipped
wrong into one that was caught, so the thing that grades and the thing that gates
are the same question asked once.

FOUR OUTCOMES, AND THE ORDER THEY ARE REPORTED IN. `wrongly_absorbed` is first
because it is the only one that costs anything: an answer that was wrong, that
the engine could not fault, and that would therefore have reached a client with
nobody the wiser. `escalated` is a SUCCESS -- the desk knew it did not know.
Never sum them into one figure; a single percentage hides the only number that
matters.

VERIFICATION READS STORED TEXT, NEVER THE LIVE SOURCE. Freshness is a different
question, handled by the staleness check. An engine that reached out here would
make every test run depend on a government website being up, and would make
"prove every check can fail" nearly impossible to satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from record import Desk, Problem


class Outcome(str, Enum):
    """Reported in this order, always. Never summed."""

    #: Answered, cited, the citation held -- and the answer was wrong anyway.
    #: The engine had nothing to catch it with, so in production this ships.
    WRONGLY_ABSORBED = "wrongly_absorbed"

    #: Answered, cited, and right.
    CORRECT = "correct"

    #: Wrong, and the engine caught it before it left -- the citation did not
    #: resolve, so the answer never had authority behind it.
    WRONG_CAUGHT = "wrong_caught"

    #: The desk declined to answer. A success, and it carries a reason.
    ESCALATED = "escalated"


#: Why a desk could not answer. A closed set, because an open one becomes prose
#: and prose cannot be counted. Each carries a fix, and only the last is not one:
#: a question the rules genuinely leave open is a POSITION, and positions are the
#: firm's. Everything else is a work item.
REASONS = (
    "source_blocked_by_us",     # our own egress policy refused the domain
    "source_refuses_us",        # the source's origin refused this client
    "authority_absent",         # not in the record yet; add it, cited
    "authority_permits_choice",  # NOT fixable. the firm decides.
    "no_citation",              # the answer cited nothing that resolves
    "model_gave_up",            # ran out of window or abandoned the task
)


@dataclass(frozen=True)
class Answer:
    """What a desk hands back. `position` is its conclusion, in its own words."""
    position: str
    citation: str = ""
    escalated: bool = False
    reason: str = ""
    working: str = ""


@dataclass(frozen=True)
class Result:
    """One graded answer, and why it landed where it did."""
    problem_id: str
    outcome: Outcome
    reason: str = ""
    detail: str = ""

    @property
    def costly(self) -> bool:
        """The only outcome that costs anything. Reported first, always."""
        return self.outcome is Outcome.WRONGLY_ABSORBED


class EngineError(Exception):
    """A caller broke the engine's contract. Never a silent default."""


def grade(answer: Answer, problem: Problem, desk: Desk) -> Result:
    """Verify the citation, then grade against the known answer.

    The two are genuinely separate checks and stay separate. A citation can
    resolve to a real passage that does not support the claim, and an answer can
    be right while citing the wrong paragraph -- collapsing them would report
    both as the same thing.
    """
    if answer.escalated:
        if answer.reason not in REASONS:
            raise EngineError(
                f"escalation reason {answer.reason!r} is not one of: "
                f"{', '.join(REASONS)}. An open reason set cannot be counted."
            )
        return Result(problem.id, Outcome.ESCALATED, reason=answer.reason)

    if not answer.citation.strip():
        return Result(
            problem.id, Outcome.WRONG_CAUGHT, reason="no_citation",
            detail="answered with no citation; use the fixed-assets desk's "
                   "recorded authority, or escalate with a reason",
        )

    passage = desk.passage(answer.citation)
    if passage is None:
        return Result(
            problem.id, Outcome.WRONG_CAUGHT, reason="authority_absent",
            detail=f"{answer.citation!r} is not in this desk's record; add it "
                   f"cited, or escalate with reason 'authority_absent'",
        )

    source = desk.source(passage.source_id)
    if source is None:                                  # pragma: no cover
        raise EngineError(f"passage {passage.citation!r} has no source; load() checks this")

    if not source.binding:
        return Result(
            problem.id, Outcome.ESCALATED, reason="authority_permits_choice",
            detail=f"{source.title} is {source.tier} authority, which is somebody's "
                   f"reading rather than the rule; this is a position for the firm",
        )

    if _same(answer.position, problem.answer):
        return Result(problem.id, Outcome.CORRECT)

    return Result(
        problem.id, Outcome.WRONGLY_ABSORBED,
        detail=f"answered {answer.position!r} with authority that held; the "
               f"example concludes {problem.answer!r}",
    )


def _same(given: str, known: str) -> bool:
    """Compare a conclusion to the known one.

    Deliberately exact once normalised for case and surrounding space. A looser
    comparison here would quietly turn wrong answers into right ones, which is
    the one direction this code must never fail in -- and `wrongly_absorbed` is
    precisely the count that a generous comparison would hide.
    """
    return given.strip().casefold() == known.strip().casefold()


def tally(results: list[Result]) -> dict[str, int]:
    """Count outcomes. Ordered with the costly one first, never summed."""
    return {o.value: sum(1 for r in results if r.outcome is o) for o in Outcome}


def report(results: list[Result]) -> str:
    """The denominator, written so the number that costs something is read first.

    Zero is stated rather than omitted: a line that disappears when it is clean
    teaches a reader that its absence means nothing was checked.
    """
    counts = tally(results)
    width = max((len(k) for k in counts), default=0)
    lines = [f"{len(results)} graded"]
    lines += [f"  {name:<{width}}  {counts[name]}" for name in
              (o.value for o in Outcome)]
    return "\n".join(lines)
