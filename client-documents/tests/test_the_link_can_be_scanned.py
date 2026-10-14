"""A printed invoice carries its payment link as a QR code.

The firm, 13 Oct 2026: "can't it generate a qr code for the link". A link on
paper cannot be clicked; a phone camera can read a QR code.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import invoicing  # noqa: E402

TEMPLATE = Path(__file__).resolve().parents[2] / "satc-handoff" / "04-TEMPLATES" / "SATC Invoice.html"
URL = "https://square.link/u/EXAMPLE1"


def test_the_qr_is_an_svg_image_source():
    src = invoicing.payment_qr(URL)
    assert src.startswith("data:image/svg+xml;base64,")
    svg = base64.b64decode(src.split(",", 1)[1]).decode("utf-8")
    assert svg.lstrip().startswith("<svg")


def test_a_different_link_draws_a_different_code():
    """The picture is of the link, not a fixed graphic."""
    assert invoicing.payment_qr(URL) != invoicing.payment_qr(URL + "X")


def test_the_qr_is_only_drawn_inside_the_payment_link_block():
    """An invoice with no link must not show a code for one."""
    html = TEMPLATE.read_text(encoding="utf-8")
    i = html.index("&lt;&lt;PaymentQr&gt;&gt;")
    before = html[:i]
    assert before.rfind("[[IF PaymentLink]]") > before.rfind("[[END IF]]")


def test_a_bill_without_a_link_gets_no_code():
    import merge
    assert "PaymentQr" not in merge._derived({"InvoiceNumber": "2026-0100"})


def test_a_bill_with_a_link_gets_one():
    import merge
    out = merge._derived({"PaymentLink": True, "PaymentUrl": URL})
    assert out["PaymentQr"] == invoicing.payment_qr(URL)
