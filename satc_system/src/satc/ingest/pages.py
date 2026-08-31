"""Which pages of a document are the FORM, and which are the IRS talking about it.

WHY THIS MODULE EXISTS. Every reader in this package used to pick one of two
wrong answers to that question and never state it: *page 1*, or *all of them*.
Measured on 31 August 2026 against fourteen real blank IRS forms, that cost:

  * a 1098-T, a 1099-G, a 1099-MISC and a 1099-R all classified **1099-NEC at
    HIGH confidence**, because page 1 of an IRS blank is a generic notice whose
    worked example is 1099-NEC. The real form page scored the right answer and
    was never read.
  * a **blank** W-2 read as ``Box 1 - Wages = $200,000`` at HIGH confidence --
    lifted from page 7, *"Instructions for Employee ... Additional Medicare Tax
    on any of those Medicare wages and tips above $200,000"* -- which
    ``auto_confirm_high`` then writes into the workpaper with nobody looking.
  * one eleven-page W-2 split into six separate "documents", one of them a
    HIGH-confidence ``Prior-year 1040`` made out of a W-2 instruction page.

Those are three bugs with one cause, so there is one answer here and every rung
asks it. The rule is not "skip page 1" -- ``f1040.pdf`` and ``f1065sk1.pdf``
have no such page and must lose nothing.

HOW A GUIDANCE PAGE IS RECOGNISED, and why it is safe. A page where the IRS is
*explaining* the form OPENS by saying so: "Attention:", "Instructions for
Recipient", "Future developments.", "Employers, Please Note--". The match is
anchored at the start of the page, not anywhere in it, because a form page may
well mention its own instructions and must never be dropped for it. Dropping a
real form page is the expensive mistake; keeping a guidance page is the cheap
one, so the rule is deliberately narrow.

MEASURED, on all fourteen blanks (31 Aug 2026). The pages this flags on
``fw2.pdf`` are 1, 5, 7, 9 and 11 -- and the pages carrying AcroForm widgets are
2, 3, 4, 6, 8 and 10. Two independent signals, the text opener and the fillable
fields, partition the document identically and neither was used to derive the
other. On the five forms with no guidance pages, nothing is dropped.
"""

from __future__ import annotations

import re
from pathlib import Path

# THE OPENERS, in the IRS's own words. Anchored at the start of a page, matched
# on whitespace-collapsed lowercase text. Extend this list rather than widening
# a pattern: a substring match anywhere in the page would drop real forms.
GUIDANCE_OPENERS: tuple[str, ...] = (
    "attention:",                 # the "Which Revision To Use" / "Copy A ... not for filing" notice
    "instructions for ",          # ... Recipient / Employee / Student / Payer / Borrower
    "future developments",
    "employers, please note",
    "general instructions",
    "notice to employee",
    "did you know",
)

# How many pages of a document are worth reading to decide what it is. A form
# states its identity on its own face; a 200-page brokerage statement does not
# become a different form on page 60. This is a cost bound, not a rule about
# documents -- `split.py` still walks every page, because there the page count
# IS the question.
CLASSIFY_PAGE_LIMIT = 12

# The same bound for the OCR rung, and much tighter, because rasterising a page
# at 300 dpi and running Tesseract over it costs about a thousand times what
# reading a text layer costs. MEASURED: reading a page of text is ~0.03s;
# OCR'ing one is seconds. Four pages is enough for every real IRS document in
# the corpus -- the notice is page 1 and the form begins on page 2 -- and a
# scan that needs more than four pages to say what it is will come back
# Unclassified, which a preparer sees, rather than expensively wrong.
OCR_PAGE_LIMIT = 4


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def is_guidance(text: str) -> bool:
    """Is this page the IRS explaining the form, rather than the form?"""
    flat = _flat(text)
    return any(flat.startswith(opener) for opener in GUIDANCE_OPENERS)


def page_texts(source: str | Path) -> list[str]:
    """Every page's text layer, in order. ``[]`` when the file cannot be read."""
    try:
        from pypdf import PdfReader

        return [(page.extract_text() or "") for page in PdfReader(str(source)).pages]
    except Exception:      # noqa: BLE001 - an unreadable file is not a crash here
        return []


def form_pages(source: str | Path) -> list[tuple[int, str]]:
    """The pages that are the document itself, as ``(page number, text)``.

    Page numbers are 1-based and are the ORIGINAL numbers, so a caller that
    goes back to the file -- to rasterise for OCR, say -- asks for the page the
    form is actually on.

    A document that is ENTIRELY guidance keeps all its pages. That is on
    purpose: the alternative is returning nothing and reporting "no text",
    which would turn a readable document into an apparent scan and send it
    down the OCR ladder for no reason.
    """
    pages = [(i, t) for i, t in enumerate(page_texts(source), 1)]
    form = [(i, t) for i, t in pages if not is_guidance(t)]
    return form or pages


def form_text(source: str | Path, *, limit: int = CLASSIFY_PAGE_LIMIT) -> str:
    """The form's own text, guidance pages dropped, capped at ``limit`` pages."""
    return "\n".join(t for _, t in form_pages(source)[:limit])


def first_form_page(source: str | Path) -> int:
    """The page a model should be shown. 1 when we cannot tell.

    THE MODEL RUNGS DEFAULTED TO PAGE 1 and were never passed anything else, so
    on an eleven-page W-2 the model was handed the SSA notice and asked for Box 1
    wages; on a scanned 1099-R it was handed a page that is *about* 1099-NEC and
    asked which form it is. These are the last rungs -- nothing cheaper is left
    to disagree with them.

    A true scan has no text layer, so nothing here can tell a notice from a form
    and the answer is page 1, same as before. That is the honest limit: this
    fixes the documents we can read and does not pretend to fix the rest.
    """
    pages = page_texts(source)
    if not pages or not any(t.strip() for t in pages):
        return 1
    for number, text in enumerate(pages, 1):
        if not is_guidance(text):
            return number
    return 1
