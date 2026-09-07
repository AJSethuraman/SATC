"""Self-employment tax, tied line by line to Schedule SE (Form 1040).

The fourth of nine parts of the withholding engine to be checked against a
source outside our own code. Schedule C work is core to this practice, so this
is the computation most SATC clients with a side business depend on.

THE FORM, quoted from the 2025 Schedule SE as published on irs.gov and fetched
7 September 2026. Every figure below is a LITERAL taken from it, disagreeing
with our crosswalk rather than reading from it:

    line 4a   "If line 3 is more than zero, multiply line 3 by 92.35% (0.9235)."
    line 4c   "Combine lines 4a and 4b. If less than $400, stop; you don't owe
               self-employment tax."
    line 7    "$176,100" -- the maximum combined wages and self-employment
               earnings subject to social security tax for 2025
    line 9    "Subtract line 8d from line 7. If zero or less, enter -0-"
    line 10   "Multiply the smaller of line 6 or line 9 by 12.4% (0.124)"
    line 11   "Multiply line 6 by 2.9% (0.029)"
    line 13   "Multiply line 12 by 50% (0.50)"

WHAT THIS FOUND. The engine had every rate and the wage base right, and
implemented lines 7 through 13 exactly -- including the part most likely to be
wrong, where wages already taxed for social security eat into the room under the
cap. **It did not have line 4c.** On net earnings of $400 it charged $56.52
where the form charges nothing; on $430, $60.76. Small money, common shape -- a
side gig, a little 1099 income -- and it overstated the client's tax, the same
direction as the standard-deduction defect found the day before.

Nothing could have caught it from inside: `test_withholding_engine` works out
its expected answer from the same constants the engine uses, so the code and the
test agreed while both were missing a line of the form.

AND ONE CONSEQUENCE THAT IS INFERRED RATHER THAN QUOTED. Form 8959 line 8 says
*"Enter your self-employment income from Schedule SE (Form 1040), Part I,
line 6"* -- a line you never reach when 4c stops you, so the Additional Medicare
Tax sees nothing either. Form 8959's instructions do not spell out the
"Schedule SE was not required" case; this follows from the line it names. It is
marked as an inference here and in the engine rather than presented as a
citation.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput
from satc.withholding.tax_data import load_tax_tables

# ── Schedule SE, as literals ──────────────────────────────────────────────────
NET_EARNINGS_FACTOR = Decimal("0.9235")       # line 4a
MINIMUM_NET_EARNINGS = Decimal("400")         # line 4c
SS_WAGE_BASE_2025 = Decimal("176100")         # line 7
SS_RATE = Decimal("0.124")                    # line 10
MEDICARE_RATE = Decimal("0.029")              # line 11
DEDUCTIBLE_SHARE = Decimal("0.50")            # line 13


@pytest.fixture(scope="module")
def tables():
    got, _ = load_tax_tables(2025)
    return got


def _estimate(net_se, wages=0, status="single"):
    return estimate(EstimatorInput.from_dict({
        "filing_status": status, "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": wages,
                    "pay_periods_remaining": 1, "federal_tax_withheld_per_period": 0},
        "other_income": {"self_employment_net": net_se}}))


def _cents(value):
    """Round half UP, which is the tax convention and what the engine uses.

    THIS LINE COST TWO FAILURES AND THEY WERE MINE. The first draft used
    `.quantize(Decimal("0.01"))` with no mode, which is Python's default
    ROUND_HALF_EVEN -- banker's rounding. On net earnings of $150,000 the exact
    figure is $21,194.325: half up gives 21,194.33, banker's gives 21,194.32,
    and the test called the engine wrong over one cent.

    Worth recording rather than quietly fixing, because it is exactly the shape
    a tie-out is meant to surface -- two ways of doing the same arithmetic that
    agree everywhere except on a half. The engine's `_money` has used
    ROUND_HALF_UP throughout; the checker was the thing that was wrong.
    """
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _by_the_form(net_se, wages=Decimal(0)):
    """Schedule SE Part I, done here from the literals above and nothing of ours."""
    base = Decimal(net_se) * NET_EARNINGS_FACTOR                      # line 4a
    if base < MINIMUM_NET_EARNINGS:                                   # line 4c
        return Decimal("0.00")
    room = max(SS_WAGE_BASE_2025 - Decimal(wages), Decimal(0))        # line 9
    ss = min(base, room) * SS_RATE                                    # line 10
    medicare = base * MEDICARE_RATE                                   # line 11
    return _cents(ss + medicare)


# ── the constants ─────────────────────────────────────────────────────────────

def test_the_constants_are_the_ones_the_form_prints(tables):
    assert tables.se_net_earnings_factor == NET_EARNINGS_FACTOR
    assert tables.ss_wage_base == SS_WAGE_BASE_2025
    assert tables.se_social_security_rate == SS_RATE
    assert tables.se_medicare_rate == MEDICARE_RATE
    assert tables.se_minimum_net_earnings == MINIMUM_NET_EARNINGS


# ── line 4c, the defect ───────────────────────────────────────────────────────

@pytest.mark.parametrize("net_se", ["100", "400", "430"])
def test_below_the_floor_no_se_tax_is_owed(net_se):
    """THE DEFECT. Line 4c: "If less than $400, stop; you don't owe
    self-employment tax." The engine charged $56.52 on $400."""
    assert Decimal(net_se) * NET_EARNINGS_FACTOR < MINIMUM_NET_EARNINGS, \
        "wrong precondition — this case is above the floor"
    assert _estimate(net_se).breakdown.self_employment_tax == Decimal("0.00")


def test_the_floor_is_tested_after_the_92_35_percent_step():
    """WHICH AMOUNT the $400 applies to, and it is not the one you first think.

    Line 4c tests lines 4a+4b — that is, AFTER the 92.35% reduction. Net earnings
    of $430 are above $400 and still owe nothing, because 4a brings them to
    $397.10. Testing the floor against the raw figure would charge them.
    """
    assert Decimal("430") > MINIMUM_NET_EARNINGS                    # raw is above
    assert Decimal("430") * NET_EARNINGS_FACTOR < MINIMUM_NET_EARNINGS  # 4a is below
    assert _estimate("430").breakdown.self_employment_tax == Decimal("0.00")


def test_just_above_the_floor_the_tax_appears():
    """The control. A floor that swallows everything is not a floor."""
    assert Decimal("440") * NET_EARNINGS_FACTOR >= MINIMUM_NET_EARNINGS
    got = _estimate("440").breakdown.self_employment_tax
    assert got == _by_the_form("440") == Decimal("62.17")


def test_the_deductible_half_goes_too(tables):
    """Line 13 halves line 12. No SE tax, nothing to halve — and half of a tax
    that is not owed would reduce AGI for nothing."""
    below = _estimate("400")
    above = _estimate("440")
    assert below.breakdown.self_employment_tax == 0
    assert above.breakdown.self_employment_tax > 0
    # the deduction moves AGI, so compare the two AGIs against wages of 0
    assert below.breakdown.adjusted_gross_income == Decimal("400.00")
    assert (above.breakdown.adjusted_gross_income
            == Decimal("440") - _cents(above.breakdown.self_employment_tax * DEDUCTIBLE_SHARE))


# ── lines 7 to 11, which were already right ───────────────────────────────────

@pytest.mark.parametrize("net_se", ["440", "1000", "50000", "150000", "200000"])
def test_the_computation_matches_the_form(net_se):
    assert _estimate(net_se).breakdown.self_employment_tax == _by_the_form(net_se)


def test_the_social_security_portion_stops_at_the_wage_base():
    """Line 10 takes the SMALLER of line 6 or line 9. Above the base the social
    security portion stops and only the 2.9% keeps running."""
    base = Decimal("200000") * NET_EARNINGS_FACTOR
    assert base > SS_WAGE_BASE_2025, "wrong precondition — under the cap"
    expected = _cents(SS_WAGE_BASE_2025 * SS_RATE + base * MEDICARE_RATE)
    assert _estimate("200000").breakdown.self_employment_tax == expected


def test_wages_already_taxed_eat_into_the_room_under_the_cap():
    """LINE 9: "Subtract line 8d from line 7." The part most likely to be wrong,
    and the engine had it. A client with $150,000 of wages has only $26,100 of
    room left before the social security portion of their SE tax stops."""
    wages = Decimal("150000")
    room = SS_WAGE_BASE_2025 - wages
    assert room == Decimal("26100")
    got = _estimate("60000", wages=wages).breakdown.self_employment_tax
    assert got == _by_the_form("60000", wages=wages)
    # and it is genuinely capped by the room rather than by the base
    base = Decimal("60000") * NET_EARNINGS_FACTOR
    assert base > room, "wrong precondition — the room is not binding here"


def test_wages_over_the_base_leave_no_room_at_all():
    """Line 9: "If zero or less, enter -0-." Only the Medicare portion remains."""
    got = _estimate("50000", wages=Decimal("180000")).breakdown.self_employment_tax
    expected = _cents(Decimal("50000") * NET_EARNINGS_FACTOR * MEDICARE_RATE)
    assert got == expected


# ── the inferred consequence, marked as inferred ──────────────────────────────

def test_additional_medicare_also_sees_nothing_below_the_floor():
    """INFERRED, NOT QUOTED. Form 8959 line 8 reads Schedule SE line 6, which
    does not exist when 4c stopped the schedule. Form 8959's instructions do not
    address that case; this follows from the line it names.

    Asserted because the two must not disagree — one function answers both.
    """
    r = _estimate("400", wages=Decimal("250000"))
    assert r.breakdown.self_employment_tax == 0
    plain = _estimate("0", wages=Decimal("250000"))
    assert r.breakdown.additional_medicare_tax == plain.breakdown.additional_medicare_tax, (
        "SE earnings below the Schedule SE floor still reached Form 8959")


def test_above_the_floor_additional_medicare_does_see_it():
    """The control. The floor must not silently remove SE income from Form 8959
    for everybody."""
    with_se = _estimate("50000", wages=Decimal("250000"))
    without = _estimate("0", wages=Decimal("250000"))
    assert with_se.breakdown.additional_medicare_tax > without.breakdown.additional_medicare_tax


# ── the denominator ───────────────────────────────────────────────────────────

def test_no_self_employment_means_no_se_tax():
    assert _estimate("0").breakdown.self_employment_tax == 0
    assert _estimate("-500").breakdown.self_employment_tax == 0


def test_the_floor_and_the_cap_are_different_numbers():
    """Without this, a test suite could pass with the two swapped."""
    assert MINIMUM_NET_EARNINGS != SS_WAGE_BASE_2025
    assert MINIMUM_NET_EARNINGS < SS_WAGE_BASE_2025
