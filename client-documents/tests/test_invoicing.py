"""The estimate becomes the invoice, and cannot disagree with it.

The rule this file defends: **an invoice is built from the priced engagement,
never typed alongside it.** Two documents stating the same money from two
sources will eventually disagree, and the one the client keeps is the one that
says the larger number.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import invoicing  # noqa: E402
import pricing  # noqa: E402


def _record(**over):
    base = {
        "LineItems": [
            {"Service": "Standard", "Detail": "Schedules", "Amount": "$325.00"},
            {"Service": "Rental schedule", "Detail": "Schedule E", "Amount": "$145.00"},
        ],
        "EstimateTotal": "$470.00",
        "LetterDate": "February 3, 2027",
    }
    base.update(over)
    return base


def _build(**kw):
    kw.setdefault("number", "2027-0001")
    kw.setdefault("billed", "2026 tax year")
    kw.setdefault("today", date(2027, 4, 20))
    record = kw.pop("record", None) or _record()
    return invoicing.build(record, **kw)


# ── the lines come from the estimate ──────────────────────────────────────

def test_the_invoice_bills_exactly_what_the_estimate_quoted():
    inv = _build()
    assert [i["Service"] for i in inv["LineItems"]] == ["Standard", "Rental schedule"]
    assert inv["Subtotal"] == "$470.00"
    assert inv["AmountDue"] == "$470.00"


def test_the_invoice_carries_the_estimate_it_came_from():
    """A client comparing the two documents should not have to fetch one."""
    inv = _build()
    assert inv["EstimateTotal"] == "$470.00"
    assert inv["EstimateDate"] == "February 3, 2027"


def test_an_unpriced_engagement_cannot_be_invoiced():
    with pytest.raises(invoicing.InvoiceError) as exc:
        _build(record=_record(LineItems=[]))
    assert "nothing to invoice" in str(exc.value)


def test_a_line_that_cannot_be_added_up_refuses():
    """An invoice whose total omits a line is worse than one that refuses."""
    bad = _record(LineItems=[{"Service": "Mystery", "Detail": "",
                              "Amount": "[CONFIRM: what this costs]"}])
    with pytest.raises(invoicing.InvoiceError) as exc:
        _build(record=bad)
    assert "Mystery" in str(exc.value)


# ── the variance rule ─────────────────────────────────────────────────────

def test_billing_over_the_estimate_without_saying_why_refuses():
    """`registry/fields.yaml` has always said the note is "not optional when
    the invoice exceeds the estimate". A rule stated in a registry and
    enforced nowhere is a rule that holds until the first busy week — which is
    exactly when a client gets a bigger bill than they were quoted.
    """
    over = _record(LineItems=_record()["LineItems"] +
                   [{"Service": "Brokerage entered by hand", "Detail": "",
                     "Amount": "$95.00"}])
    with pytest.raises(invoicing.InvoiceError) as exc:
        _build(record=over)
    assert "$565.00" in str(exc.value) and "$470.00" in str(exc.value)


def test_billing_over_the_estimate_with_a_note_is_fine():
    over = _record(LineItems=_record()["LineItems"] +
                   [{"Service": "Brokerage entered by hand", "Detail": "",
                     "Amount": "$95.00"}])
    inv = _build(record=over,
                 variance_note="Your 1099-B could not be summarised.")
    assert inv["AmountDue"] == "$565.00"
    assert "1099-B" in inv["VarianceNote"]


def test_billing_UNDER_the_estimate_needs_no_note():
    """A smaller bill than quoted is good news and explains itself."""
    under = _record(LineItems=[_record()["LineItems"][0]])
    inv = _build(record=under)
    assert inv["AmountDue"] == "$325.00"
    assert inv["VarianceNote"] == ""


def test_an_estimate_that_never_totalled_is_not_compared_against():
    """Inventing a comparison is worse than not making one."""
    odd = _record(EstimateTotal="[CONFIRM: 1 line cannot be priced]")
    inv = _build(record=odd)
    assert inv["AmountDue"] == "$470.00"


# ── credits ───────────────────────────────────────────────────────────────

def test_a_credit_reduces_the_amount_due_and_prints_a_real_minus():
    inv = _build(credits=[{"label": "Retainer held", "detail": "paid 1 Feb",
                           "amount": 200}])
    assert inv["AmountDue"] == "$270.00"
    assert inv["CreditAmount"].startswith("−"), "a real minus sign, not a hyphen"
    assert "Retainer held" in inv["CreditLabel"]


def test_a_negative_credit_refuses():
    """A credit is entered as what it is WORTH. Letting a minus sign through
    here is how a credit quietly increases a bill."""
    with pytest.raises(invoicing.InvoiceError) as exc:
        _build(credits=[{"label": "Oops", "amount": -200}])
    assert "positive amount" in str(exc.value)


# ── the period, and the numbers ───────────────────────────────────────────

def test_the_billed_period_is_required_and_is_not_the_engagement_period():
    """`PeriodLabel` means something different on each document. One shared
    value prints the wrong thing on one of them."""
    with pytest.raises(invoicing.InvoiceError) as exc:
        _build(billed="")
    assert "BILLS" in str(exc.value)


def test_numbers_are_sequential_and_never_reused(tmp_path):
    assert invoicing.next_number(tmp_path, year=2027) == "2027-0001"
    d = tmp_path / "2027-0001" / "invoices"
    d.mkdir(parents=True)
    (d / "a.json").write_text(json.dumps({"InvoiceNumber": "2027-0001"}))
    (d / "b.json").write_text(json.dumps({"InvoiceNumber": "2027-0004"}))
    assert invoicing.next_number(tmp_path, year=2027) == "2027-0005", (
        "the next number is past the HIGHEST issued, not a count — deleting "
        "an invoice must never hand its number to a second client"
    )


def test_an_unreadable_invoice_file_does_not_free_up_its_number(tmp_path):
    """Too high wastes a number. Too low reuses one."""
    d = tmp_path / "2027-0001" / "invoices"
    d.mkdir(parents=True)
    (d / "good.json").write_text(json.dumps({"InvoiceNumber": "2027-0003"}))
    (d / "broken.json").write_text("{ not json")
    assert invoicing.next_number(tmp_path, year=2027) == "2027-0004"


def test_an_invoice_equal_to_its_estimate_needs_no_variance_note():
    """Money is compared in cents, not in floats.

    A sorting amount a preparer types with cents in it -- 175.08 -- sums to
    275.08000000000004, while the estimate string re-parses to exactly 275.08.
    The invoice that billed EXACTLY its estimate was refused, with a message
    reading "bills $275.08 against an estimate of $275.08".

    The refusal was loud rather than silent, which is why nothing caught it --
    but the preparer's way out of it was to write a variance note explaining a
    difference that does not exist, and that puts a false sentence on a
    client's bill. `consistency.py` has rounded to integer cents since it was
    written; this was the one place on the money path that did not.
    """
    schedule = pricing.load()
    record = pricing.price(
        {"federal_form": "1040", "federal_schedules": [],
         "other_income_documents": "no", "count_sorting": 1,
         "sorting_amount": 175.08, "count_states": 1},
        schedule)
    assert record["EstimateTotal"] == "$275.08"
    bill = invoicing.build(record, number="2026-0001", billed="2026 tax year")
    assert bill["Subtotal"] == "$275.08"


def test_a_real_overage_still_refuses_without_a_reason():
    """The cents comparison must not have blunted the check it fixed."""
    schedule = pricing.load()
    record = pricing.price(
        {"federal_form": "1040", "federal_schedules": [],
         "other_income_documents": "no", "count_sorting": 1,
         "sorting_amount": 175.08, "count_states": 1},
        schedule)
    quoted_low = dict(record, EstimateTotal="$100.00")
    with pytest.raises(invoicing.InvoiceError, match="says nothing about"):
        invoicing.build(quoted_low, number="2026-0002", billed="2026 tax year")

    # A single cent over is still over.
    one_cent_under = dict(record, EstimateTotal="$275.07")
    with pytest.raises(invoicing.InvoiceError, match="says nothing about"):
        invoicing.build(one_cent_under, number="2026-0003",
                        billed="2026 tax year")
