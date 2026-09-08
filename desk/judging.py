"""A second reader, and the little the engine is allowed to do with their verdict.

WHAT THIS EXISTS FOR. Every gate in `engine._check` is exact: the citation
resolves or it does not, the position matches the firm's or it does not, the
publisher governs the domain or it does not. None of them is a statement about
whether THIS PARAGRAPH SUPPORTS THIS CONCLUSION, and none can be. The desk that
found the sharpest defect in this system said so plainly on 8 September 2026:

    "What it cannot catch is a correct position applied to the wrong facts --
     and that is the more likely error in a real close, because the agent isn't
     disagreeing with the firm, it's misreading which of the firm's two
     positions is in play."

The answer named there, three times over three days, is a JUDGE: a second model
handed the paragraph and the conclusion and asked whether one supports the other.

THE ENGINE DOES NOT JUDGE, AND MUST NOT. It has no model, no network -- the
suite replaces the socket layer, and `comparing`'s docstring records what
happened the one time a front-door module could reach a fetcher by import. What
the engine can do is exactly what it does everywhere else: refuse to take a
claim on trust. So a judgment arrives as an INPUT, like `prove`'s transport, and
the engine checks the only thing about it that is checkable without reading:

    THE WORDS THE JUDGE SAYS CARRY THE ANSWER MUST BE IN THE PASSAGE.

That is not a heuristic and not a word-overlap score -- both of which `guards.py`
already refuses to block on. It is the same comparison `proving` makes against a
publisher, through the same `comparing` module, with the same meaning for a
marked omission. A judge that quotes words the paragraph does not contain did not
read the paragraph, and that is decidable here.

WHAT IS STILL NOT DECIDABLE HERE, stated so nobody reads this as more than it is:
whether the quoted words actually carry the conclusion. That is the judge's call
and this module records it. `judging` is a check on the JUDGMENT, not a second
opinion on the answer.

AND THE CONSEQUENCE, measured on the Forge across seven trials on the night this
shipped: THE SAME QUOTATION SUPPORTS BOTH VERDICTS. A careless reader quotes "a
taxpayer must capitalize amounts paid to acquire or produce a unit of real or
personal property" -- really there, really in order -- says yes, and the lease
answer is served. A careful reader quotes the identical words, says no, and it is
refused. The tester's framing, and it is the right one:

    "the judge does not make a wrong answer impossible -- it makes a wrong
     answer ATTRIBUTABLE. Instead of 'nobody checked', the record now says WHO
     checked, WHAT they quoted, and that they said yes. A reviewer can disagree
     with a named reader holding a specific quotation. Nobody can disagree with
     'unchecked'."

That gain is real. It is NOT a gate the way the domain check is a gate: that one
can be right without a human; this one is exactly as good as the second reader,
and two models sharing a blind spot will agree. Two tests pin the pair so nobody
later writes that this stops wrong answers.

NOTHING DEMANDS A JUDGMENT YET. `ask.answer(..., judged=...)` checks one when it
is given and nothing anywhere requires one -- which desks must not serve
unjudged is the firm's to decide, and is on the docket. A gate that turned
itself on across seven desks overnight would be this session deciding it.
"""
from __future__ import annotations

import dataclasses

import comparing

#: The judge read it and the words are there.
HOLDS = "holds"
#: The judge said the paragraph does not carry the conclusion. A finding.
SAYS_NO = "says_no"
#: The judge quoted words the paragraph does not contain.
NOT_IN_THE_PASSAGE = "not_in_the_passage"


class JudgingError(Exception):
    """A caller assembled something that is not a judgment. Never defaulted."""


@dataclasses.dataclass(frozen=True)
class Judgment:
    """One second reader's verdict, and the words they rest it on.

    `by` IS REQUIRED AND IS NOT DECORATION. C6 -- the preparer does not become
    the verifier. A judgment whose author is the party that answered is a model
    marking its own work, which is the thing this was built to stop, so the
    check is on the identity rather than on a promise of independence.

    `because` IS QUOTED, NOT SUMMARISED. A paraphrase cannot be checked against
    anything; a quotation can. Marked omissions are allowed and are read exactly
    as a stored passage's are -- `[...]`, matched in order -- because a judge
    pointing at two clauses of a long paragraph is doing the right thing and
    should not have to transcribe the procedure between them.
    """
    by: str
    supports: bool
    because: str

    def __post_init__(self):
        if not self.by.strip():
            raise JudgingError(
                "a judgment with no author is not a judgment; name the party "
                "that read the passage")
        if not self.because.strip():
            raise JudgingError(
                "a judgment with no words in it is not a judgment; quote what "
                "the passage says" if self.supports else
                "say what is missing; a bare no tells the answerer nothing")


@dataclasses.dataclass(frozen=True)
class Read:
    """What the engine found when it checked the judgment. Never a score."""
    verdict: str
    by: str
    because: str
    #: The first quoted segment that is not in the passage. Empty otherwise.
    missing: str = ""

    @property
    def stands(self) -> bool:
        return self.verdict == HOLDS


def read(judgment: Judgment, passage_text: str, *, answered_by: str = "") -> Read:
    """Check a judgment against the paragraph it claims to have read.

    `answered_by` is who produced the answer. When it is the same party as the
    judge this raises rather than refusing: a caller that hands the engine one
    model wearing both hats has broken the contract, and a refusal filed in
    `unsupported/` would record it as a finding about the record when it is a
    finding about the caller.
    """
    if answered_by.strip() and judgment.by.strip() == answered_by.strip():
        raise JudgingError(
            f"{judgment.by!r} both answered and judged; a second reader is the "
            f"whole of what this checks, and one party cannot be it")

    if not judgment.supports:
        return Read(SAYS_NO, judgment.by, judgment.because)

    ours = comparing.normalise(judgment.because)
    live = comparing.normalise(passage_text)
    matched, missing = comparing.elided_match(ours, live)
    if not matched:
        return Read(NOT_IN_THE_PASSAGE, judgment.by, judgment.because,
                    missing=missing)
    return Read(HOLDS, judgment.by, judgment.because)
