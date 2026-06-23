"""Database models for the invoice generator.

Tables:

* ``User``     - account with hashed password and a per-user API key.
* ``Invoice``  - header / totals / metadata, owned by a user.
* ``LineItem`` - each billed row.

Monetary inputs (tax, discount, shipping) are stored as raw values plus a flag
indicating whether the value is a percentage or a flat amount, mirroring the
way the source service exposes those fields.

Uploaded logos are stored as bytes in the database (not on disk) so they
survive redeploys on hosts with an ephemeral filesystem.
"""
import secrets
from datetime import datetime, date

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def generate_api_key():
    return "sk_" + secrets.token_urlsafe(32)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    api_key = db.Column(
        db.String(64), unique=True, nullable=False, default=generate_api_key
    )
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    # Subscription plan (dormant until BILLING_ENABLED). "free" | "pro" | ...
    plan = db.Column(db.String(32), default="free", nullable=False)
    # Stripe Connect: the user's own connected account (where their payments
    # land). charges_enabled flips true once they finish Stripe onboarding.
    stripe_account_id = db.Column(db.String(64), nullable=True)
    stripe_charges_enabled = db.Column(
        db.Boolean, default=False, nullable=False
    )
    # Business profile — appears on every invoice (set once in Account).
    business_name = db.Column(db.String(200), default="")
    business_email = db.Column(db.String(255), default="")
    business_address = db.Column(db.Text, default="")
    tax_id = db.Column(db.String(80), default="")
    default_currency = db.Column(db.String(8), default="USD")
    default_terms = db.Column(db.String(120), default="")
    # Per-workspace email sender (white-label foundation). With custom SMTP set,
    # the workspace's own server + From address are used; otherwise mail goes via
    # the app's shared/authenticated sender with Reply-To pointed at the
    # workspace so client replies still reach them.
    email_from_name = db.Column(db.String(120), default="")
    email_from_email = db.Column(db.String(255), default="")
    email_reply_to = db.Column(db.String(255), default="")
    smtp_host = db.Column(db.String(255), default="")
    smtp_port = db.Column(db.Integer, nullable=True)
    smtp_username = db.Column(db.String(255), default="")
    smtp_password = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship(
        "Invoice", backref="owner", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def can_accept_payments(self):
        return bool(self.stripe_account_id and self.stripe_charges_enabled)

    @property
    def has_business_profile(self):
        return bool((self.business_name or "").strip())

    @property
    def has_custom_smtp(self):
        """True if this workspace brings its own SMTP server."""
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)

    @property
    def custom_smtp_ready(self):
        """True if we should actually send via the workspace's own SMTP: it
        needs the SMTP credentials AND a workspace-owned From address. We never
        send the app's shared address through a customer's SMTP server."""
        return bool(
            self.has_custom_smtp
            and (self.email_from_email or self.business_email)
        )

    @property
    def from_info(self):
        """Assemble the sender block shown on invoices from the profile."""
        lines = []
        if self.business_name:
            lines.append(self.business_name)
        if self.business_address:
            lines.extend(self.business_address.splitlines())
        if self.business_email:
            lines.append(self.business_email)
        if self.tax_id:
            lines.append(f"Tax ID {self.tax_id}")
        return "\n".join(line for line in lines if line.strip())

    @property
    def initials(self):
        name = (self.business_name or self.email or "").strip()
        parts = [p for p in name.replace("@", " ").split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[1][0]).upper()


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # Header / parties
    invoice_number = db.Column(db.String(64), nullable=False)
    from_info = db.Column(db.Text, nullable=False, default="")
    bill_to = db.Column(db.Text, nullable=False, default="")
    ship_to = db.Column(db.Text, default="")
    client_email = db.Column(db.String(255), default="")

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

    # Branding (logo stored in the DB, not on disk)
    logo_data = db.Column(db.LargeBinary, nullable=True)
    logo_mimetype = db.Column(db.String(64), nullable=True)

    # Workflow / integrations
    status = db.Column(db.String(20), default="Draft")  # Draft | Sent | Paid
    stripe_session_id = db.Column(db.String(255), nullable=True)
    stripe_payment_url = db.Column(db.Text, nullable=True)
    # The connected account a Checkout Session was created on. Stamped so a
    # payment still credits this invoice even if the owner later disconnects or
    # reconnects a different Stripe account before the client pays.
    stripe_account_id = db.Column(db.String(64), nullable=True)
    # Comma-separated Stripe Checkout Session ids already credited to this
    # invoice — the idempotency key so webhook retries don't double-count.
    paid_session_ids = db.Column(db.Text, default="")

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

    @property
    def has_logo(self):
        return self.logo_data is not None

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

    @property
    def is_overdue(self):
        from datetime import date as _date

        return bool(
            self.status != "Paid"
            and self.balance_due > 0
            and self.due_date
            and self.due_date < _date.today()
        )

    @property
    def is_partial(self):
        return bool(
            self.status != "Paid"
            and (self.amount_paid or 0) > 0
            and self.balance_due > 0
        )

    @property
    def display_status(self):
        """Status used for badges: Paid / Overdue / Partial / Sent / Draft."""
        if self.status == "Paid":
            return "Paid"
        if self.is_overdue:
            return "Overdue"
        if self.is_partial:
            return "Partial"
        return self.status  # Draft | Sent

    @property
    def client_name(self):
        for line in (self.bill_to or "").splitlines():
            if line.strip():
                return line.strip()
        return "—"


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
