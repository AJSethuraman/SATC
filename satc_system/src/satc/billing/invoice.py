"""Invoices that show what the work was worth, then what you're being charged.

Most invoices show one number and leave the client guessing whether it was fair.
This one is built the other way round, because the practice bills on value and
adjusts for means:

    Your federal individual tax return .................. 450.00
    Rental property (x2) ................................ 370.00
    Self-employment income and expenses ................. 275.00
                                         Full value    1,095.00
                                  Household rate  25%   -273.75
                                         YOU PAY        821.25

That is not decoration. Someone on a reduced rate should be able to see what
they were given, and someone on full rate should be able to see what they got.
A quiet discount teaches the client nothing and gets the practice no credit.

PIECEMEAL BY DESIGN. An engagement produces several invoices as work happens,
not one at the end. ``billed_to_date`` answers "what has this client already
been charged this year", so the next invoice can be raised without anyone
reconstructing it from memory.

The structural guarantee: a line is ``service × quantity``, discounted by a
PERCENTAGE. There is nowhere to put a refund amount, so a contingent fee is not
something the engine declines — it is something it cannot express. Circular 230
§10.27.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from satc.billing.catalogue import RatePlan, Service, _money, plan, service


class BillingError(Exception):
    """An invoice was asked to do something it must not."""


@dataclass(slots=True)
class InvoiceLine:
    """One thing the client received, at full value and at their rate."""

    service_code: str
    label: str
    quantity: Decimal = Decimal(1)
    standard_rate: Decimal = Decimal(0)
    note: str = ""
    performed_on: date | None = None
    rate_adjusted: bool = False
    """Whether this line was priced away from the catalogue.

    Recorded rather than re-derived, because the catalogue is hot-reloaded: a
    rate that moves next March must not silently turn an ordinary line into an
    adjusted one, or an adjusted line into an ordinary one."""

    @property
    def standard_amount(self) -> Decimal:
        return _money(self.standard_rate * self.quantity)

    def discount_amount(self, rate_plan: RatePlan) -> Decimal:
        return rate_plan.discount_on(self.standard_amount)

    def charged_amount(self, rate_plan: RatePlan) -> Decimal:
        return rate_plan.charge_on(self.standard_amount)

    def is_reduced_from(self, catalogue_rate: Decimal) -> bool:
        return self.standard_rate < catalogue_rate

    def describe(self) -> str:
        """How the line reads on the invoice.

        A line priced below the catalogue carries its reason INTO the
        description, so the adjustment reaches the printed invoice and the
        covering email rather than living only on the screen the owner typed it
        into. A smaller number with no explanation is the thing this whole
        module exists to avoid.
        """
        head = f"{self.label} (x{self.quantity:g})" if self.quantity != 1 else self.label
        return f"{head} — {self.note}" if self.note and self.rate_adjusted else head


@dataclass(slots=True)
class Invoice:
    """One bill. A client gets several of these across an engagement."""

    invoice_id: str
    client_id: str
    tax_year: int
    plan_key: str = "standard"
    plan_basis: str = ""
    """WHY this client is on this plan. Required for any reduced plan.

    A sliding scale with no recorded basis is not a sliding scale, it is
    improvisation — and improvisation is what looks arbitrary when two clients
    compare notes."""

    issued_on: date | None = None
    due_on: date | None = None
    paid_on: date | None = None
    lines: list[InvoiceLine] = field(default_factory=list)
    note: str = ""

    # -- money -------------------------------------------------------------

    @property
    def rate_plan(self) -> RatePlan:
        return plan(self.plan_key)

    @property
    def standard_total(self) -> Decimal:
        """What the work is worth at full rate."""
        return _money(sum((line.standard_amount for line in self.lines), Decimal(0)))

    @property
    def discount_total(self) -> Decimal:
        return _money(sum((line.discount_amount(self.rate_plan)
                           for line in self.lines), Decimal(0)))

    @property
    def total(self) -> Decimal:
        """What the client actually pays."""
        return _money(self.standard_total - self.discount_total)

    @property
    def is_paid(self) -> bool:
        return self.paid_on is not None

    @property
    def is_issued(self) -> bool:
        return self.issued_on is not None

    @property
    def shows_a_discount(self) -> bool:
        return self.discount_total > 0

    def is_overdue(self, today: date) -> bool:
        return (self.is_issued and not self.is_paid
                and self.due_on is not None and self.due_on < today)

    # -- building ----------------------------------------------------------

    def add(self, service_code: str, *, quantity: Decimal | int | str = 1,
            note: str = "", performed_on: date | None = None,
            rate_override: Decimal | None = None) -> InvoiceLine:
        """Put a service on the invoice at its standard rate.

        ``rate_override`` exists because real work sometimes is not standard —
        but it overrides the VALUE, never the discount. Adjusting what the work
        was worth is an honest thing to record; secretly discounting by shaving
        the rate would hide the very thing this invoice exists to show.
        """
        if self.is_issued:
            raise BillingError(
                f"Invoice {self.invoice_id} was issued on {self.issued_on} and "
                f"cannot be changed. Raise a new invoice, or credit this one.")
        svc: Service = service(service_code)
        qty = Decimal(str(quantity))
        if not qty.is_finite():
            raise BillingError(
                f"{quantity!r} is not a quantity. Write how many as a plain "
                f"number, like 1 or 2 — three rentals is three Schedule Es.")
        if qty <= 0:
            raise BillingError(f"Quantity for {service_code!r} must be positive")
        if svc.unit == "fixed" and qty != 1:
            raise BillingError(
                f"{svc.name} is a fixed-price service — quantity must be 1. "
                f"If it genuinely took more, use rate_override to record what it "
                f"was worth.")
        rate = svc.standard_rate if rate_override is None else Decimal(str(rate_override))
        # Finiteness first: a signalling NaN raises InvalidOperation on the very
        # comparison used to decide whether the rate moved, so it has to be
        # refused before anything looks at it.
        self._check_is_an_amount(rate)
        adjusted = rate_override is not None and rate != svc.standard_rate
        self._check_the_rate(svc, rate, note=note, adjusted=adjusted)
        line = InvoiceLine(
            service_code=svc.code, label=svc.label_for_client, quantity=qty,
            standard_rate=rate, note=note, performed_on=performed_on,
            rate_adjusted=adjusted)
        self.lines.append(line)
        return line

    @staticmethod
    def _check_is_an_amount(rate: Decimal) -> None:
        """``Decimal()`` accepts NaN and Infinity, and every guard written as a
        comparison silently passes NaN — so this is asked before any comparison
        is made, not alongside them."""
        if not rate.is_finite():
            raise BillingError(
                f"{rate} is not an amount. A price has to be a plain number of "
                f"dollars, like 450 or 187.50.")

    @staticmethod
    def _check_the_rate(svc: Service, rate: Decimal, *, note: str,
                        adjusted: bool) -> None:
        """Guard the one hole a per-line price opens in the whole design.

        ``issue()`` refuses a reduced PLAN with no recorded basis. A rate
        override is a reduction by another route, and left unguarded it walks
        straight past that refusal: bill a 450 return at 180, and the invoice
        shows no discount, records no reason, and tells the client the amount
        due is $180 — the exact opacity the plan_basis rule exists to prevent.

        This lives on ``add()`` rather than on the screen deliberately. A guard
        in the view only covers the path the view takes; a draft restored from
        a session, rebuilt at issue time, or written by a script would slip
        past it. The engine is the only place every caller has to go through.

        Pricing something HIGHER needs no defence — that is the work genuinely
        being worth more, and it is recorded in plain sight either way.
        """
        if rate < 0:
            raise BillingError(
                f"{svc.name} cannot be billed at {rate}. A negative invoice is "
                f"not a credit note — if money is owed back, that is a separate "
                f"act, not a line on this bill.")
        if adjusted and rate < svc.standard_rate and not note.strip():
            raise BillingError(
                f"Billing {svc.name} at {rate:,.2f} when the catalogue says it "
                f"is worth {svc.standard_rate:,.2f} is a reduction, and it needs "
                f"a recorded reason — the same rule as a reduced rate plan. "
                f"Write why, and the client sees the adjustment rather than just "
                f"a smaller number they cannot interpret.")

    def issue(self, *, on: date, due_in_days: int = 30) -> "Invoice":
        """Fix the invoice. After this it cannot change.

        Refuses a reduced plan with no recorded basis, and refuses an empty
        invoice — sending someone a bill for nothing is a worse mistake than
        forgetting to bill them.
        """
        from datetime import timedelta

        if not self.lines:
            raise BillingError(
                f"Invoice {self.invoice_id} has no lines. Add what the client "
                f"received before issuing it.")
        rate_plan = self.rate_plan
        if rate_plan.requires_basis and not self.plan_basis.strip():
            raise BillingError(
                f"The {rate_plan.name} plan needs a recorded reason before this "
                f"invoice can go out. Write why this client is on it — a reduced "
                f"rate with no basis is improvisation, and improvisation is what "
                f"looks arbitrary when two clients compare notes.")
        self.issued_on = on
        self.due_on = on + timedelta(days=due_in_days)
        return self

    # -- how it reads ------------------------------------------------------

    def as_lines(self) -> list[tuple[str, str]]:
        """(description, amount) for each line, at FULL value."""
        return [(line.describe(), f"{line.standard_amount:,.2f}") for line in self.lines]

    def summary_block(self) -> str:
        """The whole invoice as the client reads it.

        Full value first, then the reduction with its name, then what they pay.
        A client on a reduced rate sees what they were given.
        """
        width = 56
        rows = [f"{desc:<{width}}{amount:>12}" for desc, amount in self.as_lines()]
        rows.append("")
        rate_plan = self.rate_plan
        if self.shows_a_discount:
            rows.append(f"{'Full value of work':<{width}}{self.standard_total:>12,.2f}")
            label = rate_plan.client_label or rate_plan.name
            pct = f"{rate_plan.discount_pct:g}%"
            rows.append(f"{label + '  ' + pct:<{width}}{-self.discount_total:>12,.2f}")
            rows.append("")
        rows.append(f"{'TOTAL DUE' if not rate_plan.is_free else 'TOTAL — no charge':<{width}}"
                    f"{self.total:>12,.2f}")
        return "\n".join(rows)

    def client_sentence(self) -> str:
        """One line for an email, honest about the discount."""
        if self.rate_plan.is_free:
            return (f"There is no charge for this — the work is itemised at its full "
                    f"value of ${self.standard_total:,.2f} so you can see what was done.")
        if self.shows_a_discount:
            return (f"The work came to ${self.standard_total:,.2f} at our standard "
                    f"rates; with the {self.rate_plan.name.lower()} applied, the amount "
                    f"due is ${self.total:,.2f}.")
        return f"The amount due is ${self.total:,.2f}."


def next_invoice_number(existing, *, year: int) -> str:
    """Sequential within a year: ``2026-0001``.

    Derived from what already exists rather than a stored counter, so it cannot
    drift out of step with reality or hand out the same number twice after a
    restart.
    """
    prefix = f"{year}-"
    used = [inv.invoice_id for inv in existing if str(inv.invoice_id).startswith(prefix)]
    highest = 0
    for number in used:
        tail = str(number)[len(prefix):]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{prefix}{highest + 1:04d}"


def billed_to_date(invoices, *, client_id: str, tax_year: int) -> dict[str, Decimal]:
    """What this client has already been charged — the piecemeal running total."""
    mine = [i for i in invoices
            if i.client_id == client_id and i.tax_year == tax_year and i.is_issued]
    standard = _money(sum((i.standard_total for i in mine), Decimal(0)))
    charged = _money(sum((i.total for i in mine), Decimal(0)))
    paid = _money(sum((i.total for i in mine if i.is_paid), Decimal(0)))
    return {"invoices": Decimal(len(mine)), "standard_value": standard,
            "charged": charged, "paid": paid, "outstanding": _money(charged - paid)}
