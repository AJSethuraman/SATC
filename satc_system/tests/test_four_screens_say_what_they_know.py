"""Four screens that knew something and did not say it.

All four from the walk of 5 September 2026. Grouped because they are one shape:
the fact was already computed, already correct, and simply not on the page.

D22 · AN OVERPAYMENT WAS ON THE CLIENT'S COPY AND NOT ON THE FIRM'S SCREENS.
600.00 arrived against a 180.00 bill. `/today` raised it by name, and the
client's printed invoice said it in green. `/invoices/<id>` showed
`Still outstanding 0.00` -- `owed` is floored at zero, so a credit renders as
the same figure a bill paid to the penny shows -- and `/payments` listed both
amounts, attributed, with nothing saying they exceed what was billed.

Worth being exact about what was already right, because I got this wrong twice
while walking it: the Money in panel on the same invoice page ALREADY carried a
loud flag, and `/today` already named the credit and even said "the invoice is
settled, so nothing else here mentions it". What was missing is the summary line
at the top of the invoice -- the one somebody reads first -- and the payments
list. A summary that contradicts the panel underneath it is worse than either.

D23 · THE PAYMENT SCREEN POINTED AT A RETIRED PRODUCT. "Collection lives in
Invoicer" -- and the firm retired Invoicer by its own docket decision: *"the
firm takes Square; Invoicer was Stripe end to end."* The division of duties the
sentence describes never changed; only the thing on the far side of it did,
which is exactly how a stale name survives a decision.

D15 · THE TILE COUNTED THREE TASKS AND THE PANEL LISTED NONE. "0/3 Tasks
complete" three inches above "No internal tasks for this checklist". Both true
-- all three are the CLIENT's -- but the tile never said which side of the work
it counted, so the only available reading was that three things exist and none
is listed.

D17 · A CLIENT WHO SAID "NO CRYPTO" WAS ASKED FOR CRYPTO EXPORTS. One request
template carried `brokerageActivity OR digitalAssets` and named both in its
text. The first thing that client reads from the firm asked for something they
had just said they do not have, which is how somebody decides the questionnaire
was not read. It is also the exact shape the plan screen warns about -- "a
request typed as a BUCKET rather than as the form the rule names".
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.billing.invoice import Invoice
from satc.billing.payment import Payment, Method, MatchBasis
from satc.persistence import SATCStore

CLIENT = "SATC-001000"
YEAR = 2025


@pytest.fixture()
def state(tmp_path):
    return AppState(store=SATCStore(tmp_path / "store"))


def _overpaid(state):
    """A 180.00 invoice with 600.00 recorded against it."""
    invoice = Invoice(invoice_id="2026-0001", client_id=CLIENT, tax_year=YEAR)
    invoice.add("planning_session", quantity=Decimal("0.9"))   # 200/hr -> 180.00
    invoice.issue(on=date(2026, 9, 5), due_in_days=30)
    state.store.save_invoices([invoice])
    state.store.save_payments([
        Payment(client_id=CLIENT, amount=Decimal("100.00"),
                received_on=date(2026, 9, 5), method=Method.CHECK,
                invoice_id="2026-0001", basis=MatchBasis.REFERENCE, sequence=1),
        Payment(client_id=CLIENT, amount=Decimal("500.00"),
                received_on=date(2026, 9, 5), method=Method.CHECK,
                invoice_id="2026-0001", basis=MatchBasis.REFERENCE, sequence=2),
    ])
    state.reload()
    return invoice


def _page(state, monkeypatch, path):
    monkeypatch.setattr("satc.app.server.STATE", state)
    monkeypatch.setattr("satc.app.billing_views.STATE", state)
    return create_app().test_client().get(path).get_data(as_text=True)


# ── D22 ───────────────────────────────────────────────────────────────────────

def test_the_bill_really_is_overpaid(state):
    """The denominator. Without a genuine credit the assertions below are empty."""
    invoice = _overpaid(state)
    assert invoice.total == Decimal("180.00")


def test_the_invoice_summary_does_not_read_as_a_settled_bill(state, monkeypatch):
    """THE DEFECT. `owed` is floored, so a credit rendered as a clean 0.00."""
    _overpaid(state)
    body = _page(state, monkeypatch, "/invoices/2026-0001")
    assert "420.00 over" in body, (
        "the summary line still shows 0.00 outstanding with no mention of the credit")
    assert "Not a settled bill" in body


def test_the_loud_panel_underneath_is_still_there(state, monkeypatch):
    """The control. That panel was already right, and this must not replace it."""
    _overpaid(state)
    body = _page(state, monkeypatch, "/invoices/2026-0001")
    assert "more than\n      was due" in body or "more than" in body


def test_the_payments_list_says_the_money_exceeds_the_bill(state, monkeypatch):
    _overpaid(state)
    body = _page(state, monkeypatch, "/payments")
    assert "420.00 over" in body, "both payments listed with nothing about the excess"
    assert "180.00 billed" in body


def test_a_bill_paid_exactly_says_nothing_of_the_kind(state, monkeypatch):
    """The control. A credit note on a settled bill is its own wrong answer."""
    invoice = Invoice(invoice_id="2026-0002", client_id=CLIENT, tax_year=YEAR)
    invoice.add("planning_session", quantity=Decimal("0.9"))
    invoice.issue(on=date(2026, 9, 5), due_in_days=30)
    state.store.save_invoices([invoice])
    state.store.save_payments([
        Payment(client_id=CLIENT, amount=Decimal("180.00"),
                received_on=date(2026, 9, 5), method=Method.CHECK,
                invoice_id="2026-0002", basis=MatchBasis.REFERENCE)])
    state.reload()

    body = _page(state, monkeypatch, "/invoices/2026-0002")
    # The exact phrases the fix adds, not a bare "over" -- which matches
    # "covering email" and "overdue" and made this fail against correct code.
    assert "Not a settled bill" not in body
    assert " over." not in body
    assert "0.00" in body, "the settled bill stopped saying it is settled"


# ── D23 ───────────────────────────────────────────────────────────────────────

def test_no_screen_sends_the_reader_to_the_retired_product(state, monkeypatch):
    """The firm retired Invoicer: "the firm takes Square; Invoicer was Stripe
    end to end"."""
    _overpaid(state)
    body = _page(state, monkeypatch, "/invoices/2026-0001")
    visible = body.split("<!--")[0] if "<!--" in body else body
    assert "Invoicer" not in visible


def test_it_names_what_collection_actually_is(state, monkeypatch):
    """Deleting the name and saying nothing would leave the reader worse off."""
    _overpaid(state)
    body = _page(state, monkeypatch, "/invoices/2026-0001")
    assert "Square" in body


def test_the_division_of_duties_is_kept(state, monkeypatch):
    """What the sentence was FOR. SATC records money; it does not take it."""
    _overpaid(state)
    body = _page(state, monkeypatch, "/invoices/2026-0001")
    assert "does not take it" in body
    assert "identity vault" in body


# ── D17 ───────────────────────────────────────────────────────────────────────

def _requests_for(answers):
    from satc.intake.fanout import fan_out
    from satc.intake.workflows import load_workflow

    plan = fan_out(load_workflow("personal_1040_core"), answers,
                   client_id=CLIENT, tax_year=YEAR, today=date(2026, 2, 1))
    return [r.request_text for r in plan.requests]


def test_a_client_who_said_no_crypto_is_not_asked_for_crypto():
    """THE DEFECT."""
    texts = " ".join(_requests_for({"brokerageActivity": "yes",
                                    "digitalAssets": "no"}))
    assert "brokerage" in texts.lower(), "the brokerage ask went missing entirely"
    assert "crypto" not in texts.lower(), (
        "a client who answered No to digital assets is asked for crypto exports")


def test_a_client_who_said_yes_to_crypto_is_asked_for_it():
    """The control. Splitting the bucket must not lose the ask."""
    texts = " ".join(_requests_for({"digitalAssets": "yes"}))
    assert "crypto" in texts.lower()


def test_both_answers_produce_both_asks_separately():
    """Two answers, two asks -- so each closes on its own arrival rather than
    one bundle closing on whichever document turns up first."""
    texts = _requests_for({"brokerageActivity": "yes", "digitalAssets": "yes"})
    joined = " ".join(texts).lower()
    assert "brokerage" in joined and "crypto" in joined
    assert sum(1 for t in texts if "brokerage" in t.lower() or "crypto" in t.lower()) == 2


def test_neither_answer_produces_neither_ask():
    texts = " ".join(_requests_for({"brokerageActivity": "no", "digitalAssets": "no"}))
    assert "brokerage" not in texts.lower() and "crypto" not in texts.lower()


# ── D15 ───────────────────────────────────────────────────────────────────────

def _an_engagement(state, answers):
    """A stored engagement, through the real producer."""
    from satc.intake.service import create_engagement_from_intake

    plan = create_engagement_from_intake(
        state.store, client_id=CLIENT, workflow_key="personal_1040_core",
        tax_year=YEAR, answers=answers, today=date(2026, 2, 1))
    state.reload()
    return plan.job


def test_the_engagement_really_has_client_tasks_and_no_internal_ones(state):
    """The denominator, and the precondition the walk actually hit."""
    job = _an_engagement(state, {"brokerageActivity": "yes"})
    client_side = [t for t in job.tasks if t.audience == "client"]
    internal = [t for t in job.tasks if t.audience != "client"]
    assert client_side, "no client tasks; the disagreement cannot arise"
    assert not internal, "this engagement has internal tasks; wrong precondition"


def test_the_tile_says_which_side_of_the_work_it_counted(state, monkeypatch):
    """THE DEFECT. "0/3 Tasks complete" over "No internal tasks", with nothing
    saying the three were the client's."""
    job = _an_engagement(state, {"brokerageActivity": "yes"})
    n = len([t for t in job.tasks if t.audience == "client"])

    monkeypatch.setattr("satc.app.server.STATE", state)
    monkeypatch.setattr("satc.app.intake_views.STATE", state)
    body = create_app().test_client().get(
        f"/engagements/{job.job_id}").get_data(as_text=True)

    assert f"{n} theirs, 0 ours" in body, (
        "the tile still counts three things without saying whose they are")


def test_the_empty_panel_points_at_where_they_are(state, monkeypatch):
    """The other half. "No internal tasks" alone leaves the reader to reconcile
    it with a count of three on their own."""
    job = _an_engagement(state, {"brokerageActivity": "yes"})
    monkeypatch.setattr("satc.app.server.STATE", state)
    monkeypatch.setattr("satc.app.intake_views.STATE", state)
    body = create_app().test_client().get(
        f"/engagements/{job.job_id}").get_data(as_text=True)

    assert "No internal tasks" in body
    assert "are the client's, and they" in body
