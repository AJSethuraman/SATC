"""Free label-anchored extraction from text-layer PDFs (no API key, no OCR)."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")

from satc.config import load_extraction_map  # noqa: E402
from satc.fixtures.sample_docs import TEXT_W2, write_text_form  # noqa: E402
from satc.ingest.readers import TextAnchorReader  # noqa: E402

W2 = load_extraction_map("w2")


def test_reads_money_and_tin_from_text():
    fields = TextAnchorReader(W2).read_text("\n".join(TEXT_W2)).labeled_fields
    assert fields["Box 1 - Wages, tips, other comp"] == "98000.00"
    assert fields["Box 2 - Federal income tax withheld"] == "12500.00"
    assert fields["Employer EIN"] == "31-0009999"           # masked later by MapExtractor


def test_strict_money_confident_but_free_text_flagged():
    r = TextAnchorReader(W2).read_text("\n".join(TEXT_W2))
    assert "Box 1 - Wages, tips, other comp" not in r.uncertain_labels   # strict cents => confident
    assert "Employer name" in r.uncertain_labels                         # name grab => review


def test_does_not_mistake_a_year_for_an_amount():
    text = "Interest income reported for tax year 2024."   # a year, not a dollar amount
    fields = TextAnchorReader(load_extraction_map("1099int")).read_text(text).labeled_fields
    assert "Box 1 - Interest income" not in fields


def test_reads_a_real_text_layer_pdf_end_to_end(tmp_path):
    p = tmp_path / "consolidated.pdf"        # text layer, NOT a fillable form
    write_text_form(p, TEXT_W2)
    fields = TextAnchorReader(W2).read(str(p)).labeled_fields
    assert fields.get("Box 1 - Wages, tips, other comp") == "98000.00"


def test_short_anchor_does_not_match_inside_a_longer_word():
    # "State" (Box 15) must not fire inside "Statement".
    fields = TextAnchorReader(W2).read_text("Form W-2 Wage and Tax Statement 2024").labeled_fields
    assert "Box 15 - State" not in fields


def test_sensitive_tin_is_masked_through_the_extractor():
    from satc.ingest import MapExtractor
    cfg = load_extraction_map("1099int")
    r = TextAnchorReader(cfg).read_text("Interest income 1200.00\nPayer name Heartland Bank\n"
                                        "Payer TIN 34-0001111")
    staged = MapExtractor(cfg).extract(document_id="x", client_id="c", tax_year=2024,
                                       labeled_fields=r.labeled_fields,
                                       confidences=r.confidence_map())
    tin = next(f for f in staged.fields if f.field_path == "int.payer_tin")
    assert tin.effective_text() == "**-***1111"
    assert "34-0001111" not in tin.effective_text()
