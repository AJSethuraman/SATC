"""What we ask a client to send, and the bug that hid for the whole project.

Until 26 August 2026 nothing built `RequestList`. Every onboarding letter
promised "below is everything we need to start your work" and then listed
nothing — and nothing complained, because an `[[EACH]]` over an empty list
leaves no token behind for the strict check to catch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import intake  # noqa: E402
import pricing  # noqa: E402
import requests  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture
def answers():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


def _docs(answers):
    return [r["Document"] for r in requests.for_answers(answers)]


# ── the bug ───────────────────────────────────────────────────────────────

def test_the_record_carries_a_request_list_at_all():
    """The regression that matters. `compose_record` built no RequestList, so
    the onboarding letter in every signing pack went out empty."""
    record = intake.compose_record(
        json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8")))
    assert record["RequestList"], "the onboarding letter would list nothing"
    assert all(r["Document"] for r in record["RequestList"])


def test_everybody_is_asked_for_the_basics():
    """Ungated entries apply to every client. If these ever stop appearing,
    the registry has lost its unconditional rows and every letter is thin.

    "The signed engagement letter" WAS the first thing asserted here, until
    the firm removed it on 26 August 2026: "they dont send it to us - it would
    be sent automatically via encyro". A list headed "What to send us" cannot
    carry something the client never sends. The rule this test guards is
    unchanged; only the example moved, and it is now checked against three
    rows rather than one so a single removal cannot hollow it out again.
    """
    for extra in ({}, {"federal_schedules": ["A", "C", "D", "E1", "E2", "F"]}):
        docs = _docs({"federal_form": "1040", **extra})
        assert "Every W-2 for the year" in docs
        assert "Photo ID" in docs
        assert "The Social Security number for everyone on the return" in docs


def test_a_client_with_nothing_still_gets_a_list():
    assert _docs({"federal_form": "1040"})


# ── it asks for what is on the return ─────────────────────────────────────

@pytest.mark.parametrize("schedule,wanted", [
    ("D", "Your brokerage statements"),
    ("E1", "Rental income and expenses for each property"),
    ("E2", "Each K-1 you received"),
    ("C", "Your business income and expenses"),
    ("F", "Farm income and expenses"),
    ("A", "Your itemized deduction records"),
])
def test_each_schedule_asks_for_its_own_records(schedule, wanted):
    assert wanted in _docs({"federal_form": "1040", "federal_schedules": [schedule]})
    assert wanted not in _docs({"federal_form": "1040", "federal_schedules": []})


def test_a_ticked_schedule_with_no_count_is_still_asked_for():
    """The same trap the package gates were designed around. A client who
    ticks the rentals schedule and leaves the number blank still has rentals
    and still needs to send rental records."""
    assert "Rental income and expenses for each property" in _docs(
        {"federal_form": "1040", "federal_schedules": ["E1"]})


def test_a_multi_select_answer_is_matched_by_membership():
    """`answer_is` compares equality, so pointing it at a multi-select
    silently never matches — worse than an error, because the gate looks right
    and simply never fires. `answer_includes` was added for exactly this."""
    docs = _docs({"federal_form": "1040", "extra_forms": ["marketplace", "hsa"]})
    assert "Form 1095-A" in docs
    assert "The closing statement from the sale of your home" not in docs


def test_answer_includes_handles_a_comma_string_too():
    gate = {"answer_includes": {"extra_forms": "hsa"}}
    assert pricing.gate_holds(gate, {"extra_forms": "marketplace, hsa"})
    assert not pricing.gate_holds(gate, {"extra_forms": "marketplace"})


# ── order and refusals ────────────────────────────────────────────────────

def test_the_order_is_the_registry_s_not_the_answers(answers):
    """Two clients with the same return get the same letter, in one order.

    The order is the REGISTRY's, so a client who happens to have answered in a
    different sequence does not get a differently-ordered letter. What sits
    first changed on 26 August 2026 when the engagement-letter row was
    removed; that it is stable is the property under test, not which row wins.
    """
    docs = _docs(answers)
    assert docs[0] == "Every W-2 for the year"
    reordered = dict(answers)
    reordered["federal_schedules"] = list(reversed(answers["federal_schedules"]))
    assert _docs(reordered) == docs


def test_an_entry_with_no_document_refuses():
    """It would print as a blank bullet on a client's letter."""
    with pytest.raises(requests.RequestError) as exc:
        requests.for_answers({}, entries=[{"detail": "no document named"}])
    assert "blank bullet" in str(exc.value)


def test_a_registry_that_applies_to_nobody_refuses():
    with pytest.raises(requests.RequestError) as exc:
        requests.for_answers({}, entries=[
            {"document": "Something", "when": {"schedules_any": ["Z"]}}])
    assert "asked of everybody" in str(exc.value)


def test_every_gate_in_the_registry_is_one_the_engine_knows():
    """A misspelled operator would never fire, and a request that never fires
    is a document nobody is asked for."""
    for i, entry in enumerate(requests._load(), 1):
        gate = entry.get("when")
        if gate is not None:
            pricing.gate_holds(gate, {}, f"document-requests[{i}]")
