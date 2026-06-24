"""Content-based classification: identify documents by reading them, not by name."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")

from satc.fixtures.sample_docs import (  # noqa: E402
    write_plain_pdf,
    write_sample_1099int,
    write_sample_w2,
)
from satc.ingest import load_classifier  # noqa: E402


def test_fillable_w2_classified_by_form_fields_despite_bad_name(tmp_path):
    # A W-2 saved under a meaningless scan name — a filename sorter would miss it.
    path = tmp_path / "scan0012.pdf"
    write_sample_w2(path)
    c = load_classifier(has_key=False).classify_path(path)

    assert c.label == "W-2"
    assert c.key == "w2"
    assert c.method == "form fields"
    assert c.confidence == "HIGH"
    assert c.extractable


def test_fillable_1099int_classified_by_form_fields(tmp_path):
    path = tmp_path / "IMG_4471.pdf"
    write_sample_1099int(path)
    c = load_classifier(has_key=False).classify_path(path)

    assert c.label == "1099-INT"
    assert c.method == "form fields"
    assert c.extractable


def test_flat_document_classified_by_text_layer(tmp_path):
    # No form fields, but the printed title names it. Read for free, no OCR.
    path = tmp_path / "random_name.pdf"
    write_plain_pdf(path, "SATC Engagement Letter — Maplewood 2024")
    c = load_classifier(has_key=False).classify_path(path)

    assert c.label == "Engagement letter"
    assert c.method == "text"
    assert not c.extractable          # filed, not extracted


def test_filename_is_only_a_fallback(tmp_path):
    # Content is silent (no fields, no marker text), so the name breaks the tie.
    path = tmp_path / "W2_clientname.pdf"
    write_plain_pdf(path, "Miscellaneous correspondence")
    c = load_classifier(has_key=False).classify_path(path)

    assert c.label == "W-2"
    assert c.method == "filename"
    assert c.confidence == "LOW"


def test_unidentifiable_without_key_is_unclassified(tmp_path):
    path = tmp_path / "mystery.pdf"
    write_plain_pdf(path, "Nothing recognizable here")
    c = load_classifier(has_key=False).classify_path(path)

    assert c.method == "unclassified"
    assert not c.extractable


# -- weighted text scoring (ported from the keyword-scoring approach) -----------

def _clf():
    return load_classifier(has_key=False)


def test_text_scoring_classifies_strong_title():
    c = _clf().classify_text("2024 Form W-2  Wage and Tax Statement")
    assert c.label == "W-2" and c.confidence == "HIGH"


def test_w2_structural_fallback_without_title():
    # No "Wage and Tax Statement" title — recognized by its box labels alone.
    text = "Social Security Wages  Medicare Wages and Tips  Social Security Tax Withheld"
    c = _clf().classify_text(text)
    assert c.label == "W-2" and c.extractable


def test_close_runner_up_is_downgraded_to_medium():
    # A consolidated statement that reads as both 1099-INT and 1099-DIV: don't guess.
    text = "1099-INT Interest Income   1099-DIV Dividends and Distributions"
    c = _clf().classify_text(text)
    assert c.confidence == "MEDIUM"


def test_ocr_hyphen_repair_in_form_names():
    # A scan that dropped the hyphen + used an em dash still matches 1099-INT.
    c = _clf().classify_text("Form 1099 INT — Interest Income")
    assert c.label == "1099-INT"


def test_weak_keyword_alone_does_not_classify():
    # A single low-weight phrase is below threshold — falls through, never guesses.
    assert _clf().classify_text("Qualified dividends were mentioned in passing") is None


@pytest.mark.parametrize("text,label", [
    ("Form 1099-NEC  Nonemployee Compensation", "1099-NEC"),
    ("Form 1099-K  Payment Card and Third Party Network Transactions", "1099-K"),
    ("Form 1099-R  Distributions From Pensions, Annuities, Retirement", "1099-R"),
    ("Form 1095-A  Health Insurance Marketplace Statement", "1095-A"),
    ("Form 1098-T  Tuition Statement", "1098-T"),
])
def test_additional_forms_are_recognized(text, label):
    # Recognized so an arriving copy auto-closes its request; filed, not extracted.
    c = _clf().classify_text(text)
    assert c is not None and c.label == label and c.confidence == "HIGH"
    assert not c.extractable
