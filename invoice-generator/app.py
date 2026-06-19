"""Flask invoice generator application.

Run locally with::

    flask --app app run

See README.md for full setup, environment variables, and Stripe webhook
testing instructions.
"""
import csv
import io
import os
import uuid
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
from werkzeug.utils import secure_filename

import email_utils
import stripe_utils
from config import Config
from helpers import currency_symbol, format_money, parse_date, parse_float
from models import Invoice, LineItem, db
from pdf import render_invoice_pdf

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure runtime directories exist.
    app.config["INVOICES_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_DIR"].mkdir(parents=True, exist_ok=True)

    # If the SQLite database lives in a subdirectory (e.g. /app/data in
    # Docker), make sure that directory exists before SQLAlchemy connects.
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////:"):
        db_path = uri.replace("sqlite:///", "", 1)
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    # Make formatting helpers available inside all templates.
    app.jinja_env.globals.update(
        format_money=format_money, currency_symbol=currency_symbol
    )

    with app.app_context():
        db.create_all()

    register_routes(app)

    # JSON REST API (token-protected).
    from api import api_bp

    app.register_blueprint(api_bp)
    return app


# --------------------------------------------------------------------------
# Form handling
# --------------------------------------------------------------------------
def _save_logo(file_storage, app):
    """Persist an uploaded logo and return its stored filename, or None."""
    if not file_storage or not file_storage.filename:
        return None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        return None
    fname = f"{uuid.uuid4().hex}{ext}"
    file_storage.save(app.config["UPLOAD_DIR"] / fname)
    return fname


def _populate_invoice_from_form(invoice, form, app, files=None):
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

    # Logo: keep existing unless a new file is uploaded.
    if files:
        new_logo = _save_logo(files.get("logo"), app)
        if new_logo:
            invoice.logo_filename = new_logo

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
        # Skip fully empty rows.
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
    """Render and store the invoice PDF, returning its filesystem path.

    Shared by the web UI and the JSON API. Requires an active app context.
    """
    fname = f"invoice_{invoice.invoice_number}_{invoice.id}.pdf".replace(
        "/", "-"
    )
    out_path = app.config["INVOICES_DIR"] / fname
    logo_path = None
    if invoice.logo_filename:
        logo_path = app.config["UPLOAD_DIR"] / invoice.logo_filename
    render_invoice_pdf(invoice, out_path, logo_path=logo_path)
    invoice.pdf_filename = fname
    db.session.commit()
    return out_path


def next_invoice_number():
    """Suggest the next sequential invoice number (e.g. INV-0007)."""
    last = Invoice.query.order_by(Invoice.id.desc()).first()
    return f"INV-{(last.id + 1) if last else 1:04d}"


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("new_invoice"))

    @app.route("/new")
    def new_invoice():
        # Suggest a sensible next invoice number.
        suggested = next_invoice_number()
        return render_template(
            "form.html",
            invoice=None,
            suggested_number=suggested,
            today=date.today().isoformat(),
        )

    @app.route("/invoices", methods=["POST"])
    def create_invoice():
        invoice = Invoice()
        _populate_invoice_from_form(invoice, request.form, app, request.files)
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
    def view_invoice(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
        return render_template(
            "view.html",
            invoice=invoice,
            stripe_configured=bool(app.config["STRIPE_SECRET_KEY"]),
            smtp_configured=bool(
                app.config["SMTP_HOST"] and app.config["FROM_EMAIL"]
            ),
        )

    @app.route("/invoice/<int:invoice_id>/edit")
    def edit_invoice(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
        return render_template(
            "form.html",
            invoice=invoice,
            suggested_number=invoice.invoice_number,
            today=date.today().isoformat(),
        )

    @app.route("/invoice/<int:invoice_id>", methods=["POST"])
    def update_invoice(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
        _populate_invoice_from_form(invoice, request.form, app, request.files)
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
        # Totals may have changed; invalidate stale PDF.
        invoice.pdf_filename = None
        db.session.commit()
        flash("Invoice updated.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice.id))

    @app.route("/invoice/<int:invoice_id>/delete", methods=["POST"])
    def delete_invoice(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
        # Remove generated PDF if present.
        if invoice.pdf_filename:
            pdf_path = app.config["INVOICES_DIR"] / invoice.pdf_filename
            if pdf_path.exists():
                pdf_path.unlink()
        db.session.delete(invoice)
        db.session.commit()
        flash("Invoice deleted.", "success")
        return redirect(url_for("history"))

    def _generate_pdf(invoice):
        """Render and store the invoice PDF, returning its filesystem path."""
        return generate_pdf(app, invoice)

    @app.route("/invoice/<int:invoice_id>/pdf")
    def download_pdf(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
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
    def create_payment(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
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
    def email_invoice(invoice_id):
        invoice = db.session.get(Invoice, invoice_id) or abort(404)
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
    def history():
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
        return render_template("history.html", invoices=invoices)

    @app.route("/history/export.csv")
    def export_csv():
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
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
                # Fall back to matching by stored session id.
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
