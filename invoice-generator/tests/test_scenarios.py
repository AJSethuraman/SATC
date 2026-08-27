"""End-to-end scenario tests for Invoicer.

Where ``test_calculations.py`` checks the totals arithmetic on a bare model,
these drive whole paths through the running app — sign up, invoice, send, pay,
edit, delete — and assert on what the *owner* and the *paying client* actually
end up with: the badge on the invoice, the balance owed, the row in the CSV,
the bytes in the PDF.

Every test states the real failure it guards against. A test that cannot name
one is not earning its place in a suite that gates a money-handling app.

Nothing here touches the network. Stripe Checkout and SMTP are stubbed at the
module seam (``stripe_utils`` / ``email_utils``), and webhook payloads are
signed locally with a throwaway secret so signature verification is exercised
for real rather than bypassed.

People and companies in these fixtures are invented. Amounts and the 10% tax
rate are round synthetic numbers chosen to make the arithmetic checkable by
eye — they are not SATC's prices and not anyone's real tax rate.

Run with: ``python -m pytest`` from the project root.
"""
import hashlib
import hmac
import json
import time
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import app as appmod
import email_utils
import stripe_utils
from app import create_app
from config import Config
from models import Invoice, LineItem, User, db

# A local stand-in for a Stripe webhook signing secret. Real ones start with
# "whsec_"; this one exists only so construct_event has something to verify
# against, and is never sent anywhere.
TEST_WEBHOOK_SECRET = "whsec_test_only_not_a_real_secret"

OWNER_EMAIL = "amara.okonkwo@bramblefinch.example"
OWNER_PASSWORD = "correct-horse-staple"
SECOND_OWNER_EMAIL = "devraj.pillai@larkspur-audio.example"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def app(tmp_path):
    """A fully wired app on a throwaway SQLite file and a throwaway PDF dir."""

    class ScenarioConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/invoicer-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        APP_BASE_URL = "http://localhost:5000"
        REQUIRE_EMAIL_VERIFICATION = "never"
        STRIPE_SECRET_KEY = "sk_test_not_a_real_key"
        STRIPE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET

    application = create_app(ScenarioConfig)
    yield application


@pytest.fixture
def owner(app):
    """A signed-up business owner, Stripe-connected, ready to invoice."""
    with app.app_context():
        user = User(
            email=OWNER_EMAIL,
            business_name="Bramble & Finch Consulting",
            business_email=OWNER_EMAIL,
            business_address="4 Tinder Lane\nPortsend, ZZ 00000",
            default_currency="USD",
            email_verified=True,
            stripe_account_id="acct_scenariotest001",
            stripe_charges_enabled=True,
        )
        user.set_password(OWNER_PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def client(app, owner):
    """A browser session logged in as the owner."""
    c = app.test_client()
    c.post(
        "/login", data={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    return c


@pytest.fixture
def stub_stripe(monkeypatch):
    """Replace Stripe Checkout with a local fake and record what was asked for.

    Returns the list of created sessions so a test can assert on the amount
    Stripe would have charged — the number that actually leaves the client's
    bank account.
    """
    created = []

    class FakeSession:
        def __init__(self, invoice, amount):
            self.id = f"cs_test_{len(created) + 1:03d}"
            self.url = f"https://checkout.stripe.example/{self.id}"
            self.amount = amount
            self.invoice_id = invoice.id

    def fake_create(invoice, secret_key, base_url, connected_account_id,
                    config=None, success_url=None, cancel_url=None):
        if not connected_account_id:
            raise RuntimeError("Connect a Stripe account first.")
        amount = invoice.balance_due
        if amount <= 0:
            raise ValueError("Invoice has no positive balance due.")
        session = FakeSession(invoice, amount)
        created.append(session)
        return session

    monkeypatch.setattr(stripe_utils, "create_checkout_session", fake_create)
    return created


@pytest.fixture
def sent_mail(monkeypatch):
    """Capture invoice emails instead of delivering them."""
    outbox = []

    def fake_send(config, to_email, invoice, pdf_path, payment_url=None,
                  html_body=None, user=None):
        outbox.append(
            {
                "to": to_email,
                "invoice_number": invoice.invoice_number,
                "pdf_path": pdf_path,
                "payment_url": payment_url,
                "balance_due": invoice.balance_due,
            }
        )

    monkeypatch.setattr(email_utils, "send_invoice_email", fake_send)
    monkeypatch.setattr(email_utils, "can_send", lambda config, user=None: True)
    return outbox


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def make_invoice(client, number="INV-0001", rate="1000.00", quantity="1",
                 tax="10", discount="0", shipping="0",
                 bill_to="Northwind Widgets Ltd\n88 Cargo Road\nHarbourton",
                 client_email="accounts.payable@northwind.example",
                 description="Quarterly bookkeeping review",
                 terms="Net 30", invoice_date=None):
    """Create an invoice through the real form POST. Returns the response.

    The date defaults to *today* rather than a fixed literal so the invoice is
    inside its Net 30 terms whenever the suite runs. A hardcoded date silently
    turns every fixture overdue once it passes, which changes ``display_status``
    and would make these tests start failing on a calendar boundary rather than
    on a code change.
    """
    return client.post(
        "/invoices",
        data={
            "invoice_number": number,
            "bill_to": bill_to,
            "client_email": client_email,
            "invoice_date": invoice_date or date.today().isoformat(),
            "payment_terms": terms,
            "tax": tax,
            "discount": discount,
            "shipping": shipping,
            "item_description": [description],
            "item_quantity": [quantity],
            "item_rate": [rate],
        },
        follow_redirects=False,
    )


def _snapshot(invoice):
    """Read an invoice's stored fields and derived totals into a plain object.

    The ORM instance would be detached the moment its app context closes, and
    every derived total (``total``, ``balance_due``, ``display_status``) walks
    the ``items`` relationship — so it has to be evaluated while the session is
    still open. Returning a snapshot keeps the assertions in the tests readable
    without wrapping each one in a context manager.
    """
    return SimpleNamespace(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        display_status=invoice.display_status,
        currency=invoice.currency,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        amount_paid=invoice.amount_paid,
        balance_due=invoice.balance_due,
        is_partial=invoice.is_partial,
        is_overdue=invoice.is_overdue,
        paid_session_ids=invoice.paid_session_ids,
        client_email=invoice.client_email,
        item_count=len(invoice.items),
    )


def only_invoice(app):
    with app.app_context():
        return _snapshot(Invoice.query.one())


def reload_invoice(app, invoice_id):
    """Snapshot of one invoice, or None if it no longer exists."""
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        return _snapshot(invoice) if invoice is not None else None


def sign_payload(payload: bytes, secret=TEST_WEBHOOK_SECRET, timestamp=None):
    """Produce a Stripe-Signature header the real verifier will accept."""
    timestamp = timestamp or int(time.time())
    signature = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def checkout_event(invoice_id, session_id, amount_cents, currency="usd",
                   account="acct_scenariotest001", payment_status="paid",
                   event_type="checkout.session.completed"):
    event = {
        "id": f"evt_{session_id}",
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "amount_total": amount_cents,
                "currency": currency,
                "payment_status": payment_status,
                "metadata": {"invoice_id": str(invoice_id)},
            }
        },
    }
    if account:
        event["account"] = account
    return event


def post_webhook(app, event, secret=TEST_WEBHOOK_SECRET, timestamp=None):
    body = json.dumps(event).encode()
    return app.test_client().post(
        "/webhook/stripe",
        data=body,
        headers={
            "Stripe-Signature": sign_payload(body, secret, timestamp),
            "Content-Type": "application/json",
        },
    )


def render_pdf(app, invoice_id):
    """Generate the invoice PDF and return its bytes."""
    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        path = appmod.generate_pdf(app, invoice)
        return path.read_bytes()


# --------------------------------------------------------------------------
# The happy path, end to end
# --------------------------------------------------------------------------
def test_create_send_view_pay_receipt(app, client, stub_stripe, sent_mail):
    """The whole billing lifecycle in one pass.

    Guards against a break anywhere along the only path that actually earns
    money: if the invoice is created but the emailed link 404s, or the client
    pays and the invoice never settles, the owner is chasing a client who has
    already paid. Each step asserts the artefact the *next* step depends on.
    """
    assert make_invoice(client).status_code == 302
    invoice = only_invoice(app)
    invoice_id = invoice.id
    # 1000.00 + 10% tax = 1100.00
    assert invoice.total == 1100.00
    assert invoice.status == "Draft"

    # Owner emails it to the client -> status becomes Sent, recipient stored.
    response = client.post(
        f"/invoice/{invoice_id}/email",
        data={"to_email": "accounts.payable@northwind.example"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert len(sent_mail) == 1
    assert sent_mail[0]["to"] == "accounts.payable@northwind.example"
    assert sent_mail[0]["balance_due"] == 1100.00
    assert reload_invoice(app, invoice_id).status == "Sent"

    # The client opens the public link from the email — no login.
    with app.app_context():
        public_url = sent_mail[0]["payment_url"]
    token = public_url.rsplit("/", 1)[-1]
    page = app.test_client().get(f"/i/{token}")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Northwind Widgets Ltd" in body
    assert "1,100.00" in body

    # The client pays.
    pay = app.test_client().post(f"/i/{token}/pay")
    assert pay.status_code == 302
    assert len(stub_stripe) == 1
    assert stub_stripe[0].amount == 1100.00

    # Stripe confirms it.
    assert post_webhook(
        app, checkout_event(invoice_id, stub_stripe[0].id, 110000)
    ).status_code == 200

    settled = reload_invoice(app, invoice_id)
    assert settled.status == "Paid"
    assert settled.amount_paid == 1100.00
    assert settled.balance_due == 0.0

    # The receipt: the same public link now reads as settled, not as a demand.
    receipt = app.test_client().get(f"/i/{token}").get_data(as_text=True)
    assert "Paid" in receipt

    # And the PDF the client keeps is a real, non-empty PDF.
    assert render_pdf(app, invoice_id).startswith(b"%PDF")


# --------------------------------------------------------------------------
# Payment edge cases
# --------------------------------------------------------------------------
def test_partial_payment_leaves_a_chaseable_balance(app, client):
    """A part payment must reduce the balance without settling the invoice.

    Guards against the two opposite failures that both lose money: crediting a
    400.00 payment as though it cleared the whole 1,100.00 (the owner never
    chases the remaining 700.00), or failing to record it at all (the client is
    dunned for money they already sent).
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    assert post_webhook(
        app, checkout_event(invoice_id, "cs_test_partial", 40000)
    ).status_code == 200

    invoice = reload_invoice(app, invoice_id)
    assert invoice.amount_paid == 400.00
    assert invoice.balance_due == 700.00
    assert invoice.status != "Paid"
    assert invoice.is_partial is True
    assert invoice.display_status == "Partial"

    # The remaining 700.00 arrives as a separate Checkout Session and settles it.
    assert post_webhook(
        app, checkout_event(invoice_id, "cs_test_remainder", 70000)
    ).status_code == 200
    settled = reload_invoice(app, invoice_id)
    assert settled.amount_paid == 1100.00
    assert settled.balance_due == 0.0
    assert settled.status == "Paid"


def test_overpayment_is_recorded_not_silently_dropped(app, client):
    """An overpayment must survive as a visible credit.

    Guards against the app clamping ``amount_paid`` to the invoice total. If a
    client pays 1,100.00 twice, the second 1,100.00 is real money that has left
    their account; silently discarding it means the refund owed to them exists
    nowhere in the system and is found only when they complain.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    post_webhook(app, checkout_event(invoice_id, "cs_test_first", 110000))
    post_webhook(app, checkout_event(invoice_id, "cs_test_second", 110000))

    invoice = reload_invoice(app, invoice_id)
    assert invoice.amount_paid == 2200.00
    assert invoice.balance_due == -1100.00, "the credit owed back to the client"
    assert invoice.status == "Paid"


def test_duplicate_webhook_delivery_does_not_double_credit(app, client):
    """Redelivering the same Checkout Session must change nothing.

    Stripe retries a webhook until it gets a 2xx, and delivers at-least-once
    even after success. Guards against the retry inflating ``amount_paid``:
    one 1,100.00 payment delivered three times would show as 3,300.00 paid, a
    2,200.00 phantom credit on the client's account.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    event = checkout_event(invoice_id, "cs_test_retried", 110000)

    for _ in range(3):
        assert post_webhook(app, event).status_code == 200

    invoice = reload_invoice(app, invoice_id)
    assert invoice.amount_paid == 1100.00
    assert invoice.balance_due == 0.0
    assert invoice.paid_session_ids == "cs_test_retried"


def test_webhook_with_a_bad_signature_is_rejected(app, client):
    """An unsigned or wrongly-signed payload must not move money.

    The webhook route is unauthenticated and publicly reachable; the signature
    is the *only* thing standing between the internet and "mark this invoice
    paid". Guards against a regression that parses the body before verifying
    it — anyone could then settle any invoice by POSTing JSON.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    event = checkout_event(invoice_id, "cs_test_forged", 110000)

    forged = post_webhook(app, event, secret="whsec_wrong_secret_entirely")
    assert forged.status_code == 400

    unsigned = app.test_client().post(
        "/webhook/stripe",
        data=json.dumps(event).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert unsigned.status_code == 400

    untouched = reload_invoice(app, invoice_id)
    assert untouched.amount_paid == 0.0
    assert untouched.status == "Draft"


def test_stale_webhook_replay_is_rejected(app, client):
    """A captured payload replayed later must not re-credit the invoice.

    Guards against an attacker who obtains one genuine signed payload (from a
    log, a proxy, a bug report) and replays it repeatedly. Stripe's signature
    covers a timestamp; the verifier must enforce its tolerance window.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    thirty_days_ago = int(time.time()) - 60 * 60 * 24 * 30

    replayed = post_webhook(
        app,
        checkout_event(invoice_id, "cs_test_replayed", 110000),
        timestamp=thirty_days_ago,
    )
    assert replayed.status_code == 400
    assert reload_invoice(app, invoice_id).amount_paid == 0.0


def test_webhook_for_a_deleted_invoice_does_not_error(app, client):
    """A payment landing after the invoice is gone must return 2xx, not 500.

    Guards against Stripe's retry storm: a 500 makes Stripe redeliver the event
    for days and eventually disable the endpoint, which would then drop *real*
    payments for *other* invoices. The event is unmatchable, but that is a log
    line, not a server error.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    client.post(f"/invoice/{invoice_id}/delete")
    assert reload_invoice(app, invoice_id) is None

    orphaned = post_webhook(
        app, checkout_event(invoice_id, "cs_test_orphaned", 110000)
    )
    assert orphaned.status_code == 200


def test_webhook_from_another_stripe_account_is_refused(app, client):
    """One connected account must not be able to settle another's invoice.

    Connected accounts choose their own Checkout metadata. Guards against the
    handler trusting ``metadata.invoice_id``: any Stripe user connected to this
    platform could otherwise mark a stranger's 1,100.00 invoice paid by
    charging themselves one cent with the right metadata.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    intruder = post_webhook(
        app,
        checkout_event(
            invoice_id, "cs_test_intruder", 1, account="acct_someoneelse999"
        ),
    )
    assert intruder.status_code == 200, "acknowledged, but not acted on"

    invoice = reload_invoice(app, invoice_id)
    assert invoice.amount_paid == 0.0
    assert invoice.status == "Draft"


def test_webhook_in_the_wrong_currency_is_not_credited(app, client):
    """A payment in a different currency must not be credited at face value.

    Guards against treating 110000 minor units as interchangeable across
    currencies. Crediting a ¥110,000 session against a $1,100.00 invoice would
    settle it for roughly a fifth of what is owed.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    assert post_webhook(
        app,
        checkout_event(invoice_id, "cs_test_wrongccy", 110000, currency="jpy"),
    ).status_code == 200

    invoice = reload_invoice(app, invoice_id)
    assert invoice.amount_paid == 0.0
    assert invoice.status != "Paid"


def test_delayed_payment_method_is_not_credited_until_it_settles(app, client):
    """checkout.session.completed with payment_status "unpaid" is not money.

    For ACH / SEPA / Bacs / Boleto / OXXO, Stripe fires
    ``checkout.session.completed`` the moment the client finishes the Checkout
    page — days before the funds clear, with ``payment_status: unpaid`` — and
    then sends ``checkout.session.async_payment_succeeded`` if and when it
    actually settles. Crediting the first event marks the invoice Paid for a
    debit that can still bounce, and nobody ever chases it.

    This is the bug the fix in app.py's stripe_webhook guards.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    pending = post_webhook(
        app,
        checkout_event(
            invoice_id, "cs_test_ach", 110000, payment_status="unpaid"
        ),
    )
    assert pending.status_code == 200
    unsettled = reload_invoice(app, invoice_id)
    assert unsettled.amount_paid == 0.0, "funds have not cleared yet"
    assert unsettled.status != "Paid"

    # Days later the bank debit clears and Stripe says so.
    cleared = post_webhook(
        app,
        checkout_event(
            invoice_id,
            "cs_test_ach",
            110000,
            event_type="checkout.session.async_payment_succeeded",
        ),
    )
    assert cleared.status_code == 200
    settled = reload_invoice(app, invoice_id)
    assert settled.amount_paid == 1100.00
    assert settled.status == "Paid"


# --------------------------------------------------------------------------
# Editing and deleting
# --------------------------------------------------------------------------
def test_editing_a_paid_invoice_upward_reopens_it(app, client):
    """Adding work to a settled invoice must un-settle it.

    ``status`` is stored, not derived, so before the fix an invoice that was
    paid at 1,100.00 and then edited to 5,500.00 kept its "Paid" badge while
    4,400.00 was owed — and the History KPIs skipped it entirely, because
    outstanding only sums invoices whose status is not "Paid". The money was
    invisible in both places an owner would look.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    post_webhook(app, checkout_event(invoice_id, "cs_test_paid", 110000))
    assert reload_invoice(app, invoice_id).status == "Paid"

    client.post(
        f"/invoice/{invoice_id}",
        data={
            "invoice_number": "INV-0001",
            "bill_to": "Northwind Widgets Ltd\n88 Cargo Road\nHarbourton",
            "client_email": "accounts.payable@northwind.example",
            "invoice_date": date.today().isoformat(),
            "payment_terms": "Net 30",
            "tax": "10",
            "discount": "0",
            "shipping": "0",
            "item_description": ["Quarterly bookkeeping review", "Extra scope"],
            "item_quantity": ["1", "1"],
            "item_rate": ["1000.00", "4000.00"],
        },
    )

    reopened = reload_invoice(app, invoice_id)
    assert reopened.total == 5500.00
    assert reopened.amount_paid == 1100.00
    assert reopened.balance_due == 4400.00
    assert reopened.status != "Paid", "4,400.00 is owed; it cannot read as Paid"
    assert reopened.display_status == "Partial"

    # And it shows up as outstanding on the dashboard.
    history = client.get("/history").get_data(as_text=True)
    assert "4,400.00" in history


def test_editing_a_paid_invoice_downward_settles_it(app, client):
    """Discounting a settled invoice below what was paid must not leave it open.

    The mirror of the reopen case. Guards against an invoice paid at 1,100.00
    and then reduced to 550.00 sitting forever in the "Sent" pile with a
    negative balance, permanently distorting the outstanding KPI.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    post_webhook(app, checkout_event(invoice_id, "cs_test_paid", 110000))

    client.post(
        f"/invoice/{invoice_id}",
        data={
            "invoice_number": "INV-0001",
            "bill_to": "Northwind Widgets Ltd\n88 Cargo Road\nHarbourton",
            "client_email": "accounts.payable@northwind.example",
            "invoice_date": date.today().isoformat(),
            "payment_terms": "Net 30",
            "tax": "10",
            "discount": "50",
            "shipping": "0",
            "item_description": ["Quarterly bookkeeping review"],
            "item_quantity": ["1"],
            "item_rate": ["1000.00"],
        },
    )

    invoice = reload_invoice(app, invoice_id)
    assert invoice.total == 550.00
    assert invoice.balance_due == -550.00
    assert invoice.status == "Paid"


def test_overdue_outranks_partial_on_the_badge(app, client):
    """A part-paid invoice past its due date must read Overdue, not Partial.

    Guards the badge precedence in ``display_status``. "Partial" reads as
    healthy and in-progress; "Overdue" is the one that gets an invoice chased.
    An invoice 60 days past due with 400.00 of 1,100.00 paid is overdue, and
    showing the gentler badge is how a debt quietly ages out of attention.
    """
    long_ago = (date.today() - timedelta(days=60)).isoformat()
    make_invoice(client, invoice_date=long_ago, terms="Net 30")
    invoice_id = only_invoice(app).id
    post_webhook(app, checkout_event(invoice_id, "cs_test_part", 40000))

    invoice = reload_invoice(app, invoice_id)
    assert invoice.balance_due == 700.00
    assert invoice.is_partial is True
    assert invoice.is_overdue is True
    assert invoice.display_status == "Overdue"

    # And it is counted in the overdue KPI, not just the outstanding one.
    history = client.get("/history?status=overdue").get_data(as_text=True)
    assert "INV-0001" in history


def test_mark_unpaid_erases_a_recorded_stripe_payment(app, client):
    """Documents that "mark as unpaid" zeroes real, Stripe-confirmed money.

    Current behaviour, pinned deliberately. ``mark_unpaid`` exists to reverse a
    manual "mark as paid", but it cannot tell a manual entry from a webhook
    credit: it sets ``amount_paid`` to 0 outright. A 400.00 card payment that
    Stripe really took is erased, and because its session id stays in
    ``paid_session_ids`` the webhook will never re-credit it — the money cannot
    be recovered by any action in the app.

    This test is a tripwire, not an endorsement. Once payments are recorded
    individually (see docs/invoicer-review.md), it SHOULD fail — rewrite it to
    assert the Stripe-confirmed 400.00 survives.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    post_webhook(app, checkout_event(invoice_id, "cs_test_cardpayment", 40000))
    assert reload_invoice(app, invoice_id).amount_paid == 400.00

    client.post(f"/invoice/{invoice_id}/mark-unpaid")

    after = reload_invoice(app, invoice_id)
    assert after.amount_paid == 0.0, "the real 400.00 is gone"
    assert "cs_test_cardpayment" in after.paid_session_ids

    # Replaying the original webhook cannot bring it back.
    post_webhook(app, checkout_event(invoice_id, "cs_test_cardpayment", 40000))
    assert reload_invoice(app, invoice_id).amount_paid == 0.0


def test_deleting_an_invoice_removes_its_line_items(app, client):
    """Deleting an invoice must not strand its line items in the database.

    Guards against a regression in the delete-orphan cascade. Orphaned rows
    with a dangling ``invoice_id`` accumulate silently and break any later
    reporting that joins the two tables.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    with app.app_context():
        assert LineItem.query.filter_by(invoice_id=invoice_id).count() == 1

    client.post(f"/invoice/{invoice_id}/delete")

    with app.app_context():
        assert db.session.get(Invoice, invoice_id) is None
        assert LineItem.query.filter_by(invoice_id=invoice_id).count() == 0


def test_deleting_a_paid_invoice_destroys_the_payment_record(app, client):
    """Documents that deleting a paid invoice erases the only record of payment.

    This is the app's *current* behaviour, pinned deliberately: there is no
    payments table, so ``amount_paid`` and ``paid_session_ids`` live on the
    invoice row and go with it. A 1,100.00 charge that still exists in Stripe
    then has no counterpart here.

    This test is a tripwire, not an endorsement. If a payments ledger is added
    (see docs/invoicer-review.md), this test SHOULD fail — rewrite it to assert
    the payment survives.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    post_webhook(app, checkout_event(invoice_id, "cs_test_realmoney", 110000))
    assert reload_invoice(app, invoice_id).amount_paid == 1100.00

    client.post(f"/invoice/{invoice_id}/delete")

    with app.app_context():
        assert db.session.get(Invoice, invoice_id) is None
        # Nothing anywhere else remembers the 1,100.00.
        assert Invoice.query.filter_by(
            paid_session_ids="cs_test_realmoney"
        ).count() == 0


# --------------------------------------------------------------------------
# Authorization — one account must never reach another's data
# --------------------------------------------------------------------------
def _second_owner(app):
    with app.app_context():
        other = User(
            email=SECOND_OWNER_EMAIL,
            business_name="Larkspur Audio",
            email_verified=True,
            default_currency="USD",
        )
        other.set_password("another-long-passphrase")
        db.session.add(other)
        db.session.commit()
        return other.api_key


def test_another_user_cannot_reach_the_owners_invoice_over_the_web(app, client):
    """Every per-invoice web route must refuse a signed-in stranger.

    Invoice ids are sequential integers, so "guess an id" is one loop. Guards
    against a new route being added without ``owned_or_404`` — the failure mode
    is any customer reading, editing, settling or deleting any other
    customer's invoices, including their clients' names and amounts.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    _second_owner(app)

    intruder = app.test_client()
    intruder.post(
        "/login",
        data={
            "email": SECOND_OWNER_EMAIL,
            "password": "another-long-passphrase",
        },
    )
    assert intruder.get("/account").status_code == 200, "intruder is logged in"

    for method, path in [
        ("get", f"/invoice/{invoice_id}"),
        ("get", f"/invoice/{invoice_id}/edit"),
        ("get", f"/invoice/{invoice_id}/pdf"),
        ("get", f"/invoice/{invoice_id}/logo"),
        ("post", f"/invoice/{invoice_id}"),
        ("post", f"/invoice/{invoice_id}/mark-paid"),
        ("post", f"/invoice/{invoice_id}/mark-unpaid"),
        ("post", f"/invoice/{invoice_id}/email"),
        ("post", f"/invoice/{invoice_id}/delete"),
    ]:
        response = getattr(intruder, method)(path)
        assert response.status_code == 404, f"{method.upper()} {path} leaked"

    survivor = reload_invoice(app, invoice_id)
    assert survivor is not None, "the intruder's DELETE must not have landed"
    assert survivor.status == "Draft", "nor their mark-paid"


def test_another_user_cannot_reach_the_owners_invoice_over_the_api(app, client):
    """The JSON API must scope every invoice route to the key's owner.

    Guards against the API becoming the soft underbelly: it is CSRF-exempt and
    machine-facing, so a key holder probing ``/api/invoices/1..n`` is cheap and
    silent. Read, PDF, payment-link and delete are each checked.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    other_key = _second_owner(app)

    for method, path in [
        ("get", f"/api/invoices/{invoice_id}"),
        ("get", f"/api/invoices/{invoice_id}/pdf"),
        ("post", f"/api/invoices/{invoice_id}/payment-link"),
        ("delete", f"/api/invoices/{invoice_id}"),
    ]:
        response = getattr(app.test_client(), method)(
            path, headers={"X-API-Key": other_key}
        )
        assert response.status_code == 404, f"{method.upper()} {path} leaked"

    assert reload_invoice(app, invoice_id) is not None
    # And the owner's list never mentions the other workspace's invoices.
    listing = app.test_client().get(
        "/api/invoices", headers={"X-API-Key": other_key}
    )
    assert listing.get_json()["invoices"] == []


def test_api_rejects_a_missing_or_wrong_key(app, client):
    """No API key, or a made-up one, must never authenticate.

    Guards against a fallback that treats an absent key as an anonymous or
    default user — which would expose every invoice in the database.
    """
    make_invoice(client)
    assert app.test_client().get("/api/invoices").status_code == 401
    assert app.test_client().get(
        "/api/invoices", headers={"X-API-Key": "sk_not_a_real_key"}
    ).status_code == 401
    assert app.test_client().get(
        "/api/invoices", headers={"X-API-Key": ""}
    ).status_code == 401


def test_signed_out_visitors_are_sent_to_login(app, client):
    """Owner-facing pages must not serve anything to an anonymous visitor.

    Guards against a missing ``@login_required``. The listing and CSV export
    are the worst cases: both dump every client name and amount at once.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    anon = app.test_client()

    for path in [
        "/history",
        "/history/export.csv",
        "/account",
        f"/invoice/{invoice_id}",
        f"/invoice/{invoice_id}/pdf",
        f"/invoice/{invoice_id}/edit",
    ]:
        response = anon.get(path)
        assert response.status_code == 302, path
        assert "/login" in response.headers["Location"], path


def test_login_next_parameter_cannot_redirect_off_site(app, owner):
    """?next= must only ever send the user to a path on this site.

    "starts with /" is not enough: ``//evil.example/x`` is protocol-relative,
    so the browser leaves the site. A phishing mail linking to
    ``/login?next=//evil.example`` drops the user on the attacker's page at the
    exact moment they have just proved the site is real by signing in.
    """
    for hostile in [
        "//evil.example.com/steal",
        "/\\evil.example.com",
        "https://evil.example.com",
    ]:
        session = app.test_client()
        response = session.post(
            f"/login?next={hostile}",
            data={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
        )
        assert response.headers["Location"] == "/history", hostile

    session = app.test_client()
    allowed = session.post(
        "/login?next=/account",
        data={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
    )
    assert allowed.headers["Location"] == "/account", "real paths still work"


def test_public_token_does_not_expose_other_invoices(app, client):
    """A public link must open exactly one invoice and never be forgeable.

    The ``/i/<token>`` page is the app's only unauthenticated read surface.
    Guards against a token that is really just the invoice id, or a signature
    that is not checked — either would turn one shared link into a directory
    listing of every client's billing.
    """
    make_invoice(client, number="INV-0001")
    make_invoice(client, number="INV-0002", bill_to="Contoso Freight\nDock 9",
                 rate="250.00")
    with app.app_context():
        first, second = Invoice.query.order_by(Invoice.id).all()
        first_id, second_id = first.id, second.id

    with app.app_context(), app.test_request_context():
        token = appmod.make_token(first_id, salt="invoice-public")

    page = app.test_client().get(f"/i/{token}")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Northwind Widgets Ltd" in body
    assert "Contoso Freight" not in body, "leaked another invoice"

    # A raw id, a tampered token, and a token signed with the wrong salt.
    assert app.test_client().get(f"/i/{second_id}").status_code == 404
    assert app.test_client().get(f"/i/{token}x").status_code == 404
    with app.app_context(), app.test_request_context():
        wrong_salt = appmod.make_token(second_id, salt="not-the-right-salt")
    assert app.test_client().get(f"/i/{wrong_salt}").status_code == 404


def test_production_refuses_to_boot_on_the_development_secret_key(tmp_path):
    """A production deploy must not start on the shipped default secret.

    SECRET_KEY signs both session cookies and the ``/i/<token>`` public links.
    On the default ``dev-only-change-me`` anyone can mint a session cookie for
    any account and a public link for any invoice id. A self-hosted or
    hand-configured deploy that forgets FLASK_SECRET_KEY previously booted
    perfectly happily and looked completely normal.
    """

    class InsecureProdConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/boot-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        ENV = "production"
        SECRET_KEY = "dev-only-change-me"

    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        create_app(InsecureProdConfig)

    # A real secret boots fine.
    class SecureProdConfig(InsecureProdConfig):
        SECRET_KEY = "a-genuinely-random-production-value"

    assert create_app(SecureProdConfig) is not None


# --------------------------------------------------------------------------
# Amounts at the edges
# --------------------------------------------------------------------------
def test_zero_amount_invoice(app, client, stub_stripe):
    """A 0.00 invoice must be issuable but not payable.

    Written-off or courtesy work still needs a document. Guards against two
    failures: refusing to create it at all, and offering a "Pay now" button
    that hands Stripe a zero-amount Checkout Session (which Stripe rejects with
    an error the client sees).
    """
    assert make_invoice(client, rate="0.00", tax="0").status_code == 302
    invoice_id = only_invoice(app).id

    invoice = reload_invoice(app, invoice_id)
    assert invoice.total == 0.0
    assert invoice.balance_due == 0.0

    with app.app_context(), app.test_request_context():
        token = appmod.make_token(invoice_id, salt="invoice-public")
    assert app.test_client().get(f"/i/{token}").status_code == 200

    # Paying it is a no-op redirect, and no Stripe session is created.
    assert app.test_client().post(f"/i/{token}/pay").status_code == 302
    assert stub_stripe == [], "must not open Checkout for a zero balance"

    assert render_pdf(app, invoice_id).startswith(b"%PDF")


def test_large_amount_invoice_keeps_full_precision(app, client):
    """A seven-figure invoice must not lose cents to float display.

    Guards against a total that renders as 1,234,567.89 but is stored or
    charged as 1,234,567.88 — and against the Stripe minor-unit conversion
    (``int(round(amount * 100))``) drifting on large values, which is where
    binary floating point actually bites.
    """
    make_invoice(client, rate="1234567.89", tax="0", quantity="1")
    invoice_id = only_invoice(app).id

    invoice = reload_invoice(app, invoice_id)
    assert invoice.subtotal == 1234567.89
    assert invoice.total == 1234567.89
    assert invoice.balance_due == 1234567.89
    # The exact integer of cents Stripe would be asked to charge.
    assert int(round(invoice.total * 100)) == 123456789

    listing = client.get("/history").get_data(as_text=True)
    assert "1,234,567.89" in listing

    assert render_pdf(app, invoice_id).startswith(b"%PDF")


def test_invoice_with_no_line_items_is_rejected(app, client):
    """An empty invoice must not be creatable through the form.

    Guards against sending a client a document with a total of 0.00 and no
    explanation of what it is for — and against the "at least one line item"
    rule being lost when the form parsing changes.
    """
    response = client.post(
        "/invoices",
        data={
            "invoice_number": "INV-0001",
            "bill_to": "Northwind Widgets Ltd",
            "invoice_date": date.today().isoformat(),
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": [""],
            "item_quantity": [""],
            "item_rate": [""],
        },
    )
    assert response.status_code == 400
    assert "line item" in response.get_data(as_text=True).lower()
    with app.app_context():
        assert Invoice.query.count() == 0


def test_pdf_renders_for_an_invoice_with_no_line_items(app, owner):
    """A line-item-less row already in the database must still render a PDF.

    Rows like this predate the validation rule and can still arrive via a
    direct database edit. Guards against ``/invoice/<id>/pdf`` raising a 500 on
    an empty items list, which would make the invoice impossible to open.
    """
    with app.app_context():
        invoice = Invoice(
            user_id=owner,
            invoice_number="INV-LEGACY",
            from_info="Bramble & Finch Consulting",
            bill_to="Contoso Freight",
            currency="USD",
        )
        db.session.add(invoice)
        db.session.commit()
        invoice_id = invoice.id

    assert reload_invoice(app, invoice_id).total == 0.0
    assert render_pdf(app, invoice_id).startswith(b"%PDF")


def test_discount_over_one_hundred_percent_is_rejected(app, client):
    """A discount above 100% must not produce a negative invoice.

    A 150% discount drove the taxable base negative, which produced a negative
    tax and a total of -500.00 — a document telling the client the firm owes
    *them*. It also subtracted from the outstanding KPI, understating the
    whole book by that amount.
    """
    response = make_invoice(client, rate="1000.00", discount="150")
    assert response.status_code == 400
    assert "100%" in response.get_data(as_text=True)
    with app.app_context():
        assert Invoice.query.count() == 0

    # 100% exactly is legitimate — a fully written-off invoice.
    assert make_invoice(client, rate="1000.00", discount="100",
                        tax="0").status_code == 302
    assert only_invoice(app).total == 0.0


def test_api_rejects_a_discount_over_one_hundred_percent(app, owner):
    """The JSON API must not be a way around the web form's validation.

    Guards against the two entry points drifting apart. The API is the more
    likely source of bad data, since it is driven by another system rather
    than by a person looking at a form.
    """
    with app.app_context():
        key = db.session.get(User, owner).api_key

    response = app.test_client().post(
        "/api/invoices",
        headers={"X-API-Key": key},
        json={
            "from_info": "Bramble & Finch Consulting",
            "bill_to": "Contoso Freight",
            "items": [{"description": "Advisory", "quantity": 1, "rate": 1000}],
            "discount": {"value": 150, "percent": True},
        },
    )
    assert response.status_code == 422
    assert any(
        "100" in detail for detail in response.get_json()["details"]
    )
    with app.app_context():
        assert Invoice.query.count() == 0


# --------------------------------------------------------------------------
# Exports, numbering, and file handling
# --------------------------------------------------------------------------
def test_csv_export_neutralises_spreadsheet_formula_injection(app, client):
    """Exported fields must not execute when the CSV is opened in a spreadsheet.

    ``bill_to`` is free text and, through the JSON API, can be written by a
    third-party system. Excel, LibreOffice and Sheets all execute a cell whose
    text starts with =, +, - or @, so a client name of ``=cmd|'/c calc'!A1``
    runs on the accountant's machine the moment they open the export.
    """
    make_invoice(client, bill_to="=cmd|'/c calc'!A1", number="+INV-0001")

    body = client.get("/history/export.csv").get_data(as_text=True)
    row = [line for line in body.splitlines() if "cmd" in line][0]

    assert "'=cmd" in row, "the formula must be quoted inert"
    assert not row.split(",")[0].startswith("+"), "and so must the number"
    # The text is still readable to a human.
    assert "cmd|'/c calc'!A1" in row


def test_suggested_invoice_number_does_not_repeat_after_a_deletion(app, client):
    """The next suggested number must never collide with an issued one.

    The suggestion was ``count + 1``, so deleting any invoice handed the next
    one a number already in use. Two different invoices both called INV-0002
    cannot be reconciled against Drake or against the client's own accounts
    payable, and the duplicate is only noticed when someone pays the wrong one.
    """
    make_invoice(client, number="INV-0001")
    make_invoice(client, number="INV-0002")
    make_invoice(client, number="INV-0003")
    with app.app_context():
        second = Invoice.query.filter_by(invoice_number="INV-0002").one()
        second_id = second.id

    client.post(f"/invoice/{second_id}/delete")

    with app.app_context():
        suggested = appmod.next_invoice_number(owner_id(app, client))
        issued = {i.invoice_number for i in Invoice.query.all()}
    assert suggested not in issued
    assert suggested == "INV-0004"


def owner_id(app, client):
    with app.app_context():
        return User.query.filter_by(email=OWNER_EMAIL).one().id


def test_pdf_filename_cannot_escape_the_invoices_directory(app, owner):
    """A hostile invoice number must not steer the PDF outside its directory.

    ``invoice_number`` is free text and lands in the output filename. Only "/"
    was stripped, so ``..\\..\\evil`` wrote outside INVOICES_DIR on the Windows
    run.ps1 path, and the same string was handed back as the browser's
    download filename.
    """
    for hostile in [
        "../../../../tmp/pwned",
        "..\\..\\..\\windows\\system32",
        "....//....//escape",
    ]:
        with app.app_context():
            invoice = Invoice(
                user_id=owner,
                invoice_number=hostile,
                from_info="Bramble & Finch Consulting",
                bill_to="Contoso Freight",
                currency="USD",
            )
            invoice.items = [
                LineItem(description="Advisory", quantity=1, rate=100)
            ]
            db.session.add(invoice)
            db.session.commit()
            path = appmod.generate_pdf(app, invoice)

        invoices_dir = app.config["INVOICES_DIR"].resolve()
        assert path.resolve().parent == invoices_dir, hostile
        assert ".." not in path.name, hostile
        assert "\\" not in path.name and "/" not in path.name, hostile
        assert path.read_bytes().startswith(b"%PDF")


def test_pdf_is_generated_for_every_payment_state(app, client):
    """The PDF must render whatever state the invoice is in.

    The PDF is the artefact the client actually receives, and it is generated
    on demand at send time and at every public-link download. A template that
    assumes a positive balance, or chokes on a negative one, breaks delivery
    for the invoice rather than just displaying oddly.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    states = {}
    states["draft"] = render_pdf(app, invoice_id)

    post_webhook(app, checkout_event(invoice_id, "cs_test_part", 40000))
    states["partial"] = render_pdf(app, invoice_id)

    post_webhook(app, checkout_event(invoice_id, "cs_test_rest", 70000))
    states["paid"] = render_pdf(app, invoice_id)

    post_webhook(app, checkout_event(invoice_id, "cs_test_extra", 50000))
    states["overpaid"] = render_pdf(app, invoice_id)

    for label, content in states.items():
        assert content.startswith(b"%PDF"), label
        assert len(content) > 1000, f"{label} PDF is suspiciously small"


def test_public_pdf_download_works_without_login(app, client, sent_mail):
    """The client's PDF link in the email must work with no account.

    Guards against ``/i/<token>/pdf`` acquiring a ``@login_required`` — the
    recipient of an invoice has no account and never will, so that would make
    every emailed invoice undownloadable.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id
    client.post(
        f"/invoice/{invoice_id}/email",
        data={"to_email": "accounts.payable@northwind.example"},
    )
    token = sent_mail[0]["payment_url"].rsplit("/", 1)[-1]

    response = app.test_client().get(f"/i/{token}/pdf")
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")


# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------
def test_a_failed_send_does_not_mark_the_invoice_sent(app, client, monkeypatch):
    """If the email bounces at the SMTP layer, the invoice stays a Draft.

    Guards against the owner seeing "Sent" for an invoice that never left the
    building, waiting 30 days for payment on a document the client never got.
    The status change must happen only after delivery is accepted.
    """
    make_invoice(client)
    invoice_id = only_invoice(app).id

    def explode(*args, **kwargs):
        raise RuntimeError("SMTP server refused the connection")

    monkeypatch.setattr(email_utils, "send_invoice_email", explode)
    monkeypatch.setattr(email_utils, "can_send", lambda config, user=None: True)

    response = client.post(
        f"/invoice/{invoice_id}/email",
        data={"to_email": "accounts.payable@northwind.example"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Email failed" in response.get_data(as_text=True)

    invoice = reload_invoice(app, invoice_id)
    assert invoice.status == "Draft", "a failed send must not claim success"


def test_emailing_without_a_recipient_is_refused(app, client, sent_mail):
    """A send with no address must be refused rather than attempted.

    Guards against handing an empty To: to the SMTP layer, which either raises
    deep in ``smtplib`` as a 500 or, worse, silently delivers nowhere while the
    invoice flips to "Sent".
    """
    make_invoice(client, client_email="")
    invoice_id = only_invoice(app).id

    response = client.post(
        f"/invoice/{invoice_id}/email", data={"to_email": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Recipient email is required" in response.get_data(as_text=True)
    assert sent_mail == []
    assert reload_invoice(app, invoice_id).status == "Draft"


# --------------------------------------------------------------------------
# Numbers that are not numbers
#
# Added by exercise.py (the scenario harness) — each of these was reproduced
# against a running instance first. The shared failure: a money field that
# could not be parsed, or that parsed into something that is not a real
# amount, was accepted and billed rather than refused. See
# docs/invoicer-scenarios.md.
# --------------------------------------------------------------------------
def test_unparseable_money_is_refused_not_silently_billed_as_zero(app, client):
    """A rate of "$500.00" must be refused, not quietly turned into $0.00.

    ``parse_float`` caught the ValueError from ``float("$500.00")`` and
    returned its default, so pasting a rate with the currency symbol on it —
    which is exactly how an amount arrives from a quote, an email, or another
    system — created a line item worth nothing. The invoice was saved, shown,
    exported and could be emailed to the client for $0.00 with no warning at
    any point. A blank box still means "leave it at the default"; a box with
    something unreadable in it now stops the save.
    """
    response = client.post(
        "/invoices",
        data={
            "invoice_number": "INV-PARSE",
            "bill_to": "Pellham Marine Supply\n2 Quay Street",
            "invoice_date": date.today().isoformat(),
            "payment_terms": "Net 30",
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Hull survey"],
            "item_quantity": ["1"],
            "item_rate": ["$500.00"],
        },
    )
    assert response.status_code == 400
    assert "must be a number" in response.get_data(as_text=True)
    with app.app_context():
        assert Invoice.query.count() == 0, "nothing may be stored on a refusal"


def test_an_overflowing_rate_cannot_produce_a_nan_invoice(app, client):
    """A rate that overflows to infinity must be refused before it is stored.

    ``1e308 x 10`` is ``inf``; ``inf * 0% tax`` is ``nan``; and ``nan < 0`` is
    False, so the negative-total guard let it through. The invoice was stored
    with a NaN total and the History page then rendered "$nan" for
    outstanding, overdue AND paid — every KPI in the account, not just this
    invoice's row. The owner's dashboard stopped reporting any figure at all.
    """
    response = client.post(
        "/invoices",
        data={
            "invoice_number": "INV-OVERFLOW",
            "bill_to": "Pellham Marine Supply\n2 Quay Street",
            "invoice_date": date.today().isoformat(),
            "payment_terms": "Net 30",
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Dredging"],
            "item_quantity": ["10"],
            "item_rate": ["1e308"],
        },
    )
    assert response.status_code == 400
    assert "not a real amount" in response.get_data(as_text=True)
    with app.app_context():
        assert Invoice.query.count() == 0

    # And the dashboard still reports numbers.
    make_invoice(client, number="INV-OK", rate="1000.00")
    history = client.get("/history").get_data(as_text=True)
    assert "nan" not in history.lower()


def test_a_literal_exponent_overflow_is_refused_too(app, client):
    """"1e400" is a *valid* float literal that evaluates to infinity.

    Distinct from the test above: nothing has to be multiplied for this one to
    go wrong, so it slipped past any guard placed on the arithmetic rather
    than on the input. It is a plausible paste or a fat-fingered exponent.
    """
    response = client.post(
        "/invoices",
        data={
            "invoice_number": "INV-1E400",
            "bill_to": "Pellham Marine Supply",
            "invoice_date": date.today().isoformat(),
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Dredging"],
            "item_quantity": ["1"],
            "item_rate": ["1e400"],
        },
    )
    assert response.status_code == 400
    with app.app_context():
        assert Invoice.query.count() == 0


def test_mismatched_line_item_arrays_are_refused_not_silently_truncated(
    app, client
):
    """Three descriptions and two quantities must not become a two-line bill.

    ``zip`` truncates to the shortest of the three parallel form arrays, so a
    disabled input, a JS change, or a row the browser dropped removed a whole
    line item and its money with no error anywhere. The invoice was created,
    could be sent, and could be paid — at the wrong amount. Refusing is the
    only safe answer: inventing a blank quantity for the missing cell would
    bill the line at zero, which is the same failure wearing a hat.
    """
    response = client.post(
        "/invoices",
        data={
            "invoice_number": "INV-ZIP",
            "bill_to": "Ironbridge Joinery\n14 Forge Row",
            "invoice_date": date.today().isoformat(),
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Design", "Build", "Install"],
            "item_quantity": ["1", "1"],
            "item_rate": ["100.00", "100.00", "100.00"],
        },
    )
    assert response.status_code == 400
    assert "did not arrive intact" in response.get_data(as_text=True)
    with app.app_context():
        assert Invoice.query.count() == 0


def test_a_refused_edit_leaves_the_stored_invoice_untouched(app, client):
    """A refusal must write nothing — including on the edit path.

    The edit path clears ``invoice.items`` on the live ORM instance *before*
    validation runs, so a refusal happens with the invoice already emptied in
    the session. If any of that reached the database, refusing a bad edit
    would destroy the good invoice it was protecting.
    """
    make_invoice(client, number="INV-EDIT", rate="1000.00", tax="10")
    before = only_invoice(app)
    assert before.total == 1100.0

    response = client.post(
        f"/invoice/{before.id}",
        data={
            "invoice_number": "INV-EDIT",
            "bill_to": "Ironbridge Joinery",
            "invoice_date": date.today().isoformat(),
            "tax": "10", "discount": "0", "shipping": "0",
            "item_description": ["Design", "Build"],
            "item_quantity": ["1"],
            "item_rate": ["1000.00", "500.00"],
        },
    )
    assert response.status_code == 400

    after = reload_invoice(app, before.id)
    assert after is not None, "a refused edit must not delete the invoice"
    assert after.item_count == before.item_count
    assert after.total == before.total


def test_api_rejects_a_negative_amount_paid(app, owner):
    """amount_paid: -500 must be refused, not treated as money owed.

    A negative payment makes ``balance_due`` larger than the total, so a $100
    invoice reads as $600 outstanding and the account's outstanding KPI gains
    $500 that no client will ever pay. Overpayment stays legal — that happens
    for real — so only the negative side is refused.
    """
    with app.app_context():
        api_key = db.session.get(User, owner).api_key

    response = app.test_client().post(
        "/api/invoices",
        headers={"X-API-Key": api_key},
        json={
            "invoice_number": "API-NEGPAID",
            "from_info": "Halloway & Vance",
            "bill_to": "Sable Court Chambers",
            "items": [{"description": "Advice", "quantity": 1, "rate": 100}],
            "amount_paid": -500,
        },
    )
    assert response.status_code == 422
    assert "amount_paid cannot be negative" in json.dumps(response.get_json())
    with app.app_context():
        assert Invoice.query.count() == 0


def test_api_rejects_a_nan_rate(app, owner):
    """Python's JSON decoder accepts the bare literal NaN. The API must not.

    ``{"rate": NaN}`` reached the model, and SQLite stored the NaN as NULL —
    so the line silently came back worth 0.00 after the commit. Whatever the
    engine does with it, the request should never have been accepted.
    """
    with app.app_context():
        api_key = db.session.get(User, owner).api_key

    response = app.test_client().post(
        "/api/invoices",
        headers={"X-API-Key": api_key},
        data=json.dumps(
            {
                "invoice_number": "API-NAN",
                "from_info": "Halloway & Vance",
                "bill_to": "Sable Court Chambers",
                "items": [
                    {"description": "Advice", "quantity": 1,
                     "rate": float("nan")}
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 422
    assert "finite number" in json.dumps(response.get_json())
    with app.app_context():
        assert Invoice.query.count() == 0


def test_both_front_doors_refuse_the_same_unparseable_value(app, client, owner):
    """The web form and the JSON API must agree about what is not a number.

    They had separate coercion helpers with separate holes, which is how the
    API came to accept things the form rejected. Both now call
    ``helpers.parse_money``; this holds them to the same answer so the two
    cannot drift apart again.
    """
    with app.app_context():
        api_key = db.session.get(User, owner).api_key

    web = client.post(
        "/invoices",
        data={
            "invoice_number": "INV-BOTH",
            "bill_to": "Sable Court Chambers",
            "invoice_date": date.today().isoformat(),
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Advice"],
            "item_quantity": ["1"],
            "item_rate": ["£420"],
        },
    )
    api = app.test_client().post(
        "/api/invoices",
        headers={"X-API-Key": api_key},
        json={
            "invoice_number": "API-BOTH",
            "from_info": "Halloway & Vance",
            "bill_to": "Sable Court Chambers",
            "items": [{"description": "Advice", "quantity": 1, "rate": "£420"}],
        },
    )
    assert web.status_code == 400
    assert api.status_code == 422
    with app.app_context():
        assert Invoice.query.count() == 0


# ── a public link must not outlive its invoice ────────────────────────────

def test_a_deleted_invoice_id_is_never_reused(client, app):
    """A PUBLIC LINK POINTING AT SOMEBODY ELSE'S INVOICE.

    `/i/<token>` signs the invoice's integer primary key. Without
    AUTOINCREMENT, SQLite hands the next insert the highest free rowid, so
    deleting an invoice releases its id and the next invoice raised on the
    instance inherits it — and every link already in a client's inbox resolves
    to a different invoice.

    Reproduced across accounts by the harness: owner A raises a confidential
    invoice, sends the link, deletes it; owner B, a different workspace, raises
    the next one and inherits the id; A's client opens A's link and reads B's
    invoice.

    Postgres allocates from a sequence and never reuses, so Render was never
    affected. `docker compose up`, `run.ps1` and a bare `flask run` all default
    to SQLite and were.
    """
    from models import db, Invoice, User

    with app.app_context():
        owner = User(email="recycle@example.com", password_hash="x")
        db.session.add(owner)
        db.session.commit()

        ids = []
        for n in range(3):
            inv = Invoice(user_id=owner.id, invoice_number=f"R-{n}",
                          from_info="", bill_to="")
            db.session.add(inv)
            db.session.commit()
            ids.append(inv.id)

        db.session.delete(db.session.get(Invoice, ids[-1]))
        db.session.commit()

        nxt = Invoice(user_id=owner.id, invoice_number="R-next",
                      from_info="", bill_to="")
        db.session.add(nxt)
        db.session.commit()

        assert nxt.id not in ids, (
            f"invoice id {nxt.id} was recycled from a deleted invoice — a "
            f"public link already sent to a client now resolves to this one")


def test_the_model_declares_sqlite_autoincrement():
    """Asserted directly as well, because the behaviour above depends on a
    table created WITH the flag: an existing database file does not gain it,
    and a fixture that happens to be fresh would pass either way."""
    from models import Invoice

    args = getattr(Invoice, "__table_args__", {})
    if isinstance(args, tuple):
        args = next((a for a in args if isinstance(a, dict)), {})
    assert args.get("sqlite_autoincrement") is True, (
        "SQLite will reuse a deleted invoice's id, and every public link "
        "already in a client's hands will follow it")
