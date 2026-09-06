"""Database models for the invoice generator.

Tables:

* ``User``     - account with hashed password and a per-user API key.
* ``Invoice``  - header / totals / metadata, owned by a user.
* ``LineItem`` - each billed row.
* ``Payment``  - each payment received, individually. See its docstring: the
  invoice's ``amount_paid`` is a CACHE of this ledger, not the record.

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

from currencies import decimals_for

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

    # A PUBLIC LINK MUST NOT OUTLIVE ITS INVOICE AND POINT AT THE NEXT ONE.
    # `/i/<token>` signs this integer. Without AUTOINCREMENT, SQLite hands the
    # next insert the highest free rowid, so deleting an invoice releases its
    # id and the next invoice raised on the instance inherits it -- and every
    # link already sitting in a client's inbox resolves to somebody else's
    # invoice.
    #
    # Reproduced ACROSS ACCOUNTS by the scenario harness: owner A raises a
    # confidential $5,000 invoice, sends the link, deletes the invoice; owner
    # B, a different workspace, raises the next invoice and inherits the id;
    # A's client opens A's link and reads B's invoice, client name and all.
    # Nothing about the authorization is wrong -- the public page is meant to
    # be readable by whoever holds the link. The identifier underneath it was.
    #
    # `sqlite_autoincrement` makes SQLite keep a monotonic counter in
    # `sqlite_sequence` and never reuse an id. Chosen over a random public
    # token deliberately: a token change invalidates every link already in a
    # client's hands, which is the owner's call, and this closes the hole
    # without touching one of them.
    #
    # Postgres allocates from a sequence and never reuses, so the Render
    # deployment was never affected; `docker compose up`, `run.ps1` and a bare
    # `flask run` all default to SQLite and were.
    #
    # AN EXISTING SQLite FILE DOES NOT GAIN THIS. The table would have to be
    # rebuilt. New installs are safe; an instance that has already been
    # deleting invoices needs `docs/invoicer-scenarios.md` read before it is
    # trusted with a public link.
    __table_args__ = {"sqlite_autoincrement": True}

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
    # A CACHE OF THE `payments` LEDGER, not the record -- see Payment's
    # docstring. Nothing assigns to this directly any more; `record_payment`
    # and `reverse_manual_payments` recompute it. It stays a column because a
    # dozen readers use it, including one raw SQL statement in _ensure_schema
    # and the History KPIs, and because a property cannot be queried in SQL.
    amount_paid = db.Column(db.Float, default=0.0)

    # Free text
    notes = db.Column(db.Text, default="")
    terms = db.Column(db.Text, default="")

    # Branding (logo stored in the DB, not on disk)
    logo_data = db.Column(db.LargeBinary, nullable=True)
    logo_mimetype = db.Column(db.String(64), nullable=True)

    # The chosen look, e.g. "band-emerald". See designs.py. NULLABLE on
    # purpose: every invoice written before the gallery existed has no design,
    # and designs.resolve(None) hands back the look the app already shipped,
    # so those invoices re-print exactly as their clients first saw them.
    # Nullable also makes the column safe to add under a rolling deploy — a
    # worker still running the old code inserts rows without it.
    design = db.Column(db.String(64), nullable=True)
    # "INVOICE" / "QUOTE" / "RECEIPT" / "ESTIMATE". The document is the same
    # shape either way; only the word at the top and the label on the number
    # change. Nullable for the same reason as `design`.
    doc_title = db.Column(db.String(40), nullable=True)

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

    payments = db.relationship(
        "Payment",
        backref="invoice",
        cascade="all, delete-orphan",
        order_by="Payment.id",
    )

    @property
    def has_logo(self):
        return self.logo_data is not None

    # --- Derived totals -------------------------------------------------
    #
    # EVERY FIGURE ROUNDS TO THE CURRENCY'S OWN MINOR UNIT, not to two places.
    # Hardcoding 2 was right for the fourteen currencies this app used to
    # offer and wrong for a quarter of the 157 it offers now, in both
    # directions:
    #
    #   * A KWD line of 1 x 1.235 printed "KD1.235" as the unit price and
    #     "KD1.240" as the amount, on the same row, because the display
    #     honoured the dinar's three places and the arithmetic did not.
    #   * A JPY invoice of 3 x 100.5 STORED 301.5 -- an amount of yen that
    #     cannot exist. It displayed as ¥302 and charged ¥302, so the number
    #     in the database was the only one that was wrong, which is the
    #     hardest kind to notice.
    #
    # Caught by Codex on PR #289. Guarded by tests/test_currency_precision.py.

    @property
    def places(self):
        """How many decimal places this invoice's currency actually has."""
        return decimals_for(self.currency)

    def _round(self, value):
        return round(value, self.places)

    @property
    def subtotal(self):
        return self._round(sum(item.amount for item in self.items))

    @property
    def discount_amount(self):
        if self.discount_is_percent:
            return self._round(self.subtotal * (self.discount_value or 0) / 100.0)
        return self._round(self.discount_value or 0.0)

    @property
    def taxable_base(self):
        return self._round(self.subtotal - self.discount_amount)

    @property
    def tax_amount(self):
        if self.tax_is_percent:
            return self._round(self.taxable_base * (self.tax_value or 0) / 100.0)
        return self._round(self.tax_value or 0.0)

    @property
    def total(self):
        return self._round(
            self.taxable_base + self.tax_amount + (self.shipping or 0.0)
        )

    @property
    def balance_due(self):
        return self._round(self.total - (self.amount_paid or 0.0))

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

    # --- the payment ledger ---------------------------------------------
    #
    # THE ONLY THREE WAYS MONEY MOVES ON AN INVOICE. Everything that used to
    # assign to `amount_paid` goes through one of these, so the ledger and the
    # cache cannot disagree and no caller has to remember to keep them in step.

    @property
    def ledger_total(self):
        """What the ledger says is paid. `amount_paid` must equal this."""
        return self._round(sum(p.amount or 0.0 for p in self.payments))

    @property
    def confirmed_paid(self):
        """The part a payment processor confirmed. Not reversible in this app."""
        return self._round(
            sum(p.amount or 0.0 for p in self.payments if p.is_confirmed)
        )

    @property
    def manual_paid(self):
        """The part somebody entered by hand, net of any reversals."""
        return self._round(
            sum(
                p.amount or 0.0
                for p in self.payments
                if p.source in ("manual", "reversal", "migrated")
            )
        )

    def has_credited(self, external_id):
        """Has this processor reference already been counted?

        Reads the ledger AND the legacy ``paid_session_ids`` string. Both,
        because invoices that were paid before this table existed carry their
        session ids only in that string -- and a replayed webhook for one of
        them must still not double-credit. Nothing writes the legacy column
        any more; it is read for exactly this reason and can be dropped once
        no invoice predating the ledger is still live.
        """
        if not external_id:
            return False
        if any(p.external_id == external_id for p in self.payments):
            return True
        legacy = [s for s in (self.paid_session_ids or "").split(",") if s]
        return external_id in legacy

    def record_payment(
        self, amount, source, external_id=None, note="", currency=None
    ):
        """Append a payment and refresh the cache. Returns the Payment."""
        payment = Payment(
            amount=self._round(float(amount or 0.0)),
            currency=(currency or self.currency or ""),
            source=source,
            external_id=external_id,
            note=note[:255],
        )
        self.payments.append(payment)
        self._sync_amount_paid()
        return payment

    def reverse_manual_payments(self, note=""):
        """Undo what a person entered by hand. Returns the amount reversed.

        **Confirmed payments are not touched, and that is the point.** The old
        `mark_unpaid` set `amount_paid = 0` outright, which meant a button in
        our UI could erase money Stripe had already moved. It cannot: a card
        payment is a fact about the world, and reversing it is a refund, which
        happens at the processor and arrives back here as its own event.

        The reversal is an ENTRY, not a deletion -- the original stays legible,
        so "this was marked paid in error on the 5th" is still answerable.
        """
        outstanding = self.manual_paid
        if outstanding == 0:
            return 0.0
        self.record_payment(
            -outstanding,
            source="reversal",
            note=note or "Reversed a manual payment entry",
        )
        return outstanding

    def set_manual_paid_total(self, target, note=""):
        """Adjust the MANUAL entries until the total paid reads ``target``.

        This is what a typed "amount paid" box means: a person stating what
        they have received. It is expressed as a delta rather than an
        assignment so it lands in the ledger like everything else.

        **Confirmed payments are a floor.** A figure typed into a form can
        raise the total or lower it down to what a processor has confirmed,
        and no further -- the same rule as `reverse_manual_payments`, applied
        at the other door. Somebody correcting a typo must not be able to
        delete a card payment by typing a smaller number over it.
        """
        target = self._round(float(target or 0.0))
        floor = self.confirmed_paid
        if target < floor:
            target = floor
        delta = self._round(target - self.ledger_total)
        if delta == 0:
            return 0.0
        self.record_payment(
            delta,
            source="manual" if delta > 0 else "reversal",
            note=note or "Amount paid entered on the invoice",
        )
        return delta

    def _sync_amount_paid(self):
        self.amount_paid = self.ledger_total


class Payment(db.Model):
    """One payment against one invoice. The record; never overwritten.

    ## Why this table exists

    ``Invoice.amount_paid`` used to be the whole record: a single mutable
    float that every path overwrote. Three things followed from that, all of
    them recorded in ``docs/REPO-INVENTORY.md`` as the last money bug left in
    this app, and the firm's answer on 5 September 2026 was *"Fix it before
    any client sees it."*

    1. **"Mark as unpaid" destroyed real money.** It set ``amount_paid = 0``
       without being able to tell a card payment from a typo. A 400.00
       payment Stripe had actually taken was gone in one click.
    2. **It was unrecoverable.** The spent Checkout Session id stayed in
       ``paid_session_ids``, so replaying the very webhook that recorded the
       payment hit the "already credited" branch and did nothing.
    3. **Two payments became one number.** 400.00 by card and 700.00 by
       cheque stored as ``1100.00``; if the card payment was later disputed
       there was nothing to say which part of it was the card's.

    A ledger fixes all three at once, and it is what an accounting practice
    would expect to exist: entries are appended, never edited, and a reversal
    is its own entry rather than the absence of the original.

    ## amount_paid is now a cache of this, and must tie out

    ``Invoice.amount_paid`` is kept because a dozen readers use it -- the
    templates, the CSV export, the JSON API, the History KPIs and one raw SQL
    statement in ``_ensure_schema``. It is no longer written directly by
    anything: every change goes through ``Invoice.record_payment`` or
    ``Invoice.reverse_manual_payments``, which append here and then recompute
    it. ``tests/test_payment_ledger.py`` ties the two together after every
    operation, the way a control account ties to its subsidiary ledger.

    ``amount`` is signed: positive is money in, negative is a reversal.
    ``source`` says who to believe -- ``stripe`` is money a processor
    confirmed moved, and nothing in this application's UI may reverse it.
    """

    __tablename__ = "payments"

    # THE IDEMPOTENCY KEY IS ENFORCED BY THE DATABASE, not by the read that
    # precedes the write. `has_credited` asks whether a processor reference is
    # already in the ledger, but gunicorn runs two workers and Stripe delivers
    # a retry concurrently -- so both can answer "no" before either commits,
    # and the payment lands twice. A check-then-insert is not a guard.
    #
    # Migrated opening balances carry a synthetic `migrated:<invoice_id>`
    # reference for the same reason: _ensure_schema's backfill runs per worker
    # at boot, and two workers can both find no rows and both insert a full
    # set. With this constraint the loser's INSERT violates it and rolls the
    # whole statement back, which leaves exactly one set.
    #
    # NULL is exempt in both SQLite and Postgres -- several manual payments on
    # one invoice are legitimate and carry no reference at all.
    __table_args__ = (
        db.UniqueConstraint(
            "invoice_id", "external_id", name="uq_payment_invoice_external"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )

    # Signed. Positive = money in; negative = a reversal of an earlier entry.
    amount = db.Column(db.Float, nullable=False, default=0.0)
    # Snapshotted, because an invoice's currency can be edited afterwards and
    # a payment happened in whatever currency it happened in.
    currency = db.Column(db.String(8), default="")

    # "stripe"   - a processor confirmed the money moved. Not reversible here.
    # "manual"   - somebody in this app said it was paid (cash, cheque, bank).
    # "reversal" - undoing a manual entry. Never generated for a stripe one.
    # "migrated" - the opening balance carried over when this table was added.
    source = db.Column(db.String(20), nullable=False, default="manual")

    # The Stripe Checkout Session id, for stripe rows. This is the
    # idempotency key that stops a webhook retry counting twice, and it is
    # now held per-payment instead of in a comma-joined string on the invoice.
    external_id = db.Column(db.String(255), nullable=True, index=True)

    note = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_confirmed(self):
        """Money a payment processor says actually moved."""
        return self.source == "stripe"


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
        """Rounded to the parent invoice's currency, not to two places.

        A line item has no currency of its own, so it asks the invoice. A
        detached row -- one built in a test, or read before its parent is
        loaded -- falls back to two, which is right for all but 23 of the 157
        currencies and is the only answer available without inventing one.
        """
        invoice = getattr(self, "invoice", None)
        digits = decimals_for(invoice.currency) if invoice is not None else 2
        return round((self.quantity or 0.0) * (self.rate or 0.0), digits)
