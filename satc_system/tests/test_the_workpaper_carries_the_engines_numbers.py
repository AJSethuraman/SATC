"""The workpaper the client is handed, tied to the engine that produced it.

**THE HOP NOBODY HAD EXECUTED.** Nine parts of the withholding engine were tied
to IRS documents on 7 September 2026 -- the rate tables to Rev. Proc. 2024-40,
self-employment tax to Schedule SE, the surtaxes to Forms 8959 and 8960, and so
on. Every one of those read the `ours` side out of `estimate()`.

**`estimate()` is not what anybody is handed.** The preparer downloads an Excel
workpaper and gives it to the client, and between the engine and that file sits
`audit_tape.build_audit_tape`, which nothing had ever checked figure by figure.
So the chain that was proved is:

    IRS document  =  engine          proved, nine parts
    engine        =  the workpaper   NEVER EXECUTED

which is canon's tie-out skill describing its own named failure: *"comparing the
source against something upstream of the artifact proves that the intermediate
agrees with the source. It says nothing about the number on the screen, and the
last hop is the one the reader depends on."* This file is that last hop.

WHAT EXISTED BEFORE. One test, and it asserted that
`float(result.breakdown.total_tax_liability) in numbers` -- that **one** of the
sheet's figures appeared **somewhere** among its numeric cells. It would have
passed with every figure in the wrong row, with the W-4 line 4c number wrong, or
with the deduction showing a superseded amount, because it never asked which
cell held what.

WHAT THIS FOUND, and both are about a workpaper being *read* rather than computed:

* **Three labels appeared twice in one sheet.** `Self-employment tax`,
  `Additional Medicare tax` and `Net investment income tax` each named a dollar
  amount in the projection walk AND a citation in the tax-law basis block. It
  was found because it broke the first draft of this test -- a checker keyed by
  label silently kept the second of each pair and reported three false
  mismatches. If a label collision can mislead a program reading the file, it
  can mislead the client reading it.
* **The `Source` line named a superseded authority.** It read
  *"IRS Rev. Proc. 2024-40; SSA; ..."* -- the revenue procedure -- while the
  Standard deduction row three cells below correctly cited P.L. 119-21, the law
  that superseded it in July 2025. A header disagreeing with the row beneath it
  is canon's one sentence: a claim in one place, the behaviour in another, and
  nothing comparing them.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.withholding.audit_tape import build_audit_tape
from satc.withholding.engine import estimate
from satc.withholding.models import EstimatorInput

BASIS_HEADER = "Tax-law basis"


def _stub(**over):
    stub = {"pay_frequency": "biweekly", "gross_pay_per_period": 3800,
            "taxable_wages_per_period": 3800, "federal_tax_withheld_per_period": 395,
            "pay_periods_remaining": 8, "ytd_taxable_wages": 65000,
            "ytd_federal_tax_withheld": 7110, "adjust_withholding": True}
    stub.update(over)
    return stub


#: Three genuinely different clients. One shape would leave every surtax at zero,
#: and a workpaper that writes 0.00 into the wrong row still matches on a client
#: who owes nothing -- which is most of them, and is why the third case is here.
CLIENTS = {
    "wages only": {"filing_status": "single", "tax_year": 2025, "paystub": _stub()},
    "wages and a Schedule C": {
        "filing_status": "single", "tax_year": 2025, "paystub": _stub(),
        "other_income": {"self_employment_net": 60000}},
    "joint, gains, self-employment and NIIT": {
        "filing_status": "married_jointly", "tax_year": 2025,
        "paystub": _stub(gross_pay_per_period=12000, taxable_wages_per_period=12000,
                         federal_tax_withheld_per_period=3000, pay_periods_remaining=10,
                         ytd_taxable_wages=190000, ytd_federal_tax_withheld=45000),
        "other_income": {"interest": 40000, "long_term_capital_gains": 80000,
                         "self_employment_net": 30000}},
}


def _sheet(data):
    inp = EstimatorInput.from_dict(data)
    result = estimate(inp)
    return result, build_audit_tape(result, inp).active


def _labelled_rows(ws):
    """Every row that puts a label in column A and something in column C."""
    for i, row in enumerate(ws.iter_rows(), 1):
        v = {c.column_letter: c.value for c in row if c.value is not None}
        if "A" in v and "C" in v:
            yield i, str(v["A"]).strip(), v["C"]


def _basis_row(ws):
    """Where money stops and citations start."""
    return next((i for i, row in enumerate(ws.iter_rows(), 1)
                 if row[0].value and BASIS_HEADER in str(row[0].value)), ws.max_row + 1)


def _rows(ws, *, before_basis: bool):
    """Label to value, read out of the file the preparer opens.

    Split at the tax-law basis header on purpose: above it the third column
    holds MONEY, below it the same column holds CITATIONS. A reader keyed on
    label alone crosses that line, which is exactly what happened.
    """
    cut = _basis_row(ws)
    out = {}
    for i, label, value in _labelled_rows(ws):
        if (i < cut) is before_basis:
            out.setdefault(label, value)
    return out


def _figures(result):
    b, w = result.breakdown, result.recommendation
    return {
        "Adjusted gross income": b.adjusted_gross_income,
        "Deduction used": b.deduction_used,
        "Taxable income": b.taxable_income,
        "Ordinary income tax": b.ordinary_income_tax,
        "Capital-gains / qualified-dividend tax": b.capital_gains_tax,
        "Self-employment tax": b.self_employment_tax,
        "Additional Medicare tax": b.additional_medicare_tax,
        "Net investment income tax": b.net_investment_income_tax,
        "Total tax liability": b.total_tax_liability,
        "Withholding to date (all jobs)": w.ytd_withholding,
        "Projected balance (+refund / -due)": w.projected_balance,
        "Recommended withholding per period": w.recommended_withholding_per_period,
        "Additional per period (W-4 line 4c)": w.additional_withholding_per_period,
    }


# -- the last hop -------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(CLIENTS))
def test_every_figure_in_the_workpaper_is_the_figure_the_engine_computed(name):
    """Cell by cell, by name, out of the workbook -- not a membership test.

    Thirteen figures on three clients. Nine of the engine's parts are tied to an
    IRS document; this is what makes those nine mean something for the person
    holding the printout.
    """
    result, ws = _sheet(CLIENTS[name])
    rows = _rows(ws, before_basis=True)

    wrong = []
    for label, engine_value in _figures(result).items():
        got = rows.get(label, "<<the workpaper has no such row>>")
        if not isinstance(got, (int, float)) or Decimal(str(got)) != Decimal(str(engine_value)):
            wrong.append(f"{label}: workpaper {got!r}, engine {engine_value}")
    assert not wrong, f"{len(wrong)} of 13 figures disagree on '{name}':\n  " + "\n  ".join(wrong)


def test_the_w4_number_the_client_acts_on_is_on_the_page_and_says_what_it_is():
    """Of the thirteen, this is the one somebody copies onto a form. It has to
    be there, be right, and be labelled with the box it goes in."""
    result, ws = _sheet(CLIENTS["wages only"])
    rows = _rows(ws, before_basis=True)
    label = "Additional per period (W-4 line 4c)"
    assert label in rows, "the workpaper does not carry the number the client acts on"
    assert Decimal(str(rows[label])) == result.recommendation.additional_withholding_per_period


# -- the collision that broke the first draft of this test --------------------

@pytest.mark.parametrize("name", sorted(CLIENTS))
def test_no_label_names_two_different_rows(name):
    """THE FINDING. Three labels named both a dollar amount and a citation.

    A checker keyed by label kept the second of each pair and reported three
    mismatches that were not there -- behaviour 3's *"the checker is the likelier
    culprit than the code"*, except here both were: my reader was wrong AND the
    sheet had one label on two rows. A client reading down the page for
    'Self-employment tax' would have found it twice, meaning two things.
    """
    _, ws = _sheet(CLIENTS[name])
    labels = [label for _, label, _ in _labelled_rows(ws)]
    repeated = sorted({x for x in labels if labels.count(x) > 1})
    assert not repeated, f"one label on two rows, in a document a client reads: {repeated}"


# -- the citations, which are the whole point of a workpaper ------------------

def test_the_standard_deduction_cites_the_law_that_actually_applies():
    """The tie-out found the engine using a superseded standard deduction. The
    workpaper has to carry the citation that replaced it, not the one it was
    built from."""
    _, ws = _sheet(CLIENTS["wages only"])
    cited = str(_rows(ws, before_basis=False).get("Standard deduction", ""))
    assert "119-21" in cited, f"the workpaper cites {cited!r} for the standard deduction"


def test_the_source_line_does_not_contradict_the_row_beneath_it():
    """THE SECOND FINDING. The Source header read 'IRS Rev. Proc. 2024-40; ...'
    while the Standard deduction row three cells below cited P.L. 119-21 -- the
    law that superseded it. Canon's one sentence: a claim in one place, the
    behaviour in another, and nothing comparing them. This is the comparison.
    """
    _, ws = _sheet(CLIENTS["wages only"])
    source = str(_rows(ws, before_basis=False).get("Source", ""))
    assert source, "the workpaper names no source at all"
    assert "119-21" in source, (
        f"the Source line reads {source!r}, which does not mention the enacted law "
        "the Standard deduction row below it cites")


def test_the_paystub_mark_travels_onto_the_workpaper():
    """The ninth part could not be tied to any IRS document, so it is marked on
    the screen. A mark that does not survive onto the printout marks nothing --
    the printout is what leaves the office."""
    _, ws = _sheet(CLIENTS["wages only"])
    text = " ".join(str(c.value) for row in ws.iter_rows()
                    for c in row if c.value is not None)
    assert "read by software" in text
    assert "Compare the wages and withholding above against the stub" in text


# -- the denominator ----------------------------------------------------------

def test_the_three_clients_are_genuinely_different():
    """Without this the parametrisation is decoration: three runs of one shape
    would leave every surtax at zero and prove nothing about those rows."""
    figures = {n: _figures(_sheet(d)[0]) for n, d in CLIENTS.items()}
    joint = figures["joint, gains, self-employment and NIIT"]
    assert figures["wages only"]["Self-employment tax"] == 0
    assert figures["wages and a Schedule C"]["Self-employment tax"] > 0, \
        "the Schedule C client owes no self-employment tax"
    assert joint["Net investment income tax"] > 0, "no client exercises the NIIT row"
    assert joint["Capital-gains / qualified-dividend tax"] > 0, "no client exercises the gains row"
    assert joint["Additional Medicare tax"] > 0, "no client exercises the surtax row"
