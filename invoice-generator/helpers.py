"""Small shared helpers: currency formatting and form parsing."""
from datetime import datetime

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "$",
    "AUD": "$",
    "INR": "₹",
    "CHF": "CHF ",
    "CNY": "¥",
    "BRL": "R$",
    "ZAR": "R",
    "MXN": "$",
    "SGD": "$",
    "NZD": "$",
}


def currency_symbol(code):
    return CURRENCY_SYMBOLS.get((code or "USD").upper(), "")


EM_DASH = "\u2014"


def format_money(amount, code="USD", symbol=True):
    """Return a money string in the SAT-C house conventions.

    The single place money becomes a string anywhere in this app. The rules come
    from ``satc-handoff/03-COLLATERAL/SATC Figures and Tables.html``, which says
    in terms that they apply to the Jinja templates here as much as to the site:

    * **Two decimals always**, including round amounts -- ``$300.00``, never
      ``$300``. Thousands separated above 999.
    * **Negatives in parentheses, never a minus sign** -- ``($1,500.00)``. This
      is the accounting convention, and it is the one that survives a
      photocopier; a red minus does not. Colour is never the only signal.
    * **Credits drop the symbol** when they sit in a column that already carries
      it -- ``(1,500.00)``, not ``($1,500.00)``. Pass ``symbol=False``.
    * **Nil is an em dash**, and it means something different from a computed
      zero. ``None`` is nothing to report; ``0`` came out to zero and prints as
      ``$0.00``.

    ``symbol=False`` also serves GAAP-style statement rows, where the symbol
    belongs on the first row of a column and on totals only.
    """
    if amount is None:
        return EM_DASH
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0.0
    prefix = currency_symbol(code) if symbol else ""
    body = f"{prefix}{abs(amount):,.2f}"
    return f"({body})" if amount < 0 else body


def parse_float(value, default=0.0):
    if value is None:
        return default
    value = str(value).strip().replace(",", "")
    if value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
