"""The invoice does not name a second price for work the client has a quote for.

D21, FROM THE WALK OF 5 SEPTEMBER 2026 — and it is the seam #267 was about.

Walked end to end on one day, for one household, under one engagement ref:

    The client's estimate (client-documents)   $350.00
    The firm's invoice (satc_system)           $450.00 full value

Same ref, same 2025 Form 1040. `Service`'s own docstring has said since #267
that *"this catalogue refuses to put a number on it — the refusal being the
point, because the failure mode is not a wrong number, it is a second confident
one."* `quote.py` implements that on the ESTIMATE route. `Invoice.add` read
`svc.standard_rate` regardless, so **the refusal existed in the documentation
and on one of the two paths.**

The firm settled it in the docket: *"One price, and it's the one on the client's
estimate."* The operating procedure already says what happens when two survive:
*"the one the client keeps is the one that says the larger number."*

WHY THE CHECK IS AS NARROW AS IT IS, AND IT TOOK A WRONG ANSWER TO FIND OUT.
The first version refused any `priced_by` service outright. That is defensible,
and it reddened **159 tests across twelve files** (measured, then measured again after
narrowing) — because it makes a tax
return unbillable anywhere until somebody types a figure in, which is a change
to how the firm bills and therefore theirs to make rather than mine. The
module's own sentence is the narrower rule: the failure is a SECOND number.
Where the engagement carries a price, this catalogue must not answer with a
different one; where it does not, the catalogue rate is the only figure anybody
has and billing it contradicts nothing.

AND THE FIGURE IS NOT TAKEN AUTOMATICALLY. `EngagementPrice.total` is a STRING
— `"$350.00"`, as written on the estimate the client is holding — and that
module says why: re-deriving it here *"would be a second rendering of the same
money and the two would eventually disagree"*. So the refusal NAMES the figure
and a person puts it in.

WHY THE REF IS AN ARGUMENT AND NOT A FIELD. `Invoice` has no link to its
engagement, which is the actual reason the engine could not check this. The ref
is needed to DECIDE a line, not to describe it afterwards, and a stored column
would mean migrating a store that holds real client data.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from satc.billing import engagement_price
from satc.billing.invoice import BillingError, Invoice
from satc.billing.catalogue import service, services

CLIENT = "SATC-001000"
YEAR = 2025
REF = "2026-0001"


@pytest.fixture()
def quoted(tmp_path, monkeypatch):
    """An engagements store holding a real estimate for REF, at $350.00."""
    record = tmp_path / REF
    record.mkdir(parents=True)
    # THE RECORD'S REAL SHAPE, read out of `price_for_ref` rather than invented.
    # The first draft of this fixture used a nested `quote` object, which
    # resolved to NoPrice -- and every assertion below would then have passed
    # for the wrong reason, because nothing refuses when there is no second
    # price. `test_the_engagement_price_actually_resolves` is what caught it.
    (record / "record.json").write_text(json.dumps({
        "EstimateTotal": "$350.00",
        "LineItems": [
            {"Service": "Simple Filer", "Amount": "$100.00"},
            {"Service": "Extension with a payment estimate", "Amount": "$75.00"},
            {"Service": "Records sorting", "Amount": "$175.00"},
        ],
    }), encoding="utf-8")
    monkeypatch.setenv(engagement_price.ENGAGEMENTS_ENV, str(tmp_path))
    return tmp_path


# ── the denominator ───────────────────────────────────────────────────────────

def test_the_service_still_says_somebody_else_prices_it(quoted):
    """Without `priced_by` on the catalogue entry there is nothing to enforce,
    and every assertion below is about a branch that cannot be reached."""
    assert service("return_1040").priced_by


def test_the_engagement_price_actually_resolves(quoted):
    """The other denominator. If the fixture does not resolve, the refusal
    below would not fire and the test would pass for the wrong reason."""
    got = engagement_price.price_for_ref(REF)
    assert got.is_priced, getattr(got, "reason", got)
    assert got.total == "$350.00"


def test_the_two_numbers_really_do_differ(quoted):
    """And that the catalogue's is the larger one, which is the direction that
    matters: "the one the client keeps is the one that says the larger number"."""
    assert service("return_1040").standard_rate == Decimal("450")


# ── the defect ────────────────────────────────────────────────────────────────

def test_billing_a_quoted_return_from_the_catalogue_is_refused(quoted):
    """THE DEFECT. This put 450.00 on the invoice while the client held 350.00."""
    invoice = Invoice(invoice_id="draft", client_id=CLIENT, tax_year=YEAR)
    with pytest.raises(BillingError) as exc:
        invoice.add("return_1040", engagement_ref=REF)

    said = str(exc.value)
    assert "$350.00" in said, "the refusal does not name the figure the client holds"
    assert REF in said, "the refusal does not say which engagement"
    assert not invoice.lines, "the line went on anyway"


def test_the_engagements_figure_is_accepted(quoted):
    """What the preparer is meant to do next, and it has to work."""
    invoice = Invoice(invoice_id="draft", client_id=CLIENT, tax_year=YEAR)
    invoice.add("return_1040", rate_override=Decimal("350"),
                note="the figure on engagement 2026-0001", engagement_ref=REF)
    assert invoice.lines[0].standard_rate == Decimal("350")
    assert invoice.total == Decimal("350.00")


# ── the controls, which are what keep this narrow ─────────────────────────────

def test_with_no_ref_the_catalogue_still_bills(quoted):
    """THE CONTROL THAT DEFINES THE SCOPE. No ref, no second number, no
    contradiction -- and 159 tests depend on this staying true,
    because they raise invoices without engagements. Measured: a blanket refusal
    reddens 159 across twelve files."""
    invoice = Invoice(invoice_id="draft", client_id=CLIENT, tax_year=YEAR)
    invoice.add("return_1040")
    assert invoice.lines[0].standard_rate == Decimal("450")


def test_a_ref_that_resolves_to_nothing_still_bills(quoted):
    """A ref with no record is not a second price -- it is a missing one, and
    refusing on it would stop billing over an unrelated file being absent."""
    invoice = Invoice(invoice_id="draft", client_id=CLIENT, tax_year=YEAR)
    invoice.add("return_1040", engagement_ref="2026-9999")
    assert invoice.lines[0].standard_rate == Decimal("450")


def test_a_service_this_catalogue_does_price_is_untouched(quoted):
    """The other control, and the one that keeps this from becoming a blanket
    refusal. Only services that DECLARE somebody else prices them are affected;
    ordinary catalogue work still bills at the catalogue rate even with the ref
    in hand and an estimate on file."""
    priced_here = [c for c in services() if not service(c).priced_by]
    assert priced_here, "every service is priced elsewhere; this proves nothing"

    for code in priced_here:
        invoice = Invoice(invoice_id="draft", client_id=CLIENT, tax_year=YEAR)
        invoice.add(code, quantity=2, engagement_ref=REF)
        assert invoice.lines[0].standard_rate == service(code).standard_rate, code


# ── it is reached from the screen ─────────────────────────────────────────────

def test_the_build_screen_passes_the_ref(quoted, monkeypatch, tmp_path):
    """A check the app never reaches is a check that does not exist.

    `_invoice_from` is what the Add line button goes through, and it had no
    idea which engagement the invoice belonged to -- which is the actual reason
    the engine could not see the contradiction.
    """
    from satc.app import billing_views

    monkeypatch.setattr(billing_views, "_engagement_ref_for", lambda c, y: REF)
    with pytest.raises(BillingError, match=r"\$350\.00"):
        billing_views._invoice_from(
            {"client_id": CLIENT, "tax_year": YEAR,
             "lines": [{"service_code": "return_1040", "quantity": "1"}]},
            invoice_id="draft")
