"""The gates, and the guarantee that every front door goes through them.

The rule this file defends: **one engine, two front doors.** A human clicks
through the web UI, automation calls the CLI or `intake` directly, and both
pass the same controls. A control that lives in one front door is a control the
other silently skips.

That is not hypothetical. Every gate below used to live inside `cli._finish`,
so anything driving the interview any other way got none of them -- a HARD NO
would not have stopped an engagement, `decision: no` would still have created
one, and the record would have been missing the fields every document needs.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engagements  # noqa: E402
import intake  # noqa: E402
import interview as iv  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture
def answers():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


@pytest.fixture
def priced():
    return SAMPLES / "fee-schedule-example.yaml"


# ── the gates ─────────────────────────────────────────────────────────────

def test_a_hard_no_creates_nothing(answers, tmp_path, priced):
    answers["red_flags"] = ["assurance_needed"]
    out = intake.finish(answers, store=tmp_path, fee_schedule=priced)
    assert out.status == "refused"
    assert out.ref is None
    assert list(tmp_path.iterdir()) == [], "a refusal must not touch the store"


def test_a_hard_no_reports_which_one(answers, tmp_path, priced):
    answers["red_flags"] = ["assurance_needed", "missing_records"]
    out = intake.finish(answers, store=tmp_path, fee_schedule=priced)
    assert out.blockers == ["Needs assurance work — HARD NO"], (
        "only the HARD NO options are blockers; 'missing records' is a note"
    )


def test_a_hard_no_exits_nonzero(answers, tmp_path, priced):
    """So a script calling this cannot carry on as though it worked."""
    answers["red_flags"] = ["assurance_needed"]
    assert intake.finish(answers, store=tmp_path, fee_schedule=priced).exit_code == 1


def test_an_override_creates_but_records_that_it_was_overridden(answers, tmp_path, priced):
    """A flag that can be set silently is a flag that means nothing."""
    answers["red_flags"] = ["assurance_needed"]
    out = intake.finish(answers, store=tmp_path, fee_schedule=priced,
                        override_hard_no=True)
    assert out.created and out.overridden and out.blockers


def test_a_decision_that_is_not_yes_creates_nothing(answers, tmp_path, priced):
    for decision in ("no", "undecided", None):
        answers["decision"] = decision
        out = intake.finish(answers, store=tmp_path, fee_schedule=priced)
        assert out.status == "declined"
        assert list(tmp_path.iterdir()) == []


def test_declining_work_is_not_a_failure(answers, tmp_path, priced):
    """Exit 0: deciding not to take a client is the interview working."""
    answers["decision"] = "no"
    assert intake.finish(answers, store=tmp_path, fee_schedule=priced).exit_code == 0


def test_a_hard_no_is_refused_even_when_the_decision_says_yes(answers, tmp_path, priced):
    """Order matters. A HARD NO is not a judgement call, so it is not put to
    one -- it is checked before the decision is consulted at all."""
    answers["decision"] = "yes"
    answers["red_flags"] = ["assurance_needed"]
    assert intake.finish(answers, store=tmp_path, fee_schedule=priced).status == "refused"


def test_an_unpriceable_schedule_leaves_no_half_made_engagement(answers, tmp_path):
    """Pricing runs before the store is touched."""
    answers["federal_form"] = "990"          # no base fee exists for it
    out = intake.finish(answers, store=tmp_path, fee_schedule=None)
    assert out.status == "error"
    assert list(tmp_path.iterdir()) == []


# ── the record ────────────────────────────────────────────────────────────

def test_the_record_carries_what_every_document_needs(answers):
    """These four were composed inside the CLI. A caller that skipped it got a
    record that could not render."""
    record = intake.compose_record(answers, today=date(2026, 8, 22))
    for key in ("LetterDate", "_season", "_return_type", "_billable_counts"):
        assert key in record, f"{key} missing -- documents depend on it"
    assert record["LetterDate"] == "August 22, 2026"


@pytest.mark.parametrize("form,expected", [
    ("1040", "individual"), ("1120S", "s_corp"),
    ("1065", "partnership"), ("1120", "c_corp"),
])
def test_the_federal_form_picks_the_engagement_kind(answers, form, expected):
    """It decides which opening package the client gets, so a wrong mapping is
    a wrong letter, not a wrong label."""
    answers["federal_form"] = form
    assert intake.compose_record(answers)["_return_type"] == expected


def test_a_created_engagement_is_priced(answers, tmp_path, priced):
    out = intake.finish(answers, store=tmp_path, fee_schedule=priced)
    assert out.created
    assert out.record["EstimateTotal"] == "$1,225.00"
    assert out.record["LineItems"]


def test_composing_a_record_creates_no_engagement(answers, tmp_path):
    """A UI has to be able to show what a record WOULD be before committing."""
    intake.compose_record(answers)
    assert list(tmp_path.iterdir()) == []


# ── one engine, two front doors ───────────────────────────────────────────

def test_the_cli_decides_nothing_of_its_own(answers, tmp_path, priced):
    """The guard on the whole arrangement.

    `cli._finish` is a renderer over the outcome. If a gate reappears there,
    every other front door has quietly lost it -- so the CLI's exit code must
    be exactly what the core decided, with no logic of its own in between.
    """
    import argparse
    import cli

    for flags, expected in (
        ({"red_flags": ["assurance_needed"]}, "refused"),
        ({"decision": "no"}, "declined"),
        ({}, "created"),
    ):
        a = dict(answers) | flags
        core = intake.finish(a, store=tmp_path / f"core-{expected}",
                             fee_schedule=priced)
        session = iv.Interview(answers=a)
        args = argparse.Namespace(store=str(tmp_path / f"cli-{expected}"),
                                  ref=None, fee_schedule=priced,
                                  override_hard_no=False)
        assert cli._finish(session, args) == core.exit_code, (
            f"the CLI and the core disagree about {expected!r}"
        )
        assert core.status == expected


# ── review flags: not blockers, not derivations ───────────────────────────

def test_more_rentals_than_local_returns_is_flagged(answers, tmp_path, priced):
    """The firm's ruling of 25 August 2026: warn, do not derive.

    Rental income is often taxed by the municipality the property sits in, so
    four rentals and one local return is worth a preparer's eye. It is not
    worth a derivation: townships levy no income tax, an out-of-state rental
    owes nothing to an Ohio city, and deriving the count would quietly bill
    for returns nobody has to file.
    """
    a = dict(answers) | {"count_rentals": 4, "count_localities": 1}
    out = intake.finish(a, store=tmp_path, fee_schedule=priced)
    assert out.created, "a review flag must not stop an engagement"
    assert len(out.flags) == 1
    assert "4 rental properties but 1 local return" in out.flags[0]


def test_a_flag_changes_no_price(answers, tmp_path, priced):
    """The whole point of warning instead of deriving."""
    a = dict(answers) | {"count_rentals": 4, "count_localities": 1}
    b = dict(a)
    flagged = intake.finish(a, store=tmp_path / "a", fee_schedule=priced)
    assert flagged.flags
    assert flagged.record["EstimateTotal"] == intake.finish(
        b, store=tmp_path / "b", fee_schedule=priced).record["EstimateTotal"]


def test_a_flag_never_reaches_a_client_document(answers, tmp_path, priced):
    """Preparer-facing means preparer-facing.

    The flag says the firm may have missed a filing. On a client's own
    estimate that reads as either an accusation or an admission, and it is
    neither -- it is a note to look.
    """
    a = dict(answers) | {"count_rentals": 4, "count_localities": 1}
    out = intake.finish(a, store=tmp_path, fee_schedule=priced)
    blob = json.dumps(out.record)
    assert "local return" not in blob
    assert not any(k.lower().startswith("flag") for k in out.record)


def test_a_flag_is_raised_even_when_the_work_is_refused(answers, tmp_path, priced):
    """A flag that only appears when everything else went well is a flag
    nobody sees on the day it matters."""
    a = dict(answers) | {"count_rentals": 4, "count_localities": 1,
                         "red_flags": ["assurance_needed"]}
    out = intake.finish(a, store=tmp_path, fee_schedule=priced)
    assert out.status == "refused"
    assert out.flags


def test_an_unreadable_count_does_not_raise_a_flag_or_an_error(answers, tmp_path, priced):
    """`pricing._count` refuses a bool because billing one is a wrong invoice.
    Here a bad answer should not stop a review note being considered, so it
    falls out of the comparison instead of stopping the interview."""
    a = dict(answers) | {"count_rentals": True, "count_localities": None}
    assert intake.finish(a, store=tmp_path, fee_schedule=priced).flags == []


def test_the_web_front_door_shows_the_same_flags(answers, tmp_path, priced):
    """One engine, two front doors -- including for the things that do not
    block. A note the CLI prints and the web page swallows is a note that
    depends on which door somebody walked through."""
    a = dict(answers) | {"count_rentals": 4, "count_localities": 1}
    out = intake.finish(a, store=tmp_path, fee_schedule=priced)

    import web
    body = web.outcome_body("sid", out)
    assert "Worth a look before this is quoted" in body
    assert "4 rental properties but 1 local return" in body


def test_every_gate_lives_in_the_core_not_the_cli():
    """Read the CLI's own source. A gate written here again is the failure
    mode this whole module exists to prevent."""
    src = (ROOT / "cli.py").read_text(encoding="utf-8")
    finish = src[src.index("def _finish("):src.index("def cmd_engagements(")]
    for smell in ("hard_no()", "'yes'", "engagements.create(",
                  "pricing.price(", "iv.compose(", "review_flags("):
        assert smell not in finish, (
            f"cli._finish contains {smell!r} -- that decision belongs in "
            f"intake.finish, or the web UI will not enforce it"
        )
