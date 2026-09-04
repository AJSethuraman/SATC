"""The harness, tested with a stub. No model runs here, and none is faked.

The thing that answers is injected precisely so this is testable without one.
The numbers a real model produces are committed as a record, never asserted --
a non-deterministic run cannot gate a build without either flaking or being
weakened until it proves nothing.
"""
from __future__ import annotations

import pytest

from engine import Answer, Outcome
from scoreboard import Run, gap, render, run


def always(position, citation=""):
    def _ask(problem):
        return Answer(position=position,
                      citation=citation or problem.citation)
    return _ask


def test_a_perfect_pass_is_all_correct(fixed_assets):
    r = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="stub")
    assert r.counts["correct"] == len(fixed_assets.problems)
    assert r.counts["wrongly_absorbed"] == 0


def test_a_model_that_answers_without_citing_is_never_scored_correct(
        fixed_assets):
    """The rule the whole plugin rests on, exercised through the harness."""
    r = run(fixed_assets, lambda p: Answer(p.answer, ""), model="stub")
    assert r.counts["correct"] == 0
    assert r.counts["wrong_caught"] == len(fixed_assets.problems)


def test_a_model_that_gives_up_is_counted_not_hidden(fixed_assets):
    """Small models abandon long tasks and no prompt fixes it. An exception must
    still produce a denominator rather than nothing."""
    def boom(problem):
        raise RuntimeError("ran out of window")

    r = run(fixed_assets, boom, model="stub")
    assert r.gave_up == len(fixed_assets.problems)
    assert r.counts["escalated"] == len(fixed_assets.problems)
    assert r.graded == len(fixed_assets.problems), "the run still has a denominator"


def test_every_problem_is_graded_exactly_once(fixed_assets):
    r = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="stub")
    assert r.graded == len(fixed_assets.problems)
    assert len({res.problem_id for res in r.results}) == r.graded


# ── the report ───────────────────────────────────────────────────────────────

def test_wrongly_absorbed_is_the_first_column(fixed_assets):
    r = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="forge")
    head = render([r]).splitlines()[0]
    assert head.strip().startswith("wrongly_absorbed"), (
        "the number that costs something must be read before the ones that do not"
    )


def test_two_brains_are_reported_side_by_side_and_never_summed(fixed_assets):
    a = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="forge")
    b = run(fixed_assets, lambda p: Answer(p.answer, ""), model="frontier")
    text = render([a, b])
    assert "forge" in text and "frontier" in text
    assert "%" not in text, "a single percentage hides the only number that matters"
    assert "total" not in text.lower(), "the two rows must not be merged"


def test_the_report_names_what_was_not_checked(fixed_assets):
    r = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="stub")
    text = render([r], notes=["the Forge was not run: no model on this machine"])
    assert "NOT CHECKED:" in text
    assert "no model on this machine" in text


def test_an_empty_gap_says_none_rather_than_vanishing(fixed_assets):
    r = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="stub")
    assert "(none)" in render([r])


def test_the_gap_between_brains_is_reported_as_a_distance_not_a_verdict(
        fixed_assets):
    a = run(fixed_assets, lambda p: Answer(p.answer, p.citation), model="forge")
    b = run(fixed_assets, lambda p: Answer(p.answer, ""), model="frontier")
    g = gap([a, b])
    assert set(g) == {"forge", "frontier"}
    assert g["forge"] > g["frontier"]


def test_no_runs_is_stated_rather_than_rendering_an_empty_table():
    assert render([]) == "no runs"


def test_scores_are_read_from_engine_state_not_the_models_prose(fixed_assets):
    """A model claiming success proves nothing. The harness never reads a claim.

    Here the stub asserts it was right about every problem, while citing nothing
    — and the score must disagree with it.
    """
    def confident_liar(problem):
        return Answer(position=problem.answer, citation="", working="I am certain")

    r = run(fixed_assets, confident_liar, model="stub")
    assert r.counts["correct"] == 0
