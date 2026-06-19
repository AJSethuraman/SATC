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


def format_money(amount, code="USD"):
    """Return a human-friendly currency string, e.g. ``$1,250.00``."""
    try:
        amount = float(amount or 0.0)
    except (TypeError, ValueError):
        amount = 0.0
    symbol = currency_symbol(code)
    return f"{symbol}{amount:,.2f}"


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
