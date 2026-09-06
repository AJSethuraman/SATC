"""Where a "pay online" invitation may appear, and where it may not.

An invoice can carry a pay button in three places: the public web page, the
PDF, and the email. The rule is one rule — offer it only where pressing it
would work — and it was implemented in one place. `public_invoice` asked
whether the owner had Stripe AND whether the currency was chargeable;
`download_pdf`, `email_invoice` and `public_pdf` asked neither, so the same
invoice said "Pay online in seconds" on paper and "no online payment" on the
web, and a client in a refused currency was invited to pay and then declined.

Inviting a payment and failing is worse than never offering, which is the
whole reason `stripe_utils.guard_chargeable` exists.

Raised by Codex on PR #289, round five.
"""
import pytest

from config import Config
from app import create_app
from models import Invoice, LineItem, User, db

OWNER_EMAIL = "amara.okonkwo@bramblefinch.example"
OWNER_PASSWORD = "correct-horse-staple"
MARKER = "Pay online in seconds"


@pytest.fixture
def app(tmp_path):
    class PayConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/pay-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        REQUIRE_EMAIL_VERIFICATION = "never"
        APP_BASE_URL = "https://invoicer.example"

    return create_app(PayConfig)


def make_owner(app, *, stripe_ready=True):
    with app.app_context():
        user = User(
            email=OWNER_EMAIL,
            business_name="Bramble & Finch Consulting",
            business_email=OWNER_EMAIL,
            business_address="4 Tinder Lane\nPortsend, ZZ 00000",
            default_currency="USD",
            email_verified=True,
            stripe_account_id="acct_test_123" if stripe_ready else None,
            stripe_charges_enabled=bool(stripe_ready),
        )
        user.set_password(OWNER_PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user.id


def make_invoice(app, owner_id, currency):
    with app.app_context():
        invoice = Invoice(
            user_id=owner_id,
            invoice_number=f"INV-{currency}",
            from_info="Bramble & Finch Consulting\n4 Tinder Lane",
            bill_to="Northwind Traders LLC\n9 Harbor Way",
            client_email="ap@northwind.example",
            currency=currency,
            status="Sent",
            amount_paid=0.0,
            tax_is_percent=True,
            discount_is_percent=True,
        )
        invoice.items.append(
            LineItem(description="Return", quantity=1, rate=1000)
        )
        db.session.add(invoice)
        db.session.commit()
        return invoice.id


def signed_in(app):
    c = app.test_client()
    c.post("/login", data={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    return c


def pdf_text(payload):
    pypdf = pytest.importorskip("pypdf")
    import io as _io

    reader = pypdf.PdfReader(_io.BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


# --- the PDF the owner downloads ------------------------------------------

def test_the_downloaded_pdf_invites_payment_in_a_currency_we_can_charge(app):
    owner_id = make_owner(app)
    invoice_id = make_invoice(app, owner_id, "USD")
    r = signed_in(app).get(f"/invoice/{invoice_id}/pdf")
    assert r.status_code == 200
    assert MARKER in pdf_text(r.data)


def test_the_downloaded_pdf_stays_quiet_in_a_currency_we_refuse(app):
    """JPY is zero-decimal: `is_chargeable` refuses it, so the paper must too."""
    owner_id = make_owner(app)
    invoice_id = make_invoice(app, owner_id, "JPY")
    r = signed_in(app).get(f"/invoice/{invoice_id}/pdf")
    assert r.status_code == 200
    assert MARKER not in pdf_text(r.data)


def test_the_downloaded_pdf_stays_quiet_when_the_owner_has_no_stripe(app):
    owner_id = make_owner(app, stripe_ready=False)
    invoice_id = make_invoice(app, owner_id, "USD")
    r = signed_in(app).get(f"/invoice/{invoice_id}/pdf")
    assert r.status_code == 200
    assert MARKER not in pdf_text(r.data)


# --- the page and the PDF the client sees ---------------------------------

def public_token(app, invoice_id):
    from app import make_token

    # `make_token` signs with the app's secret, so it needs the app current.
    with app.app_context():
        return make_token(invoice_id, salt="invoice-public")


@pytest.mark.parametrize(
    "currency, invited", [("USD", True), ("JPY", False)],
)
def test_the_public_page_and_the_public_pdf_agree(app, currency, invited):
    """These two disagreed, which is the shape of the bug: same invoice, one
    surface offering a payment the other knew would be refused."""
    owner_id = make_owner(app)
    invoice_id = make_invoice(app, owner_id, currency)
    token = public_token(app, invoice_id)
    client = app.test_client()

    page = client.get(f"/i/{token}").get_data(as_text=True)
    pdf = pdf_text(client.get(f"/i/{token}/pdf").data)

    # The page's button is a form posting to `public_pay`; the PDF's is the
    # "Pay online in seconds" block. Both, or neither — never one of them.
    assert ("/pay" in page) is invited
    assert (MARKER in pdf) is invited


# --- the email ------------------------------------------------------------

def test_the_email_does_not_offer_a_payment_in_a_refused_currency(
    app, monkeypatch
):
    import email_utils

    sent = {}

    def capture(config, to_email, invoice, path, **kwargs):
        sent["html"] = kwargs.get("html_body") or ""

    monkeypatch.setattr(email_utils, "send_invoice_email", capture)

    owner_id = make_owner(app)
    refused = make_invoice(app, owner_id, "JPY")
    allowed = make_invoice(app, owner_id, "USD")
    client = signed_in(app)

    client.post(f"/invoice/{refused}/email", data={"to_email": "a@b.example"})
    assert "Pay" not in sent["html"] or "View invoice" in sent["html"]
    assert "pay securely online" not in sent["html"].lower()

    client.post(f"/invoice/{allowed}/email", data={"to_email": "a@b.example"})
    assert "pay securely online" in sent["html"].lower()
