"""A request naming several forms closes only when every one of them has arrived.

FOUND IN A LIVE RUN, 31 August 2026. The request read *"Upload Forms 1099-INT,
1099-DIV and brokerage statements"*. The 1099-DIV arrived and closed it. The
1099-INT that came next found no open request to satisfy, and nobody was ever
asked for the brokerage statement again.

The firm's read: it is the same shape as the consolidated-1099 bug they had
already paid for -- the packet reads complete while a named form is still
missing -- arriving from the other direction. That one was a document carrying
several forms; this one is a request naming several forms.
"""

from __future__ import annotations

from satc.intake import matching
from satc.intake.service import outstanding_parts, reconcile_received
from satc.models.mart import DocumentRecord
from satc.persistence.store import SATCStore

REQUEST = "Upload Forms 1099-INT, 1099-DIV and brokerage statements"


def _store(tmp_path, note=REQUEST, doc_type="Core income documents"):
    store = SATCStore(str(tmp_path / "data"))
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="DOC-1", client_id="C1", tax_year=2026,
        doc_type=doc_type, status="Requested", note=note))
    store.save_mart(mart)
    return store


def _status(store, document_id="DOC-1"):
    return next(d.status for d in store.load_mart().documents
                if d.document_id == document_id)


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
    assert _status(store) == "Requested", "the 1099-DIV closed the whole bundle"
    assert outstanding_parts(got) == {"1099INT", "1099B"}


def test_the_second_form_still_finds_the_request_open(tmp_path):
    """The half of the bug that cost the client: after the 1099-DIV closed it,
    the 1099-INT arrived and matched nothing at all."""
    store = _store(tmp_path)
    reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    got = reconcile_received(store, client_id="C1", doc_type="1099-INT")

    assert got is not None, "the 1099-INT found no open request — the live bug"
    assert _status(store) == "Requested"
    assert outstanding_parts(got) == {"1099B"}


def test_the_last_form_closes_it(tmp_path):
    store = _store(tmp_path)
    for label in ("1099-DIV", "1099-INT", "1099-B"):
        got = reconcile_received(store, client_id="C1", doc_type=label)
    assert _status(store) == "Received"
    assert outstanding_parts(got) == set()


def test_the_same_form_twice_does_not_advance_the_bundle(tmp_path):
    """Two 1099-DIVs from two brokers is an ordinary year, not two forms."""
    store = _store(tmp_path)
    reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    got = reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    assert _status(store) == "Requested"
    assert outstanding_parts(got) == {"1099INT", "1099B"}


# -- the behaviour that must not change --------------------------------------

def test_a_single_form_request_still_closes_on_its_form(tmp_path):
    """The whole point of the loop. Breaking this to fix bundles would be worse
    than the bug."""
    store = _store(tmp_path, note="Upload your W-2 from each employer",
                   doc_type="W-2")
    got = reconcile_received(store, client_id="C1", doc_type="W-2")
    assert got is not None
    assert _status(store) == "Received"
    assert outstanding_parts(got) == set()


def test_what_arrived_survives_a_reload(tmp_path):
    """Held in the mart, not in memory: a run tomorrow must know the 1099-DIV
    came in today, or the bundle never closes."""
    store = _store(tmp_path)
    reconcile_received(store, client_id="C1", doc_type="1099-DIV")

    reopened = SATCStore(str(tmp_path / "data"))
    record = next(d for d in reopened.load_mart().documents
                  if d.document_id == "DOC-1")
    assert record.parts == {"1099DIV"}
    assert outstanding_parts(record) == {"1099INT", "1099B"}


def test_the_outstanding_forms_are_named_the_way_the_firm_reads_them(tmp_path):
    """A note saying "still waiting on 1099INT, 1099B" is storage leaking into
    something a person reads."""
    store = _store(tmp_path)
    got = reconcile_received(store, client_id="C1", doc_type="1099-DIV")
    assert matching.names(outstanding_parts(got)) == "1099-B / brokerage, 1099-INT"
