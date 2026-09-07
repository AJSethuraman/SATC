"""A request naming several forms closes only when every one of them has arrived.

FOUND IN A LIVE RUN, 31 August 2026. The request read *"Upload Forms 1099-INT,
1099-DIV and brokerage statements"*. The 1099-DIV arrived and closed it. The
1099-INT that came next found no open request to satisfy, and nobody was ever
asked for the brokerage statement again.

The firm's read: it is the same shape as the consolidated-1099 bug they had
already paid for -- the packet reads complete while a named form is still
missing -- arriving from the other direction. That one was a document carrying
several forms; this one is a request naming several forms.

DECIDED 4 September 2026, when the firm was asked directly whether a bundle
should stay open when one part arrives: it stays open until every named part
has arrived. A partly-satisfied bundle is still a debt, and the chase list is
the thing that says who owes what.

Ported from `parked/satc-system-pre-schema-port` onto `RequestedItem`. The
original was written against `DocumentRecord`, which the schema port deleted --
the mechanism went with it, and this file is the mechanism coming back.
"""

from __future__ import annotations

from satc.intake import matching
from satc.intake.service import outstanding_parts, reconcile_received
from satc.models.evidence import RequestedItem
from satc.persistence.store import SATCStore

REQUEST = "Upload Forms 1099-INT, 1099-DIV and brokerage statements"


def _store(tmp_path, request_text=REQUEST, doc_type="Core income documents"):
    store = SATCStore(str(tmp_path / "data"))
    store.save_requested_items([RequestedItem(
        request_id="REQ-1", client_id="C1", tax_year=2026,
        doc_type=doc_type, request_text=request_text, status="outstanding")])
    return store


def _status(store, request_id="REQ-1"):
    return next(i.status for i in store.load_requested_items()
                if i.request_id == request_id)


# -- what the request names ---------------------------------------------------

def test_the_request_is_recognised_as_naming_three_forms():
    assert matching.is_bundle(REQUEST)
    assert matching.families(REQUEST) == {"1099INT", "1099DIV", "1099B"}


def test_a_plain_request_is_not_a_bundle():
    """Nearly every request names one form and must behave exactly as before."""
    assert not matching.is_bundle("W-2", "Upload your W-2 from each employer")


# -- the live failure ---------------------------------------------------------

def test_the_first_form_of_a_bundle_does_not_close_it(tmp_path):
    store = _store(tmp_path)
    got = reconcile_received(store, client_id="C1", doc_type="1099-DIV")

    assert got is not None, "the document still belongs to that request"
    assert _status(store) == "outstanding", "the 1099-DIV closed the whole bundle"
    assert outstanding_parts(got) == {"1099INT", "1099B"}


def test_the_second_form_still_finds_the_request_open(tmp_path):
    """The half of the bug that cost the client: after the 1099-DIV closed it,
    the 1099-INT arrived and matched nothing at all."""
    store = _store(tmp_path)
    reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    got = reconcile_received(store, client_id="C1", doc_type="1099-INT")

    assert got is not None, "the 1099-INT found no open request — the live bug"
    assert _status(store) == "outstanding"
    assert outstanding_parts(got) == {"1099B"}


def test_the_last_form_closes_it(tmp_path):
    store = _store(tmp_path)
    for label in ("1099-DIV", "1099-INT", "1099-B"):
        got = reconcile_received(store, client_id="C1", doc_type=label)
    assert _status(store) == "satisfied"
    assert outstanding_parts(got) == set()


def test_the_same_form_twice_does_not_advance_the_bundle(tmp_path):
    """Two 1099-DIVs from two brokers is an ordinary year, not two forms."""
    store = _store(tmp_path)
    reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    got = reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    assert _status(store) == "outstanding"
    assert outstanding_parts(got) == {"1099INT", "1099B"}


# -- the behaviour that must not change --------------------------------------

def test_a_single_form_request_still_closes_on_its_form(tmp_path):
    """The whole point of the loop. Breaking this to fix bundles would be worse
    than the bug."""
    store = _store(tmp_path, request_text="Upload your W-2 from each employer",
                   doc_type="W-2")
    got = reconcile_received(store, client_id="C1", doc_type="W-2")
    assert got is not None
    assert _status(store) == "satisfied"
    assert outstanding_parts(got) == set()


def test_what_arrived_survives_a_reload(tmp_path):
    """Held in the mart, not in memory: a run tomorrow must know the 1099-DIV
    came in today, or the bundle never closes."""
    store = _store(tmp_path)
    reconcile_received(store, client_id="C1", doc_type="1099-DIV")

    reopened = SATCStore(str(tmp_path / "data"))
    item = next(i for i in reopened.load_requested_items()
                if i.request_id == "REQ-1")
    assert item.parts == {"1099DIV"}
    assert outstanding_parts(item) == {"1099INT", "1099B"}


def test_the_outstanding_forms_are_named_the_way_the_firm_reads_them(tmp_path):
    """A note saying "still waiting on 1099INT, 1099B" is storage leaking into
    something a person reads."""
    store = _store(tmp_path)
    got = reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    assert matching.names(outstanding_parts(got)) == "1099-B / brokerage, 1099-INT"


# -- the migration ------------------------------------------------------------

def test_a_database_written_before_this_column_existed_still_opens(tmp_path):
    """THE STORE ON THIS MACHINE ALREADY HAS ROWS.

    A new column is free on a fresh database and is exactly where a real one
    breaks, so this builds the before picture rather than asserting against the
    after picture and calling it a migration test: the table is rebuilt WITHOUT
    `parts`, a row is written into it, and only then is the store opened the way
    the app opens it.
    """
    import sqlite3

    _store(tmp_path)                       # let the store lay the schema down
    db = tmp_path / "data" / "satc_mart.db"

    con = sqlite3.connect(db)
    con.execute("DROP TABLE requested_items")
    con.execute("""CREATE TABLE requested_items (
        request_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER,
        doc_type TEXT, request_text TEXT, blocking TEXT, status TEXT,
        not_applicable_reason TEXT, requested_at TEXT,
        satisfied_by_document_id TEXT, task_id TEXT, follow_up_round INTEGER)""")
    con.execute("INSERT INTO requested_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("REQ-1", "C1", 2026, "Core income documents", REQUEST,
                 "non_blocking", "outstanding", "", None, "", "", 0))
    con.commit()
    cols = {r[1] for r in con.execute("PRAGMA table_info(requested_items)")}
    con.close()
    assert "parts" not in cols, "the before picture must actually be the before picture"

    again = SATCStore(str(tmp_path / "data"))
    item = next(i for i in again.load_requested_items() if i.request_id == "REQ-1")
    assert item.parts == set(), "an untouched request has received nothing"
    assert item.outstanding_parts == {"1099INT", "1099DIV", "1099B"}

    # And it still WORKS afterwards -- a migration that opens the file but
    # cannot write to it is the failure worth catching.
    got = reconcile_received(again, client_id="C1", doc_type="1099-DIV")
    assert outstanding_parts(got) == {"1099INT", "1099B"}
    assert _status(again) == "outstanding"


def test_the_migration_runs_twice_without_complaining(tmp_path):
    """Every app start calls it. The second start must not fail on a duplicate
    column."""
    _store(tmp_path)
    for _ in range(3):
        SATCStore(str(tmp_path / "data"))


# -- the limit of the rule, and why it has one --------------------------------

STANDING_ASK = ("Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G, and any "
                "other income forms received.")


def test_a_standing_checklist_is_not_a_bundle_that_must_all_arrive():
    """THE RULE HAS TO STOP SOMEWHERE, AND ITS OWN WORDS SAY WHERE.

    `personal_1040_core.yaml` sends this to every 1040 client. It names five
    forms and means "whichever of these you have". Requiring all five would
    hold the request open forever for the ordinary client with no 1099-B and no
    1099-G -- a permanent chase-list entry for documents that do not exist,
    which is a worse failure than the one this file fixes.

    Applying the all-parts rule to it broke three existing tests, and those
    tests were RIGHT.
    """
    assert matching.is_bundle(STANDING_ASK), "it does name several forms"
    assert matching.is_open_ended(STANDING_ASK), "and it says the list is partial"
    assert not matching.needs_every_part(STANDING_ASK)

    assert matching.needs_every_part(REQUEST), \
        "a closed list of three named forms is exactly what the rule is for"


def test_the_standing_checklist_still_closes_on_the_first_form(tmp_path):
    """End to end, not just the predicate: the ordinary path must be untouched."""
    store = _store(tmp_path, request_text=STANDING_ASK)
    got = reconcile_received(store, client_id="C1", doc_type="W-2")

    assert got is not None
    assert _status(store) == "satisfied", \
        "the standing core-income ask jammed open on a client with one W-2"
    assert outstanding_parts(got) == set()


def test_the_open_ended_wordings_we_actually_use_are_all_caught():
    """One phrasing slipping through re-jams the chase list, and the failure is
    silent -- a request that never closes looks like a client who never sent it."""
    for tail in ("and any other income forms received",
                 "and other supporting documents",
                 "1099-INT, 1099-DIV, etc.",
                 "1099-INT and 1099-DIV as applicable",
                 "1099-INT, 1099-DIV, if applicable"):
        assert matching.is_open_ended(f"Upload Forms 1099-INT, 1099-DIV, {tail}"), tail
