#!/usr/bin/env python3
"""Drive the whole of Invoicer, for real, and prove each step on the artifact.

    python exercise.py                 # everything
    python exercise.py --only money    # one chapter
    python exercise.py --list          # what the chapters are

THIS IS NOT THE TEST SUITE AND NOT A SECOND ONE. ``pytest`` asserts
properties on fixtures: that a total equals its parts, that a bad signature is
refused, that user B gets a 404. It produces nothing anybody looks at.

This runs the business. Two accounts are signed up through the signup form,
log in through the login form, fill in a business profile, raise invoices,
edit them, email them, take payments through a signed Stripe webhook, chase
what is overdue, export the book to CSV and delete what they should not have
raised — every step over real HTTP, with CSRF live, through the same routes a
browser hits. Then it OPENS what came out: every PDF is parsed for its text
AND rasterised to check ink is actually on the page, and the page the paying
client sees is loaded in Chromium against a live server.

WHY THE OPENING MATTERS (docs/SOFTWARE-TENETS.md S1, S16). The sister harness
in ``client-documents/exercise.py`` once reported "190 documents produced, 0
surprises" having read every one of them as a string. Every one opened as
unstyled plain text. A PDF that renders blank, or that drops the total, has
the same shape: the bytes are there, the file is a valid PDF, and the client
cannot see what they owe. So "produced" here means opened, and the total in
the PDF is compared against the total in the database.

THREE VERDICTS, and the difference is the point (S27):

  ok      the thing was checked and it held.
  FAIL    a surprise. The harness exits non-zero. Read it.
  KNOWN   a real defect, reproduced deliberately, written up in
          docs/invoicer-scenarios.md with a reason it was not fixed. These do
          NOT fail the run — they are not surprises. But each is a tripwire:
          if the behaviour changes, even to something better, the check goes
          FAIL and tells you to update the document. A known problem that
          quietly stops being known is how a document starts lying.

Every check prints what it compared, and the summary prints the denominator
(S2): a green run that examined nothing is worse than a red one.

Nothing here touches the network, a real database, or anyone's money. The
database is a throwaway SQLite file, Stripe Checkout is a local fake, webhook
payloads are signed with a throwaway secret so the REAL verifier runs against
them, and SMTP is a fake transport so ``email_utils`` builds a real MIME
message that we then read. Every person, company, address and amount below is
invented. Output goes to ``out/`` which is gitignored (S22.4) — everything
written there is invoice-shaped.
"""

from __future__ import annotations

import argparse
import csv as csvmod
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import smtplib
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# The app reads os.environ at import time (config.Config is evaluated on the
# first `import config`), so neutralise the developer's .env BEFORE importing
# anything from the app. Without this a run on a workstation with a populated
# .env would point at a real database and real Stripe/SMTP credentials.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["FLASK_SECRET_KEY"] = "exercise-harness-not-a-real-key"
os.environ["APP_ENV"] = "development"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "never"
for _blank in (
    "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET",
    "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "FROM_EMAIL", "SENTRY_DSN",
):
    os.environ[_blank] = ""
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["PLATFORM_FEE_PERCENT"] = "0"
os.environ["PLATFORM_FEE_FLAT_CENTS"] = "0"

import email_utils                                          # noqa: E402
import stripe_utils                                         # noqa: E402
from app import create_app, make_token                      # noqa: E402
from config import Config                                   # noqa: E402
from helpers import format_money                            # noqa: E402
from models import Invoice, User, db                        # noqa: E402


# A stand-in for a Stripe webhook signing secret. Real ones begin "whsec_";
# this exists only so the real signature verifier has something to verify.
WEBHOOK_SECRET = "whsec_exercise_harness_not_a_real_secret"

# ── the people ────────────────────────────────────────────────────────────
# INVENTED, every one, and deliberately not the names the pytest suite uses so
# a stray record can never be mistaken for a fixture from the other side.
OWNER_A = {
    "email": "tamsin.vane@halloway-vance.example",
    "password": "quiet-ledger-forty-two",
    "business_name": "Halloway & Vance Bookkeeping",
    "business_address": "17 Cordwainer Street\nAshgrove, ZZ 00000",
    "tax_id": "ZZ-0000000",
    "ip": "203.0.113.11",
}
OWNER_B = {
    "email": "oren.mbeki@kestreldata.example",
    "password": "kestrel-over-the-weir",
    "business_name": "Kestrel Data Works",
    "business_address": "3 Weirbank Yard\nAshgrove, ZZ 00000",
    "tax_id": "ZZ-0000001",
    "ip": "203.0.113.22",
}
CLIENT_DAIRY = "Ravensworth Dairy Co-operative\n9 Mill Lane\nRavensworth"
CLIENT_MARINE = "Pellham Marine Supply\n2 Quay Street\nPellham"
CLIENT_JOINERY = "Ironbridge Joinery\n14 Forge Row\nIronbridge"
CLIENT_CHAMBERS = "Sable Court Chambers\n1 Sable Court\nAshgrove"


# ══════════════════════════════════════════════════════════════════════════
# Recording what happened
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class Row:
    chapter: str
    check: str
    verdict: str          # ok | FAIL | KNOWN | skip
    detail: str = ""
    compared: int = 1


@dataclass
class Report:
    rows: list[Row] = field(default_factory=list)
    chapter: str = "-"
    artifacts: list[str] = field(default_factory=list)

    # -- recording ---------------------------------------------------------
    def ok(self, check, detail="", compared=1):
        self.rows.append(Row(self.chapter, check, "ok", detail, compared))

    def fail(self, check, detail="", compared=1):
        self.rows.append(Row(self.chapter, check, "FAIL", detail, compared))

    def skip(self, check, detail="", compared=0):
        self.rows.append(Row(self.chapter, check, "skip", detail, compared))

    def check(self, name, condition, detail="", compared=1):
        """Assert something and record it either way. Returns the condition."""
        if condition:
            self.ok(name, detail, compared)
        else:
            self.fail(name, detail, compared)
        return bool(condition)

    def equal(self, name, got, want, note="", compared=1):
        same = got == want
        detail = f"got {got!r} want {want!r}" if not same else f"{got!r}"
        if note:
            detail = f"{detail} — {note}"
        return self.check(name, same, detail, compared)

    def tripwire(self, name, still_broken, detail):
        """Record a defect that is known, documented, and deliberately unfixed.

        KNOWN does not fail the run. But if the behaviour ever changes the
        tripwire goes FAIL, because docs/invoicer-scenarios.md now describes
        something that is no longer true — and a stale list of known problems
        is worse than no list, since people stop reading it.
        """
        if still_broken:
            self.rows.append(Row(self.chapter, name, "KNOWN", detail))
        else:
            self.rows.append(Row(
                self.chapter, name, "FAIL",
                "this KNOWN behaviour has CHANGED. If you fixed it, delete "
                "this tripwire and move the entry out of the 'still wrong' "
                f"list in docs/invoicer-scenarios.md. Expected: {detail}",
            ))

    def crash(self, check, exc):
        self.fail(check, f"{type(exc).__name__}: {exc}")

    # -- reading -----------------------------------------------------------
    @property
    def failures(self):
        return [r for r in self.rows if r.verdict == "FAIL"]

    @property
    def compared_total(self):
        return sum(r.compared for r in self.rows)


R = Report()


# ══════════════════════════════════════════════════════════════════════════
# A browser
# ══════════════════════════════════════════════════════════════════════════
class Browser:
    """One person's browser session: cookies, an IP, and a CSRF token.

    CSRF protection is left ON for this run. That costs a token fetch per
    session and buys the thing a test client with ``WTF_CSRF_ENABLED = False``
    can never tell you: that the forms a person actually submits still work
    with the protection in place, and that a post without a token is refused.

    The IP is distinct per person because Flask-Limiter keys on the remote
    address. It is what lets the harness prove the login rate limit fires
    without locking its own sessions out for the rest of the minute.
    """

    def __init__(self, app, ip, label):
        self.app = app
        self.client = app.test_client()
        self.env = {"REMOTE_ADDR": ip}
        self.label = label
        self._csrf = None

    # -- csrf --------------------------------------------------------------
    def csrf(self, refresh=False):
        if self._csrf and not refresh:
            return self._csrf
        for path in ("/login", "/account", "/signup"):
            page = self.client.get(path, environ_base=self.env)
            if page.status_code != 200:
                continue
            found = re.search(
                r'name="csrf_token"\s+value="([^"]+)"',
                page.get_data(as_text=True),
            )
            if found:
                self._csrf = found.group(1)
                return self._csrf
        raise RuntimeError(
            f"{self.label}: no CSRF token on /login, /account or /signup — "
            "the harness cannot submit a form"
        )

    # -- verbs -------------------------------------------------------------
    def get(self, path, **kw):
        return self.client.get(path, environ_base=self.env, **kw)

    def post(self, path, data=None, with_csrf=True, **kw):
        payload = dict(data or {})
        if with_csrf:
            payload["csrf_token"] = self.csrf()
        return self.client.post(
            path, data=payload, environ_base=self.env, **kw
        )

    def post_raw(self, path, **kw):
        """POST without touching the body (for the CSRF-refusal check)."""
        return self.client.post(path, environ_base=self.env, **kw)

    def json(self, method, path, api_key=None, **kw):
        headers = kw.pop("headers", {})
        if api_key:
            headers["X-API-Key"] = api_key
        return getattr(self.client, method)(
            path, headers=headers, environ_base=self.env, **kw
        )

    # -- flows -------------------------------------------------------------
    def login(self, email, password, next_url=None):
        path = "/login" + (f"?next={next_url}" if next_url else "")
        response = self.post(
            path, {"email": email, "password": password}
        )
        self.csrf(refresh=True)
        return response

    def logout(self):
        response = self.post("/logout")
        self.csrf(refresh=True)
        return response


# ══════════════════════════════════════════════════════════════════════════
# Fakes: Stripe Checkout and the SMTP transport
# ══════════════════════════════════════════════════════════════════════════
class FakeCheckout:
    """Stand in for stripe.checkout.Session.create and record what was asked.

    The number this records is the number that would actually leave the
    client's bank account, so it is worth asserting on directly.
    """

    def __init__(self):
        self.sessions = []
        self._real = stripe_utils.create_checkout_session

    def install(self):
        harness = self

        class Session:
            def __init__(self, invoice, amount, currency):
                self.id = f"cs_exercise_{len(harness.sessions) + 1:03d}"
                self.url = f"https://checkout.stripe.example/{self.id}"
                self.amount = amount
                self.currency = currency
                self.invoice_id = invoice.id
                self.invoice_number = invoice.invoice_number

        def create(invoice, secret_key, base_url, connected_account_id,
                   config=None, success_url=None, cancel_url=None):
            if not secret_key:
                raise RuntimeError("STRIPE_SECRET_KEY is not configured.")
            if not connected_account_id:
                raise RuntimeError("Connect a Stripe account first.")
            amount = invoice.balance_due
            if amount <= 0:
                raise ValueError("Invoice has no positive balance due.")
            session = Session(invoice, amount, (invoice.currency or "usd").lower())
            harness.sessions.append(session)
            return session

        stripe_utils.create_checkout_session = create
        return self

    def last(self):
        return self.sessions[-1] if self.sessions else None


class FakeSMTP:
    """A transport that captures the message instead of sending it.

    Patched at ``smtplib`` rather than at ``email_utils.send_invoice_email``,
    so the REAL sender assembly runs: the real subject line, the real
    plain-text alternative, the real rendered HTML alternative and the real
    PDF attachment all get built, and the harness reads what a client would
    have received. Stubbing one layer higher would have proved only that the
    function was called.
    """

    outbox: list = []

    def __init__(self, host, port=0, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, *a, **kw):
        pass

    def login(self, username, password):
        pass

    def send_message(self, msg):
        FakeSMTP.outbox.append(msg)
        return {}


def install_fake_smtp():
    FakeSMTP.outbox = []
    smtplib.SMTP = FakeSMTP
    smtplib.SMTP_SSL = FakeSMTP


# ══════════════════════════════════════════════════════════════════════════
# Money, computed independently of the application
# ══════════════════════════════════════════════════════════════════════════
def cents(value) -> Decimal:
    """Exact decimal, rounded half-up to 2dp — how an invoice is meant to add.

    Deliberately NOT the application's arithmetic. The app rounds float
    products with Python's ``round``, which is round-half-to-EVEN and works on
    binary floats that cannot hold 0.125 or 2.675 exactly. Recomputing the
    expected total with the app's own method would only prove the app agrees
    with itself, which is the shape of every bug in SOFTWARE-TENETS.md part 0.
    """
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def expected_totals(lines, tax_pct=0, discount_pct=0, discount_flat=None,
                    shipping=0):
    """Work out what the invoice should say, in exact decimal arithmetic."""
    amounts = [cents(Decimal(str(q)) * Decimal(str(r))) for q, r in lines]
    subtotal = cents(sum(amounts, Decimal("0")))
    if discount_flat is not None:
        discount = cents(discount_flat)
    else:
        discount = cents(subtotal * Decimal(str(discount_pct)) / Decimal(100))
    base = cents(subtotal - discount)
    tax = cents(base * Decimal(str(tax_pct)) / Decimal(100))
    total = cents(base + tax + cents(shipping))
    return {
        "amounts": amounts, "subtotal": subtotal, "discount": discount,
        "base": base, "tax": tax, "total": total,
    }


@dataclass
class Snapshot:
    """An invoice read out while its session is open, safe to assert on later."""
    id: int = 0
    number: str = ""
    status: str = ""
    display_status: str = ""
    currency: str = "USD"
    bill_to: str = ""
    client_name: str = ""
    client_email: str = ""
    subtotal: float = 0.0
    discount_amount: float = 0.0
    taxable_base: float = 0.0
    tax_amount: float = 0.0
    tax_value: float = 0.0
    discount_value: float = 0.0
    shipping: float = 0.0
    total: float = 0.0
    amount_paid: float = 0.0
    balance_due: float = 0.0
    is_overdue: bool = False
    is_partial: bool = False
    paid_session_ids: str = ""
    line_amounts: list = field(default_factory=list)
    line_descriptions: list = field(default_factory=list)
    due_date: object = None
    public_token: str = ""


def snapshot(invoice) -> Snapshot:
    return Snapshot(
        id=invoice.id, number=invoice.invoice_number, status=invoice.status,
        display_status=invoice.display_status, currency=invoice.currency,
        bill_to=invoice.bill_to or "", client_name=invoice.client_name,
        client_email=invoice.client_email or "",
        subtotal=invoice.subtotal, discount_amount=invoice.discount_amount,
        taxable_base=invoice.taxable_base, tax_amount=invoice.tax_amount,
        tax_value=invoice.tax_value or 0.0,
        discount_value=invoice.discount_value or 0.0,
        shipping=invoice.shipping or 0.0, total=invoice.total,
        amount_paid=invoice.amount_paid or 0.0, balance_due=invoice.balance_due,
        is_overdue=invoice.is_overdue, is_partial=invoice.is_partial,
        paid_session_ids=invoice.paid_session_ids or "",
        line_amounts=[i.amount for i in invoice.items],
        line_descriptions=[i.description for i in invoice.items],
        due_date=invoice.due_date,
        public_token=make_token(invoice.id, salt="invoice-public"),
    )


def read(app, number=None, invoice_id=None) -> Snapshot | None:
    with app.app_context():
        query = Invoice.query
        invoice = (
            db.session.get(Invoice, invoice_id) if invoice_id
            else query.filter_by(invoice_number=number).first()
        )
        return snapshot(invoice) if invoice is not None else None


def count_invoices(app, user_id=None) -> int:
    with app.app_context():
        query = Invoice.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.count()


# ══════════════════════════════════════════════════════════════════════════
# Opening the artifacts
# ══════════════════════════════════════════════════════════════════════════
def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def pdf_ink(path: Path):
    """Rasterise page 1 and return (pages, fraction of non-white pixels).

    Text extraction proves the text objects exist in the content stream. It
    does NOT prove anything is visible: white-on-white, a zero-height box, a
    clipped region and a failed font all extract perfectly and print blank.
    So the page is actually drawn and the ink is counted. A page under ~1%
    coverage is not an invoice.
    """
    import fitz  # PyMuPDF

    document = fitz.open(str(path))
    pixmap = document[0].get_pixmap(dpi=72)
    dark = bytes(1 if v < 250 else 0 for v in range(256))
    non_white = pixmap.samples.translate(dark).count(1) / max(pixmap.n, 1)
    coverage = non_white / max(pixmap.width * pixmap.height, 1)
    pages = document.page_count
    document.close()
    return pages, coverage


NBSP = " "
MINUS = "−"


def normalise(text: str) -> str:
    return (
        text.replace(NBSP, " ").replace(MINUS, "-").replace("‑", "-")
    )


def verify_pdf(path: Path, inv: Snapshot) -> list[str]:
    """Open one PDF and say what is wrong with it. Empty list is the good answer.

    A non-trivial byte length is not evidence: xhtml2pdf and WeasyPrint both
    emit a perfectly well-formed multi-kilobyte PDF for a page with nothing on
    it. What is checked here is what the client needs to be able to read —
    who it is from, which invoice it is, and what the total is — plus that the
    total on the page is the same number as the total in the database.
    """
    problems = []
    if not path.exists():
        return [f"{path.name}: not written at all"]
    if path.stat().st_size < 1000:
        problems.append(f"{path.name}: {path.stat().st_size} bytes")

    try:
        text = normalise(pdf_text(path))
    except Exception as exc:                                  # noqa: BLE001
        return [f"{path.name}: could not be parsed as a PDF — "
                f"{type(exc).__name__}: {exc}"]

    flat = re.sub(r"\s+", " ", text)
    if inv.number not in flat:
        problems.append(f"{path.name}: invoice number {inv.number!r} is not "
                        "on the page")
    if inv.client_name and inv.client_name not in flat:
        problems.append(f"{path.name}: client {inv.client_name!r} is not on "
                        "the page")

    # A money figure as the PDF prints it: an optional symbol or currency
    # word ("CHF 1,000.00" has a space in it), then the digits.
    money = r"((?:[A-Z]{2,4} )?[^\s\d]{0,2}-?[\d,]+\.\d\d)"

    want_total = normalise(format_money(inv.total, inv.currency))
    if want_total not in flat:
        money_like = sorted(set(re.findall(money, flat)))
        problems.append(
            f"{path.name}: the total {want_total!r} does not appear; "
            f"amounts on the page are {money_like[:10]}"
        )
    else:
        # Present is not enough — it has to be the number *labelled* Total.
        labelled = re.search(r"Total\s+" + money, flat)
        if not labelled:
            problems.append(f"{path.name}: no line labelled 'Total'")
        elif labelled.group(1) != want_total:
            problems.append(
                f"{path.name}: the PDF says Total {labelled.group(1)} but the "
                f"database says {want_total}"
            )

    balance = re.search(r"Balance due\s+" + money, flat)
    want_balance = normalise(format_money(inv.balance_due, inv.currency))
    if balance and balance.group(1) != want_balance:
        problems.append(
            f"{path.name}: the PDF says Balance due {balance.group(1)} but "
            f"the database says {want_balance}"
        )

    for leak in ("{{", "}}", "{%", "None", "Undefined"):
        if leak in flat:
            problems.append(f"{path.name}: unrendered template marker {leak!r}")

    try:
        pages, coverage = pdf_ink(path)
    except Exception as exc:                                  # noqa: BLE001
        problems.append(f"{path.name}: could not be rasterised — "
                        f"{type(exc).__name__}: {exc}")
    else:
        if pages < 1:
            problems.append(f"{path.name}: no pages")
        elif coverage < 0.01:
            problems.append(
                f"{path.name}: page 1 is effectively blank — only "
                f"{coverage * 100:.2f}% of it has ink on it"
            )
    return problems


# ══════════════════════════════════════════════════════════════════════════
# A live server, for the page the client actually opens
# ══════════════════════════════════════════════════════════════════════════
class LiveServer:
    def __init__(self, app):
        from werkzeug.serving import make_server

        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)

    def __enter__(self):
        self.thread.start()
        time.sleep(0.3)
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.thread.join(timeout=5)
        return False

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"


# ══════════════════════════════════════════════════════════════════════════
# Stripe webhook plumbing (the real verifier, a local signature)
# ══════════════════════════════════════════════════════════════════════════
def sign(payload: bytes, secret=WEBHOOK_SECRET, timestamp=None) -> str:
    timestamp = timestamp or int(time.time())
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def checkout_event(invoice_id, session_id, amount_cents, currency="usd",
                   account=None, payment_status="paid",
                   event_type="checkout.session.completed"):
    event = {
        "id": f"evt_{session_id}",
        "type": event_type,
        "data": {"object": {
            "id": session_id,
            "object": "checkout.session",
            "amount_total": amount_cents,
            "currency": currency,
            "payment_status": payment_status,
            "metadata": {"invoice_id": str(invoice_id)},
        }},
    }
    if account:
        event["account"] = account
    return event


def deliver(app, event, secret=WEBHOOK_SECRET, timestamp=None,
            signature=None, body=None):
    payload = body if body is not None else json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["Stripe-Signature"] = signature
    elif secret is not None:
        headers["Stripe-Signature"] = sign(payload, secret, timestamp)
    return app.test_client().post(
        "/webhook/stripe", data=payload, headers=headers,
        environ_base={"REMOTE_ADDR": "198.51.100.7"},
    )


# ══════════════════════════════════════════════════════════════════════════
# The world
# ══════════════════════════════════════════════════════════════════════════
class World:
    """Everything one run needs: the app, the sessions, the fakes, the output."""

    def __init__(self, out: Path):
        self.out = out
        self.pdf_dir = out / "pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        stripe_account_a = "acct_exercise_halloway"

        class HarnessConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{out / 'exercise.db'}"
            INVOICES_DIR = self.pdf_dir
            SECRET_KEY = "exercise-harness-not-a-real-key"
            ENV = "development"
            TESTING = True
            # CSRF ON, rate limits ON — see Browser.
            WTF_CSRF_ENABLED = True
            RATELIMIT_ENABLED = True
            APP_BASE_URL = "http://localhost:5000"
            REQUIRE_EMAIL_VERIFICATION = "never"
            STRIPE_SECRET_KEY = "sk_test_exercise_not_a_real_key"
            STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
            SMTP_HOST = "smtp.exercise.invalid"
            SMTP_PORT = 587
            SMTP_USERNAME = "harness"
            SMTP_PASSWORD = "harness"
            FROM_EMAIL = "billing@invoicer.example"

        db_file = out / "exercise.db"
        if db_file.exists():
            db_file.unlink()
        self.app = create_app(HarnessConfig)
        self.stripe = FakeCheckout().install()
        install_fake_smtp()

        self.a = Browser(self.app, OWNER_A["ip"], "owner A")
        self.b = Browser(self.app, OWNER_B["ip"], "owner B")
        self.anon = Browser(self.app, "203.0.113.99", "anonymous")
        self.stripe_account_a = stripe_account_a
        self.stripe_account_b = "acct_exercise_kestrel"
        self.a_id = None
        self.b_id = None
        self.a_key = None
        self.b_key = None
        self.pdfs: list[tuple[Path, Snapshot]] = []

    # -- helpers -----------------------------------------------------------
    def api_key(self, email):
        with self.app.app_context():
            return User.query.filter_by(email=email).one().api_key

    def user_id(self, email):
        with self.app.app_context():
            return User.query.filter_by(email=email).one().id

    def connect_stripe(self, email, account_id):
        """Mark an account Stripe-connected without driving Stripe's OAuth."""
        with self.app.app_context():
            user = User.query.filter_by(email=email).one()
            user.stripe_account_id = account_id
            user.stripe_charges_enabled = True
            db.session.commit()

    def keep_pdf(self, response_or_path, inv: Snapshot, label: str) -> Path:
        """Save a produced PDF into out/ under a readable name, and remember it.

        Everything remembered here is opened in the artifacts chapter, so the
        harness can never report a PDF as produced without something having
        read it.
        """
        target = self.out / "produced" / f"{label}.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(response_or_path, Path):
            shutil.copyfile(response_or_path, target)
        else:
            target.write_bytes(response_or_path.data)
        self.pdfs.append((target, inv))
        return target


# ══════════════════════════════════════════════════════════════════════════
# Chapter 1 — accounts, sessions, and the front door
# ══════════════════════════════════════════════════════════════════════════
def chapter_accounts(w: World):
    R.chapter = "accounts"
    anon = w.anon

    R.equal("landing page serves an anonymous visitor",
            anon.get("/").status_code, 200)

    # Refusals first (S12): a refusal must write nothing.
    bad_signups = [
        ("short password", {"email": "too.short@ashgrove.example",
                            "password": "abc", "agree": "on"}),
        ("no terms accepted", {"email": "no.terms@ashgrove.example",
                               "password": "long-enough-password"}),
        ("malformed email", {"email": "not-an-email",
                             "password": "long-enough-password",
                             "agree": "on"}),
    ]
    for name, data in bad_signups:
        response = anon.post("/signup", data)
        R.equal(f"signup refused: {name}", response.status_code, 400)
    with w.app.app_context():
        R.equal("no account was created by any refused signup",
                User.query.count(), 0, compared=len(bad_signups))

    # A post with no CSRF token at all. The protection is live for this run,
    # so this is the real refusal and not a simulation of one.
    naked = anon.post_raw("/signup", data={
        "email": "csrfless@ashgrove.example", "password": "long-enough-pass",
        "agree": "on",
    })
    R.equal("a form post with no CSRF token is refused", naked.status_code, 400)

    # Now the real thing, through the real form.
    for owner, browser in ((OWNER_A, w.a), (OWNER_B, w.b)):
        response = browser.post("/signup", {
            "email": owner["email"], "password": owner["password"],
            "business_name": owner["business_name"], "agree": "on",
        })
        R.check(f"signup succeeded for {owner['business_name']}",
                response.status_code == 302,
                f"HTTP {response.status_code} -> {response.headers.get('Location')}")
        browser.csrf(refresh=True)

    with w.app.app_context():
        R.equal("two accounts exist", User.query.count(), 2, compared=2)
    w.a_id, w.b_id = w.user_id(OWNER_A["email"]), w.user_id(OWNER_B["email"])
    w.a_key, w.b_key = w.api_key(OWNER_A["email"]), w.api_key(OWNER_B["email"])
    R.check("the two accounts got different API keys", w.a_key != w.b_key,
            f"{w.a_key[:10]}… vs {w.b_key[:10]}…")

    duplicate = w.anon.post("/signup", {
        "email": OWNER_A["email"], "password": "another-long-password",
        "agree": "on",
    })
    R.equal("signing up again with the same email is refused",
            duplicate.status_code, 400)
    with w.app.app_context():
        R.equal("still two accounts", User.query.count(), 2)

    # Signup logs you in; log out so the login form itself gets exercised.
    w.a.logout()
    w.b.logout()

    wrong = w.a.login(OWNER_A["email"], "not-the-password")
    R.equal("login with the wrong password is refused", wrong.status_code, 401)
    R.check("...and leaves no session behind",
            w.a.get("/history").status_code == 302,
            "/history still redirects to login")

    unknown = w.a.login("nobody@ashgrove.example", OWNER_A["password"])
    R.equal("login for an account that does not exist is refused",
            unknown.status_code, 401,
            "and must not distinguish itself from a wrong password")

    good = w.a.login(OWNER_A["email"], OWNER_A["password"])
    R.equal("login with the right password succeeds", good.status_code, 302)
    R.equal("...and /history is now reachable", w.a.get("/history").status_code,
            200)
    w.b.login(OWNER_B["email"], OWNER_B["password"])

    # The open-redirect guard, from a third IP so the login limiter is fresh.
    redirects = Browser(w.app, "203.0.113.44", "redirect probe")
    off_site = [
        "//evil.example.com/steal", "/\\evil.example.com",
        "https://evil.example.com/steal", "http://evil.example.com",
    ]
    for target in off_site:
        redirects.logout()
        response = redirects.login(OWNER_A["email"], OWNER_A["password"],
                                   next_url=target)
        location = response.headers.get("Location", "")
        R.check(f"?next={target} does not leave the site",
                "evil.example.com" not in location, f"landed on {location!r}")
    redirects.logout()
    on_site = redirects.login(OWNER_A["email"], OWNER_A["password"],
                             next_url="/account")
    R.equal("a legitimate ?next is honoured",
            on_site.headers.get("Location"), "/account")

    # The login rate limit, on its own IP so nothing else is locked out.
    limited = Browser(w.app, "203.0.113.55", "rate-limit probe")
    codes = []
    for _ in range(14):
        codes.append(limited.login(OWNER_A["email"], "wrong-password").status_code)
    R.check("the login rate limit actually fires", 429 in codes,
            f"14 bad attempts from one IP returned {sorted(set(codes))}",
            compared=14)

    # Anonymous access to everything an owner sees.
    owner_only = [
        "/history", "/history/export.csv", "/account", "/new",
        "/invoice/1", "/invoice/1/edit", "/invoice/1/pdf", "/invoice/1/logo",
    ]
    leaked = []
    for path in owner_only:
        response = w.anon.get(path)
        location = response.headers.get("Location", "")
        if not (response.status_code == 302 and "/login" in location):
            leaked.append(f"{path} -> {response.status_code} {location}")
    R.check("every owner-facing page sends an anonymous visitor to login",
            not leaked, "; ".join(leaked) or f"{len(owner_only)} routes checked",
            compared=len(owner_only))

    w.a.logout()
    R.check("logout ends the session",
            w.a.get("/history").status_code == 302, "back to login")
    w.a.login(OWNER_A["email"], OWNER_A["password"])


# ══════════════════════════════════════════════════════════════════════════
# Chapter 2 — the business profile and invoice numbering
# ══════════════════════════════════════════════════════════════════════════
def chapter_profile(w: World):
    R.chapter = "profile"

    # A third account that signs up without a business name, to prove the
    # gate. A and B gave one on the signup form, so they are already past it.
    bare = Browser(w.app, "203.0.113.66", "profileless owner")
    bare.post("/signup", {
        "email": "no.profile@ashgrove.example",
        "password": "no-profile-yet-please", "agree": "on",
    })
    bare.csrf(refresh=True)
    before = bare.get("/new")
    R.check("raising an invoice before the business profile is set is refused",
            before.status_code == 302
            and "/account" in before.headers.get("Location", ""),
            f"HTTP {before.status_code} -> {before.headers.get('Location')}")
    blocked = bare.post("/invoices", {
        "invoice_number": "NOPROFILE-1", "bill_to": CLIENT_MARINE,
        "invoice_date": date.today().isoformat(),
        "tax": "0", "discount": "0", "shipping": "0",
        "item_description": ["Work"], "item_quantity": ["1"],
        "item_rate": ["100.00"],
    })
    R.check("...and so is posting the form directly past it",
            blocked.status_code == 302
            and "/account" in blocked.headers.get("Location", ""),
            f"HTTP {blocked.status_code} -> {blocked.headers.get('Location')}")
    with w.app.app_context():
        R.equal("...leaving no invoice behind",
                Invoice.query.filter_by(invoice_number="NOPROFILE-1").count(), 0)

    for owner, browser in ((OWNER_A, w.a), (OWNER_B, w.b)):
        response = browser.post("/account/business", {
            "business_name": owner["business_name"],
            "business_email": owner["email"],
            "business_address": owner["business_address"],
            "tax_id": owner["tax_id"],
            "default_currency": "USD",
            "default_terms": "Net 30",
        })
        R.equal(f"business profile saved for {owner['business_name']}",
                response.status_code, 302)

    form = w.a.get("/new")
    R.equal("the new-invoice form opens once the profile exists",
            form.status_code, 200)
    R.check("the first suggested number is INV-0001",
            'value="INV-0001"' in form.get_data(as_text=True),
            "read off the rendered form")

    w.connect_stripe(OWNER_A["email"], w.stripe_account_a)
    w.connect_stripe(OWNER_B["email"], w.stripe_account_b)


# ══════════════════════════════════════════════════════════════════════════
# Raising an invoice through the real form
# ══════════════════════════════════════════════════════════════════════════
def raise_invoice(browser, number, bill_to, lines, tax="0", discount="0",
                  shipping="0", client_email="", terms="Net 30",
                  invoice_date=None, due_date=""):
    """POST the invoice form exactly as the browser does."""
    return browser.post("/invoices", {
        "invoice_number": number,
        "bill_to": bill_to,
        "client_email": client_email,
        "invoice_date": (invoice_date or date.today()).isoformat(),
        "payment_terms": terms,
        "due_date": due_date,
        "tax": tax, "discount": discount, "shipping": shipping,
        "item_description": [d for d, _q, _r in lines],
        "item_quantity": [str(q) for _d, q, _r in lines],
        "item_rate": [str(r) for _d, _q, r in lines],
    })


# ══════════════════════════════════════════════════════════════════════════
# Chapter 3 — the client on the invoice, created, edited, deleted
# ══════════════════════════════════════════════════════════════════════════
def chapter_clients(w: World):
    R.chapter = "clients"
    R.skip("Invoicer has no separate client record",
           "the client is free text in bill_to on each invoice, so 'client "
           "CRUD' is exercised as invoice CRUD below. There is no client "
           "table, no client list and no way to correct a client's address "
           "across the invoices already raised — see docs/invoicer-scenarios.md")

    created = raise_invoice(
        w.a, "INV-0001", CLIENT_DAIRY,
        [("Quarterly bookkeeping review", 1, "1200.00")],
        tax="0", client_email="accounts@ravensworth.example",
    )
    R.equal("an invoice is raised through the form", created.status_code, 302)
    inv = read(w.app, "INV-0001")
    R.check("it exists in the database", inv is not None)
    if inv is None:
        return

    detail = w.a.get(f"/invoice/{inv.id}").get_data(as_text=True)
    R.check("the client's name is on the invoice page",
            "Ravensworth Dairy Co-operative" in detail)
    R.check("the client's address is on the invoice page",
            "9 Mill Lane" in detail)

    edited = w.a.post(f"/invoice/{inv.id}", {
        "invoice_number": "INV-0001",
        "bill_to": "Ravensworth Dairy Co-operative\n11 Mill Lane\nRavensworth",
        "client_email": "ap@ravensworth.example",
        "invoice_date": date.today().isoformat(),
        "payment_terms": "Net 30", "due_date": "",
        "tax": "0", "discount": "0", "shipping": "0",
        "item_description": ["Quarterly bookkeeping review"],
        "item_quantity": ["1"], "item_rate": ["1200.00"],
    })
    R.equal("the client's address is corrected by editing the invoice",
            edited.status_code, 302)
    after = read(w.app, "INV-0001")
    R.check("the correction stuck", "11 Mill Lane" in after.bill_to,
            after.bill_to.replace("\n", " / "))

    found = w.a.get("/history?q=Ravensworth").get_data(as_text=True)
    R.check("the client can be found by name in History", "INV-0001" in found)
    missing = w.a.get("/history?q=Pellham").get_data(as_text=True)
    R.check("searching for a different client does not return this one",
            "INV-0001" not in missing)

    # A throwaway invoice, so deletion can be exercised without losing a
    # record the later chapters need.
    raise_invoice(w.a, "INV-DELETE-ME", CLIENT_MARINE,
                  [("Raised in error", 1, "50.00")])
    doomed = read(w.app, "INV-DELETE-ME")
    with w.app.app_context():
        from models import LineItem
        lines_before = LineItem.query.filter_by(invoice_id=doomed.id).count()
    deleted = w.a.post(f"/invoice/{doomed.id}/delete")
    R.equal("an invoice raised in error can be deleted", deleted.status_code, 302)
    R.check("it is gone", read(w.app, invoice_id=doomed.id) is None)
    R.check("the invoice page now 404s",
            w.a.get(f"/invoice/{doomed.id}").status_code == 404)
    with w.app.app_context():
        from models import LineItem
        lines_after = LineItem.query.filter_by(invoice_id=doomed.id).count()
    R.equal("its line items went with it", (lines_before, lines_after), (1, 0))

    # Numbering must not hand back a number already in use.
    raise_invoice(w.a, "INV-0002", CLIENT_MARINE, [("Survey", 1, "300.00")])
    raise_invoice(w.a, "INV-0003", CLIENT_JOINERY, [("Advice", 1, "300.00")])
    second = read(w.app, "INV-0002")
    w.a.post(f"/invoice/{second.id}/delete")
    form = w.a.get("/new").get_data(as_text=True)
    suggested = re.search(r'name="invoice_number"[^>]*value="([^"]+)"', form)
    number = suggested.group(1) if suggested else "?"
    R.check("the next suggested number does not repeat a deleted one",
            number not in ("INV-0002", "INV-0003"),
            f"suggested {number} with INV-0001 and INV-0003 in the book")


# ══════════════════════════════════════════════════════════════════════════
# Chapter 4 — money
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class MoneyCase:
    key: str
    what: str
    lines: list
    tax: str = "0"
    discount: str = "0"
    shipping: str = "0"
    expect: str = "created"          # or "refused"
    note: str = ""


def money_cases() -> list[MoneyCase]:
    """The shapes an ordinary week of billing produces, plus both sides of
    every boundary that matters (S18). Written out rather than generated: a
    generated matrix buries the cases that matter in combinations nobody would
    ever bill."""
    return [
        MoneyCase("plain", "one line, no adjustments",
                  [("Monthly bookkeeping", 1, "1200.00")]),
        MoneyCase("taxed", "one line with sales tax",
                  [("Monthly bookkeeping", 1, "1200.00")], tax="8.25"),
        MoneyCase("multi", "three lines, tax, percentage discount, shipping",
                  [("Audit fieldwork", 12, "185.00"),
                   ("Travel", 3, "210.75"),
                   ("Filing fee", 1, "99.99")],
                  tax="8.25", discount="12.5", shipping="45.00"),
        MoneyCase("order-of-operations", "50% off, then 10% tax",
                  [("Consultancy", 1, "1000.00")], tax="10", discount="50",
                  note="tax must be charged on 500, not on 1000"),
        MoneyCase("twelve-lines", "a long job sheet",
                  [(f"Site visit {n:02d}", 1, f"{80 + n}.50") for n in range(1, 13)],
                  tax="7", discount="5", shipping="12.34"),
        MoneyCase("fractional-hours", "billed in quarter hours",
                  [("Advisory", "12.75", "187.50")], tax="6.5"),
        MoneyCase("credit-line", "an invoice carrying a credit line",
                  [("Year-end accounts", 1, "2400.00"),
                   ("Goodwill credit", 1, "-400.00")], tax="0"),
        MoneyCase("zero", "a zero-value invoice",
                  [("Written off as a courtesy", 1, "0.00")]),
        MoneyCase("full-discount", "written off in full at 100%",
                  [("Year-end accounts", 1, "500.00")], tax="10",
                  discount="100"),
        MoneyCase("tiny", "three cents",
                  [("Rounding adjustment", 3, "0.01")], tax="10"),
        MoneyCase("large", "a very large amount",
                  [("Portfolio migration", 1, "108000000.00")], tax="8.875"),
        MoneyCase("zero-quantity", "a line with nothing on it",
                  [("Standby", 0, "500.00"), ("Work done", 1, "500.00")]),
        MoneyCase("quarter-hour", "a quarter hour at a rate ending .50",
                  [("Advisory", "0.25", "250.50")],
                  note="0.25 x 250.50 is exactly 62.625"),
        MoneyCase("half-cent-tax", "a tax that lands exactly on half a cent",
                  [("Advisory", 1, "0.15")], tax="10",
                  note="10% of 0.15 is exactly 0.015"),
        # Refusals.
        MoneyCase("no-lines", "no line items at all", [], expect="refused"),
        MoneyCase("no-number", "no invoice number",
                  [("Work", 1, "100.00")], expect="refused"),
        MoneyCase("discount-150", "a 150% discount (a typo for 15)",
                  [("Work", 1, "1000.00")], discount="150", expect="refused"),
        MoneyCase("negative-tax", "a negative tax rate",
                  [("Work", 1, "1000.00")], tax="-10", expect="refused"),
        MoneyCase("negative-total", "line items that sum below zero",
                  [("Credit", 1, "-1000.00")], expect="refused"),
        MoneyCase("dollar-sign", "a rate pasted with its currency symbol",
                  [("Work", 1, "$500.00")], expect="refused",
                  note="used to become a $0.00 invoice, silently"),
        MoneyCase("overflow", "a rate that overflows to infinity",
                  [("Work", 10, "1e308")], expect="refused",
                  note="used to store a NaN total and print $nan on every KPI"),
        MoneyCase("exponent", "a rate typed as 1e400",
                  [("Work", 1, "1e400")], expect="refused"),
        MoneyCase("words", "a rate that is words",
                  [("Work", 1, "five hundred")], expect="refused"),
    ]


def chapter_money(w: World):
    R.chapter = "money"
    cases = money_cases()
    invariant_holds = 0
    exact_agreements = 0
    cent_losses = []          # discovered, not declared: see below
    worse = []

    for case in cases:
        number = f"MON-{case.key}"
        before = count_invoices(w.app)
        response = raise_invoice(
            w.a, "" if case.key == "no-number" else number, CLIENT_JOINERY,
            case.lines, tax=case.tax, discount=case.discount,
            shipping=case.shipping,
        )

        if case.expect == "refused":
            refused = response.status_code == 400
            R.check(f"[{case.key}] refused: {case.what}", refused,
                    f"HTTP {response.status_code}"
                    + (f" — {case.note}" if case.note else ""))
            R.check(f"[{case.key}] the refusal wrote nothing",
                    count_invoices(w.app) == before,
                    f"{count_invoices(w.app)} invoices, was {before}")
            continue

        if not R.check(f"[{case.key}] raised: {case.what}",
                       response.status_code == 302,
                       f"HTTP {response.status_code}"):
            continue
        inv = read(w.app, number)
        if inv is None:
            R.fail(f"[{case.key}] accepted but not stored")
            continue

        # --- the invariant, on every invoice, not on one ------------------
        line_sum = round(sum(inv.line_amounts), 2)
        rebuilt = round(
            line_sum - inv.discount_amount + inv.tax_amount + inv.shipping, 2
        )
        if R.check(
            f"[{case.key}] sum(lines) - discount + tax + shipping == total",
            abs(rebuilt - inv.total) < 0.005,
            f"{line_sum} - {inv.discount_amount} + {inv.tax_amount} + "
            f"{inv.shipping} = {rebuilt}, invoice says {inv.total}",
        ):
            invariant_holds += 1

        # --- independent decimal arithmetic ------------------------------
        want = expected_totals(
            [(q, r) for _d, q, r in case.lines],
            tax_pct=float(case.tax), discount_pct=float(case.discount),
            shipping=float(case.shipping),
        )
        #
        # Which invoices lose a cent is DISCOVERED here, not declared in the
        # case table. Naming the boundaries in advance would only prove the
        # harness knows where they are; letting it find them is what turns
        # "12.75 hours at $187.50" — an ordinary line on an ordinary invoice —
        # from a curiosity into a finding.
        drift = abs(Decimal(str(inv.total)) - want["total"])
        if drift == 0:
            exact_agreements += 1
        elif drift == Decimal("0.01"):
            cent_losses.append(
                f"[{case.key}] {case.what}: exact {want['total']}, "
                f"invoice {inv.total}"
                + (f" ({case.note})" if case.note else "")
            )
        else:
            worse.append(
                f"[{case.key}] invoice {inv.total} vs exact {want['total']} "
                f"— off by {drift}"
            )
        R.check(
            f"[{case.key}] is within a cent of exact decimal arithmetic",
            drift <= Decimal("0.01"),
            f"invoice {inv.total} vs exact {want['total']} "
            f"(subtotal {inv.subtotal}/{want['subtotal']}, "
            f"discount {inv.discount_amount}/{want['discount']}, "
            f"tax {inv.tax_amount}/{want['tax']})",
        )

        # --- tax is charged on the discounted base, not the gross --------
        if case.key == "order-of-operations":
            R.equal("[order-of-operations] tax is charged after the discount",
                    (inv.discount_amount, inv.tax_amount, inv.total),
                    (500.0, 50.0, 550.0),
                    "charging tax on the gross would give 100.00 / 600.00")

        # --- what the owner sees on the screen ---------------------------
        page = normalise(w.a.get(f"/invoice/{inv.id}").get_data(as_text=True))
        shown = normalise(format_money(inv.total, inv.currency))
        R.check(f"[{case.key}] the invoice page shows {shown}", shown in page)

    raised = len([c for c in cases if c.expect == "created"])
    R.check("the totals invariant held on every invoice raised",
            invariant_holds == raised, f"{invariant_holds} of {raised}",
            compared=invariant_holds)
    R.check("no invoice is off by more than a cent", not worse,
            "; ".join(worse) or f"{raised} invoices re-added in exact decimal",
            compared=raised)
    R.tripwire(
        "some invoices lose a cent to binary float rounding",
        bool(cent_losses),
        f"{len(cent_losses)} of {raised} invoices disagree with exact decimal "
        f"arithmetic by one cent, in the client's favour or the firm's "
        f"depending on the digits: " + " | ".join(cent_losses),
    )
    R.ok("exact-decimal agreements",
         f"{exact_agreements} of {raised} invoices matched decimal arithmetic "
         f"to the cent",
         compared=exact_agreements)

    # A blank row with the form's default quantity of 1 still creates a line.
    raise_invoice(w.a, "MON-blank-row", CLIENT_JOINERY,
                  [("Real work", 1, "500.00"), ("", 1, "0")])
    blank = read(w.app, "MON-blank-row")
    if blank:
        R.tripwire(
            "a blank row with a quantity still becomes a line item",
            len(blank.line_amounts) == 2 and "" in blank.line_descriptions,
            f"{len(blank.line_amounts)} lines: {blank.line_descriptions}",
        )


# ══════════════════════════════════════════════════════════════════════════
# Chapter 5 — currency
# ══════════════════════════════════════════════════════════════════════════
def chapter_currency(w: World):
    R.chapter = "currency"
    expectations = {
        "USD": "$1,000.00", "EUR": "€1,000.00", "GBP": "£1,000.00",
        "JPY": "¥1,000.00", "INR": "₹1,000.00",
        "CHF": "CHF 1,000.00", "BRL": "R$1,000.00",
    }
    for code, want in expectations.items():
        response = w.a.json("post", "/api/invoices", api_key=w.a_key, json={
            "invoice_number": f"CUR-{code}",
            "from_info": OWNER_A["business_name"],
            "bill_to": CLIENT_CHAMBERS,
            "currency": code,
            "items": [{"description": "Advice", "quantity": 1, "rate": 1000}],
        })
        if not R.check(f"{code} invoice created", response.status_code == 201,
                       f"HTTP {response.status_code}"):
            continue
        R.equal(f"{code} formats as {want}",
                format_money(1000.0, code), want)
        inv = read(w.app, f"CUR-{code}")
        page = normalise(w.a.get(f"/invoice/{inv.id}").get_data(as_text=True))
        R.check(f"{code} shows {want} on the invoice page",
                normalise(want) in page)
        pdf = w.a.get(f"/invoice/{inv.id}/pdf")
        if pdf.status_code == 200:
            w.keep_pdf(pdf, inv, f"currency-{code}")

    R.check("an unknown currency code does not crash the formatter",
            format_money(1000.0, "XYZ") == "1,000.00",
            f"XYZ renders as {format_money(1000.0, 'XYZ')!r} — no symbol at all")

    # Changing the account default does not restate historical invoices, and
    # must not: an invoice raised in dollars was agreed in dollars.
    inv_usd = read(w.app, "CUR-USD")
    w.a.post("/account/business", {
        "business_name": OWNER_A["business_name"],
        "business_email": OWNER_A["email"],
        "business_address": OWNER_A["business_address"],
        "tax_id": OWNER_A["tax_id"], "default_currency": "EUR",
        "default_terms": "Net 30",
    })
    still = read(w.app, "CUR-USD")
    R.equal("changing the account default leaves old invoices in their currency",
            still.currency, inv_usd.currency)

    # ...but the History KPIs add them all up and label the sum with the new
    # default. This is finding 7 of docs/invoicer-review.md, left alone there
    # as a product decision. It is reachable with no API involved at all —
    # the owner only has to change their default currency once.
    history = w.a.get("/history").get_data(as_text=True)
    mixed = re.search(r"outstanding", history, re.I)
    euro_labelled = "€" in history
    R.tripwire(
        "the History KPIs add different currencies together",
        bool(mixed) and euro_labelled,
        "seven invoices in seven currencies are summed into one figure and "
        "labelled with the account default (now EUR)",
    )
    w.a.post("/account/business", {
        "business_name": OWNER_A["business_name"],
        "business_email": OWNER_A["email"],
        "business_address": OWNER_A["business_address"],
        "tax_id": OWNER_A["tax_id"], "default_currency": "USD",
        "default_terms": "Net 30",
    })


# ══════════════════════════════════════════════════════════════════════════
# Chapter 6 — payments, partials, and going overdue
# ══════════════════════════════════════════════════════════════════════════
def chapter_payments(w: World):
    R.chapter = "payments"

    # ── a partial payment ────────────────────────────────────────────────
    raise_invoice(w.a, "PAY-partial", CLIENT_DAIRY,
                  [("Year-end accounts", 1, "1100.00")],
                  client_email="ap@ravensworth.example")
    inv = read(w.app, "PAY-partial")
    response = deliver(w.app, checkout_event(
        inv.id, "cs_partial_001", 40000, account=w.stripe_account_a))
    R.equal("a signed webhook for $400 of $1,100 is accepted",
            response.status_code, 200)
    after = read(w.app, "PAY-partial")
    R.equal("$400 is recorded", after.amount_paid, 400.0)
    R.equal("$700 is still owed", after.balance_due, 700.0)
    R.equal("the badge reads Partial", after.display_status, "Partial")
    R.check("it is still counted as outstanding", after.status != "Paid",
            f"status {after.status}")

    # ── the same event again ─────────────────────────────────────────────
    again = deliver(w.app, checkout_event(
        inv.id, "cs_partial_001", 40000, account=w.stripe_account_a))
    twice = read(w.app, "PAY-partial")
    R.equal("re-delivering the same event is accepted", again.status_code, 200)
    R.equal("...and does not credit it twice", twice.amount_paid, 400.0,
            "Stripe retries; a second credit would settle an unpaid invoice")

    # ── the rest of the money, on a second session ───────────────────────
    deliver(w.app, checkout_event(
        inv.id, "cs_partial_002", 70000, account=w.stripe_account_a))
    settled = read(w.app, "PAY-partial")
    R.equal("the balance clears on the second payment", settled.balance_due, 0.0)
    R.equal("the invoice reads Paid", settled.display_status, "Paid")
    R.equal("both sessions are recorded against it",
            len(settled.paid_session_ids.split(",")), 2, compared=2)

    # ── overpayment ──────────────────────────────────────────────────────
    raise_invoice(w.a, "PAY-over", CLIENT_MARINE, [("Survey", 1, "500.00")])
    over = read(w.app, "PAY-over")
    deliver(w.app, checkout_event(over.id, "cs_over_001", 60000,
                                  account=w.stripe_account_a))
    overpaid = read(w.app, "PAY-over")
    R.equal("an overpayment is recorded in full", overpaid.amount_paid, 600.0)
    R.equal("...and shows as a negative balance rather than being lost",
            overpaid.balance_due, -100.0)

    # ── overdue ──────────────────────────────────────────────────────────
    raise_invoice(w.a, "PAY-overdue", CLIENT_JOINERY,
                  [("Cabinetry advice", 1, "800.00")],
                  invoice_date=date.today() - timedelta(days=90),
                  terms="Net 30")
    overdue = read(w.app, "PAY-overdue")
    R.check("an invoice past its due date is overdue", overdue.is_overdue,
            f"due {overdue.due_date}, today {date.today()}")
    R.equal("the badge reads Overdue", overdue.display_status, "Overdue")
    listing = w.a.get("/history?status=overdue").get_data(as_text=True)
    R.check("it appears under the Overdue filter", "PAY-overdue" in listing)

    deliver(w.app, checkout_event(overdue.id, "cs_overdue_001", 30000,
                                  account=w.stripe_account_a))
    both = read(w.app, "PAY-overdue")
    R.equal("overdue outranks partial on the badge", both.display_status,
            "Overdue", "part-paid and late is still late")

    # ── an invoice whose custom due date precedes its issue date ─────────
    raise_invoice(w.a, "PAY-backwards", CLIENT_JOINERY,
                  [("Advice", 1, "100.00")], terms="",
                  due_date=(date.today() - timedelta(days=5)).isoformat())
    backwards = read(w.app, "PAY-backwards")
    R.tripwire(
        "a due date before the issue date is accepted",
        backwards is not None and backwards.is_overdue,
        "the invoice is issued today, due five days ago, and is overdue the "
        "moment it is created",
    )

    # ── mark paid / mark unpaid, and what they cost ──────────────────────
    raise_invoice(w.a, "PAY-manual", CLIENT_CHAMBERS,
                  [("Retainer", 1, "1000.00")])
    manual = read(w.app, "PAY-manual")
    w.a.post(f"/invoice/{manual.id}/mark-paid")
    marked = read(w.app, "PAY-manual")
    R.equal("mark-paid settles the invoice", marked.display_status, "Paid")
    R.equal("...and records the full amount", marked.amount_paid, 1000.0)
    w.a.post(f"/invoice/{manual.id}/mark-unpaid")
    reopened = read(w.app, "PAY-manual")
    R.equal("mark-unpaid reopens it", reopened.display_status, "Sent")
    R.equal("...and clears the recorded payment", reopened.amount_paid, 0.0)

    # The same button on a Stripe-confirmed payment. This is finding 4a of
    # docs/invoicer-review.md, left alone there because the fix is a Payment
    # ledger table.
    raise_invoice(w.a, "PAY-erased", CLIENT_CHAMBERS,
                  [("Advisory", 1, "400.00")])
    erased = read(w.app, "PAY-erased")
    deliver(w.app, checkout_event(erased.id, "cs_erased_001", 40000,
                                  account=w.stripe_account_a))
    w.a.post(f"/invoice/{erased.id}/mark-unpaid")
    gone = read(w.app, "PAY-erased")
    replay = deliver(w.app, checkout_event(erased.id, "cs_erased_001", 40000,
                                           account=w.stripe_account_a))
    unrecoverable = read(w.app, "PAY-erased")
    R.tripwire(
        "mark-unpaid erases a Stripe-confirmed payment, unrecoverably",
        gone.amount_paid == 0.0 and unrecoverable.amount_paid == 0.0
        and replay.status_code == 200,
        "$400 confirmed by Stripe is set to 0 by one click, and replaying the "
        "original event will not restore it because the session id is still "
        "in paid_session_ids",
    )

    # mark-paid over a partial payment.
    raise_invoice(w.a, "PAY-mixed", CLIENT_CHAMBERS,
                  [("Advisory", 1, "1100.00")])
    mixed = read(w.app, "PAY-mixed")
    deliver(w.app, checkout_event(mixed.id, "cs_mixed_001", 40000,
                                  account=w.stripe_account_a))
    w.a.post(f"/invoice/{mixed.id}/mark-paid")
    blended = read(w.app, "PAY-mixed")
    R.tripwire(
        "mark-paid over a partial payment loses where the money came from",
        blended.amount_paid == 1100.0 and blended.paid_session_ids != "",
        "$400 by card and $700 by cheque are now one indistinguishable "
        "1100.00; if the card payment is disputed there is no record of it",
    )

    # Deleting a paid invoice.
    raise_invoice(w.a, "PAY-deleted", CLIENT_CHAMBERS,
                  [("Advisory", 1, "900.00")])
    doomed = read(w.app, "PAY-deleted")
    deliver(w.app, checkout_event(doomed.id, "cs_deleted_001", 90000,
                                  account=w.stripe_account_a))
    w.a.post(f"/invoice/{doomed.id}/delete")
    R.tripwire(
        "deleting a paid invoice destroys the payment record",
        read(w.app, invoice_id=doomed.id) is None,
        "$900 that Stripe still holds a charge for now has no counterpart in "
        "this system to reconcile against",
    )

    # ── editing after payment ────────────────────────────────────────────
    raise_invoice(w.a, "PAY-edit-up", CLIENT_DAIRY,
                  [("Year-end accounts", 1, "1100.00")])
    up = read(w.app, "PAY-edit-up")
    w.a.post(f"/invoice/{up.id}/mark-paid")
    w.a.post(f"/invoice/{up.id}", {
        "invoice_number": "PAY-edit-up", "bill_to": CLIENT_DAIRY,
        "invoice_date": date.today().isoformat(), "payment_terms": "Net 30",
        "due_date": "", "tax": "0", "discount": "0", "shipping": "0",
        "item_description": ["Year-end accounts", "Additional scope"],
        "item_quantity": ["1", "1"], "item_rate": ["1100.00", "4000.00"],
    })
    reopened = read(w.app, "PAY-edit-up")
    R.equal("adding scope to a paid invoice reopens it", reopened.status, "Sent")
    R.equal("...and the new balance is visible", reopened.balance_due, 4000.0)

    outstanding = w.a.get("/history").get_data(as_text=True)
    R.check("...and it is back in the outstanding list",
            "PAY-edit-up" in outstanding)


# ══════════════════════════════════════════════════════════════════════════
# Chapter 7 — two accounts, one database
# ══════════════════════════════════════════════════════════════════════════
def chapter_isolation(w: World):
    R.chapter = "isolation"

    raise_invoice(w.a, "ISO-A", CLIENT_DAIRY,
                  [("Confidential engagement", 1, "9999.00")],
                  client_email="ap@ravensworth.example")
    raise_invoice(w.b, "ISO-B", CLIENT_MARINE,
                  [("Kestrel work", 1, "111.00")])
    a_inv, b_inv = read(w.app, "ISO-A"), read(w.app, "ISO-B")
    if a_inv is None or b_inv is None:
        R.fail("could not raise one invoice per account")
        return

    # -- reads --------------------------------------------------------------
    reads = [
        f"/invoice/{a_inv.id}", f"/invoice/{a_inv.id}/edit",
        f"/invoice/{a_inv.id}/pdf", f"/invoice/{a_inv.id}/logo",
    ]
    leaks = []
    for path in reads:
        response = w.b.get(path)
        if response.status_code != 404:
            leaks.append(f"GET {path} -> {response.status_code}")
        elif b"9999" in response.data or b"Ravensworth" in response.data:
            leaks.append(f"GET {path} leaked content in its 404")
    R.check("account B cannot READ account A's invoice over the web",
            not leaks, "; ".join(leaks) or f"{len(reads)} routes -> 404",
            compared=len(reads))

    # -- writes -------------------------------------------------------------
    writes = [
        (f"/invoice/{a_inv.id}", {
            "invoice_number": "ISO-A", "bill_to": "Hijacked",
            "invoice_date": date.today().isoformat(),
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Hijacked"], "item_quantity": ["1"],
            "item_rate": ["1.00"]}),
        (f"/invoice/{a_inv.id}/delete", {}),
        (f"/invoice/{a_inv.id}/mark-paid", {}),
        (f"/invoice/{a_inv.id}/mark-unpaid", {}),
        (f"/invoice/{a_inv.id}/email", {"to_email": "attacker@evil.example"}),
    ]
    breaches = []
    for path, payload in writes:
        response = w.b.post(path, payload)
        if response.status_code != 404:
            breaches.append(f"POST {path} -> {response.status_code}")
    R.check("account B cannot WRITE to account A's invoice",
            not breaches, "; ".join(breaches) or f"{len(writes)} routes -> 404",
            compared=len(writes))

    survivor = read(w.app, "ISO-A")
    R.check("A's invoice is untouched after all of that",
            survivor is not None
            and survivor.total == a_inv.total
            and survivor.bill_to == a_inv.bill_to
            and survivor.status == a_inv.status,
            f"total {survivor.total if survivor else None}, "
            f"status {survivor.status if survivor else None}")

    # -- the JSON API -------------------------------------------------------
    api_probes = [
        ("get", f"/api/invoices/{a_inv.id}"),
        ("get", f"/api/invoices/{a_inv.id}/pdf"),
        ("delete", f"/api/invoices/{a_inv.id}"),
        ("post", f"/api/invoices/{a_inv.id}/payment-link"),
    ]
    api_leaks = []
    for method, path in api_probes:
        response = w.b.json(method, path, api_key=w.b_key)
        if response.status_code != 404:
            api_leaks.append(f"{method.upper()} {path} -> {response.status_code}")
    R.check("account B's API key cannot reach account A's invoice",
            not api_leaks,
            "; ".join(api_leaks) or f"{len(api_probes)} endpoints -> 404",
            compared=len(api_probes))

    listing = w.b.json("get", "/api/invoices", api_key=w.b_key).get_json()
    numbers = [i["invoice_number"] for i in listing.get("invoices", [])]
    R.check("account B's API listing contains only its own invoices",
            all(n.startswith("ISO-B") or not n.startswith(("MON-", "CUR-", "PAY-", "INV-"))
                for n in numbers) and "ISO-A" not in numbers,
            f"B sees {numbers}", compared=len(numbers))

    page = w.b.get("/history").get_data(as_text=True)
    R.check("account B's History shows none of A's invoices",
            "ISO-A" not in page and "Ravensworth" not in page)
    csv_text = w.b.get("/history/export.csv").get_data(as_text=True)
    R.check("account B's CSV export contains none of A's invoices",
            "ISO-A" not in csv_text and "Ravensworth" not in csv_text)

    # -- the public link ----------------------------------------------------
    public = w.anon.get(f"/i/{a_inv.public_token}")
    R.equal("A's public link opens for anyone holding it (by design)",
            public.status_code, 200)
    R.check("...and shows A's invoice, not somebody else's",
            "ISO-A" in public.get_data(as_text=True))
    forged = w.anon.get("/i/not-a-real-token")
    R.equal("a made-up public token is refused", forged.status_code, 404)
    tampered = a_inv.public_token[:-3] + "AAA"
    R.equal("a tampered public token is refused",
            w.anon.get(f"/i/{tampered}").status_code, 404)
    b_token = read(w.app, "ISO-B").public_token
    b_page = w.anon.get(f"/i/{b_token}").get_data(as_text=True)
    R.check("B's public token shows only B's invoice",
            "ISO-B" in b_page and "ISO-A" not in b_page)

    # -- a public link outliving the invoice it was minted for --------------
    #
    # The public token signs the invoice's INTEGER PRIMARY KEY, and SQLite
    # hands the next insert the highest free rowid — so deleting an invoice
    # releases its id, and the next invoice raised on the instance takes it.
    # Every link already in a client's inbox then resolves to somebody else's
    # invoice. This run reproduces it ACROSS ACCOUNTS: A's client opens the
    # link A sent them and reads B's invoice. Nothing in Invoicer's own
    # authorization is wrong — the public page is meant to be readable by
    # whoever holds the link — the identifier underneath it is.
    raise_invoice(w.a, "RECYCLE-A", CLIENT_MARINE,
                  [("Confidential retainer", 1, "5000.00")])
    doomed = read(w.app, "RECYCLE-A")
    stale_link = doomed.public_token
    R.equal("a public link works before the invoice is deleted",
            w.anon.get(f"/i/{stale_link}").status_code, 200)
    w.a.post(f"/invoice/{doomed.id}/delete")
    R.equal("...and 404s straight after the deletion",
            w.anon.get(f"/i/{stale_link}").status_code, 404)

    raise_invoice(w.b, "RECYCLE-B", CLIENT_CHAMBERS,
                  [("Kestrel confidential work", 1, "7777.00")])
    recycled = read(w.app, "RECYCLE-B")
    stale = w.anon.get(f"/i/{stale_link}")
    leaked_body = stale.get_data(as_text=True)
    # FIXED 27 August 2026. This was a tripwire on known-broken behaviour, and
    # it fired the moment the behaviour changed, which is what a tripwire is
    # for. `Invoice.__table_args__` now carries `sqlite_autoincrement`, so
    # SQLite keeps a monotonic counter and never hands a deleted invoice's id
    # to the next one. Chosen over a random public token because a token
    # change invalidates every link already in a client's hands.
    R.check("account B's next invoice does not inherit A's deleted id",
            recycled is not None and recycled.id != doomed.id,
            f"invoice id {doomed.id} was recycled — every link A already sent "
            f"its clients now resolves to B's invoice")
    R.check("A's stale link still 404s rather than serving somebody else",
            stale.status_code == 404 and "RECYCLE-B" not in leaked_body,
            f"the deleted link returned {stale.status_code} and "
            f"{'leaked B' if 'RECYCLE-B' in leaked_body else 'did not leak'}")

    # -- the account itself -------------------------------------------------
    with w.app.app_context():
        before_accounts = User.query.count()
    attempt = w.b.post("/account/delete", {"password": OWNER_A["password"]})
    with w.app.app_context():
        survivors = User.query.count()
    R.check("B cannot delete an account by guessing another owner's password",
            survivors == before_accounts,
            f"{survivors} accounts remain, was {before_accounts}")
    R.check("...and B's own account survives its own wrong password",
            attempt.status_code == 302)


# ══════════════════════════════════════════════════════════════════════════
# Chapter 8 — the JSON API
# ══════════════════════════════════════════════════════════════════════════
def chapter_api(w: World):
    R.chapter = "api"

    R.equal("the health probe is open and says nothing else",
            w.anon.json("get", "/api/health").get_json(), {"status": "ok"})
    R.equal("no API key is refused",
            w.anon.json("get", "/api/invoices").status_code, 401)
    R.equal("a wrong API key is refused",
            w.anon.json("get", "/api/invoices",
                        api_key="sk_not_a_real_key").status_code, 401)

    created = w.a.json("post", "/api/invoices", api_key=w.a_key, json={
        "invoice_number": "API-0001",
        "from_info": OWNER_A["business_name"] + "\n17 Cordwainer Street",
        "bill_to": CLIENT_CHAMBERS,
        "items": [
            {"description": "Advisory", "quantity": 8, "rate": 175.50},
            {"description": "Filing", "quantity": 1, "rate": 90.00},
        ],
        "tax": {"value": 8.25, "percent": True},
        "discount": {"value": 100, "percent": False},
        "shipping": 0,
        "payment_terms": "Net 14",
    })
    if R.equal("an invoice is created over the API", created.status_code, 201):
        body = created.get_json()
        want = expected_totals([(8, "175.50"), (1, "90.00")],
                               tax_pct=8.25, discount_flat=100)
        R.equal("the API's stated subtotal is exact",
                Decimal(str(body["subtotal"])), want["subtotal"])
        # 8.25% of 1,394.00 is exactly 115.005 — the same half-cent boundary
        # the money chapter finds, reached here through the other front door.
        R.tripwire(
            "the API loses the same cent the web form does",
            Decimal(str(body["tax"])) == want["tax"] - Decimal("0.01"),
            f"8.25% of 1394.00 is exactly 115.005; the API says "
            f"{body['tax']}, exact decimal is {want['tax']}",
        )
        R.check("the API's total is within a cent of exact",
                abs(Decimal(str(body["total"])) - want["total"])
                <= Decimal("0.01"),
                f"{body['total']} vs {want['total']}")
        R.check("the API's total is its own parts added up",
                abs(Decimal(str(body["subtotal"]))
                    - Decimal(str(body["discount"]))
                    + Decimal(str(body["tax"]))
                    + Decimal(str(body["shipping"]))
                    - Decimal(str(body["total"]))) < Decimal("0.005"),
                f"{body['subtotal']} - {body['discount']} + {body['tax']} + "
                f"{body['shipping']} vs {body['total']}")
        stored = read(w.app, "API-0001")
        R.equal("the API response matches what was stored",
                (body["total"], body["balance_due"]),
                (stored.total, stored.balance_due))
        R.check("the API's line amounts sum to its subtotal",
                abs(sum(i["amount"] for i in body["items"])
                    - body["subtotal"]) < 0.005,
                f"{[i['amount'] for i in body['items']]} -> {body['subtotal']}",
                compared=len(body["items"]))

        fetched = w.a.json("get", f"/api/invoices/{body['id']}",
                           api_key=w.a_key)
        R.equal("the invoice reads back identically",
                fetched.get_json()["total"], body["total"])
        pdf = w.a.json("get", f"/api/invoices/{body['id']}/pdf",
                       api_key=w.a_key)
        R.check("the API serves a real PDF",
                pdf.status_code == 200 and pdf.data[:5] == b"%PDF-",
                f"HTTP {pdf.status_code}, starts {pdf.data[:5]!r}")
        if pdf.status_code == 200:
            w.keep_pdf(pdf, stored, "api-0001")

    auto = w.a.json("post", "/api/invoices", api_key=w.a_key, json={
        "from_info": OWNER_A["business_name"], "bill_to": CLIENT_CHAMBERS,
        "items": [{"description": "Advisory", "quantity": 1, "rate": 10}],
    })
    R.check("an invoice with no number is auto-numbered",
            auto.status_code == 201
            and (auto.get_json() or {}).get("invoice_number", "").startswith("INV-"),
            (auto.get_json() or {}).get("invoice_number"))

    # -- refusals -----------------------------------------------------------
    base = {"from_info": "X", "bill_to": "Y",
            "items": [{"description": "W", "quantity": 1, "rate": 100}]}
    refusals = [
        ("no body at all", None, 400),
        ("a JSON array instead of an object", [], 400),
        ("no line items", {**base, "items": []}, 422),
        ("no bill_to", {**base, "bill_to": ""}, 422),
        ("no from_info", {**base, "from_info": ""}, 422),
        ("a 150% discount", {**base, "discount": {"value": 150,
                                                  "percent": True}}, 422),
        ("a negative discount", {**base, "discount": {"value": -5,
                                                      "percent": True}}, 422),
        ("a negative tax", {**base, "tax": {"value": -5,
                                            "percent": True}}, 422),
        ("a negative amount_paid", {**base, "amount_paid": -500}, 422),
        ("a rate that is not a number", {
            "from_info": "X", "bill_to": "Y",
            "items": [{"description": "W", "quantity": 1, "rate": "$500"}]},
         422),
        ("a line item that is not an object", {
            "from_info": "X", "bill_to": "Y", "items": ["not a dict"]}, 422),
        ("a total below zero", {
            "from_info": "X", "bill_to": "Y",
            "items": [{"description": "W", "quantity": 1, "rate": -100}]}, 422),
    ]
    wrong = []
    for name, payload, want_code in refusals:
        if payload is None:
            response = w.a.json("post", "/api/invoices", api_key=w.a_key,
                                data="not json",
                                content_type="application/json")
        else:
            response = w.a.json("post", "/api/invoices", api_key=w.a_key,
                                json=payload)
        if response.status_code != want_code:
            wrong.append(f"{name}: got {response.status_code}, "
                         f"wanted {want_code}")
    R.check("every malformed API request is refused with the right code",
            not wrong, "; ".join(wrong) or f"{len(refusals)} probed",
            compared=len(refusals))

    # NaN and Infinity are bare literals Python's JSON decoder accepts.
    for literal in ("NaN", "Infinity", "-Infinity"):
        body = json.dumps({
            "invoice_number": f"API-{literal}", "from_info": "X",
            "bill_to": "Y",
            "items": [{"description": "W", "quantity": 1, "rate": 0}],
        }).replace('"rate": 0', f'"rate": {literal}')
        response = w.a.json("post", "/api/invoices", api_key=w.a_key,
                            data=body, content_type="application/json")
        R.equal(f"a rate of {literal} is refused", response.status_code, 422)

    # Deleting over the API.
    doomed = w.a.json("post", "/api/invoices", api_key=w.a_key, json={
        "invoice_number": "API-DELETE", "from_info": "X",
        "bill_to": CLIENT_CHAMBERS,
        "items": [{"description": "W", "quantity": 1, "rate": 100}]}).get_json()
    removed = w.a.json("delete", f"/api/invoices/{doomed['id']}",
                       api_key=w.a_key)
    R.equal("an invoice can be deleted over the API", removed.status_code, 200)
    R.equal("...and is then a 404",
            w.a.json("get", f"/api/invoices/{doomed['id']}",
                     api_key=w.a_key).status_code, 404)

    # Regenerating the key must actually invalidate the old one.
    old_key = w.b_key
    w.b.post("/account/regenerate-key")
    new_key = w.api_key(OWNER_B["email"])
    R.check("regenerating the API key changes it", new_key != old_key)
    R.equal("...and the old key stops working",
            w.anon.json("get", "/api/invoices", api_key=old_key).status_code,
            401)
    w.b_key = new_key


# ══════════════════════════════════════════════════════════════════════════
# Chapter 9 — Stripe
# ══════════════════════════════════════════════════════════════════════════
def chapter_stripe(w: World):
    R.chapter = "stripe"

    raise_invoice(w.a, "STR-0001", CLIENT_DAIRY,
                  [("Year-end accounts", 1, "1000.00")], tax="10")
    inv = read(w.app, "STR-0001")

    # -- the paying client's route ----------------------------------------
    pay = w.anon.post_raw(f"/i/{inv.public_token}/pay")
    R.check("the public pay button creates a Checkout Session",
            pay.status_code == 302 and w.stripe.last() is not None,
            f"HTTP {pay.status_code}")
    session = w.stripe.last()
    if session:
        R.equal("Stripe is asked for the balance due, not the total",
                session.amount, inv.balance_due)
        R.equal("...in the invoice's own currency", session.currency,
                inv.currency.lower())

    # -- signatures --------------------------------------------------------
    good_event = checkout_event(inv.id, "cs_str_001", 110000,
                                account=w.stripe_account_a)
    payload = json.dumps(good_event).encode()

    bad_signatures = [
        ("no Stripe-Signature header at all",
         dict(signature=None, secret=None)),
        ("an empty signature", dict(signature="")),
        ("a signature made with the wrong secret",
         dict(secret="whsec_a_different_secret")),
        ("a made-up signature", dict(signature="t=1,v1=deadbeef")),
        ("a signature over a DIFFERENT body",
         dict(signature=sign(b'{"tampered":true}'), body=payload)),
        ("a signature more than a day old",
         dict(timestamp=int(time.time()) - 86400 * 2)),
    ]
    accepted = []
    for name, kwargs in bad_signatures:
        response = deliver(w.app, good_event, **kwargs)
        if response.status_code == 200:
            accepted.append(name)
    R.check("no badly signed webhook is accepted", not accepted,
            "; ".join(accepted)
            or f"{len(bad_signatures)} bad signatures, all rejected",
            compared=len(bad_signatures))
    unpaid = read(w.app, "STR-0001")
    R.equal("...and none of them credited the invoice", unpaid.amount_paid, 0.0,
            "an endpoint that accepts an unsigned webhook is a way to mark "
            "invoices paid for free")

    # -- a correctly signed one -------------------------------------------
    good = deliver(w.app, good_event)
    R.equal("a correctly signed webhook is accepted", good.status_code, 200)
    credited = read(w.app, "STR-0001")
    R.equal("...and credits exactly the amount in the event",
            credited.amount_paid, 1100.0)
    R.equal("...and settles the invoice", credited.status, "Paid")

    # -- idempotency, again, in the chapter that owns it ------------------
    for _ in range(3):
        deliver(w.app, good_event)
    stable = read(w.app, "STR-0001")
    R.equal("four deliveries of one event credit it once",
            stable.amount_paid, 1100.0, compared=4)

    # -- an event that is not ours ----------------------------------------
    raise_invoice(w.a, "STR-0002", CLIENT_MARINE, [("Survey", 1, "500.00")])
    other = read(w.app, "STR-0002")
    foreign = deliver(w.app, checkout_event(
        other.id, "cs_foreign_001", 50000, account="acct_somebody_else"))
    R.equal("an event from another Stripe account is not credited",
            read(w.app, "STR-0002").amount_paid, 0.0,
            f"webhook returned {foreign.status_code}")

    mismatch = deliver(w.app, checkout_event(
        other.id, "cs_currency_001", 50000, currency="eur",
        account=w.stripe_account_a))
    R.equal("an event in the wrong currency is not credited",
            read(w.app, "STR-0002").amount_paid, 0.0,
            f"webhook returned {mismatch.status_code}")

    # -- a delayed payment method -----------------------------------------
    raise_invoice(w.a, "STR-ach", CLIENT_JOINERY, [("Advice", 1, "500.00")])
    ach = read(w.app, "STR-ach")
    pending = deliver(w.app, checkout_event(
        ach.id, "cs_ach_001", 50000, account=w.stripe_account_a,
        payment_status="unpaid"))
    still_owed = read(w.app, "STR-ach")
    R.equal("an ACH debit that has not settled is accepted but not credited",
            (pending.status_code, still_owed.amount_paid, still_owed.status),
            (200, 0.0, "Draft"),
            "checkout.session.completed fires days before the funds clear")
    deliver(w.app, checkout_event(
        ach.id, "cs_ach_001", 50000, account=w.stripe_account_a,
        payment_status="paid",
        event_type="checkout.session.async_payment_succeeded"))
    cleared = read(w.app, "STR-ach")
    R.equal("...and is credited once when it settles", cleared.amount_paid, 500.0)
    deliver(w.app, checkout_event(
        ach.id, "cs_ach_001", 50000, account=w.stripe_account_a,
        payment_status="paid",
        event_type="checkout.session.async_payment_succeeded"))
    R.equal("...and not again on the retry", read(w.app, "STR-ach").amount_paid,
            500.0)

    # -- events about invoices that are not there -------------------------
    ghost = deliver(w.app, checkout_event(
        999999, "cs_ghost_001", 10000, account=w.stripe_account_a))
    R.equal("an event for an invoice that no longer exists returns 200",
            ghost.status_code, 200,
            "a 500 here triggers Stripe's retry storm and eventually disables "
            "the endpoint, which would drop OTHER invoices' payments")

    unhandled = deliver(w.app, {"id": "evt_x", "type": "invoice.voided",
                                "data": {"object": {}}})
    R.equal("an event type we do not handle is acknowledged, not errored",
            unhandled.status_code, 200)

    # -- a connected account cannot claim someone else's invoice ----------
    raise_invoice(w.b, "STR-B", CLIENT_MARINE, [("Kestrel work", 1, "700.00")])
    b_inv = read(w.app, "STR-B")
    forged = deliver(w.app, checkout_event(
        b_inv.id, "cs_forged_001", 70000, account=w.stripe_account_a))
    R.equal("account A's Stripe account cannot settle account B's invoice",
            read(w.app, "STR-B").amount_paid, 0.0,
            f"webhook returned {forged.status_code}")


# ══════════════════════════════════════════════════════════════════════════
# Chapter 10 — email
# ══════════════════════════════════════════════════════════════════════════
def part_of(msg, content_type):
    for part in msg.walk():
        if part.get_content_type() == content_type:
            return part
    return None


def chapter_email(w: World):
    R.chapter = "email"
    FakeSMTP.outbox.clear()

    # An invoice with NO stored client email, so an empty To: really is empty
    # (the route legitimately falls back to invoice.client_email otherwise).
    raise_invoice(w.a, "EML-NOWHERE", CLIENT_MARINE,
                  [("Survey", 1, "100.00")], client_email="")
    nowhere = read(w.app, "EML-NOWHERE")
    blank = w.a.post(f"/invoice/{nowhere.id}/email", {"to_email": ""},
                     follow_redirects=True)
    R.check("a send with no recipient anywhere is refused",
            "Recipient email is required" in blank.get_data(as_text=True))
    R.equal("...and nothing was handed to the transport",
            len(FakeSMTP.outbox), 0)
    R.equal("...and the invoice is not marked Sent",
            read(w.app, "EML-NOWHERE").status, "Draft")

    raise_invoice(w.a, "EML-0001", CLIENT_DAIRY,
                  [("Year-end accounts", 1, "1100.00"),
                   ("Companies House filing", 1, "34.00")],
                  tax="8.25", client_email="ap@ravensworth.example")
    inv = read(w.app, "EML-0001")

    sent = w.a.post(f"/invoice/{inv.id}/email",
                    {"to_email": "ap@ravensworth.example"},
                    follow_redirects=True)
    R.equal("the invoice is emailed", sent.status_code, 200)
    if not R.equal("one message reached the transport",
                   len(FakeSMTP.outbox), 1):
        return
    msg = FakeSMTP.outbox[-1]
    R.equal("...marked Sent afterwards", read(w.app, "EML-0001").status, "Sent")

    R.equal("the subject names the invoice", msg["Subject"],
            f"Invoice {inv.number}")
    R.check("it is addressed to the client",
            msg["To"] == "ap@ravensworth.example", msg["To"])
    R.check("the From address is the configured sender",
            "billing@invoicer.example" in (msg["From"] or ""), msg["From"])

    text_part = part_of(msg, "text/plain")
    html_part = part_of(msg, "text/html")
    pdf_part = part_of(msg, "application/pdf")

    R.check("there is a plain-text alternative", text_part is not None)
    R.check("there is an HTML alternative", html_part is not None)
    R.check("the PDF is attached",
            pdf_part is not None and pdf_part.get_content()[:5] == b"%PDF-",
            pdf_part.get_filename() if pdf_part else "no attachment")
    if pdf_part is not None:
        emailed = w.out / "produced" / "emailed-EML-0001.pdf"
        emailed.parent.mkdir(parents=True, exist_ok=True)
        emailed.write_bytes(pdf_part.get_content())
        w.pdfs.append((emailed, inv))

    want_amount = normalise(format_money(inv.total, inv.currency))
    bodies = {}
    if text_part is not None:
        bodies["plain text"] = normalise(text_part.get_content())
    if html_part is not None:
        bodies["HTML"] = normalise(html_part.get_content())

    for name, body in bodies.items():
        R.check(f"the {name} body names the invoice", inv.number in body)
        leaks = [t for t in ("{{", "}}", "{%", "%}", "<<", ">>",
                             "Undefined", "None")
                 if t in body]
        R.check(f"the {name} body has no unresolved template tokens",
                not leaks, f"found {leaks}" if leaks else f"{len(body)} chars")

    if "HTML" in bodies:
        # Unescaped for the "is this word on the page" checks — the business
        # name contains an ampersand, and &amp; is correct escaping, not a
        # missing name. The token checks above run on the RAW body, where an
        # unrendered {{ }} would still be visible.
        import html as htmlmod
        readable = htmlmod.unescape(bodies["HTML"])
        R.check("the HTML body states the amount due",
                want_amount in readable, f"looking for {want_amount}")
        R.check("the HTML body names the client",
                inv.client_name in readable)
        R.check("the HTML body names the business",
                OWNER_A["business_name"] in readable,
                f"looking for {OWNER_A['business_name']!r}")
        R.check("the HTML body links to the public invoice page",
                "/i/" in readable)

    if "plain text" in bodies:
        R.tripwire(
            "the plain-text email body carries no amount",
            want_amount not in bodies["plain text"],
            "a client reading in plain text sees 'Please find attached "
            "invoice EML-0001' and no figure, no due date and no balance",
        )

    # A send that fails must not claim the invoice went out.
    raise_invoice(w.a, "EML-FAIL", CLIENT_MARINE, [("Survey", 1, "200.00")])
    failing = read(w.app, "EML-FAIL")

    def explode(self, msg):                                   # noqa: ARG001
        raise smtplib.SMTPServerDisconnected("the server hung up")

    original = FakeSMTP.send_message
    FakeSMTP.send_message = explode
    try:
        response = w.a.post(f"/invoice/{failing.id}/email",
                            {"to_email": "ap@pellham.example"},
                            follow_redirects=True)
    finally:
        FakeSMTP.send_message = original
    R.check("a failed send says so", "Email failed" in response.get_data(as_text=True))
    R.equal("...and does not mark the invoice Sent",
            read(w.app, "EML-FAIL").status, "Draft",
            "the owner must not believe the client received it")


# ══════════════════════════════════════════════════════════════════════════
# Chapter 11 — the CSV the bookkeeper opens
# ══════════════════════════════════════════════════════════════════════════
def chapter_csv(w: World):
    R.chapter = "csv"

    # bill_to is free text, and through the JSON API it can be written by
    # another system entirely.
    w.a.json("post", "/api/invoices", api_key=w.a_key, json={
        "invoice_number": "CSV-INJECT", "from_info": OWNER_A["business_name"],
        "bill_to": "=cmd|'/c calc'!A1",
        "items": [{"description": "Advice", "quantity": 1, "rate": 10}],
    })

    response = w.a.get("/history/export.csv")
    R.equal("the CSV export downloads", response.status_code, 200)
    text = response.get_data(as_text=True)
    rows = list(csvmod.reader(io.StringIO(text)))
    header = rows[0] if rows else []
    R.check("it has a header row", "Invoice Number" in header,
            ", ".join(header[:4]))

    with w.app.app_context():
        mine = Invoice.query.filter_by(user_id=w.a_id).all()
        expected = {i.invoice_number: (round(i.total, 2),
                                       round(i.balance_due, 2)) for i in mine}
    R.equal("one row per invoice in the book", len(rows) - 1, len(expected),
            compared=len(expected))

    columns = {name: index for index, name in enumerate(header)}
    disagreements = []
    for row in rows[1:]:
        number = row[columns["Invoice Number"]].lstrip("'")
        if number not in expected:
            continue
        total = float(row[columns["Total"]])
        balance = float(row[columns["Balance Due"]])
        if (round(total, 2), round(balance, 2)) != expected[number]:
            disagreements.append(
                f"{number}: CSV {total}/{balance} vs DB {expected[number]}")
    R.check("every total in the CSV equals the total in the database",
            not disagreements, "; ".join(disagreements[:4])
            or f"{len(expected)} invoices reconciled",
            compared=len(expected))

    injected = [r for r in rows if "calc" in ",".join(r)]
    R.check("a formula in a client name is neutralised in the export",
            bool(injected) and injected[0][columns["Bill To"]].startswith("'"),
            injected[0][columns["Bill To"]] if injected else "row not found")

    # And the arithmetic inside a row has to add up too.
    row_errors = []
    for row in rows[1:]:
        subtotal, discount, tax, shipping, total = (
            float(row[columns[name]]) for name in
            ("Subtotal", "Discount", "Tax", "Shipping", "Total")
        )
        if abs((subtotal - discount + tax + shipping) - total) > 0.005:
            row_errors.append(row[columns["Invoice Number"]])
    R.check("every CSV row adds up on its own", not row_errors,
            "; ".join(row_errors) or f"{len(rows) - 1} rows re-added",
            compared=len(rows) - 1)


# ══════════════════════════════════════════════════════════════════════════
# Chapter 12 — the artifacts: open every one of them
# ══════════════════════════════════════════════════════════════════════════
def chapter_artifacts(w: World):
    R.chapter = "artifacts"

    # A PDF for every payment state, plus the awkward shapes.
    with w.app.app_context():
        mine = (
            Invoice.query.filter_by(user_id=w.a_id)
            .order_by(Invoice.id).all()
        )
        wanted = [snapshot(i) for i in mine]

    for inv in wanted:
        response = w.a.get(f"/invoice/{inv.id}/pdf")
        if response.status_code != 200:
            R.fail(f"the PDF for {inv.number} was refused",
                   f"HTTP {response.status_code}")
            continue
        w.keep_pdf(response, inv, f"web-{inv.number}")

    # The client's own download, with no login at all.
    if wanted:
        public = w.anon.get(f"/i/{wanted[0].public_token}/pdf")
        if R.check("the client can download the PDF from the public link "
                   "without an account",
                   public.status_code == 200 and public.data[:5] == b"%PDF-",
                   f"HTTP {public.status_code}"):
            w.keep_pdf(public, wanted[0], f"public-{wanted[0].number}")

    # ── NOW OPEN THEM. This is the whole reason the harness exists. ──────
    problems = []
    for path, inv in w.pdfs:
        problems.extend(verify_pdf(path, inv))
    R.check(
        f"every PDF produced in this run opens, and its total matches the "
        f"database",
        not problems,
        "; ".join(problems[:6]) if problems
        else f"{len(w.pdfs)} PDFs opened: text extracted, invoice number, "
             f"client name and Total read off each page, and page 1 "
             f"rasterised to confirm there is ink on it",
        compared=len(w.pdfs),
    )
    R.check("more than a handful of PDFs were actually opened",
            len(w.pdfs) >= 15,
            f"{len(w.pdfs)} — a check that examined nothing is worse than a "
            "red one", compared=len(w.pdfs))

    # ── the page the paying client opens, in a real browser ─────────────
    browser_check(w, wanted)


def browser_check(w: World, invoices):
    """Load the public invoice page in Chromium against a LIVE server.

    Reading the HTML as a string proves the bytes. It cannot prove the page
    renders: a stylesheet that 404s, a template that emits an empty totals
    table under a confident heading, a number the layout pushes off the page —
    all of those serve a perfectly good 200. So the page is opened, and what
    is read back is what the browser computed, not what the template said.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        R.skip("the public invoice page was NOT opened in a browser",
               "playwright is not installed — this run proves nothing about "
               "whether the page a client opens actually renders")
        return

    payable = [i for i in invoices if i.balance_due > 0][:1]
    paid = [i for i in invoices if i.balance_due <= 0][:1]
    targets = payable + paid
    if not targets:
        R.skip("no invoice to open in a browser")
        return

    executable = os.environ.get("PW_CHROMIUM") or "/opt/pw-browsers/chromium"
    launch = {"executable_path": executable} if Path(executable).exists() else {}

    with LiveServer(w.app) as server, sync_playwright() as pw:
        browser = pw.chromium.launch(**launch)
        page = browser.new_page()
        for inv in targets:
            url = f"{server.base}/i/{inv.public_token}"
            try:
                page.goto(url, wait_until="networkidle", timeout=20000)
            except Exception as exc:                          # noqa: BLE001
                R.fail(f"the public page for {inv.number} would not load",
                       f"{type(exc).__name__}: {exc}")
                continue
            seen = page.evaluate(
                """() => {
                    const body = document.body;
                    const text = body.innerText;
                    const style = getComputedStyle(body);
                    return {
                        text,
                        chars: text.replace(/\\s+/g, '').length,
                        height: body.scrollHeight,
                        font: style.fontFamily,
                        background: style.backgroundColor,
                        buttons: [...document.querySelectorAll(
                            'button, a.btn, .pay-btn, form button')]
                            .map(el => el.innerText.trim()).filter(Boolean),
                    };
                }"""
            )
            flat = re.sub(r"\s+", " ", normalise(seen["text"]))
            faults = []
            if seen["chars"] < 120:
                faults.append(f"the page rendered {seen['chars']} characters")
            if seen["height"] < 200:
                faults.append(f"the page is {seen['height']}px tall")
            if inv.number not in flat:
                faults.append("the invoice number is not visible")
            if inv.client_name not in flat:
                faults.append("the client's name is not visible")
            want = normalise(format_money(inv.balance_due, inv.currency))
            total = normalise(format_money(inv.total, inv.currency))
            if want not in flat and total not in flat:
                faults.append(f"neither {total} nor {want} is visible on the "
                              "page")
            for marker in ("{{", "}}", "{%", "Undefined"):
                if marker in flat:
                    faults.append(f"unrendered template marker {marker!r}")
            R.check(
                f"the public invoice page for {inv.number} renders in Chromium",
                not faults, "; ".join(faults)
                or f"{seen['chars']} characters, {seen['height']}px tall, "
                   f"type {seen['font'][:28]}, buttons {seen['buttons'][:3]}",
            )
        browser.close()


# ══════════════════════════════════════════════════════════════════════════
# Chapter 13 — the error paths
# ══════════════════════════════════════════════════════════════════════════
def chapter_errors(w: World):
    R.chapter = "errors"

    not_found = [
        "/invoice/999999", "/invoice/999999/edit", "/invoice/999999/pdf",
        "/i/definitely-not-a-token", "/i/definitely-not-a-token/pdf",
        "/verify/definitely-not-a-token",
    ]
    wrong = []
    for path in not_found:
        response = w.a.get(path)
        if response.status_code not in (302, 404):
            wrong.append(f"{path} -> {response.status_code}")
    R.check("a URL that names nothing gives a clean 404 or redirect",
            not wrong, "; ".join(wrong) or f"{len(not_found)} probed",
            compared=len(not_found))

    R.check("the 404 page is the app's own, not a stack trace",
            b"Traceback" not in w.a.get("/invoice/999999").data)

    R.equal("GET on a POST-only route is 405",
            w.a.get("/invoice/1/mark-paid").status_code, 405)

    R.equal("a password reset for an unknown address does not confirm or deny",
            w.anon.post("/forgot", {"email": "nobody@nowhere.example"}
                        ).status_code, 302)
    R.equal("a made-up reset token is refused",
            w.anon.get("/reset/not-a-real-token").status_code, 302)

    # A logo that is not an image must be refused without breaking the save.
    bad_logo = (io.BytesIO(b"this is not a PNG"), "logo.png")
    response = w.a.client.post(
        "/invoices",
        data={
            "csrf_token": w.a.csrf(),
            "invoice_number": "ERR-LOGO", "bill_to": CLIENT_MARINE,
            "invoice_date": date.today().isoformat(),
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Work"], "item_quantity": ["1"],
            "item_rate": ["100.00"], "logo": bad_logo,
        },
        content_type="multipart/form-data",
        environ_base=w.a.env,
    )
    R.equal("an invoice with a corrupt logo upload still saves",
            response.status_code, 302)
    logo_inv = read(w.app, "ERR-LOGO")
    R.check("...with no logo attached rather than a broken one",
            logo_inv is not None
            and w.a.get(f"/invoice/{logo_inv.id}/logo").status_code == 404)
    if logo_inv:
        pdf = w.a.get(f"/invoice/{logo_inv.id}/pdf")
        R.check("...and the PDF still renders", pdf.status_code == 200)
        if pdf.status_code == 200:
            w.keep_pdf(pdf, logo_inv, "err-logo")

    # The webhook with no secret configured.
    no_secret = w.app.config["STRIPE_WEBHOOK_SECRET"]
    w.app.config["STRIPE_WEBHOOK_SECRET"] = ""
    response = deliver(w.app, checkout_event(1, "cs_x", 100))
    w.app.config["STRIPE_WEBHOOK_SECRET"] = no_secret
    R.tripwire(
        "an unconfigured webhook secret answers Stripe with a 500",
        response.status_code == 500,
        "a 5xx makes Stripe retry and eventually disable the endpoint, which "
        "then drops OTHER invoices' payments; the misconfiguration deserves "
        "a loud alarm but a 4xx answer",
    )


# ══════════════════════════════════════════════════════════════════════════
# Chapter 14 — the standing posture
#
# docs/invoicer-review.md left seven findings unfixed. Five of them are
# reachable from a request and are reproduced in the chapters above. The rest
# are structural — a column type, a declared dependency, a limiter backend —
# and a harness that only drives HTTP would report a clean run while every one
# of them was still true. So they are checked here, from the same run, and
# labelled as what they are: a configuration audit, not a runtime result.
# ══════════════════════════════════════════════════════════════════════════
def chapter_posture(w: World):
    R.chapter = "posture"

    # -- an SMTP password a workspace brings ------------------------------
    secret = "not-a-real-mailbox-password-9f2c"
    w.a.post("/account/email", {
        "email_from_name": "Halloway & Vance",
        "email_from_email": OWNER_A["email"],
        "email_reply_to": OWNER_A["email"],
        "smtp_host": "smtp.halloway-vance.example",
        "smtp_port": "587", "smtp_username": "billing",
        "smtp_password": secret,
    })
    with w.app.app_context():
        stored = User.query.filter_by(email=OWNER_A["email"]).one().smtp_password
    R.tripwire(
        "a workspace SMTP password is stored in the clear",
        stored == secret,
        "it comes back out of the users table byte for byte, so any database "
        "read — a backup, a support query, a Render dashboard session — "
        "yields working outbound mail credentials for every workspace",
    )
    R.check("...but it is at least not echoed back to the browser",
            secret not in w.a.get("/account").get_data(as_text=True))
    w.a.post("/account/email", {
        "email_from_name": "", "email_from_email": "", "email_reply_to": "",
        "smtp_host": "", "smtp_port": "", "smtp_username": "",
        "smtp_password": "",
    })

    # -- two invoices, one number ------------------------------------------
    raise_invoice(w.a, "DUP-0007", CLIENT_DAIRY, [("Advice", 1, "100.00")])
    second = raise_invoice(w.a, "DUP-0007", CLIENT_MARINE,
                           [("Different work", 1, "9000.00")])
    with w.app.app_context():
        duplicates = Invoice.query.filter_by(
            user_id=w.a_id, invoice_number="DUP-0007").count()
    R.tripwire(
        "two different invoices can carry the same number",
        second.status_code == 302 and duplicates == 2,
        f"{duplicates} invoices in one account are both called DUP-0007, to "
        "two different clients, for $100.00 and $9,000.00 — nothing can "
        "reconcile that against a client's accounts payable, and it is "
        "usually noticed when somebody pays the wrong one",
    )

    # -- money stored as binary floating point ----------------------------
    from sqlalchemy import Float as SAFloat
    from models import LineItem as LI

    float_columns = sorted(
        f"{model.__tablename__}.{column.name}"
        for model in (Invoice, LI)
        for column in model.__table__.columns
        if isinstance(column.type, SAFloat)
    )
    R.tripwire(
        "every monetary column is a binary float, not a decimal",
        bool(float_columns),
        f"{', '.join(float_columns)} — this is the root of the lost cents the "
        "money chapter finds. Today the derived properties round at every "
        "step so the displayed parts always add up; the day anything sums "
        "these columns in SQL instead of in Python, that discipline is gone",
    )

    # -- rate limits that are not what they say ---------------------------
    storage = w.app.config.get("RATELIMIT_STORAGE_URI")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    workers = re.search(r"--workers\s+(\d+)", dockerfile)
    R.tripwire(
        "the configured rate limits are not the effective ones",
        storage == "memory://" and workers is not None
        and int(workers.group(1)) > 1,
        f"limits are held in {storage} while the Dockerfile runs "
        f"{workers.group(1) if workers else '?'} gunicorn workers, so each "
        "worker keeps its own counter: '10 per minute' on login is really 10 "
        "per worker per minute, and every deploy resets them",
    )

    # -- a dependency used but not declared -------------------------------
    declared = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("requirements.txt", "requirements-deploy.txt")
        if (ROOT / name).exists()
    ).lower()
    uses_pillow = "from PIL import" in (ROOT / "app.py").read_text(
        encoding="utf-8")
    R.tripwire(
        "Pillow is used for logo validation but never declared",
        uses_pillow and "pillow" not in declared,
        "it is present only transitively via the PDF engines; drop one of "
        "those and every raster logo upload is rejected silently, because "
        "the ImportError is caught by the same handler that catches a "
        "corrupt image",
    )


# ══════════════════════════════════════════════════════════════════════════
# Running it
# ══════════════════════════════════════════════════════════════════════════
CHAPTERS = [
    ("accounts", chapter_accounts),
    ("profile", chapter_profile),
    ("clients", chapter_clients),
    ("money", chapter_money),
    ("currency", chapter_currency),
    ("payments", chapter_payments),
    ("isolation", chapter_isolation),
    ("api", chapter_api),
    ("stripe", chapter_stripe),
    ("email", chapter_email),
    ("csv", chapter_csv),
    ("artifacts", chapter_artifacts),
    ("errors", chapter_errors),
    ("posture", chapter_posture),
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", default=str(ROOT / "out" / "exercise"),
        help="where the invoices and PDFs go. Keep it inside an ignored "
             "directory: everything written here is invoice-shaped.",
    )
    parser.add_argument("--only", help="run one chapter by name")
    parser.add_argument("--list", action="store_true",
                        help="list the chapters and exit")
    args = parser.parse_args(argv)

    if args.list:
        for name, function in CHAPTERS:
            first = (function.__doc__ or "").strip().splitlines()
            print(f"  {name:12} {first[0] if first else ''}")
        return 0

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print("Invoicer — scenario harness")
    print(f"  output      {out}")
    print(f"  database    throwaway SQLite, deleted and rebuilt each run")
    print(f"  stripe      local fake; webhooks signed locally and verified "
          f"by the real verifier")
    print(f"  email       captured at the SMTP transport, real MIME built")
    print()

    world = World(out)
    todo = [(n, f) for n, f in CHAPTERS if not args.only or n == args.only]
    if args.only and not todo:
        print(f"no chapter named {args.only!r}")
        return 2

    # Chapters build on one another (an account has to exist before an
    # invoice does), so a crash in one is reported and the run continues
    # rather than hiding everything after it.
    for name, function in todo:
        try:
            function(world)
        except Exception as exc:                              # noqa: BLE001
            R.chapter = name
            R.fail(f"the {name} chapter crashed",
                   traceback.format_exc().strip().splitlines()[-1])
            print(f"!! {name} crashed:\n{traceback.format_exc()}",
                  file=sys.stderr)

    # ── the report ───────────────────────────────────────────────────────
    (out / "report.json").write_text(
        json.dumps([r.__dict__ for r in R.rows], indent=2), encoding="utf-8"
    )

    width = max((len(r.check) for r in R.rows), default=20)
    width = min(max(width, 30), 78)
    current = None
    marks = {"ok": "  ", "FAIL": "!!", "KNOWN": "??", "skip": "--"}
    for row in R.rows:
        if row.chapter != current:
            current = row.chapter
            print(f"\n── {current} " + "─" * max(0, 66 - len(current)))
        print(f"{marks.get(row.verdict, '  ')} {row.check:<{width}} "
              f"{row.verdict}")
        if row.detail and row.verdict != "ok":
            print(f"     {row.detail}")

    counts = {verdict: sum(1 for r in R.rows if r.verdict == verdict)
              for verdict in ("ok", "FAIL", "KNOWN", "skip")}
    print("\n" + "=" * 72)
    print(f"{len(R.rows)} checks over {len(todo)} chapters — "
          f"{counts['ok']} ok · {counts['FAIL']} FAILED · "
          f"{counts['KNOWN']} known · {counts['skip']} not checked")
    print(f"{R.compared_total} things compared "
          f"(routes, invoices, PDFs, signatures, rows)")
    print(f"{len(world.pdfs)} PDFs produced AND opened; "
          f"{count_invoices(world.app)} invoices raised across 2 accounts")

    if counts["KNOWN"]:
        print("\nKnown, documented, deliberately not fixed "
              "(docs/invoicer-scenarios.md):")
        for row in R.rows:
            if row.verdict == "KNOWN":
                print(f"  ?? [{row.chapter}] {row.check}")
                print(f"       {row.detail}")
    if counts["skip"]:
        print("\nNot checked by this run:")
        for row in R.rows:
            if row.verdict == "skip":
                print(f"  -- [{row.chapter}] {row.check}")
                print(f"       {row.detail}")

    if R.failures:
        print(f"\n{len(R.failures)} SURPRISES — these are the ones to read:")
        for row in R.failures:
            print(f"  !! [{row.chapter}] {row.check}")
            print(f"       {row.detail}")
        print(f"\nEverything produced is in {out}")
        return 1

    print(f"\nNo surprises. Everything produced is in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
