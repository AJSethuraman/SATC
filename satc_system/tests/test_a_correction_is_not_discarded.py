"""A correction that is not a number is refused, not absorbed.

THE DEFECT, found by walking the product on 5 September 2026. `StagingGate.edit`
set `confirmed_value_amount = value_amount` unconditionally, so a correction that
would not parse stored `None` -- and `StagedField.effective_amount()` then fell
back to `self.value_amount`, the machine's original read:

    def effective_amount(self):
        if self.is_trusted and self.confirmed_value_amount is not None:
            return self.confirmed_value_amount
        return self.value_amount          # <- the machine's number, silently

The row went on displaying the typed text as `CONFIRMED / human:owner`, with the
machine's HIGH confidence badge still beside it, while the workpaper carried the
number the preparer believed they had replaced.

Measured on the screen, both ways, before the fix:

    Box 1 typed as `90000.00`      -> workpaper Wages 148,150.00   (edit used)
    Box 1 typed as `not a number`  -> workpaper Wages 150,550.00   (edit ignored)

This is the worst shape a data defect can take: the record and the display
disagree, and the display is the reassuring one.

WHY THE TEST IS NARROW. Only a field the reader ALREADY got a number out of
refuses text. A field it could not read may legitimately take a word -- `Box 15 -
State` wants `OH` -- and a blanket rule would block the correction that matters
most, on exactly the rows a human is there to fix.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.models.actor import Actor
from satc.models.provenance import Provenance
from satc.models.staging import StagedDocument, StagedField


@pytest.fixture()
def client():
    return create_app().test_client()


def _gate_with(amount, *, field_id="doc1:w2.box1_wages", label="Box 1 - Wages"):
    """One staged W-2 wage field, read by the machine as ``amount``."""
    from satc.ingest import StagingGate

    prov = Provenance(source_kind="SOURCE_DOC", confidence="HIGH", extractor="test")
    f = StagedField(field_id=field_id, document_id="doc1", client_id="SATC-000999",
                    tax_year=2025, field_path="w2.box1_wages", label=label,
                    value_text=str(amount) if amount is not None else "",
                    provenance=prov, value_amount=amount)
    doc = StagedDocument(document_id="doc1", client_id="SATC-000999", tax_year=2025,
                         doc_type="W-2", fields=[f])
    return StagingGate().add(doc), f


def test_a_number_is_still_taken():
    """The everyday case has to keep working, or the guard is worse than the bug."""
    gate, f = _gate_with(Decimal("92400.00"))
    assert gate.edit(f.field_id, Actor.owner(), value_text="90000.00",
                     value_amount=Decimal("90000.00")) is True
    assert f.effective_amount() == Decimal("90000.00")


def test_text_over_a_figure_is_refused():
    """THE DEFECT. `parse_money` returns None, and the gate must not absorb it."""
    gate, f = _gate_with(Decimal("92400.00"))
    assert gate.edit(f.field_id, Actor.owner(), value_text="not a number",
                     value_amount=None) is False


def test_the_refused_correction_leaves_no_trace_of_itself():
    """Refusing has to leave the row exactly as it was.

    A half-applied refusal is worse than the original defect: the text would show
    the preparer's value and the amount the machine's, which is the very
    disagreement this exists to stop.
    """
    gate, f = _gate_with(Decimal("92400.00"))
    gate.edit(f.field_id, Actor.owner(), value_text="not a number", value_amount=None)

    assert f.confirmed_value_text == "", "the refused text was stored anyway"
    assert f.effective_amount() == Decimal("92400.00")
    assert f.status != "CONFIRMED", "a refused correction confirmed the row"


def test_a_field_the_reader_could_not_read_still_takes_a_word():
    """`Box 15 - State` wants `OH`, and the walk found `income tax` sitting in it.

    The reader got no number, so there is nothing for a correction to contradict
    and text is the right answer.
    """
    gate, f = _gate_with(None, field_id="doc1:w2.box15_state", label="Box 15 - State")
    assert gate.edit(f.field_id, Actor.owner(), value_text="OH", value_amount=None) is True
    assert f.effective_text() == "OH"


def test_the_screen_says_what_it_refused_and_what_would_post(client):
    """Silence here is the whole defect. The message must name both numbers."""
    from satc.app.state import STATE

    gate, f = _gate_with(Decimal("92400.00"))
    STATE.gate = gate

    r = client.post(f"/staging/{f.field_id}/edit", data={"value": "not a number"})
    body = r.get_data(as_text=True)

    assert r.status_code == 200, "a refusal must not redirect the message away"
    assert "is not an amount" in body
    assert "92400" in body, "it did not say which figure would post instead"
    assert "Nothing was changed" in body


def test_every_door_meets_the_guard_not_just_the_one_that_was_walked():
    """The guard is in the GATE, not in the route.

    Putting it in the view would have protected the one door the walk happened to
    use and left `edit_field`'s other callers free to do the thing that was found.

    Driven through a request context because that is what makes the caller the
    owner: `principals.py` treats no-role-and-no-request as `headless`, and
    `require_human` refuses a hand-correction from one outright -- a second,
    stronger guard that this test is not about.
    """
    gate, f = _gate_with(Decimal("92400.00"))
    state = AppState()
    state.gate = gate

    with create_app().test_request_context("/"):
        problem = state.edit_field(f.field_id, "not a number")

    assert problem, "edit_field reported success on a refused correction"
    assert "is not an amount" in problem
    assert f.effective_amount() == Decimal("92400.00")
