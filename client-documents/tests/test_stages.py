"""Where an engagement has got to, derived rather than declared.

THE TESTS THAT EXIST AND THE ONES THAT DID NOT. `test_screens.py` covers how
the bar is DRAWN -- that it never prints a count, that a step nobody can tell
about is not drawn as undone. Nothing covered whether a mark LIGHTS from the
evidence it claims, which is the whole point of the module: `PROOF` promises
each step names a file on disk, and a promise with no test is a claim.

Every case here builds the evidence the way the software writes it and then
asks `reached`. The one thing deliberately not done is to build the store by
calling `stages` itself -- a fixture that agrees with the code proves only
that the code agrees with itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import stages  # noqa: E402

REF = "2027-0114"


def _engagement(tmp_path: Path, ref: str = REF) -> Path:
    """An engagement folder with a record in it and nothing else done."""
    folder = tmp_path / ref
    folder.mkdir(parents=True)
    (folder / "record.json").write_text(
        json.dumps({"EngagementRef": ref, "ReturnType": "individual"}),
        encoding="utf-8")
    return tmp_path


def _answers(k: dict) -> dict:
    return {s.key: s.reached for s in k}


def _at(store: Path, ref: str = REF) -> dict:
    return _answers(stages.reached(ref, store))


# ── nothing is lit for free ───────────────────────────────────────────────

def test_a_new_engagement_has_reached_nothing():
    """Every mark starts unlit. A bar that lights a step on an empty folder
    is telling somebody work has happened that has not."""
    import tempfile
    store = _engagement(Path(tempfile.mkdtemp()))
    at = _at(store)
    assert at["sitting"] is False
    assert at["packed"] is False
    assert at["billed"] is False
    assert at["paid"] is False
    assert at["closed"] is False


def test_every_step_gets_an_answer(tmp_path):
    """Seven steps, seven answers. A key `reached` forgot would come back
    missing rather than false, and the screen would draw a gap."""
    store = _engagement(tmp_path)
    got = stages.reached(REF, store)
    assert [s.key for s in got] == [k for k, _ in stages.STEPS]
    assert all(s.name and s.why for s in got)


# ── each mark, from its own evidence ───────────────────────────────────────

def test_the_sitting_lights_from_the_answers_saved_with_the_record(tmp_path):
    store = _engagement(tmp_path)
    assert _at(store)["sitting"] is False
    (store / REF / "interview.json").write_text("{}", encoding="utf-8")
    assert _at(store)["sitting"] is True


def test_the_pack_lights_from_a_manifest_this_software_wrote(tmp_path):
    """A FOLDER IS NOT A PACK. `sending.build` writes the manifest last, so a
    half-written pack -- or a folder somebody made by hand -- does not count."""
    store = _engagement(tmp_path)
    (store / REF / "pack").mkdir()
    (store / REF / "pack" / "letter.html").write_text("x", encoding="utf-8")
    assert _at(store)["packed"] is False, "a folder of files passed as a pack"
    (store / REF / "pack" / "MANIFEST.json").write_text("{}", encoding="utf-8")
    assert _at(store)["packed"] is True


def test_sent_lights_only_from_a_send_being_written_down(tmp_path):
    """Recorded, not inferred. Building a pack is not sending one -- the two
    are separate marks precisely because a pack can sit built for a week."""
    store = _engagement(tmp_path)
    log = store / REF / "signatures.json"
    log.write_text(json.dumps([{"kind": "signed", "when": "2027-03-01"}]),
                   encoding="utf-8")
    assert _at(store)["sent"] is False, "a signature counted as a send"
    log.write_text(json.dumps([{"kind": "signed", "when": "2027-03-01"},
                               {"kind": "sent", "when": "2027-03-02"}]),
                   encoding="utf-8")
    assert _at(store)["sent"] is True


def test_billed_lights_from_an_invoice_being_raised(tmp_path):
    store = _engagement(tmp_path)
    assert _at(store)["billed"] is False
    bills = store / REF / "invoices"
    bills.mkdir()
    (bills / "2027-0001.json").write_text(
        json.dumps({"InvoiceNumber": "2027-0001", "AmountDue": "$645.00"}),
        encoding="utf-8")
    assert _at(store)["billed"] is True


def test_closed_lights_from_the_close_out(tmp_path):
    store = _engagement(tmp_path)
    assert _at(store)["closed"] is False
    (store / REF / "closeout.json").write_text("{}", encoding="utf-8")
    assert _at(store)["closed"] is True


# ── paid is the one with a trap in it ─────────────────────────────────────

def test_paid_needs_every_bill_settled_not_merely_one(tmp_path):
    """An engagement can carry several invoices. Lighting `paid` off any one
    of them tells the firm they have been paid for work they have not."""
    store = _engagement(tmp_path)
    bills = store / REF / "invoices"
    bills.mkdir()
    (bills / "2027-0001.json").write_text(
        json.dumps({"InvoiceNumber": "2027-0001", "AmountDue": "$645.00",
                    "SettledOn": "2027-03-04"}), encoding="utf-8")
    assert _at(store)["paid"] is True

    (bills / "2027-0002.json").write_text(
        json.dumps({"InvoiceNumber": "2027-0002", "AmountDue": "$250.00"}),
        encoding="utf-8")
    assert _at(store)["paid"] is False, "one unpaid bill still read as paid"


def test_an_engagement_with_no_bill_is_not_paid(tmp_path):
    """`all([])` IS TRUE, which would light `paid` on every engagement nobody
    had billed yet -- the emptiest possible way to claim money arrived."""
    store = _engagement(tmp_path)
    (store / REF / "invoices").mkdir()
    assert _at(store)["paid"] is False


# ── cannot tell is a third answer ─────────────────────────────────────────

def test_signed_says_it_cannot_tell_rather_than_guessing_no(tmp_path):
    """The census reads signature lines out of the templates. Pointed at a
    directory with no templates in it, the honest answer is that we do not
    know -- not that nobody has signed."""
    store = _engagement(tmp_path)
    got = stages.reached(REF, store, template_dir=tmp_path / "not-here")
    signed = next(s for s in got if s.key == "signed")
    assert signed.reached is None
    assert stages.unknown(got) == [signed]
    assert signed not in stages.lit(got)


# ── a broken file must not take the screen down ───────────────────────────

def test_one_unreadable_invoice_does_not_break_the_bar(tmp_path):
    """A stage bar is not a control. A screen that fails because one invoice
    file is malformed is worse than a screen with one mark unlit."""
    store = _engagement(tmp_path)
    bills = store / REF / "invoices"
    bills.mkdir()
    (bills / "2027-0001.json").write_text("{ not json", encoding="utf-8")
    got = stages.reached(REF, store)
    assert len(got) == len(stages.STEPS)


def test_a_collaborator_that_raises_costs_one_mark_not_the_page(monkeypatch,
                                                                tmp_path):
    """THE FIRST VERSION OF THIS TEST PROVED NOTHING. It wrote malformed JSON
    into an invoice and asserted the bar survived -- but `invoicing.issued_for`
    already swallows a bad file itself, so the exception never reached the
    guard here, and deleting the guard left the test green. A mutant found it.

    So this raises from the collaborator, which is the failure the guard is
    actually for: something changes underneath, and one mark goes dark rather
    than the whole screen.
    """
    import invoicing

    def boom(*args, **kwargs):
        raise RuntimeError("the invoice store moved")

    monkeypatch.setattr(invoicing, "issued_for", boom)
    got = stages.reached(REF, _engagement(tmp_path))
    assert len(got) == len(stages.STEPS)
    at = {s.key: s.reached for s in got}
    assert at["billed"] is False and at["paid"] is False
    assert at["closed"] is False, "the steps after the failure were skipped"


def test_an_engagement_that_does_not_exist_still_answers(tmp_path):
    """Asked about a reference with no folder, every mark is unlit and
    nothing raises -- the listing draws a row per engagement and one bad
    reference must not empty the page."""
    got = stages.reached(REF, tmp_path)
    assert len(got) == len(stages.STEPS)
    assert stages.lit(got) == []


# ── the helpers say what they are called ──────────────────────────────────

def test_lit_and_unknown_split_the_three_answers(tmp_path):
    steps = [stages.Step("a", "a", True, "x"),
             stages.Step("b", "b", False, "x"),
             stages.Step("c", "c", None, "x")]
    assert [s.key for s in stages.lit(steps)] == ["a"]
    assert [s.key for s in stages.unknown(steps)] == ["c"]
