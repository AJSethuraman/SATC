"""Which pages of a document are the form -- and what it cost when nobody asked.

EVERY TEST HERE IS A REAL FAILURE, measured on 31 August 2026 against fourteen
real blank IRS forms, then reconstructed synthetically so it is provable without
them. The real PDFs are not in the repository (they are large, and the corpus is
fetched); a check that can only run on the firm's laptop is not a check.

The three failures had one cause: nothing in the package ever answered "which
page is the form?", so every reader picked one of two wrong defaults -- page 1,
or all of them.
"""

from __future__ import annotations

import pytest

from satc.ingest.classify import MIN_SIGNALS, load_classifier
from satc.ingest.pages import form_pages, is_guidance
from satc.ingest.readers.text_anchor import TextAnchorReader

# The real notice, verbatim from page 1 of `f1099g.pdf`, `f1099msc.pdf`,
# `f1099r.pdf` and `f1098t.pdf` -- byte-identical across all four, which is why
# all four came back "1099-NEC".
NOTICE = (
    "Attention: Which Revision To Use for Which Year. We issue information "
    "returns up to a year in advance of when issuers will first file them. For "
    "all forms, use the December 2026 revision of Form 1099-NEC to report "
    "nonemployee compensation paid in 2026."
)

# The real instruction sentence, verbatim from page 7 of `fw2.pdf`.
INSTRUCTIONS = (
    "Instructions for Employee (See also Notice to Employee on the back of Copy "
    "B.) Box 5. You may be required to report this amount on Form 8959. Enter "
    "this amount on the wages line of your tax return. Medicare wages and tips "
    "above $200,000 are subject to the 0.9% Additional Medicare Tax."
)

# A real W-2 form page: the labels are printed, the boxes are empty.
BLANK_W2_PAGE = (
    "22222 VOID a Employee's social security number OMB No. 1545-0029 "
    "b Employer identification number (EIN) c Employer's name, address, and ZIP "
    "code 1 Wages, tips, other compensation 2 Federal income tax withheld "
    "3 Social security wages 4 Social security tax withheld "
    "5 Medicare wages and tips 6 Medicare tax withheld "
    "Form W-2 Wage and Tax Statement 2026 Department of the Treasury"
)


def _page(tmp_path, name, *texts):
    """A PDF with one page per text. Real pages, so this exercises the real read."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    for body in texts:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(36, 36, 560, 740), body, fontsize=9)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return path


# -- the predicate ------------------------------------------------------------

def test_the_irs_notice_is_recognised_as_guidance():
    assert is_guidance(NOTICE)


def test_an_instructions_page_is_recognised_as_guidance():
    assert is_guidance(INSTRUCTIONS)


def test_a_form_page_is_never_guidance():
    """The expensive mistake is dropping a real page, so the rule is anchored at
    the START of the page. A form that mentions its own instructions keeps."""
    assert not is_guidance(BLANK_W2_PAGE)
    assert not is_guidance(
        "Form W-2 Wage and Tax Statement. See the instructions for employee on "
        "the back of Copy B before you file."
    )


def test_a_document_that_is_all_guidance_keeps_its_pages(tmp_path):
    """Returning nothing would turn a readable document into an apparent scan
    and send it down the OCR ladder for no reason."""
    path = _page(tmp_path, "notice.pdf", NOTICE)
    assert len(form_pages(path)) == 1


def test_the_form_pages_are_numbered_as_they_are_in_the_file(tmp_path):
    """A caller that goes back to rasterise must ask for the page the form is
    actually on, not the page it is in some filtered list."""
    path = _page(tmp_path, "w2.pdf", NOTICE, BLANK_W2_PAGE, INSTRUCTIONS,
                 BLANK_W2_PAGE)
    assert [n for n, _ in form_pages(path)] == [2, 4]


# -- failure 1: the notice page decided what the document was -----------------

def test_a_1099_g_is_not_classified_off_the_notice_that_precedes_it(tmp_path):
    """THE MEASURED BUG. Page 1 scored 1099-NEC 28; page 2 scored 1099-G 37 and
    was never read. A 1098-T, a 1099-G, a 1099-MISC and a 1099-R all came back
    1099-NEC at HIGH confidence, which files each of them against a client's
    open 1099-NEC request and closes it."""
    body = ("Form 1099-G (Rev. December 2026) Certain Government Payments "
            "Copy B For Recipient. Box 1 Unemployment compensation. "
            "Box 2 State or local income tax refunds, credits, or offsets.")
    path = _page(tmp_path, "IMG_4471.pdf", NOTICE, body)
    clf = load_classifier()
    clf.ocr_text_provider = clf.ocr_page_text_provider = None
    got = clf.classify_path(path)
    assert got.label == "1099-G", got.label
    assert got.method == "text", "the filename must not be what saved this"


# -- failure 2: a blank form read as $200,000 ---------------------------------

def test_a_blank_w2_yields_no_money_at_all(tmp_path):
    """THE WORST ONE. On the real eleven-page blank W-2 this returned
    ``Box 1 - Wages = 200000`` and ``Box 5 - Medicare wages = 200000``, both
    HIGH, both auto-confirmed into the workpaper by `auto_confirm_high`. The
    figure is a THRESHOLD IN A SENTENCE on the instructions page, 30 characters
    from the anchor `medicare wages and tips`.

    The fix is not that a blank box now beats a distant number -- it is that the
    instructions page is not the form, so nothing there is read at all.
    """
    from satc.config import load_extraction_map

    path = _page(tmp_path, "blank_w2.pdf", NOTICE, BLANK_W2_PAGE, INSTRUCTIONS)
    result = TextAnchorReader(load_extraction_map("w2")).read(str(path))

    # NOTHING FROM A BLANK FORM MAY AUTO-CONFIRM. This is the assertion that
    # matches the harm: `auto_confirm_high` writes HIGH fields into the
    # workpaper with nobody looking, and $200,000 of wages arrived that way.
    high = [label for label, conf in result.confidence_map().items()
            if conf == "HIGH"]
    assert high == [], f"a BLANK form produced auto-confirming fields: {high}"

    # AND NO FIGURE AT ALL in a money box. Stated separately because the two
    # could come apart: a money field staged LOW is still a number a preparer
    # has to disbelieve, and on a blank form there is nothing to disbelieve.
    amounts = {label: value for label, value in result.labeled_fields.items()
               if value.replace(",", "").replace(".", "").isdigit()}
    assert amounts == {}, f"a BLANK form produced figures: {amounts}"

    # WHAT IS STILL LEFT, named rather than hidden: the reader is heuristic and
    # a free-text box can pick up the printed label beside it. Those stage LOW,
    # a preparer sees them, and no number reaches the workbook. Left as it is
    # because tightening it further risks losing real values from real forms --
    # but recorded here so the next person knows it was seen, not missed.


# -- failure 3: one form split into several documents -------------------------

def test_an_instruction_page_does_not_split_a_form_into_two_documents(tmp_path):
    """The real eleven-page W-2 became SIX "documents", one of them a
    HIGH-confidence `Prior-year 1040` cut from a W-2 instruction page. This is
    the path production runs: sort, intake and collect all split before they
    classify."""
    from satc.ingest.split import plan_split

    path = _page(tmp_path, "w2.pdf", NOTICE, BLANK_W2_PAGE, INSTRUCTIONS,
                 BLANK_W2_PAGE)
    clf = load_classifier()
    clf.ocr_text_provider = clf.ocr_page_text_provider = None
    segments = plan_split(path, clf)
    assert len(segments) == 1, [s.classification.label for s in segments]
    assert segments[0].classification.label == "W-2"
    assert (segments[0].start, segments[0].end) == (0, 3), "no page was dropped"


# -- the partial answer that a page rule must not reintroduce -----------------

def test_a_consolidated_1099_with_one_form_PER_PAGE_reports_several_forms(tmp_path):
    """THE MONEY BUG A BEST-PAGE RULE WOULD HAVE CAUSED, and the reason each
    page is judged on its own and the VERDICTS unioned, rather than the pages
    scored against each other. Taking the highest-scoring page answers a
    consolidated statement with one form, `reconcile_received` closes that
    request, and the others are never asked for again."""
    div = ("Form 1099-DIV Dividends and Distributions. Box 1a Total ordinary "
           "dividends. Box 1b Qualified dividends. Box 2a Total capital gain "
           "distributions.")
    interest = ("Form 1099-INT Interest Income. Box 1 Interest income. "
                "Box 3 Interest on U.S. Savings Bonds and Treasury obligations. "
                "Box 4 Federal income tax withheld.")
    path = _page(tmp_path, "consolidated.pdf", div, interest)
    clf = load_classifier()
    clf.ocr_text_provider = clf.ocr_page_text_provider = None
    got = clf.classify_path(path)
    assert got.multi, got.label
    assert set(got.forms) == {"1099-DIV", "1099-INT"}, got.forms


# -- one mention is not a document --------------------------------------------

def test_a_single_mention_of_a_form_does_not_classify_a_document_as_it():
    """Schedule C says "Form W-2", "Form 1065" and "Form 1040" once each, and
    came back "Several forms: W-2, Schedule K-1 (1065), Prior-year 1040" -- any
    of which would close a client request with a Schedule C.

    Measured over the fourteen real blanks: every real form matched at least
    two distinct keywords for its own type; the false positive matched one.
    """
    clf = load_classifier()
    clf.ocr_text_provider = clf.ocr_page_text_provider = None
    assert clf.classify_text(
        "Profit or Loss From Business. If you checked the box, see Form W-2, "
        "Form 1065 and Form 1040 for where to report this amount."
    ) is None


def test_min_signals_is_the_rule_being_relied_on():
    """Names the constant, so raising it back to 1 fails here rather than
    quietly reopening the Schedule C hole somewhere else."""
    assert MIN_SIGNALS == 2


# -- the model rungs, which are shown one page and asked to judge --------------

def test_the_page_a_model_is_shown_is_the_form_not_the_notice(tmp_path):
    """Both model readers defaulted to `page=1` and were never passed anything
    else, so on a real IRS document the model was handed the notice -- a page
    that is ABOUT 1099-NEC -- and asked which form it is. These are the last
    rungs: nothing cheaper is left to disagree with them."""
    from satc.ingest.pages import first_form_page

    assert first_form_page(_page(tmp_path, "a.pdf", NOTICE, BLANK_W2_PAGE)) == 2
    assert first_form_page(_page(tmp_path, "b.pdf", BLANK_W2_PAGE)) == 1


def test_a_scan_with_no_text_falls_back_to_page_one_rather_than_guessing(tmp_path):
    """The honest limit. With no text layer nothing can tell a notice from a
    form, so the answer is what it always was -- said here so that a later
    reader knows it was decided rather than overlooked."""
    from satc.ingest.pages import first_form_page

    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    doc.new_page(); doc.new_page()
    path = tmp_path / "scan.pdf"
    doc.save(str(path)); doc.close()
    assert first_form_page(path) == 1


def test_the_model_readers_ask_for_that_page(tmp_path, monkeypatch):
    """Not just that the helper is right -- that the readers call it. The
    default was a literal 1 in two constructors, so this is the assertion that
    would have failed before the fix."""
    from satc.ingest.readers import ollama as ollama_mod
    from satc.ingest.readers import vision as vision_mod

    path = _page(tmp_path, "w2.pdf", NOTICE, BLANK_W2_PAGE)
    asked: list[int] = []

    def spy(pdf, page):
        asked.append(page)
        return b"\x89PNG", "image/png"

    monkeypatch.setattr(vision_mod, "_rasterize_pdf", spy)
    monkeypatch.setattr(ollama_mod, "_rasterize_pdf", spy)
    vision_mod.VisionDocumentReader({"fields": []})._image_bytes(str(path))
    ollama_mod.OllamaVisionReader({"fields": []})._image_b64(str(path))
    assert asked == [2, 2], asked
