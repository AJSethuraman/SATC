"""The challenge: what the record has to say about a decision in flight.

THE ONE RULE. Challenge from the record, never from an opinion. Every output
here is grounded in something the firm already said; nothing in this file has
a view about what they ought to do.

WHAT IS DETERMINISTIC AND WHAT IS NOT, stated plainly rather than blurred. The
firm asked for outcomes that are deterministic wherever possible. "Does this
decision contradict this belief" is a judgement no code makes honestly. "Does
this decision touch the subject this belief is about" is not -- it is a
comparison against `fires_on`, and it is exactly what this module does.

So: the machine NARROWS, testably. The judgement that remains is made in the
open by whoever reads the candidates, and it is theirs. A module that pretended
to do the second half would be the confident-wrong-answer this operation has
been bitten by twice in a week.

SILENCE IS A RESULT. A decision that touches nothing returns nothing -- not a
note, not a reassurance, not a summary of what it failed to match. A thing that
speaks on every decision is a thing you learn to click past, and then its
silence has stopped meaning anything.

A CONFLICT IS NEVER RESOLVED HERE. Two convictions bearing on one decision are
returned as a pair and left that way. The disagreement is the finding; a
disagreement resolved fluently is a finding destroyed.
"""
from __future__ import annotations

from dataclasses import dataclass

from record import Conviction, touches

# The moments that fire whether or not anybody noticed anything. Kept small on
# purpose: every entry is a promise that something runs there, and a list that
# grows without that promise being kept is worse than no list.
#
# BLOCKING VERSUS ADVISORY follows the rule the firm already set for the tenet
# linter: what a machine can check EXACTLY may block; what it can only guess at
# advises, and is promoted only after a full cycle with no false positive.
# Candidate selection is a guess about relevance, so every gate starts advisory.
GATES: dict[str, str] = {
    "price-change": "advisory",
    "client-document-release": "advisory",
    "decision-recorded": "advisory",
}


@dataclass(frozen=True)
class Decision:
    """Something about to happen, described well enough to be checked."""
    what: str
    scope: str = ""
    moment: str = ""


@dataclass(frozen=True)
class Challenge:
    """One conviction, and the question it raises. Never an answer."""
    conviction: Conviction
    because: tuple[str, ...]

    def say(self) -> str:
        """The whole output. Quote, collision, question, stop.

        QUOTE, NEVER PARAPHRASE. A conviction in somebody else's words is one
        the firm will disown on sight, and a challenge they disown teaches them
        to skip the next one.
        """
        return (f"{self.conviction.id} · {self.conviction.title}\n\n"
                f"You said, on {self.conviction.recorded}:\n"
                f'  "{self.conviction.quote}"\n\n'
                f"Because: {self.conviction.why}\n\n"
                f"This touches {', '.join(self.because)}. "
                f"Has the reason changed?")


def _in_scope(c: Conviction, scope: str) -> bool:
    """A conviction scoped to one venture does not fire in another.

    An unscoped decision is checked against everything: not knowing where you
    are is a reason to hear more, not less.
    """
    if not scope or not c.applies:
        return True
    return c.applies.lower() in scope.lower() or scope.lower() in c.applies.lower()


def candidates(convictions: list[Conviction], decision: Decision) -> list[Challenge]:
    """Every held conviction this decision touches. Possibly none.

    RETIRED CONVICTIONS NEVER FIRE, and that is the whole point of retiring
    rather than deleting: it stops speaking and stays readable.
    """
    out = []
    for c in convictions:
        if not c.held or not _in_scope(c, decision.scope):
            continue
        hit = tuple(t for t in c.fires_on if touches(decision.what, t))
        if hit:
            out.append(Challenge(conviction=c, because=hit))
    return out


def conflicts(found: list[Challenge]) -> list[tuple[Challenge, Challenge]]:
    """Pairs of convictions bearing on one decision. RESOLVED BY NOBODY HERE.

    Returned as pairs rather than a ranking, because ranking beliefs in the
    abstract is far harder than choosing between two in a real situation -- and
    a wrong ranking resolves quietly, in the wrong direction, with nobody
    watching.
    """
    return [(a, b) for i, a in enumerate(found) for b in found[i + 1:]]


def gate(convictions: list[Conviction], decision: Decision) -> tuple[list[Challenge], str]:
    """A named moment. Fires whether or not anything was noticed.

    Returns what it found and whether this gate blocks or advises. An unknown
    moment is not a gate: it advises, and says so, rather than silently
    becoming one.
    """
    return candidates(convictions, decision), GATES.get(decision.moment, "advisory")


def report(found: list[Challenge], clashes: list[tuple[Challenge, Challenge]]) -> str:
    """What a person reads. Empty when there is nothing, deliberately."""
    # NO EARLY RETURN FOR THE EMPTY CASE, and that is deliberate. One was here
    # and a mutant removed it without a single test noticing: with nothing
    # found the joins below produce "" on their own, so the branch guarded
    # nothing. A guard that cannot fail is decoration, and decoration in a file
    # about honesty is worse than nothing. Silence falls out of the structure
    # instead, and `test_a_decision_touching_nothing_produces_nothing` holds it.
    lines: list[str] = []
    if clashes:
        lines.append("Two things you believe are pulling against each other "
                     "here. Both are yours; neither is resolved for you.\n")
        for a, b in clashes:
            lines.append(f"  {a.conviction.id} vs {b.conviction.id} — "
                         f"{a.conviction.title}  /  {b.conviction.title}")
        lines.append("\nHow you settle it is worth recording: it says what you "
                     "value when it costs something.\n")
    lines.extend(c.say() for c in found)
    return "\n\n".join(lines)
