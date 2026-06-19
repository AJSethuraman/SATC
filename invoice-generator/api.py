"""JSON REST API for programmatic invoice creation.

All endpoints live under ``/api`` and require an ``X-API-Key`` header whose
value is a user's personal API key (find it on the Account page). The key
identifies the user, and every request is scoped to that user's invoices.

Typical use::

    curl -X POST http://localhost:5000/api/invoices \
      -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
      -d '{
            "from_info": "Acme LLC\\n1 Road",
            "bill_to": "Client Co\\n2 Street",
            "items": [{"description": "Design", "quantity": 10, "rate": 100}],
            "tax": {"value": 8.25, "percent": true},
            "create_payment_link": true
          }'
"""
from datetime import date
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request, send_file

import stripe_utils
from helpers import parse_date
from models import Invoice, LineItem, User, db

api_bp = Blueprint("api", __name__, url_prefix="/api")


# --------------------------------------------------------------------------
# Auth (per-user API key)
# --------------------------------------------------------------------------
def require_api_key(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        provided = request.headers.get("X-API-Key", "")
        user = (
            User.query.filter_by(api_key=provided).first() if provided else None
        )
        if user is None:
            return jsonify(error="Invalid or missing X-API-Key header."), 401
        g.api_user = user
        return view(*args, **kwargs)

    return wrapper


def _owned_or_404(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None or invoice.user_id != g.api_user.id:
        return None
    return invoice


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _adjustment(data, key):
    """Parse a tax/discount block.

    Accepts either ``{"value": 8.25, "percent": true}`` or a bare number
    (treated as a flat amount). Returns ``(value, is_percent)``.
    """
    block = data.get(key)
    if block is None:
        return 0.0, (key == "tax")  # tax defaults to percent, discount flat
    if isinstance(block, dict):
        value = _to_float(block.get("value"), 0.0)
        is_percent = bool(block.get("percent", key == "tax"))
        return value, is_percent
    return _to_float(block, 0.0), False


def _populate_invoice_from_json(invoice, data):
    """Fill an Invoice from a decoded JSON body."""
    invoice.invoice_number = str(
        data.get("invoice_number") or invoice.invoice_number or ""
    ).strip()
    invoice.from_info = str(data.get("from_info", "")).strip()
    invoice.bill_to = str(data.get("bill_to", "")).strip()
    invoice.ship_to = str(data.get("ship_to", "")).strip()

    invoice.invoice_date = parse_date(data.get("invoice_date")) or date.today()
    invoice.payment_terms = str(data.get("payment_terms", "")).strip()
    invoice.due_date = parse_date(data.get("due_date"))
    invoice.po_number = str(data.get("po_number", "")).strip()
    invoice.currency = str(data.get("currency", "USD")).strip().upper() or "USD"

    tax_value, tax_pct = _adjustment(data, "tax")
    invoice.tax_value = tax_value
    invoice.tax_is_percent = tax_pct
    disc_value, disc_pct = _adjustment(data, "discount")
    invoice.discount_value = disc_value
    invoice.discount_is_percent = disc_pct

    invoice.shipping = _to_float(data.get("shipping"), 0.0)
    invoice.amount_paid = _to_float(data.get("amount_paid"), 0.0)

    invoice.notes = str(data.get("notes", "")).strip()
    invoice.terms = str(data.get("terms", "")).strip()

    invoice.items.clear()
    for position, raw in enumerate(data.get("items") or []):
        if not isinstance(raw, dict):
            continue
        desc = str(raw.get("description", "")).strip()
        qty = _to_float(raw.get("quantity"), 0.0)
        rate = _to_float(raw.get("rate"), 0.0)
        if not desc and qty == 0 and rate == 0:
            continue
        invoice.items.append(
            LineItem(
                position=position, description=desc, quantity=qty, rate=rate
            )
        )


def _validate(invoice):
    errors = []
    if not invoice.invoice_number:
        errors.append("invoice_number is required (or omit to auto-number).")
    if not invoice.from_info:
        errors.append("from_info is required.")
    if not invoice.bill_to:
        errors.append("bill_to is required.")
    if not invoice.items:
        errors.append("at least one line item is required.")
    return errors


def serialize(invoice):
    base = current_app.config["APP_BASE_URL"].rstrip("/")
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "currency": invoice.currency,
        "from_info": invoice.from_info,
        "bill_to": invoice.bill_to,
        "ship_to": invoice.ship_to,
        "invoice_date": invoice.invoice_date.isoformat()
        if invoice.invoice_date
        else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "payment_terms": invoice.payment_terms,
        "po_number": invoice.po_number,
        "items": [
            {
                "description": i.description,
                "quantity": i.quantity,
                "rate": i.rate,
                "amount": i.amount,
            }
            for i in invoice.items
        ],
        "subtotal": invoice.subtotal,
        "discount": invoice.discount_amount,
        "tax": invoice.tax_amount,
        "shipping": invoice.shipping,
        "total": invoice.total,
        "amount_paid": invoice.amount_paid,
        "balance_due": invoice.balance_due,
        "notes": invoice.notes,
        "terms": invoice.terms,
        "stripe_payment_url": invoice.stripe_payment_url,
        "pdf_url": f"{base}/api/invoices/{invoice.id}/pdf",
        "created_at": invoice.created_at.isoformat()
        if invoice.created_at
        else None,
    }


def _maybe_create_payment_link(invoice):
    """Create a Stripe Checkout link if requested. Returns a warning or None."""
    try:
        session = stripe_utils.create_checkout_session(
            invoice,
            current_app.config["STRIPE_SECRET_KEY"],
            current_app.config["APP_BASE_URL"],
        )
    except (RuntimeError, ValueError) as exc:
        return str(exc)
    except Exception as exc:  # pragma: no cover - network/Stripe errors
        return f"Stripe error: {exc}"
    invoice.stripe_session_id = session.id
    invoice.stripe_payment_url = session.url
    if invoice.status == "Draft":
        invoice.status = "Sent"
    db.session.commit()
    return None


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@api_bp.get("/health")
def health():
    # Unauthenticated liveness probe (used by Docker healthcheck).
    return jsonify(status="ok"), 200


@api_bp.get("/invoices")
@require_api_key
def list_invoices():
    invoices = (
        Invoice.query.filter_by(user_id=g.api_user.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    return jsonify(invoices=[serialize(i) for i in invoices])


@api_bp.post("/invoices")
@require_api_key
def create_invoice():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object."), 400

    # Import here to avoid a circular import with app.py at module load.
    from app import generate_pdf, next_invoice_number

    invoice = Invoice(user_id=g.api_user.id)
    if not data.get("invoice_number"):
        invoice.invoice_number = next_invoice_number(g.api_user.id)
    _populate_invoice_from_json(invoice, data)

    errors = _validate(invoice)
    if errors:
        return jsonify(error="Validation failed.", details=errors), 422

    db.session.add(invoice)
    db.session.commit()

    warnings = []
    if data.get("create_payment_link"):
        warning = _maybe_create_payment_link(invoice)
        if warning:
            warnings.append(warning)

    # Pre-render the PDF so pdf_url works immediately.
    try:
        generate_pdf(current_app._get_current_object(), invoice)
    except Exception as exc:  # pragma: no cover - rendering env issues
        warnings.append(f"PDF generation deferred: {exc}")

    body = serialize(invoice)
    if warnings:
        body["warnings"] = warnings
    return jsonify(body), 201


@api_bp.get("/invoices/<int:invoice_id>")
@require_api_key
def get_invoice(invoice_id):
    invoice = _owned_or_404(invoice_id)
    if invoice is None:
        return jsonify(error="Invoice not found."), 404
    return jsonify(serialize(invoice))


@api_bp.delete("/invoices/<int:invoice_id>")
@require_api_key
def delete_invoice(invoice_id):
    invoice = _owned_or_404(invoice_id)
    if invoice is None:
        return jsonify(error="Invoice not found."), 404
    db.session.delete(invoice)
    db.session.commit()
    return jsonify(deleted=invoice_id), 200


@api_bp.post("/invoices/<int:invoice_id>/payment-link")
@require_api_key
def create_payment_link(invoice_id):
    invoice = _owned_or_404(invoice_id)
    if invoice is None:
        return jsonify(error="Invoice not found."), 404
    warning = _maybe_create_payment_link(invoice)
    if warning:
        return jsonify(error=warning), 400
    return jsonify(
        stripe_payment_url=invoice.stripe_payment_url, status=invoice.status
    )


@api_bp.get("/invoices/<int:invoice_id>/pdf")
@require_api_key
def invoice_pdf(invoice_id):
    invoice = _owned_or_404(invoice_id)
    if invoice is None:
        return jsonify(error="Invoice not found."), 404

    from app import generate_pdf

    try:
        out_path = generate_pdf(current_app._get_current_object(), invoice)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503
    return send_file(
        out_path,
        as_attachment=True,
        download_name=out_path.name,
        mimetype="application/pdf",
    )
