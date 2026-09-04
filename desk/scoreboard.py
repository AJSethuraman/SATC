"""Run a desk's problems and report the denominator. Measured, never asserted.

WHAT THIS IS AND IS NOT. The harness is deterministic and lives here. The thing
that answers is injected, because a model's output is not reproducible and a
non-deterministic run cannot gate a build without either flaking or being
weakened until it proves nothing. So this is a script run at the desk, and the
numbers it produces are committed as a record rather than asserted as a test --
the same posture `credit-suite` takes with its live pulls.

EVERY NUMBER IS READ FROM ENGINE STATE, NEVER FROM THE MODEL'S PROSE. Rule 10:
"every score reads engine state, never the model's claims [...] Seven of our
check bugs produced false passes." What the model says it did is not evidence
that it did it.

TWO BRAINS, TWO ROWS, NEVER SUMMED. A Forge score and a frontier score sit side
by side. The gap between them is the finding -- it is what the local lean
actually costs, measured rather than argued about. Summing them would produce one
number describing neither.

THE ADAPTER MUST NEVER BE HANDED THE PASSAGE FOR THE PROBLEM'S OWN CITATION.
`Problem.facts` now withholds the sentence in which the regulation states its
outcome, so a problem cannot be solved by reading it back. The desk's STORED
authority is the same example complete -- conclusion included -- because that is
what the authority is, and the engine needs it to verify. So the leak closed in
`extract_ecfr.py` reopens the moment an adapter passes `desk.passage(problem
.citation)` in as context. This cannot be tested here: the thing that answers is
injected and does not exist yet (#227). It is a constraint on whoever writes it,
recorded rather than assumed.

WRONGLY ABSORBED IS PRINTED FIRST AND STATED AT ZERO. It is the only outcome that
costs anything, and a line that disappears when it is clean teaches a reader that
its absence means nothing was checked.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine import Answer, Outcome, Result, grade, tally
from record import Desk


@dataclass
class Run:
    """One brain's pass over one desk."""
    model: str
    results: list[Result] = field(default_factory=list)
    gave_up: int = 0

    @property
    def counts(self) -> dict[str, int]:
        return tally(self.results)

    @property
    def graded(self) -> int:
        return len(self.results)


class HarnessError(Exception):
    """A fault in the harness, never a brain abandoning the task.

    `run` absorbs anything an adapter raises, because a small model fails in
    unpredictable ways and rule 9 says that must still produce a denominator.
    The cost of that breadth was measured on this pull request: a replay adapter
    raised because the transcript answered a different prompt, and the catch-all
    turned all sixteen refusals into `model_gave_up` -- so the run "succeeded",
    wrote a scoreboard claiming an authority shape the brain never saw, and
    filed sixteen false entries in the unsupported queue. The refusal existed
    and did nothing.

    Anything raised for a reason that is OURS rather than the brain's subclasses
    this and reaches the caller. Deciding that by type keeps rule 9's behaviour
    for the failures it was written for.
    """


def run(desk: Desk, ask, *, model: str) -> Run:
    """Put every problem to `ask` and grade what comes back.

    `ask(problem) -> Answer` is whatever hands back an answer: a local model, a
    frontier one, a person, or a stub. It is injected so this module has no
    opinion about which, and so the harness is testable without one.

    **A model that abandons the task is counted, not hidden.** Small models give
    up on roughly one run in six to nine, worse under memory pressure, and no
    prompt fixes it (rule 9). An exception here becomes an escalation with reason
    `model_gave_up`, so the run still produces a denominator instead of nothing.

    **A `HarnessError` is not that and is re-raised.** A run built on a broken
    harness reports a denominator that reads exactly like a real one, which is
    worse than reporting nothing: nothing invites a second look.
    """
    out = Run(model=model)
    for problem in desk.problems:
        try:
            answer = ask(problem)
        except HarnessError:
            raise
        except Exception:
            answer = Answer(position="", escalated=True, reason="model_gave_up")
            out.gave_up += 1
        out.results.append(grade(answer, problem, desk))
    return out


ORDER = (Outcome.WRONGLY_ABSORBED, Outcome.CORRECT,
         Outcome.WRONG_CAUGHT, Outcome.ESCALATED)


def render(runs: list[Run], *, notes: list[str] | None = None) -> str:
    """Side by side, never summed, with what was not checked in its own list."""
    if not runs:
        return "no runs"
    width = max(len(r.model) for r in runs)
    head = f"{'':<{width}}  " + "  ".join(f"{o.value:>18}" for o in ORDER)
    lines = [head]
    for r in runs:
        c = r.counts
        lines.append(f"{r.model:<{width}}  " +
                     "  ".join(f"{c[o.value]:>18}" for o in ORDER))
    lines.append("")
    lines.append("graded: " + ", ".join(f"{r.model} {r.graded}" for r in runs))
    lines.append("")
    lines.append("NOT CHECKED:")
    for n in (notes or []):
        lines.append(f"  {n}")
    if not notes:
        lines.append("  (none)")
    return "\n".join(lines)


def gap(runs: list[Run], outcome: Outcome = Outcome.CORRECT) -> dict[str, int]:
    """What the local lean costs, per brain. The finding, not a verdict.

    C10 is a lean and the firm said so in the same breath as naming its cost.
    The honest way to honour a lean is to know what it costs, which means
    reporting both rows and the distance between them -- never merging them into
    a single figure that describes neither.
    """
    return {r.model: r.counts[outcome.value] for r in runs}
