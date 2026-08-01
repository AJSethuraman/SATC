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
