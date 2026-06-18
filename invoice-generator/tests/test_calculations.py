"""Unit tests for invoice total calculations.

Run with: ``python -m pytest`` from the project root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Invoice, LineItem  # noqa: E402


def _invoice(**kwargs):
    inv = Invoice(**kwargs)
    return inv


def test_subtotal():
    inv = _invoice()
    inv.items = [
        LineItem(description="A", quantity=2, rate=50),
        LineItem(description="B", quantity=1, rate=25.5),
    ]
    assert inv.subtotal == 125.5


def test_flat_discount():
    inv = _invoice(discount_value=20, discount_is_percent=False)
    inv.items = [LineItem(quantity=1, rate=100)]
    assert inv.discount_amount == 20
    assert inv.taxable_base == 80


def test_percent_discount():
    inv = _invoice(discount_value=10, discount_is_percent=True)
    inv.items = [LineItem(quantity=1, rate=200)]
    assert inv.discount_amount == 20
    assert inv.taxable_base == 180


def test_percent_tax_applies_after_discount():
    inv = _invoice(
        discount_value=10,
        discount_is_percent=True,
        tax_value=10,
        tax_is_percent=True,
    )
    inv.items = [LineItem(quantity=1, rate=200)]
    # base = 180, tax = 18
    assert inv.tax_amount == 18
    assert inv.total == 198


def test_flat_tax_and_shipping_and_total():
    inv = _invoice(
        tax_value=5,
        tax_is_percent=False,
        shipping=15,
    )
    inv.items = [LineItem(quantity=2, rate=100)]
    # subtotal 200, tax 5, shipping 15 => 220
    assert inv.total == 220


def test_balance_due():
    inv = _invoice(shipping=0, amount_paid=50)
    inv.items = [LineItem(quantity=1, rate=120)]
    assert inv.total == 120
    assert inv.balance_due == 70


def test_full_combo():
    inv = _invoice(
        discount_value=25,
        discount_is_percent=False,
        tax_value=8.25,
        tax_is_percent=True,
        shipping=10,
        amount_paid=100,
    )
    inv.items = [
        LineItem(quantity=3, rate=40),  # 120
        LineItem(quantity=1, rate=80),  # 80
    ]
    assert inv.subtotal == 200
    assert inv.discount_amount == 25
    assert inv.taxable_base == 175
    assert inv.tax_amount == round(175 * 0.0825, 2)  # 14.44
    assert inv.total == round(175 + 14.44 + 10, 2)  # 199.44
    assert inv.balance_due == round(199.44 - 100, 2)  # 99.44
