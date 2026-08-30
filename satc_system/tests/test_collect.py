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
