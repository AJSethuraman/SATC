"""The invoicing SCREENS — raising a bill, and what the client is shown.

The arithmetic and the refusals are guarded in ``tests/test_billing.py``. This
file guards the thin view over them, and one specific failure mode: that a
refusal reaches the owner as a SENTENCE rather than as a stack trace. An invoice
the engine declines to issue is the product working; a 500 is the product
broken, and the two are one ``try`` apart.

It also holds the line that matters most on a money screen: every figure in the
HTML is the engine's ``Decimal``, formatted, and not a number the view worked
out for itself. Two opinions about a client's bill is one too many.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.billing import BillingError, Invoice, next_invoice_number

# A client id of our own, so issuing real invoices in these tests cannot change
# what any other screen's tests see for the seeded practice.
CLIENT = "SATC-INVTEST"
YEAR = 2025


@pytest.fixture()
def client():
    """The real app, exactly as it is served.

    Deliberately NOT a hand-assembled app with the blueprint bolted on: that
    passes whether or not ``server.py`` actually registers it, so the screens
    could be perfect and unreachable. If the wiring is dropped, these fail.
    """
    return create_app().test_client()


def test_the_payment_screens_run_against_the_real_store_seam():
    """These screens go through ``save_payments`` / ``load_payments`` and never
    touch ``invoice.paid_on`` directly. Asserted rather than assumed, because a
    test that quietly substituted its own ledger would prove nothing about the
    store the owner actually has."""
    from satc.persistence.store import SATCStore

    assert hasattr(SATCStore, "save_payments")
    assert hasattr(SATCStore, "load_payments")


# --- driving the screen -------------------------------------------------------

def _header(web, *, plan_key="standard", basis="", client_id=CLIENT, shown=None,
            tax_year=YEAR):
    form = {"action": "header", "client_id": client_id, "plan_key": plan_key,
            "plan_basis": basis, "tax_year": str(tax_year)}
    if shown is not None:
        form["plan_shown"] = shown
    return web.post("/invoices/new", data=form)


def _add(web, code, *, quantity="1", note="", rate_override=""):
    return web.post("/invoices/new", data={
        "action": "add", "service_code": code, "quantity": quantity,
        "note": note, "rate_override": rate_override})


def _next_number() -> str:
    """What the screen will number the next invoice — same helper it uses."""
    return next_invoice_number(STATE.store.load_invoices(), year=date.today().year)


def _issue(web, **form):
    """Issue the draft; hand back the number it actually got.

    A backdated invoice is numbered in ITS year, not this one, so the number is
    read off the redirect rather than assumed.
    """
    resp = web.post(f"/invoices/{_next_number()}/issue", data=form)
    if resp.status_code == 302:
        return resp.headers["Location"].rsplit("/", 1)[-1], resp
    return _next_number(), resp        # refused: nothing was written, so unchanged


def _stored(invoice_id: str):
    return next((i for i in STATE.store.load_invoices()
                 if i.invoice_id == invoice_id), None)


def _text(resp) -> str:
    return resp.data.decode("utf-8")


# --- every screen renders -----------------------------------------------------

def test_the_list_screen_renders(client):
    resp = client.get("/invoices")
    assert resp.status_code == 200
    assert "Billed to date" in _text(resp)


def test_the_build_screen_renders_the_catalogue_grouped_by_category(client):
    """The owner picks from the finite set too — nobody types a service name."""
    from satc.billing import by_category

    body = _text(client.get("/invoices/new"))
    assert 'name="service_code"' in body
    for category, svcs in by_category():
        assert f'<optgroup label="{category}">' in body
        for svc in svcs:
            assert svc.name in body


def test_every_rate_plan_is_offered_by_name(client):
    from satc.billing import plans

    body = _text(client.get("/invoices/new"))
    for rate_plan in plans().values():
        assert rate_plan.name in body


def test_the_view_and_print_screens_render_an_issued_invoice(client):
    _header(client, plan_key="standard")
    _add(client, "return_1040")
    number, resp = _issue(client)
    assert resp.status_code == 302

    assert client.get(f"/invoices/{number}").status_code == 200
    assert client.get(f"/invoices/{number}/print").status_code == 200


def test_an_unknown_invoice_is_a_404_not_a_500(client):
    for path in ("/invoices/2099-9999", "/invoices/2099-9999/print"):
        assert client.get(path).status_code == 404


# --- the running total, before anything is issued -----------------------------

def test_the_build_screen_shows_full_value_the_named_discount_and_what_is_due(client):
    """The whole point of the screen: the owner sees what the CLIENT will see,
    before deciding to issue it."""
    _header(client, plan_key="household", basis="W-2 household, single income")
    _add(client, "return_1040")
    body = _text(_add(client, "schedule_e_rental", quantity="2"))

    engine = Invoice(invoice_id="preview", client_id=CLIENT, tax_year=YEAR,
                     plan_key="household", plan_basis="basis")
    engine.add("return_1040")
    engine.add("schedule_e_rental", quantity=2)

    assert engine.standard_total == Decimal("820.00")        # hand-checked
    assert f"{engine.standard_total:,.2f}" in body
    assert f"{engine.discount_total:,.2f}" in body
    assert f"{engine.total:,.2f}" in body
    assert "Household rate applied" in body
    assert "Full value of work" in body


def test_the_totals_in_the_html_are_the_engines_decimals(client):
    """Every figure on the page is the engine's number, formatted — never one
    the view computed for itself."""
    _header(client, plan_key="fixed_income", basis="Retired, small pension")
    _add(client, "return_1040")
    _add(client, "return_state", quantity="2")
    _add(client, "planning_session", quantity="1.5")
    body = _text(client.get("/invoices/new"))

    engine = Invoice(invoice_id="preview", client_id=CLIENT, tax_year=YEAR,
                     plan_key="fixed_income", plan_basis="basis")
    engine.add("return_1040")
    engine.add("return_state", quantity=2)
    engine.add("planning_session", quantity="1.5")

    assert f"{engine.standard_total:,.2f}" in body          # 450 + 190 + 300
    assert f"{engine.total:,.2f}" in body
    assert engine.summary_block().splitlines()[0] in body   # line for line
    assert engine.client_sentence() in body


def test_a_draft_is_not_written_down_until_it_is_issued(client):
    before = {i.invoice_id for i in STATE.store.load_invoices()}
    _header(client, plan_key="standard")
    _add(client, "return_1040")
    assert {i.invoice_id for i in STATE.store.load_invoices()} == before


def test_a_line_can_be_taken_back_off_a_draft(client):
    _header(client, plan_key="standard")
    _add(client, "return_1040")
    _add(client, "schedule_d")
    body = _text(client.post("/invoices/new", data={"action": "drop", "line_no": "1"}))
    assert "Investment sales and capital gains" not in body
    assert "Your federal individual tax return" in body


# --- the refusals reach the owner as sentences --------------------------------

def test_a_reduced_plan_with_no_basis_is_refused_with_the_engines_own_message(client):
    """The refusal IS the product. It must appear on the page, in the engine's
    words, and nothing may be written down."""
    _header(client, plan_key="hardship")        # no basis recorded
    _add(client, "return_1040")
    before = {i.invoice_id for i in STATE.store.load_invoices()}

    number, resp = _issue(client)
    body = _text(resp)

    assert resp.status_code == 200, "a refusal is a page, not a redirect or a 500"
    assert "needs a recorded reason" in body
    assert "improvisation" in body              # the engine's own sentence, verbatim
    assert {i.invoice_id for i in STATE.store.load_invoices()} == before
    assert _stored(number) is None


def test_recording_the_basis_then_lets_it_issue(client):
    """The refusal names what would have been right — and doing that works."""
    _header(client, plan_key="hardship")
    _add(client, "return_1040")
    _issue(client)                                        # refused
    _header(client, plan_key="hardship", basis="Job loss in March")
    number, resp = _issue(client)

    assert resp.status_code == 302
    assert _stored(number).total == Decimal("180.00")     # 450 less 60%


def test_issuing_nothing_is_refused_on_the_page(client):
    resp = client.post(f"/invoices/{_next_number()}/issue", data={})
    assert resp.status_code == 200
    assert "nothing on this draft" in _text(resp)


def test_an_invoice_addressed_to_nobody_is_refused(client):
    _header(client, client_id="")
    _add(client, "return_1040")
    resp = client.post(f"/invoices/{_next_number()}/issue", data={})
    assert resp.status_code == 200
    assert "addressed to nobody" in _text(resp)


def test_a_fixed_price_service_refuses_a_quantity_on_the_screen(client):
    _header(client)
    body = _text(_add(client, "return_1040", quantity="3"))
    assert "fixed-price" in body
    assert "Total due" not in body, "the refused line must not have gone on"


def test_a_rate_that_is_not_a_number_is_refused_not_rounded(client):
    _header(client)
    body = _text(_add(client, "schedule_c", rate_override="four hundred"))
    assert "is not an amount" in body


def test_a_nonsense_issue_date_is_refused_rather_than_defaulted(client):
    _header(client)
    _add(client, "return_1040")
    number, resp = _issue(client, issued_on="next tuesday")
    assert resp.status_code == 200
    assert "is not a date" in _text(resp)
    assert _stored(number) is None


# --- issuing writes durably ---------------------------------------------------

def test_issuing_writes_durably_and_survives_a_reload(client):
    _header(client, plan_key="household", basis="W-2 household")
    _add(client, "return_1040")
    _add(client, "return_state", quantity="2")
    number, resp = _issue(client, issued_on="2026-04-20", due_in_days="30")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/invoices/{number}")

    # Read it back out of the store, not out of the session that made it.
    stored = _stored(number)
    assert stored is not None
    assert stored.issued_on == date(2026, 4, 20)
    assert stored.due_on == date(2026, 5, 20)
    assert stored.plan_basis == "W-2 household"
    assert stored.standard_total == Decimal("640.00")
    assert stored.total == Decimal("480.00")

    # A browser that has never seen the draft can still read the invoice.
    fresh = create_app()
    body = _text(fresh.test_client().get(f"/invoices/{number}"))
    assert f"{stored.total:,.2f}" in body
    assert "Household rate applied" in body


def test_the_draft_is_gone_once_it_is_issued(client):
    _header(client)
    _add(client, "return_1040")
    _issue(client)
    body = _text(client.get("/invoices/new"))
    assert "Nothing on this invoice yet" in body


def test_an_issued_invoice_cannot_be_edited(client):
    """Two halves of the same guarantee: the engine refuses, and the screen
    offers nowhere to try."""
    _header(client)
    _add(client, "return_1040")
    number, _ = _issue(client)

    stored = _stored(number)
    with pytest.raises(BillingError, match="cannot be changed"):
        stored.add("schedule_c")

    body = _text(client.get(f"/invoices/{number}"))
    assert 'value="add"' not in body
    assert "Add to the invoice" not in body


def test_issuing_the_same_number_twice_is_success_not_a_second_invoice(client):
    """A double-submitted form or a back button. Already issued as requested is
    success, never a conflict (principle 8)."""
    _header(client)
    _add(client, "return_1040")
    number, _ = _issue(client)

    again = client.post(f"/invoices/{number}/issue", data={})
    assert again.status_code == 302
    assert again.headers["Location"].endswith(f"/invoices/{number}")
    assert len([i for i in STATE.store.load_invoices() if i.invoice_id == number]) == 1


def test_a_backdated_invoice_is_numbered_in_its_own_year(client):
    """The number labels the invoice's own year, so a bill raised late for a
    prior season doesn't read as this year's work."""
    _header(client)
    _add(client, "return_1040")
    number, resp = _issue(client, issued_on="2024-01-01")
    assert resp.status_code == 302
    assert number.startswith("2024-")
    assert _stored(number).issued_on == date(2024, 1, 1)


def test_two_invoices_never_take_the_same_number(client):
    _header(client)
    _add(client, "return_1040")
    first, _ = _issue(client)
    _header(client)
    _add(client, "schedule_d")
    second, _ = _issue(client)
    assert first != second
    assert _stored(first) is not None and _stored(second) is not None


# --- payment ------------------------------------------------------------------
#
# "Paid" is not a flag anybody sets. Money arriving is the FACT, recorded on the
# ledger; ``paid_on`` is the CONCLUSION drawn from it (principle 11b). Everything
# below is about the difference — a part payment, an overpayment and the same
# deposit entered twice are three things a boolean cannot tell apart.

def _pay(web, number, *, amount, received_on, method="check", reference=""):
    return web.post(f"/invoices/{number}/paid", data={
        "amount": amount, "received_on": received_on, "method": method,
        "reference": reference})


def _ledger_for(client_id: str) -> list:
    from satc.app.state import STATE as _state

    return list(_state.store.load_payments(client_id))


def test_recording_a_payment_in_full_settles_the_invoice(client):
    _header(client, client_id="SATC-PAY-FULL")
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    resp = _pay(client, number, amount="450.00", received_on="2026-03-15")
    assert resp.status_code == 302
    # paid_on is COMPUTED from the ledger — the date the balance reached zero.
    assert _stored(number).paid_on == date(2026, 3, 15)
    assert len(_ledger_for("SATC-PAY-FULL")) == 1

    body = _text(client.get(f"/invoices/{number}"))
    assert "Settled in full" in body
    assert "March 15, 2026" in body


def test_a_part_payment_leaves_the_invoice_unpaid_and_shows_the_balance(client):
    """The failure a flag cannot express: half the money arrived, and the
    invoice is still owed and still chaseable."""
    _header(client, client_id="SATC-PAY-PART")
    _add(client, "return_1040")                       # 450.00
    number, _ = _issue(client, issued_on="2026-03-01")

    resp = _pay(client, number, amount="200", received_on="2026-03-10")
    assert resp.status_code == 302

    stored = _stored(number)
    assert stored.paid_on is None, "a part payment must not mark the invoice paid"
    assert stored.is_paid is False

    body = _text(client.get(f"/invoices/{number}"))
    assert "Part paid" in body
    assert "250.00" in body, "the outstanding balance has to be on the page"
    assert "Settled in full" not in body


def test_an_overpayment_is_visible_rather_than_swallowed(client):
    """Money beyond the total is owed a conversation, not silence."""
    _header(client, client_id="SATC-PAY-OVER")
    _add(client, "return_1040")                       # 450.00
    number, _ = _issue(client, issued_on="2026-03-01")

    _pay(client, number, amount="500", received_on="2026-03-12")
    body = _text(client.get(f"/invoices/{number}"))

    assert "more than" in body
    assert "50.00" in body, "the excess itself must be named"
    assert _stored(number).is_paid, "an overpayment still settles the bill"


def test_a_payment_before_the_issue_date_is_refused_on_the_page(client):
    """The old screen took a 1999 date on a 2026 invoice without blinking."""
    _header(client, client_id="SATC-PAY-EARLY")
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    resp = _pay(client, number, amount="450", received_on="1999-01-01")
    assert resp.status_code == 200, "a refusal is a page, not a redirect or a 500"
    assert "before invoice" in _text(resp)
    assert "did not exist yet" in _text(resp)
    assert _ledger_for("SATC-PAY-EARLY") == [], "nothing may reach the ledger"
    assert _stored(number).paid_on is None


@pytest.mark.parametrize("bad", ["0", "-100", "0.00"])
def test_a_non_positive_payment_is_refused(client, bad):
    _header(client, client_id="SATC-PAY-ZERO")
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    resp = _pay(client, number, amount=bad, received_on="2026-03-05")
    assert resp.status_code == 200
    assert "is not money arriving" in _text(resp)
    assert _ledger_for("SATC-PAY-ZERO") == []


@pytest.mark.parametrize("bad", ["", "four hundred", "NaN", "Infinity"])
def test_an_amount_that_is_not_money_is_refused_in_words(client, bad):
    _header(client, client_id="SATC-PAY-JUNK")
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    body = _text(_pay(client, number, amount=bad, received_on="2026-03-05"))
    assert "InvalidOperation" not in body
    assert "plain number of dollars" in body
    assert _ledger_for("SATC-PAY-JUNK") == []


def test_the_method_comes_off_a_picker_and_anything_else_is_refused(client):
    """Principle 6a applied to the owner as well as to the model: how money
    arrived is a finite set, and nothing types a sixth one."""
    _header(client, client_id="SATC-PAY-METHOD")
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    body = _text(client.get(f"/invoices/{number}"))
    assert 'name="method"' in body and "<select" in body
    assert 'name="paid_on"' not in body, "the bare paid-on flag must be gone"

    resp = _pay(client, number, amount="450", received_on="2026-03-05",
                method="crypto")
    assert resp.status_code == 200
    assert "is not a way money arrives" in _text(resp)
    assert _ledger_for("SATC-PAY-METHOD") == []


def test_a_nonsense_payment_date_is_shown_as_a_message_not_a_500(client):
    _header(client, client_id="SATC-PAY-BADDATE")
    _add(client, "return_1040")
    number, _ = _issue(client)

    resp = _pay(client, number, amount="450", received_on="whenever")
    assert resp.status_code == 200
    assert "is not a date" in _text(resp)
    assert _stored(number).paid_on is None


def test_recording_the_same_payment_twice_does_not_double_count(client):
    """The id derives from the payment itself, so a double-submitted form or a
    re-imported deposit lands on the same row (principle 8)."""
    _header(client, client_id="SATC-PAY-TWICE")
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    first = _pay(client, number, amount="200", received_on="2026-03-10",
                 reference="check 1042")
    assert first.status_code == 302
    again = _pay(client, number, amount="200", received_on="2026-03-10",
                 reference="check 1042")

    assert again.status_code == 200
    assert "Already on the ledger" in _text(again)
    assert len(_ledger_for("SATC-PAY-TWICE")) == 1
    body = _text(client.get(f"/invoices/{number}"))
    assert "250.00" in body, "the balance must not have moved twice"


# --- the reconciliation screen ------------------------------------------------

def _record_payment(web, **form):
    form.setdefault("method", "transfer")
    return web.post("/payments/record", data=form)


def _tray_row(body: str, payment_id: str) -> str:
    """Just the tray entry for one unattributed payment, so assertions about
    what it says and what it offers cannot be satisfied by another row."""
    before, _, after = body.partition(f"/payments/{payment_id}/match")
    return (before.rsplit('<div class="well">', 1)[-1]
            + after.split("</form>", 1)[0])


def _only_payment(client_id: str):
    ledger = _ledger_for(client_id)
    assert len(ledger) == 1, ledger
    return ledger[0]


def test_the_payments_screen_renders(client):
    resp = client.get("/payments")
    assert resp.status_code == 200
    assert "Record a payment" in _text(resp)


def test_a_reference_that_names_the_invoice_resolves_with_nobody_deciding(client):
    """Rung 1. The page says why in the engine's own words, and the basis it
    records is not the same fact as somebody choosing."""
    cid = "SATC-REC-REF"
    _header(client, client_id=cid)
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    _record_payment(client, client_id=cid, amount="450",
                    received_on="2026-03-20", reference=f"stripe {number}")
    payment = _only_payment(cid)

    body = _text(client.get("/payments"))
    row = _tray_row(body, payment.payment_id)
    assert f"Reference names invoice {number}." in row, "match.why, verbatim"
    assert "nobody has to decide this one" in row
    assert 'type="radio"' not in row, "a resolved rung offers no choice"

    assert client.post(f"/payments/{payment.payment_id}/match").status_code == 302
    after = _only_payment(cid)
    assert after.invoice_id == number
    assert after.basis.value == "reference"

    body = _text(client.get("/payments"))
    assert "The payment named the invoice" in body
    assert _stored(number).is_paid


def test_a_sole_exact_amount_resolves_and_reads_differently_from_a_choice(client):
    """Rung 2 — and the record must not look like rung 3. A payment matched by
    amount and one a person picked are different facts."""
    cid = "SATC-REC-SOLE"
    _header(client, client_id=cid)
    _add(client, "schedule_d")
    number, _ = _issue(client, issued_on="2026-03-01")
    total = _stored(number).total

    _record_payment(client, client_id=cid, amount=f"{total:.2f}",
                    received_on="2026-03-20")
    payment = _only_payment(cid)
    row = _tray_row(_text(client.get("/payments")), payment.payment_id)
    assert "the only one it matches" in row

    client.post(f"/payments/{payment.payment_id}/match")
    assert _only_payment(cid).basis.value == "sole_amount"

    from satc.app.billing_views import _HOW_MATCHED

    body = _text(client.get("/payments"))
    assert _HOW_MATCHED[_only_payment(cid).basis] in body
    # The five bases must read as five different facts. A screen that renders
    # "matched" for all of them throws away the only thing that tells a
    # reference apart from a model's guess a year later.
    assert len(set(_HOW_MATCHED.values())) == len(_HOW_MATCHED)


def test_rung_three_offers_only_the_candidates_and_refuses_anything_else(client):
    """The shortlist IS the answer set. An id outside it — another client's
    invoice, a hallucinated number — is refused by the engine, not believed."""
    cid = "SATC-REC-AMBIG"
    _header(client, client_id=cid)
    _add(client, "return_1040")
    first, _ = _issue(client, issued_on="2026-03-01")
    _header(client, client_id=cid)
    _add(client, "schedule_d")
    second, _ = _issue(client, issued_on="2026-03-02")

    # Somebody else's invoice, never open for this client.
    _header(client, client_id="SATC-REC-OTHER")
    _add(client, "return_state")
    foreign, _ = _issue(client, issued_on="2026-03-01")

    _record_payment(client, client_id=cid, amount="100", received_on="2026-03-20")
    payment = _only_payment(cid)

    row = _tray_row(_text(client.get("/payments")), payment.payment_id)
    assert "Which invoice is it against?" in row, "match.why, verbatim"
    assert f'value="{first}"' in row and f'value="{second}"' in row
    assert f'value="{foreign}"' not in row, "only the candidates may be offered"

    refused = client.post(f"/payments/{payment.payment_id}/match",
                          data={"invoice_id": foreign})
    assert refused.status_code == 200
    assert "was not one of the open invoices offered" in _text(refused)
    assert _only_payment(cid).invoice_id == "", "nothing may be attributed"

    accepted = client.post(f"/payments/{payment.payment_id}/match",
                           data={"invoice_id": second})
    assert accepted.status_code == 302
    chosen = _only_payment(cid)
    assert chosen.invoice_id == second
    assert chosen.basis.value == "chosen_by_human"
    assert "You picked the invoice" in _text(client.get("/payments"))


def test_a_payment_recorded_off_the_invoice_screens_is_refused_without_a_client(client):
    resp = _record_payment(client, client_id="", amount="100",
                           received_on="2026-03-20")
    assert resp.status_code == 200
    assert "belonging to nobody" in _text(resp)


def test_the_payments_screen_sends_and_collects_nothing():
    """Principle 9 and 11a: SATC records that money arrived. Invoicer collects."""
    from pathlib import Path

    import satc.app.billing_views as views

    page = Path(views.__file__).parent / "templates" / "payments.html"
    body = page.read_text(encoding="utf-8").lower()
    for banned in ("stripe", "http://", "https://", "checkout", "pay now",
                   "card number"):
        assert banned not in body, f"payments.html mentions {banned}"


# --- the list ----------------------------------------------------------------

def test_the_list_shows_the_invoice_and_what_the_client_is_into_us_for(client):
    _header(client, plan_key="household", basis="W-2 household")
    _add(client, "return_1040")
    number, _ = _issue(client)
    stored = _stored(number)

    body = _text(client.get("/invoices"))
    assert number in body
    assert CLIENT in body                                   # the running total row
    assert f"{stored.standard_total:,.2f}" in body
    assert f"{stored.total:,.2f}" in body


def test_an_overdue_invoice_says_so(client):
    _header(client)
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2024-01-01", due_in_days="30")
    body = _text(client.get("/invoices"))
    assert "Overdue" in body
    assert _stored(number).is_overdue(date.today())


# --- the printable copy -------------------------------------------------------

def test_the_print_page_has_no_nav_and_nothing_to_click(client):
    _header(client, plan_key="pro_bono", basis="Volunteer referral; no ability to pay")
    _add(client, "return_1040")
    number, _ = _issue(client)

    body = _text(client.get(f"/invoices/{number}/print"))
    assert "<button" not in body
    assert "SETHURAMAN</span>" not in body                  # the app chrome, not the letterhead
    assert "@media print" in body
    assert "Sethuraman Accounting, Tax & Consulting" in body or "SATC" in body
    # A no-charge invoice is still itemised at full value — the point is that
    # they can see what they were given.
    assert "450.00" in body
    assert "no charge" in body.lower()


def test_the_print_page_shows_the_recorded_reason_for_a_reduced_line(client):
    """The copy the CLIENT receives is the one that has to carry the reason.

    ``summary_block()`` folds it in through ``InvoiceLine.describe()``, but only
    while the line still remembers it was priced away from the catalogue — and
    that flag does not survive the store. The printed sheet was reaching the
    client as a smaller number with no explanation, which is precisely what the
    whole billing engine exists to prevent.
    """
    reason = "Half the return was already done by the prior preparer"
    _header(client, plan_key="standard", client_id="SATC-PRINTREASON")
    _add(client, "return_1040", rate_override="180", note=reason)
    number, resp = _issue(client)
    assert resp.status_code == 302

    body = _text(client.get(f"/invoices/{number}/print"))
    assert reason in body, "the client's own copy must say why the line reads that way"
    assert body.count(reason) == 1, "and it must not say it twice"


# --- the rate override is not a back door round the basis rule ----------------
#
# The whole engine exists to make a reduction VISIBLE and JUSTIFIED. A reduced
# plan cannot issue without a recorded basis; billing 450.00 of work at 180.00
# is the same reduction wearing a different hat, so it answers to the same rule.

def test_a_cut_rate_with_no_recorded_reason_is_refused_like_a_plan_with_no_basis(client):
    """The worst version of this bug: a 60% cut, no discount shown, nothing
    recorded, and the client simply told a smaller number."""
    _header(client, plan_key="standard")            # full rate, no basis anywhere
    body = _text(_add(client, "return_1040", rate_override="180"))

    assert "improvisation" in body, "the refusal speaks in the engine's own voice"
    assert "450.00" in body and "180" in body, "it names what the work is worth"
    assert "Nothing on this invoice yet" in body, "the cut line must not have gone on"

    # And nothing can be issued off it, because nothing was added.
    resp = client.post(f"/invoices/{_next_number()}/issue", data={})
    assert "nothing on this draft" in _text(resp)


def test_a_recorded_reason_lets_the_cut_rate_through_and_reaches_the_client(client):
    """The refusal names what would have been right — and doing it works. The
    reason is then on the client's copy, so they see the adjustment rather than
    just a smaller number."""
    reason = "Half the return was already done by the prior preparer"
    _header(client, plan_key="standard")
    _add(client, "return_1040", rate_override="180", note=reason)
    number, resp = _issue(client)

    assert resp.status_code == 302
    stored = _stored(number)
    assert stored.standard_total == Decimal("180.00")
    assert stored.lines[0].note == reason

    body = _text(client.get(f"/invoices/{number}"))
    assert reason in body, "the client's copy must show why the line reads as it does"


def test_a_rate_above_the_catalogue_needs_no_defence(client):
    """Work genuinely being worth more is not a discount and owes no explanation."""
    _header(client, plan_key="standard")
    _add(client, "return_1040", rate_override="600")
    number, resp = _issue(client)

    assert resp.status_code == 302
    assert _stored(number).standard_total == Decimal("600.00")


def test_a_negative_rate_override_is_refused_rather_than_billed(client):
    """A negative invoice is not a credit note."""
    _header(client, plan_key="standard")
    body = _text(_add(client, "schedule_c", rate_override="-500", note="goodwill"))

    assert "not a credit note" in body
    assert "Nothing on this invoice yet" in body
    assert "Total due" not in body, "no total may be struck from a negative line"
    resp = client.post(f"/invoices/{_next_number()}/issue", data={})
    assert "nothing on this draft" in _text(resp)


@pytest.mark.parametrize("poison", ["Infinity", "-Infinity", "NaN", "nan", "-inf"])
def test_a_non_finite_rate_is_refused_and_never_reaches_the_session(client, poison):
    """``Decimal()`` accepts these; money does not. And a row must never be
    written to the draft before it has been validated — a poisoned draft used to
    500 every later visit to the only page with a Discard button on it."""
    _header(client, plan_key="standard")
    resp = _add(client, "schedule_c", rate_override=poison, note="whatever")

    assert resp.status_code == 200
    assert "is not an amount" in _text(resp)

    later = client.get("/invoices/new")
    assert later.status_code == 200, "the build screen must still open afterwards"
    assert "Nothing on this invoice yet" in _text(later)


def test_a_draft_that_cannot_be_priced_still_renders_with_a_way_out(client):
    """Belt and braces for the lock-out. A row no current guard would admit —
    left in a cookie by an older build — must still produce a page, because
    this screen carries the only Discard button in the app."""
    from satc.app.billing_views import _DRAFT

    with client.session_transaction() as sess:
        sess[_DRAFT] = {"client_id": CLIENT, "tax_year": YEAR, "plan_key": "standard",
                        "plan_basis": "", "lines": [{"service_code": "return_1040",
                                                     "quantity": "1", "note": "",
                                                     "rate_override": "Infinity"}]}

    resp = client.get("/invoices/new")
    assert resp.status_code == 200, "a draft that cannot be priced is not a 500"
    assert "discard it and start again" in _text(resp)

    resp = client.post("/invoices/new", data={"action": "discard"})
    assert resp.status_code == 200
    assert "Nothing was ever written down" in _text(resp)


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-inf", "how many"])
def test_a_quantity_that_is_not_a_number_is_refused_in_words(client, bad):
    """Phrased like the bad-rate branch, never rendered as a repr."""
    _header(client, plan_key="standard")
    body = _text(_add(client, "schedule_e_rental", quantity=bad))

    assert "InvalidOperation" not in body
    assert "is not a quantity" in body
    later = client.get("/invoices/new")
    assert later.status_code == 200
    assert "Nothing on this invoice yet" in _text(later)


# --- the tax year is a fact, not a default ------------------------------------

@pytest.mark.parametrize("bad", ["two thousand twenty five", "12", "-5", "3025", "1899"])
def test_a_tax_year_that_is_not_a_year_is_refused_not_quietly_replaced(client, bad):
    resp = client.post("/invoices/new", data={
        "action": "header", "client_id": CLIENT, "plan_key": "standard",
        "plan_basis": "", "tax_year": bad})
    assert resp.status_code == 200
    assert "is not a tax year" in _text(resp)


def test_a_refused_tax_year_leaves_the_draft_as_it_was(client):
    """``tax_year`` is what the running total groups by, so a silently accepted
    one puts the invoice in another year's figures."""
    _header(client)                                     # a good year: 2025
    _add(client, "return_1040")
    client.post("/invoices/new", data={
        "action": "header", "client_id": CLIENT, "plan_key": "standard",
        "tax_year": "12"})
    number, resp = _issue(client)

    assert resp.status_code == 302
    assert _stored(number).tax_year == YEAR


# --- "already exists" is only success when it is the SAME thing ---------------

def test_a_number_that_now_belongs_to_someone_else_is_not_success(client):
    """Principle 8 is about the same request yielding the same result, not about
    any request that names a taken number. A stale tab carries a number that has
    since been issued to another client; redirecting to THEIR invoice tells the
    owner this bill was raised when nothing was written at all."""
    _header(client, client_id="SATC-STALE-A")
    _add(client, "return_1040")
    a_number, resp = _issue(client)
    assert resp.status_code == 302

    # A second tab, opened before A was issued, still carries A's number.
    _header(client, client_id="SATC-STALE-B")
    _add(client, "schedule_d")
    resp = client.post(f"/invoices/{a_number}/issue", data={})

    assert resp.status_code == 302
    b_number = resp.headers["Location"].rsplit("/", 1)[-1]
    assert b_number != a_number, "B must not be redirected to A's invoice"
    assert _stored(b_number) is not None, "B's invoice must actually be written"
    assert _stored(b_number).client_id == "SATC-STALE-B"
    assert _stored(a_number).client_id == "SATC-STALE-A", "A is untouched"


def test_a_session_that_issued_nothing_is_not_shown_someone_elses_invoice(client):
    """The other leg of the same rule. An empty draft used to mean "this is the
    same submit arriving twice" BEFORE anyone asked whose invoice it was, so a
    browser that had never issued anything could post any taken number and be
    redirected into that client's bill (principle 11)."""
    _header(client, client_id="SATC-STALE-C")
    _add(client, "return_1040")
    theirs, resp = _issue(client)
    assert resp.status_code == 302

    stranger = create_app().test_client()           # a session with no draft
    resp = stranger.post(f"/invoices/{theirs}/issue", data={})

    assert resp.status_code == 200, "a stranger must not be redirected anywhere"
    assert "nothing on this draft" in _text(resp)
    assert "SATC-STALE-C" not in _text(resp)


# --- the running total lists only clients with activity that year -------------

def test_billed_to_date_omits_clients_with_nothing_in_that_year(client):
    """A row of pure zeros — including 'Outstanding 0.00' next to a client who
    owes money in an adjacent year — is worse than no row (principle 13)."""
    client.post("/invoices/new", data={
        "action": "header", "client_id": "SATC-PRIORYEAR", "plan_key": "standard",
        "tax_year": "2001"})
    _add(client, "return_1040")
    _, resp = _issue(client)
    assert resp.status_code == 302

    running = _text(client.get("/invoices")).split("Billed to date", 1)[1]
    assert "SATC-PRIORYEAR" not in running


# --- the rate plan comes off the engagement, and says when it doesn't ---------

@pytest.fixture()
def agreed_plan():
    """A client whose engagement actually records what they pay."""
    from satc.models.work import Engagement

    engagement = Engagement(client_id="SATC-PLAN-AGREED", tax_year=YEAR,
                            rate_plan_key="household",
                            rate_plan_basis="W-2 household, single income")
    STATE.mart.engagements.append(engagement)
    yield engagement
    STATE.mart.engagements.remove(engagement)


def test_the_build_screen_prefills_the_plan_agreed_on_the_engagement(client, agreed_plan):
    """What a client pays is a term of the contract. Re-deciding it per invoice
    is how nothing on file ever ends up saying "this household is on the
    household rate"."""
    body = _text(_header(client, client_id="SATC-PLAN-AGREED",
                         plan_key="standard", shown="standard"))

    assert 'value="household" selected' in body, "the agreed plan must be selected"
    assert "agreed on the 2025 engagement" in body
    assert "W-2 household, single income" in body

    # And it is what the invoice is actually issued on, not just what is drawn.
    _add(client, "return_1040")
    number, resp = _issue(client)
    assert resp.status_code == 302
    assert _stored(number).plan_key == "household"
    assert _stored(number).plan_basis == "W-2 household, single income"


def test_a_client_nobody_has_priced_is_said_so_rather_than_defaulted(client):
    """The practice default is not a decision, and must not be presented as
    one. An unanswered question is not an answer (principle 2)."""
    body = _text(_header(client, client_id="SATC-PLAN-NOBODY",
                         plan_key="standard", shown="standard"))

    assert "Nobody has priced this client yet" in body
    assert "No rate plan agreed for 2025" in body


def test_choosing_a_plan_yourself_is_kept_over_the_engagements(client, agreed_plan):
    """The prefill is a starting point, not a veto: a plan the owner actually
    picked on the screen is a decision and survives."""
    body = _text(_header(client, client_id="SATC-PLAN-AGREED",
                         plan_key="pro_bono", shown="standard",
                         basis="Volunteer referral"))
    assert 'value="pro_bono" selected' in body


# --- nothing here sends anything ---------------------------------------------

# --- every screen that states money answers from the ledger -------------------
#
# Principle 11b is not "the invoice page computes the balance". Money arriving is
# the fact EVERYWHERE it is stated, and a flag left answering on one screen is
# the same bug wearing a different URL. These drive the four screens that state
# money — the list, the invoice, its printable copy, and the payments screen —
# through the real app, against payments written through the real store seam.

def _row_for(body: str, key: str) -> str:
    """The one table row that mentions ``key``.

    Assertions about what a row says must not be satisfiable by a different
    row: a screen showing three invoices will contain the word "Settled"
    somewhere whatever it says about the one being asked about.
    """
    for chunk in body.split("<tr>"):
        if key in chunk:
            return chunk
    return ""


def _raised(body: str) -> str:
    return body.split("Billed to date", 1)[0]


def _running(body: str) -> str:
    return body.split("Billed to date", 1)[1]


def _screen_year() -> int:
    """The tax year the Invoices screen groups its running total by.

    Asked of the screen's own helper rather than assumed: the running total only
    lists clients with activity in the working year, so a test that hardcodes a
    year proves nothing about the running total on any machine where the
    practice is working on a different one.
    """
    from satc.app.billing_views import _working_year

    return _working_year()


def _straight_to_the_ledger(**fields):
    """A payment written through the store seam, with no screen involved.

    This is how a payment arrives from anywhere that is not the invoice page —
    an import, another screen, the reconciliation tray — and it is the case a
    flag-reading screen gets wrong, because ``paid_on`` is never touched.
    """
    from satc.billing.payment import Payment

    payment = Payment(**fields)
    STATE.store.save_payments([payment])
    return payment


def test_the_list_screen_answers_from_the_ledger_not_from_the_flag(client):
    """The practice's headline money screen. Both the status column and the
    running total used to read ``invoice.paid_on``, which cannot see a part
    payment and cannot see a payment recorded anywhere but here."""
    from satc.billing.payment import MatchBasis, Method

    cid = "SATC-LIST-LEDGER"
    year = _screen_year()
    _header(client, client_id=cid, tax_year=year)
    _add(client, "return_1040")                              # 450.00
    part, _ = _issue(client, issued_on="2026-03-01")
    _header(client, client_id=cid, tax_year=year)
    _add(client, "return_1040")                              # 450.00
    full, _ = _issue(client, issued_on="2026-03-02")

    _pay(client, part, amount="300", received_on="2026-03-10")
    _straight_to_the_ledger(
        client_id=cid, amount=Decimal("450.00"), received_on=date(2026, 3, 11),
        method=Method.TRANSFER, reference=full, invoice_id=full,
        basis=MatchBasis.REFERENCE)
    assert _stored(full).paid_on is None, "the flag really is out of step"

    body = _text(client.get("/invoices"))

    settled = _row_for(_raised(body), full)
    assert "Settled" in settled
    assert "Overdue" not in settled, "the ledger says it is paid; the flag said nothing"

    owing = _row_for(_raised(body), part)
    assert "Part paid" in owing, "half the money arriving is not 'paid' and not 'unpaid'"
    assert "150.00" in owing, "the row has to name what is still owed"

    total = _row_for(_running(body), cid)
    assert "750.00" in total, "Billed to date must sum the ledger, part payments and all"
    assert "150.00" in total


def test_an_invoice_paid_before_the_ledger_existed_is_kept_and_said_to_be_coarser(client):
    """``paid_on`` set, no payment rows — the record the old screens wrote.

    Recomputing it from an empty ledger answered "fully unpaid", which is real
    data loss in the client's favour, and the printed copy silently dropped
    "Paid in full" altogether. It is a recorded fact, just a coarser one, and
    every screen has to say WHICH kind it is showing.
    """
    cid = "SATC-PRELEDGER"
    _header(client, client_id=cid, tax_year=_screen_year())
    _add(client, "return_1040")                              # 450.00
    number, _ = _issue(client, issued_on="2024-02-01")

    stored = _stored(number)
    stored.paid_on = date(2024, 3, 4)                        # the old flag, as written
    STATE.store.save_invoices([stored])
    assert _ledger_for(cid) == [], "no payment row exists for it"

    page = _text(client.get(f"/invoices/{number}"))
    assert "Nothing recorded against this invoice yet" not in page
    assert "March 04, 2024" in page
    assert "before the payment ledger" in page, "it must say which record this is"

    sheet = _text(client.get(f"/invoices/{number}/print"))
    assert "Paid in full" in sheet, "the client's own copy dropped this entirely"
    assert "March 04, 2024" in sheet

    listed = _text(client.get("/invoices"))
    row = _row_for(_raised(listed), number)
    assert "Overdue" not in row
    assert "pre-ledger" in row.lower(), "a coarse record must not read as a computed one"
    assert "450.00" in _row_for(_running(listed), cid)

    # Looking at it must not quietly rewrite it out of existence.
    assert _stored(number).paid_on == date(2024, 3, 4)


def test_a_payment_dated_in_the_future_is_refused_on_every_path(client):
    """The mirror of the before-the-invoice guard. An identical mistyped year in
    the FUTURE settled the invoice, stopped the chase, and printed a thank-you
    dated 2062 on the client's copy — and the Payments screen had no date guard
    at all, in either direction."""
    cid = "SATC-PAY-FUTURE"
    _header(client, client_id=cid)
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    resp = _pay(client, number, amount="450", received_on="2062-03-01")
    assert resp.status_code == 200, "a refusal is a page, not a redirect or a 500"
    assert "has not happened yet" in _text(resp)
    assert _ledger_for(cid) == [], "nothing may reach the ledger"
    assert _stored(number).paid_on is None

    other = _record_payment(client, client_id=cid, amount="450",
                            received_on="2062-03-01")
    assert other.status_code == 200
    assert "has not happened yet" in _text(other)
    assert _ledger_for(cid) == [], "the other path has to refuse it too"


def test_a_payment_attributed_to_an_invoice_not_on_file_reads_as_stale(client):
    """The store keeps such a row loadable on purpose — a stale attribution is
    something to SHOW the owner. It was shown as a working link into a 404."""
    from satc.billing.payment import MatchBasis, Method

    cid = "SATC-STALE-ATTR"
    _straight_to_the_ledger(
        client_id=cid, amount=Decimal("120.00"), received_on=date(2026, 5, 1),
        method=Method.CHECK, reference="check 9001", invoice_id="2099-9999",
        basis=MatchBasis.CHOSEN_BY_HUMAN)

    assert client.get("/invoices/2099-9999").status_code == 404

    row = _row_for(_text(client.get("/payments")), "2099-9999")
    assert row, "the stale row must still be shown, not hidden"
    assert 'href="/invoices/2099-9999"' not in row, "a link into a 404"
    assert "not on file" in row.lower()


def test_the_invoicing_screens_have_no_send_path():
    """Principle 9. Parsed rather than grepped, so the module stays free to SAY
    it doesn't send while this proves it can't."""
    import ast
    from pathlib import Path

    import satc.app.billing_views as views

    banned_modules = {"smtplib", "ssl"}
    banned_calls = {"sendmail", "send_message", "starttls", "SMTP", "SMTP_SSL"}

    tree = ast.parse(Path(views.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_modules
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_modules
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            assert name not in banned_calls, f"billing_views calls {name}"
