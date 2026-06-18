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
