"""A file whose bytes are not here must refuse, not classify as Unclassified.

OneDrive's Files On-Demand leaves PLACEHOLDERS: entries that appear in the folder
listing, report a size in Explorer, and have no bytes on the disk. Reading one
either blocks on a slow download or yields nothing.

Measured 30 August 2026, and predicted before that in the collection design: a
zero-byte PDF classified as **Unclassified**, silently, and was filed into the
Unclassified folder. A document that arrived, was processed, and disappeared
into a folder nobody reads.

THE DISTINCTION. "We looked at this document and could not identify it" and "we
never saw this document's contents" are different facts with different remedies
-- the first wants a new keyword, the second wants you to right-click and choose
Always keep on this device. In a folder listing they are the same grey word.
Refusing loudly and shrugging quietly must not look identical.

This is the third instance of the same shape in this package, which is why it is
worth its own module: the reader ladder conflated "no text to read" with "we
could not read the text", the classifier conflated "several forms" with "unsure
which form", and here a file we never read is reported as a file we read and did
not recognise.
"""

from __future__ import annotations

import pymupdf
import pytest

from satc.ingest.classify import load_classifier, NOT_DOWNLOADED


def _real_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Form 1099-INT  Interest Income", fontsize=11)
    page.insert_text((72, 92), "1 Interest income  412.55", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


def test_a_zero_byte_file_refuses_rather_than_classifying(tmp_path):
    p = tmp_path / "placeholder.pdf"
    p.write_bytes(b"")
    got = load_classifier().classify_path(p)
    assert got.method == "not downloaded", got
    assert got.label == NOT_DOWNLOADED.label


def test_the_refusal_is_distinguishable_from_unclassified(tmp_path):
    """The whole point: these must not be the same word in a folder listing."""
    from satc.ingest.classify import UNCLASSIFIED

    p = tmp_path / "placeholder.pdf"
    p.write_bytes(b"")
    got = load_classifier().classify_path(p)
    assert got.label != UNCLASSIFIED.label
    assert got.method != UNCLASSIFIED.method


def test_the_refusal_says_what_to_do_about_it(tmp_path):
    p = tmp_path / "placeholder.pdf"
    p.write_bytes(b"")
    got = load_classifier().classify_path(p)
    assert "download" in got.evidence.lower(), got.evidence


def test_a_refused_file_is_never_extracted(tmp_path):
    p = tmp_path / "placeholder.pdf"
    p.write_bytes(b"")
    got = load_classifier().classify_path(p)
    assert not got.extractable
    assert not got.classified, \
        "a file we never read must not count as classified -- reconcile keys off this"


def test_a_real_file_is_untouched(tmp_path):
    got = load_classifier().classify_path(_real_pdf(tmp_path / "real.pdf"))
    assert got.label == "1099-INT"
    assert got.method != "not downloaded"


def test_a_missing_file_refuses_too(tmp_path):
    """A file that vanished mid-sync is the same situation as one never pulled."""
    got = load_classifier().classify_path(tmp_path / "gone.pdf")
    assert got.method == "not downloaded"


def test_a_tiny_but_real_file_is_not_mistaken_for_a_placeholder(tmp_path):
    """Only ZERO bytes counts. A small real PDF must go down the normal path."""
    p = _real_pdf(tmp_path / "small.pdf")
    assert p.stat().st_size > 0
    got = load_classifier().classify_path(p)
    assert got.method != "not downloaded"


def test_a_refused_file_is_not_filed_among_the_unrecognised(tmp_path):
    """Saying "Not downloaded" and then filing it in Unclassified anyway would
    put the refusal back where nobody sees it. Found by running the sorter, not
    by reading the code."""
    from satc.ingest.sort import sort_folder

    src = tmp_path / "in"
    src.mkdir()
    (src / "placeholder.pdf").write_bytes(b"")
    _real_pdf(src / "real.pdf")
    (src / "junk.pdf").write_bytes(b"%PDF-1.4\nnot a real document\n")

    plan = sort_folder(src, dest=tmp_path / "out")
    where = {i.original_name: i.new_relpath.split("/")[0] for i in plan.items}
    assert where["placeholder.pdf"] == "Not downloaded", where
    assert where["placeholder.pdf"] != where.get("junk.pdf"), \
        "a file we never read is in the same folder as one we read and did not know"


def test_the_sort_tally_does_not_count_a_file_it_never_read(tmp_path):
    """SortPlan.classified stated the same rule as Classification.classified and
    was missed when that one was fixed -- it counted a placeholder as identified."""
    from satc.ingest.sort import sort_folder

    src = tmp_path / "in"
    src.mkdir()
    (src / "placeholder.pdf").write_bytes(b"")
    _real_pdf(src / "real.pdf")
    plan = sort_folder(src, dest=tmp_path / "out")
    assert plan.classified == 1, "the placeholder was counted as identified"
