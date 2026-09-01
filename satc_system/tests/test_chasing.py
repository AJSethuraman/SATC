"""Who owes us a DOCUMENT this morning — the half of a promise that was missing.

The business engagement letter says *"We will tell you what we need and when,
and we will chase it."* Telling them was built: intake opens a ``Requested`` row
per ask and the organizer carries the list. The chasing was a single number on a
workbook dashboard — ``COUNTIF(status, "Requested")``. A count tells nobody
whose document it is, how long it has been out, or which of the five forms one
request named are still missing, so nothing was ever actually chased with it.

These tests hold the three things that make the list worth opening: it is
ordered by how long somebody has been waiting, it never invents a wait it does
not know, and it says what it looked at rather than printing "all clear" over an
empty store.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from satc.cli import main
from satc.intake.chasing import waiting
from satc.intake.service import create_person_client, reconcile_received
from satc.models.mart import DocumentRecord
from satc.persistence.store import SATCStore

TODAY = date(2026, 9, 1)

# The core-income request as the firm actually ships it, five forms in one ask.
BUNDLE = ("Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G, and any other "
          "income forms received.")


def _days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def _store(tmp_path, *rows):
    """A register of ``(id, client, doc_type, status, as_of, note)`` rows."""
    store = SATCStore(str(tmp_path / "data"))
    mart = store.load_mart()
    for doc_id, client_id, doc_type, status, as_of, note in rows:
        mart.documents.append(DocumentRecord(
            document_id=doc_id, client_id=client_id, tax_year=2025,
            doc_type=doc_type, status=status, as_of=as_of, note=note))
    store.save_mart(mart)
    return store


# -- the order of the list ----------------------------------------------------

def test_the_client_waiting_longest_is_first(tmp_path):
    """The whole reason to open the screen. A register in insertion order is
    what the Documents page already showed, and it put the request nobody has
    chased in three months underneath one opened last week."""
    store = _store(
        tmp_path,
        ("D1", "C1", "1099-DIV", "Requested", _days_ago(9), "corrected 1099-DIV"),
        ("D2", "C2", "Trial balance", "Requested", _days_ago(96), "year-end TB"),
        ("D3", "C3", "Organizer", "Requested", _days_ago(40), "organizer"),
    )
    sweep = waiting(store, today=TODAY)

    assert [w.document_id for w in sweep.rows] == ["D2", "D3", "D1"]
    assert [w.waiting_days(TODAY) for w in sweep.rows] == [96, 40, 9]


def test_a_request_with_no_date_is_an_unknown_wait_and_not_a_new_one(tmp_path):
    """NEVER INVENT A WAIT. A row with no ``as_of`` has waited an unknown time,
    which may well be the longest of all — it is the request most likely to have
    been forgotten. Treated as zero it sorts to the bottom of a longest-first
    list, which is exactly where a forgotten request goes to stay forgotten."""
    store = _store(
        tmp_path,
        ("D1", "C1", "Trial balance", "Requested", _days_ago(200), "year-end TB"),
        ("D2", "C2", "Organizer", "Requested", None, "organizer outstanding"),
    )
    sweep = waiting(store, today=TODAY)

    dateless = next(w for w in sweep.rows if w.document_id == "D2")
    assert dateless.waiting_days(TODAY) is None, "an absent date is not zero days"
    assert sweep.rows[0].document_id == "D2", (
        "the unknown wait sorted below a 200-day one — it was ranked as if new")


def test_a_request_opened_this_morning_is_held_back_but_still_counted(tmp_path):
    """Mirrors the signature screen's rule for a pack built today: chasing on
    the morning you asked is noise, not a chase, and a list that is mostly noise
    is a list nobody opens. Held back is not hidden — the count is reported, or
    the sweep would silently stop adding up to the register."""
    store = _store(
        tmp_path,
        ("D1", "C1", "Organizer", "Requested", TODAY, "asked this morning"),
        ("D2", "C2", "Trial balance", "Requested", _days_ago(30), "year-end TB"),
    )
    sweep = waiting(store, today=TODAY)

    assert [w.document_id for w in sweep.rows] == ["D2"]
    assert sweep.opened_today == 1
    assert sweep.documents == 2, "the row was dropped from the denominator too"


# -- a request that names several forms ---------------------------------------

def test_a_bundle_says_which_of_its_forms_are_still_missing(tmp_path):
    """"Still outstanding" is what gets skimmed past. "Still waiting on the
    1099-B" is what gets a document into the office. The core-income request
    names five forms and stays open until all five arrive, so the chase has to
    say which two of them the client has actually sent."""
    store = _store(tmp_path,
                   ("D1", "C1", "Core income documents", "Requested",
                    _days_ago(21), BUNDLE))
    reconcile_received(store, client_id="C1", doc_type="W-2", doc_year=2025)
    reconcile_received(store, client_id="C1", doc_type="1099-INT", doc_year=2025)

    row = waiting(store, today=TODAY).rows[0]

    assert row.is_bundle and row.named == 5
    assert row.here == "1099-INT, W-2"
    assert row.still_missing == "1099-B / brokerage, 1099-DIV, 1099-G"
    assert row.part_way == "2 of 5 here"


def test_an_ordinary_single_form_request_claims_nothing_about_parts(tmp_path):
    """Nearly every request names one form. A "1 of 1 here" line under each of
    them would bury the bundles that matter."""
    store = _store(tmp_path, ("D1", "C1", "W-2", "Requested", _days_ago(5),
                              "Upload your W-2 from each employer"))
    row = waiting(store, today=TODAY).rows[0]

    assert not row.is_bundle
    assert row.still_missing == "" and row.part_way == ""


# -- what the sweep looked at -------------------------------------------------

def test_an_empty_store_reports_that_it_examined_nothing(tmp_path):
    """S2. "Nothing outstanding" and "nothing looked at" are the same sentence
    unless the check says which, and only one of them is good news."""
    sweep = waiting(SATCStore(str(tmp_path / "data")), today=TODAY)

    assert sweep.rows == [] and sweep.documents == 0
    assert sweep.examined_nothing


def test_a_register_with_nothing_outstanding_reports_what_it_read(tmp_path):
    """The other half of the same rule: a genuinely clear register must be
    distinguishable from a store nobody has put anything in."""
    store = _store(
        tmp_path,
        ("D1", "C1", "W-2", "Received", _days_ago(30), ""),
        ("D2", "C1", "Engagement letter", "Signed", _days_ago(60), ""),
        ("D3", "C2", "Delivery email", "Sent", _days_ago(10), ""),
    )
    sweep = waiting(store, today=TODAY)

    assert sweep.rows == []
    assert not sweep.examined_nothing
    assert (sweep.documents, sweep.clients) == (3, 2)


def test_a_document_already_here_is_not_chased(tmp_path):
    """Chasing a client for something they sent last week is worse than not
    chasing at all — it is the message that teaches them to ignore the next."""
    store = _store(
        tmp_path,
        ("D1", "C1", "Trial balance", "Requested", _days_ago(50), "year-end TB"),
        ("D2", "C1", "W-2", "Received", _days_ago(90), "arrived"),
        ("D3", "C1", "1095-A", "N/A", _days_ago(90), "no marketplace coverage"),
    )
    sweep = waiting(store, today=TODAY)

    assert [w.document_id for w in sweep.rows] == ["D1"]
    assert sweep.documents == 3, "the sweep must report every row it read"


# -- PII ----------------------------------------------------------------------

def test_the_screen_names_the_client_and_never_their_tin(tmp_path, capsys):
    """The register is de-identified and the vault holds the name; a screen left
    open on a desk all morning is the last place a TIN belongs. The mart's
    ``tin_last4`` and ``tin_masked`` sit on the same row as the display label,
    one attribute away from whoever adds the next column."""
    store = SATCStore(str(tmp_path))
    cid = create_person_client(store, first_name="Priya", last_name="Raghavan",
                               ssn="123-45-6789", client_id="SATC-005000")
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D1", client_id=cid, tax_year=2025, doc_type="Trial balance",
        status="Requested", as_of=date.today() - timedelta(days=12),
        note="Awaiting year-end trial balance"))
    store.save_mart(mart)

    assert main(["chase", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out

    assert "Priya Raghavan" in out, "a handle is not something you can chase"
    assert "6789" not in out and "123-45-6789" not in out
    assert "*" not in out, "a masked TIN is still a TIN on the screen"


# -- the command itself -------------------------------------------------------

def test_the_command_prints_the_wait_the_ask_and_the_missing_forms(tmp_path, capsys):
    store = SATCStore(str(tmp_path))
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D1", client_id="SATC-005000", tax_year=2025,
        doc_type="Core income documents", status="Requested",
        as_of=date.today() - timedelta(days=24), note=BUNDLE))
    store.save_mart(mart)
    reconcile_received(store, client_id="SATC-005000", doc_type="1099-DIV",
                       doc_year=2025)

    assert main(["chase", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out

    assert "24d" in out
    assert "Core income documents" in out
    assert "still waiting on" in out
    assert "1099-B / brokerage" in out


def test_the_command_says_which_kind_of_empty_it_found(tmp_path, capsys):
    """The bug this repository keeps having is something reporting success it
    did not verify. An empty store must not print the sentence a clear one
    prints."""
    assert main(["chase", "--dir", str(tmp_path / "empty")]) == 0
    nothing = capsys.readouterr().out
    assert "Nothing looked at" in nothing
    assert "Nothing outstanding" not in nothing

    store = SATCStore(str(tmp_path / "clear"))
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D1", client_id="C1", tax_year=2025, doc_type="W-2",
        status="Received", as_of=date.today()))
    store.save_mart(mart)

    assert main(["chase", "--dir", str(tmp_path / "clear")]) == 0
    clear = capsys.readouterr().out
    assert "Nothing outstanding" in clear
    assert "1 register row(s) read" in clear


# -- the browser half ---------------------------------------------------------

def test_the_documents_page_shows_the_same_sweep_in_the_same_order():
    """S3: two halves of one tool must make the same call, because whichever
    you ran is the one you believed. The Documents page used to list outstanding
    requests in register order with no wait on them at all, so the screen and
    the morning list disagreed about who to ring first."""
    import pytest

    pytest.importorskip("flask")
    from satc.app.server import create_app
    from satc.app.state import STATE

    sweep = waiting(STATE.store)
    assert sweep.rows, "nothing outstanding in the demo store — this proved nothing"

    page = create_app().test_client().get("/documents").get_data(as_text=True)
    panel = page[page.index("Who owes us a document"):]
    on_screen = [int(n) for n in re.findall(r"<td>(\d+) day\(s\)", panel)]

    assert on_screen == [w.waiting_days() for w in sweep.rows
                         if w.waiting_days() is not None], (
        "the page ordered the chase differently from the command")
    assert panel.count("not known") == sum(
        1 for w in sweep.rows if w.waiting_days() is None)
    assert f"{sweep.documents} register row(s) read" in panel
