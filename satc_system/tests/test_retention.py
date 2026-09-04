"""Seven years from the end of the engagement — and the letter says when that is.

The firm settled the clock start on 4 September 2026, then pointed at the source
rather than at their own memory of it: *"you can look at the engagement letter,
it outlines the end of the engagement."*

It does, and it contradicts the obvious guess. The letter ends the engagement on
delivery, or on signature-plus-transmission, or on written notice — and says in
as many words that acceptance is not it. Payment is not mentioned at all.

These tests are written against that clause, not against an idea of how tax work
finishes.
"""

from __future__ import annotations

from datetime import date

import pytest

from satc.retention import (RETENTION_YEARS, Ended, Undetermined,
                            due_for_disposal, engagement_ended)

APRIL = date(2026, 4, 15)


# -- the three endings the letter names ---------------------------------------

def test_a_delivered_paper_return_ends_on_delivery():
    got = engagement_ended(delivered_on=APRIL)
    assert got == Ended(APRIL, "delivered")
    assert got.label == "completed returns delivered"


def test_an_efiled_return_ends_when_signed_AND_transmitted():
    got = engagement_ended(transmitted_on=APRIL, authorization_signed=True)
    assert got == Ended(APRIL, "transmitted")


def test_written_notice_ends_it_whatever_else_happened():
    """"Either of us may end this engagement in writing at any time." At any
    time includes after the work is done, so a later delivery cannot un-end it,
    and an earlier one cannot outrank it."""
    notice = date(2026, 2, 1)
    got = engagement_ended(ended_in_writing_on=notice,
                           delivered_on=APRIL,
                           transmitted_on=APRIL, authorization_signed=True)
    assert got == Ended(notice, "written_notice")


# -- the two things that are NOT endings, and are the easy mistakes -----------

def test_acceptance_is_not_an_ending():
    """The letter: "not when the return is accepted." An acknowledgement can
    arrive days later or never, so a destruction clock hung on it starts on a
    date the firm neither controls nor always receives.

    Asserted by shape: there is no way to pass an acceptance date in, and that
    is deliberate. If one is ever added, this test should be the thing that
    argues with it.
    """
    import inspect
    params = set(inspect.signature(engagement_ended).parameters)
    assert not {"accepted_on", "ack_date", "acknowledged_on"} & params, (
        "an acceptance date reached this function; the letter says acceptance "
        "does not end the engagement")


def test_payment_is_not_an_ending():
    """Fees are owed for work done — a debt, not a duration. An unpaid
    engagement still ends, and still owes seven years of keeping."""
    import inspect
    params = set(inspect.signature(engagement_ended).parameters)
    assert not {"paid", "paid_on", "invoiced"} & params


# -- what is missing is said, never defaulted --------------------------------

def test_nothing_recorded_is_an_answer_not_a_date():
    got = engagement_ended()
    assert isinstance(got, Undetermined)
    assert "no written notice" in got.why


def test_transmitted_without_a_signature_refuses_and_says_why():
    """THE ONE WORTH CATCHING. The letter needs BOTH. A transmission with no
    signed authorization on file is either a missing record or a return that
    should not have gone, and both deserve a person looking rather than a
    quietly-started clock."""
    got = engagement_ended(transmitted_on=APRIL, authorization_signed=False)
    assert isinstance(got, Undetermined)
    assert "signed authorization" in got.why


def test_a_signature_alone_does_not_end_it():
    """A signed 8879 in a drawer has ended nothing."""
    assert isinstance(engagement_ended(authorization_signed=True), Undetermined)


# -- bookkeeping is a different contract --------------------------------------

def test_a_bookkeeping_engagement_ends_only_on_written_notice():
    """Its letter has no "concludes when" clause at all — only "either of us may
    end this engagement on <<NoticePeriod>> written notice". Nothing about it
    concludes on its own, so silence must mean KEEP, not dispose."""
    got = engagement_ended(is_rolling=True, delivered_on=APRIL)
    assert isinstance(got, Undetermined)
    assert "written notice" in got.why


def test_a_bookkeeping_engagement_does_end_when_notice_is_given():
    notice = date(2026, 6, 30)
    assert engagement_ended(is_rolling=True,
                            ended_in_writing_on=notice) == Ended(notice, "written_notice")


# -- the clock itself ---------------------------------------------------------

def test_seven_years_is_seven_years():
    assert RETENTION_YEARS == 7
    assert Ended(APRIL, "delivered").destroy_not_before() == date(2033, 4, 15)


def test_a_leap_day_ending_does_not_raise():
    """29 February plus seven years is not a date. Stepping back to the 28th
    moves destruction one day LATER, which is the safe direction; raising would
    make one engagement a year unanswerable."""
    got = Ended(date(2024, 2, 29), "delivered").destroy_not_before()
    assert got == date(2031, 2, 28)


def test_the_disposal_list_reports_and_never_destroys():
    """It returns what is due. Nothing in this module deletes anything, and the
    promise to clients is still unkept until something does."""
    old = Ended(date(2015, 1, 1), "delivered")
    recent = Ended(date(2025, 1, 1), "delivered")
    due = due_for_disposal([("2015-0001", old), ("2025-0001", recent)],
                           today=date(2026, 9, 4))
    assert due == [("2015-0001", date(2022, 1, 1))]


def test_the_disposal_list_is_oldest_first():
    """A morning list is read from the top, so the longest-overdue is the one a
    person should see first."""
    items = [("b", Ended(date(2016, 5, 1), "delivered")),
             ("a", Ended(date(2014, 5, 1), "delivered")),
             ("c", Ended(date(2015, 5, 1), "transmitted"))]
    assert [r for r, _ in due_for_disposal(items, today=date(2026, 9, 4))] \
        == ["a", "c", "b"]


def test_an_engagement_is_not_due_on_the_day_before():
    e = Ended(date(2019, 9, 5), "delivered")
    assert due_for_disposal([("x", e)], today=date(2026, 9, 4)) == []
    assert due_for_disposal([("x", e)], today=date(2026, 9, 5)) != []
