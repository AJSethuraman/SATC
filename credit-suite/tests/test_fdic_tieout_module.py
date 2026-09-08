"""One comparison, used by every check that compares.

`tieout.compare` is the single answer to "what does this filing say about this
field". It exists because the build-time tie-out was first written with its own
copy and reported 157 differences against a feed the full run calls clean --
every one of them the copy rather than the data.

These tests pin the four kinds of field it has to tell apart, and the one
mistake that made the copy wrong.
"""

from __future__ import annotations

import pytest

from credit_suite.sources.fdic import tieout as T


def test_a_capital_ratio_is_filed_as_a_fraction_and_published_as_a_percent():
    """RC-R carries 0.140877; the FDIC publishes 14.0877. A checker that
    compares the two without the hundred reports every bank as a difference."""
    facts = {"RCFA7205": 0.140877}
    value, where, kind = T.filed_value("RBCRWAJ", facts, "2026-03-31")
    assert kind == T.TIES
    assert value == pytest.approx(14.0877)
    assert "RC-R" in where


def test_the_lower_of_two_capital_frameworks_is_the_one_that_binds():
    """A bank that has exited parallel run files the ratio twice. The binding
    one is the lower, and taking the higher flatters the bank."""
    facts = {"RCFA7205": 0.140877, "RCFW7205": 0.131000}
    value, _where, _kind = T.filed_value("RBCRWAJ", facts, "2026-03-31")
    assert value == pytest.approx(13.1000)


def test_the_parenthetical_in_a_citation_is_part_of_the_citation():
    """`RCON2200 (+RCFN2200 031)` means domestic PLUS foreign offices on form
    031. Stripping the bracket and reading RCON alone gave JPMorgan's deposits
    as 2,226,790,000 against a delivered 2,820,284,000 -- domestic against
    consolidated, and 4,067 values wrongly called differences."""
    # The XBRL facts are in DOLLARS; the feed publishes thousands.
    facts = {"RCON2200": 2226790000000, "RCFN2200": 593494000000}
    value, used, kind = T.filed_value("DEP", facts, "2026-06-30")
    assert kind == T.TIES
    assert value == pytest.approx(2820284000)
    assert "RCFN2200" in used


def test_a_domestic_only_citation_does_not_take_the_consolidated_column():
    """`1797 (domestic)` names RCON. The consolidated column is a different,
    larger number that ties to nothing we publish."""
    facts = {"RCFD1797": 14102000000, "RCON1797": 13787000000}
    value, used, _kind = T.filed_value("LNRELOC", facts, "2026-06-30")
    assert value == pytest.approx(13787000)
    assert used.startswith("RCON")


def test_a_ratio_the_fdic_computes_is_not_a_filed_line_and_says_so():
    """There is no row on any form to compare a computed ratio with, and
    saying that is the answer rather than a gap."""
    _value, _cite, kind = T.filed_value("EQV", {"RCFD3210": 1, "RCFD2170": 2},
                                        "2026-06-30")
    assert kind == T.NOT_A_FILED_LINE


def test_a_quarterly_flow_is_refused_rather_than_answered_from_one_filing():
    """A filing carries the YEAR-TO-DATE. Returning it as the quarter is a
    wrong answer that looks right, so this module declines and the caller that
    holds the previous filing does the subtraction."""
    for field in ("NTCIQ", "DRRENRSQ"):
        _v, _c, kind = T.filed_value(field, {"RIAD4645": 1}, "2026-06-30")
        assert kind == T.IS_A_FLOW, field


def test_an_absent_line_is_unanswerable_and_not_zero():
    """A line nobody filed and a line filed as zero are different facts."""
    got = T.evaluate("RCFD9999", {}, {})
    assert got is None


def test_compare_calls_it_a_difference_when_it_is_one():
    facts = {"RCFD2170": 4091315000000}
    assert T.compare("ASSET", 4091315000, facts, "2026-06-30")[0] == T.TIES
    assert T.compare("ASSET", 4091316000, facts, "2026-06-30")[0] == T.DIFFERS
    # and half a thousand is the filing's own rounding, not a difference
    assert T.compare("ASSET", 4091315000.4, facts, "2026-06-30")[0] == T.TIES
