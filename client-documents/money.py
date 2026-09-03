"""The one place a number becomes a money string.

Conventions from `satc-handoff/03-COLLATERAL/SATC Figures and Tables.html`, which
is the document the authoring contract defers to for figures:

* **Two decimals always**, including round amounts — ``$450.00``, never ``$450``.
  Thousands separated above 999.
* **Negatives in parentheses, never a minus sign** — ``($1,500.00)``. It is the
  accounting convention and it survives a photocopier; a red minus does not.
* **Credits drop the symbol** in a column that already carries it —
  ``(1,500.00)``. Pass ``symbol=False``.
* **Nil is an em dash.** ``None`` is nothing to report; ``0`` is a computed zero
  and prints as ``$0.00``. Accountants read the difference.

`invoice-generator/helpers.py` implements the same rules for the Flask app. Two
implementations of one convention is exactly what the collateral warns about, so
they are tested against the same worked example — the "Correct" column of that
document — and if they ever disagree, one of them is wrong.
"""

from __future__ import annotations

EM_DASH = "—"

SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "$", "AUD": "$"}


def symbol_for(code: str = "USD") -> str:
    return SYMBOLS.get((code or "USD").upper(), "")


def money(amount, code: str = "USD", *, symbol: bool = True) -> str:
    """Format one amount. The only place this happens."""
    if amount is None:
        return EM_DASH
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        # A `[CONFIRM: ...]` reaching here is a decision nobody made. Pass it
        # through untouched so the merge engine refuses the document, rather
        # than turning it into $0.00 and quietly quoting a client nothing.
        return str(amount)
    prefix = symbol_for(code) if symbol else ""
    body = f"{prefix}{abs(amount):,.2f}"
    return f"({body})" if amount < 0 else body


def parse(amount) -> float | None:
    """A money string back to a number, or None when it is not one.

    THE OTHER HALF OF `money`, and it lived in `invoicing` alone until a
    second caller needed it. Two parsers for one format is the thing this
    module's own docstring warns about: one of them would learn about a
    `[CONFIRM:` or a credit and the other would not, and the one that did not
    would be the one deciding whether a client had been billed over their
    estimate.

    `None` is "cannot be compared", never zero. A `[CONFIRM:` reaching here is
    a decision nobody made, and reading it as nothing would let a comparison
    against it quietly succeed.
    """
    import re

    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
        return float(amount)
    if not isinstance(amount, str):
        return None
    cleaned = amount.replace(",", "").strip()
    cleaned = re.sub(r"^[^\d\-\u2212.]+", "", cleaned).replace("\u2212", "-")
    try:
        return float(cleaned)
    except ValueError:
        return None
