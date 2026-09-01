"""Collecting what a client uploaded — the two links of pipe that were missing.

Everything after this already worked: split, classify, file by client and year,
match to the request, mark Received, stage figures behind the confirmation gate,
draft the chase email. What did not exist was getting the bytes from the firm's
SharePoint upload folder onto the machine, and knowing when they landed.

THE SOURCE IS BEHIND A SEAM on purpose. Today it is a folder OneDrive syncs --
no app registration, no stored secret, and `graph.microsoft.com` is blocked from
the build environment so an API adapter could be written here but never run. The
seam means that stays a second file rather than a rewrite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from satc.collect import Drop, SyncedFolder, collect


def _form(path: Path, lines: list[str]) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 16
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


W2 = ["Form W-2  Wage and Tax Statement", "2026",
      "Employer: Buckeye Manufacturing LLC",
      "1 Wages, tips, other compensation  64,500.00"]
INT = ["Form 1099-INT", "Interest Income", "PAYER'S name: Heartland Bank",
       "1 Interest income   412.55"]


@pytest.fixture
def drop_root(tmp_path):
    root = tmp_path / "Client Uploads"
    _form(root / "2026-0001 — Maplewood" / "IMG_4471.pdf", W2)
    _form(root / "2026-0001 — Maplewood" / "scan0012.pdf", INT)
    _form(root / "2026-0002 — Riverbend" / "w2.pdf", W2)
    (root / "2026-0001 — Maplewood" / "placeholder.pdf").write_bytes(b"")
    return root


# -- reading the drop folders -------------------------------------------------

def test_a_synced_folder_is_just_a_folder(drop_root):
    """No API, no credential. The whole integration is this path."""
    drops = SyncedFolder(drop_root).drops()
    assert {d.ref for d in drops} == {"2026-0001", "2026-0002"}


def test_the_engagement_ref_comes_off_the_folder_name(drop_root):
    """Why the naming convention earns its place: an arriving file already knows
    whose it is, so nothing downstream has to guess."""
    d = next(d for d in SyncedFolder(drop_root).drops() if d.ref == "2026-0001")
    assert d.label == "Maplewood"
    assert len(d.files) == 3          # two forms and the placeholder


def test_a_folder_with_no_ref_is_still_reported_not_skipped(tmp_path):
    """Silently ignoring a folder loses documents. It is listed with no ref so
    the report can say what is wrong with it."""
    root = tmp_path / "up"
    _form(root / "some client" / "a.pdf", W2)
    drops = SyncedFolder(root).drops()
    assert len(drops) == 1 and drops[0].ref == ""


def test_an_empty_drop_folder_is_not_reported_as_an_arrival(tmp_path):
    root = tmp_path / "up"
    (root / "2026-0009 — Nobody").mkdir(parents=True)
    assert SyncedFolder(root).drops() == []


# -- collecting ---------------------------------------------------------------

def test_collect_files_each_document_by_type(drop_root, tmp_path):
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True)
    one = next(r for r in rep.drops if r.drop.ref == "2026-0001")
    kinds = {a.label for a in one.arrivals}
    assert kinds == {"W-2", "1099-INT"}


def test_the_clients_upload_is_never_moved_or_deleted(drop_root, tmp_path):
    before = sorted(p.name for p in (drop_root / "2026-0001 — Maplewood").iterdir())
    collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True)
    after = sorted(p.name for p in (drop_root / "2026-0001 — Maplewood").iterdir())
    assert before == after, "the copy the client sent is the evidence of what they sent"


def test_a_placeholder_is_refused_and_named(drop_root, tmp_path):
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True)
    one = next(r for r in rep.drops if r.drop.ref == "2026-0001")
    assert one.not_downloaded == ["placeholder.pdf"], one.not_downloaded
    assert "placeholder.pdf" not in {a.name for a in one.arrivals}


def test_a_placeholder_is_collected_on_a_later_run_once_it_downloads(drop_root, tmp_path):
    lib = tmp_path / "lib"
    collect(SyncedFolder(drop_root), library=lib, apply=True)
    # the client's file finishes syncing
    _form(drop_root / "2026-0001 — Maplewood" / "placeholder.pdf", INT)
    rep = collect(SyncedFolder(drop_root), library=lib, apply=True)
    one = next(r for r in rep.drops if r.drop.ref == "2026-0001")
    assert one.not_downloaded == []
    assert "placeholder.pdf" in {a.name for a in one.arrivals}, \
        "a refused file must not be marked done -- it has to come back"


def test_running_twice_does_not_collect_the_same_document_twice(drop_root, tmp_path):
    lib = tmp_path / "lib"
    first = collect(SyncedFolder(drop_root), library=lib, apply=True)
    second = collect(SyncedFolder(drop_root), library=lib, apply=True)
    assert first.collected == 3        # two for Maplewood, one for Riverbend
    assert second.collected == 0, "a second run re-filed documents it already had"


def test_a_preview_run_writes_nothing(drop_root, tmp_path):
    lib = tmp_path / "lib"
    rep = collect(SyncedFolder(drop_root), library=lib, apply=False)
    assert rep.collected == 3
    assert not lib.exists(), "preview must not write"


def test_the_report_says_which_folder_it_could_not_place(tmp_path):
    root = tmp_path / "up"
    _form(root / "no ref here" / "a.pdf", W2)
    rep = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True)
    assert rep.drops[0].unresolved
    assert "name" in rep.drops[0].unresolved.lower()


def test_a_combined_upload_becomes_one_document_per_form(tmp_path):
    """A client's single scan is often several documents. The register should
    count documents -- which is what a request is about -- not files, which is
    an accident of how they used their scanner."""
    root = tmp_path / "up"
    stack = root / "2026-0003 — Ashford" / "Untitled (3).pdf"
    doc = pymupdf.open()
    for lines in ([["Form 1099-DIV", "Dividends and Distributions",
                    "1a Total ordinary dividends 1,204.00"],
                   ["Form 1099-INT", "Interest Income",
                    "1 Interest income 412.55"]]):
        page = doc.new_page()
        y = 72
        for line in lines:
            page.insert_text((72, y), line, fontsize=11)
            y += 16
    stack.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(stack))
    doc.close()

    lib = tmp_path / "lib"
    rep = collect(SyncedFolder(root), library=lib, apply=True)
    labels = sorted(a.label for a in rep.drops[0].arrivals)
    assert labels == ["1099-DIV", "1099-INT"], labels


def test_splitting_leaves_no_working_files_in_the_library(tmp_path):
    """Found by running it: the splitter wrote its parts into the library and
    left them there, so every combined upload produced a duplicate of each
    document in a stray folder beside the real ones."""
    root = tmp_path / "up"
    stack = root / "2026-0003 — Ashford" / "combined.pdf"
    doc = pymupdf.open()
    for lines in ([["Form 1099-DIV", "Dividends and Distributions"],
                   ["Form 1099-INT", "Interest Income"]]):
        page = doc.new_page()
        page.insert_text((72, 72), lines[0], fontsize=11)
        page.insert_text((72, 88), lines[1], fontsize=11)
    stack.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(stack))
    doc.close()

    lib = tmp_path / "lib"
    collect(SyncedFolder(root), library=lib, apply=True)
    strays = [p for p in lib.rglob("*") if p.is_dir() and p.name.startswith("_")]
    assert strays == [], f"working files left in the library: {strays}"


def test_the_preview_counts_what_the_run_will_actually_file(tmp_path):
    """A preview that undercounts is worse than no preview.

    Found by running both: splitting was gated on `apply`, so a combined upload
    showed as ONE document in the preview and filed as TWO. The preview is the
    thing the firm decides on -- "a claim in one place, behaviour in another,
    and nothing comparing them" is the shape this repository keeps paying for,
    and this test is the comparison.
    """
    root = tmp_path / "up"
    stack = root / "2026-0004 — Calder" / "combined.pdf"
    doc = pymupdf.open()
    for title, sub in (("Form 1099-DIV", "Dividends and Distributions"),
                       ("Form 1099-INT", "Interest Income")):
        page = doc.new_page()
        page.insert_text((72, 72), title, fontsize=11)
        page.insert_text((72, 88), sub, fontsize=11)
    stack.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(stack))
    doc.close()

    preview = collect(SyncedFolder(root), library=tmp_path / "lib", apply=False)
    applied = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True)
    assert preview.collected == applied.collected == 2
    assert ([a.label for a in preview.drops[0].arrivals]
            == [a.label for a in applied.drops[0].arrivals])


# -- closing the loop: a collected document marks its request Received --------

def test_a_collected_document_closes_the_request_it_satisfies(tmp_path):
    """The half that was open until 31 Aug 2026.

    Filing always worked. Marking Received did not, because the drop folder
    carries the client-facing ref and the request table keys on a client id, and
    nothing joined them. `engagement_ref` on the engagement is that join.
    """
    from satc.models.intake import IntakeEngagement
    from satc.models.mart import DocumentRecord
    from satc.persistence.store import SATCStore

    root = tmp_path / "up"
    _form(root / "2026-0001 — Maplewood" / "IMG_4471.pdf", W2)

    store = SATCStore(tmp_path / "db")
    store.save_intake_engagement(IntakeEngagement(
        engagement_id="E1", client_id="C1", workflow_key="1040",
        engagement_ref="2026-0001"))
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D1", client_id="C1", tax_year=2026, doc_type="W-2",
        status="Requested", note="Upload your W-2s"))
    store.save_mart(mart)

    rep = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True,
                  store=store)
    one = rep.drops[0]
    assert one.client_id == "C1"
    assert [a.satisfied for a in one.arrivals] == ["W-2"]
    assert [d.status for d in store.load_mart().documents] == ["Received"]


def test_an_unknown_ref_files_the_document_and_says_it_could_not_place_it(tmp_path):
    """Never a guess. A ref the store does not hold must not reconcile against
    whichever client was saved first — that would mark another client's request
    Received on a stranger's document."""
    from satc.persistence.store import SATCStore

    root = tmp_path / "up"
    _form(root / "2026-9999 — Nobody" / "w2.pdf", W2)
    store = SATCStore(tmp_path / "db")

    rep = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True,
                  store=store)
    one = rep.drops[0]
    assert one.client_id == ""
    assert one.arrivals, "the document is still filed"
    assert all(a.satisfied == "" for a in one.arrivals)
    assert "2026-9999" in one.unresolved


def test_collecting_without_a_store_still_files(tmp_path, drop_root):
    """The store is optional: filing is useful on its own and must not require
    the intake database to exist."""
    rep = collect(SyncedFolder(drop_root), library=tmp_path / "lib", apply=True)
    assert rep.collected == 3
    assert all(a.satisfied == "" for d in rep.drops for a in d.arrivals)


def test_an_unplaceable_document_cannot_close_a_request_with_a_blank_client(tmp_path):
    """The guard mutation testing said was unproven, made real.

    Removing `and dr.client_id` from the reconcile call broke no test, because
    reconcile_received finds no candidates for client_id="" — as long as no
    DocumentRecord carries a blank client_id. Nothing forbids one: the field is a
    plain string and an import, a fixture or a half-written row can leave it
    empty.

    So the exposure is: a drop folder whose ref does not resolve produces
    client_id="", and without the guard that would be handed to reconcile, where
    it would match any request with an equally blank client and mark a stranger's
    document Received. Unlikely, cheap to prevent, and impossible to notice
    afterwards — which is the combination that earns a check.
    """
    from satc.models.mart import DocumentRecord
    from satc.persistence.store import SATCStore

    root = tmp_path / "up"
    _form(root / "2026-9999 — Nobody" / "w2.pdf", W2)      # ref not in the store

    store = SATCStore(tmp_path / "db")
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D-ORPHAN", client_id="", tax_year=2026, doc_type="W-2",
        status="Requested", note="a row with no client on it"))
    store.save_mart(mart)

    rep = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True,
                  store=store)
    assert rep.drops[0].client_id == ""
    assert all(a.satisfied == "" for a in rep.drops[0].arrivals)
    assert [d.status for d in store.load_mart().documents] == ["Requested"], \
        "a document we could not place closed a request with a blank client"


# -- how long a client's upload lives -----------------------------------------
#
# SEVEN YEARS, and it is a transcription rather than a choice: the firm's
# engagement letters already promise "we keep copies of your records and our
# work papers for seven years". NOTHING DELETES. The firm said never delete on
# ingest; removing a client's documents unattended is not something this
# software does, so the period is reported and a person acts on it.

def _aged_drop(tmp_path, ages_in_days):
    import os
    import time

    from satc.collect import Drop

    folder = tmp_path / "2026-0001 — Maplewood"
    folder.mkdir(parents=True)
    files = []
    for i, days in enumerate(ages_in_days):
        f = folder / f"doc{i}.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        os.utime(f, (time.time() - days * 86400,) * 2)
        files.append(f)
    return Drop(path=folder, ref="2026-0001", label="Maplewood", files=tuple(files))


def test_a_file_older_than_the_retention_period_is_reported():
    from satc.collect import RETENTION_YEARS
    assert RETENTION_YEARS == 7, "the period the engagement letter already promises"


def test_only_the_files_past_the_period_are_named(tmp_path):
    from satc.collect import _past_retention

    drop = _aged_drop(tmp_path, [30, 8 * 365, 3 * 365, 9 * 365])
    assert _past_retention(drop) == ["doc1.pdf", "doc3.pdf"]


def test_a_file_exactly_at_the_period_is_not_yet_past_it(tmp_path):
    """ON the boundary, not near it. Written a day inside first, which pinned
    nothing: `<` and `<=` both passed it. An off-by-one here reports a client's
    documents expired a day early, which is the direction that loses things."""
    from satc.collect import RETENTION_DAYS, _past_retention

    assert _past_retention(_aged_drop(tmp_path / "on", [RETENTION_DAYS])) == []
    assert _past_retention(_aged_drop(tmp_path / "past", [RETENTION_DAYS + 1])) \
        == ["doc0.pdf"]


def test_reporting_them_does_not_remove_them(tmp_path):
    """The assertion that matters. Everything else here is arithmetic."""
    from satc.collect import _past_retention

    drop = _aged_drop(tmp_path, [9 * 365, 9 * 365])
    _past_retention(drop)
    assert all(f.exists() for f in drop.files)


def test_a_file_that_cannot_be_read_is_not_judged(tmp_path):
    """A OneDrive placeholder with no local bytes has no honest date, and
    guessing one would report a document expired that nobody has seen."""
    from satc.collect import Drop, _past_retention

    missing = tmp_path / "gone.pdf"
    drop = Drop(path=tmp_path, ref="2026-0001", label="X", files=(missing,))
    assert _past_retention(drop) == []


# -- filing and closing are different jobs ------------------------------------

def test_a_filename_only_verdict_files_the_document_but_closes_nothing(tmp_path):
    """THE SAME MONEY BUG THROUGH A DIFFERENT DOOR, found by an adversarial
    review of the page fix. The gate here asked only whether ANY rung had named
    the document, and the FILENAME rung names things it has not read: a
    Schedule C called `2025 Schedule C 1040.pdf` comes back `Prior-year 1040`
    at LOW and closed the client's open prior-year request.

    The document is still collected and still filed -- a helpful name is a fine
    hint for WHERE to put something. It is not evidence of WHAT it is.
    """
    from satc.models.intake import IntakeEngagement
    from satc.models.mart import DocumentRecord
    from satc.persistence.store import SATCStore

    root = tmp_path / "up"
    # Prose that names no form: the content rung must decline, so the filename
    # is the only thing left to go on.
    _form(root / "2026-0001 — Maplewood" / "2025 Schedule C 1040.pdf",
          "Profit or Loss From Business. Gross receipts or sales.")

    store = SATCStore(tmp_path / "db")
    store.save_intake_engagement(IntakeEngagement(
        engagement_id="E1", client_id="C1", workflow_key="1040",
        engagement_ref="2026-0001"))
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D1", client_id="C1", tax_year=2026,
        doc_type="Prior-year return", status="Requested",
        note="Upload prior-year federal and state tax returns"))
    store.save_mart(mart)

    rep = collect(SyncedFolder(root), library=tmp_path / "lib", apply=True,
                  store=store)
    one = rep.drops[0]

    assert one.arrivals, "the document must still be collected"
    assert one.arrivals[0].method == "filename"
    assert one.arrivals[0].filed_to, "and still filed somewhere"
    assert one.arrivals[0].satisfied == "", "a filename guess closed a request"
    assert [d.status for d in store.load_mart().documents] == ["Requested"]
