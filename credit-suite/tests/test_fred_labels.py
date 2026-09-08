"""A series' label has to describe the series, and nothing checked that.

Found 5 September 2026, tying all 142 FRED series to the agencies that compute
them. Every landed value was correct. Five SLOOS labels were not:

    DRTSSP          said "Consumer Loans (subprime)"   was subprime MORTGAGE
    SUBLPDHMSENQ    said "Stronger Demand"             was GSE-eligible
                                                       mortgage TIGHTENING
    SUBLPDRCSC      said "Nonfarm Nonresidential"      was CONSTRUCTION
    SUBLPDRCSN      said "Construction & Land"         was NONFARM NONRES
    SUBLPDCILSLGNQ  said "Increasing Spreads"          was LARGE BANKS
                                                       tightening standards

Two of them were a straight swap, each wearing the other's description. The
numbers never moved, so no numeric test could see it, and none did.

The last one cost behaviour, not just wording. `_sloos(demand=True)` sets
`alert_rule` to "none" -- right for a demand series, and SUBLPDHMSENQ is not
one. A real mortgage-tightening indicator sat on the dashboard with its alert
switched off.

So this file checks the *label* against the publisher's own definition, the
way the numbers are checked against the publisher's own tables. The
definitions below are quoted from the Federal Reserve Board's Senior Loan
Officer Opinion Survey and from each series' official title.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_suite.sources.fred import series_seed as S    # noqa: E402


#: series id -> (words the official definition requires the title to carry,
#:               words that belong to a DIFFERENT series and must not appear,
#:               whether the official definition is a tightening measure)
#:
#: "must not carry" is the half that catches a swap: a title can contain the
#: right word and still be the wrong series' description.
OFFICIAL = {
    "DRTSCILM": (["tightening", "c&i", "large"], ["small"], True),
    "DRTSCIS": (["tightening", "c&i", "small"], [], True),
    "DRSDCILM": (["demand", "c&i", "large"], ["small"], False),
    "DRSDCIS": (["demand", "c&i", "small"], [], False),
    "DRTSCLCC": (["tightening", "credit card"], [], True),
    "STDSAUTO": (["tightening", "auto"], [], True),
    "STDSOTHCONS": (["tightening", "consumer"], ["credit card"], True),
    # Subprime MORTGAGE standards, not consumer loans.
    "DRTSSP": (["tightening", "subprime", "mortgage"], ["consumer"], True),
    # GSE-eligible MORTGAGE standards. Was labelled a demand series and so
    # carried alert_rule "none"; that is what this row exists to hold down.
    "SUBLPDHMSENQ": (["tightening", "gse", "mortgage"], ["demand", "consumer"], True),
    # The swapped pair. Each must carry its own words and neither the other's.
    "SUBLPDRCSC": (["tightening", "construction"], ["nonfarm", "nonresidential"], True),
    "SUBLPDRCSN": (["tightening", "nonfarm", "nonresidential"], ["construction"], True),
    "SUBLPDRCSM": (["tightening", "multifamily"], ["construction", "nonfarm"], True),
    # Large banks only, and it is a standards measure, not a spreads measure.
    "SUBLPDCILSLGNQ": (["tightening", "large banks"], ["spread"], True),
}


def _seed_rows():
    rows = {}
    for group in (S.CONSUMER, S.COMMERCIAL):
        for row in group:
            rows[row["series_id"]] = row
    return rows


SEED = _seed_rows()


def test_every_sloos_series_in_the_seed_has_a_recorded_definition():
    """The check is worthless if a new series can slip in unchecked."""
    in_seed = {sid for sid, row in SEED.items()
               if row["category"] == "sloos_diffusion"}
    missing = sorted(in_seed - set(OFFICIAL))
    assert not missing, (
        "these SLOOS series carry no recorded publisher definition, so nothing "
        "is checking their labels: %s. Add them to OFFICIAL with the words the "
        "Board's own survey uses." % missing)
    stale = sorted(set(OFFICIAL) - in_seed)
    assert not stale, (
        "OFFICIAL names series the seed no longer has: %s" % stale)


@pytest.mark.parametrize("sid", sorted(OFFICIAL))
def test_the_title_says_what_the_publisher_says_it_is(sid):
    required, forbidden, _ = OFFICIAL[sid]
    title = SEED[sid]["title"].lower()
    for word in required:
        assert word in title, (
            "%s: the publisher's definition is a %r measure and the title does "
            "not say so -- %r" % (sid, word, SEED[sid]["title"]))
    for word in forbidden:
        assert word not in title, (
            "%s: the title claims %r, which belongs to a different series -- "
            "%r. This is the swap that shipped until 5 Sep 2026."
            % (sid, word, SEED[sid]["title"]))


@pytest.mark.parametrize("sid", sorted(OFFICIAL))
def test_a_tightening_series_is_not_wired_up_as_a_demand_series(sid):
    """The label is cosmetic; this is not.

    A series flagged as demand gets `alert_rule` "none" and never fires. Wire a
    tightening indicator that way and the dashboard silently stops warning.
    """
    _, _, is_tightening = OFFICIAL[sid]
    rule = SEED[sid]["alert_rule"]
    if is_tightening:
        assert rule == "sloos_level", (
            "%s measures tightening, so it must carry the sloos_level alert; it "
            "carries %r. SUBLPDHMSENQ shipped exactly this way -- a real "
            "mortgage-tightening signal with its alert switched off."
            % (sid, rule))
    else:
        assert rule == "none", (
            "%s measures demand, not tightening, so it must not carry a "
            "tightening alert; it carries %r" % (sid, rule))


def test_the_two_commercial_real_estate_labels_are_not_each_other():
    """The swap, stated as its own case so a regression names itself."""
    construction = SEED["SUBLPDRCSC"]["title"]
    nonfarm = SEED["SUBLPDRCSN"]["title"]
    assert "Construction" in construction and "Nonfarm" not in construction
    assert "Nonfarm" in nonfarm and "Construction" not in nonfarm
    assert construction != nonfarm


#: series id -> the unit its publisher states. Listed for series where a wrong
#: unit is invisible to arithmetic and glaring to a reader.
#:
#: Found 5 September 2026, photographing the workbook cell for a tie-out: four
#: G.19 series declared "billions $" beside values in millions. The Board's own
#: table prints 5,166,907.71 for June 2026 and so does the workbook -- calling
#: that billions is five quadrillion dollars of consumer credit. Nothing
#: computes with this field, so no numeric test could see it.
#:
#: The two Z.1 commercial-property series are deliberately absent. Our config
#: calls both "millions $", FRED labels one "Mil. of $" and the other "%", and
#: the Board describes both identically as price indexes. Three authorities,
#: three answers; pinning one here would be inventing a fact.
PUBLISHED_UNITS = {
    "TOTALSL": "millions $",
    "TOTALNS": "millions $",
    "REVOLSL": "millions $",
    "NONREVSL": "millions $",
    "TOTALSLAR": "percent (annual rate)",
}


def _all_rows():
    rows = {}
    for name in ("CONSUMER", "COMMERCIAL", "PRICE"):
        for row in getattr(S, name, []):
            rows[row["series_id"]] = row
    return rows


@pytest.mark.parametrize("sid", sorted(PUBLISHED_UNITS))
def test_the_declared_unit_is_the_unit_the_publisher_uses(sid):
    row = _all_rows()[sid]
    assert row["units"] == PUBLISHED_UNITS[sid], (
        "%s is published in %r and the workbook declares %r. These said "
        "'billions $' beside millions until 5 Sep 2026 -- a factor of a "
        "thousand on the line a person reads, with the number itself correct."
        % (sid, PUBLISHED_UNITS[sid], row["units"]))
