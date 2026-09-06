"""Currency precision, end to end — the four P1s Codex raised on PR #289.

Every one was real, and the worst was one this branch had itself introduced.

The theme: the app used to know fourteen currencies, all of them two-decimal,
so "two decimal places" was hardcoded in a dozen places and was never wrong.
Offering 157 made 23 of them wrong at once — zero-decimal currencies like the
yen and three-decimal ones like the Kuwaiti dinar.
"""
import pytest

from config import Config
from app import create_app, _ensure_schema
from currencies import format_unit_price
from helpers import format_money
from models import Invoice, LineItem, Payment, User, db
from stripe_utils import from_minor_units, to_minor_units

OWNER_EMAIL = "amara.okonkwo@bramblefinch.example"


@pytest.fixture
def app(tmp_path):
    class PrecisionConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/precision-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False

    return create_app(PrecisionConfig)


@pytest.fixture
def owner(app):
    with app.app_context():
        user = User(email=OWNER_EMAIL, business_name="Bramble & Finch",
                    default_currency="USD", email_verified=True)
        user.set_password("correct-horse-staple")
        db.session.add(user)
        db.session.commit()
        return user.id


def invoice(currency, lines, **kw):
    inv = Invoice(
        invoice_number="INV-0001", from_info="Bramble & Finch",
        bill_to="Northwind Traders LLC", currency=currency, status="Sent",
        tax_value=kw.get("tax", 0), tax_is_percent=True,
        discount_value=0, discount_is_percent=True,
        shipping=0, amount_paid=0,
    )
    for i, (qty, rate) in enumerate(lines):
        inv.items.append(LineItem(position=i, description="Work",
                                  quantity=qty, rate=rate))
    return inv


# --- P1: the arithmetic must follow the currency, not just the display ----

def test_a_three_decimal_row_multiplies_out_on_the_page():
    """Codex: "a KWD line with quantity 1 and rate 1.235 prints a unit price of
    KD1.235 but computes and charges an amount of KD1.240"."""
    inv = invoice("KWD", [(1, 1.235)])
    assert format_unit_price(1.235, "KWD") == "KD1.235"
    assert inv.items[0].amount == 1.235
    assert format_money(inv.items[0].amount, "KWD") == "KD1.235"
    assert inv.total == 1.235
    assert to_minor_units(inv.total, "KWD") == 1235


def test_a_zero_decimal_invoice_never_stores_an_impossible_amount():
    """3 x 100.5 stored 301.5 — an amount of yen that cannot exist. It showed
    as ¥302 and charged ¥302, so the database held the only wrong number."""
    inv = invoice("JPY", [(3, 100.5)])
    assert inv.items[0].amount == 302.0
    assert inv.total == 302.0
    assert inv.total == round(inv.total), "a yen amount must be whole"
    assert to_minor_units(inv.total, "JPY") == 302


def test_the_unit_price_may_carry_more_precision_than_the_currency():
    """The amount must be payable; the rate only has to be honest.

    Clamping the rate made the row read `3 x ¥100 = ¥302`.
    """
    assert format_unit_price(100.5, "JPY") == "¥100.5"
    assert format_unit_price(500, "JPY") == "¥500", "no invented decimals"
    assert format_unit_price(19.99, "USD") == "$19.99"
    assert format_unit_price(1.235, "KWD") == "KD1.235"


@pytest.mark.parametrize("code", ["USD", "EUR", "GBP", "CAD", "INR"])
def test_two_decimal_currencies_are_completely_unchanged(code):
    """The overwhelmingly common path must behave exactly as it always did."""
    inv = invoice(code, [(3, 100.5), (2, 19.99)], tax=8.25)
    assert inv.items[0].amount == 301.5
    assert inv.items[1].amount == 39.98
    assert inv.subtotal == 341.48
    assert inv.tax_amount == 28.17
    assert inv.total == 369.65


def test_a_detached_line_item_falls_back_to_two_places():
    """It has no currency of its own and must not invent one.

    Asserted as a property rather than a literal: 3 x 100.505 is 301.515, whose
    double sits a hair BELOW the half, so the two-place answer is 301.51 and
    not the 301.52 you get by rounding the decimal in your head. Writing the
    literal is how you end up asserting your own arithmetic instead of the
    code's.
    """
    orphan = LineItem(position=0, description="x", quantity=3, rate=100.505)
    assert orphan.amount == round(3 * 100.505, 2)
    assert orphan.amount != round(3 * 100.505, 3), "it is not using 3 places"


def test_percentages_round_to_the_currency_too():
    inv = invoice("JPY", [(1, 1000)], tax=8.25)
    assert inv.tax_amount == 82.0, "8.25% of ¥1,000 is ¥82, not ¥82.50"
    assert inv.total == 1082.0


# --- P1: the webhook must decode with the currency's exponent -------------

def test_the_webhook_decode_is_the_exact_inverse_of_the_charge():
    """The bug this branch introduced by fixing only one half.

    Before `to_minor_units`, outbound `x100` and inbound `/100` cancelled for
    the yen: the client was overcharged 100x and the invoice still recorded the
    right figure. Fixing outbound alone left a ¥1,500 payment recording as ¥15.
    """
    for code, amount in [("JPY", 1500), ("KWD", 12.345), ("USD", 1071.67),
                         ("EUR", 0.01), ("VND", 250000)]:
        assert from_minor_units(to_minor_units(amount, code), code) == amount


def test_a_yen_payment_settles_a_yen_invoice(app, owner):
    """End to end through the model, the way the webhook path does it."""
    with app.app_context():
        inv = invoice("JPY", [(1, 1500)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()

        # what Stripe sends back for a correctly-charged ¥1,500 session
        amount_total = to_minor_units(inv.total, "JPY")
        assert amount_total == 1500

        inv.record_payment(from_minor_units(amount_total, "jpy"),
                           source="stripe", external_id="cs_jpy", currency="JPY")
        db.session.commit()

        settled = db.session.get(Invoice, inv.id)
        assert settled.amount_paid == 1500.0, "not ¥15"
        assert settled.balance_due == 0.0


def test_a_dinar_payment_settles_a_dinar_invoice(app, owner):
    with app.app_context():
        inv = invoice("KWD", [(1, 12.345)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()

        amount_total = to_minor_units(inv.total, "KWD")
        assert amount_total == 12345

        inv.record_payment(from_minor_units(amount_total, "kwd"),
                           source="stripe", external_id="cs_kwd", currency="KWD")
        db.session.commit()
        assert db.session.get(Invoice, inv.id).balance_due == 0.0


# --- P1: idempotency belongs in the database ------------------------------

def test_the_same_processor_reference_cannot_be_recorded_twice(app, owner):
    """Two workers can both pass `has_credited` before either commits.

    A check-then-insert is not a guard; the unique constraint is.
    """
    from sqlalchemy.exc import IntegrityError

    with app.app_context():
        inv = invoice("USD", [(1, 1000)])
        inv.user_id = owner
        db.session.add(inv)
        inv.record_payment(400, source="stripe", external_id="cs_race")
        db.session.commit()
        invoice_id = inv.id

    with app.app_context():
        # the losing worker: it never saw the first commit
        db.session.add(Payment(invoice_id=invoice_id, amount=400.0,
                               currency="USD", source="stripe",
                               external_id="cs_race"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert len(inv.payments) == 1
        assert inv.amount_paid == 400.0


def test_manual_payments_carry_no_reference_and_are_not_constrained(app, owner):
    """Several cash payments on one invoice are legitimate. NULL is exempt."""
    with app.app_context():
        inv = invoice("USD", [(1, 1000)])
        inv.user_id = owner
        db.session.add(inv)
        inv.record_payment(100, source="manual")
        inv.record_payment(100, source="manual")
        inv.record_payment(100, source="manual")
        db.session.commit()
        assert len(db.session.get(Invoice, inv.id).payments) == 3
        assert db.session.get(Invoice, inv.id).amount_paid == 300.0


# --- P1: the backfill must survive two workers booting at once ------------

def test_the_backfill_cannot_double_even_without_the_not_in(app, owner):
    """The NOT IN makes a re-boot a no-op; the constraint is what makes a RACE
    safe. Simulated by running the insert twice with the NOT IN defeated.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    with app.app_context():
        inv = invoice("USD", [(1, 1000)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()
        inv.amount_paid = 400.0
        db.session.commit()

        _ensure_schema()
        assert len(db.session.get(Invoice, inv.id).payments) == 1

        # the second worker, mid-race: it read the table before the first
        # committed, so its NOT IN found nothing to exclude.
        raw = (
            "INSERT INTO payments "
            "(invoice_id, amount, currency, source, external_id, note, created_at) "
            "SELECT id, amount_paid, currency, 'migrated', "
            "'migrated:' || CAST(id AS TEXT), 'opening', created_at "
            "FROM invoices WHERE amount_paid > 0"
        )
        with pytest.raises(SQLAlchemyError):
            db.session.execute(text(raw))
            db.session.commit()
        db.session.rollback()

        inv = db.session.get(Invoice, inv.id)
        assert len(inv.payments) == 1, "the opening balance was not doubled"
        assert inv.amount_paid == 400.0


# --- second round of Codex findings --------------------------------------

@pytest.mark.parametrize(
    "code,because",
    [("HUF", "differently"), ("TWD", "differently"), ("MGA", "differently"),
     ("ISK", "no decimal places"), ("JPY", "no decimal places"),
     ("KWD", "three decimal places"), ("VND", "no decimal places")],
)
def test_only_currencies_we_can_convert_with_confidence_are_chargeable(code, because):
    """An ALLOWLIST, and the polarity is the point.

    The first attempt at this was a DENYLIST of the four currencies I had
    noticed were disputed — which assumed I had found them all. Three review
    rounds proved otherwise: HUF went on that list through a misreading (its
    zero-decimal rule is documented for PAYOUTS, not charges) and ISK was
    missing. For a number that goes on somebody's card, "allow unless known
    bad" is the wrong default.

    Chargeable now means: two decimal places in ISO 4217, which is Stripe's
    own default, with no recorded departure. Everything else waits for
    evidence — including JPY, which this app has in fact never charged
    correctly, so there is no history to lean on.
    """
    from stripe_utils import UnsupportedCurrency, guard_chargeable, is_chargeable

    assert is_chargeable(code) is False
    with pytest.raises(UnsupportedCurrency) as raised:
        guard_chargeable(code)
    assert code in str(raised.value)
    assert because in str(raised.value)
    assert "invoice itself is unaffected" in str(raised.value)


@pytest.mark.parametrize("code", ["HUF", "TWD", "MGA", "ISK", "JPY", "KWD"])
def test_a_currency_we_cannot_charge_can_still_be_invoiced(code):
    """Only the pay-online button is withheld. Refusing to PRINT an invoice
    because we cannot card it would be absurd, and the arithmetic for these is
    tested elsewhere in this file and correct."""
    inv = invoice(code, [(2, 750)])
    assert inv.total == 1500.0
    assert format_money(inv.total, code)


def test_the_ordinary_currencies_are_chargeable():
    from stripe_utils import guard_chargeable, is_chargeable

    for code in ["USD", "EUR", "GBP", "CAD", "AUD", "INR", "CHF", "CNY",
                 "BRL", "ZAR", "MXN", "SGD", "NZD", "SEK", "NOK", "PLN"]:
        assert is_chargeable(code), code
        guard_chargeable(code)   # must not raise


def test_the_allowlist_is_the_two_decimal_currencies_minus_the_disputed():
    """Stated as a property so the count cannot drift silently."""
    from currencies import CURRENCIES, decimals_for
    from stripe_utils import DIVERGENT_FROM_ISO, is_chargeable

    for code in CURRENCIES:
        expected = decimals_for(code) == 2 and code.lower() not in DIVERGENT_FROM_ISO
        assert is_chargeable(code) is expected, code
    assert sum(1 for c in CURRENCIES if is_chargeable(c)) > 100, (
        "the ordinary path must stay wide — this is not meant to be a short list"
    )


def test_currencies_where_stripe_and_iso_agree_are_untouched():
    for code, amount, expected in [
        ("USD", 15.00, 1500), ("JPY", 1500, 1500),
        ("KWD", 1.5, 1500), ("EUR", 15.00, 1500),
    ]:
        assert to_minor_units(amount, code) == expected


def test_marking_paid_uses_the_invoices_precision_for_the_shortfall(app, owner):
    """A KWD 1.235 invoice computed a 1.24 shortfall and stored 1.240,
    overstating the ledger by half a fils and hiding an overpayment."""
    with app.app_context():
        inv = invoice("KWD", [(1, 1.235)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()
        invoice_id = inv.id

    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    client.post(f"/invoice/{invoice_id}/mark-paid")

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert inv.amount_paid == 1.235, "not 1.240"
        assert inv.balance_due == 0.0
        assert inv.payments[0].amount == 1.235


def test_an_edit_without_a_currency_field_keeps_the_invoices_currency(app, owner):
    """The owner's Edit form has no currency box, so it submits None — which
    used to mean "use the account default" and silently re-denominated any
    invoice saved from the generator in anything else.
    """
    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    client.post("/generator/save", data={
        "from_name": "Bramble & Finch", "bill_to_name": "Northwind",
        "invoice_number": "INV-JPY", "invoice_date": "2026-09-06",
        "payment_terms": "Net 14", "currency": "JPY", "design": "classic-navy",
        "item_description": ["Work"], "item_quantity": ["1"],
        "item_rate": ["150000"], "tax": "0", "discount": "0", "shipping": "0",
    })
    with app.app_context():
        inv = db.session.query(Invoice).filter_by(invoice_number="INV-JPY").one()
        assert inv.currency == "JPY"
        invoice_id = inv.id

    # an ordinary edit through the owner's form, which carries no currency
    client.post(f"/invoice/{invoice_id}", data={
        "invoice_number": "INV-JPY", "bill_to": "Northwind",
        "invoice_date": "2026-09-06", "payment_terms": "Net 14",
        "tax": "0", "discount": "0", "shipping": "0",
        "item_description": ["Work, revised"], "item_quantity": ["1"],
        "item_rate": ["160000"],
    })
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert inv.currency == "JPY", "the account default must not overwrite it"
        assert inv.total == 160000.0


def test_the_cache_is_recomputed_from_the_table_not_the_collection(app, owner):
    """Two DIFFERENT Checkout sessions can settle one invoice at once — each
    visit to /pay makes its own — so the unique constraint does not cover it.
    Both inserts are legitimate; the danger is each worker writing a cache
    computed from only the rows it happened to see.
    """
    with app.app_context():
        inv = invoice("USD", [(1, 1100)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()
        invoice_id = inv.id

    with app.app_context():
        # a row inserted by "another worker", invisible to the next session's
        # identity map until it reloads
        db.session.add(Payment(invoice_id=invoice_id, amount=400.0,
                               currency="USD", source="stripe",
                               external_id="cs_worker_a"))
        db.session.commit()

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        inv.record_payment(700, source="stripe", external_id="cs_worker_b")
        inv.resync_amount_paid_from_db()
        db.session.commit()

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert inv.amount_paid == 1100.0, "both payments, not just the last"
        assert inv.ledger_total == 1100.0
        assert inv.balance_due == 0.0


# --- third round ----------------------------------------------------------

def test_a_single_currency_account_is_labelled_with_that_currency(app, owner):
    """A USD-default account whose only invoice is in yen showed a ¥10,000
    receivable as "$10,000.00" — the figure was right and the label was not,
    which is the worse of the two."""
    with app.app_context():
        inv = invoice("JPY", [(1, 10000)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()

    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    page = client.get("/history").get_data(as_text=True)
    assert "¥10,000" in page
    assert "$10,000" not in page, "labelled with the account default"


def test_a_mixed_account_reports_each_currency_apart(app, owner):
    with app.app_context():
        for code, rate in [("USD", 100), ("JPY", 10000)]:
            inv = invoice(code, [(1, rate)])
            inv.user_id = owner
            inv.invoice_number = f"INV-{code}"
            db.session.add(inv)
        db.session.commit()

    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    page = client.get("/history").get_data(as_text=True)
    assert "$100" in page and "¥10,000" in page
    assert "$10,100" not in page, "the two were added together"


def test_the_csv_export_keeps_the_invoices_precision(app, owner):
    """The one artifact an accountant imports must not disagree with the PDF."""
    with app.app_context():
        inv = invoice("KWD", [(1, 1.235)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()

    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    csv_text = client.get("/history/export.csv").get_data(as_text=True)
    assert "1.235" in csv_text
    assert "1.24" not in csv_text, "truncated to two places"


def test_the_edit_form_speaks_the_invoices_currency(app, owner):
    with app.app_context():
        inv = invoice("JPY", [(1, 150000)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()
        invoice_id = inv.id

    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    page = client.get(f"/invoice/{invoice_id}/edit").get_data(as_text=True)
    assert "Currency: JPY" in page, "the page showed the account default"
    assert "const DP = 0" in page, "and calculated at two places"


def test_marking_paid_counts_a_payment_another_session_recorded(app, owner):
    """The owner's route resyncs from the table, so a card payment that landed
    underneath them is counted rather than overwritten."""
    with app.app_context():
        inv = invoice("USD", [(1, 1000)])
        inv.user_id = owner
        db.session.add(inv)
        db.session.commit()
        invoice_id = inv.id

    with app.app_context():
        db.session.add(Payment(invoice_id=invoice_id, amount=400.0,
                               currency="USD", source="stripe",
                               external_id="cs_underneath"))
        db.session.commit()

    client = app.test_client()
    client.post("/login", data={"email": OWNER_EMAIL,
                                "password": "correct-horse-staple"})
    client.post(f"/invoice/{invoice_id}/mark-paid")

    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert inv.amount_paid == 1000.0
        assert inv.confirmed_paid == 400.0, "the card payment survived"
        assert inv.manual_paid == 600.0, "and only the shortfall was added"
        assert inv.amount_paid == inv.ledger_total
