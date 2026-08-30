"""The end-of-cycle control: what we said, against what we filed.

Every other check in this repo is a TEST — it asserts a property on a fixture
and runs in CI. This is the suite for a CONTROL: something that runs on real
work, after the work is done, and compares two things nobody was comparing.
The interview's answers were recorded in January; the return was filed in
April; the engagement letter, the fee estimate and the invoice were all written
from January. If the return diverged and nothing said so, three documents in
the client's file are quietly wrong and next year's interview starts from the
wrong place.

The firm asked for it in these words: *"our interview and such is system of
record until proven wrong. we should update the data to match what we file if
required. this should be a control we build at the end of the cycle."*
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import closeout  # noqa: E402
import engagements  # noqa: E402
import intake  # noqa: E402

SAMPLES = ROOT / "samples"

FILED_CLEAN = {
    "filed_form": "1040", "filed_basis": "original", "filed_joint": "yes",
    "filed_dependents": "no", "filed_state_count": 1,
    "filed_locality_count": 1, "filed_k1s_received": 2, "filed_rentals": 1,
    "filed_businesses": 1, "filed_extended": "no", "closeout_note": "",
}


@pytest.fixture
def answers():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


@pytest.fixture
def engaged(answers, tmp_path):
    store = tmp_path / "store"
    out = intake.finish(dict(answers), store=store)
    assert out.created, out.reason
    return {"store": store, "ref": out.ref, "answers": answers}


# ── the registry ──────────────────────────────────────────────────────────

def test_every_question_says_why_it_is_asked():
    """A question nobody can justify is one nobody will answer honestly."""
    for q in closeout.load():
        assert q.get("why"), q["id"]
        assert len(q["why"].split()) >= 6, q["id"]


def test_no_question_asks_for_a_figure():
    """Asking what the tax or the refund was would make this a second set of
    books beside Drake, which is the one thing the firm said not to build."""
    said = " ".join((q["question"] + " " + q["why"]).lower()
                    for q in closeout.load())
    for word in ("refund", "tax due", "balance due", "adjusted gross",
                 "taxable income", "how much"):
        assert word not in said, word


def test_a_partnership_is_not_asked_about_filing_status():
    """A partnership has no filing status and a 1040 issues no K-1s. Asking
    anyway is the filler problem in a different costume: a preparer asked four
    questions that cannot apply learns to answer the set without reading it."""
    partnership = {q["id"] for q in closeout.questions_for("partnership")}
    assert "filed_joint" not in partnership
    assert "filed_dependents" not in partnership
    assert "filed_k1s_issued" in partnership


def test_an_individual_is_not_asked_how_many_k1s_they_issued():
    individual = {q["id"] for q in closeout.questions_for("individual")}
    assert "filed_k1s_issued" not in individual
    assert "filed_k1s_received" in individual


# ── comparison ────────────────────────────────────────────────────────────

def test_a_return_that_matches_the_interview_diverges_nowhere(answers):
    assert closeout.compare(answers, FILED_CLEAN, "individual") == []


def test_a_state_that_appeared_after_the_interview_is_caught(answers):
    """The commonest way a fee estimate turns out short."""
    found = closeout.compare(answers, FILED_CLEAN | {"filed_state_count": 3},
                             "individual")
    assert len(found) == 1
    assert found[0].against == "count_states"
    assert found[0].asked == 1 and found[0].filed == 3


def test_a_marriage_between_the_interview_and_the_filing_is_caught(answers):
    found = closeout.compare(answers, FILED_CLEAN | {"filed_joint": "no"},
                             "individual")
    assert [d.against for d in found] == ["joint_return"]


def test_a_number_typed_as_text_is_not_a_divergence(answers):
    """A count arrives from the interview as an int and from a terminal as a
    string. "1" and 1 are the same answer, and reporting them as a finding is
    how a control teaches people to ignore it."""
    assert closeout.compare(answers, FILED_CLEAN | {"filed_state_count": "1"},
                            "individual") == []


def test_case_is_not_a_divergence(answers):
    assert closeout.compare(answers, FILED_CLEAN | {"filed_joint": "Yes"},
                            "individual") == []


def test_a_list_answer_is_compared_by_its_length(answers):
    """`states` is ["Ohio — resident"] and the close-out asks how many were
    filed."""
    thin = dict(answers)
    del thin["count_states"]
    assert closeout.compare(thin, FILED_CLEAN, "individual") == []
    found = closeout.compare(thin, FILED_CLEAN | {"filed_state_count": 4},
                             "individual")
    assert len(found) == 1


def test_an_unanswered_question_is_not_agreement(answers):
    """SILENTLY TREATING IT AS AGREEMENT would let a half-finished close-out
    read as a clean one, and an absent check reading like a passing one is the
    failure this whole controls layer exists to stop."""
    half = {k: v for k, v in FILED_CLEAN.items() if k != "filed_state_count"}
    assert closeout.compare(answers, half, "individual") == []
    assert "filed_state_count" in closeout.missing(half, "individual")


def test_every_divergence_carries_the_reason_the_question_exists(answers):
    found = closeout.compare(answers, FILED_CLEAN | {"filed_state_count": 3},
                             "individual")
    assert found[0].why and len(found[0].why.split()) >= 6


# ── the sweep, and applying it ────────────────────────────────────────────

def test_an_engagement_nobody_closed_is_reported_not_skipped(engaged):
    """A control that only examines the work somebody remembered to close is a
    control over the diligent, which is not where the problem is."""
    reviewed = closeout.sweep(engaged["store"])
    assert len(reviewed) == 1
    assert reviewed[0].closed is False
    assert reviewed[0].ref == engaged["ref"]


def test_closing_records_what_was_filed(engaged, tmp_path):
    filed = tmp_path / "filed.json"
    filed.write_text(json.dumps(FILED_CLEAN), encoding="utf-8")
    assert cli.main(["close", "--engagement", engaged["ref"],
                     "--store", str(engaged["store"]),
                     "--filed", str(filed)]) == 0

    saved = closeout.load_filed(engaged["ref"], engaged["store"])
    assert saved == FILED_CLEAN


def test_the_whole_cycle_converges(engaged, tmp_path):
    """Not closed -> closed and diverging -> applied -> agrees. The last step
    is the one that matters: a control that reports the same divergence every
    year has not been acted on."""
    store, ref = engaged["store"], engaged["ref"]
    filed = tmp_path / "filed.json"
    filed.write_text(json.dumps(FILED_CLEAN | {"filed_state_count": 2}),
                     encoding="utf-8")

    assert closeout.sweep(store)[0].closed is False
    cli.main(["close", "--engagement", ref, "--store", str(store),
              "--filed", str(filed)])

    before = closeout.sweep(store)[0]
    assert before.closed and len(before.divergences) == 1

    assert cli.main(["reconcile", "--store", str(store), "--apply"]) == 0

    after = closeout.sweep(store)[0]
    assert after.divergences == [], [d.line() for d in after.divergences]


def test_applying_moves_the_answer_and_writes_it_down(engaged, tmp_path):
    """"System of record UNTIL PROVEN WRONG." This is the proving, and the log
    is what makes it evidence rather than a silent edit — next year's
    interview is seeded from these answers."""
    store, ref = engaged["store"], engaged["ref"]
    filed = tmp_path / "filed.json"
    filed.write_text(json.dumps(FILED_CLEAN | {"filed_state_count": 2}),
                     encoding="utf-8")
    cli.main(["close", "--engagement", ref, "--store", str(store),
              "--filed", str(filed)])
    cli.main(["reconcile", "--store", str(store), "--apply"])

    saved = json.loads((engagements._dir(store, ref) / "interview.json")
                       .read_text(encoding="utf-8"))
    assert saved["count_states"] == 2

    log = json.loads((engagements._dir(store, ref) / "reconciled.json")
                     .read_text(encoding="utf-8"))
    assert len(log) == 1
    moved = log[0]["moved"]
    assert len(moved) == 1
    assert moved[0] == {"answer": "count_states", "was": 1, "now": 2,
                        "because": "filed_state_count"}
    assert log[0]["at"].endswith("+00:00")


def test_the_log_is_append_only(engaged, tmp_path):
    """A record you can edit is not evidence."""
    store, ref = engaged["store"], engaged["ref"]
    for count in (2, 3):
        filed = tmp_path / f"filed{count}.json"
        filed.write_text(json.dumps(FILED_CLEAN | {"filed_state_count": count}),
                         encoding="utf-8")
        cli.main(["close", "--engagement", ref, "--store", str(store),
                  "--filed", str(filed)])
        cli.main(["reconcile", "--store", str(store), "--apply"])

    log = json.loads((engagements._dir(store, ref) / "reconciled.json")
                     .read_text(encoding="utf-8"))
    assert len(log) == 2


def test_reconcile_changes_nothing_without_apply(engaged, tmp_path):
    store, ref = engaged["store"], engaged["ref"]
    filed = tmp_path / "filed.json"
    filed.write_text(json.dumps(FILED_CLEAN | {"filed_state_count": 2}),
                     encoding="utf-8")
    cli.main(["close", "--engagement", ref, "--store", str(store),
              "--filed", str(filed)])

    before = (engagements._dir(store, ref) / "interview.json").read_text(encoding="utf-8")
    assert cli.main(["reconcile", "--store", str(store)]) == 0
    assert (engagements._dir(store, ref) / "interview.json").read_text(
        encoding="utf-8") == before
    assert not (engagements._dir(store, ref) / "reconciled.json").exists()


def test_closing_an_engagement_with_no_interview_refuses(tmp_path):
    store = tmp_path / "store"
    (store / "2026-0001").mkdir(parents=True)
    (store / "2026-0001" / "record.json").write_text("{}", encoding="utf-8")
    assert cli.main(["close", "--engagement", "2026-0001",
                     "--store", str(store)]) == 1
