"""The 2025 tables hold the law as ENACTED, not as forecast a year earlier.

FOUND BY TYING ONE FIGURE TO THE IRS, 6 September 2026 -- and it could not have
been found any other way.

`configs/crosswalk/federal/2025.yaml` held the standard deduction as the IRS
published it in **Rev. Proc. 2024-40, October 2024**. **P.L. 119-21 (OBBBA),
signed 4 July 2025, raised it for tax year 2025 itself** -- single 15,000 ->
15,750, MFJ 30,000 -> 31,500, HOH 22,500 -> 23,625. The revenue procedure is the
authority for the *inflation adjustments*; it is not the last word on 2025 law,
and nine months later it was superseded.

The estimator therefore overstated federal tax on **every 2025 estimate it
produced**: $165 on a single filer with $100,000 of wages, more on a joint
return, and growing with the marginal rate.

WHY THE SUITE COULD NOT CATCH IT, AND WHY THIS FILE IS SHAPED THE WAY IT IS.

`test_withholding_engine.py` works out its expected answers from the same
brackets and deductions the engine reads. That is the right shape for testing
*arithmetic* -- and it means the code and the tests agree with each other while
both are wrong about the world. A test that derives from the file under test can
only ever confirm the file is self-consistent.

**So every figure below is a LITERAL, carried in this file with its citation,
and disagreeing with the crosswalk rather than reading from it.** Change
`2025.yaml` and this file goes red. That is the entire point: it is a second,
independent statement of what the law says, and the two have to match.

The exhibit that found it, with the IRS pages captured and the arithmetic done
by hand, is `docs/tie-out/withholding-2026-09-06/`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput
from satc.withholding.tax_data import load_tax_tables


# ── the law, as literals, with where each one comes from ──────────────────────

#: P.L. 119-21 (OBBBA) sec. 70102, as the IRS states it on
#: "How to update withholding to account for tax law changes for 2025":
#: "$31,500 (up from $30,000) ... $23,625 (up from $22,500) ... $15,750 (up
#: from $15,000)". Captured 6 Sep 2026; the page's own review date is 28-Jul-2026.
ENACTED_2025_STANDARD_DEDUCTION = {
    "single": Decimal("15750"),
    "married_jointly": Decimal("31500"),
    "married_separately": Decimal("15750"),
    "head_of_household": Decimal("23625"),
}

#: The amounts these replaced. Rev. Proc. 2024-40 sec. 2.15, page 12.
#: Held so the test can prove the file is no longer using them.
SUPERSEDED_2025_STANDARD_DEDUCTION = {
    "single": Decimal("15000"),
    "married_jointly": Decimal("30000"),
    "married_separately": Decimal("15000"),
    "head_of_household": Decimal("22500"),
}

#: Rev. Proc. 2024-40 sec. 2.01, Tables 1-3, page 6. Each entry is the
#: threshold and the "$X plus Y% of the excess over" amount the IRS PRINTS
#: beside it -- an independent statement about every bracket edge below it.
#: These were NOT superseded by OBBBA.
IRS_PRINTED_BASES = {
    "single": [(11925, "1192.50"), (48475, "5578.50"), (103350, "17651"),
               (197300, "40199"), (250525, "57231"), (626350, "188769.75")],
    "married_jointly": [(23850, "2385"), (96950, "11157"), (206700, "35302"),
                        (394600, "80398"), (501050, "114462"), (751600, "202154.50")],
    "head_of_household": [(17000, "1700"), (64850, "7442"), (103350, "15912"),
                          (197300, "38460"), (250500, "55484"), (626350, "187031.50")],
}


@pytest.fixture(scope="module")
def tables():
    got, _ = load_tax_tables(2025)
    return got


# ── the standard deduction ────────────────────────────────────────────────────

@pytest.mark.parametrize("status,enacted", ENACTED_2025_STANDARD_DEDUCTION.items())
def test_the_standard_deduction_is_the_enacted_figure(tables, status, enacted):
    """THE DEFECT."""
    assert tables.standard_deduction(status) == enacted, (
        f"{status} uses {tables.standard_deduction(status)}; P.L. 119-21 sets "
        f"{enacted} for tax year 2025")


@pytest.mark.parametrize("status,superseded", SUPERSEDED_2025_STANDARD_DEDUCTION.items())
def test_the_superseded_figure_is_not_in_use(tables, status, superseded):
    """Stated the other way round, so a partial revert is caught too.

    The two dictionaries differ for every status, so this cannot pass by
    accident -- and it names the old number, which is what somebody restoring
    Rev. Proc. 2024-40 by mistake would put back.
    """
    assert tables.standard_deduction(status) != superseded


def test_the_two_sets_of_figures_actually_differ():
    """The denominator. If enacted and superseded were ever the same, both tests
    above would pass while proving nothing at all."""
    for status in ENACTED_2025_STANDARD_DEDUCTION:
        assert (ENACTED_2025_STANDARD_DEDUCTION[status]
                != SUPERSEDED_2025_STANDARD_DEDUCTION[status]), status


# ── the brackets, which OBBBA did not touch ───────────────────────────────────

@pytest.mark.parametrize("status", sorted(IRS_PRINTED_BASES))
def test_the_brackets_reproduce_what_the_irs_prints(tables, status):
    """The IRS prints, for each band, the tax accumulated below it.

    Those printed amounts are an independent arithmetic statement about every
    bracket edge underneath, so a single mistyped edge shifts all of them. This
    is the check that says the bracket table is right, and it is not derived
    from the bracket table.
    """
    brackets = tables.ordinary_brackets(status)
    for threshold, printed in IRS_PRINTED_BASES[status]:
        thresh, accumulated, low = Decimal(threshold), Decimal(0), Decimal(0)
        for b in brackets:
            if b.up_to is None or b.up_to >= thresh:
                accumulated += (thresh - low) * b.rate
                break
            accumulated += (b.up_to - low) * b.rate
            low = b.up_to
        assert accumulated == Decimal(printed), (
            f"{status} at {threshold:,}: our brackets imply {accumulated}, "
            f"the IRS prints {printed}")


# ── the figure the tie-out proved, end to end ─────────────────────────────────

def test_the_tie_out_case_lands_on_the_hand_computed_irs_figure():
    """$100,000 of wages, single, 2025 — the exhibit's case.

        taxable income = 100,000 − 15,750 = 84,250
        tax            = 5,578.50 + 22% × (84,250 − 48,475) = 13,449.00

    The right-hand side is computed here from the IRS's own printed base and
    rate, not from the crosswalk.
    """
    result = estimate(EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 100000,
                    "pay_periods_remaining": 1, "federal_tax_withheld_per_period": 0},
    }))
    by_hand = Decimal("5578.50") + Decimal("0.22") * (Decimal("84250") - Decimal("48475"))

    assert result.breakdown.taxable_income == Decimal("84250.00")
    assert result.breakdown.total_tax_liability == by_hand == Decimal("13449.00")


def test_the_old_answer_is_gone():
    """13,614.00 is what the estimator said before this was fixed. Named, so the
    regression is unmistakable rather than a number that merely moved."""
    result = estimate(EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 100000,
                    "pay_periods_remaining": 1},
    }))
    assert result.breakdown.total_tax_liability != Decimal("13614.00")


# ── what is NOT modelled is declared, not assumed ─────────────────────────────

def test_the_estimate_says_what_it_does_not_model():
    """"Fix the three, flag the rest" — the flag half.

    OBBBA also created deductions for tips, overtime, car loan interest and
    seniors, raised the SALT cap and changed the child tax credit. None are
    modelled. A half-reconciled table that LOOKS current is worse than one that
    is obviously stale, so the estimate says so on the screen.
    """
    result = estimate(EstimatorInput.from_dict({
        "filing_status": "single", "tax_year": 2025,
        "paystub": {"pay_frequency": "annual", "taxable_wages_per_period": 100000,
                    "pay_periods_remaining": 1},
    }))
    said = " ".join(result.notes)
    assert "NOT modelled" in said
    for provision in ("tips", "overtime", "car loan interest", "seniors", "SALT"):
        assert provision in said, provision
    assert "too high" in said, "the note does not say which way the error runs"


def test_the_gap_is_read_from_the_dated_table_not_hardcoded():
    """So the list cannot drift from the year it describes. A year that models
    everything has no such key and says nothing."""
    from satc.crosswalk import CrosswalkLibrary

    crosswalk = CrosswalkLibrary().resolve(2025, "US")
    listed = crosswalk.value("obbba_not_modeled")
    assert listed, "the crosswalk carries no declaration of what it omits"
    assert any("tips" in str(x) for x in listed)


# ── the screen ────────────────────────────────────────────────────────────────

def test_the_note_reaches_the_withholding_screen(tmp_path, monkeypatch):
    """A declaration computed and never displayed is the same as no declaration."""
    from satc.app.server import create_app
    from satc.app.state import AppState
    from satc.persistence import SATCStore

    monkeypatch.setattr("satc.app.server.STATE", AppState(store=SATCStore(tmp_path / "s")))
    client = create_app().test_client()
    body = client.post("/withholding", data={
        "filing_status": "single", "tax_year": "2025",
        "j0_name": "Case", "j0_pay_frequency": "annual",
        "j0_gross_pay_per_period": "100000",
        "j0_federal_tax_withheld_per_period": "0",
        "j0_retirement_pretax_per_period": "0",
        "j0_pay_periods_remaining": "1",
    }).get_data(as_text=True)

    assert "$15,750" in body, "the screen still shows the superseded deduction"
    assert "13,449" in body
    assert "NOT modelled" in body
