"""The events after the opening pack, and the documents they produce.

FOUR DOCUMENTS COULD NOT BE PRODUCED BY ANY COMMAND A PREPARER CAN RUN. The
delivery letter, the organizer cover, the extension notice and the
disengagement letter each need facts that do not exist when the engagement is
created — a signature deadline, an extended deadline, what was actually
delivered, the date an engagement ended — and nothing collected them. `doctor`
reported the organizer letter blocked on every engagement in the store,
correctly, and there was no way to unblock it.

So the opening pack was a third of the process and the other two thirds had no
front door. Found by opening 303 rendered documents, not by any test — because
every test rendered from a fixture that already carried the answers. These
tests go through the command instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import intake  # noqa: E402
import lifecycle  # noqa: E402

SAMPLES = ROOT / "samples"

ANSWERS = {
    "delivery": {
        "answers": {"signature_deadline": "April 10, 2027", "filing": "efiled",
                    "estimated_payments": "yes"},
        "rows": {"ReturnsDelivered": [{"Return": "Federal Form 1040",
                                       "Detail": "With Schedules A and C"}],
                 "ActionList": [{"Action": "Sign the e-file authorization",
                                 "Detail": "By 10 April"}]},
    },
    "organizer": {
        "answers": {"tax_year": "2027", "materials_deadline": "March 1, 2027",
                    "fee_change": "no",
                    "fee_change_note": "Our fee for 2027 is unchanged."},
        "rows": {"Requested": [{"Category": "Income",
                                "Detail": "Every W-2 and 1099"}]},
    },
    "extension": {
        "answers": {"extended_deadline": "October 15, 2027",
                    "payment_deadline": "April 15, 2027",
                    "materials_deadline": "August 1, 2027",
                    "payment": "yes",
                    "estimated_payment_amount": "$450.00"},
        "rows": {"ExtendedReturns": [{"Return": "Federal Form 1040",
                                      "Detail": "Extended to 15 October"}],
                 "OutstandingItems": [{"Document": "Brokerage 1099-B",
                                       "Detail": "Corrected copy expected"}]},
    },
    "disengagement": {
        "answers": {"effective_date": "June 1, 2027",
                    "records_available_until": "September 1, 2027",
                    "scope_ended": "the preparation of your 2026 federal and "
                                   "Ohio individual income tax returns",
                    "ended_by": "client", "balance": "no"},
        "rows": {"WorkStatus": [{"Work": "2026 federal and Ohio returns",
                                 "Status": "Complete and filed"}],
                 "OpenDeadlines": [{"Obligation": "2027 estimated payments",
                                    "Detail": "Quarterly, from 15 April"}]},
    },
}


@pytest.fixture
def engaged(tmp_path):
    answers = json.loads((SAMPLES / "interview-answers.json").read_text(
        encoding="utf-8"))
    store = tmp_path / "store"
    out = intake.finish(dict(answers), store=store)
    assert out.created, out.reason
    return {"store": store, "ref": out.ref}


def _run(kind, engaged, tmp_path, payload=None):
    f = tmp_path / f"{kind}.json"
    f.write_text(json.dumps(payload or ANSWERS[kind]), encoding="utf-8")
    out = tmp_path / kind
    code = cli.main(["event", "--kind", kind, "--engagement", engaged["ref"],
                     "--store", str(engaged["store"]), "--answers", str(f),
                     "--out", str(out), "--no-pdf"])
    return code, sorted(out.glob("*.html")) if out.exists() else []


# ── the registry ──────────────────────────────────────────────────────────

def test_every_question_fills_something():
    """A question that supplies no field, sets no flag and derives no pair is
    one nobody can act on."""
    for key, ev in lifecycle.load().items():
        for q in ev.questions:
            assert q.get("supplies") or q.get("flag") or q.get("pair"), \
                f"{key}.{q['id']}"


def test_every_event_names_a_real_document():
    for key, ev in lifecycle.load().items():
        assert ev.document in cli.DOCUMENTS, f"{key} -> {ev.document}"


def test_a_booleanised_option_is_refused(tmp_path):
    """YAML 1.1 READS A BARE `yes:` AS A BOOLEAN, so a `pair: { yes: X, no: Y }`
    becomes `{True: X, False: Y}`, never matches the answer a preparer types,
    and leaves BOTH flags false — which is exactly the empty section the pair
    exists to prevent. It cost two of the four documents on the first run."""
    reg = tmp_path / "lifecycle.yaml"
    reg.write_text(
        "events:\n"
        "  thing:\n"
        "    document: delivery-letter\n"
        "    questions:\n"
        "      - id: q\n"
        "        pair: { yes: A, no: B }\n", encoding="utf-8")
    with pytest.raises(lifecycle.LifecycleError, match="BOOLEAN"):
        lifecycle.load(reg)


def test_a_quoted_option_loads(tmp_path):
    reg = tmp_path / "lifecycle.yaml"
    reg.write_text(
        "events:\n"
        "  thing:\n"
        "    document: delivery-letter\n"
        "    questions:\n"
        '      - id: q\n'
        '        pair: { "yes": A, "no": B }\n', encoding="utf-8")
    assert list(lifecycle.load(reg)["thing"].questions[0]["pair"]) == ["yes", "no"]


# ── deriving the fields ───────────────────────────────────────────────────

def test_a_pair_comes_from_one_answer():
    """Two independent booleans can both be false, and when they were, the
    extension notice printed a warning and then nothing at all."""
    got = lifecycle.fields("extension", {"payment": "yes"})
    assert got["PaymentEnclosed"] is True
    assert got["NoPaymentRequired"] is False

    got = lifecycle.fields("extension", {"payment": "no"})
    assert got["PaymentEnclosed"] is False
    assert got["NoPaymentRequired"] is True


def test_a_flag_that_was_never_asked_is_false_not_absent():
    """Absent and false render the same and mean different things, and merge
    can only report what it can see."""
    got = lifecycle.fields("delivery", {})
    assert got["EFiled"] is False and got["PaperFiled"] is False
    assert "EFiled" in got, "an absent flag is a hole the engine cannot see"


def test_a_question_gated_on_another_is_not_asked():
    """"How much should they pay" applies only where a payment is due."""
    got = lifecycle.fields("extension", {"payment": "no",
                                         "estimated_payment_amount": "$450"})
    assert "EstimatedPaymentAmount" not in got


def test_missing_names_what_is_still_needed():
    short = lifecycle.missing("delivery", lifecycle.fields("delivery", {}))
    assert "SignatureDeadline" in short
    assert "ReturnsDelivered" in short, "a required list counts"
    assert "ActionList" not in short, "an optional one does not"


# ── the whole command, on a real engagement ───────────────────────────────

@pytest.mark.parametrize("kind", sorted(ANSWERS))
def test_each_event_produces_its_document(kind, engaged, tmp_path):
    code, made = _run(kind, engaged, tmp_path)
    assert code == 0, kind
    assert len(made) == 1, made


def test_an_incomplete_event_writes_nothing(engaged, tmp_path):
    """A document that cannot be honest is not written, and neither is the
    half-answered event beside it."""
    code, made = _run("delivery", engaged, tmp_path,
                      payload={"answers": {"filing": "efiled"}, "rows": {}})
    assert code == 1
    assert made == []
    assert lifecycle.load_saved(engaged["ref"], "delivery",
                                engaged["store"]) is None


def test_each_event_is_recorded_under_its_own_name(engaged, tmp_path):
    """An engagement can be extended and later disengaged, and the second must
    not overwrite the first."""
    _run("extension", engaged, tmp_path)
    _run("disengagement", engaged, tmp_path)

    assert lifecycle.events_on(engaged["ref"], engaged["store"]) == \
        ["disengagement", "extension"]
    assert lifecycle.load_saved(engaged["ref"], "extension",
                                engaged["store"])["answers"]["payment"] == "yes"


def test_the_answers_are_reused_on_a_second_run(engaged, tmp_path):
    """Re-rendering a delivery letter should not mean re-typing the deadline."""
    _run("delivery", engaged, tmp_path)
    out = tmp_path / "again"
    code = cli.main(["event", "--kind", "delivery",
                     "--engagement", engaged["ref"],
                     "--store", str(engaged["store"]), "--out", str(out),
                     "--no-pdf"])
    assert code == 0
    assert len(sorted(out.glob("*.html"))) == 1


def test_the_delivery_letter_says_what_was_delivered(engaged, tmp_path):
    _, made = _run("delivery", engaged, tmp_path)
    said = made[0].read_text(encoding="utf-8")
    assert "Federal Form 1040" in said
    assert "Sign the e-file authorization" in said
    assert "April 10, 2027" in said


def test_the_extension_notice_says_what_to_pay(engaged, tmp_path):
    """The failure this whole registry exists to stop: a heading warning that
    the payment deadline has not moved, and nothing about the payment."""
    _, made = _run("extension", engaged, tmp_path)
    said = made[0].read_text(encoding="utf-8")
    assert "$450.00" in said
    assert "October 15, 2027" in said


def test_the_disengagement_letter_names_what_ends(engaged, tmp_path):
    _, made = _run("disengagement", engaged, tmp_path)
    said = made[0].read_text(encoding="utf-8")
    assert "2026 federal and Ohio individual income tax returns" in said
    assert "Complete and filed" in said
