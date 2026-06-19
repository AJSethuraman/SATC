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
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from markupsafe import Markup, escape

import email_utils
import stripe_utils
from config import Config
from helpers import currency_symbol, format_money, parse_date, parse_float
from models import Invoice, LineItem, User, db

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


def nl2br(value):
    """Escape text and convert newlines to <br> (for engines without
    CSS ``white-space`` support, e.g. xhtml2pdf)."""
    if value is None:
        return ""
    text = str(escape(value)).replace("\r\n", "<br>").replace("\n", "<br>")
    return Markup(text)


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

    db.init_app(app)

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

    register_routes(app)

    from api import api_bp

    app.register_blueprint(api_bp)
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
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Your account is ready.", "success")
            return redirect(url_for("history"))
        return render_template("signup.html", email="")

    @app.route("/login", methods=["GET", "POST"])
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
            login_user(user)
            nxt = request.args.get("next")
            # Only allow relative redirects (avoid open redirect).
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
        try:
            session = stripe_utils.create_checkout_session(
                invoice,
                app.config["STRIPE_SECRET_KEY"],
                app.config["APP_BASE_URL"],
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
            invoice_id = (session.get("metadata") or {}).get("invoice_id")
            invoice = None
            if invoice_id:
                invoice = db.session.get(Invoice, int(invoice_id))
            if invoice is None:
                invoice = Invoice.query.filter_by(
                    stripe_session_id=session.get("id")
                ).first()
            if invoice is not None:
                invoice.status = "Paid"
                invoice.amount_paid = invoice.total
                db.session.commit()

        return ("", 200)

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
