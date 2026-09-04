"""Who owes us a DOCUMENT this morning — the half of a promise that was missing.

The business engagement letter says *"We will tell you what we need and when,
and we will chase it."* Telling them was built: intake opens a ``RequestedItem``
per ask and the organizer carries the list. The chasing was a single number on a
workbook dashboard — ``COUNTIF(status, "Requested")``. A count tells nobody
whose document it is, how long it has been out, or which of the forms one
request named are still missing, so nothing was ever actually chased with it.

These tests hold the three things that make the list worth opening: it is
ordered by how long somebody has been waiting, it never invents a wait it does
not know, and it says what it looked at rather than printing "all clear" over an
empty store.

Ported from ``parked/satc-system-pre-schema-port`` onto ``RequestedItem``. The
original was written against ``DocumentRecord`` and a ``"Requested"`` status
string, both of which the schema port deleted.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from satc.cli import main
from satc.intake.chasing import waiting
from satc.intake.service import create_person_client, reconcile_received
from satc.models.evidence import RequestedItem
from satc.persistence.store import SATCStore

TODAY = date(2026, 9, 1)

# A CLOSED list of forms the interview established this client HAS. Every one of
# them must arrive before the request closes, so every one of them is chaseable.
BUNDLE = "Upload Forms 1099-INT, 1099-DIV and brokerage statements"

# THE ONE THAT IS NOT A BUNDLE FOR THIS PURPOSE. The standing core-income ask in
# `personal_1040_core.yaml`, sent to every 1040 client. It names five forms and
# its own wording says the list is partial, so it requires none of them in
# particular — see `matching.needs_every_part` and `test_bundle_stays_open.py`.
STANDING_ASK = ("Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G, and any "
                "other income forms received.")


def _days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def _store(tmp_path, *rows):
    """A register of ``(request_id, client, doc_type, status, requested_at, text)``."""
    store = SATCStore(str(tmp_path / "data"))
    store.save_requested_items([
        RequestedItem(request_id=rid, client_id=cid, tax_year=2025,
                      doc_type=doc_type, request_text=text or "",
                      status=status, requested_at=asked)
        for rid, cid, doc_type, status, asked, text in rows])
    return store


# -- the order of the list ----------------------------------------------------

def test_the_client_waiting_longest_is_first(tmp_path):
    """The whole reason to open the screen. A register in insertion order is
    what the Documents page already showed, and it put the request nobody has
    chased in three months underneath one opened last week."""
    store = _store(
        tmp_path,
        ("D1", "C1", "1099-DIV", "outstanding", _days_ago(9), "corrected 1099-DIV"),
        ("D2", "C2", "Trial balance", "outstanding", _days_ago(96), "year-end TB"),
        ("D3", "C3", "Organizer", "outstanding", _days_ago(40), "organizer"),
    )
    sweep = waiting(store, today=TODAY)

    assert [w.request_id for w in sweep.rows] == ["D2", "D3", "D1"]
    assert [w.waiting_days(TODAY) for w in sweep.rows] == [96, 40, 9]


def test_a_request_with_no_date_is_an_unknown_wait_and_not_a_new_one(tmp_path):
    """NEVER INVENT A WAIT. A row with no ``requested_at`` has waited an unknown
    time, which may well be the longest of all — it is the request most likely to
    have been forgotten. Treated as zero it sorts to the bottom of a longest-first
    list, which is exactly where a forgotten request goes to stay forgotten."""
    store = _store(
        tmp_path,
        ("D1", "C1", "Trial balance", "outstanding", _days_ago(200), "year-end TB"),
        ("D2", "C2", "Organizer", "outstanding", None, "organizer outstanding"),
    )
    sweep = waiting(store, today=TODAY)

    dateless = next(w for w in sweep.rows if w.request_id == "D2")
    assert dateless.waiting_days(TODAY) is None, "an absent date is not zero days"
    assert sweep.rows[0].request_id == "D2", (
        "the unknown wait sorted below a 200-day one — it was ranked as if new")


def test_a_request_opened_this_morning_is_held_back_but_still_counted(tmp_path):
    """Mirrors the signature screen's rule for a pack built today: chasing on
    the morning you asked is noise, not a chase, and a list that is mostly noise
    is a list nobody opens. Held back is not hidden — the count is reported, or
    the sweep would silently stop adding up to the register."""
    store = _store(
        tmp_path,
        ("D1", "C1", "Organizer", "outstanding", TODAY, "asked this morning"),
        ("D2", "C2", "Trial balance", "outstanding", _days_ago(30), "year-end TB"),
    )
    sweep = waiting(store, today=TODAY)

    assert [w.request_id for w in sweep.rows] == ["D2"]
    assert sweep.opened_today == 1
    assert sweep.requests == 2, "the row was dropped from the denominator too"


# -- a request that names several forms ---------------------------------------

def test_a_bundle_says_which_of_its_forms_are_still_missing(tmp_path):
    """"Still outstanding" is what gets skimmed past. "Still waiting on the
    1099-B" is what gets a document into the office. A closed list of three
    named forms stays open until all three arrive, so the chase has to say which
    one of them the client has actually sent."""
    store = _store(tmp_path,
                   ("D1", "C1", "Core income documents", "outstanding",
                    _days_ago(21), BUNDLE))
    reconcile_received(store, client_id="C1", doc_type="1099-DIV", doc_year=2025)

    row = waiting(store, today=TODAY).rows[0]

    assert row.needs_every_part and row.named == 3
    assert row.here == "1099-DIV"
    assert row.still_missing == "1099-B / brokerage, 1099-INT"
    assert row.part_way == "1 of 3 here"


def test_a_standing_checklist_is_never_chased_for_forms_that_may_not_exist(tmp_path):
    """THE TRAP THE PARKED VERSION WALKED INTO, AND THE REASON THIS IS A PORT
    RATHER THAN A RESTORE.

    The parked `Waiting` asked `matching.is_bundle` — "does this name more than
    one form" — which the standing core-income ask answers yes to. Under that
    rule this row would sit on the chase list forever demanding a 1099-B and a
    1099-G from the ordinary client who has neither, because the request never
    closes on parts it does not require. A permanent entry for documents that do
    not exist is worse than the count this screen replaced.

    The request's own words are the tell: it ends "and any other income forms
    received", so it admits its list is partial and cannot also demand all of it.
    """
    store = _store(tmp_path,
                   ("D1", "C1", "Core income documents", "outstanding",
                    _days_ago(21), STANDING_ASK))
    row = waiting(store, today=TODAY).rows[0]

    from satc.intake import matching
    assert matching.is_bundle(STANDING_ASK), "it does name several forms"
    assert not row.needs_every_part, (
        "the standing checklist was treated as a bundle that must all arrive")
    assert row.still_missing == "", (
        "the chase named a 1099-B and a 1099-G nobody established this client has")
    assert row.part_way == ""

    # And it is still ON the list — it is genuinely outstanding, just not
    # chaseable form-by-form. Suppressing the row would lose the whole ask.
    assert row.doc_type == "Core income documents" and row.waiting_days(TODAY) == 21


def test_an_ordinary_single_form_request_claims_nothing_about_parts(tmp_path):
    """Nearly every request names one form. A "1 of 1 here" line under each of
    them would bury the bundles that matter."""
    store = _store(tmp_path, ("D1", "C1", "W-2", "outstanding", _days_ago(5),
                              "Upload your W-2 from each employer"))
    row = waiting(store, today=TODAY).rows[0]

    assert not row.needs_every_part
    assert row.still_missing == "" and row.part_way == ""


# -- what the sweep looked at -------------------------------------------------

def test_an_empty_store_reports_that_it_examined_nothing(tmp_path):
    """S2. "Nothing outstanding" and "nothing looked at" are the same sentence
    unless the check says which, and only one of them is good news."""
    sweep = waiting(SATCStore(str(tmp_path / "data")), today=TODAY)

    assert sweep.rows == [] and sweep.requests == 0
    assert sweep.examined_nothing


def test_a_register_with_nothing_outstanding_reports_what_it_read(tmp_path):
    """The other half of the same rule: a genuinely clear register must be
    distinguishable from a store nobody has put anything in."""
    store = _store(
        tmp_path,
        ("D1", "C1", "W-2", "satisfied", _days_ago(30), ""),
        ("D2", "C1", "1095-A", "not_applicable", _days_ago(60), ""),
        ("D3", "C2", "Mileage log", "withdrawn", _days_ago(10), ""),
    )
    sweep = waiting(store, today=TODAY)

    assert sweep.rows == []
    assert not sweep.examined_nothing
    assert (sweep.requests, sweep.clients) == (3, 2)


def test_a_document_already_here_is_not_chased(tmp_path):
    """Chasing a client for something they sent last week is worse than not
    chasing at all — it is the message that teaches them to ignore the next."""
    store = _store(
        tmp_path,
        ("D1", "C1", "Trial balance", "outstanding", _days_ago(50), "year-end TB"),
        ("D2", "C1", "W-2", "satisfied", _days_ago(90), "arrived"),
        ("D3", "C1", "1095-A", "not_applicable", _days_ago(90), "no marketplace cover"),
    )
    sweep = waiting(store, today=TODAY)

    assert [w.request_id for w in sweep.rows] == ["D1"]
    assert sweep.requests == 3, "the sweep must report every row it read"


# -- PII ----------------------------------------------------------------------

def test_the_screen_names_the_client_and_never_their_tin(tmp_path, capsys):
    """The register is de-identified and the vault holds the name; a screen left
    open on a desk all morning is the last place a TIN belongs. The mart's
    ``tin_last4`` and ``tin_masked`` sit on the same row as the display label,
    one attribute away from whoever adds the next column."""
    store = SATCStore(str(tmp_path))
    cid = create_person_client(store, first_name="Priya", last_name="Raghavan",
                               ssn="123-45-6789", client_id="SATC-005000")
    store.save_requested_items([RequestedItem(
        request_id="D1", client_id=cid, tax_year=2025, doc_type="Trial balance",
        request_text="Awaiting year-end trial balance",
        requested_at=date.today() - timedelta(days=12))])

    assert main(["chase", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out

    assert "Priya Raghavan" in out, "a handle is not something you can chase"
    assert "6789" not in out and "123-45-6789" not in out
    assert "*" not in out, "a masked TIN is still a TIN on the screen"


# -- the command itself -------------------------------------------------------

def test_the_command_prints_the_wait_the_ask_and_the_missing_forms(tmp_path, capsys):
    store = SATCStore(str(tmp_path))
    store.save_requested_items([RequestedItem(
        request_id="D1", client_id="SATC-005000", tax_year=2025,
        doc_type="Core income documents", request_text=BUNDLE,
        requested_at=date.today() - timedelta(days=24))])
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
    store.save_requested_items([RequestedItem(
        request_id="D1", client_id="C1", tax_year=2025, doc_type="W-2",
        status="satisfied", requested_at=date.today())])

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
    assert f"{sweep.requests} register row(s) read" in panel


def test_the_page_says_not_known_rather_than_leaving_the_wait_blank(monkeypatch):
    """The assertion above is worth nothing on the demo store, which dates every
    request — it compares zero against zero. This puts an undated request in
    front of the template, because a blank cell in a "waiting" column reads as
    "just asked", which is the one thing an undated request is not."""
    import pytest

    pytest.importorskip("flask")
    from satc.app.server import create_app
    from satc.app.state import STATE

    monkeypatch.setattr(STATE.store, "load_requested_items", lambda *a, **kw: [
        RequestedItem(request_id="D1", client_id="SATC-001000", tax_year=2025,
                      doc_type="Trial balance", request_text="year-end TB",
                      requested_at=None)])

    page = create_app().test_client().get("/documents").get_data(as_text=True)
    panel = page[page.index("Who owes us a document"):]

    assert "not known" in panel
    assert "no date on this request" in panel
    assert not re.search(r"<td>(\d+) day\(s\)", panel), (
        "a wait was printed for a request that carries no date")
