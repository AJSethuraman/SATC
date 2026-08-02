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


# --- driving the screen -------------------------------------------------------

def _header(web, *, plan_key="standard", basis="", client_id=CLIENT):
    return web.post("/invoices/new", data={
        "action": "header", "client_id": client_id, "plan_key": plan_key,
        "plan_basis": basis, "tax_year": str(YEAR)})


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

def test_recording_a_payment_marks_it_paid(client):
    _header(client)
    _add(client, "return_1040")
    number, _ = _issue(client, issued_on="2026-03-01")

    resp = client.post(f"/invoices/{number}/paid", data={"paid_on": "2026-03-15"})
    assert resp.status_code == 302
    assert _stored(number).paid_on == date(2026, 3, 15)
    assert "Paid March 15, 2026" in _text(client.get(f"/invoices/{number}"))


def test_a_nonsense_payment_date_is_shown_as_a_message_not_a_500(client):
    _header(client)
    _add(client, "return_1040")
    number, _ = _issue(client)

    resp = client.post(f"/invoices/{number}/paid", data={"paid_on": "whenever"})
    assert resp.status_code == 200
    assert "is not a date" in _text(resp)
    assert _stored(number).paid_on is None


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


# --- nothing here sends anything ---------------------------------------------

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
