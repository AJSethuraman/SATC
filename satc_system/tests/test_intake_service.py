"""Tests for the intake service (:mod:`satc.intake.service`) over a temp store.

The service is the seam between the checklist workflows and SATC's data model:
minting clients into the vault with a de-identified mart projection, generating
engagements that open ``Requested`` documents per client ask, and reconciling
arriving documents back to their tasks.

Each test uses a fresh :class:`SATCStore` rooted at pytest's ``tmp_path`` (an
unseeded, empty store) and passes explicit ``client_id`` values for determinism.
"""

from __future__ import annotations

from satc.intake.service import (
    add_relationship,
    create_engagement,
    create_person_client,
    next_client_id,
    reconcile_received,
)
from satc.persistence import SATCStore


# ---------------------------------------------------------------------------
# create_person_client — vault + de-identified mart projection
# ---------------------------------------------------------------------------

def test_create_person_client_projects_to_mart_without_raw_pii(tmp_path):
    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id="SATC-009001")
    assert cid == "SATC-009001"

    mart = store.load_mart()
    public = next((p for p in mart.public_clients if p.client_id == cid), None)
    assert public is not None, "the new client must appear in the mart projection"

    # The sensitive legal name lives in the vault, keyed by client_id.
    assert store.names()[cid] == "Dana Reyes"

    # The mart projection masks the TIN — it is non-empty but not the raw SSN.
    assert public.tin_masked, "masked TIN should be present in the projection"
    assert "123-45-6789" not in public.tin_masked
    assert "123456789" not in public.tin_masked


# ---------------------------------------------------------------------------
# next_client_id — opaque handle allocation
# ---------------------------------------------------------------------------

def test_next_client_id_is_valid_and_auto_ids_are_distinct(tmp_path):
    store = SATCStore(tmp_path)

    candidate = next_client_id(store)
    assert candidate.startswith("SATC-")
    suffix = candidate.split("-")[-1]
    assert suffix.isdigit()

    # Creating two clients without explicit ids yields two distinct handles.
    first = create_person_client(store, first_name="A", last_name="One")
    second = create_person_client(store, first_name="B", last_name="Two")
    assert first != second
    assert first.startswith("SATC-") and second.startswith("SATC-")


# ---------------------------------------------------------------------------
# add_relationship — persisted in the mart graph
# ---------------------------------------------------------------------------

def test_add_relationship_persists(tmp_path):
    store = SATCStore(tmp_path)
    create_person_client(store, first_name="Dana", last_name="Reyes",
                         ssn="123-45-6789", client_id="SATC-009001")

    rel = add_relationship(store, from_client_id="SATC-009001", to_client_id="SATC-009002",
                           relationship_type="shareholder", ownership_pct="60")

    persisted = store.load_relationships()
    match = next((r for r in persisted if r.rel_id == rel.rel_id), None)
    assert match is not None
    assert match.from_client_id == "SATC-009001"
    assert match.to_client_id == "SATC-009002"
    assert match.relationship_type == "shareholder"
    assert match.ownership_pct == "60"


# ---------------------------------------------------------------------------
# create_engagement — opens a Requested document per client ask
# ---------------------------------------------------------------------------

def test_create_engagement_opens_requested_docs_and_persists(tmp_path):
    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id="SATC-009001")

    eng = create_engagement(store, client_id=cid, workflow_key="personal_1040_core",
                            due_date="2026-04-15", tax_year=2025,
                            answers={"newSatcClient": "yes"})

    client_tasks = [t for t in eng.tasks if t.audience == "client"]
    assert client_tasks, "the engagement should produce client-facing tasks"
    # Every client-facing task is linked to the document it requested.
    assert all(t.document_id for t in client_tasks)

    mart = store.load_mart()
    requested = [d for d in mart.documents
                 if d.client_id == cid and d.status == "Requested"]
    assert len(requested) == len(client_tasks)

    # The engagement is durably persisted.
    persisted = store.load_intake_engagements()
    assert any(e.engagement_id == eng.engagement_id for e in persisted)

    # Internal-only tasks do not open documents.
    internal_tasks = [t for t in eng.tasks if t.audience != "client"]
    assert all(not t.document_id for t in internal_tasks)


# ---------------------------------------------------------------------------
# reconcile_received — closes the requested -> received loop
# ---------------------------------------------------------------------------

def test_reconcile_received_marks_doc_and_completes_task(tmp_path):
    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id="SATC-009001")
    create_engagement(store, client_id=cid, workflow_key="personal_1040_core",
                      due_date="2026-04-15", tax_year=2025,
                      answers={"newSatcClient": "yes"})

    # Pick a real outstanding request that names ONE form, and reconcile against
    # its doc_type. It used to take `requested[0]`, which is the core-income
    # BUNDLE -- five forms, closed by whichever one arrived first. The point of
    # this test is the Requested -> Received loop and the linked task, so it now
    # exercises that on a request where closing on one document is correct;
    # `test_intake_matching.py` holds the bundle behaviour.
    from satc.intake import matching

    requested = [d for d in store.load_mart().documents
                 if d.client_id == cid and d.status == "Requested"]
    assert requested
    single = [d for d in requested if not matching.is_bundle(str(d.doc_type), d.note)]
    assert single, "no single-form request to test the loop with"
    target_type = single[0].doc_type

    result = reconcile_received(store, client_id=cid, doc_type=target_type)
    assert result is not None
    assert result.status == "Received"

    # Reloading the store shows the document Received and its linked task complete.
    reloaded = SATCStore(tmp_path)
    docs = {d.document_id: d.status for d in reloaded.load_mart().documents}
    assert docs[result.document_id] == "Received"

    linked_tasks = [t for e in reloaded.load_intake_engagements() for t in e.tasks
                    if t.document_id == result.document_id]
    assert linked_tasks, "the received document should be linked to a task"
    assert all(t.completed for t in linked_tasks)


def test_reconcile_received_returns_none_for_unknown_doc_type(tmp_path):
    store = SATCStore(tmp_path)
    cid = create_person_client(store, first_name="Dana", last_name="Reyes",
                               ssn="123-45-6789", client_id="SATC-009001")
    create_engagement(store, client_id=cid, workflow_key="personal_1040_core",
                      due_date="2026-04-15", tax_year=2025,
                      answers={"newSatcClient": "yes"})

    assert reconcile_received(store, client_id=cid, doc_type="nonexistent-zzz") is None


def _one_request(store, *, tax_year=2026, doc_type="1099-INT"):
    from satc.models.mart import DocumentRecord
    mart = store.load_mart()
    mart.documents.append(DocumentRecord(
        document_id="D1", client_id="C1", tax_year=tax_year, doc_type=doc_type,
        status="Requested", note=f"Upload your {doc_type}"))
    store.save_mart(mart)
    return store


def test_the_year_explanation_is_only_given_when_the_year_is_why(tmp_path):
    """It names the request the year blocked — not every request the form
    matches. Without the check it would explain a document that closed fine as
    though something had gone wrong with it."""
    from satc.intake.service import request_missed_on_year
    store = _one_request(SATCStore(tmp_path))
    assert request_missed_on_year(store, client_id="C1", doc_type="1099-INT",
                                  doc_year=2024) == "1099-INT"
    assert request_missed_on_year(store, client_id="C1", doc_type="1099-INT",
                                  doc_year=2026) == "", (
        "the year matched: there is nothing to explain")


def test_a_year_we_could_not_read_is_never_blamed(tmp_path):
    """`wrong_year` is asymmetric on purpose: a year we could not read blocks
    nothing. Telling the firm the year was wrong when we never read one would
    send them looking at a document that is fine.

    This is pinned here rather than guarded in `request_missed_on_year`,
    because a guard there restates `wrong_year`'s rule in a second place and
    mutation testing showed no test could tell the two apart. The behaviour is
    the contract; where it comes from is not."""
    from satc.intake.service import request_missed_on_year
    store = _one_request(SATCStore(tmp_path))
    assert request_missed_on_year(store, client_id="C1", doc_type="1099-INT",
                                  doc_year=None) == ""
