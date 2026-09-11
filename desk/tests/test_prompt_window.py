"""Two ways a run reports a number for a question nobody ever asked.

Both are the same shape and it is the shape this repository keeps finding: a
claim in one place and the behaviour in another. `ollama()`'s docstring has said
since it was written that a request over the window "does not error -- it
silently drops the front of the prompt", and the front of this prompt is the
instruction to cite. Nothing checked it. `Leak` was raised where
`scoreboard.run` converts anything into `model_gave_up`, and escalation is a
SUCCESS on this scoreboard -- so a desk whose every prompt the harness refused
to build published as a careful one.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import record                                               # noqa: E402
import scoreboard                                           # noqa: E402
import scoreboard_run as sr                                 # noqa: E402
from conftest import CORPUS                                 # noqa: E402


# -- the window ---------------------------------------------------------------

def test_the_estimate_runs_high_never_low():
    """Under-counting is the one failure this must not have: it means the check
    passes and the prompt is cut anyway. English is nearer 4 characters to the
    token and regulation text is denser than English, so 3.2 is the pessimism."""
    assert sr.CHARS_PER_TOKEN < 4
    assert sr.estimate_tokens("x" * 400) > 100
    assert sr.estimate_tokens("") == 0


def test_the_reply_is_taken_out_of_the_window_not_added_to_it():
    """`num_ctx` is the whole of what the model holds, prompt and answer
    together. Sized against the window alone, a prompt that "fits" leaves the
    answer nowhere to go and the reply is what gets cut."""
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    just_over = "x" * int((room + 50) * sr.CHARS_PER_TOKEN)
    with pytest.raises(sr.PromptTooLong):
        sr.check_fits(just_over, num_ctx=8192)

    just_under = "x" * int((room - 200) * sr.CHARS_PER_TOKEN)
    assert sr.check_fits(just_under, num_ctx=8192) <= room


def test_a_prompt_that_will_not_fit_stops_the_run_rather_than_scoring_it():
    """A `HarnessError`, so `scoreboard.run` re-raises instead of recording an
    escalation for a question the model never saw."""
    assert issubclass(sr.PromptTooLong, scoreboard.HarnessError)


def test_the_refusal_says_what_to_do_about_it():
    with pytest.raises(sr.PromptTooLong) as e:
        sr.check_fits("x" * 100_000, num_ctx=8192, where="the vehicle desk")
    said = str(e.value)
    assert "the vehicle desk" in said
    assert "--corpus index" in said and "--num-ctx" in said


def test_neither_shape_fits_the_window_any_more_and_the_size_is_pinned():
    """The measurement, kept as a test so it cannot rot quietly — AND IT WENT
    THE WRONG WAY ON 10 SEPTEMBER 2026.

    WHAT IT USED TO SAY. Seven desks, and the `index` shape fitted every one of
    them: the largest was under 7,616 tokens of room. The `text` shape fitted
    exactly one, `personal-or-business` at 4,388. That pair of facts is what
    `docs/CONTEXT-ON-FILE.md` is built on and it is why the harness defaults to
    `--corpus index`.

    WHAT ONE CORPUS DID TO IT. `dec-kill` merged the seven, so the index a
    graded prompt shows is every RULE the record holds — 525 citations, up from
    176 on the largest desk — and the prompt is **25,622 tokens against 7,616 of
    room**. Full text is 91,067. NEITHER SHAPE FITS ANY MORE, and the shape that
    was chosen precisely because it fitted now overruns by three and a half
    times.

    THIS IS NOT THE ANSWERING PATH AND THE DIFFERENCE IS THE WHOLE POINT.
    `ask.consult` narrows through the pool to the eight citations a question
    actually reaches, and comes in at five to sixteen thousand CHARACTERS. The
    grading path has no narrowing: `scoreboard_run.build_prompt` shows the
    index, and the index is now the corpus. So `dec-kill` did not make the
    answering brief bigger — it made the GRADED one unusable on a small model,
    which is a real cost of the decision and is recorded here rather than
    smoothed over.

    IT IS NOT URGENT AND IT IS NOT NOTHING. The firm, 8 September 2026: *"We
    currently do not need to test against ollama. Stop trying to."* So nothing
    is scored against an 8k window today. The day something is, this is what it
    will hit, and the fix is to narrow the graded prompt the way the answering
    one is narrowed — which is a decision about how a score is taken, not a
    thing to do quietly inside a test.
    """
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    desk = record.load(CORPUS)
    biggest = {}
    for shape in ("index", "text"):
        sizes = []
        for problem in desk.problems:
            try:
                sizes.append(sr.estimate_tokens(
                    sr.build_prompt(problem, desk, shape=shape)))
            except sr.Leak:
                pass                     # a separate defect, checked below
        assert len(sizes) == len(desk.problems), (
            f"{len(desk.problems) - len(sizes)} problems could not be prompted "
            f"in the {shape} shape, so this is measured over the rows that "
            f"happened to be readable — the failure this file is named for")
        biggest[shape] = max(sizes)

    # Up 30 on 10 September 2026: `dec-pos2` added the firm's own standing
    # policy as a source row, and the index a graded prompt shows lists every
    # source the record holds.
    assert biggest == {"index": 25652, "text": 91096}, (
        f"the graded prompt changed size: {biggest}, and this file says "
        f"{{'index': 25652, 'text': 91096}}. That is allowed — it is what "
        f"storing authority does — but it is quoted in docs/CONTEXT-ON-FILE.md "
        f"and must move deliberately.")
    assert biggest["index"] > room, (
        "the index shape fits an 8k window again. That is good news and this "
        "test is now wrong: rewrite it, and correct CONTEXT-ON-FILE.md, rather "
        "than deleting the assertion.")


# -- the leak that read as a careful desk -------------------------------------

def _leaking_desk():
    for d in [CORPUS]:
        desk = record.load(d)
        for p in desk.problems:
            try:
                sr.build_prompt(p, desk, shape="index")
            except sr.Leak:
                return desk
    return None


def test_a_leak_is_ours_and_stops_the_run():
    """It was a plain Exception, so it landed in the catch-all that exists for a
    small model failing unpredictably -- and became `model_gave_up`."""
    assert issubclass(sr.Leak, scoreboard.HarnessError)


def test_a_desk_the_harness_cannot_prompt_does_not_publish_as_a_careful_one():
    """The reproduction, with no model involved. Before the fix this recorded 19
    of 19 as ESCALATED, which this scoreboard reports as a success."""
    desk = _leaking_desk()
    if desk is None:
        pytest.skip("no desk currently leaks, so there is nothing to prove here")

    def ask(problem):
        sr.build_prompt(problem, desk, shape="index")   # raises Leak where it does
        # Not every problem on the desk leaks. The ones that do not are the
        # brain's to fail, so they take rule 9's path and become a row -- which
        # is the behaviour the fix must not have broken.
        raise RuntimeError("this one does not leak, and that is not the point")

    with pytest.raises(scoreboard.HarnessError):
        scoreboard.run(desk, ask, model="a model that was never called")


def test_a_brain_giving_up_is_still_counted_as_a_denominator():
    """The other half, so the fix does not take rule 9 with it: a failure that
    really is the brain's still produces a row rather than stopping the run."""
    desk = record.load(CORPUS)

    def ask(problem):
        raise RuntimeError("the model said something unparseable")

    run = scoreboard.run(desk, ask, model="a brain having a bad day")
    assert run.gave_up == len(desk.problems)
    assert len(run.results) == len(desk.problems)


# -- the narrowing, and the proof it did not blind the check ------------------

def _promptable():
    """A desk and problem the harness can currently build a prompt for."""
    for d in [CORPUS]:
        desk = record.load(d)
        for problem in desk.problems:
            try:
                sr.build_prompt(problem, desk, shape="index")
                return desk, problem
            except sr.Leak:
                continue
    raise AssertionError("no desk can be prompted at all")


def test_the_rules_own_words_are_not_a_leak():
    """The narrowing itself. § 1.274-11(a) says entertainment is not deductible;
    a model that reads that and concludes it has reasoned correctly from
    authority. Counted over the whole prompt, that refused 11 real problems."""
    import dataclasses

    desk, problem = _promptable()
    planted = dataclasses.replace(
        desk, passages=desk.passages + (record.Passage(
            citation="26 CFR 9.99-9(a)", source_id=desk.sources[0].id,
            checked="2026-09-05",
            text=f"A charge of this kind is {problem.answer}. Nothing turns on "
                 f"who sold it."),))
    sr.build_prompt(problem, planted, shape="text")     # must not raise


def test_the_answer_in_the_facts_is_still_a_leak():
    """The half that matters. Everywhere except the quoted authority and the
    list of conclusions, the answer has no business appearing."""
    import dataclasses

    desk, problem = _promptable()
    planted = dataclasses.replace(problem, facts=f"{problem.facts} It is {problem.answer}.")
    desk = dataclasses.replace(
        desk, problems=tuple(planted if p is problem else p for p in desk.problems))
    with pytest.raises(sr.Leak):
        sr.build_prompt(planted, desk, shape="index")


def test_the_answer_in_a_source_title_is_still_a_leak():
    """The source list is printed and is not authority. A source retitled
    helpfully -- "S4 - when it is not deductible" -- would hand the conclusion
    over in the one block a reader would never think to check."""
    import dataclasses

    desk, problem = _promptable()
    first = desk.sources[0]
    desk = dataclasses.replace(desk, sources=(
        dataclasses.replace(first, title=f"{first.title} — when it is {problem.answer}"),
    ) + desk.sources[1:])
    with pytest.raises(sr.Leak):
        sr.build_prompt(problem, desk, shape="index")


def test_a_conclusion_that_contains_another_is_not_a_leak():
    """Four problems were refused for this and none of them leaked: `an
    allowable deduction` occurs inside `not an allowable deduction`, so the old
    at-most-one count saw two. The list is now cut out, not budgeted for."""
    for d in [CORPUS]:
        desk = record.load(d)
        listed = sr.admissible(desk)
        nested = [a for a in listed if any(a != b and a in b for b in listed)]
        if not nested:
            continue
        for problem in desk.problems:
            if problem.answer in nested:
                sr.build_prompt(problem, desk, shape="index")   # must not raise
                return
    pytest.fail("no desk has one admissible conclusion inside another, so the "
                "case these four were refused for no longer exists to prove")


# -- the OTHER prompt, which nothing has ever measured -------------------------

#: Estimated tokens in `ask.brief()` per desk, measured 7 September 2026. THE
#: ANSWERING brief, not the graded one -- `sr.build_prompt` shows rules only and
#: is checked above; this is what `ask_desk` hands a real answerer, examples
#: included.
#:
#: (Moved twice on 7 September 2026: the fifth docket's answers added a
#: `Records:` line and a ratified position, and the sixth ratified three more.
#: Neither round changed which desks fit.)
#:
#: (Both moved on 7 September 2026 when the firm answered the fifth docket:
#: `capitalization` gained a `Records:` line, `personal-or-business` gained a
#: ratified position. Neither changed which desks fit.)
#:
#: SIX OF SEVEN DO NOT FIT AN 8,192-TOKEN WINDOW, AND SIX OF SEVEN DID NOT FIT
#: BEFORE TODAY EITHER. Storing the worked examples made them larger; it moved
#: no desk from fitting to not fitting. The before column is exact rather than
#: remembered -- `desk.rules_only()` IS the corpus as it stood this morning.
#:
#: WHY IT IS A ROSTER AND NOT AN ASSERTION THAT THEY FIT. They do not, and
#: pretending otherwise would fail the build over a fact rather than a
#: regression. LOCAL-LLM-PATTERN rule 1 is the stake: a request over the window
#: "does not error -- it silently drops the front of the prompt", and the front
#: of this prompt is the instruction to answer only from what follows. A desk
#: whose brief overflows does not refuse; it answers from recall and cites
#: whatever it remembers, which the engine then refuses as `authority_absent`
#: and the scoreboard records as a careful escalation.
#:
#: THE FIRM'S DECISION, 7 SEPTEMBER 2026: *"for the time being - this is meant to
#: work as a claude code thing. we will get a larger gpu later."* So the 8,192
#: window is NOT the target today and none of these six is a defect to fix. The
#: roster stays for two reasons: it is the measurement that says what a larger
#: GPU has to be larger THAN, and the silent-truncation failure returns the day
#: anything small is pointed at these desks again.
#:
#: So the number is published, and it may only move deliberately. It moved on
#: 7 September 2026 when the three thin desks gained the worked examples their
#: own regulations carry: cash 15,142 -> 20,685, meals 11,750 -> 20,734, vehicle
#: 22,329 -> 26,382. And again when the firm admitted eCFR for § 1.162-3 on the
#: seventh docket: fixed-assets 22,231 -> 22,456 and 75,063 -> 75,288, two
#: paragraphs on both sides, because a stored RULE is shown to a graded model
#: and these are rules. And again on the EIGHTH docket, when the firm declared
#: § 1.263(a)-2 on the same desk -- **"Declare it"**, 7 September 2026 -- for the
#: same reason and the same amount either side: 22,456 -> 22,967 and
#: 75,288 -> 75,799. THE FIRST FIGURE IN EACH PAIR DID NOT MOVE ANYWHERE when
#: EXAMPLES were added, and
#: that is the property worth noticing rather than the growth: it is the brief a
#: GRADED model sees, examples withheld, and adding 34 examples changed none of
#: the seven. The withholding is doing what it claims.
#:
#: AND AGAIN on 8 September 2026 — four or five tokens on EVERY desk and both
#: sides, when the brief's first line began carrying the RUNNING CODE'S VERSION
#: (`record.VERSION`). The smallest move this roster has recorded, and the one
#: most worth explaining: the Skill tool served a session an `ask-desk` FIVE
#: releases stale that day, and the version warning meant to catch that lives in
#: the file that does not load. A check cannot detect its own staleness, so the
#: stamp had to come from the code doing the work — and the brief is the one
#: artifact an answerer always reads.
#: AND AGAIN on 8 September 2026, at 0.13.1 — **+113 tokens on every desk and
#: both sides**, which is the largest FLAT move this roster has recorded and the
#: one with the most behind it. The brief said, and had always said, *"A citation
#: to anything not printed here is refused by the engine, however real it is."*
#: That sentence was the ceiling: everything outside the stored corpus refused,
#: the searcher found the rule, and the trail stopped at the firm because a
#: source had to be admitted before any desk could cite it. Verification is the
#: gate now (#343), so the brief has to say what an answerer may do instead —
#: hand in the URL and the exact words, and let the engine fetch the page.
#:
#: THE OLD SENTENCE IS STILL THERE, UNWEAKENED, and the six lines added are
#: spent almost entirely on why: the gate is a FETCH and not the answerer's
#: word, so "you may cite something not printed here" must never read as "you
#: may quote it from memory". Identical on every desk because it is one fixed
#: paragraph, and identical on both sides because it is not authority.
#: WHAT A REAL QUESTION ACTUALLY SENDS, in tokens, at `limit=8`.
#:
#: THIS ROSTER USED TO BE PER DESK AND MEASURED THE WHOLE RECORD. Seven rows,
#: `ask.brief(question, desk)` over everything the desk held — 3,725 tokens on
#: `personal-or-business` up to 23,085 on `fixed-assets`, and six of the seven
#: overran an 8B window. `dec-kill` makes the unnarrowed figure meaningless:
#: the whole corpus is 91,497 tokens of rules and 185,571 with the worked
#: examples, and nothing sends it. `ask.consult` scores every citation against
#: the question and builds the brief from the top eight.
#:
#: SO THE MEASUREMENT MOVED TO THE PATH A QUESTION TAKES, and the answer is the
#: best news in this file: every one of these fits the 7,616 tokens of room,
#: where six of seven desks did not. Narrowing by what the question reaches
#: beats narrowing by which folder it landed in, on the dimension a small model
#: cares about.
#:
#: The four questions are real: two of Forge-Occam's from their field report,
#: and two from the working vernacular of a close.
NARROWED = {
    # Each up 125 tokens on 10 September 2026, and deliberately: `dec-coverage`
    # added the paragraph telling an answerer that these passages were chosen by
    # word overlap and that being shown one is not evidence it settles anything.
    # A fixed cost on every brief, and the cheapest of the three places that
    # warning could have gone.
    "is a brewery tab a business meal?": 2_410,
    "what supporting documents does the client have to keep?": 6_050,
    "hand tools bought for the trade - deducted or capitalized?": 2_846,
    "mileage or actual expenses for the van?": 2_420,
}

#: The whole corpus, unnarrowed, in tokens: `(rules only, with examples)`.
#: NOTHING SENDS THIS. It is here as the denominator the narrowing works
#: against, and so that a change in what the corpus holds is visible.
#: Up 118 on 10 September 2026: `dec-pos2` added S34, the firm's own standing
#: policy, and the paragraph that marks POS11 as resting on the firm rather than
#: on a paragraph. The narrowed briefs above are unchanged, because none of
#: those four questions reaches POS11.
WHOLE = (91_740, 185_814)


def _answering_sizes():
    import ask
    return {q: sr.estimate_tokens(ask.consult(q)) for q in NARROWED}


def test_the_answering_brief_is_the_size_the_roster_says():
    got = _answering_sizes()
    assert got == NARROWED, (
        "the answering brief changed size. That is allowed -- it is what "
        "storing authority does -- but the figure is published and must move "
        "deliberately:\n"
        + "\n".join(f"  {k!r}: roster {NARROWED.get(k)} measured {v}"
                     for k, v in got.items() if NARROWED.get(k) != v))


def test_the_whole_corpus_is_what_the_narrowing_works_against():
    """The denominator, so the win above is not measured against nothing."""
    import ask

    desk = record.load(CORPUS)
    got = (sr.estimate_tokens(ask.brief("a question", desk.rules_only())),
           sr.estimate_tokens(ask.brief("a question", desk)))
    assert got == WHOLE, f"the corpus changed size: {got}, roster says {WHOLE}"


def test_every_narrowed_brief_fits_the_window():
    """THE THING ONE CORPUS BOUGHT, and it is worth stating plainly.

    Six of seven desks overran an 8,192-token window on their own record. Every
    one of these questions fits, because the brief is now built from what the
    question reaches rather than from what a folder holds. It is the same
    mechanism that killed the word list, measured on the other axis.

    NOT A GUARANTEE, and this does not pretend to be one. Four questions is
    four questions; nothing here says the ninth citation of some other question
    could not push it over, and nothing in `ask.brief` checks — see the test
    below, which pins that absence.
    """
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    over = {q: n for q, n in _answering_sizes().items() if n > room}
    assert not over, (
        f"a narrowed brief no longer fits {room} tokens of room: {over}. "
        f"Either the corpus grew under a question or `limit` moved.")
    assert max(_answering_sizes().values()) > room // 4, (
        "every brief is now tiny, which usually means the narrowing found "
        "almost nothing rather than that it worked")


def test_nothing_checks_this_window_on_the_answering_path():
    """THE GAP ITSELF, recorded because it is the finding.

    `sr.build_prompt` calls `fits_window`; `ask.brief` calls nothing. The graded
    path refuses a prompt it cannot send, and the answering path -- the one a
    real question goes down -- has never had the check at all. Six of seven
    desks would silently lose their citation instruction on an 8B model today.

    This asserts the ABSENCE so that closing it goes red here, deliberately,
    rather than being closed by accident and never noticed.
    """
    import ask
    src = (pathlib.Path(__file__).resolve().parents[1] / "ask.py").read_text(encoding="utf-8")
    body = src.split("def brief(")[1].split("\ndef ")[0]
    assert "fits_window" not in body and "num_ctx" not in body, (
        "`ask.brief` now checks the window. Good -- update this test and the "
        "roster above to say what it does when the brief does not fit.")
