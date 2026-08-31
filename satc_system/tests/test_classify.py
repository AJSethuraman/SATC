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


# A real engagement letter, in the firm's own words -- the same sentences that
# appear in all four templates under `satc-handoff/04-TEMPLATES/`.
#
# THE FIXTURE USED TO BE THE TITLE AND NOTHING ELSE: "SATC Engagement Letter --
# Maplewood 2024". It passed, and it was measuring nothing. Those five words are
# also exactly what a REFERENCE to an engagement letter looks like in some other
# document, and the classifier could not tell the two apart -- so a delivery
# letter mentioning the engagement letter classified as one. Worse, the real
# letters mention `Form 1040` and `Schedule K-1` in passing, and the classifier
# reported "Several forms: Engagement letter, Schedule K-1" for our own document.
# Neither could be seen from a one-line fixture. This is the firm's own point:
# "the synthetic tests weren't doing it."
ENGAGEMENT_LETTER = (
    "SATC Engagement Letter — Maplewood 2024. This letter outlines what each of "
    "us is responsible for, and what this engagement is and is not. Work outside "
    "the scope described in this letter is billed separately. We keep copies of "
    "your records and our work papers for seven years. We will not disclose your "
    "information to anyone without your written consent, except where the law "
    "requires it. Your 2024 Form 1040 will be prepared from what you give us."
)


def test_flat_document_classified_by_text_layer(tmp_path):
    # No form fields, but the printed words say what it is. Read for free, no OCR.
    path = tmp_path / "random_name.pdf"
    write_plain_pdf(path, ENGAGEMENT_LETTER)
    c = load_classifier(has_key=False).classify_path(path)

    assert c.label == "Engagement letter"
    assert c.method == "text"
    assert not c.extractable          # filed, not extracted


def test_a_letter_that_mentions_a_form_is_not_that_form(tmp_path):
    """The engagement letter says "Form 1040" once, in passing. Reporting that
    as a 1040 -- or as "Several forms: Engagement letter, Prior-year 1040" --
    files our own document against a client's open return request."""
    path = tmp_path / "letter.pdf"
    write_plain_pdf(path, ENGAGEMENT_LETTER)
    c = load_classifier(has_key=False).classify_path(path)
    assert not c.multi, c.label
    assert c.label == "Engagement letter"


def test_a_mere_reference_to_an_engagement_letter_is_not_one():
    """The old fixture, kept as the counter-example it always was."""
    clf = load_classifier(has_key=False)
    clf.ocr_text_provider = clf.ocr_page_text_provider = None
    assert clf.classify_text("SATC Engagement Letter — Maplewood 2024") is None


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


def test_a_statement_that_is_two_forms_is_reported_as_two_forms():
    """Rewritten 30 Aug 2026. Its own comment always asked for the right thing.

    This used to assert MEDIUM confidence on a single label and was written
    "don't guess" -- but MEDIUM on one label IS a guess, and downstream it was a
    costly one: matching accepted that label against a core-income bundle and
    reconcile closed the request, so the other form was never asked for again.
    The classifier now distinguishes "unsure which one form this is" from "sure
    it is more than one". Left here rather than deleted because this text is the
    canonical two-form case and the sibling of every rule in test_multiform.py.
    """
    text = "1099-INT Interest Income   1099-DIV Dividends and Distributions"
    c = _clf().classify_text(text)
    assert c.multi, c
    assert set(c.forms) == {"1099-INT", "1099-DIV"}, c.forms
    assert c.key is None


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
