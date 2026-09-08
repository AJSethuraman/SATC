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
from conftest import DESKS                                  # noqa: E402


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


def test_the_index_shape_fits_every_desk_and_the_full_text_fits_one():
    """The measurement, kept as a test so it cannot rot quietly.

    IT SAID "FITS NONE" FOR AN HOUR AND THAT WAS WRONG. It was measured while
    four desks could not be prompted at all -- the leak check was refusing them
    -- so their full-text size was never taken. With that fixed, one desk's full
    text does fit: `personal-or-business`, at 4,388 against 7,616 of room. A
    denominator taken over the rows that happened to be readable is the failure
    this repository is named for, and it caught me on the same afternoon I wrote
    the guard.

    AND ON 6 SEPTEMBER 2026 THE DENOMINATOR BECAME WHOLE. The last blocked desk,
    `rewards-and-information-returns`, was 0 of 19 promptable while two worked
    examples sat in its corpus; it is 19 of 19, and every one of the seven desks
    now contributes a real size in both shapes. Nothing is being measured over
    the rows that happened to be readable any more, because every row is.

    THE FULL-TEXT ANSWER DID NOT CHANGE WHEN THE MISSING ROW ARRIVED, and that
    is worth one line: rewards comes in at 9,953 against 7,616 of room, so it
    joins the five that do not fit rather than the one that does. The earlier
    correction stands on its own now instead of on an incomplete set.
    """
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    index, text = {}, {}
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for shape, into in (("index", index), ("text", text)):
            sizes = []
            for problem in desk.problems:
                try:
                    sizes.append(sr.estimate_tokens(
                        sr.build_prompt(problem, desk, shape=shape)))
                except sr.Leak:
                    pass                 # that desk's own, separate defect
            if sizes:
                into[desk.name] = max(sizes)

    # SEVEN, AND IT WAS SIX UNTIL 6 SEPTEMBER 2026. This assertion is the reason
    # anyone noticed: `rewards-and-information-returns` contributed no size at
    # all while its corpus carried two worked examples, and the comment here
    # predicted that fixing them would turn this line red. It did, on the commit
    # that fixed them -- the two tests holding hands rather than a nuisance.
    #
    # NAMED, NOT COUNTED. `len(index) == 7` would pass while a desk silently
    # swapped places with another, which is the same failure as measuring over
    # the readable rows.
    assert sorted(index) == [
        "capitalization-and-de-minimis", "cash-and-bank", "fixed-assets",
        "meals-and-entertainment", "personal-or-business",
        "rewards-and-information-returns", "vehicle-expense",
    ], f"the set of promptable desks moved: {sorted(index)}"
    # AND EVERY DESK CONTRIBUTES TO BOTH SHAPES, which is the claim the docstring
    # above actually rests on. A desk blocked in `text` but not `index` would
    # leave the full-text finding measured over six again, silently.
    assert sorted(text) == sorted(index), (
        f"a desk is promptable in one shape and not the other: "
        f"{sorted(set(index) ^ set(text))}")
    assert not [d for d, n in index.items() if n > room], \
        f"the index shape no longer fits: {[(d, n) for d, n in index.items() if n > room]}"

    fits = sorted(d for d, n in text.items() if n <= room)
    assert fits == ["personal-or-business"], (
        f"the full-text shape now fits {fits}. It fitted exactly one desk when "
        f"this was measured; if that changed, say so in the docs rather than "
        f"here — the number is quoted in docs/CONTEXT-ON-FILE.md."
    )


# -- the leak that read as a careful desk -------------------------------------

def _leaking_desk():
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
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
    desk = record.load(DESKS / "cash-and-bank")

    def ask(problem):
        raise RuntimeError("the model said something unparseable")

    run = scoreboard.run(desk, ask, model="a brain having a bad day")
    assert run.gave_up == len(desk.problems)
    assert len(run.results) == len(desk.problems)


# -- the narrowing, and the proof it did not blind the check ------------------

def _promptable():
    """A desk and problem the harness can currently build a prompt for."""
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
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
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
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
ANSWERING_BRIEF = {
    "capitalization-and-de-minimis":     (8_666, 19_534),
    "cash-and-bank":                     (15_260, 20_803),
    "fixed-assets":                      (23_085, 75_916),
    "meals-and-entertainment":           (11_867, 20_851),
    "personal-or-business":              (3_725, 4_229),
    "rewards-and-information-returns":   (9_550, 20_240),
    "vehicle-expense":                   (21_006, 26_500),
}


def _answering_sizes():
    import ask
    out = {}
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        out[desk.name] = (sr.estimate_tokens(ask.brief("a question", desk.rules_only())),
                          sr.estimate_tokens(ask.brief("a question", desk)))
    return out


def test_the_answering_brief_is_the_size_the_roster_says():
    got = _answering_sizes()
    assert got == ANSWERING_BRIEF, (
        "the answering brief changed size. That is allowed -- it is what "
        "storing authority does -- but the figure is published and must move "
        "deliberately:\n"
        + "\n".join(f"  {k}: roster {ANSWERING_BRIEF.get(k)} measured {v}"
                    for k, v in got.items() if ANSWERING_BRIEF.get(k) != v))


def test_storing_the_examples_moved_no_desk_out_of_the_window():
    """The claim that matters about today, asserted rather than argued.

    Six desks already overflowed an 8B window this morning. If storing the
    examples had pushed a SEVENTH over, that would be a cost of this change; it
    did not, and the one desk that fits still fits.
    """
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    for name, (before, after) in _answering_sizes().items():
        assert not (before <= room < after), (
            f"{name} fitted the window before the worked examples were stored "
            f"({before:,}) and does not now ({after:,}). That is a desk this "
            f"change broke.")


def test_at_least_one_desk_fits_so_the_measurement_is_not_vacuous():
    """Narrowing. A room of zero would satisfy everything above."""
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    fits = [n for n, (_, a) in _answering_sizes().items() if a <= room]
    assert fits == ["personal-or-business"], fits


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
