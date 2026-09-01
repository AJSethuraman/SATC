"""Content-based classification: identify documents by reading them, not by name."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")

from satc.fixtures.sample_docs import (  # noqa: E402
    write_plain_pdf,
    write_sample_1099int,
    write_sample_w2,
)
from satc.ingest import load_classifier  # noqa: E402
from satc.ingest.classify import _normalize_text  # noqa: E402


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


# -- our own outbound documents, coming back in -------------------------------
#
# A client who is sent a packet returns the packet. Everything the firm posts
# out is a candidate for intake, so every one of them is a document the
# classifier has to be right about.

# THE FIRM'S OWN DISENGAGEMENT LETTER, rendered from the example values its own
# FIELDS spec documents -- `ScopeEnded` = "the preparation of your 2026
# individual income tax returns", `Item.Work` = "2026 Federal Form 1040". This
# is not a contrived fixture: section 02 of the letter exists to LIST THE WORK
# THAT WAS DONE, so a disengagement letter for a 1040 client names the 1040
# twice over, in the two phrasings the classifier scores highest for a return.
#
# NOTE WHAT IS ABSENT. The word "disengagement" appears nowhere below, because
# it appears nowhere in the letter a client receives -- the subject line is
# "Ending our engagement" and the only "disengagement" in the template is its
# on-screen title, which `@media print` hides. See
# test_the_word_disengagement_never_reaches_the_client.
DISENGAGEMENT_LETTER = (
    "Sethuraman Accounting, Tax & Consulting. ENGAGEMENT REF 2027-0114. "
    "Ending our engagement — 2026 tax year. "
    "This letter confirms that our engagement ends on June 30, 2027. It sets out "
    "what we completed, what we did not, what you now have, and what you need to "
    "arrange. 01 What this ends. As the Ending this engagement section of your "
    "engagement letter provides, either of us may end it in writing at any time. "
    "This is that writing. It covers the preparation of your 2026 individual "
    "income tax returns, and it takes effect on June 30, 2027. "
    "02 What we completed, and what we did not. 2026 Federal Form 1040 — Prepared "
    "and e-filed on April 9, 2027; accepted April 9. Anything not marked complete "
    "above is not filed, not lodged, and not being worked on by us. "
    "03 Deadlines you now own. Engage someone promptly. A new preparer needs time "
    "to read a file before a deadline, not after it. "
    "04 Your records. Your original records are returned with this letter, or are "
    "available for collection until August 31, 2027. "
    "06 What we are not saying. This letter ends an engagement. Nothing here "
    "changes what was already filed. It is not a new engagement."
)


def test_our_own_disengagement_letter_is_not_the_return_it_lists():
    """It came back "Prior-year 1040", HIGH -- our own outbound document filed
    against the client's open prior-year request.

    Measured 1 Sep 2026: "individual income tax return" (9) + "form 1040" (8)
    = 17, from section 02, which lists the work that was done. That verdict
    carries an extraction key, so `may_close_a_request` was True and the client's
    request for the actual return closed. Nobody asks for it again, and the
    return the client never sent is the one the letter says we stopped work on.
    """
    c = _clf().classify_text(DISENGAGEMENT_LETTER)
    assert c is not None, "the letter must not fall through to Unclassified"
    assert c.label == "Disengagement letter", c
    assert not c.multi, c.label


def test_our_own_letter_does_not_close_the_clients_prior_year_request(tmp_path):
    """The money assertion, driven through the seam that actually loses the
    document rather than through the classifier alone.

    `may_close_a_request` is True for any confident content verdict -- the
    engagement letter's included -- so the protection was never "this verdict
    cannot close anything". It is that the verdict no longer says "1040", so
    `reconcile_received` finds no prior-year request it matches. Asserted here
    against a real store because a label assertion would have passed for a fix
    that named the type correctly and still matched the return.
    """
    from satc.intake.service import reconcile_received
    from satc.models.mart import DocumentRecord
    from satc.persistence.store import SATCStore

    store = SATCStore(str(tmp_path / "data"))
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="DOC-1", client_id="C1", tax_year=2026,
        doc_type="Prior-year 1040", status="Requested",
        note="Upload your prior-year Form 1040 as filed"))
    store.save_mart(mart)

    c = _clf().classify_text(DISENGAGEMENT_LETTER)
    assert c.may_close_a_request, "a confident content verdict; the guard is the LABEL"
    matched = reconcile_received(store, client_id="C1", doc_type=c.label,
                                 doc_year=c.tax_year)

    assert matched is None, f"our own letter was filed against the request as {c.label}"
    assert next(d.status for d in store.load_mart().documents) == "Requested"
    assert not c.extractable, "nothing may try to read 1040 figures off a letter"


def test_the_disengagement_letter_is_not_also_reported_as_a_1040():
    """Beating 17 is not enough -- a runner-up scoring MULTI_SHARE of the winner
    is reported as a SECOND FORM, so a mid-weight fix answers "Several forms:
    Disengagement letter, Prior-year 1040" about our own letter.

    The weights are sized so the return the letter merely LISTS stays well under
    that share. This pins the margin, not just the winner.
    """
    from satc.ingest.classify import MULTI_SHARE

    clf = _clf()
    norm = _normalize_text(DISENGAGEMENT_LETTER)
    scores = {dt.label: sum(w for p, w in dt.keywords if p and p in norm)
              for dt in clf.doc_types}
    best, runner = scores["Disengagement letter"], scores["Prior-year 1040"]
    assert runner > 0, "fixture no longer names the 1040 -- it must, that is the bug"
    assert runner < best * MULTI_SHARE, (
        f"Prior-year 1040 scores {runner} against {best}; at or above "
        f"{best * MULTI_SHARE:.1f} the letter is reported as several forms")


def test_the_word_disengagement_never_reaches_the_client():
    """The obvious keyword would have read as load-bearing and never once fired.

    Measured 1 Sep 2026: "disengagement" occurs in the template only in its
    on-screen title and spec table, both hidden by `@media print`. The letter a
    client is sent says "Ending our engagement". A
    `["disengagement letter", 10]` entry would have looked like the primary
    signal to the next reader while contributing nothing, which is the exact
    shape of a check that cannot fire.
    """
    clf = _clf()
    dt = next(d for d in clf.doc_types if d.label == "Disengagement letter")
    assert "disengagement" not in _normalize_text(DISENGAGEMENT_LETTER)
    assert not [p for p, _ in dt.keywords if "disengagement" in p], (
        "a keyword that cannot fire on the rendered letter")
    # ...and the type still wins on the firm's own sentences alone.
    assert clf.classify_text(DISENGAGEMENT_LETTER).label == "Disengagement letter"


def test_a_disengagement_letter_is_not_an_engagement_letter_by_its_name():
    """"disengagement" CONTAINS "engagement", and the filename rung returns the
    first type whose hint matches -- so `SATC Disengagement Letter.pdf` came
    back "Engagement letter". Specific hints must be ordered before generic
    ones; this is the pair that proves it.
    """
    clf = _clf()
    assert clf._by_filename("SATC Disengagement Letter.pdf").label == "Disengagement letter"
    # The generic hint still works for the document it was written for.
    assert clf._by_filename("SATC Engagement Letter 2027.pdf").label == "Engagement letter"


def test_an_engagement_letter_is_still_an_engagement_letter():
    """The sibling document, kept beside the fix. Adding a near-identical type
    next to an existing one is how the existing one starts losing."""
    c = _clf().classify_text(ENGAGEMENT_LETTER)
    assert c.label == "Engagement letter", c
    assert not c.multi, c.label


# -- the measurement the keywords were chosen by, pinned ----------------------

_TEMPLATES = Path(__file__).resolve().parents[2] / "satc-handoff" / "04-TEMPLATES"


def _template_body(path: Path) -> str:
    """The document itself -- not the on-screen spec table below it.

    Every template wraps the printable page in `div.letter` (or `div.doc` for
    the two that are not letters). Everything after it is the merge-field
    documentation, which `@media print` hides and no client ever sees. Merge
    fields and `[[...]]` directives are removed because a rendered document has
    values there, not syntax.
    """
    raw = path.read_text(errors="ignore")
    for cls in ("letter", "doc"):
        start = raw.find(f'<div class="{cls}">')
        if start < 0:
            continue
        depth = 0
        for m in re.finditer(r"<div\b|</div>", raw[start:]):
            depth += 1 if m.group(0) != "</div>" else -1
            if depth == 0:
                html = raw[start:start + m.end()]
                break
        else:
            continue
        html = re.sub(r"&lt;&lt;.*?&gt;&gt;", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\[\[.*?\]\]", " ", text, flags=re.S)
    raise AssertionError(f"no printable wrapper in {path.name}")


def _template_all_text(path: Path) -> str:
    """The whole page -- the printable document AND the spec table beneath it.

    The wider of the two nets, and the one the keywords were actually chosen
    against. The spec table is `@media print` hidden, so a client never reads
    it, but it is real text in a real file in this repository and a phrase that
    collides there is a phrase chosen by luck. It is also where the collision
    that got a candidate dropped actually lived.
    """
    raw = re.sub(r"&lt;&lt;.*?&gt;&gt;", " ", path.read_text(errors="ignore"), flags=re.S)
    return re.sub(r"\[\[.*?\]\]", " ", re.sub(r"<[^>]+>", " ", raw), flags=re.S)


@pytest.mark.skipif(not _TEMPLATES.is_dir(), reason="satc-handoff not checked out")
@pytest.mark.parametrize("extract,where", [(_template_body, "the printable document"),
                                           (_template_all_text, "the page, spec table included")])
def test_no_disengagement_keyword_appears_in_another_template(extract, where):
    """The keywords are only worth their weights if they are the firm's own
    sentences AND nobody else's. Every one was checked against the other eleven
    templates on 1 Sep 2026, over both nets below; a ninth candidate, "what we
    are not saying", was dropped for colliding with the bookkeeping letter --
    in its spec table, which the narrow net alone would have called clean.
    Nothing re-checks any of this by hand when a template is next edited.
    """
    clf = _clf()
    dt = next(d for d in clf.doc_types if d.label == "Disengagement letter")
    others = {p.name: _normalize_text(extract(p))
              for p in sorted(_TEMPLATES.glob("SATC *.html"))
              if "Disengagement" not in p.name}
    assert len(others) == 11, f"expected eleven sibling templates, found {len(others)}"
    for phrase, _ in dt.keywords:
        hits = [n for n, body in others.items() if phrase in body]
        assert not hits, f"{phrase!r} also appears in {hits} ({where})"


@pytest.mark.skipif(not _TEMPLATES.is_dir(), reason="satc-handoff not checked out")
def test_every_keyword_is_in_the_firms_actual_letter():
    """The other half of the same guard: a phrase unique to nothing is no use.

    Both halves matter because they fail in opposite directions -- a phrase that
    drifts out of the template silently costs the type its score, and a phrase
    that drifts INTO a sibling silently mislabels that sibling.
    """
    clf = _clf()
    dt = next(d for d in clf.doc_types if d.label == "Disengagement letter")
    body = _normalize_text(_template_body(_TEMPLATES / "SATC Disengagement Letter.html"))
    missing = [p for p, _ in dt.keywords if p not in body]
    assert not missing, f"no longer in the firm's letter: {missing}"


@pytest.mark.skipif(not _TEMPLATES.is_dir(), reason="satc-handoff not checked out")
@pytest.mark.parametrize("stem,expected", [
    ("SATC Disengagement Letter", "Disengagement letter"),
    ("SATC Engagement Letter - Bookkeeping", "Engagement letter"),
    ("SATC Engagement Letter - Business Return", "Engagement letter"),
    ("SATC Engagement Letter - C Corporation", "Engagement letter"),
    ("SATC Engagement Letter - Tax Preparation", "Engagement letter"),
    ("SATC Extension Notice", None),
    ("SATC Fee Estimate", None),
    ("SATC Invoice", None),
    ("SATC Onboarding Letter", None),
    ("SATC Organizer Cover Letter", None),
    ("SATC Records Release Authorization", None),
    ("SATC Tax Return Delivery Letter", None),
])
def test_every_outbound_template_reads_as_itself(stem, expected):
    """All twelve, opened and classified -- not the one that was being fixed.

    `None` means the classifier declines to name it, which is the honest answer
    for a document that has no type here yet. The failure this guards is a new
    type quietly swallowing a sibling: six of these are letters too, and the
    phrases that identify one letter are the kind that turn up in another.
    """
    got = _clf().classify_text(_template_body(_TEMPLATES / f"{stem}.html"))
    assert (got.label if got else None) == expected, got
