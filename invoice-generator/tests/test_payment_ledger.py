"""The payment ledger: what was paid, individually, and never overwritten.

``docs/REPO-INVENTORY.md`` carried this as the last money bug in the app —
*"`amount_paid` is one mutable float with no ledger"*, recorded as **"one thing
to fix before real money."** The firm's answer on 5 September 2026 was *"Fix it
before any client sees it."*

The property these tests exist for, above all the others: **the cache ties out
to the ledger.** ``Invoice.amount_paid`` is kept as a column because a dozen
readers use it, so it is a control account and ``payments`` is its subsidiary
ledger. If those two can disagree, the ledger has bought nothing.
"""
import pytest

from config import Config
from app import create_app, _ensure_schema
from models import Invoice, LineItem, Payment, User, db

OWNER_EMAIL = "amara.okonkwo@bramblefinch.example"
OWNER_PASSWORD = "correct-horse-staple"


@pytest.fixture
def app(tmp_path):
    class LedgerConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/ledger-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        REQUIRE_EMAIL_VERIFICATION = "never"

    return create_app(LedgerConfig)


@pytest.fixture
def owner(app):
    with app.app_context():
        user = User(
            email=OWNER_EMAIL,
            business_name="Bramble & Finch Consulting",
            business_email=OWNER_EMAIL,
            business_address="4 Tinder Lane",
            default_currency="USD",
            email_verified=True,
        )
        user.set_password(OWNER_PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user.id


def make_invoice(app, owner_id, total=1000.0, number="INV-0001"):
    with app.app_context():
        inv = Invoice(
            user_id=owner_id,
            invoice_number=number,
            from_info="Bramble & Finch Consulting",
            bill_to="Northwind Traders LLC",
            currency="USD",
            status="Sent",
        )
        inv.items.append(
            LineItem(position=0, description="Work", quantity=1, rate=total)
        )
        db.session.add(inv)
        db.session.commit()
        return inv.id


def ties_out(inv):
    """The control account equals its subsidiary ledger."""
    return inv.amount_paid == inv.ledger_total


# --- the tie-out, after every operation ----------------------------------

def test_the_cache_ties_out_to_the_ledger_after_every_operation(app, owner):
    invoice_id = make_invoice(app, owner, total=1000.0)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert ties_out(inv) and inv.amount_paid == 0.0

        inv.record_payment(400, source="stripe", external_id="cs_1")
        assert ties_out(inv) and inv.amount_paid == 400.0

        inv.record_payment(250, source="manual", note="cheque")
        assert ties_out(inv) and inv.amount_paid == 650.0

        inv.reverse_manual_payments()
        assert ties_out(inv) and inv.amount_paid == 400.0

        inv.set_manual_paid_total(1000)
        assert ties_out(inv) and inv.amount_paid == 1000.0

        db.session.commit()
        reloaded = db.session.get(Invoice, invoice_id)
        assert ties_out(reloaded), "still ties out after a round trip"


def test_entries_are_appended_never_edited(app, owner):
    """A reversal is its own entry, so the original stays legible."""
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(500, source="manual", note="cheque 0041")
        inv.reverse_manual_payments(note="entered against the wrong invoice")
        db.session.commit()

        entries = db.session.get(Invoice, invoice_id).payments
        assert [e.amount for e in entries] == [500.0, -500.0]
        assert [e.source for e in entries] == ["manual", "reversal"]
        assert entries[0].note == "cheque 0041"
        assert "wrong invoice" in entries[1].note
        assert db.session.get(Invoice, invoice_id).amount_paid == 0.0


# --- confirmed money is not ours to undo ---------------------------------

def test_reversing_never_touches_a_confirmed_payment(app, owner):
    invoice_id = make_invoice(app, owner, total=1000.0)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(400, source="stripe", external_id="cs_card")
        inv.record_payment(300, source="manual", note="cheque")

        reversed_amount = inv.reverse_manual_payments()

        assert reversed_amount == 300.0
        assert inv.confirmed_paid == 400.0
        assert inv.amount_paid == 400.0, "the card payment survives"
        assert ties_out(inv)


def test_a_typed_total_cannot_reduce_below_what_was_confirmed(app, owner):
    """The same rule as the button, applied at the other door.

    Somebody correcting a typo in the "amount paid" box must not be able to
    delete a card payment by typing a smaller number over it.
    """
    invoice_id = make_invoice(app, owner, total=1000.0)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(400, source="stripe", external_id="cs_card")

        inv.set_manual_paid_total(0)

        assert inv.amount_paid == 400.0
        assert ties_out(inv)


def test_a_typed_total_can_still_add_to_a_confirmed_payment(app, owner):
    invoice_id = make_invoice(app, owner, total=1000.0)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(400, source="stripe", external_id="cs_card")
        inv.set_manual_paid_total(900)
        assert inv.amount_paid == 900.0
        assert inv.confirmed_paid == 400.0
        assert inv.manual_paid == 500.0


# --- the second tripwire: where the money came from ----------------------

def test_marking_paid_over_a_card_payment_keeps_them_distinguishable(app, owner):
    """`exercise.py` recorded this as a tripwire before the ledger existed:

    *"$400 by card and $700 by cheque are now one indistinguishable 1100.00;
    if the card payment is disputed there is no record of it."*
    """
    invoice_id = make_invoice(app, owner, total=1100.0)
    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(400, source="stripe", external_id="cs_card")
        db.session.commit()

    client.post(f"/invoice/{invoice_id}/mark-paid")

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert inv.amount_paid == 1100.0
        assert inv.confirmed_paid == 400.0, "the card's share is still knowable"
        assert inv.manual_paid == 700.0, "and only the shortfall was added"
        assert [p.source for p in inv.payments] == ["stripe", "manual"]
        assert ties_out(inv)


# --- idempotency ---------------------------------------------------------

def test_a_replayed_session_is_not_credited_twice(app, owner):
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(400, source="stripe", external_id="cs_dup")
        db.session.commit()

        inv = db.session.get(Invoice, invoice_id)
        assert inv.has_credited("cs_dup") is True
        assert inv.has_credited("cs_other") is False
        assert inv.has_credited(None) is False
        assert inv.has_credited("") is False


def test_a_session_recorded_before_the_ledger_existed_is_still_known(app, owner):
    """Invoices paid before this table existed carry their session ids only in
    the legacy comma-joined string. A replay for one of those must still not
    double-credit, so ``has_credited`` reads both.
    """
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.paid_session_ids = "cs_old_a,cs_old_b"
        db.session.commit()

        inv = db.session.get(Invoice, invoice_id)
        assert inv.has_credited("cs_old_a") is True
        assert inv.has_credited("cs_old_b") is True
        assert inv.has_credited("cs_never") is False


# --- the migration -------------------------------------------------------

def test_an_invoice_paid_before_the_ledger_gets_an_opening_entry(app, owner):
    """The backfill in ``_ensure_schema``.

    An invoice carrying ``amount_paid = 400`` with an empty ledger would read
    as unpaid the moment anything asked the ledger instead of the cache.
    """
    invoice_id = make_invoice(app, owner, total=1000.0)
    with app.app_context():
        # Simulate a row written before the table existed: money on the
        # invoice, nothing in the ledger.
        inv = db.session.get(Invoice, invoice_id)
        inv.amount_paid = 400.0
        db.session.commit()
        assert db.session.get(Invoice, invoice_id).payments == []

        _ensure_schema()

        inv = db.session.get(Invoice, invoice_id)
        assert len(inv.payments) == 1
        entry = inv.payments[0]
        assert entry.amount == 400.0
        assert entry.source == "migrated"
        assert "carried over" in entry.note
        assert ties_out(inv)


def test_the_backfill_is_idempotent(app, owner):
    """It runs per worker at every boot, so running it twice must be a no-op."""
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.amount_paid = 250.0
        db.session.commit()

        for _ in range(3):
            _ensure_schema()

        inv = db.session.get(Invoice, invoice_id)
        assert len(inv.payments) == 1, "one entry, not three"
        assert inv.amount_paid == 250.0


def test_the_backfill_leaves_unpaid_invoices_alone(app, owner):
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        _ensure_schema()
        assert db.session.get(Invoice, invoice_id).payments == []


def test_a_migrated_entry_counts_as_manual_and_can_be_reversed(app, owner):
    """Its origin is unknown, and treating an unknown origin as confirmed
    would let a mistyped total masquerade as a card payment nobody may undo.
    """
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.amount_paid = 300.0
        db.session.commit()
        _ensure_schema()

        inv = db.session.get(Invoice, invoice_id)
        assert inv.confirmed_paid == 0.0
        assert inv.manual_paid == 300.0
        assert inv.reverse_manual_payments() == 300.0
        assert inv.amount_paid == 0.0


# --- housekeeping --------------------------------------------------------

def test_deleting_an_invoice_takes_its_payments_with_it(app, owner):
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(100, source="manual")
        inv.record_payment(200, source="stripe", external_id="cs_x")
        db.session.commit()
        assert db.session.query(Payment).count() == 2

        db.session.delete(db.session.get(Invoice, invoice_id))
        db.session.commit()
        assert db.session.query(Payment).count() == 0, "no orphaned payments"


def test_an_overpayment_is_still_recordable(app, owner):
    """Paying twice by mistake is a real thing; the ledger shows both."""
    invoice_id = make_invoice(app, owner, total=1000.0)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(1000, source="stripe", external_id="cs_1")
        inv.record_payment(1000, source="stripe", external_id="cs_2")
        assert inv.amount_paid == 2000.0
        assert inv.balance_due == -1000.0, "the credit owed back to the client"
        assert len(inv.payments) == 2


def test_a_payment_snapshots_its_currency(app, owner):
    """An invoice's currency can be edited afterwards; a payment happened in
    whatever currency it happened in."""
    invoice_id = make_invoice(app, owner)
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(100, source="stripe", external_id="cs_1", currency="JPY")
        inv.record_payment(100, source="manual")
        assert inv.payments[0].currency == "JPY"
        assert inv.payments[1].currency == "USD", "defaults to the invoice's"
