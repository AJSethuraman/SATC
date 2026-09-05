"""Flask invoice generator application.

Run locally with::

    flask --app app run

See README.md for setup, environment variables, deployment, and Stripe
webhook testing instructions.
"""
import csv
import io
import logging
import math
import mimetypes
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import CSRFProtect
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from markupsafe import Markup, escape

import email_utils
import stripe_utils
from config import Config
from currencies import CURRENCY_CHOICES, CURRENCIES, symbol_for
from designs import DEFAULT_DESIGN, FAMILIES, all_designs, resolve
from helpers import (
    currency_symbol,
    format_money,
    parse_date,
    parse_money,
)
from models import Invoice, LineItem, User, db

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# App logger -> stdout at INFO so Render/gunicorn captures it. Child loggers
# (e.g. "invoicer.email") propagate up to this handler.
logger = logging.getLogger("invoicer")


def _configure_logging(app):
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)


ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


def nl2br(value):
    """Escape text and convert newlines to <br> (for engines without
    CSS ``white-space`` support, e.g. xhtml2pdf)."""
    if value is None:
        return ""
    text = str(escape(value)).replace("\r\n", "<br>").replace("\n", "<br>")
    return Markup(text)


def fmtdate(value, fmt="%b %d, %Y"):
    """Format a date/datetime for display (e.g. ``Apr 14, 2026``). Blank for
    None. Used by the web templates, the PDF, and the email."""
    if not value:
        return ""
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def _ensure_schema():
    """Additive, idempotent, race-safe migration for columns introduced after
    the first deploy. Avoids pulling in a full migration tool for a couple of
    columns, and works on both SQLite and PostgreSQL.

    Crucially this must never crash app startup: multiple gunicorn workers boot
    at once, so two may try to add the same column concurrently. Each change is
    wrapped so a "column already exists" race is treated as success.

    Existing accounts are grandfathered in as already email-verified so that
    enabling verification never locks current users out.
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import SQLAlchemyError

    def column_exists(table, col):
        try:
            cols = {c["name"] for c in inspect(db.engine).get_columns(table)}
            return col in cols
        except Exception:
            return True  # can't inspect (e.g. no table yet) -> skip DDL

    def safe_exec(statements):
        try:
            for stmt in statements:
                db.session.execute(text(stmt))
            db.session.commit()
        except SQLAlchemyError:
            # Another worker likely applied this concurrently; ignore.
            db.session.rollback()

    if not column_exists("users", "email_verified"):
        safe_exec(
            [
                "ALTER TABLE users ADD COLUMN email_verified BOOLEAN",
                "UPDATE users SET email_verified = TRUE "
                "WHERE email_verified IS NULL",
            ]
        )
    if not column_exists("users", "plan"):
        safe_exec(
            [
                "ALTER TABLE users ADD COLUMN plan VARCHAR(32)",
                "UPDATE users SET plan = 'free' WHERE plan IS NULL",
            ]
        )
    if not column_exists("users", "stripe_account_id"):
        safe_exec(
            ["ALTER TABLE users ADD COLUMN stripe_account_id VARCHAR(64)"]
        )
    if not column_exists("users", "stripe_charges_enabled"):
        safe_exec(
            [
                "ALTER TABLE users ADD COLUMN stripe_charges_enabled BOOLEAN",
                "UPDATE users SET stripe_charges_enabled = FALSE "
                "WHERE stripe_charges_enabled IS NULL",
            ]
        )
    if not column_exists("invoices", "paid_session_ids"):
        safe_exec(
            ["ALTER TABLE invoices ADD COLUMN paid_session_ids TEXT"]
        )
    if not column_exists("invoices", "client_email"):
        safe_exec(["ALTER TABLE invoices ADD COLUMN client_email VARCHAR(255)"])
    # The design gallery (designs.py). Both are nullable with no backfill:
    # designs.resolve(None) returns the pre-gallery look, so an existing row
    # needs no value to keep printing exactly as it always did. Nullable is
    # also what makes these safe under a rolling deploy — gunicorn runs two
    # workers and _ensure_schema runs per worker at boot, so for a moment one
    # worker is inserting rows without these columns.
    #
    # NOTE FOR THE NEXT COLUMN: this function knows nothing about the models.
    # It ALTERs only the names hardcoded here, and db.create_all() creates
    # missing TABLES but never alters an existing one. A column added to
    # models.py without a block here brings down every query against the table
    # in production Postgres with UndefinedColumn, while passing every local
    # test on a SQLite file that was created fresh from the models.
    if not column_exists("invoices", "design"):
        safe_exec(["ALTER TABLE invoices ADD COLUMN design VARCHAR(64)"])
    if not column_exists("invoices", "doc_title"):
        safe_exec(["ALTER TABLE invoices ADD COLUMN doc_title VARCHAR(40)"])
    if not column_exists("invoices", "stripe_account_id"):
        safe_exec(
            ["ALTER TABLE invoices ADD COLUMN stripe_account_id VARCHAR(64)"]
        )
        # Stamp the owner's current connected account onto invoices that
        # already have an in-flight Checkout session, so a payment completing
        # after this deploy still credits even if they later disconnect.
        safe_exec(
            [
                "UPDATE invoices SET stripe_account_id = ("
                "SELECT users.stripe_account_id FROM users "
                "WHERE users.id = invoices.user_id) "
                "WHERE stripe_session_id IS NOT NULL "
                "AND (stripe_account_id IS NULL OR stripe_account_id = '')"
            ]
        )
    # Account-level business profile columns.
    for col, ddl in [
        ("business_name", "ALTER TABLE users ADD COLUMN business_name VARCHAR(200)"),
        ("business_email", "ALTER TABLE users ADD COLUMN business_email VARCHAR(255)"),
        ("business_address", "ALTER TABLE users ADD COLUMN business_address TEXT"),
        ("tax_id", "ALTER TABLE users ADD COLUMN tax_id VARCHAR(80)"),
        ("default_currency", "ALTER TABLE users ADD COLUMN default_currency VARCHAR(8)"),
        ("default_terms", "ALTER TABLE users ADD COLUMN default_terms VARCHAR(120)"),
        # Per-workspace email sender (white-label foundation).
        ("email_from_name", "ALTER TABLE users ADD COLUMN email_from_name VARCHAR(120)"),
        ("email_from_email", "ALTER TABLE users ADD COLUMN email_from_email VARCHAR(255)"),
        ("email_reply_to", "ALTER TABLE users ADD COLUMN email_reply_to VARCHAR(255)"),
        ("smtp_host", "ALTER TABLE users ADD COLUMN smtp_host VARCHAR(255)"),
        ("smtp_port", "ALTER TABLE users ADD COLUMN smtp_port INTEGER"),
        ("smtp_username", "ALTER TABLE users ADD COLUMN smtp_username VARCHAR(255)"),
        ("smtp_password", "ALTER TABLE users ADD COLUMN smtp_password VARCHAR(255)"),
    ]:
        if not column_exists("users", col):
            safe_exec([ddl])
    # Backfill the idempotency key for invoices already credited from a Stripe
    # session before this column existed, so a post-deploy webhook retry of
    # that same session isn't counted again. Idempotent (only fills blanks);
    # kept separate so a failure can't roll back the grandfather updates.
    if column_exists("invoices", "paid_session_ids"):
        safe_exec(
            [
                "UPDATE invoices SET paid_session_ids = stripe_session_id "
                "WHERE stripe_session_id IS NOT NULL "
                "AND (paid_session_ids IS NULL OR paid_session_ids = '') "
                "AND (status = 'Paid' OR amount_paid > 0)"
            ]
        )

    # Grandfather any pre-existing accounts regardless of which worker added
    # the columns (idempotent; only touches rows left NULL by ALTER). This is
    # what guarantees current users aren't locked out when verification turns
    # on. New signups insert an explicit value, so they're unaffected.
    safe_exec(
        [
            "UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL",
            "UPDATE users SET plan = 'free' WHERE plan IS NULL",
            "UPDATE users SET stripe_charges_enabled = FALSE "
            "WHERE stripe_charges_enabled IS NULL",
        ]
    )


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    _configure_logging(app)

    # Transient directory for generated PDFs (regenerated on demand).
    app.config["INVOICES_DIR"].mkdir(parents=True, exist_ok=True)

    # If a SQLite database lives in a subdirectory, ensure it exists.
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////:"):
        db_path = uri.replace("sqlite:///", "", 1)
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Secure session cookies in production (served over HTTPS).
    if app.config.get("ENV") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True
        # Refuse to serve production traffic on the development fallback
        # secret. SECRET_KEY signs session cookies AND the /i/<token> public
        # invoice links, so a known key means anyone can mint a session for
        # any account and read any invoice by guessing its integer id. Render's
        # blueprint sets FLASK_SECRET_KEY via generateValue, so this can only
        # fire on a hand-rolled deploy that forgot it — where failing loudly at
        # boot is far better than quietly serving forgeable sessions.
        #
        # Caught by tests/test_scenarios.py::
        #   test_production_refuses_to_boot_on_the_development_secret_key
        if app.config.get("SECRET_KEY") in (None, "", "dev-only-change-me"):
            raise RuntimeError(
                "FLASK_SECRET_KEY must be set to a strong random value when "
                "APP_ENV=production — refusing to start on the development "
                "default, which would make session cookies and public invoice "
                "links forgeable."
            )

    # Error monitoring (optional).
    if app.config.get("SENTRY_DSN"):
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=app.config["SENTRY_DSN"],
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.0,
        )

    db.init_app(app)
    csrf.init_app(app)
    # Flask-Limiter reads RATELIMIT_STORAGE_URI from app.config.
    limiter.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.login_message_category = "error"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.jinja_env.globals.update(
        format_money=format_money,
        currency_symbol=currency_symbol,
        # The 157-currency table. `currency_symbol` only knows 14 and returns
        # an empty string for anything else, which would print a bare number
        # with no indication of what money it is.
        symbol_for=symbol_for,
    )
    app.jinja_env.filters["nl2br"] = nl2br
    app.jinja_env.filters["fmtdate"] = fmtdate

    with app.app_context():
        db.create_all()
        _ensure_schema()

    register_routes(app)

    from api import api_bp

    app.register_blueprint(api_bp)
    # The JSON API authenticates with its own key, and Stripe signs its
    # webhook — exempt both from CSRF (which is for browser form posts).
    csrf.exempt(api_bp)
    return app


# --------------------------------------------------------------------------
# Form handling
# --------------------------------------------------------------------------
def _read_logo(file_storage):
    """Return (bytes, mimetype) for a valid uploaded logo, or (None, None).

    Raster images are verified with Pillow so a corrupt file can't get stored
    and later break PDF rendering. SVGs are passed through unchecked.
    """
    if not file_storage or not file_storage.filename:
        return None, None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        return None, None
    data = file_storage.read()
    if not data:
        return None, None
    mime = (
        file_storage.mimetype
        or mimetypes.guess_type(file_storage.filename)[0]
        or "image/png"
    )
    if mime != "image/svg+xml":
        # A MISSING LIBRARY IS NOT A CORRUPT IMAGE, and it used to be reported
        # as one: `PIL` was imported here and declared in neither requirements
        # file -- present only transitively via the PDF engines. Drop one of
        # those and every raster logo upload is rejected, silently, with the
        # ImportError swallowed by the same handler that catches a real
        # corrupt file. The owner would be told their logo was broken.
        #
        # Pillow is declared now, and the two failures are told apart: a
        # genuinely unreadable image is skipped as before, and an absent
        # library raises rather than pretending to be a verdict about the
        # file.
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - a broken install
            raise RuntimeError(
                "Pillow is not installed, so raster logos cannot be checked. "
                "This is a broken install, not a bad image — see "
                "requirements.txt.") from exc
        try:
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            return None, None  # corrupt / unreadable image -> skip
    return data, mime


def _due_from_terms(issue_date, terms, custom):
    """Derive a due date from payment terms (Net N / Due on receipt) or an
    explicit custom date."""
    import re as _re
    from datetime import timedelta

    custom_date = parse_date(custom)
    if custom_date:
        return custom_date
    t = (terms or "").lower()
    if "receipt" in t:
        return issue_date
    m = _re.search(r"net\s*(\d+)", t)
    if m:
        return issue_date + timedelta(days=int(m.group(1)))
    return None


def _populate_invoice_from_form(
    invoice, form, files=None, sender=None, currency=None
):
    """Fill an Invoice instance from submitted form data (create or edit).

    Returns a list of validation errors raised by the *parsing* itself (a
    money box that was filled in but does not hold a number, or line-item
    arrays that do not line up). They are handed to ``_validate_invoice``
    rather than raised, so the owner gets them alongside the other messages
    on the re-rendered form.

    ## Two front doors, one function

    ``sender`` and ``currency`` used to be read straight off ``current_user``
    here. They are parameters now because the anonymous generator has no
    logged-in user: it collects the sender block and the currency on the
    document itself. Passing them in is what lets the signed-out editor reuse
    this function *exactly* — the same coercion, the same refusals, the same
    line-item reconstruction — instead of growing a second parser beside it.
    That mattered before: the web form and the JSON API once had separate
    money coercion with separate holes, which is why ``helpers.parse_money``
    exists at all. A third one would have been a third set of holes.

    Both default to the logged-in user's values when omitted, so the owner's
    form calls this exactly as it always did.

    ## Fields are only written when the form actually carries them

    Several fields below are guarded by ``in form`` rather than read with a
    default. That guard is load-bearing for money: the owner's form does not
    post ``amount_paid``, so reading it with a default of 0.0 would silently
    zero a Stripe-confirmed payment every time somebody edited a part-paid
    invoice — the edit would look successful and the balance due would jump
    back to the full amount. Absent means "leave alone", not "set to zero".
    """
    errors = []

    def money(field_name, label):
        value, ok = parse_money(form.get(field_name))
        if not ok:
            errors.append(
                f"{label} must be a number — "
                f"'{(form.get(field_name) or '').strip()[:40]}' is not one."
            )
        return value

    invoice.invoice_number = (form.get("invoice_number") or "").strip()
    invoice.from_info = (
        current_user.from_info if sender is None else (sender or "").strip()
    )
    invoice.bill_to = (form.get("bill_to") or "").strip()
    invoice.client_email = (form.get("client_email") or "").strip()
    if "ship_to" in form:
        invoice.ship_to = (form.get("ship_to") or "").strip()

    invoice.invoice_date = parse_date(form.get("invoice_date")) or date.today()
    invoice.payment_terms = (form.get("payment_terms") or "").strip()
    invoice.due_date = _due_from_terms(
        invoice.invoice_date, invoice.payment_terms, form.get("due_date")
    )
    invoice.po_number = (form.get("po_number") or "").strip()
    invoice.currency = (
        (current_user.default_currency if currency is None else currency)
        or "USD"
    ).strip().upper()

    # Tax and discount default to percentages, which is what the owner's form
    # posts (it has no flat/percent control). The generator does have one, so
    # honour it when the form carries it. A missing box is not "flat" — it is
    # the older front door not asking, and flipping the meaning of a tax value
    # because a checkbox was absent would restate the tax on every edit.
    invoice.tax_value = money("tax", "Tax")
    if "tax_is_percent" in form:
        invoice.tax_is_percent = form.get("tax_is_percent") == "1"
    else:
        invoice.tax_is_percent = True
    invoice.discount_value = money("discount", "Discount")
    if "discount_is_percent" in form:
        invoice.discount_is_percent = form.get("discount_is_percent") == "1"
    else:
        invoice.discount_is_percent = True
    invoice.shipping = money("shipping", "Shipping")
    # See the docstring: absent means leave alone, never zero.
    if "amount_paid" in form:
        invoice.amount_paid = money("amount_paid", "Amount paid")

    if "design" in form:
        invoice.design = resolve(form.get("design"))["id"]
    if "doc_title" in form:
        title = (form.get("doc_title") or "").strip().upper()[:40]
        invoice.doc_title = title or "INVOICE"

    invoice.notes = (form.get("notes") or "").strip()
    invoice.terms = (form.get("terms") or "").strip()

    # Logo: keep existing unless a new file is uploaded; allow clearing.
    if form.get("remove_logo") == "1":
        invoice.logo_data = None
        invoice.logo_mimetype = None
    if files:
        data, mime = _read_logo(files.get("logo"))
        if data:
            invoice.logo_data = data
            invoice.logo_mimetype = mime

    # Rebuild line items from the parallel form arrays.
    descriptions = form.getlist("item_description")
    quantities = form.getlist("item_quantity")
    rates = form.getlist("item_rate")

    # zip() truncates to the shortest array, so three descriptions, three
    # rates and two quantities silently produced a TWO-line invoice — the
    # third line, and its money, simply gone, with no error shown anywhere.
    # That is one disabled input or one browser quirk away from an invoice
    # being created, sent and paid at the wrong amount. Refuse instead:
    # inventing a blank quantity for the missing cell would be worse.
    #
    # Caught by tests/test_scenarios.py::
    #   test_mismatched_line_item_arrays_are_refused_not_silently_truncated
    if not (len(descriptions) == len(quantities) == len(rates)):
        errors.append(
            "The line items did not arrive intact "
            f"({len(descriptions)} descriptions, {len(quantities)} "
            f"quantities, {len(rates)} rates). Nothing was saved — reload "
            "the form and re-enter the lines."
        )

    invoice.items.clear()
    position = 0
    for index, (desc, qty, rate) in enumerate(
        zip(descriptions, quantities, rates), start=1
    ):
        desc = (desc or "").strip()
        qty_f, qty_ok = parse_money(qty)
        rate_f, rate_ok = parse_money(rate)
        if not qty_ok:
            errors.append(
                f"Line {index}: quantity must be a number — "
                f"'{str(qty).strip()[:40]}' is not one."
            )
        if not rate_ok:
            errors.append(
                f"Line {index}: rate must be a number — "
                f"'{str(rate).strip()[:40]}' is not one."
            )
        # A ROW NOBODY TYPED IN IS NOT A LINE ITEM. The form defaults every
        # row's quantity to 1, and this used to require the quantity to be 0
        # as well -- so an untouched row became a line with an empty
        # description and $0.00, and printed as a blank row on the client's
        # PDF. What makes a row real is a description or a rate; the quantity
        # alone is the form's own default talking.
        if not desc and rate_f == 0:
            continue
        invoice.items.append(
            LineItem(
                position=position,
                description=desc,
                quantity=qty_f,
                rate=rate_f,
            )
        )
        position += 1
    return errors


def _validate_invoice(invoice, parse_errors=None, anonymous=False):
    """Return a list of human-readable validation errors.

    ``parse_errors`` carries anything ``_populate_invoice_from_form`` could
    not make sense of. They come first because every later check reads totals
    computed from the values that *did* parse, so they would otherwise be
    reported against numbers nobody typed.
    """
    errors = list(parse_errors or [])
    if not invoice.invoice_number:
        errors.append("Invoice number is required.")
    if not invoice.from_info:
        # The fix differs by front door, and "go to Account" is useless advice
        # to somebody who has no account and is looking straight at the box
        # they need to fill in.
        errors.append(
            "Add your business name at the top of the invoice."
            if anonymous
            else "Add your business profile in Account first."
        )
    if not invoice.bill_to:
        errors.append("'Bill To' client information is required.")
    if not invoice.items:
        errors.append("At least one line item is required.")
    # A percentage discount above 100 drives the taxable base negative, which
    # then produces a negative tax and a negative total — an "invoice" that
    # says the business owes the client. Nothing downstream expects that: the
    # PDF renders it, the CSV exports it, and the History KPIs subtract it from
    # the outstanding figure, quietly understating what is owed across the
    # whole book. Negative line items stay allowed (they are how credits and
    # adjustments are entered); only a negative bottom line is rejected.
    #
    # Caught by tests/test_scenarios.py::
    #   test_discount_over_one_hundred_percent_is_rejected
    if invoice.discount_is_percent and (invoice.discount_value or 0) > 100:
        errors.append("A percentage discount cannot exceed 100%.")
    if (invoice.discount_value or 0) < 0:
        errors.append("Discount cannot be negative.")
    if (invoice.tax_value or 0) < 0:
        errors.append("Tax cannot be negative.")
    # A finite rate can still overflow on multiply: 1e308 x 10 is inf, and
    # inf * 0% tax is nan. `nan < 0` is False, so the negative-total guard
    # below waves it through, the row is stored, and every KPI on the History
    # page that sums balances then reads "$nan" — for the whole account, not
    # just this invoice. Check the number is real before comparing it.
    #
    # Caught by tests/test_scenarios.py::
    #   test_an_overflowing_rate_cannot_produce_a_nan_invoice
    if not errors and not math.isfinite(invoice.total):
        errors.append(
            "Invoice total is not a real amount — one of the quantities or "
            "rates is too large to bill."
        )
    if not errors and invoice.total < 0:
        errors.append(
            "Invoice total cannot be negative — check the line items, "
            "discount, and shipping."
        )
    return errors


def generate_pdf(app, invoice, pay_url=None):
    """Render the invoice PDF to a transient file and return its path.

    Shared by the web UI and the JSON API. Requires an active app context.
    """
    from pdf import render_invoice_pdf

    # invoice_number is free text, so it reaches this filename. Replacing "/"
    # alone left the Windows separator through: a number of "..\..\evil" wrote
    # the PDF outside INVOICES_DIR on the Windows run.ps1 path, and the same
    # string is handed back as the download_name. Keep only characters that are
    # safe on every platform.
    #
    # Caught by tests/test_scenarios.py::
    #   test_pdf_filename_cannot_escape_the_invoices_directory
    import re as _re

    safe_number = _re.sub(r"[^A-Za-z0-9._-]", "-", invoice.invoice_number or "")
    safe_number = safe_number.strip(".-") or "invoice"
    fname = f"invoice_{safe_number}_{invoice.id}.pdf"
    out_path = app.config["INVOICES_DIR"] / fname
    render_invoice_pdf(invoice, out_path, pay_url=pay_url)
    return out_path


def _csv_safe(value):
    """Neutralise spreadsheet formula injection in an exported CSV field.

    Excel / LibreOffice / Sheets execute a cell whose text begins with =, +,
    -, @, or a leading tab/CR. ``bill_to`` and ``invoice_number`` are free
    text — and via the JSON API they can be written by a third-party system,
    not just by the account owner — so a field like ``=cmd|'/c calc'!A1``
    reaches the accountant's spreadsheet as a live formula. Prefixing with an
    apostrophe makes the cell inert while still displaying the original text.

    Caught by tests/test_scenarios.py::
      test_csv_export_neutralises_spreadsheet_formula_injection
    """
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def next_invoice_number(user_id):
    """Suggest the next per-user invoice number (e.g. INV-0007).

    Derived from the highest number already issued, not from how many rows
    survive: counting reuses a number as soon as any invoice is deleted, so
    the account ends up with two different invoices both called INV-0003 —
    which breaks reconciliation against Drake and against the client's own
    accounts payable records.

    Caught by tests/test_scenarios.py::
      test_suggested_invoice_number_does_not_repeat_after_a_deletion
    """
    import re as _re

    highest = 0
    for (number,) in db.session.query(Invoice.invoice_number).filter_by(
        user_id=user_id
    ):
        match = _re.search(r"(\d+)\s*$", number or "")
        if match:
            highest = max(highest, int(match.group(1)))
    count = Invoice.query.filter_by(user_id=user_id).count()
    return f"INV-{max(highest, count) + 1:04d}"


# --- Signed tokens for email verification / password reset ----------------
def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def make_token(value, salt):
    return _serializer().dumps(value, salt=salt)


def read_token(token, salt, max_age=86400):
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def verification_enforced():
    """Whether new accounts must confirm their email before logging in.

    "auto" (default) enforces it only once SMTP is configured, so a fresh
    deploy without email never locks anyone out.
    """
    mode = (current_app.config.get("REQUIRE_EMAIL_VERIFICATION") or "auto").lower()
    if mode == "always":
        return True
    if mode == "never":
        return False
    return email_utils.is_configured(current_app.config)


def _send_verification(user):
    token = make_token(user.email, salt="email-verify")
    link = current_app.config["APP_BASE_URL"].rstrip("/") + url_for(
        "verify_email", token=token
    )
    email_utils.send_email(
        current_app.config,
        user.email,
        "Confirm your email",
        f"Welcome to Invoicer!\n\nConfirm your email to activate your "
        f"account:\n{link}\n\nThis link expires in 24 hours.",
    )


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
def register_routes(app):
    def owned_or_404(invoice_id):
        """Fetch an invoice that belongs to the current user, else 404."""
        invoice = db.session.get(Invoice, invoice_id)
        if invoice is None or invoice.user_id != current_user.id:
            abort(404)
        return invoice

    # --- Auth ----------------------------------------------------------
    @app.route("/signup", methods=["GET", "POST"])
    @limiter.limit("10 per hour", methods=["POST"])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("history"))
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            business_name = (request.form.get("business_name") or "").strip()
            agreed = request.form.get("agree")
            errors = []
            if "@" not in email or "." not in email:
                errors.append("Enter a valid email address.")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if not agreed:
                errors.append("Please accept the Terms and Privacy Policy.")
            if User.query.filter_by(email=email).first():
                errors.append("An account with that email already exists.")
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template(
                    "signup.html", email=email, business_name=business_name
                ), 400

            user = User(email=email)
            user.set_password(password)
            user.business_name = business_name
            user.business_email = email
            enforce = verification_enforced()
            user.email_verified = not enforce
            db.session.add(user)
            db.session.commit()

            if enforce:
                try:
                    _send_verification(user)
                    flash(
                        "Account created. Check your email for a link to "
                        "confirm your address before logging in.",
                        "success",
                    )
                except Exception:
                    # If the email can't go out, don't strand the user.
                    user.email_verified = True
                    db.session.commit()
                    login_user(user)
                    flash("Welcome! Your account is ready.", "success")
                    return redirect(url_for("history"))
                return redirect(url_for("login"))

            login_user(user)
            flash("Welcome! Your account is ready.", "success")
            return redirect(url_for("account"))
        return render_template("signup.html", email="", business_name="")

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per minute;50 per hour", methods=["POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("history"))
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            user = User.query.filter_by(email=email).first()
            if user is None or not user.check_password(password):
                flash("Invalid email or password.", "error")
                return render_template("login.html", email=email), 401
            if verification_enforced() and not user.email_verified:
                flash(
                    "Please confirm your email first. "
                    "Need a new link? Use 'Resend confirmation' below.",
                    "error",
                )
                return render_template(
                    "login.html", email=email, unverified=True
                ), 403
            login_user(user, remember=bool(request.form.get("remember")))
            nxt = request.args.get("next")
            # "starts with /" alone is not enough: "//evil.example.com/x" is a
            # protocol-relative URL, so the browser leaves the site entirely.
            # "/\evil.example.com" is treated the same way by some browsers.
            # A phishing link to /login?next=//evil.example.com lands the user
            # on an attacker's page immediately after a successful sign-in,
            # which is exactly when they are primed to trust it.
            #
            # Caught by tests/test_scenarios.py::
            #   test_login_next_parameter_cannot_redirect_off_site
            if (
                not nxt
                or not nxt.startswith("/")
                or nxt.startswith("//")
                or nxt.startswith("/\\")
            ):
                nxt = url_for("history")
            return redirect(nxt)
        return render_template("login.html", email="")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("Signed out.", "success")
        return redirect(url_for("login"))

    @app.route("/verify/<token>")
    def verify_email(token):
        email = read_token(token, salt="email-verify")
        if not email:
            flash("That confirmation link is invalid or expired.", "error")
            return redirect(url_for("login"))
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash("Account not found.", "error")
            return redirect(url_for("login"))
        if not user.email_verified:
            user.email_verified = True
            db.session.commit()
        flash("Email confirmed — you can log in now.", "success")
        return redirect(url_for("login"))

    @app.route("/resend-verification", methods=["POST"])
    @limiter.limit("5 per hour")
    def resend_verification():
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()
        # Always show the same message (don't reveal whether the email exists).
        if user and not user.email_verified and verification_enforced():
            try:
                _send_verification(user)
            except Exception:
                pass
        flash(
            "If that account needs confirmation, a new link is on its way.",
            "success",
        )
        return redirect(url_for("login"))

    @app.route("/forgot", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def forgot_password():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if user and email_utils.is_configured(app.config):
                token = make_token(user.email, salt="pw-reset")
                link = app.config["APP_BASE_URL"].rstrip("/") + url_for(
                    "reset_password", token=token
                )
                try:
                    email_utils.send_email(
                        app.config,
                        user.email,
                        "Reset your password",
                        f"Reset your Invoicer password here:\n{link}\n\n"
                        f"This link expires in 1 hour. If you didn't request "
                        f"this, ignore this email.",
                    )
                except Exception:
                    pass
            flash(
                "If an account exists for that email, a reset link has been "
                "sent.",
                "success",
            )
            return redirect(url_for("login"))
        return render_template(
            "forgot.html", email_configured=email_utils.is_configured(app.config)
        )

    @app.route("/reset/<token>", methods=["GET", "POST"])
    @limiter.limit("10 per hour", methods=["POST"])
    def reset_password(token):
        email = read_token(token, salt="pw-reset", max_age=3600)
        if not email:
            flash("That reset link is invalid or expired.", "error")
            return redirect(url_for("forgot_password"))
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash("Account not found.", "error")
            return redirect(url_for("forgot_password"))
        if request.method == "POST":
            password = request.form.get("password") or ""
            confirm = request.form.get("confirm") or ""
            if len(password) < 8:
                flash("Password must be at least 8 characters.", "error")
                return render_template("reset.html", token=token), 400
            if password != confirm:
                flash("Passwords do not match.", "error")
                return render_template("reset.html", token=token), 400
            user.set_password(password)
            user.email_verified = True  # proves control of the inbox
            db.session.commit()
            flash("Password updated — log in with your new password.", "success")
            return redirect(url_for("login"))
        return render_template("reset.html", token=token)

    # --- Legal ---------------------------------------------------------
    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/account")
    @login_required
    def account():
        return render_template(
            "account.html",
            stripe_configured=bool(app.config["STRIPE_SECRET_KEY"]),
            smtp_configured=email_utils.can_send(app.config, current_user),
            shared_email_configured=email_utils.is_configured(app.config),
        )

    @app.route("/account/regenerate-key", methods=["POST"])
    @login_required
    def regenerate_key():
        from models import generate_api_key

        current_user.api_key = generate_api_key()
        db.session.commit()
        flash("API key regenerated. Update any integrations.", "success")
        return redirect(url_for("account"))

    @app.route("/account/business", methods=["POST"])
    @login_required
    def account_business():
        current_user.business_name = (
            request.form.get("business_name") or ""
        ).strip()
        current_user.business_email = (
            request.form.get("business_email") or ""
        ).strip()
        current_user.business_address = (
            request.form.get("business_address") or ""
        ).strip()
        current_user.tax_id = (request.form.get("tax_id") or "").strip()
        current_user.default_currency = (
            request.form.get("default_currency") or "USD"
        ).strip().upper()
        current_user.default_terms = (
            request.form.get("default_terms") or ""
        ).strip()
        db.session.commit()
        flash("Business profile saved.", "success")
        return redirect(url_for("account"))

    @app.route("/account/email", methods=["POST"])
    @login_required
    def account_email():
        current_user.email_from_name = (
            request.form.get("email_from_name") or ""
        ).strip()
        current_user.email_from_email = (
            request.form.get("email_from_email") or ""
        ).strip()
        current_user.email_reply_to = (
            request.form.get("email_reply_to") or ""
        ).strip()
        current_user.smtp_host = (request.form.get("smtp_host") or "").strip()
        port = (request.form.get("smtp_port") or "").strip()
        current_user.smtp_port = int(port) if port.isdigit() else None
        current_user.smtp_username = (
            request.form.get("smtp_username") or ""
        ).strip()
        # Password field is write-only: a blank submission keeps the stored one.
        pw = request.form.get("smtp_password")
        if pw:
            current_user.smtp_password = pw.strip()
        db.session.commit()
        flash("Email settings saved.", "success")
        return redirect(url_for("account"))

    @app.route("/account/delete", methods=["POST"])
    @login_required
    def delete_account():
        # Permanently remove the user and (via cascade) all their invoices and
        # line items. Require the password so a stray click / stale session
        # can't wipe an account.
        password = request.form.get("password") or ""
        if not current_user.check_password(password):
            flash("Password incorrect — your account was not deleted.", "error")
            return redirect(url_for("account"))
        user = db.session.get(User, current_user.id)
        logout_user()
        db.session.delete(user)
        db.session.commit()
        flash(
            "Your account and all its invoices have been deleted.", "success"
        )
        return redirect(url_for("index"))

    # --- Stripe Connect (each user collects into their own account) -----
    @app.route("/connect/start", methods=["POST"])
    @login_required
    def connect_start():
        sk = app.config["STRIPE_SECRET_KEY"]
        if not sk:
            flash("Stripe isn't configured on this site yet.", "error")
            return redirect(url_for("account"))
        base = app.config["APP_BASE_URL"].rstrip("/")
        try:
            if not current_user.stripe_account_id:
                acct_id = stripe_utils.create_connect_account(
                    sk, current_user.email
                )
                current_user.stripe_account_id = acct_id
                db.session.commit()
            link = stripe_utils.create_account_link(
                sk,
                current_user.stripe_account_id,
                refresh_url=base + url_for("connect_refresh"),
                return_url=base + url_for("connect_return"),
            )
        except Exception as exc:  # pragma: no cover - Stripe/network errors
            flash(f"Could not start Stripe onboarding: {exc}", "error")
            return redirect(url_for("account"))
        return redirect(link)

    @app.route("/connect/refresh")
    @login_required
    def connect_refresh():
        # Onboarding links are single-use/expiring; mint a fresh one.
        sk = app.config["STRIPE_SECRET_KEY"]
        if not sk or not current_user.stripe_account_id:
            return redirect(url_for("account"))
        base = app.config["APP_BASE_URL"].rstrip("/")
        try:
            link = stripe_utils.create_account_link(
                sk,
                current_user.stripe_account_id,
                refresh_url=base + url_for("connect_refresh"),
                return_url=base + url_for("connect_return"),
            )
        except Exception:  # pragma: no cover
            return redirect(url_for("account"))
        return redirect(link)

    @app.route("/connect/return")
    @login_required
    def connect_return():
        sk = app.config["STRIPE_SECRET_KEY"]
        if sk and current_user.stripe_account_id:
            try:
                acct = stripe_utils.get_account(
                    sk, current_user.stripe_account_id
                )
                current_user.stripe_charges_enabled = bool(
                    getattr(acct, "charges_enabled", False)
                )
                db.session.commit()
            except Exception:  # pragma: no cover
                pass
        if current_user.can_accept_payments:
            flash("Stripe connected — you can accept payments now.", "success")
        else:
            flash(
                "Stripe onboarding isn't finished yet. You can resume it "
                "anytime from this page.",
                "error",
            )
        return redirect(url_for("account"))

    @app.route("/connect/dashboard")
    @login_required
    def connect_dashboard():
        # Standard connected accounts have their own full Stripe Dashboard;
        # send the user there to sign in (no Express login link needed).
        if not current_user.stripe_account_id:
            return redirect(url_for("account"))
        return redirect("https://dashboard.stripe.com/")

    @app.route("/connect/disconnect", methods=["POST"])
    @login_required
    def connect_disconnect():
        # Forget the linked account on our side (the account still exists in
        # the user's own Stripe). Lets them reconnect a different account.
        current_user.stripe_account_id = None
        current_user.stripe_charges_enabled = False
        db.session.commit()
        flash("Stripe disconnected. You can reconnect anytime.", "success")
        return redirect(url_for("account"))

    # --- Landing / invoices --------------------------------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("history"))
        return render_template("landing.html")

    def _require_profile():
        if not current_user.has_business_profile:
            flash(
                "Add your business details first — they appear on every "
                "invoice.",
                "error",
            )
            return False
        return True

    @app.route("/new")
    @login_required
    def new_invoice():
        if not _require_profile():
            return redirect(url_for("account"))
        suggested = next_invoice_number(current_user.id)
        return render_template(
            "invoice_form.html",
            invoice=None,
            suggested_number=suggested,
            today=date.today().isoformat(),
        )

    @app.route("/invoices", methods=["POST"])
    @login_required
    def create_invoice():
        if not _require_profile():
            return redirect(url_for("account"))
        invoice = Invoice(user_id=current_user.id)
        parse_errors = _populate_invoice_from_form(
            invoice, request.form, request.files
        )
        errors = _validate_invoice(invoice, parse_errors)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "invoice_form.html",
                invoice=invoice,
                suggested_number=invoice.invoice_number,
                today=date.today().isoformat(),
            ), 400
        db.session.add(invoice)
        db.session.commit()
        logger.info(
            "invoice created id=%s number=%s user=%s total=%s %s",
            invoice.id, invoice.invoice_number, current_user.id,
            invoice.total, invoice.currency,
        )
        flash("Invoice created.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/invoice/<int:invoice_id>")
    @login_required
    def view_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        return render_template(
            "invoice_detail.html",
            invoice=invoice,
            public_url=_public_url(invoice),
            stripe_configured=bool(app.config["STRIPE_SECRET_KEY"]),
            smtp_configured=email_utils.can_send(app.config, current_user),
        )

    @app.route("/invoice/<int:invoice_id>/logo")
    @login_required
    def invoice_logo(invoice_id):
        invoice = owned_or_404(invoice_id)
        if not invoice.logo_data:
            abort(404)
        return send_file(
            io.BytesIO(invoice.logo_data),
            mimetype=invoice.logo_mimetype or "image/png",
        )

    @app.route("/invoice/<int:invoice_id>/edit")
    @login_required
    def edit_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        return render_template(
            "invoice_form.html",
            invoice=invoice,
            suggested_number=invoice.invoice_number,
            today=date.today().isoformat(),
        )

    @app.route("/invoice/<int:invoice_id>", methods=["POST"])
    @login_required
    def update_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        parse_errors = _populate_invoice_from_form(
            invoice, request.form, request.files
        )
        errors = _validate_invoice(invoice, parse_errors)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "invoice_form.html",
                invoice=invoice,
                suggested_number=invoice.invoice_number,
                today=date.today().isoformat(),
            ), 400
        # An edit can raise the total above what has already been paid (add a
        # line item to a settled invoice, remove a discount, bump a rate). The
        # stored status is not derived, so without this the invoice keeps
        # showing "Paid" while money is owed — and the History KPIs skip it,
        # because outstanding only sums invoices whose status != "Paid". Reopen
        # it so the balance is visible and chaseable. The reverse case (an edit
        # that lowers the total to at or below what was paid) settles it.
        #
        # Caught by tests/test_scenarios.py::
        #   test_editing_a_paid_invoice_upward_reopens_it
        if invoice.balance_due > 0 and invoice.status == "Paid":
            invoice.status = "Sent"
        elif (
            invoice.status != "Paid"
            and (invoice.amount_paid or 0) > 0
            and invoice.balance_due <= 0
        ):
            invoice.status = "Paid"
        db.session.commit()
        flash("Invoice updated.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/invoice/<int:invoice_id>/delete", methods=["POST"])
    @login_required
    def delete_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        db.session.delete(invoice)
        db.session.commit()
        flash("Invoice deleted.", "success")
        return redirect(url_for("history"))

    def _generate_pdf(invoice, pay_url=None):
        return generate_pdf(app, invoice, pay_url=pay_url)

    @app.route("/invoice/<int:invoice_id>/pdf")
    @login_required
    def download_pdf(invoice_id):
        invoice = owned_or_404(invoice_id)
        try:
            out_path = _generate_pdf(invoice, pay_url=_public_url(invoice))
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_path.name,
            mimetype="application/pdf",
        )

    @app.route("/invoice/<int:invoice_id>/mark-paid", methods=["POST"])
    @login_required
    def mark_paid(invoice_id):
        invoice = owned_or_404(invoice_id)
        invoice.status = "Paid"
        invoice.amount_paid = invoice.total
        db.session.commit()
        flash("Invoice marked as paid.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/invoice/<int:invoice_id>/mark-unpaid", methods=["POST"])
    @login_required
    def mark_unpaid(invoice_id):
        # Reverse a "mark as paid": clear the recorded payment and reopen the
        # invoice. We keep paid_session_ids so a stale Stripe webhook retry of
        # an already-seen session can't silently re-credit it.
        invoice = owned_or_404(invoice_id)
        invoice.status = "Sent"
        invoice.amount_paid = 0.0
        # Drop the spent Checkout Session so nothing copies/sends a dead link;
        # a fresh session is created on demand when the invoice is paid again.
        invoice.stripe_session_id = None
        invoice.stripe_payment_url = None
        db.session.commit()
        flash("Invoice marked as unpaid.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/invoice/<int:invoice_id>/email", methods=["POST"])
    @login_required
    def email_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        to_email = (
            request.form.get("to_email") or invoice.client_email or ""
        ).strip()
        if not to_email:
            flash("Recipient email is required.", "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))

        public_url = _public_url(invoice)
        try:
            out_path = _generate_pdf(invoice, pay_url=public_url)
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))

        html_body = render_template(
            "email_invoice.html",
            invoice=invoice,
            public_url=public_url,
            can_pay=current_user.can_accept_payments,
        )
        try:
            email_utils.send_invoice_email(
                app.config,
                to_email,
                invoice,
                out_path,
                payment_url=public_url,
                html_body=html_body,
                user=current_user,
            )
        except Exception as exc:  # SMTP errors vary; log fully, don't swallow.
            logger.exception(
                "invoice send FAILED id=%s to=%s: %s",
                invoice.id, email_utils.mask_email(to_email), exc,
            )
            flash(f"Email failed: {exc}", "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))

        # Remember the recipient and mark as sent.
        if not invoice.client_email:
            invoice.client_email = to_email
        if invoice.status == "Draft":
            invoice.status = "Sent"
        db.session.commit()
        logger.info(
            "invoice sent id=%s number=%s to=%s",
            invoice.id, invoice.invoice_number, email_utils.mask_email(to_email),
        )
        flash(f"Invoice emailed to {to_email}.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    # --- Public invoice page (no login; the link shared with the client) ---
    PUBLIC_MAX_AGE = 60 * 60 * 24 * 365 * 5  # ~5 years

    def _public_url(invoice):
        token = make_token(invoice.id, salt="invoice-public")
        return app.config["APP_BASE_URL"].rstrip("/") + url_for(
            "public_invoice", token=token
        )

    def _invoice_from_token(token):
        inv_id = read_token(
            token, salt="invoice-public", max_age=PUBLIC_MAX_AGE
        )
        if inv_id is None:
            abort(404)
        invoice = db.session.get(Invoice, int(inv_id))
        if invoice is None:
            abort(404)
        return invoice

    @app.route("/i/<token>")
    def public_invoice(token):
        invoice = _invoice_from_token(token)
        can_pay = bool(invoice.owner and invoice.owner.can_accept_payments)
        return render_template(
            "public_invoice.html",
            invoice=invoice,
            can_pay=can_pay,
            token=token,
        )

    @app.route("/i/<token>/logo")
    def public_logo(token):
        invoice = _invoice_from_token(token)
        if not invoice.logo_data:
            abort(404)
        return send_file(
            io.BytesIO(invoice.logo_data),
            mimetype=invoice.logo_mimetype or "image/png",
        )

    @app.route("/i/<token>/pdf")
    def public_pdf(token):
        invoice = _invoice_from_token(token)
        try:
            out_path = generate_pdf(
                app, invoice, pay_url=_public_url(invoice)
            )
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("public_invoice", token=token))
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_path.name,
            mimetype="application/pdf",
        )

    @app.route("/i/<token>/pay", methods=["POST"])
    @csrf.exempt
    # Unauthenticated and CSRF-exempt by necessity (the client paying has no
    # account), and every hit creates a real Stripe Checkout Session on the
    # owner's connected account. Without a cap, anyone holding a public link
    # can drive unbounded Stripe API calls against that account and bury the
    # owner's Stripe dashboard in abandoned sessions.
    @limiter.limit("20 per hour")
    def public_pay(token):
        invoice = _invoice_from_token(token)
        owner = invoice.owner
        if not owner or not owner.can_accept_payments:
            flash("Online payment isn't set up for this invoice.", "error")
            return redirect(url_for("public_invoice", token=token))
        if invoice.balance_due <= 0:
            return redirect(url_for("public_invoice", token=token))
        base = app.config["APP_BASE_URL"].rstrip("/")
        pub = base + url_for("public_invoice", token=token)
        try:
            session = stripe_utils.create_checkout_session(
                invoice,
                app.config["STRIPE_SECRET_KEY"],
                app.config["APP_BASE_URL"],
                owner.stripe_account_id,
                app.config,
                success_url=pub + "?paid=1",
                cancel_url=pub + "?canceled=1",
            )
        except (RuntimeError, ValueError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("public_invoice", token=token))
        except Exception as exc:  # pragma: no cover - network/Stripe errors
            flash(f"Stripe error: {exc}", "error")
            return redirect(url_for("public_invoice", token=token))
        invoice.stripe_session_id = session.id
        invoice.stripe_payment_url = session.url
        invoice.stripe_account_id = owner.stripe_account_id
        if invoice.status == "Draft":
            invoice.status = "Sent"
        db.session.commit()
        logger.info(
            "payment link created invoice=%s session=%s account=%s amount=%s %s",
            invoice.id, session.id, owner.stripe_account_id,
            invoice.balance_due, invoice.currency,
        )
        return redirect(session.url)

    # ---- the signed-out invoice generator ------------------------------
    #
    # The app's front door used to be a login wall: you could not see an
    # invoice, never mind make one, without signing up first. This is the
    # other order — make the invoice, then decide whether you want an account
    # to send it and be paid for it. Nothing here writes to the database, and
    # nothing here needs an email address.

    def _join_block(name, rest):
        """Join a name line and an address block into one stored field.

        The document splits a party into a bold name line and the address
        under it, because that is how the printed invoice sets it. The model
        stores one text field. Joining here rather than in
        ``_populate_invoice_from_form`` keeps that function free of a branch
        it would only ever take for one caller.
        """
        parts = [(name or "").strip(), (rest or "").strip()]
        return "\n".join(p for p in parts if p)

    def _generator_invoice(raw, files=None):
        """Build an UNSAVED Invoice from the generator's form.

        Returns ``(invoice, errors)``. The invoice is transient: it is never
        added to a session, so nothing reaches the database on this path.
        ``tests/test_generator.py`` asserts the row count does not move.
        """
        form = raw.copy()
        form["bill_to"] = _join_block(
            raw.get("bill_to_name"), raw.get("bill_to_address")
        )
        form["ship_to"] = _join_block(
            raw.get("ship_to_name"), raw.get("ship_to_address")
        )
        sender = _join_block(raw.get("from_name"), raw.get("from_address"))

        invoice = Invoice()
        # Column defaults are applied by the database on INSERT, and this row
        # is never inserted — so a transient invoice starts with None in every
        # one of them. Set what the document reads before it is rendered.
        invoice.status = "Draft"
        invoice.amount_paid = 0.0
        invoice.tax_is_percent = True
        invoice.discount_is_percent = True
        errors = _populate_invoice_from_form(
            invoice,
            form,
            files=files,
            sender=sender,
            currency=raw.get("currency"),
        )
        return invoice, _validate_invoice(invoice, errors, anonymous=True)

    def _generator_context(invoice, errors=None):
        from pdf import _business_context

        design = resolve(
            invoice.design if invoice is not None else DEFAULT_DESIGN
        )
        return {
            "invoice": invoice,
            "business": _business_context(invoice, allow_svg=True),
            "design": design,
            "designs": all_designs(),
            "design_count": len(all_designs()),
            "families": FAMILIES,
            "doc_title": invoice.doc_title or "INVOICE",
            "currency_choices": CURRENCY_CHOICES,
            # Symbol and minor units for the live totals. The preview has to
            # know that the yen takes no decimals for the same reason the
            # gateway does.
            "currency_js": {
                c["code"]: {"s": c["symbol"], "d": c["decimals"]}
                for c in CURRENCIES.values()
            },
            "zero_money": format_money(0, invoice.currency or "USD"),
            "errors": errors or [],
        }

    @app.route("/generator")
    def generator():
        invoice = Invoice()
        invoice.status = "Draft"
        invoice.invoice_date = date.today()
        invoice.currency = (
            current_user.default_currency
            if current_user.is_authenticated
            else "USD"
        )
        invoice.design = DEFAULT_DESIGN
        invoice.doc_title = "INVOICE"
        invoice.amount_paid = 0.0
        # Stated, not left to the column defaults — this row is never inserted,
        # so those defaults never run and both flags would arrive as None. The
        # document renders the flat/percent control from them, and `not None`
        # is True, so a fresh page came up with BOTH set to flat: an 8.25 typed
        # into the tax box was billed as 8.25 of currency rather than 8.25%.
        # Percent for both matches what the signed-in form has always posted.
        invoice.tax_is_percent = True
        invoice.discount_is_percent = True
        invoice.tax_value = 0.0
        invoice.discount_value = 0.0
        invoice.shipping = 0.0
        invoice.payment_terms = "Net 14"
        invoice.due_date = _due_from_terms(date.today(), "Net 14", None)
        if current_user.is_authenticated:
            invoice.from_info = current_user.from_info
            invoice.invoice_number = next_invoice_number(current_user.id)
        return render_template("generator.html", **_generator_context(invoice))

    @app.route("/generator/theme.css")
    def generator_theme():
        """The document stylesheet for one design.

        The gallery fetches this and swaps it in, which is what makes a design
        change keep everything already typed: the markup is identical for
        every design, so only these rules move.
        """
        css = render_template(
            "_invoice_css.html", design=resolve(request.args.get("design"))
        )
        return Response(css, mimetype="text/css")

    @app.route("/generator/pdf", methods=["POST"])
    # An unauthenticated endpoint that renders a PDF is real work for anyone
    # who asks, so it is capped. The limit is generous enough that a person
    # iterating on one invoice will not meet it.
    @limiter.limit("40 per hour")
    def generator_pdf():
        invoice, errors = _generator_invoice(request.form, request.files)
        if errors:
            return (
                render_template(
                    "generator.html", **_generator_context(invoice, errors)
                ),
                422,
            )
        # Rendered into a temporary directory and returned as bytes: the
        # shared INVOICES_DIR names its files after the invoice id, and an
        # unsaved invoice has none — two anonymous senders would have written
        # over each other's file and downloaded the wrong invoice.
        from pdf import render_invoice_pdf

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "invoice.pdf"
            render_invoice_pdf(invoice, out)
            data = out.read_bytes()

        import re as _re

        stem = _re.sub(r"[^A-Za-z0-9._-]", "-", invoice.invoice_number or "")
        stem = stem.strip(".-") or "invoice"
        return Response(
            data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{stem}.pdf"',
                "Content-Length": str(len(data)),
            },
        )

    @app.route("/generator/save", methods=["POST"])
    @login_required
    def generator_save():
        """Keep a generated invoice against the signed-in account."""
        invoice, errors = _generator_invoice(request.form, request.files)
        if errors:
            return (
                render_template(
                    "generator.html", **_generator_context(invoice, errors)
                ),
                422,
            )
        invoice.user_id = current_user.id
        if not invoice.invoice_number:
            invoice.invoice_number = next_invoice_number(current_user.id)
        db.session.add(invoice)
        db.session.commit()
        flash("Invoice saved.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/history")
    @login_required
    def history():
        status = (request.args.get("status") or "all").lower()
        q = (request.args.get("q") or "").strip()
        invoices = (
            Invoice.query.filter_by(user_id=current_user.id)
            .order_by(Invoice.created_at.desc())
            .all()
        )
        if q:
            ql = q.lower()
            invoices = [
                inv
                for inv in invoices
                if ql in (inv.invoice_number or "").lower()
                or ql in (inv.bill_to or "").lower()
            ]
        if status != "all":
            invoices = [
                inv for inv in invoices if inv.display_status.lower() == status
            ]

        # KPIs across the user's invoices (computed in Python on the models).
        all_inv = Invoice.query.filter_by(user_id=current_user.id).all()
        outstanding = sum(
            i.balance_due for i in all_inv if i.status != "Paid"
        )
        overdue = sum(i.balance_due for i in all_inv if i.is_overdue)
        paid_total = sum(i.total for i in all_inv if i.status == "Paid")
        kpis = {
            "outstanding": outstanding,
            "outstanding_count": sum(
                1 for i in all_inv if i.status != "Paid" and i.balance_due > 0
            ),
            "overdue": overdue,
            "overdue_count": sum(1 for i in all_inv if i.is_overdue),
            "paid_total": paid_total,
            "total_count": len(all_inv),
        }
        return render_template(
            "invoices.html",
            invoices=invoices,
            kpis=kpis,
            status=status,
            q=q,
            currency=current_user.default_currency or "USD",
        )

    @app.route("/history/export.csv")
    @login_required
    def export_csv():
        invoices = (
            Invoice.query.filter_by(user_id=current_user.id)
            .order_by(Invoice.created_at.desc())
            .all()
        )
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "Invoice Number",
                "Date",
                "Bill To",
                "Currency",
                "Subtotal",
                "Discount",
                "Tax",
                "Shipping",
                "Total",
                "Amount Paid",
                "Balance Due",
                "Status",
            ]
        )
        for inv in invoices:
            bill_to_oneline = _csv_safe(" ".join((inv.bill_to or "").split()))
            writer.writerow(
                [
                    _csv_safe(inv.invoice_number),
                    inv.invoice_date.isoformat() if inv.invoice_date else "",
                    bill_to_oneline,
                    inv.currency,
                    f"{inv.subtotal:.2f}",
                    f"{inv.discount_amount:.2f}",
                    f"{inv.tax_amount:.2f}",
                    f"{(inv.shipping or 0):.2f}",
                    f"{inv.total:.2f}",
                    f"{(inv.amount_paid or 0):.2f}",
                    f"{inv.balance_due:.2f}",
                    inv.status,
                ]
            )
        output = io.BytesIO(buffer.getvalue().encode("utf-8"))
        return send_file(
            output,
            mimetype="text/csv",
            as_attachment=True,
            download_name="invoices.csv",
        )

    # --- Stripe webhook (unauthenticated; verified by signature) --------
    @app.route("/webhook/stripe", methods=["POST"])
    @csrf.exempt
    def stripe_webhook():
        payload = request.get_data()
        sig_header = request.headers.get("Stripe-Signature", "")
        webhook_secret = app.config["STRIPE_WEBHOOK_SECRET"]
        if not webhook_secret:
            logger.error(
                "stripe webhook received but STRIPE_WEBHOOK_SECRET is not "
                "configured — rejecting"
            )
            return ("Webhook secret not configured", 500)
        try:
            event = stripe_utils.construct_webhook_event(
                payload, sig_header, webhook_secret
            )
        except Exception as exc:  # invalid signature / payload
            logger.warning(
                "stripe webhook signature verification FAILED: %s", exc
            )
            return (f"Webhook error: {exc}", 400)

        event_type = event.get("type")
        logger.info(
            "stripe webhook signature verified: type=%s id=%s account=%s",
            event_type, event.get("id"), event.get("account"),
        )

        if event_type in (
            "checkout.session.completed",
            "checkout.session.async_payment_succeeded",
        ):
            session = event["data"]["object"]
            session_id = session.get("id")

            # Only credit money that has actually settled.
            #
            # checkout.session.completed also fires for delayed-notification
            # payment methods (ACH direct debit, SEPA, Bacs, Boleto, OXXO,
            # Konbini) at the moment the customer finishes the Checkout page —
            # before the funds clear, with payment_status "unpaid". Crediting
            # that event marks the invoice Paid for a payment that may still
            # fail days later, and the balance is never chased. Stripe sends
            # checkout.session.async_payment_succeeded when such a payment
            # really settles, which is why it is handled alongside this event.
            #
            # Caught by tests/test_scenarios.py::
            #   test_delayed_payment_method_is_not_credited_until_it_settles
            payment_status = (session.get("payment_status") or "").lower()
            if payment_status and payment_status not in (
                "paid",
                "no_payment_required",
            ):
                logger.info(
                    "stripe webhook: session %s not settled yet "
                    "(payment_status=%s) — not credited", session_id,
                    payment_status,
                )
                return ("", 200)

            # For Connect direct charges the event carries the connected
            # account it belongs to; legacy platform charges have none.
            event_account = event.get("account")
            invoice_id = (session.get("metadata") or {}).get("invoice_id")
            invoice = None
            if invoice_id:
                try:
                    invoice = db.session.get(Invoice, int(invoice_id))
                except (TypeError, ValueError):
                    invoice = None
            if invoice is None and session_id:
                invoice = Invoice.query.filter_by(
                    stripe_session_id=session_id
                ).first()

            # Authorize the event so a session on one account can't mark
            # another user's invoice paid:
            #  - Connect direct charge: the event's account must be the
            #    invoice owner's own connected account.
            #  - Legacy platform charge (no account): the session id must be
            #    the exact one we stored on this invoice (unforgeable).
            authorized = False
            if invoice is not None:
                owner = invoice.owner
                if event_account:
                    # Connect direct charge: the event's account must be the
                    # account this charge was created on — either the owner's
                    # current connected account, or the one stamped on the
                    # invoice when its session was created (so a payment still
                    # credits even if the owner later disconnected / reconnected
                    # a different account). We don't trust metadata alone here,
                    # because a connected account can set arbitrary metadata.
                    authorized = bool(
                        (owner and owner.stripe_account_id == event_account)
                        or (
                            invoice.stripe_account_id
                            and invoice.stripe_account_id == event_account
                        )
                    )
                else:
                    # No connected account => a platform Checkout Session, which
                    # only this app can create (an attacker can't mint one and
                    # connected-account payments always carry an account). So the
                    # resolved invoice is trustworthy. This also covers paying an
                    # older pre-Connect link after a newer one was generated.
                    authorized = True
            if invoice is None:
                logger.warning(
                    "stripe webhook checkout.session.completed: NO invoice "
                    "matched (session=%s metadata_invoice_id=%s)",
                    session_id, invoice_id,
                )
            elif not authorized:
                logger.warning(
                    "stripe webhook checkout.session.completed: NOT authorized "
                    "for invoice=%s (event_account=%s owner_account=%s "
                    "invoice_account=%s)",
                    invoice.id, event_account,
                    invoice.owner.stripe_account_id if invoice.owner else None,
                    invoice.stripe_account_id,
                )
            if authorized:
                # Credit the actual amount paid (from the event), accumulating
                # distinct payments. Each Checkout Session is credited at most
                # once — keyed by its id — so Stripe's webhook retries are
                # idempotent and can't inflate the amount paid.
                session_id = session.get("id")
                paid_cents = session.get("amount_total") or 0
                sess_currency = (session.get("currency") or "").lower()
                inv_currency = (invoice.currency or "usd").lower()
                counted = [
                    s for s in (invoice.paid_session_ids or "").split(",") if s
                ]
                if not session_id:
                    logger.warning(
                        "stripe webhook: event missing session id for "
                        "invoice=%s — not credited", invoice.id,
                    )
                elif session_id in counted:
                    logger.info(
                        "stripe webhook: session %s already credited to "
                        "invoice=%s — no change", session_id, invoice.id,
                    )
                elif sess_currency != inv_currency:
                    logger.warning(
                        "stripe webhook: currency mismatch for invoice=%s "
                        "(event=%s invoice=%s) — not credited",
                        invoice.id, sess_currency, inv_currency,
                    )
                else:
                    invoice.amount_paid = round(
                        (invoice.amount_paid or 0.0) + paid_cents / 100.0, 2
                    )
                    counted.append(session_id)
                    invoice.paid_session_ids = ",".join(counted)
                    logger.info(
                        "stripe webhook: credited %.2f %s to invoice=%s "
                        "(session=%s)", paid_cents / 100.0, inv_currency,
                        invoice.id, session_id,
                    )
                # Recompute paid status from the (stable) accumulated amount.
                if int(round((invoice.amount_paid or 0.0) * 100)) >= int(
                    round(invoice.total * 100)
                ):
                    invoice.status = "Paid"
                db.session.commit()
                logger.info(
                    "stripe webhook: invoice=%s now amount_paid=%s total=%s "
                    "status=%s", invoice.id, invoice.amount_paid,
                    invoice.total, invoice.status,
                )

        elif event_type == "account.updated":
            # A connected account finished (or changed) onboarding.
            account = event["data"]["object"]
            user = User.query.filter_by(
                stripe_account_id=account.get("id")
            ).first()
            if user is not None:
                user.stripe_charges_enabled = bool(
                    account.get("charges_enabled")
                )
                db.session.commit()
                logger.info(
                    "stripe webhook: account.updated account=%s "
                    "charges_enabled=%s user=%s", account.get("id"),
                    user.stripe_charges_enabled, user.id,
                )
            else:
                logger.info(
                    "stripe webhook: account.updated for unknown account=%s",
                    account.get("id"),
                )
        else:
            logger.info("stripe webhook: ignoring unhandled type=%s", event_type)

        return ("", 200)

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
