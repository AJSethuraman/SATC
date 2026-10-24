"""The shared verdict vocabulary, and C1 -- every pullable series must land.

**C1, the Nebraska defect.** Both runners shipped a gate that asked whether
*at least one* series came back::

    return not (pullable > 0 and status.get("series_pulled", 0) == 0)

One HTTP 500 on the Nebraska house-price index gave ``pulled = 141`` of 142,
an error recorded honestly in the status dict that nothing read, exit code 0,
and a workbook on the desk with a state missing from it. The comparison is
arithmetic on two numbers the runner already carries, it has no threshold to
tune, and it cannot produce a false alarm -- which is why it is the first
thing built out of ``docs/prd-data-consistency-flags.md``.

**The vocabulary.** Every check answers with its DENOMINATOR attached and with
three verdicts, not two. "0 problems found" over nothing examined is the
failure this repository keeps hitting, so a check that examined nothing says
``NONE``; it is not allowed to say ``PASS``. And where a fact cannot be
established the answer is ``UNKNOWN``, never a silent pass -- the discipline
``mergers.read_mergers`` already keeps between ``None`` ("nobody asked") and
``{}`` ("asked, none found").
"""
from __future__ import annotations

import dataclasses

import pytest

from credit_suite.engine import consistency as K
from credit_suite.engine import runtime
from credit_suite.sources.fred import runner as FR


# --------------------------------------------------------------------------
# the vocabulary
# --------------------------------------------------------------------------

def test_a_check_that_examined_nothing_says_NONE_and_never_PASS():
    """"0 problems found" over an empty population is the failure mode."""
    result = K.decide("X9", examined=0)
    assert result.verdict == K.NONE
    assert result.verdict != K.PASS


def test_a_PASS_over_an_empty_population_is_refused_at_construction():
    """Not a convention a caller can forget: the type will not hold it."""
    with pytest.raises(ValueError):
        K.CheckResult(check="X9", verdict=K.PASS, examined=0)


def test_every_summary_carries_the_denominator():
    result = K.decide("I5", examined=192)
    assert "192" in result.summary()
    assert result.verdict == K.PASS


def test_a_failure_outranks_an_unknown_and_both_are_counted():
    result = K.decide("I1", examined=10, failures=["a"], unknowns=["b", "c"])
    assert (result.verdict, result.failed, result.unknown) == (K.FAIL, 1, 2)
    assert "10" in result.summary()


def test_unknown_alone_is_its_own_verdict_not_a_pass():
    result = K.decide("I1", examined=10, unknowns=["merger record unavailable"])
    assert result.verdict == K.UNKNOWN
    assert "merger record unavailable" in result.summary()


def test_only_a_failure_blocks_a_build():
    assert K.decide("A", examined=1, failures=["x"]).blocking is True
    assert K.decide("A", examined=1, unknowns=["x"]).blocking is False
    assert K.decide("A", examined=1).blocking is False
    assert K.decide("A", examined=0).blocking is False


# --------------------------------------------------------------------------
# C1 -- the landing check itself
# --------------------------------------------------------------------------

def test_one_series_short_of_the_expected_count_is_a_failure():
    """The Nebraska case exactly: 141 of 142 is not a successful run."""
    result = K.landing_check(expected=142, landed=141, missing=["NESTHPI"])
    assert result.verdict == K.FAIL
    assert result.examined == 142
    assert "141" in result.summary() and "142" in result.summary()
    assert "NESTHPI" in result.summary()


def test_all_of_them_landing_is_the_only_pass():
    assert K.landing_check(expected=142, landed=142).verdict == K.PASS


def test_nothing_expected_is_not_a_pass_and_not_a_failure():
    """An empty peer list or an all-dead seed is a configuration, not an
    outage -- and there is nothing to pass, either."""
    result = K.landing_check(expected=0, landed=0)
    assert result.verdict == K.NONE
    assert result.blocking is False


def test_more_landing_than_were_expected_is_also_a_failure():
    """A slot landing twice, or a count read from the wrong place."""
    assert K.landing_check(expected=10, landed=11).verdict == K.FAIL


def test_the_failure_says_how_many_it_could_not_name():
    """The runners truncate their error list; the count must not be truncated
    with it, or the report understates the hole."""
    result = K.landing_check(expected=142, landed=100, missing=["NESTHPI"])
    assert result.failed == 42
    assert "41" in result.summary()          # 42 missing, 1 named


# --------------------------------------------------------------------------
# C1 wired into the FRED runner
# --------------------------------------------------------------------------

def test_fred_run_succeeded_refuses_a_partial_pull():
    """Was ``is True`` until 5 September 2026 -- the gate asked for at least
    one series, so 5 of 10 shipped a holed workbook with exit code 0."""
    assert FR.run_succeeded({"series_pullable": 10, "series_pulled": 5}) is False
    assert FR.run_succeeded({"series_pullable": 10, "series_pulled": 0}) is False
    assert FR.run_succeeded({"series_pullable": 10, "series_pulled": 10}) is True


def test_fred_run_with_nothing_to_pull_is_not_a_failure():
    assert FR.run_succeeded({"series_pullable": 0, "series_pulled": 0}) is True


def test_fred_landing_result_names_the_series_that_did_not_land():
    result = FR.landing_result({"series_pullable": 142, "series_pulled": 141,
                                "series_missing": ["NESTHPI"]})
    assert result.verdict == K.FAIL
    assert "NESTHPI" in result.summary()


def test_a_fred_status_that_cannot_say_how_many_were_pullable_is_UNKNOWN():
    """Refuse to default: without the denominator the check has no opinion,
    and it must say so rather than report a clean run."""
    result = FR.landing_result({"series_pulled": 141})
    assert result.verdict == K.UNKNOWN


# --------------------------------------------------------------------------
# C1 wired into the shared engine (the FDIC monitor's path)
# --------------------------------------------------------------------------

def test_engine_run_succeeded_refuses_a_partial_landing():
    """Was ``is True`` for 1 of 12 until 5 September 2026."""
    assert runtime.run_succeeded(
        {"entities_admitted": 12, "entities_landed": 1}) is False
    assert runtime.run_succeeded(
        {"entities_admitted": 12, "entities_landed": 0}) is False
    assert runtime.run_succeeded(
        {"entities_admitted": 12, "entities_landed": 12}) is True


def test_a_refused_entity_is_not_expected_to_land():
    """``entities_active`` counts admitted PLUS watchlist refusals, and a
    refused entity never lands by design. Measuring against it would refuse
    every build that legitimately refused a bank."""
    assert runtime.run_succeeded(
        {"entities_active": 12, "entities_admitted": 10,
         "entities_landed": 10}) is True


def test_an_engine_status_with_no_admitted_count_is_UNKNOWN():
    result = runtime.landing_result({"entities_active": 12,
                                     "entities_landed": 12})
    assert result.verdict == K.UNKNOWN


def test_the_engine_status_carries_what_the_check_needs():
    """The check reads the run's own numbers; nothing recomputes them."""
    names = {f.name for f in dataclasses.fields(K.CheckResult)}
    assert {"check", "verdict", "examined", "failed", "unknown", "findings"} <= names
