"""Flask invoice generator application.

Run locally with::

    flask --app app run

See README.md for setup, environment variables, deployment, and Stripe
webhook testing instructions.
"""
import csv
import io
import mimetypes
import os
from datetime import date
from pathlib import Path

from flask import (
    Flask,
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
from helpers import currency_symbol, format_money, parse_date, parse_float
from models import Invoice, LineItem, User, db

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


def nl2br(value):
    """Escape text and convert newlines to <br> (for engines without
    CSS ``white-space`` support, e.g. xhtml2pdf)."""
    if value is None:
        return ""
    text = str(escape(value)).replace("\r\n", "<br>").replace("\n", "<br>")
    return Markup(text)


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
        format_money=format_money, currency_symbol=currency_symbol
    )
    app.jinja_env.filters["nl2br"] = nl2br

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
        try:
            from PIL import Image

            Image.open(io.BytesIO(data)).verify()
        except Exception:
            return None, None  # corrupt / unreadable image -> skip
    return data, mime


def _populate_invoice_from_form(invoice, form, files=None):
    """Fill an Invoice instance from submitted form data (create or edit)."""
    invoice.invoice_number = (form.get("invoice_number") or "").strip()
    invoice.from_info = (form.get("from_info") or "").strip()
    invoice.bill_to = (form.get("bill_to") or "").strip()
    invoice.ship_to = (form.get("ship_to") or "").strip()

    invoice.invoice_date = parse_date(form.get("invoice_date")) or date.today()
    invoice.payment_terms = (form.get("payment_terms") or "").strip()
    invoice.due_date = parse_date(form.get("due_date"))
    invoice.po_number = (form.get("po_number") or "").strip()
    invoice.currency = (form.get("currency") or "USD").strip().upper()

    invoice.tax_value = parse_float(form.get("tax_value"))
    invoice.tax_is_percent = form.get("tax_is_percent") == "percent"
    invoice.discount_value = parse_float(form.get("discount_value"))
    invoice.discount_is_percent = form.get("discount_is_percent") == "percent"
    invoice.shipping = parse_float(form.get("shipping"))
    invoice.amount_paid = parse_float(form.get("amount_paid"))

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

    invoice.items.clear()
    position = 0
    for desc, qty, rate in zip(descriptions, quantities, rates):
        desc = (desc or "").strip()
        qty_f = parse_float(qty)
        rate_f = parse_float(rate)
        if not desc and qty_f == 0 and rate_f == 0:
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


def _validate_invoice(invoice):
    """Return a list of human-readable validation errors."""
    errors = []
    if not invoice.invoice_number:
        errors.append("Invoice number is required.")
    if not invoice.from_info:
        errors.append("'From' business information is required.")
    if not invoice.bill_to:
        errors.append("'Bill To' client information is required.")
    if not invoice.items:
        errors.append("At least one line item is required.")
    return errors


def generate_pdf(app, invoice):
    """Render the invoice PDF to a transient file and return its path.

    Shared by the web UI and the JSON API. Requires an active app context.
    """
    from pdf import render_invoice_pdf

    fname = f"invoice_{invoice.invoice_number}_{invoice.id}.pdf".replace(
        "/", "-"
    )
    out_path = app.config["INVOICES_DIR"] / fname
    render_invoice_pdf(invoice, out_path)
    return out_path


def next_invoice_number(user_id):
    """Suggest the next per-user invoice number (e.g. INV-0007)."""
    count = Invoice.query.filter_by(user_id=user_id).count()
    return f"INV-{count + 1:04d}"


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
            confirm = request.form.get("confirm") or ""
            errors = []
            if "@" not in email or "." not in email:
                errors.append("Enter a valid email address.")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if password != confirm:
                errors.append("Passwords do not match.")
            if User.query.filter_by(email=email).first():
                errors.append("An account with that email already exists.")
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("signup.html", email=email), 400

            user = User(email=email)
            user.set_password(password)
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
            return redirect(url_for("history"))
        return render_template("signup.html", email="")

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
            login_user(user)
            nxt = request.args.get("next")
            if not nxt or not nxt.startswith("/"):
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
            smtp_configured=bool(
                app.config["SMTP_HOST"] and app.config["FROM_EMAIL"]
            ),
        )

    @app.route("/account/regenerate-key", methods=["POST"])
    @login_required
    def regenerate_key():
        from models import generate_api_key

        current_user.api_key = generate_api_key()
        db.session.commit()
        flash("API key regenerated. Update any integrations.", "success")
        return redirect(url_for("account"))

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
        sk = app.config["STRIPE_SECRET_KEY"]
        if not sk or not current_user.stripe_account_id:
            return redirect(url_for("account"))
        try:
            url = stripe_utils.create_login_link(
                sk, current_user.stripe_account_id
            )
        except Exception:  # pragma: no cover
            flash("Could not open the Stripe dashboard right now.", "error")
            return redirect(url_for("account"))
        return redirect(url)

    # --- Invoices ------------------------------------------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("history"))
        return redirect(url_for("login"))

    @app.route("/new")
    @login_required
    def new_invoice():
        suggested = next_invoice_number(current_user.id)
        return render_template(
            "form.html",
            invoice=None,
            suggested_number=suggested,
            today=date.today().isoformat(),
        )

    @app.route("/invoices", methods=["POST"])
    @login_required
    def create_invoice():
        invoice = Invoice(user_id=current_user.id)
        _populate_invoice_from_form(invoice, request.form, request.files)
        errors = _validate_invoice(invoice)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "form.html",
                invoice=invoice,
                suggested_number=invoice.invoice_number,
                today=date.today().isoformat(),
            ), 400
        db.session.add(invoice)
        db.session.commit()
        flash("Invoice created.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/invoice/<int:invoice_id>")
    @login_required
    def view_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        return render_template(
            "view.html",
            invoice=invoice,
            stripe_configured=bool(app.config["STRIPE_SECRET_KEY"]),
            smtp_configured=bool(
                app.config["SMTP_HOST"] and app.config["FROM_EMAIL"]
            ),
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
            "form.html",
            invoice=invoice,
            suggested_number=invoice.invoice_number,
            today=date.today().isoformat(),
        )

    @app.route("/invoice/<int:invoice_id>", methods=["POST"])
    @login_required
    def update_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        _populate_invoice_from_form(invoice, request.form, request.files)
        errors = _validate_invoice(invoice)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "form.html",
                invoice=invoice,
                suggested_number=invoice.invoice_number,
                today=date.today().isoformat(),
            ), 400
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

    def _generate_pdf(invoice):
        return generate_pdf(app, invoice)

    @app.route("/invoice/<int:invoice_id>/pdf")
    @login_required
    def download_pdf(invoice_id):
        invoice = owned_or_404(invoice_id)
        try:
            out_path = _generate_pdf(invoice)
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_path.name,
            mimetype="application/pdf",
        )

    @app.route("/invoice/<int:invoice_id>/pay", methods=["POST"])
    @login_required
    def create_payment(invoice_id):
        invoice = owned_or_404(invoice_id)
        if not current_user.can_accept_payments:
            flash(
                "Connect your Stripe account (Account page) before creating "
                "a payment link.",
                "error",
            )
            return redirect(url_for("view_invoice", invoice_id=invoice.id))
        try:
            session = stripe_utils.create_checkout_session(
                invoice,
                app.config["STRIPE_SECRET_KEY"],
                app.config["APP_BASE_URL"],
                current_user.stripe_account_id,
                app.config,
            )
        except (RuntimeError, ValueError) as exc:
            flash(str(exc), "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))
        except Exception as exc:  # pragma: no cover - network/Stripe errors
            flash(f"Stripe error: {exc}", "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))

        invoice.stripe_session_id = session.id
        invoice.stripe_payment_url = session.url
        if invoice.status == "Draft":
            invoice.status = "Sent"
        db.session.commit()
        return redirect(session.url)

    @app.route("/invoice/<int:invoice_id>/email", methods=["POST"])
    @login_required
    def email_invoice(invoice_id):
        invoice = owned_or_404(invoice_id)
        to_email = (request.form.get("to_email") or "").strip()
        if not to_email:
            flash("Recipient email is required.", "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))

        try:
            out_path = _generate_pdf(invoice)
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))
        try:
            email_utils.send_invoice_email(
                app.config,
                to_email,
                invoice,
                out_path,
                payment_url=invoice.stripe_payment_url,
            )
        except Exception as exc:  # pragma: no cover - SMTP errors vary
            flash(f"Email failed: {exc}", "error")
            return redirect(url_for("view_invoice", invoice_id=invoice.id))

        if invoice.status == "Draft":
            invoice.status = "Sent"
            db.session.commit()
        flash(f"Invoice emailed to {to_email}.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/history")
    @login_required
    def history():
        invoices = (
            Invoice.query.filter_by(user_id=current_user.id)
            .order_by(Invoice.created_at.desc())
            .all()
        )
        return render_template("history.html", invoices=invoices)

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
            bill_to_oneline = " ".join((inv.bill_to or "").split())
            writer.writerow(
                [
                    inv.invoice_number,
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
            return ("Webhook secret not configured", 500)
        try:
            event = stripe_utils.construct_webhook_event(
                payload, sig_header, webhook_secret
            )
        except Exception as exc:  # invalid signature / payload
            return (f"Webhook error: {exc}", 400)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session.get("id")
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
                    # Connect direct charge: must be the invoice owner's own
                    # connected account. We don't trust metadata alone here,
                    # because a connected account can set arbitrary metadata.
                    authorized = bool(
                        owner and owner.stripe_account_id == event_account
                    )
                else:
                    # No connected account => a platform Checkout Session, which
                    # only this app can create (an attacker can't mint one and
                    # connected-account payments always carry an account). So the
                    # resolved invoice is trustworthy. This also covers paying an
                    # older pre-Connect link after a newer one was generated.
                    authorized = True
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
                if (
                    session_id
                    and sess_currency == inv_currency
                    and session_id not in counted
                ):
                    invoice.amount_paid = round(
                        (invoice.amount_paid or 0.0) + paid_cents / 100.0, 2
                    )
                    counted.append(session_id)
                    invoice.paid_session_ids = ",".join(counted)
                # Recompute paid status from the (stable) accumulated amount.
                if int(round((invoice.amount_paid or 0.0) * 100)) >= int(
                    round(invoice.total * 100)
                ):
                    invoice.status = "Paid"
                db.session.commit()

        elif event["type"] == "account.updated":
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

        return ("", 200)

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
