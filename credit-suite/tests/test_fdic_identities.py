"""The FDIC identity set, and what a merger quarter is allowed to say.

Four identities the publisher's own numbers have to satisfy (I2-I5 in
``docs/prd-data-consistency-flags.md``). None of them proves the FDIC agrees
with the filing -- the tie-out did that once, by hand. What they prove is that
our parse landed a numerator, a denominator and a ratio that belong to each
other, which is the exact fault class of a column read into the wrong field or
a unit off by a thousand.

Every threshold here is measured on ``verified-data/bank-values.csv``, the
audited deliverable: 12 banks x 16 quarters x 68 fields. The tests below run
the checks over all of it and assert the denominator as well as the result,
because a check that quietly examined nothing reports the same "0 problems" as
one that examined 13,056 cells.

**The merger case, and why nothing here reconstructs a number.** The 670%
chart was a quarterly flow spanning a merger. It was arithmetically right and
described nothing. The design this is built from worked PNC through as if the
adjustment were well defined; it is not, and that finding was withdrawn --
two mergers in this very panel consolidate opposite ways, one where the
survivor's year-to-date already contains the acquired bank's and one where it
does not. There is no single arithmetic that turns two year-to-dates into a
quarter across a merger, so the check marks the period NOT COMPARABLE and
never produces a repaired figure. Where the merger record cannot be
established the answer is UNKNOWN -- never a silent "fine".
"""
from __future__ import annotations

import csv
import dataclasses
from collections import defaultdict
from pathlib import Path

import pytest

from credit_suite.engine import consistency as K
from credit_suite.sources.fdic import consistency as C

PKG = Path(__file__).resolve().parents[1]
#: The shape of the deliverable, pinned as its factors rather than as one
#: number, so a change says WHICH of the three moved. Ten years of the
#: FDIC's quarterly panel for the twelve-bank set.
BANKS = 12
QUARTERS = 40
PANEL = BANKS * QUARTERS                           # 480 bank-quarters
CLASSES = 4                                        # the four loan classes
#: Acquisitions by the twelve banks inside the ten years, from the FDIC's
#: own institution history through the shipped `mergers` module.
MERGER_EVENTS = 11

BANK_VALUES = PKG / "verified-data" / "bank-values.csv"
NOT_COMPARABLE_CSV = PKG / "verified-data" / "not-comparable-periods.csv"


def _panel():
    """`{(cert, report_date): {field: value}}` from the audited deliverable."""
    panel = defaultdict(dict)
    with BANK_VALUES.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            panel[(row["cert"], row["report_date"])][row["field"]] = \
                float(row["value"])
    return dict(panel)


@pytest.fixture(scope="module")
def panel():
    return _panel()


def test_the_audited_panel_is_the_size_the_deliverable_says_it_is(panel):
    """The denominator every number below is measured against."""
    assert len(panel) == BANKS * QUARTERS           # 12 banks x 40 quarters
    assert {len(fields) for fields in panel.values()} == {68}


# --------------------------------------------------------------------------
# I5 -- the netting identity.  LNLSGR - LNATRES == LNLSNET
# --------------------------------------------------------------------------

def test_the_netting_identity_holds_exactly_across_the_whole_panel(panel):
    result = C.netting_identity(panel)
    assert (result.verdict, result.examined, result.failed) == (K.PASS, PANEL, 0)


def test_a_reserve_landed_into_the_wrong_field_breaks_the_netting_identity(panel):
    broken = dict(panel)
    key = next(iter(broken))
    row = dict(broken[key])
    row["LNATRES"] = row["LNATRES"] * 1000        # a unit slip of a thousand
    broken[key] = row
    result = C.netting_identity(broken)
    assert result.verdict == K.FAIL
    assert result.examined == PANEL                  # denominator unchanged
    assert "LNLSNET" in result.summary()


def test_a_bank_quarter_missing_a_leg_is_not_counted_as_a_pass(panel):
    thin = {("9999", "2026-06-30"): {"LNLSGR": 100.0}}
    result = C.netting_identity(thin)
    assert result.verdict == K.NONE
    assert result.examined == 0


# --------------------------------------------------------------------------
# I2 -- the publisher's ratio against the publisher's own components
# --------------------------------------------------------------------------

def test_every_published_ratio_recomputes_from_its_own_components(panel):
    """768 comparisons -- 4 ratios x 192 bank-quarters. The FDIC serves these
    at full double precision, so the tolerance is floating-point epsilon and
    not a rounding allowance: measured worst relative gap 5.3e-16."""
    result = C.ratio_identity(panel)
    assert (result.verdict, result.examined, result.failed) == (K.PASS, CLASSES * PANEL, 0)


def test_the_ratio_tolerance_is_epsilon_and_not_a_place_to_hide(panel):
    assert C.RATIO_TOLERANCE == 1e-12


def test_a_ratio_wearing_the_wrong_denominator_is_caught(panel):
    """Defect 5, 6 and 8's fault class: a label on the wrong series."""
    broken = dict(panel)
    key = next(k for k, f in panel.items() if f["NCLNLSR"] > 0.05)
    row = dict(broken[key])
    row["NCLNLSR"] = row["NCLNLSR"] * 1.01         # one percent, nothing dramatic
    broken[key] = row
    result = C.ratio_identity(broken)
    assert result.verdict == K.FAIL
    assert "NCLNLSR" in result.summary()


def test_a_zero_denominator_is_UNKNOWN_rather_than_a_division(panel):
    thin = {("9999", "2026-06-30"):
            {"EQ": 5.0, "ASSET": 0.0, "EQV": 0.0}}
    result = C.ratio_identity(thin)
    assert result.verdict == K.UNKNOWN
    assert result.examined == 1


# --------------------------------------------------------------------------
# I3 -- revolving 1-4 family is INSIDE total 1-4 family
# --------------------------------------------------------------------------

def test_the_zeros_in_the_deliverable_are_filed_nils_not_blank_cells(panel):
    """The question this test used to ask has been answered. Its name changed.

    Measured on the sixteen-quarter build, the non-zero counts of the four
    parent fields were 192 / 188 / 134 / 190 against a panel of 192 -- exactly
    the four numbers the design had recorded as cells the FDIC leaves BLANK.
    The reading at the time was that blanks had become zeros somewhere between
    the FDIC's response and the published CSV, which would make a share of the
    nesting comparisons `0 <= 0` and worth nothing.

    The ten-year tie-out settled it, one value at a time rather than by
    inference. The deliverable holds 5,385 values of exactly zero, and 5,348 of
    them were compared against an EXPLICIT ZERO on that bank's own filed Call
    Report -- for example JPMorgan's NACRCD at 2026-06-30, filed as RCFDB577 =
    0. They are reported nils. The remaining 37 carry their own verdict and are
    not counted as ties.

    So the comparisons are not vacuous in the way that was feared: a zero here
    means the bank told its regulator zero. It is still the weakest form of
    agreement there is, which is why the count is pinned and stated on the
    workbook's LIMITS tab rather than folded into a headline.
    """
    nonzero = {prefix: sum(1 for fields in panel.values()
                           if fields[prefix + "RERES"] != 0)
               for prefix in C.NESTED_PREFIXES}
    assert nonzero == {"LN": 474, "P3": 458, "P9": 354, "NA": 465}

    zeros = sum(1 for fields in panel.values()
                for value in fields.values() if value == 0.0)
    assert zeros == 5385, (
        "the count of exact zeros moved; re-run the tie-out and re-measure how "
        "many of them tie to a filed zero before trusting the number below")
    assert C.nesting_identity(panel).examined == CLASSES * PANEL


def test_the_home_equity_line_nests_inside_the_residential_book(panel):
    """The nine loan-class fields are NOT a partition: RERES contains RELOC.
    Encoding that is the point -- the obvious "components sum to the total"
    check breaches in 97 of 192 for exactly this reason."""
    result = C.nesting_identity(panel)
    assert (result.verdict, result.examined, result.failed) == (K.PASS, CLASSES * PANEL, 0)


def test_a_revolving_balance_larger_than_its_parent_is_caught(panel):
    broken = dict(panel)
    key = next(iter(broken))
    row = dict(broken[key])
    row["LNRELOC"] = row["LNRERES"] + 1.0
    broken[key] = row
    result = C.nesting_identity(broken)
    assert result.verdict == K.FAIL
    assert "LNRELOC" in result.summary() and "LNRERES" in result.summary()


# --------------------------------------------------------------------------
# I4 -- the eight disjoint noncurrent classes do not exceed the total
# --------------------------------------------------------------------------

def test_the_noncurrent_classes_fit_inside_the_noncurrent_total(panel):
    """Measured maximum exactly 1.0000 (Capital One, 2026-06-30), minimum
    0.640. With RELOC wrongly folded in it breaches in 97 of 192."""
    result = C.noncurrent_classes(panel)
    assert (result.verdict, result.examined, result.failed) == (K.PASS, PANEL, 0)


def test_folding_the_revolving_line_back_in_breaches_it_ninety_seven_times(panel):
    """The measurement that says why the eight are the eight."""
    breaches = 0
    for fields in panel.values():
        total = sum(fields[prefix + cls]
                    for cls in C.NONCURRENT_CLASSES + ("RELOC",)
                    for prefix in ("P9", "NA"))
        if total > fields["NCLNLS"]:
            breaches += 1
    assert breaches == 278


def test_a_bucket_larger_than_the_total_it_is_drawn_from_is_caught(panel):
    broken = dict(panel)
    key = next(iter(broken))
    row = dict(broken[key])
    row["NCLNLS"] = row["NCLNLS"] / 2.0
    broken[key] = row
    result = C.noncurrent_classes(broken)
    assert result.verdict == K.FAIL
    assert "NCLNLS" in result.summary()


# --------------------------------------------------------------------------
# the whole set, reported together
# --------------------------------------------------------------------------

def test_the_identity_set_reports_every_denominator(panel):
    results = C.identity_set(panel)
    assert [r.check for r in results] == ["I2", "I3", "I4", "I5"]
    assert [r.examined for r in results] == [CLASSES * PANEL, CLASSES * PANEL, PANEL, PANEL]
    assert all(r.verdict == K.PASS for r in results)


# --------------------------------------------------------------------------
# I1, reframed -- comparability, never reconstruction
# --------------------------------------------------------------------------

RECORD = {
    "4297": [{"quarter": "2022-12-31", "effective": "2022-10-03",
              "out_name": "Capital One Bank (USA) NA", "out_cert": "33954",
              "why": "quarter spans a merger"}],
    "6384": [{"quarter": "2026-06-30", "effective": "2026-06-18",
              "out_name": "FirstBank", "out_cert": "18714",
              "why": "quarter spans a merger"}],
}


def test_a_merger_quarter_is_not_comparable_and_carries_the_acquired_bank():
    verdict = C.flow_comparability("6384", "2026-06-30", RECORD)
    assert verdict.verdict == C.NOT_COMPARABLE
    assert "18714" in verdict.reason
    assert "2026-06-18" in verdict.reason


def test_a_quarter_with_no_merger_on_the_record_is_comparable():
    assert C.flow_comparability("6384", "2026-03-31", RECORD).verdict \
        == C.COMPARABLE


def test_a_bank_the_record_says_nothing_about_is_comparable():
    """`{}` means asked, none found -- a real answer."""
    assert C.flow_comparability("628", "2026-06-30", RECORD).verdict \
        == C.COMPARABLE
    assert C.flow_comparability("628", "2026-06-30", {}).verdict \
        == C.COMPARABLE


def test_no_merger_record_at_all_is_UNKNOWN_and_never_a_quiet_pass():
    """`None` is not `{}`. A caller that collapses them is back to the 670."""
    verdict = C.flow_comparability("6384", "2026-06-30", None)
    assert verdict.verdict == K.UNKNOWN
    assert "could not be established" in verdict.reason


def test_the_verdict_offers_no_repaired_number_to_use():
    """Two mergers in this panel consolidate opposite ways -- PNC's
    year-to-date contains the acquired bank's prior year-to-date and Capital
    One's does not -- so no single arithmetic reconstructs the quarter. The
    type deliberately has no field to put one in; adding one should break a
    test and start a conversation, not slip through."""
    names = [f.name for f in dataclasses.fields(C.Comparability)]
    assert names == ["verdict", "cert", "quarter", "reason", "acquired"]
    for name in names:
        assert "adjust" not in name and "value" not in name


def test_the_comparability_sweep_reports_its_denominator():
    keys = [("6384", "2026-03-31"), ("6384", "2026-06-30"),
            ("4297", "2022-12-31")]
    result = C.comparability_check(keys, RECORD)
    assert result.examined == 3
    assert result.verdict == K.UNKNOWN          # two periods not comparable
    assert result.unknown == 2
    assert "18714" in result.summary()


def test_a_sweep_with_no_merger_record_marks_every_period_unknown():
    keys = [("6384", "2026-03-31"), ("4297", "2022-12-31")]
    result = C.comparability_check(keys, None)
    assert (result.verdict, result.examined, result.unknown) == (K.UNKNOWN, 2, 2)


def test_the_events_the_deliverable_publishes_are_the_ones_it_marks():
    """Grounded on `verified-data/not-comparable-periods.csv`.

    Eleven merger quarters across the twelve-bank panel over ten years. The
    sixteen-quarter build saw six, and five of the other five would have been
    reported as the FDIC disagreeing with the filings -- a false finding of
    exactly the kind that has already been made here once.

    The count is pinned rather than derived: a test that reads the file and
    then asserts the file says what it says has checked nothing.
    """
    with NOT_COMPARABLE_CSV.open(encoding="utf-8") as handle:
        events = list(csv.DictReader(handle))
    assert len(events) == MERGER_EVENTS
    record = defaultdict(list)
    for event in events:
        record[event["cert"]].append(
            {"quarter": event["report_date"], "effective": event["effective"],
             "out_name": "", "out_cert": event["acquired_cert"],
             "why": event["what_this_means"]})
    marked = [key for key in _panel()
              if C.flow_comparability(key[0], key[1], dict(record)).verdict
              == C.NOT_COMPARABLE]
    assert len(marked) == MERGER_EVENTS
    assert len(C.FLOW_FIELDS) == 7
    assert len(marked) * len(C.FLOW_FIELDS) == MERGER_EVENTS * 7
