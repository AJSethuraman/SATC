"""The reader ladder must not hide its own parser failures behind OCR.

The firm, 30 August 2026, on why the scanner disappointed in the field:

    "it was not smart enough for some reason even though I suggested it to use
     PDF scanning over OCR when applicable"

It was applicable. The ladder simply could not tell. Its only question at each
rung was *did this reader return any fields*, so these two situations were
indistinguishable to it:

  * a photograph of a W-2, which has no text to read -- OCR is correct here;
  * a software-printed W-2 with a perfectly good text layer that our anchor
    reader failed to match -- OCR is a WORSE answer here, and worse, it is a
    worse answer that looks exactly like a good one.

The docstring above the ladder promised "fillable form fields -> text layer ->
local OCR". The code implemented "whichever rung produces fields first". A claim
in one place, behaviour in another, nothing comparing them -- the same shape as
every other bug this repository has had to find twice.

These tests compare them.
"""

from __future__ import annotations

import pymupdf
import pytest

from satc.app.state import AppState, text_layer_chars


def _pdf_with_text(path, lines):
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 16
    doc.save(str(path))
    doc.close()
    return path


def _pdf_of_pictures(path, lines):
    """The same words, but as pixels -- what a phone photo or a flatbed gives."""
    text = _pdf_with_text(path.with_name("_src.pdf"), lines)
    src = pymupdf.open(str(text))
    pix = src[0].get_pixmap(dpi=150)
    out = pymupdf.open()
    page = out.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.insert_image(page.rect, pixmap=pix)
    out.save(str(path))
    out.close()
    src.close()
    return path


# -- the fact the ladder was missing ------------------------------------------

def test_a_text_layer_pdf_reports_its_characters(tmp_path):
    p = _pdf_with_text(tmp_path / "printed.pdf",
                       ["Form W-2  Wage and Tax Statement",
                        "1 Wages, tips, other compensation  64,500.00"])
    assert text_layer_chars(p) > 40


def test_a_picture_pdf_reports_no_text(tmp_path):
    p = _pdf_of_pictures(tmp_path / "photo.pdf",
                         ["Form W-2  Wage and Tax Statement",
                          "1 Wages, tips, other compensation  64,500.00"])
    assert text_layer_chars(p) == 0


def test_a_file_that_is_not_a_pdf_reports_no_text(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello")
    assert text_layer_chars(p) == 0


def test_an_unreadable_file_reports_no_text_rather_than_raising(tmp_path):
    """A truncated or placeholder file must not take the ladder down with it."""
    p = tmp_path / "placeholder.pdf"
    p.write_bytes(b"")
    assert text_layer_chars(p) == 0


# -- and what the ladder now does with it -------------------------------------

def test_parser_failure_on_a_readable_document_is_reported_not_swallowed(tmp_path, monkeypatch):
    """A text-layer PDF our anchor reader cannot read must SAY so.

    This is the regression the firm hit. Before the fix this document fell
    through to OCR and the note read like an ordinary success.
    """
    p = _pdf_with_text(tmp_path / "printed.pdf",
                       ["Form W-2  Wage and Tax Statement",
                        "Employer: Buckeye Manufacturing LLC",
                        "1 Wages, tips, other compensation  64,500.00"])
    # An extraction map whose anchors match nothing in this document: the exact
    # shape of a real W-2 whose layout our anchors were not written for.
    cfg = {"doc_type": "W-2", "fields": [
        {"field_path": "w2.box1_wages", "label": "A label that appears nowhere",
         "money": True},
    ]}

    monkeypatch.setattr("satc.settings.ocr_enabled", lambda: False)
    monkeypatch.setattr("satc.settings.ollama_enabled", lambda: False)
    result, problem = AppState._read_document(p, cfg, False)

    assert result is None
    # The discriminating phrase is who gets BLAMED, not the words "text layer" --
    # the legitimate no-text-layer message contains those too, so asserting on
    # them would pass for the wrong reason.
    assert "our anchors, not the document" in problem, problem
    assert "64" not in problem, "the problem note must not quote the document"


def test_a_true_scan_is_not_blamed_on_the_parser(tmp_path, monkeypatch):
    """No text layer means OCR is the right rung -- no parser complaint."""
    p = _pdf_of_pictures(tmp_path / "photo.pdf",
                         ["Form W-2  Wage and Tax Statement",
                          "1 Wages, tips, other compensation  64,500.00"])
    cfg = {"doc_type": "W-2", "fields": [
        {"field_path": "w2.box1_wages", "label": "Wages, tips, other compensation",
         "money": True},
    ]}
    monkeypatch.setattr("satc.settings.ocr_enabled", lambda: False)
    monkeypatch.setattr("satc.settings.ollama_enabled", lambda: False)
    result, problem = AppState._read_document(p, cfg, False)

    assert result is None
    assert "our anchors, not the document" not in problem, \
        "a photograph has no text layer to fail at -- do not blame the parser"
    assert "no text layer" in problem.lower(), problem


def test_fillable_forms_still_short_circuit_before_any_of_this(tmp_path, monkeypatch):
    """The free, exact rung must still win, untouched by the new check."""
    doc = pymupdf.open()
    page = doc.new_page()
    widget = pymupdf.Widget()
    widget.field_name = "w2_box1_wages"
    widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    widget.rect = pymupdf.Rect(72, 72, 300, 96)
    widget.field_value = "64500.00"
    page.add_widget(widget)
    p = tmp_path / "fillable.pdf"
    doc.save(str(p))
    doc.close()

    cfg = {"doc_type": "W-2", "fields": [
        {"field_path": "w2.box1_wages", "label": "Box 1 - Wages",
         "pdf_field": "w2_box1_wages", "money": True},
    ]}
    monkeypatch.setattr("satc.settings.ocr_enabled", lambda: False)
    result, problem = AppState._read_document(p, cfg, False)
    assert result is not None and result.labeled_fields
    assert problem == ""


# -- the decision the firm made, 4 September 2026 ------------------------------

def test_a_readable_document_our_anchors_missed_still_reaches_a_model(tmp_path, monkeypatch):
    """S5, DECIDED: fall through to a model, but say whose fault it was.

    Two defensible ladders were argued and only one could ship. The stricter one
    said a text-layer PDF must never summon a model, because the document was
    readable and OUR PARSER is what failed -- asking a model there buries a
    fixable gap under an answer nobody can reproduce. The firm chose the other:

        fall through, and make the note say "our anchors, not the document".

    The reason is that a text layer can be genuine rubbish -- a scanner that
    emits a page of ligature soup produces characters without producing words --
    and refusing outright loses documents the later rungs do handle. Failing
    towards READING a document, with the parser gap named in the note, beats
    failing towards refusing one.

    THE STRICTER RULE WOULD PASS EVERY OTHER TEST IN THIS FILE. The two beside
    this one both disable OCR and vision, so they pin the note and say nothing
    about whether the ladder goes on. This test is the only thing standing
    between the chosen behaviour and a plausible-looking revert.
    """
    p = _pdf_with_text(tmp_path / "printed.pdf",
                       ["Form W-2  Wage and Tax Statement",
                        "1 Wages, tips, other compensation  64,500.00"])
    cfg = {"doc_type": "W-2", "fields": [
        {"field_path": "w2.box1_wages", "label": "A label that appears nowhere",
         "money": True},
    ]}

    reached = []

    class _Vision:
        def __init__(self, cfg):
            pass

        def read(self, path):
            reached.append(path)
            from satc.ingest.readers.base import ReadResult
            return ReadResult(labeled_fields={"A label that appears nowhere": "64500"})

    monkeypatch.setattr("satc.settings.ocr_enabled", lambda: False)
    monkeypatch.setattr("satc.settings.ollama_enabled", lambda: True)
    monkeypatch.setattr("satc.app.state.OllamaVisionReader", _Vision)

    result, problem = AppState._read_document(p, cfg, False)

    assert reached, \
        "the ladder stopped at the failed text layer instead of going on to the model"
    assert result is not None and result.labeled_fields, \
        "the model read the document and the ladder threw the answer away"
    # Reaching the model is HALF the decision. The other half is that the note
    # still blames the parser -- a silent fall-through is the bug this whole
    # file exists to prevent, and 'we decided to fall through' is not a licence
    # to stop saying why.
    assert "our anchors, not the document" in problem, problem
    assert "64" not in problem, "the problem note must not quote the document"
