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
    "citation_does_not_support",  # real authority, but not this question's
    "contradicts_ratified_position",  # cited the firm's words, said the opposite
    "facts_not_established",    # the rule is clear; what was bought is not. ASK.
    "model_gave_up",            # ran out of window or abandoned the task
)

# WHY `facts_not_established` EXISTS, and why the set went eight rounds without
# it. Every other reason here is about the AUTHORITY -- absent, non-binding,
# uncited, unsupporting, contradicted. Not one was about the FACTS, so a desk
# holding exactly the right rule and missing the thing the rule asks about had
# no way to say so, and its only options were to guess or to blame the record.
#
# The firm, 5 September 2026, on an agent that classified a client's J.Crew
# purchases as personal: "no matter what, its answer was wrong." The lookup was
# not the error -- knowing J.Crew sells clothing is real evidence about WHAT WAS
# BOUGHT. The error was going from "sells clothing" to "personal expense"
# without reaching the test, which is § 1.262-1(b)(8): whether the item is
# "especially required by his profession and does not merely take the place of
# articles required in civilian life". Their client was a laborer who could
# legitimately need protective clothing, and the regulation has no vendor test
# in it at all -- its own example deducts a sword and refuses a uniform.
#
# What the firm does instead: "i could even flag it to ask the client." That is
# a real outcome and it was inexpressible. It is FIXABLE, like `authority_absent`
# and unlike `authority_permits_choice`: the answer exists, nobody has asked for
# it yet, and the working says what to ask.


@dataclass(frozen=True)
class Answer:
    """What a desk hands back. `position` is its conclusion, in its own words."""
    position: str
    citation: str = ""
    escalated: bool = False
    reason: str = ""
    working: str = ""


#: The two things that can escalate, named once so a typo is not a third value.
DESK, ENGINE = "desk", "engine"


@dataclass(frozen=True)
class Result:
    """One graded answer, and why it landed where it did."""
    problem_id: str
    outcome: Outcome
    reason: str = ""
    detail: str = ""
    #: WHO ESCALATED: "desk" when the thing answering declined, "engine" when
    #: `_check` stopped a confident answer resting on non-binding authority.
    #: Empty for every other outcome.
    #:
    #: WITHOUT THIS THE ESCALATION COLUMN CANNOT BE READ, and on a desk built to
    #: exercise escalation it is the only column that matters. Where `_check`
    #: refuses with `authority_permits_choice` it does so before any conclusion
    #: is compared, so a desk that answered confidently and a desk that knew it
    #: did not know land in the same cell. The first was rescued by the record's
    #: tier; the second made the call. Reporting them as one number measures the
    #: record, not the brain.
    #:
    #: THE TIER GATE KEYS OFF WHAT THE BRAIN CITES, NOT WHAT THE QUESTION IS
    #: ABOUT, and this comment said otherwise until a run disproved it. It read
    #: "a problem keyed to a secondary source can ONLY grade escalated". False:
    #: on the cash desk, 5 September 2026, qwen3:8b cited § 1.446-1(a)(4) -- a
    #: PRIMARY paragraph, about inventory -- on all four problems, reasoning by
    #: explicit "extension". The tier gate never fired and the row graded
    #: wrong_caught 4/4 with zero escalations.
    #:
    #: The consequence is larger than the wording. ESCALATION CANNOT BE FORCED
    #: THROUGH THE RECORD. Keying problems to a secondary source does not compel
    #: the path; a brain routes around it by citing something binding. The
    #: escalation has to come from the brain's judgement, which is the thing
    #: measuring zero -- so a desk cannot be built that makes a brain decline.
    escalated_by: str = ""

    @property
    def costly(self) -> bool:
        """The only outcome that costs anything. Reported first, always."""
        return self.outcome is Outcome.WRONGLY_ABSORBED


class EngineError(Exception):
    """A caller broke the engine's contract. Never a silent default."""


@dataclass(frozen=True)
class Served:
    """What actually leaves the desk. Carries its authority or it does not exist."""
    position: str
    citation: str
    tier: str
    checked: str
    #: Whether the citation was checked against the question's subject. False
    #: means nobody could look -- the desk declares no subjects, or the question
    #: touched none of them -- NOT that it was checked and found fine. Those two
    #: were the same answer until 5 September 2026, and the difference is four
    #: served answers on that day's Forge row.
    checked_subject: bool = False


@dataclass(frozen=True)
class Refusal:
    """The desk declining to serve. Names the next step, never just "no"."""
    reason: str
    detail: str

    def __bool__(self) -> bool:            # so `if served:` reads correctly
        return False


def _text_of(backing) -> str:
    """Whatever words back a citation, whichever store it came from."""
    kind, obj, _ = backing
    if kind == "position":
        return f"{obj.position} {getattr(obj, 'why', '')}"
    return obj.text


def off_subject(answer: Answer, desk: Desk, question: str) -> tuple[bool, str]:
    """`(refuse, detail)` — the cited authority shares no subject with the ask.

    MEASURED, 5 SEPTEMBER 2026, AND THIS IS WHY IT EXISTS. On the cash desk
    qwen3:8b answered four bank-reconciliation questions by citing
    § 1.446-1(a)(4) -- a real, resolvable, PRIMARY paragraph about keeping
    accounting records -- reasoning by explicit "extension". `grade()` caught all
    four on `passage.citation != problem.citation`, a check it can only make
    because it holds an answer key. `serve()` holds none, had no equivalent, and
    returned the accounting conclusion stamped `tier='primary'`. So the scoreboard
    reported `wrongly_absorbed = 0` while the path with a client on the end of it
    would have shipped four.

    THE CHECK IS EXACT AND THE JUDGEMENT IS THE FIRM'S. It computes one thing:
    of the desk's declared subjects, which appear in the question, and does the
    cited authority mention any of them. Whole words only, through `touches` --
    the one matching rule in this codebase. Zero overlap is the signal; anything
    above zero passes. It does not score relevance, rank citations or read
    meaning, because none of that is checkable and `guards.py` draws the line
    where a machine stops being exact.

    IT REFUSES ONLY WHEN IT COULD ACTUALLY LOOK. A desk with no declared subjects,
    or a question touching none of them, gives it nothing to compare -- and it
    passes rather than blocks, because "I could not check" and "I checked and it
    is fine" must never be the same answer. `Served.checked_subject` carries which
    of the two happened.

    THE COST IS REAL AND IS NOT HIDDEN: an authority whose text is written in
    pronouns, or in vocabulary the desk never declared, is refused though it may
    be exactly right. That shows up as `citation_does_not_support` in the queue
    with the working intact, which is where a wrongly refused answer is meant to
    be found.
    """
    touches = _canon_touches()
    asked = tuple(t for t in desk.fires_on if touches(question, t))
    if not asked:
        return False, ""
    backing = desk.authority_for(answer.citation)
    if backing is None:
        return False, ""
    text = _text_of(backing)
    if any(touches(text, t) for t in asked):
        return False, ""
    return True, (
        f"the question is about {', '.join(asked)}; {answer.citation!r} is real "
        f"authority this desk holds and mentions none of them. A citation that "
        f"shares no subject with the question is not this question's authority"
    )


def cited_off_source(answer: Answer, desk: Desk,
                     question: str) -> tuple[bool, str]:
    """`(refuse, detail)` — the citation comes from a source that does not
    answer what was asked.

    THE FACT IS RECORDED, NOT INFERRED, and that is the whole difference. A desk
    declares in SUBJECTS.md which source answers which subject. So the check is
    a lookup: which subjects does the question touch, which sources are declared
    to answer them, and did the citation come from one of those. No word overlap
    between the question and the authority, no relevance judgement, nothing to
    tune -- which is why this one may BLOCK where `off_subject` may not.

    MEASURED, 5 SEPTEMBER 2026 (#266). qwen3:8b answered four bank-reconciliation
    questions on the cash desk by citing § 1.446-1(a)(4) -- accounting records --
    by explicit "extension". Real, resolvable, primary, and `serve()` handed all
    four out stamped `tier='primary'`, because it had no key and no equivalent of
    `grade()`'s citation check. Comparing words instead either refused four of
    the sixteen fixed-assets problems answered with their OWN citation, or caught
    nothing at all. This refuses those four and none of fixed-assets.

    IT REFUSES ONLY WHEN IT COULD LOOK. A question touching no declared subject
    gives it nothing, and it passes -- `Served.checked_subject` says which
    happened, because "I could not check" and "I checked and it is fine" must
    never be the same answer.

    THE COST IS THE FIRM'S TO CONTROL AND IS VISIBLE WHEN PAID. Under-declare a
    subject and a right answer is refused; the refusal names the sources that
    were declared, so the record says how to fix itself, and the entry lands in
    `unsupported/` with the working intact.
    """
    if not desk.answered_from:
        return False, ""
    touches = _canon_touches()
    asked = [t for t in desk.fires_on if touches(question, t)]
    if not asked:
        return False, ""
    allowed = {sid for sid, terms in desk.answered_from.items()
               if any(t in asked for t in terms)}
    if not allowed:
        return False, ""
    cited = next((s.id for s in desk.sources
                  if answer.citation.startswith(s.citation_prefix)), None)
    if cited is None or cited in allowed:
        return False, ""
    named = ", ".join(sorted(allowed))
    return True, (
        f"the question is about {', '.join(asked)}, which this desk answers from "
        f"{named}; {answer.citation!r} comes from {cited}. A citation from a "
        f"source the desk does not use for this subject is not this question's "
        f"authority, however real it is"
    )


def _canon_touches():
    """Whole-word matching, borrowed rather than rewritten.

    It lives in one place because it was briefly written twice, once whole-word
    and once not, and the two disagreed for a day with nothing comparing them.
    """
    from _canon import load_record
    return load_record().touches


def _check(answer: Answer, desk: Desk, question: str = ""):
    """The one verification. Shared by the gate and the scoreboard on purpose.

    If serving and grading each had their own copy, they would drift, and the
    scoreboard would stop measuring the thing the gate actually does — which is
    the shape of nearly every real bug in this operation: a claim in one place,
    the behaviour in another, and nothing comparing them.

    Returns `(refusal, passage, source)`. A refusal of None means it passed.
    """
    if not answer.citation.strip():
        return Refusal(
            "no_citation",
            "answered with no citation; cite this desk's recorded authority, "
            "or escalate with a reason",
        ), None, None

    backing = desk.authority_for(answer.citation)
    if backing is None:
        return Refusal(
            "authority_absent",
            f"{answer.citation!r} is not in this desk's record; add it cited, "
            f"or escalate with reason 'authority_absent'",
        ), None, None

    # THE DECLARED MAPPING, WHICH IS EXACT AND SO MAY BLOCK (#266).
    astray, why = cited_off_source(answer, desk, question)
    if astray:
        return Refusal("citation_does_not_support", why), None, None

    # `off_subject` IS NOT WIRED IN HERE, AND THE MEASUREMENT IS WHY (#266).
    # It refuses 4 of the 16 fixed-assets problems answered with their own
    # recorded citation -- a quarter of the working desk, wrongly. Comparing the
    # cited text against the DESK's subjects instead of the QUESTION's drops that
    # to zero and stops catching the case it exists for. Word overlap either
    # over-refuses or under-catches; neither is exact enough to block on, which
    # is the line `guards.py` draws. Left public, tested and unused until the
    # firm picks a shape.

    kind, passage, source = backing
    if source is None:                                  # pragma: no cover
        raise EngineError(
            f"{answer.citation!r} has no source; load() checks this")

    # A ratified position IS the firm's answer, so tier does not gate it: the
    # firm already made the choice that a secondary source would only have
    # invited. This is the whole point of `human_only` — a source the engine
    # may never read is reachable only through what the firm wrote about it.
    if kind == "position":
        # AND IT MUST BE THE POSITION THE FIRM ACTUALLY TOOK. This branch used
        # to approve on the citation alone, never comparing what was submitted
        # with what the firm wrote -- so on the `human_only` path, where a
        # position is the desk's ENTIRE knowledge of a source it may never read,
        # a model could cite a real position and hand back the opposite
        # conclusion, and `serve()` would return that conclusion as the firm's.
        # The one path that exists because a human decided was the one path that
        # did not check the human's decision.
        if not _same(answer.position, passage.position):
            return Refusal(
                "contradicts_ratified_position",
                f"cited {answer.citation!r}, where the firm's position is "
                f"{passage.position!r}; answered {answer.position!r}. A position "
                f"is the firm's word and a desk does not revise it",
            ), passage, source
        return None, passage, source

    if not source.binding:
        return Refusal(
            "authority_permits_choice",
            f"{source.title} is {source.tier} authority, which is somebody's "
            f"reading rather than the rule; this is a position for the firm",
        ), passage, source

    return None, passage, source


def serve(answer: Answer, desk: Desk, *, question: str) -> Served | Refusal:
    """The production path: hand back an answer, or refuse and say why.

    **Nothing leaves here without authority behind it.** An uncited answer is
    refused by this function, not by a prompt asking the model nicely — the
    difference was measured at 100%, 4% and 0% of runs as prose, and always at
    the choke point.

    A refusal is not a dead end. Pair it with `unsupported.from_refusal` to keep
    the reasoning, which is the best evidence of what the record is missing.

    `question` IS REQUIRED, AND THAT IS THE FIX. Without it this function could
    verify that the cited authority exists and binds, and nothing at all about
    whether it had anything to do with what was asked -- so it served four
    bank-reconciliation answers citing a rule about accounting records, stamped
    primary, on 5 September 2026. `grade()` caught them only because it holds an
    answer key. There is no key here and there never will be; the question is
    what stands in for one.

    WHAT IS STILL NOT VERIFIED, said plainly because `Served` used to imply
    otherwise: that the cited paragraph is the BEST authority, that it is the one
    the regulation itself would name, or that the conclusion follows from it.
    Only that it exists, that it binds or carries the firm's word, and that it
    shares a subject with the question. `checked_subject` says whether even that
    last one could be looked at.
    """
    if answer.escalated:
        _reason(answer.reason)
        return Refusal(answer.reason, "escalated by the desk")

    refusal, passage, source = _check(answer, desk, question)
    if refusal is not None:
        return refusal
    return Served(
        # A position is the firm's words, so those are the words that leave the
        # desk -- not a restatement, however close. `_check` has already refused
        # one that disagrees; this makes the agreeing case exact rather than
        # merely equivalent, which is what "the model proposes, the engine
        # disposes" means at the only point where it is observable.
        position=getattr(passage, "position", None) or answer.position,
        citation=passage.citation,
        tier=source.tier,
        # A passage records when someone last confirmed it against the source;
        # a position records when the firm took it. Both answer "how old is
        # this?", which is what a caller needs, and neither is allowed to be
        # absent -- so read whichever this authority carries rather than
        # defaulting one in.
        checked=getattr(passage, "checked", None) or passage.recorded,
        # Stated rather than implied. `tier='primary'` used to be the whole
        # story a caller got, and it read as "this is solid" when all that had
        # been verified was that the authority exists and binds.
        checked_subject=bool(
            question and any(_canon_touches()(question, t) for t in desk.fires_on)
        ),
    )


def _reason(reason: str) -> str:
    if reason not in REASONS:
        raise EngineError(
            f"escalation reason {reason!r} is not one of: {', '.join(REASONS)}. "
            f"An open reason set cannot be counted."
        )
    return reason


def grade(answer: Answer, problem: Problem, desk: Desk) -> Result:
    """Verify the citation, then grade against the known answer.

    Verification and grading are genuinely separate and stay separate. A citation
    can resolve to a passage that does not support the claim, and an answer can be
    right while citing the wrong paragraph — collapsing them would report both as
    the same thing.
    """
    if answer.escalated:
        return Result(problem.id, Outcome.ESCALATED, reason=_reason(answer.reason),
                      escalated_by=DESK)

    refusal, passage, source = _check(answer, desk, problem.facts)

    if refusal is not None:
        # An interpretive source is not an error, it is the case where authority
        # permits a choice — so it escalates rather than counting as wrong.
        if refusal.reason == "authority_permits_choice":
            return Result(problem.id, Outcome.ESCALATED,
                          reason=refusal.reason, detail=refusal.detail,
                          escalated_by=ENGINE)
        return Result(problem.id, Outcome.WRONG_CAUGHT,
                      reason=refusal.reason, detail=refusal.detail)

    # THE CITATION MUST SUPPORT THIS PROBLEM, not merely exist.
    #
    # Written without this check, an answer that gave the right conclusion while
    # citing any other primary passage in the desk was scored CORRECT — so a
    # model could reach the right verdict from the wrong paragraph, or from a
    # paragraph about something else entirely, and inflate the scoreboard. That
    # contradicts this function's own stated distinction between a citation that
    # resolves and a citation that is the right one, which had been written down
    # and then not implemented.
    if passage is not None and passage.citation != problem.citation:
        return Result(
            problem.id, Outcome.WRONG_CAUGHT, reason="citation_does_not_support",
            detail=f"cited {answer.citation!r}, which is real authority but not "
                   f"what this question turns on ({problem.citation!r})",
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
