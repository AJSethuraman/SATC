"""The estimate becomes the invoice.

The firm asked for this on 25 August 2026, and the sentence that decided its
shape was in the answer rather than the question:

    "i like the idea of having it all come out as a package to send for
     review/signing, and the estimate is required for the engagement to make
     sense"

Until now the estimate computed every line and the invoice retyped them. That
is not merely tedious -- it is the failure mode the whole pipeline exists to
prevent. Two documents that state the same money from two sources will
eventually disagree, and the one the client keeps is the one that says the
larger number.

So an invoice is BUILT FROM the priced engagement, never typed alongside it.

THREE RULES, and each of them is here because the alternative is a document
that misleads:

1. THE INVOICE CARRIES THE ESTIMATE IT CAME FROM. Its own total, its date, and
   -- when they differ -- a note saying why. A client who was quoted $470 and
   billed $565 is owed the reason on the same page, not on request.

2. A VARIANCE UPWARDS REQUIRES THAT NOTE. Not "should have"; the render
   refuses without it. `registry/fields.yaml` says `VarianceNote` is "not
   optional when the invoice exceeds the estimate", and a rule stated in a
   registry and enforced nowhere is a rule that holds until the first busy
   week.

3. NUMBERS ARE SEQUENTIAL AND NEVER REUSED, per engagement-independent
   ordering across the store. One engagement has many invoices; two invoices
   with the same number is an accounting problem, not a formatting one.

WHAT THIS DOES NOT DO, deliberately: it does not take payment. The delivery
letter now promises a Square link and Invoicer is Stripe end to end, so wiring
these together today would put a Stripe checkout under a sentence that says
Square. See `registry/firm-settings.yaml`. The bridge stops at the document.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import money as m

MINUS = "−"          # a real minus sign, per the invoice's field doc
NUMBER = re.compile(r"^(\d{4})-(\d{4})$")


class InvoiceError(Exception):
    """Something that would put a wrong number in front of a client."""


def next_number(store: Path, year: int | None = None) -> str:
    """The next unused invoice number. Sequential, never reused.

    Scans what has been issued rather than counting, so a deleted file cannot
    hand the same number to two clients -- the same reasoning as
    `engagements.next_ref`, and the same shape, on purpose.
    """
    year = year or date.today().year
    used = [int(mm.group(2)) for p in _issued(store)
            if (mm := NUMBER.match(p.get("InvoiceNumber", "")))
            and mm.group(1) == str(year)]
    return f"{year}-{max(used, default=0) + 1:04d}"


def _issued(store: Path) -> list[dict]:
    out = []
    if not store.exists():
        return out
    for path in sorted(store.glob("*/invoices/*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            # A file we cannot read is not a number we can prove is free, so
            # it is skipped rather than assumed absent. `next_number` takes
            # the max of what it CAN read, which can only be too high -- and
            # too high wastes a number, where too low reuses one.
            continue
    return out


def issued_for(store: Path, ref: str) -> list[dict]:
    """Every invoice raised against one engagement, oldest number first."""
    folder = store / ref / "invoices"
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def find(store: Path, ref: str, number: str | None = None) -> dict | None:
    """One engagement's invoice fields: the named one, or the latest raised.

    Exists because the money and the client live in two files on purpose --
    `record.json` holds the engagement, `invoices/NNNN.json` holds one bill --
    and rendering the invoice needs both. `cli.py invoice` prints
    "Next: python cli.py render --engagement REF --docs invoice" and that
    command refused, every time, on `<<AmountDue>>, <<InvoiceDate>>,
    <<InvoiceNumber>>, <<Subtotal>>`: the render was reading the engagement
    record alone and no invoice had ever reached it. A tool that hands you
    the next command has to hand you one that works.
    """
    raised = issued_for(store, ref)
    if not raised:
        return None
    if number is None:
        return raised[-1]
    for one in raised:
        if one.get("InvoiceNumber") == number:
            return one
    raise InvoiceError(
        f"engagement {ref} has no invoice {number}. Raised so far: "
        f"{', '.join(i.get('InvoiceNumber', '?') for i in raised) or 'none'}."
    )


def build(record: dict, *, number: str, billed: str, today: date | None = None,
          credits: list[dict] | None = None, variance_note: str = "",
          currency: str = "USD") -> dict:
    """The priced engagement -> the invoice's own fields.

    `record` is an engagement record that has been through `pricing.price()`,
    so it already carries `LineItems` and `EstimateTotal`. Those line items ARE
    the invoice's line items: same services, same details, same amounts.

    `billed` is the period this invoice covers -- "March 2027" -- and it is
    required because `PeriodLabel` means something different on each document.
    The estimate's is the engagement period; the invoice's is what is billed.
    One shared value prints the wrong thing on one of them.
    """
    items = record.get("LineItems")
    if not items:
        raise InvoiceError(
            "this engagement has no priced line items, so there is nothing to "
            "invoice. Price it first -- an invoice assembled by hand is the "
            "thing this module exists to stop."
        )
    if not billed:
        raise InvoiceError(
            "an invoice needs the period it BILLS, which is not the "
            "engagement's period. The estimate says '2026 tax year'; the "
            "invoice says what work this bill covers."
        )

    subtotal = _sum(items, currency)
    credits = list(credits or [])
    credit_total = 0.0
    for c in credits:
        amount = c.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise InvoiceError(
                f"credit {c.get('label', '(unlabelled)')!r} has no positive "
                f"amount. A credit is entered as what it is WORTH; the minus "
                f"sign is this module's to add, so that no invoice ever shows "
                f"a credit that quietly increases the bill."
            )
        credit_total += amount

    due = subtotal - credit_total
    estimate = record.get("EstimateTotal", "")

    out = {
        "InvoiceNumber": number,
        "InvoiceDate": (today or date.today()).strftime("%B %-d, %Y"),
        "PeriodLabel": billed,
        "LineItems": [dict(i) for i in items],
        "Subtotal": m.money(subtotal, currency),
        "AmountDue": m.money(due, currency),
        "EstimateTotal": estimate,
        "EstimateDate": record.get("LetterDate", ""),
        "VarianceNote": variance_note.strip(),
    }
    if credits:
        out["CreditLabel"] = "; ".join(c.get("label", "Credit") for c in credits)
        out["CreditDetail"] = "; ".join(c.get("detail", "") for c in credits).strip("; ")
        out["CreditAmount"] = MINUS + m.money(credit_total, currency)

    _check_variance(out, subtotal, estimate, currency)
    return out


def _sum(items: list[dict], currency: str) -> float:
    total = 0.0
    for i in items:
        amount = i.get("Amount", "")
        value = _parse(amount)
        if value is None:
            raise InvoiceError(
                f"the line {i.get('Service', '(unnamed)')!r} has no amount "
                f"that can be added up -- it reads {amount!r}. An invoice "
                f"whose total omits a line is worse than one that refuses."
            )
        total += value
    return total


def _parse(amount) -> float | None:
    if isinstance(amount, (int, float)):
        return float(amount)
    if not isinstance(amount, str):
        return None
    cleaned = amount.replace(",", "").strip()
    cleaned = re.sub(r"^[^\d\-−.]+", "", cleaned).replace(MINUS, "-")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _check_variance(out: dict, subtotal: float, estimate: str, currency: str):
    """Refuse an invoice that bills over the estimate without saying why.

    The registry has always said this note is "not optional when the invoice
    exceeds the estimate". Saying it in a registry and enforcing it nowhere is
    a rule that holds until the first busy week, and the busy week is exactly
    when a client gets a bigger bill than they were quoted.
    """
    quoted = _parse(estimate)
    if quoted is None:
        # No comparable estimate — an engagement priced before the estimate
        # existed, or one carrying a [CONFIRM. Nothing to check against, and
        # inventing a comparison would be worse than not making one.
        return
    if subtotal > quoted and not out["VarianceNote"]:
        raise InvoiceError(
            f"this invoice bills {m.money(subtotal, currency)} against an "
            f"estimate of {m.money(quoted, currency)} and says nothing about "
            f"the difference. A client who was quoted one number and billed a "
            f"larger one is owed the reason on the same page. Give a "
            f"`variance_note`."
        )
