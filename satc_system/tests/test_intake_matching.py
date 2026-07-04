"""Document<->request matching, and the most-specific reconciliation it drives."""

from __future__ import annotations

from satc.intake import create_engagement, create_person_client, reconcile_received
from satc.intake import matching as m
from satc.persistence import SATCStore


# -- the matcher --------------------------------------------------------------

def test_received_form_satisfies_a_bundle_request():
    # A W-2 (or a 1099) satisfies a "core income documents" bundle described in prose.
    bundle = ("Core income documents", "Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G")
    assert m.matches("W-2", *bundle)
    assert m.matches("1099-INT", *bundle)
    assert m.matches("Schedule K-1 (1065)", "K-1", "Upload all S-corp and partnership K-1s")
    assert m.matches("Prior-year 1040", "Prior-year return", "Upload prior-year federal returns")


def test_matcher_does_not_make_false_matches():
    assert not m.matches("1099-INT", "1095-A", "Upload Form 1095-A for Marketplace coverage")
    assert not m.matches("W-2", "1098-T", "Upload Form 1098-T tuition statement")
    assert not m.matches("", "1095-A", "anything")


def test_specificity_prefers_specific_over_bundle():
    assert m.specificity("1095-A", "Upload Form 1095-A") < \
           m.specificity("Core income documents", "W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G")


# -- reconciliation against real requests -------------------------------------

def _engagement(store):
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id="SATC-009100")
    create_engagement(store, client_id=cid, workflow_key="personal_1040_core",
                      due_date="2026-04-15", tax_year=2025,
                      answers={"newSatcClient": "yes", "marketplaceInsurance": "yes",
                               "brokerageActivity": "yes"})
    return cid


def test_w2_closes_the_core_income_request(tmp_path):
    store = SATCStore(tmp_path)
    cid = _engagement(store)
    matched = reconcile_received(store, client_id=cid, doc_type="W-2")
    assert matched is not None and matched.status == "Received"
    assert "income" in matched.doc_type.lower()


def test_no_false_close_and_specific_wins(tmp_path):
    store = SATCStore(tmp_path)
    cid = _engagement(store)
    # A 1099-B matches BOTH the brokerage request and the income bundle -> specific wins.
    matched = reconcile_received(store, client_id=cid, doc_type="1099-B")
    assert matched is not None and "Brokerage" in matched.doc_type
    # A 1098-T matches no open request here.
    assert reconcile_received(store, client_id=cid, doc_type="1098-T") is None


def test_reconcile_completes_the_linked_task(tmp_path):
    store = SATCStore(tmp_path)
    cid = _engagement(store)
    matched = reconcile_received(store, client_id=cid, doc_type="1095-A")
    assert matched is not None
    tasks = [t for e in store.load_intake_engagements() for t in e.tasks
             if t.document_id == matched.document_id]
    assert tasks and all(t.completed for t in tasks)
