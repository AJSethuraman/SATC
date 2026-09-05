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


def test_the_index_shape_fits_every_desk_and_the_full_text_fits_none():
    """The measurement, kept as a test so it cannot rot quietly.

    `--corpus text` was reachable from the command line and could not have run
    on the box it was written for -- 8,978 to 23,054 tokens against 7,616 of
    room. Nothing said so; the request would simply have been cut.
    """
    room = 8192 - sr.NUM_PREDICT - sr.OVERHEAD
    fits, over = [], []
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for shape, bucket in (("index", fits), ("text", over)):
            try:
                p = sr.build_prompt(desk.problems[0], desk, shape=shape)
            except sr.Leak:
                continue                       # that desk's own, separate defect
            bucket.append((desk.name, sr.estimate_tokens(p), shape))
    assert fits, "no desk could be prompted at all"
    assert all(n <= room for _, n, _ in fits), \
        f"the index shape no longer fits: {[(d, n) for d, n, _ in fits if n > room]}"
    assert over and all(n > room for _, n, _ in over), \
        f"the full-text shape now fits somewhere: {over}"


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
