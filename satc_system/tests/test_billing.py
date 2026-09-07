"""Billing: value-based pricing, adjusted for means, shown honestly.

Money is correctness-critical, so every figure below is hand-checked rather
than round-tripped through the implementation.

The two properties that make this design what it is:

  * a discount is SHOWN, never a quietly smaller number — someone on a reduced
    rate can see what they were given;
  * a contingent fee is not something the engine declines, it is something the
    engine cannot express. Circular 230 §10.27.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from satc.billing import (
    BillingError,
    Invoice,
    billed_to_date,
    next_invoice_number,
    plan,
    plans,
    service,
    services,
)
from satc.config import ConfigError


def _invoice(plan_key="standard", basis="", **kw):
    return Invoice(invoice_id="2026-0001", client_id="C", tax_year=2025,
                   plan_key=plan_key, plan_basis=basis, **kw)


# --- the catalogue ------------------------------------------------------------

def test_the_catalogue_loads_with_rates():
    assert service("return_1040").standard_rate == Decimal("450")
    assert service("return_state").unit == "per_form"


def test_a_service_reads_as_a_person_would():
    """"Your federal individual tax return", not "Form 1040 prep"."""
    assert service("return_1040").label_for_client == "Your federal individual tax return"


def test_an_extension_is_free_on_purpose():
    """Charging for it would discourage the thing we would advise anyway."""
    assert service("extension").is_free


def test_a_contingent_fee_service_is_refused_at_load(tmp_path):
    """Circular 230 §10.27. Refused when the config loads, not at invoice time —
    by then it is already the practice's policy."""
    (tmp_path / "billing").mkdir()
    (tmp_path / "billing" / "services.yaml").write_text(
        "services:\n"
        "  - code: bad\n    name: 'Refund share'\n"
        "    description: 'A percent of refund, taken as our fee'\n"
        "    unit: fixed\n    standard_rate: 0\n", encoding="utf-8")
    (tmp_path / "billing" / "rate_plans.yaml").write_text(
        "plans:\n  - key: standard\n    discount_pct: 0\n", encoding="utf-8")
    from satc.billing.catalogue import load_services

    with pytest.raises(ConfigError, match="CONTINGENT FEE"):
        load_services(tmp_path)


def test_a_plan_cannot_be_a_surcharge_or_pay_the_client(tmp_path):
    (tmp_path / "billing").mkdir()
    (tmp_path / "billing" / "rate_plans.yaml").write_text(
        "plans:\n  - key: bad\n    discount_pct: 140\n", encoding="utf-8")
    from satc.billing.catalogue import load_plans

    with pytest.raises(ConfigError, match="between"):
        load_plans(tmp_path)


# --- the arithmetic, hand-checked ---------------------------------------------

def test_a_full_rate_invoice_totals_the_lines():
    inv = _invoice()
    inv.add("return_1040")            # 450
    inv.add("return_state", quantity=2)   # 95 x 2 = 190
    assert inv.standard_total == Decimal("640.00")
    assert inv.discount_total == Decimal("0.00")
    assert inv.total == Decimal("640.00")


def test_a_household_rate_takes_25_percent_off():
    inv = _invoice("household", "W-2 household, single income")
    inv.add("return_1040")            # 450
    inv.add("schedule_e_rental", quantity=2)   # 185 x 2 = 370
    assert inv.standard_total == Decimal("820.00")
    assert inv.discount_total == Decimal("205.00")
    assert inv.total == Decimal("615.00")


def test_hardship_takes_60_percent_off():
    inv = _invoice("hardship", "Job loss in March")
    inv.add("return_1040")
    assert inv.total == Decimal("180.00")     # 450 - 60%


def test_pro_bono_charges_nothing_but_still_itemises_the_value():
    """A zero with no breakdown teaches the client nothing about what they got."""
    inv = _invoice("pro_bono", "Volunteer referral; no ability to pay")
    inv.add("return_1040")
    inv.add("schedule_c")
    assert inv.total == Decimal("0.00")
    assert inv.standard_total == Decimal("725.00")
    assert "725.00" in inv.summary_block()


def test_money_is_never_a_float():
    inv = _invoice("household", "basis")
    inv.add("planning_session", quantity="1.5")     # 200 x 1.5 = 300
    assert inv.standard_total == Decimal("300.00")
    assert isinstance(inv.total, Decimal)


def test_rounding_is_half_up_to_the_cent():
    inv = _invoice("household", "basis")
    inv.add("return_1040", rate_override=Decimal("333.33"),
            note="Agreed at signing")
    assert inv.discount_total == Decimal("83.33")     # 25% of 333.33 = 83.3325
    assert inv.total == Decimal("250.00")


# --- the discount is shown, not hidden ----------------------------------------

def test_the_invoice_states_full_value_then_the_reduction():
    inv = _invoice("household", "basis")
    inv.add("return_1040")
    block = inv.summary_block()
    assert "Full value of work" in block
    assert "Household rate applied" in block
    assert "25%" in block
    assert "-112.50" in block
    assert "TOTAL DUE" in block


def test_a_full_rate_invoice_shows_no_discount_theatre():
    """Nobody needs to be told they got 0% off."""
    inv = _invoice()
    inv.add("return_1040")
    block = inv.summary_block()
    assert "Full value of work" not in block
    assert "TOTAL DUE" in block


def test_the_client_sentence_names_the_reduction():
    inv = _invoice("fixed_income", "Retired, social security and a small pension")
    inv.add("return_1040")
    sentence = inv.client_sentence()
    assert "$450.00" in sentence          # what it was worth
    assert "$270.00" in sentence          # what they pay
    assert "fixed income" in sentence.lower()


def test_a_no_charge_invoice_says_so_and_still_shows_the_value():
    inv = _invoice("pro_bono", "basis")
    inv.add("return_1040")
    assert "no charge" in inv.client_sentence().lower()
    assert "$450.00" in inv.client_sentence()


# --- the refusals -------------------------------------------------------------

def test_a_reduced_plan_cannot_be_issued_without_a_recorded_reason():
    """A sliding scale with no basis is improvisation — and improvisation is
    what looks arbitrary when two clients compare notes."""
    inv = _invoice("hardship")           # no basis
    inv.add("return_1040")
    with pytest.raises(BillingError, match="needs a recorded reason"):
        inv.issue(on=date(2026, 4, 20))


def test_the_standard_plan_needs_no_basis():
    inv = _invoice()
    inv.add("return_1040")
    inv.issue(on=date(2026, 4, 20))
    assert inv.is_issued


def test_an_empty_invoice_cannot_be_issued():
    """Billing someone for nothing is a worse mistake than forgetting to bill."""
    with pytest.raises(BillingError, match="no lines"):
        _invoice().issue(on=date(2026, 4, 20))


def test_an_issued_invoice_cannot_be_edited():
    inv = _invoice()
    inv.add("return_1040")
    inv.issue(on=date(2026, 4, 20))
    with pytest.raises(BillingError, match="cannot be changed"):
        inv.add("schedule_c")


def test_a_fixed_price_service_refuses_a_quantity():
    inv = _invoice()
    with pytest.raises(BillingError, match="fixed-price"):
        inv.add("return_1040", quantity=3)


def test_a_rate_override_changes_the_VALUE_not_the_discount():
    """Shaving the rate to give someone a quiet discount would hide the exact
    thing this invoice exists to show."""
    inv = _invoice("household", "basis")
    inv.add("schedule_c", rate_override=Decimal("400"))
    assert inv.standard_total == Decimal("400.00")
    assert inv.discount_total == Decimal("100.00")   # still 25%, on the new value


def test_there_is_nowhere_to_put_a_refund_amount():
    """The §10.27 guarantee is STRUCTURAL: a line is service x quantity,
    discounted by a percentage, with no access to the return's outcome."""
    from satc.billing.invoice import InvoiceLine

    fields = set(InvoiceLine.__dataclass_fields__) | set(Invoice.__dataclass_fields__)
    for forbidden in ("refund", "refund_amount", "contingent", "percentage_of_refund"):
        assert forbidden not in fields


# --- piecemeal ----------------------------------------------------------------

def test_invoice_numbers_are_sequential_within_a_year():
    existing = [_invoice(), Invoice(invoice_id="2026-0002", client_id="X", tax_year=2025)]
    assert next_invoice_number(existing, year=2026) == "2026-0003"
    assert next_invoice_number(existing, year=2027) == "2027-0001"


def test_numbering_survives_a_gap_without_reusing_one():
    existing = [Invoice(invoice_id="2026-0007", client_id="X", tax_year=2025)]
    assert next_invoice_number(existing, year=2026) == "2026-0008"


def test_billed_to_date_answers_what_they_have_already_been_charged():
    """Piecemeal billing means several invoices across one engagement."""
    first = _invoice("household", "basis")
    first.add("return_1040")
    first.issue(on=date(2026, 3, 1))
    first.paid_on = date(2026, 3, 15)

    second = Invoice(invoice_id="2026-0002", client_id="C", tax_year=2025,
                     plan_key="household", plan_basis="basis")
    second.add("schedule_c")
    second.issue(on=date(2026, 4, 1))

    running = billed_to_date([first, second], client_id="C", tax_year=2025)
    assert running["invoices"] == 2
    assert running["standard_value"] == Decimal("725.00")
    assert running["charged"] == Decimal("543.75")
    assert running["paid"] == Decimal("337.50")
    assert running["outstanding"] == Decimal("206.25")


def test_an_unissued_invoice_is_not_counted_as_billed():
    draft = _invoice()
    draft.add("return_1040")
    assert billed_to_date([draft], client_id="C", tax_year=2025)["charged"] == 0


def test_overdue_needs_an_issued_unpaid_invoice():
    inv = _invoice()
    inv.add("return_1040")
    inv.issue(on=date(2026, 3, 1), due_in_days=30)
    assert inv.is_overdue(date(2026, 4, 15))
    assert not inv.is_overdue(date(2026, 3, 15))
    inv.paid_on = date(2026, 4, 1)
    assert not inv.is_overdue(date(2026, 4, 15))


# --- persistence --------------------------------------------------------------

def test_an_invoice_survives_a_round_trip_with_its_basis():
    import tempfile

    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        inv = _invoice("hardship", "Job loss in March")
        inv.add("return_1040")
        inv.add("schedule_c", note="Two businesses merged into one")
        inv.issue(on=date(2026, 4, 20))
        store.save_invoices([inv])

        back = store.load_invoices("C")[0]
        assert back.plan_basis == "Job loss in March"
        assert back.standard_total == Decimal("725.00")
        assert back.total == Decimal("290.00")
        assert back.lines[1].note == "Two businesses merged into one"


def test_invoices_are_removed_with_their_client():
    import tempfile

    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        inv = _invoice()
        inv.add("return_1040")
        store.save_invoices([inv])
        store.delete_client("C")
        assert store.load_invoices("C") == []


# --- the covering email fills itself from the invoice -------------------------

def test_the_invoice_cover_email_arrives_finished():
    """End to end: the invoice supplies its own number, breakdown and sentence,
    so the owner never retypes a figure that already exists."""
    from satc.comms import build_context, library, render
    from satc.obligations.policy import policy

    lib = library()
    inv = Invoice(invoice_id="2026-0004", client_id="C", tax_year=2025,
                  plan_key="household", plan_basis="W-2 household")
    inv.add("return_1040")
    inv.add("return_state", quantity=2)
    inv.issue(on=date(2026, 4, 20))

    values = build_context(client_id="C", client_name="Jordan Rivera", tax_year=2025,
                           invoice=inv, standing_text=policy().standing_text,
                           firm_values=lib.firm_values())
    draft = render(lib.template("invoice_cover"), values, library=lib)

    assert draft.is_complete, f"unfilled: {draft.unfilled}"
    assert "2026-0004" in draft.subject
    assert "Your federal individual tax return" in draft.body
    assert "Household rate applied" in draft.body     # the discount is SHOWN
    assert "640.00" in draft.body                     # full value
    assert "480.00" in draft.body                     # what they pay


def test_without_an_invoice_the_number_stays_visibly_blank():
    """The guarantee that did not change: a fact nothing supplies is marked,
    never guessed. An invoice number is not something a model may invent."""
    from satc.comms import build_context, library, render

    lib = library()
    values = build_context(client_id="C", client_name="Jordan Rivera", tax_year=2025,
                           firm_values=lib.firm_values())
    draft = render(lib.template("invoice_cover"), values, library=lib)
    assert "invoice_number" in draft.unfilled
    # It lives in the SUBJECT now, since the breakdown carries the body.
    assert "[[ Invoice number: fill in ]]" in draft.subject
    assert "[[ Invoice breakdown: fill in ]]" in draft.body


# --- a per-line price is a discount by another route --------------------------
#
# These live here, on the ENGINE, rather than on the screen. A guard in the view
# only covers the path the view takes — and the adversarial review found exactly
# that: a draft restored from a session issued a 60% cut with nothing recorded,
# because the screen's check had already been passed and was never asked again.

def test_pricing_below_the_catalogue_with_no_reason_is_refused():
    inv = _invoice("standard", "")
    with pytest.raises(BillingError) as refusal:
        inv.add("return_1040", rate_override=Decimal("180"))
    assert "reduction" in str(refusal.value)
    assert "450.00" in str(refusal.value)      # names what it is actually worth
    assert inv.lines == []


def test_a_recorded_reason_lets_the_reduction_through():
    inv = _invoice("standard", "")
    inv.add("return_1040", rate_override=Decimal("180"), note="Priced at signing")
    assert inv.total == Decimal("180.00")


def test_the_reason_reaches_the_invoice_the_client_reads():
    """Not just the screen the owner typed it into — the printed copy and the
    covering email are built from summary_block()."""
    inv = _invoice("standard", "")
    inv.add("return_1040", rate_override=Decimal("180"), note="Priced at signing")
    assert "Priced at signing" in inv.summary_block()


def test_pricing_above_the_catalogue_needs_no_defence():
    """Guards against over-fixing: work genuinely worth more is not a discount."""
    inv = _invoice("standard", "")
    inv.add("schedule_c", rate_override=Decimal("400"))
    assert inv.total == Decimal("400.00")


def test_a_negative_price_is_refused():
    inv = _invoice("standard", "")
    with pytest.raises(BillingError) as refusal:
        inv.add("schedule_c", rate_override=Decimal("-500"), note="goodwill")
    assert "credit note" in str(refusal.value)


@pytest.mark.parametrize("poison", ["Infinity", "-Infinity", "NaN", "sNaN"])
def test_a_price_that_is_not_a_number_is_refused(poison):
    """Decimal() accepts all of these, and every guard written as a comparison
    silently passes NaN."""
    inv = _invoice("standard", "")
    with pytest.raises(BillingError):
        inv.add("return_1040", rate_override=Decimal(poison), note="whatever")


@pytest.mark.parametrize("poison", ["NaN", "Infinity"])
def test_a_quantity_that_is_not_a_number_is_refused(poison):
    inv = _invoice("standard", "")
    with pytest.raises(BillingError) as refusal:
        inv.add("return_state", quantity=Decimal(poison))
    assert "not a quantity" in str(refusal.value)


def test_the_engine_refuses_even_when_the_screen_already_said_yes():
    """Mutation check for the structural claim — principle 12.

    This is the shape the review actually exploited: a line assembled outside
    the form and handed straight to the engine. If _check_the_rate moved back
    into the view, this is the test that would start passing silently.
    """
    inv = _invoice("standard", "")
    with pytest.raises(BillingError):
        inv.add("return_1040", rate_override=Decimal("180"), note="   ")


# --- an issued invoice does not move when the price list does ----------------
#
# The rate was stamped onto the line, so a price rise could not reprice
# February. The DISCOUNT was not, and was read live on every render — so moving
# the household rate from 25% to 30% rewrote every household invoice ever
# issued. An invoice the client paid $337.50 for came back saying $270.00, on
# their copy, in the register, and in the covering email.

@pytest.fixture
def own_plans(tmp_path, monkeypatch):
    """A billing config this test owns, wired in where the engine reads from.

    A FIXTURE, not a helper, because the helper left the price cache warm and
    pointing at a temp directory that had been deleted. Under random test order
    that made an unrelated hot-reload test fail perhaps one run in ten — the
    worst kind of failure, since it looks like flakiness in the code rather than
    in the test that caused it.
    """
    import shutil

    from satc.billing import catalogue

    shutil.copytree("configs", tmp_path / "configs")
    monkeypatch.setattr(catalogue, "billing_dir",
                        lambda *a, **k: tmp_path / "configs" / "billing")

    def write(text: str) -> None:
        (tmp_path / "configs" / "billing" / "rate_plans.yaml").write_text(
            text, encoding="utf-8")
        catalogue.forget_prices()

    yield write
    # Cleared on the way OUT as well as in: the next test must not inherit a
    # cache keyed on a directory that is about to stop existing.
    catalogue.forget_prices()


PLANS = """
meta:
  default_plan: standard
plans:
  - key: standard
    name: "Standard"
    discount_pct: 0
  - key: household
    name: "Household rate"
    discount_pct: {pct}
    requires_basis: true
    client_label: "Household rate applied"
"""


def test_changing_a_discount_does_not_reprice_an_issued_invoice(tmp_path, own_plans):
    from satc.billing import catalogue

    own_plans(PLANS.format(pct=25))

    inv = _invoice("household", "W-2 household")
    inv.add("return_1040")
    inv.issue(on=date(2026, 3, 1))
    was = inv.total
    assert was == Decimal("337.50")

    own_plans(PLANS.format(pct=40))

    assert inv.total == was, "a config edit restated what a client already paid"
    assert inv.discount_total == Decimal("112.50")
    assert "$337.50" in inv.client_sentence()


def test_a_draft_still_follows_the_current_price_list(tmp_path, own_plans):
    """Guards against over-fixing. A draft has been agreed with nobody, so it
    SHOULD pick up a change."""
    from satc.billing import catalogue

    own_plans(PLANS.format(pct=25))

    inv = _invoice("household", "W-2 household")
    inv.add("return_1040")
    assert inv.total == Decimal("337.50")

    own_plans(PLANS.format(pct=40))
    assert inv.total == Decimal("270.00")


def test_an_issued_invoice_survives_its_plan_being_deleted(tmp_path, own_plans):
    """It stopped needing the catalogue the moment it was fixed. History must
    always load."""
    from satc.billing import catalogue

    own_plans(PLANS.format(pct=25))

    inv = _invoice("household", "W-2 household")
    inv.add("return_1040")
    inv.issue(on=date(2026, 3, 1))

    (tmp_path / "configs" / "billing" / "rate_plans.yaml").write_text(
        "meta:\n  default_plan: standard\nplans:\n  - key: standard\n"
        "    name: Standard\n    discount_pct: 0\n", encoding="utf-8")
    catalogue.forget_prices()

    assert inv.total == Decimal("337.50")
    assert "Household rate applied" in inv.summary_block()


def test_the_stamped_plan_is_what_makes_it_hold(tmp_path, own_plans):
    """Mutation check — principle 12. If issue() stopped stamping, rate_plan
    would fall back to the live catalogue and the first test above would fail;
    this asserts the stamp itself so the reason is visible."""
    from satc.billing import catalogue

    own_plans(PLANS.format(pct=25))

    inv = _invoice("household", "W-2 household")
    inv.add("return_1040")
    assert not inv.is_priced, "a draft carries no stamp"
    inv.issue(on=date(2026, 3, 1))
    assert inv.is_priced
    assert inv.plan_discount_pct == Decimal(25)
    assert inv.plan_client_label == "Household rate applied"
