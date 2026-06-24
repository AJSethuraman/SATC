"""Deterministic paystub layout reader: parsing, teach->apply, profiles."""

from __future__ import annotations

from decimal import Decimal

import pytest

from satc.ingest import paystub_profiles as pp
from satc.ingest.paystub_layout import (
    Layout,
    Word,
    apply_profile,
    build_rules,
    parse_currency,
    parse_date,
)


def test_parse_currency_handles_signs_and_groups():
    assert parse_currency("$1,234.56") == Decimal("1234.56")
    assert parse_currency("(951.36)") == Decimal("-951.36")
    assert parse_currency("2,500.00") == Decimal("2500.00")
    assert parse_currency("1,23") is None        # ambiguous comma -> reject
    assert parse_currency("3.200,00") is None     # European -> reject
    assert parse_currency("words") is None


def test_parse_date_formats():
    assert parse_date("01/15/2025") == "2025-01-15"
    assert parse_date("Jan 15, 2025") == "2025-01-15"
    assert parse_date("2025-03-09") == "2025-03-09"
    assert parse_date("nope") is None


def _two_column_stub(gross_cur, gross_ytd, fed_cur, fed_ytd, *, y_shift=0.0):
    """Build a synthetic 2-column stub layout (normalized coords)."""
    y1a, y1b = 0.10 + y_shift, 0.12 + y_shift
    y2a, y2b = 0.15 + y_shift, 0.17 + y_shift
    words = [
        Word("Gross", 0.05, y1a, 0.10, y1b),
        Word("Pay", 0.11, y1a, 0.15, y1b),
        Word(gross_cur, 0.50, y1a, 0.60, y1b),
        Word(gross_ytd, 0.70, y1a, 0.82, y1b),
        Word("Federal", 0.05, y2a, 0.10, y2b),
        Word("Income", 0.11, y2a, 0.16, y2b),
        Word("Tax", 0.17, y2a, 0.20, y2b),
        Word(fed_cur, 0.50, y2a, 0.58, y2b),
        Word(fed_ytd, 0.70, y2a, 0.80, y2b),
    ]
    return Layout(image_png_b64="", img_width=1000, img_height=1300, words=words)


def test_teach_then_apply_reads_correct_columns():
    taught = _two_column_stub("2,500.00", "30,000.00", "300.00", "3,600.00")
    # "Click" the four value words by index (see word order above).
    assignments = {
        "gross_pay_per_period": [2],
        "ytd_taxable_wages": [3],
        "federal_tax_withheld_per_period": [7],
        "ytd_federal_tax_withheld": [8],
    }
    rules = build_rules(taught.words, assignments)
    by_field = {r.field: r for r in rules}
    assert by_field["gross_pay_per_period"].label_text.lower() == "gross pay"
    assert by_field["federal_tax_withheld_per_period"].label_text.lower() == "federal income tax"

    # A DIFFERENT pay period (rows shifted, new numbers) must still read right.
    later = _two_column_stub("2,500.00", "32,500.00", "310.00", "3,910.00", y_shift=0.03)
    from satc.ingest.paystub_layout import Profile
    out = apply_profile(later, Profile(name="Acme", pay_frequency="biweekly", rules=rules))
    assert out["gross_pay_per_period"] == "2500.00"
    assert out["ytd_taxable_wages"] == "32500.00"
    assert out["federal_tax_withheld_per_period"] == "310.00"
    assert out["ytd_federal_tax_withheld"] == "3910.00"
    assert out["pay_frequency"] == "biweekly"


def test_profile_store_save_list_and_match(tmp_path, monkeypatch):
    monkeypatch.setenv("SATC_DATA_DIR", str(tmp_path))
    taught = _two_column_stub("2,500.00", "30,000.00", "300.00", "3,600.00")
    rules = build_rules(taught.words, {
        "gross_pay_per_period": [2], "federal_tax_withheld_per_period": [7]})
    from satc.ingest.paystub_layout import Profile
    pp.save_profile(Profile(name="Acme (ADP)", pay_frequency="biweekly", rules=rules))

    names = [p.name for p in pp.list_profiles()]
    assert "Acme (ADP)" in names

    later = _two_column_stub("2,500.00", "32,500.00", "310.00", "3,910.00", y_shift=0.03)
    matched = pp.match_profile(later)
    assert matched is not None and matched.name == "Acme (ADP)"

    blank = Layout(image_png_b64="", img_width=10, img_height=10,
                   words=[Word("Net", 0.1, 0.1, 0.2, 0.12), Word("5.00", 0.5, 0.1, 0.6, 0.12)])
    assert pp.match_profile(blank) is None


def _pymupdf_available() -> bool:
    try:
        import pymupdf  # noqa: F401
        return True
    except ImportError:
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            return False


@pytest.mark.skipif(not _pymupdf_available(), reason="PyMuPDF not installed")
def test_extract_layout_from_textlayer_pdf():
    import io

    from reportlab.pdfgen import canvas

    from satc.ingest.paystub_layout import extract_layout

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Courier", 11)
    c.drawString(60, 760, "Gross Pay            2,500.00    30,000.00")
    c.drawString(60, 742, "Federal Income Tax     300.00     3,600.00")
    c.showPage()
    c.save()

    layout = extract_layout(buf.getvalue(), "application/pdf")
    assert layout.image_png_b64                     # rendered page present
    assert layout.words                             # words extracted
    joined = layout.text.lower()
    assert "gross" in joined and "federal" in joined
