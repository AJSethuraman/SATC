"""The evidence split, and the readiness guard it buys.

The single ``DocStatus`` enum spanned four lifecycles and could not express the
one distinction that decides whether a file can be worked: a K-1 that cannot
exist until September does not block PREP, but it does block FILING. A boolean
"complete?" cannot say that, and a practice that waits for completeness before
starting loses weeks a season.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from satc.models.actor import Actor, ActorRefused
from satc.models.evidence import (
    EvidenceError,
    ReceivedDocument,
    RequestedItem,
    mark_not_applicable,
    satisfy,
)
from satc.models.readiness import (
    assess,
    blocking_class_for,
    decide_to_proceed,
)

MODEL = Actor.model("qwen3:8b")


def _item(doc_type, blocking="non_blocking", status="outstanding", **kw):
    return RequestedItem(
        request_id=f"req-{doc_type}", client_id="C", tax_year=2025,
        doc_type=doc_type, blocking=blocking, status=status, **kw)


# --- the three-way blocking split ---------------------------------------------

def test_a_blocking_item_stops_prep_and_filing():
    item = _item("W-2", "blocking")
    assert item.blocks_prep
    assert item.blocks_transmission


def test_an_expected_late_item_stops_filing_but_not_prep():
    """THE distinction. A K-1 cannot exist until September; waiting for it
    before starting costs a practice weeks a season."""
    item = _item("K-1-1065", "expected_late")
    assert not item.blocks_prep
    assert item.blocks_transmission


def test_a_non_blocking_item_stops_neither():
    item = _item("Organizer", "non_blocking")
    assert not item.blocks_prep
    assert not item.blocks_transmission


def test_a_satisfied_item_blocks_nothing():
    item = _item("W-2", "blocking", status="satisfied")
    assert not item.blocks_prep and not item.blocks_transmission


def test_blocking_class_comes_from_the_cited_rule():
    """What blocks is config cited to Pub 1345, not a literal in code."""
    from satc.obligations.rules import rule

    blocking = rule("form_1040").blocking_docs
    assert blocking_class_for("W-2", blocking) == "blocking"
    assert blocking_class_for("W-2G", blocking) == "blocking"
    assert blocking_class_for("1099-R", blocking) == "blocking"
    assert blocking_class_for("K-1-1065", blocking) == "expected_late"
    assert blocking_class_for("Organizer", blocking) == "non_blocking"


# --- readiness ----------------------------------------------------------------

def _ready(*items):
    return assess(items, client_id="C", tax_year=2025)


def test_a_file_missing_a_w2_cannot_start_prep():
    r = _ready(_item("W-2", "blocking"))
    assert not r.can_start_prep
    assert "blocks starting prep" in r.why_not_prep()


def test_a_file_missing_only_a_k1_can_start_prep_but_not_file():
    """The practitioner's actual rule, encoded."""
    r = _ready(_item("W-2", "blocking", status="satisfied"),
               _item("K-1-1065", "expected_late"))
    assert r.can_start_prep
    assert not r.can_transmit
    assert "Ready to prep" in r.summary_line()
    assert "Pub 1345" in r.why_not_transmit()


def test_a_complete_file_is_ready_for_both():
    r = _ready(_item("W-2", "blocking", status="satisfied"))
    assert r.can_start_prep and r.can_transmit
    assert "ready to file" in r.summary_line()


def test_a_not_applicable_item_does_not_block():
    item = mark_not_applicable(_item("1099-INT", "blocking"),
                              "closed that account in March")
    r = _ready(item)
    assert r.can_transmit
    assert r.not_applicable and r.not_applicable[0].not_applicable_reason


def test_another_clients_requests_are_never_counted():
    mine = _item("W-2", "blocking", status="satisfied")
    theirs = RequestedItem(request_id="x", client_id="OTHER", tax_year=2025,
                           doc_type="W-2", blocking="blocking")
    assert assess([mine, theirs], client_id="C", tax_year=2025).can_transmit


# --- "not applicable" must carry a reason -------------------------------------

def test_marking_not_applicable_without_a_reason_is_refused():
    """A bare N/A is indistinguishable from never having asked."""
    with pytest.raises(EvidenceError, match="without a reason"):
        mark_not_applicable(_item("1099-INT"), "   ")


def test_the_reason_is_what_turns_a_gap_into_a_record():
    item = mark_not_applicable(_item("1099-INT"), "closed that account in March")
    assert item.status == "not_applicable"
    assert item.not_applicable_reason == "closed that account in March"


# --- arrivals carry how they got here -----------------------------------------

def test_a_received_document_records_how_and_from_whom():
    """26 CFR 1.6695-2(b)(4)(i)(C) requires exactly this."""
    doc = ReceivedDocument(
        document_id="doc-abc", client_id="C", tax_year=2025, doc_type="W-2",
        obtained_how="furnished_by_client", obtained_at=datetime(2026, 2, 3, 9, 0),
        furnished_by="Jordan Maplewood", channel="email")
    assert doc.has_known_provenance


def test_a_document_with_unknown_provenance_says_so():
    """Not a shrug — a compliance defect the system can see."""
    doc = ReceivedDocument(document_id="doc-abc", client_id="C", tax_year=2025,
                           doc_type="W-2")
    assert not doc.has_known_provenance


def test_satisfying_a_request_links_both_ways():
    item = _item("W-2", "blocking")
    doc = ReceivedDocument(document_id="doc-abc", client_id="C", tax_year=2025,
                           doc_type="W-2")
    satisfy(item, doc)
    assert item.status == "satisfied"
    assert item.satisfied_by_document_id == "doc-abc"
    assert doc.satisfies_request_id == item.request_id


def test_a_model_classified_arrival_is_marked_as_such():
    doc = ReceivedDocument(document_id="d", client_id="C", tax_year=2025,
                           doc_type="W-2", classified_by=MODEL)
    assert doc.is_model_classified


# --- the decision is recorded, not just computed ------------------------------

def test_proceeding_is_recorded_with_who_and_when():
    r = _ready(_item("W-2", "blocking", status="satisfied"))
    decision = decide_to_proceed(r, actor=Actor.owner())
    assert decision.decided_by.is_human
    assert not decision.was_override


def test_overriding_a_blocking_item_demands_a_reason():
    """The note IS the §1.6695-2(d) evidence. A silent bypass destroys it."""
    r = _ready(_item("W-2", "blocking"))
    with pytest.raises(ValueError, match="needs a reason"):
        decide_to_proceed(r, actor=Actor.owner())


def test_an_override_with_a_reason_records_what_was_overridden():
    r = _ready(_item("W-2", "blocking"))
    decision = decide_to_proceed(r, actor=Actor.owner(),
                                 reason="client confirmed the employer never issued one")
    assert decision.was_override
    assert decision.proceeded_despite == ("W-2",)
    assert "never issued" in decision.reason


def test_a_model_cannot_decide_a_file_is_ready():
    r = _ready(_item("W-2", "blocking", status="satisfied"))
    with pytest.raises(ActorRefused):
        decide_to_proceed(r, actor=MODEL)


# --- what the old enum could not say ------------------------------------------

def test_the_old_single_status_could_not_express_this():
    """Documentation as a test: the four states the split makes distinguishable
    all collapsed to "Requested" before."""
    states = {
        "blocking and open": _item("W-2", "blocking"),
        "expected late": _item("K-1-1065", "expected_late"),
        "not applicable with a reason": mark_not_applicable(
            _item("1099-INT"), "account closed"),
        "satisfied": _item("1099-DIV", status="satisfied"),
    }
    signatures = {
        (i.status, i.blocking, bool(i.not_applicable_reason),
         i.blocks_prep, i.blocks_transmission)
        for i in states.values()
    }
    assert len(signatures) == len(states), "two states are still indistinguishable"
