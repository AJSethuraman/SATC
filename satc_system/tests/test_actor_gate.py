"""The actor invariant: a model-produced value can never become a fact.

This is the keystone of the schema reset. A confirmed value is not "a number
that is probably right" — it is *the preparer's own act*, relied on as evidence.
The old gate took the actor as a caller-supplied string whose default asserted a
human, so any in-process caller could record work as the owner's own.

These tests prove the hole is closed, from every direction. Each one is written
to FAIL if the gate is loosened — which is the only kind of check worth having
(doctrine rule 10: prove every check can fail).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from satc.ingest.staging_gate import StagingGate
from satc.models.actor import INTAKE, Actor, ActorRefused, parse_handle, require_human
from satc.models.provenance import Provenance, SourceRef
from satc.models.staging import StagedDocument, StagedField

MODEL = Actor.model("qwen3:8b", "2026-07")


def _gate(*, confidence="HIGH", produced_by=None, status="STAGED"):
    f = StagedField(
        field_id="f1", document_id="d1", client_id="c", tax_year=2024,
        field_path="w2.box1_wages", label="Wages", value_text="145000",
        value_amount=Decimal("145000"), status=status,
        provenance=Provenance(source_kind="SOURCE_DOC", confidence=confidence,
                              source_ref=SourceRef(), produced_by=produced_by))
    g = StagingGate()
    g.add(StagedDocument(document_id="d1", client_id="c", tax_year=2024,
                         doc_type="W-2", fields=[f]))
    return g, f


# --- the actor type itself ---------------------------------------------------

def test_only_a_human_may_confirm():
    assert Actor.owner().may_confirm
    assert not MODEL.may_confirm
    assert not Actor.system("intake").may_confirm
    assert not Actor.imported("csv").may_confirm


def test_a_model_actor_must_name_the_model():
    with pytest.raises(ValueError):
        Actor.model("")


def test_handles_are_stable_and_pii_free():
    assert Actor.owner().handle == "human:owner"
    assert MODEL.handle == "model:qwen3:8b@2026-07"
    assert Actor.system("intake").handle == "system:intake"


def test_a_stored_handle_never_round_trips_into_a_human():
    """Reading history must not be a way to mint a human actor."""
    assert parse_handle("human:owner").is_human          # a real one still reads back
    assert not parse_handle("").is_human
    assert not parse_handle("garbage").is_human
    assert not parse_handle("preparer (UI)").is_human    # the OLD string form
    assert not parse_handle("wizard:owner").is_human     # an invented kind


def test_an_actor_cannot_be_mutated_into_a_different_kind():
    with pytest.raises(Exception):
        MODEL.kind = "human"          # type: ignore[misc]


def test_a_refusal_names_the_right_next_step():
    """Doctrine rule 3: on a small model, a refusal that only says no ends the run."""
    with pytest.raises(ActorRefused) as exc:
        require_human(MODEL, "confirm a staged value")
    message = str(exc.value)
    assert "model:qwen3:8b@2026-07" in message
    assert "propose" in message


# --- the gate refuses --------------------------------------------------------

def test_a_model_cannot_confirm():
    g, f = _gate()
    with pytest.raises(ActorRefused):
        g.confirm("f1", MODEL)
    assert f.status == "STAGED"
    assert f.confirmed_by is None


def test_a_model_cannot_hand_correct():
    """edit() both sets a value AND accepts it — the most powerful operation."""
    g, f = _gate()
    with pytest.raises(ActorRefused):
        g.edit("f1", MODEL, value_text="999999")
    assert f.status == "STAGED"


def test_a_model_cannot_reject_either():
    """Rejecting is a judgment too, and it destroys a value."""
    g, f = _gate()
    with pytest.raises(ActorRefused):
        g.reject("f1", MODEL)
    assert f.status == "STAGED"


def test_a_model_cannot_run_the_auto_confirm_sweep():
    g, _ = _gate()
    with pytest.raises(ActorRefused):
        g.auto_confirm_high(MODEL)


def test_a_system_actor_may_run_the_sweep_but_not_confirm_by_hand():
    """Deterministic code can be read and proven; it is not a model."""
    g, f = _gate()
    assert g.auto_confirm_high(INTAKE) == 1
    assert f.status == "CONFIRMED"

    g2, _ = _gate()
    with pytest.raises(ActorRefused):
        g2.confirm("f1", INTAKE)


def test_the_owner_can_confirm():
    g, f = _gate()
    assert g.confirm("f1", Actor.owner())
    assert f.status == "CONFIRMED"
    assert f.confirmed_by is not None and f.confirmed_by.is_human


# --- model-produced values never auto-confirm --------------------------------

def test_a_model_produced_value_is_never_auto_confirmed():
    """Even at HIGH confidence. Confidence is the signal a small model fakes best."""
    g, f = _gate(confidence="HIGH", produced_by=MODEL)
    assert g.auto_confirm_high(INTAKE) == 0
    assert f.status == "STAGED"


def test_a_model_produced_value_still_reaches_the_review_queue():
    """Blocked from skipping review — not hidden from it."""
    g, f = _gate(confidence="HIGH", produced_by=MODEL)
    g.auto_confirm_high(INTAKE)
    assert f in g.needs_review()


def test_the_owner_may_still_accept_a_model_proposal():
    """The model's route to the mart: propose, and the owner accepts in one click."""
    g, f = _gate(produced_by=MODEL)
    assert g.confirm("f1", Actor.owner())
    assert f.status == "CONFIRMED"


# --- provenance is sticky and transitive -------------------------------------

def test_a_deterministic_pass_cannot_launder_model_output():
    """The taint follows the VALUE, not the reader that last touched it.

    Defining "is this model output?" on the reader is how a model-corrected OCR
    string reaches the gate looking deterministic.
    """
    model_read = Provenance(source_kind="SOURCE_DOC", confidence="HIGH", produced_by=MODEL)
    normalised = model_read.derive(by=INTAKE, note="normalised")
    assert normalised.is_model_produced
    assert normalised.produced_by == MODEL


def test_a_model_touching_a_clean_value_taints_it():
    clean = Provenance(source_kind="SOURCE_DOC", confidence="HIGH", produced_by=INTAKE)
    touched = clean.derive(by=MODEL, note="model corrected")
    assert touched.is_model_produced


def test_a_laundered_value_still_cannot_auto_confirm():
    """The end-to-end version of the two tests above."""
    model_read = Provenance(source_kind="SOURCE_DOC", confidence="HIGH", produced_by=MODEL)
    g, f = _gate()
    f.provenance = model_read.derive(by=INTAKE, note="cleaned up")
    assert g.auto_confirm_high(INTAKE) == 0
    assert f.status == "STAGED"


def test_a_hand_correction_clears_the_taint():
    """The one legitimate way: a human read the document and decided."""
    g, f = _gate(produced_by=MODEL)
    assert g.edit("f1", Actor.owner(), value_text="145030",
                  value_amount=Decimal("145030"))
    assert not f.provenance.is_model_produced
    assert f.provenance.produced_by.is_human
    assert f.provenance.source_kind == "PREPARER_ENTRY"


# --- the app path stamps the actor rather than accepting one -----------------

def test_outside_a_request_the_app_is_not_the_owner():
    """A script, a tool, or a model rung importing STATE gets a system actor.

    This is what makes the gate hold from paths that do not exist yet: nothing
    can *claim* to be the owner, it can only *be* in a live browser request.
    """
    from satc.app.state import acting_actor

    actor = acting_actor()
    assert not actor.is_human
    assert actor.kind == "system"


def test_inside_a_request_the_app_is_the_owner():
    from satc.app.server import create_app
    from satc.app.state import acting_actor

    app = create_app()
    with app.test_request_context("/staging"):
        assert acting_actor().is_human


def test_confirming_outside_a_request_is_refused():
    """The end-to-end proof: STATE.confirm_field() from a script cannot confirm."""
    from satc.app.state import STATE

    STATE.gate = StagingGate()
    g, f = _gate()
    STATE.gate = g
    with pytest.raises(ActorRefused):
        STATE.confirm_field("f1")
    assert f.status == "STAGED"


# --- the invariant must survive persistence ----------------------------------

def test_provenance_survives_a_round_trip_through_sqlite():
    """The hole that made the sticky taint decorative.

    Provenance was rebuilt on load with produced_by=None — and AppState.reload()
    runs after EVERY mutation — so a model-produced value came back from SQLite
    indistinguishable from a preparer entry. The gate held in memory and leaked
    at the database boundary.
    """
    import tempfile
    from decimal import Decimal

    from satc.models.mart import DataMart, LineItem, ReturnRecord
    from satc.models.provenance import Provenance, SourceRef
    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        mart = DataMart()
        mart.returns.append(ReturnRecord(
            return_key="RK", client_id="C", tax_year=2025,
            return_type="1040", jurisdiction="US"))
        mart.line_items.append(LineItem(
            line_item_key="LK", return_key="RK", schedule="1040", line_code="1a",
            label="Wages", amount=Decimal("1000"),
            provenance=Provenance(source_kind="SOURCE_DOC", confidence="LOW",
                                  produced_by=MODEL,
                                  source_ref=SourceRef(document_id="doc-abc"))))
        store.save_mart(mart)

        reloaded = store.load_mart()
        prov = reloaded.line_items[0].provenance
        assert prov.is_model_produced, "the model taint died in SQLite"
        assert prov.produced_by.handle == MODEL.handle
        assert prov.confidence == "LOW", "confidence silently became HIGH on reload"
        assert prov.source_ref.document_id == "doc-abc"


def test_a_stored_human_actor_reads_back_as_human_but_only_as_history():
    import tempfile
    from decimal import Decimal

    from satc.models.mart import DataMart, LineItem, ReturnRecord
    from satc.models.provenance import Provenance
    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        mart = DataMart()
        mart.returns.append(ReturnRecord(return_key="RK", client_id="C", tax_year=2025,
                                         return_type="1040", jurisdiction="US"))
        mart.line_items.append(LineItem(
            line_item_key="LK", return_key="RK", schedule="1040", line_code="1a",
            label="Wages", amount=Decimal("1"),
            provenance=Provenance(source_kind="PREPARER_ENTRY",
                                  produced_by=Actor.owner())))
        store.save_mart(mart)
        prov = store.load_mart().line_items[0].provenance
        assert prov.produced_by.is_human
        assert not prov.is_model_produced


def test_no_client_filename_reaches_the_citation_column():
    """A live PII leak: citation used to be short_source(), which renders
    "Doc <document_id>" — and document_id was the client's own filename, which
    then went into the exported workbook. Citations are tax-law citations."""
    import tempfile
    from decimal import Decimal

    from satc.models.mart import DataMart, LineItem, ReturnRecord
    from satc.models.provenance import Provenance, SourceRef
    from satc.persistence import SATCStore

    with tempfile.TemporaryDirectory() as tmp, SATCStore(tmp) as store:
        mart = DataMart()
        mart.returns.append(ReturnRecord(return_key="RK", client_id="C", tax_year=2025,
                                         return_type="1040", jurisdiction="US"))
        mart.line_items.append(LineItem(
            line_item_key="LK", return_key="RK", schedule="1040", line_code="1a",
            label="Wages", amount=Decimal("1"),
            provenance=Provenance(
                source_kind="SOURCE_DOC",
                source_ref=SourceRef(document_id="Maplewood_Jordan_W2_2024.pdf"))))
        store.save_mart(mart)
        row = next(store.mart.execute("SELECT citation FROM line_items"))
        assert "Maplewood" not in (row["citation"] or "")
        assert "Jordan" not in (row["citation"] or "")


def test_the_auto_confirm_sweep_has_no_defaulted_actor():
    """The last place a caller could be believed by omission."""
    import inspect

    sig = inspect.signature(StagingGate.auto_confirm_high)
    assert sig.parameters["by"].default is inspect.Parameter.empty


# --- the only automatic durable write is gated too ---------------------------

def _store_with_request(tmp):
    """A store holding one outstanding W-2 request."""
    from datetime import date

    from satc.models.evidence import RequestedItem
    from satc.persistence import SATCStore

    store = SATCStore(tmp)
    mart = store.load_mart()
    mart.requested_items.append(RequestedItem(
        request_id="req-1", client_id="C", tax_year=2025, doc_type="W-2",
        request_text="Your W-2 from each employer", blocking="blocking",
        requested_at=date.today()))
    store.save_mart(mart)
    return store


def test_a_model_classified_arrival_cannot_close_a_request():
    """reconcile_received is the ONLY automatic durable write in the app, and it
    was reachable from the vision rung with no actor and no check."""
    import tempfile

    from satc.intake.service import reconcile_received

    with tempfile.TemporaryDirectory() as tmp, _store_with_request(tmp) as store:
        matched = reconcile_received(store, client_id="C", doc_type="W-2",
                                     classified_by=Actor.model("vision"))
        assert matched is None
        still = store.load_requested_items("C")[0]
        assert still.is_open, "a model closed a client request"


def test_a_deterministic_classification_still_closes_the_request():
    """The gate must not break the loop for the rungs that can be proven."""
    import tempfile

    from satc.intake.service import reconcile_received

    with tempfile.TemporaryDirectory() as tmp, _store_with_request(tmp) as store:
        matched = reconcile_received(store, client_id="C", doc_type="W-2",
                                     classified_by=Actor.system("classifier:text"))
        assert matched is not None
        assert not store.load_requested_items("C")[0].is_open


def test_the_model_still_gets_to_point_at_the_request():
    """Propose, never dispose: the owner closes it in one click."""
    import tempfile

    from satc.intake.service import find_match

    with tempfile.TemporaryDirectory() as tmp, _store_with_request(tmp) as store:
        likely = find_match(store, client_id="C", doc_type="W-2")
        assert likely is not None and likely.doc_type == "W-2"
        assert store.load_requested_items("C")[0].is_open   # read-only


def test_only_the_vision_rung_counts_as_a_model():
    """Tesseract OCR and the text layer are deterministic — they can be proven."""
    from satc.ingest.classify import Classification

    def c(method):
        return Classification(key="w2", label="W-2", code="W-2",
                              confidence="HIGH", method=method, evidence="")

    assert c("vision").is_model_classified
    for deterministic in ("form fields", "text", "filename", "ocr"):
        assert not c(deterministic).is_model_classified, deterministic
