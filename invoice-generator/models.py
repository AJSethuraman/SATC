"""Database models for the invoice generator.

Two tables: ``Invoice`` holds the header / totals / metadata, and
``LineItem`` holds each billed row. Monetary inputs (tax, discount,
shipping) are stored as raw values plus a flag indicating whether the
value is a percentage or a flat amount, mirroring the way the source
service exposes those fields.
"""
from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)

    # Header / parties
    invoice_number = db.Column(db.String(64), nullable=False)
    from_info = db.Column(db.Text, nullable=False, default="")
    bill_to = db.Column(db.Text, nullable=False, default="")
    ship_to = db.Column(db.Text, default="")

    # Dates and terms
    invoice_date = db.Column(db.Date, default=date.today)
    payment_terms = db.Column(db.String(120), default="")
    due_date = db.Column(db.Date, nullable=True)
    po_number = db.Column(db.String(120), default="")

    currency = db.Column(db.String(8), default="USD")

    # Adjustments. ``*_is_percent`` toggles flat vs. percentage handling.
    tax_value = db.Column(db.Float, default=0.0)
    tax_is_percent = db.Column(db.Boolean, default=True)
    discount_value = db.Column(db.Float, default=0.0)
    discount_is_percent = db.Column(db.Boolean, default=False)
    shipping = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)

    # Free text
    notes = db.Column(db.Text, default="")
    terms = db.Column(db.Text, default="")

    # Branding
    logo_filename = db.Column(db.String(255), nullable=True)

    # Workflow / integrations
    status = db.Column(db.String(20), default="Draft")  # Draft | Sent | Paid
    pdf_filename = db.Column(db.String(255), nullable=True)
    stripe_session_id = db.Column(db.String(255), nullable=True)
    stripe_payment_url = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items = db.relationship(
        "LineItem",
        backref="invoice",
        cascade="all, delete-orphan",
        order_by="LineItem.position",
    )

    # --- Derived totals -------------------------------------------------
    @property
    def subtotal(self):
        return round(sum(item.amount for item in self.items), 2)

    @property
    def discount_amount(self):
        if self.discount_is_percent:
            return round(self.subtotal * (self.discount_value or 0) / 100.0, 2)
        return round(self.discount_value or 0.0, 2)

    @property
    def taxable_base(self):
        return round(self.subtotal - self.discount_amount, 2)

    @property
    def tax_amount(self):
        if self.tax_is_percent:
            return round(self.taxable_base * (self.tax_value or 0) / 100.0, 2)
        return round(self.tax_value or 0.0, 2)

    @property
    def total(self):
        return round(
            self.taxable_base + self.tax_amount + (self.shipping or 0.0), 2
        )

    @property
    def balance_due(self):
        return round(self.total - (self.amount_paid or 0.0), 2)


class LineItem(db.Model):
    __tablename__ = "line_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer, db.ForeignKey("invoices.id"), nullable=False
    )
    position = db.Column(db.Integer, default=0)
    description = db.Column(db.String(500), nullable=False, default="")
    quantity = db.Column(db.Float, default=1.0)
    rate = db.Column(db.Float, default=0.0)

    @property
    def amount(self):
        return round((self.quantity or 0.0) * (self.rate or 0.0), 2)
