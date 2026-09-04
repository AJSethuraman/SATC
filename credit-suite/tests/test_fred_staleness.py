"""Staleness means "this publisher is late", not "this publisher is slow".

The rule was cadence-only: a series later than twice its own publishing interval
is stale. That is right for a prompt source and wrong for a habitually slow one,
and most of these are habitually slow -- Case-Shiller reports a month about two
months after it ends, and the Fed's G.19 and Z.1 are similar. Under the old rule
**26 of 146 series were flagged on every single run, forever**.

`engine/staleness.py` warns about exactly this in its own docstring: a flag that
always fires is a flag nobody reads, and the one real stoppage then hides inside
the noise. So the fix is not "raise the threshold" -- that would hide real
stoppages too -- but "tell the rule how late this publisher normally runs", per
category, in config.

The numbers in `[SETTINGS]` are calibrated against what the publishers actually
did on 2026-09-04, and the observed ages are recorded beside them. These tests
pin the *behaviour*: a habitual lag is forgiven, a genuine stoppage is not, and
an uncalibrated category is unchanged rather than quietly more forgiving.
"""
from __future__ import annotations

from datetime import date

import pytest

from credit_suite.sources.fred import layout as L
from credit_suite.sources.fred import runner as R

ASOF = date(2026, 9, 4)


def cfg_with(**settings) -> R.Config:
    config = R.Config()
    config.settings.update({k.replace("__", "."): str(v)
                            for k, v in settings.items()})
    return config


# --------------------------------------------------------------------------
# the rule itself
# --------------------------------------------------------------------------

def test_a_habitually_late_publisher_is_not_stale():
    """Case-Shiller at 95 days old, against a 62-day cadence allowance."""
    last = date(2026, 6, 1)
    assert R.is_stale(last, "monthly", ASOF, 2.0) is True, (
        "precondition: the old cadence-only rule flags this")
    assert R.is_stale(last, "monthly", ASOF, 2.0, 60) is False


def test_a_publisher_that_actually_stopped_is_still_stale():
    """The three metro series retired on 2026-09-04 sat at 703 days. No lag
    anyone would write down forgives that, and none should."""
    last = date(2024, 10, 1)
    assert R.is_stale(last, "quarterly", ASOF, 2.0, 75) is True
    assert R.is_stale(last, "quarterly", ASOF, 2.0, 200) is True


def test_the_lag_is_added_not_multiplied():
    """A publisher being two months late is a fixed offset. Multiplying it by
    the cadence would forgive an annual series by two YEARS."""
    last = date(2026, 6, 1)                       # 95 days before asof
    # 31*2 + 60 = 122 -> not stale; if it multiplied, any positive lag would do
    assert R.is_stale(last, "monthly", ASOF, 2.0, 60) is False
    assert R.is_stale(last, "monthly", ASOF, 2.0, 30) is True   # 92 < 95


def test_no_lag_leaves_the_old_behaviour_exactly():
    """An uncalibrated category must not become quietly more forgiving."""
    for last, freq in ((date(2026, 6, 1), "monthly"),
                       (date(2026, 1, 1), "quarterly"),
                       (date(2026, 8, 20), "monthly")):
        assert (R.is_stale(last, freq, ASOF, 2.0)
                == R.is_stale(last, freq, ASOF, 2.0, 0))


def test_a_series_that_never_landed_is_stale_whatever_the_lag():
    assert R.is_stale(None, "monthly", ASOF, 2.0, 9999) is True


# --------------------------------------------------------------------------
# reading the setting
# --------------------------------------------------------------------------

def test_an_uncalibrated_category_reads_zero():
    assert cfg_with().publication_lag_days("hpi_caseshiller") == 0.0


def test_the_setting_is_read_per_category():
    config = cfg_with(lag_days__hpi_caseshiller=60, lag_days__dsr=75)
    assert config.publication_lag_days("hpi_caseshiller") == 60.0
    assert config.publication_lag_days("dsr") == 75.0
    assert config.publication_lag_days("g19") == 0.0


def test_a_junk_setting_reads_zero_rather_than_raising():
    """A typo in a spreadsheet cell must not take the run down, and must not
    invent an allowance either -- zero is the safe direction, because it flags
    MORE rather than less."""
    assert cfg_with(lag_days__dsr="soon").publication_lag_days("dsr") == 0.0
    assert cfg_with(lag_days__dsr="").publication_lag_days("dsr") == 0.0


def test_the_category_lookup_is_case_and_space_insensitive():
    config = cfg_with(lag_days__dsr=75)
    assert config.publication_lag_days("  DSR ") == 75.0


# --------------------------------------------------------------------------
# what actually ships
# --------------------------------------------------------------------------

def shipped_lags() -> dict:
    rows = L.config_rows() if hasattr(L, "config_rows") else None
    if rows is None:                                   # pragma: no cover
        pytest.skip("layout does not expose its config rows")
    return {str(r[0]): str(r[1]) for r in rows
            if r and str(r[0]).startswith("lag_days.")}


def test_every_category_that_was_permanently_stale_now_ships_a_lag():
    """The five categories behind all 26 permanent flags. If one is dropped
    from the shipped config, its series go back to being flagged forever."""
    lags = shipped_lags()
    for category in ("hpi_caseshiller", "hpi_national", "g19", "dsr", "cre_price"):
        key = "lag_days.%s" % category
        assert key in lags, "%s lost its publication lag" % category
        assert float(lags[key]) > 0


def test_no_shipped_lag_is_generous_enough_to_hide_a_dead_series():
    """The guard on the guard. A lag large enough to forgive the series we
    retired would make the flag useless in the direction that matters."""
    retired_age_days = (ASOF - date(2024, 10, 1)).days      # 703
    for key, value in shipped_lags().items():
        allowance = float(value) + 92 * 2.0                 # quarterly worst case
        assert allowance < retired_age_days, (
            "%s allows %d days; the series retired on 2026-09-04 were %d days "
            "old and must still flag" % (key, allowance, retired_age_days))
