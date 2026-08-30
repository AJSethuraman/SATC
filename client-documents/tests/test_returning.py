"""The returning client: last year's answers shown back for confirmation.

The firm chose this over building an organizer, and gave the reason in their
own words: *"we are not copying out of drake - drake is only system of record
for info. but our interview and such is system of record until proven wrong."*

A returning client does not need last year's FIGURES typed back at them. They
need last year's ANSWERS shown back, plus the events that move a return —
because until this landed, nothing anywhere asked whether anything had changed.

The claim under test throughout: **carried is never assumed.** Every carried
answer is still asked, offered as last year's claim exactly the way a website
lead's answer is offered. A carried answer that answered itself would be an
assumption wearing a confirmation's clothes.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import intake  # noqa: E402
import interview as iv  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture
def prior():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


# ── what survives a year ──────────────────────────────────────────────────

def test_who_they_are_carries(prior):
    carried, _ = iv.carry_forward(prior)
    for key in ("client_full_name", "client_address1", "client_city",
                "client_state", "client_zip", "client_email"):
        assert key in carried, key


def test_what_they_file_carries(prior):
    carried, _ = iv.carry_forward(prior)
    assert carried["federal_form"] == prior["federal_form"]


def test_the_year_itself_does_not_carry(prior):
    carried, dropped = iv.carry_forward(prior)
    assert "tax_year" not in carried
    assert "tax_year" in dropped


def test_filing_status_does_not_carry(prior):
    """A marriage or a divorce is exactly what the change questions ask about.
    Carrying last year's filing status would answer the question this whole
    feature exists to ask."""
    carried, dropped = iv.carry_forward(prior)
    assert "joint_return" not in carried
    assert "joint_return" in dropped


def test_the_predecessor_does_not_carry(prior):
    """We are the prior firm now."""
    carried, _ = iv.carry_forward(prior)
    assert "prior_firm" not in carried
    assert "prior_firm_name" not in carried


def test_the_decision_does_not_carry(prior):
    """Taking the work is decided again every year."""
    carried, _ = iv.carry_forward(prior)
    assert "decision" not in carried


def test_no_count_carries(prior):
    """A count is a fact about ONE YEAR. Carrying one would be inventing this
    year's return out of last year's."""
    carried, _ = iv.carry_forward(prior)
    counts = [k for k in carried if k.startswith("count_")]
    assert counts == [], counts


def test_every_dropped_answer_says_why():
    """"Why was I asked this again?" is a fair question."""
    for key, why in iv.DOES_NOT_CARRY.items():
        assert why and len(why.split()) >= 3, f"{key} has no real reason"


def test_carried_and_dropped_do_not_overlap(prior):
    carried, dropped = iv.carry_forward(prior)
    assert not (set(carried) & set(dropped))


def test_an_empty_answer_does_not_carry():
    """Carrying a blank is carrying nothing while looking like an answer."""
    carried, _ = iv.carry_forward({"client_city": "", "client_state": None,
                                   "localities": [], "client_zip": "44139"})
    assert carried == {"client_zip": "44139"}


# ── the change questions ──────────────────────────────────────────────────

def test_a_first_year_client_is_not_asked_what_changed():
    """Nothing changed. Asking would be filler, and filler is how a person
    learns to skip a section."""
    session = iv.Interview(answers={"returning_client": "no"})
    asked = {q["id"] for _, q in iv.all_questions(session.schema)
             if iv.visible(q, session.answers)}
    assert "life_changes" not in asked
    assert "life_changes_detail" not in asked


def test_a_returning_client_is_asked_what_changed():
    session = iv.Interview(answers={"returning_client": "yes"})
    asked = {q["id"] for _, q in iv.all_questions(session.schema)
             if iv.visible(q, session.answers)}
    assert "life_changes" in asked
    assert "life_changes_detail" in asked


def test_the_eight_events_the_firm_named_are_all_offered():
    """Marriage, divorce, birth, death, a house bought or sold, a move, a
    retirement, an inheritance."""
    q = next(q for _, q in iv.all_questions(iv.load_schema())
             if q["id"] == "life_changes")
    values = {o["value"] for o in q["options"]}
    for event in ("married", "divorced", "birth", "death", "home_bought",
                  "home_sold", "moved", "retired", "inheritance"):
        assert event in values, event
    assert "none" in values, "a person who had no such year needs a way to say so"


def test_a_change_prints_on_no_client_document():
    """What a marriage or an inheritance MEANS for a return is a conversation
    with a person. Turning a tick box into tax advice is what this file does
    not do."""
    for qid in ("life_changes", "life_changes_detail", "returning_client"):
        q = next(q for _, q in iv.all_questions(iv.load_schema())
                 if q["id"] == qid)
        assert q.get("internal") is True
        assert q.get("internal_reason")
        assert not q.get("supplies")


# ── the whole command ─────────────────────────────────────────────────────

def _engagement(answers, store):
    out = intake.finish(dict(answers), store=store)
    assert out.created, out.reason
    return out.ref


def test_a_second_year_runs_from_the_first(prior, tmp_path):
    store = tmp_path / "store"
    last_year = _engagement(prior, store)

    canned = {k: v for k, v in prior.items() if not k.startswith("_")}
    canned |= {"tax_year": "2027", "returning_client": "yes",
               "life_changes": ["married", "moved"],
               "life_changes_detail": "Married in June; moved to Pennsylvania."}
    ans = tmp_path / "a.json"
    ans.write_text(json.dumps(canned), encoding="utf-8")

    assert cli.main(["returning", "--engagement", last_year,
                     "--store", str(store), "--answers", str(ans)]) == 0

    refs = sorted(p.name for p in store.iterdir() if p.is_dir())
    this_year = [r for r in refs if r != last_year]
    assert len(this_year) == 1, refs

    saved = json.loads((store / this_year[0] / "interview.json")
                       .read_text(encoding="utf-8"))
    assert saved["life_changes"] == ["married", "moved"]
    assert "Pennsylvania" in saved["life_changes_detail"]
    assert saved["returning_client"] == "yes"


def test_carried_answers_fill_in_when_the_replay_omits_them(prior, tmp_path):
    """The point of carrying: a preparer confirms rather than retypes."""
    store = tmp_path / "store"
    last_year = _engagement(prior, store)

    canned = {k: v for k, v in prior.items() if not k.startswith("_")}
    for key in ("client_full_name", "client_address1", "client_city",
                "client_state", "client_zip"):
        del canned[key]
    canned |= {"tax_year": "2027", "returning_client": "yes",
               "life_changes": ["none"], "life_changes_detail": ""}
    ans = tmp_path / "a.json"
    ans.write_text(json.dumps(canned), encoding="utf-8")

    assert cli.main(["returning", "--engagement", last_year,
                     "--store", str(store), "--answers", str(ans)]) == 0

    this_year = [p for p in store.iterdir() if p.is_dir() and p.name != last_year][0]
    saved = json.loads((this_year / "interview.json").read_text(encoding="utf-8"))
    assert saved["client_full_name"] == prior["client_full_name"]
    assert saved["client_zip"] == prior["client_zip"]


def test_an_engagement_with_no_saved_interview_refuses(tmp_path):
    """A client we cannot show last year's answers to is a new client as far
    as this command is concerned."""
    store = tmp_path / "store"
    (store / "2026-9999").mkdir(parents=True)
    assert cli.main(["returning", "--engagement", "2026-9999",
                     "--store", str(store)]) == 1


def test_the_new_engagement_does_not_overwrite_the_old(prior, tmp_path):
    store = tmp_path / "store"
    last_year = _engagement(prior, store)
    before = (store / last_year / "record.json").read_text(encoding="utf-8")

    canned = {k: v for k, v in prior.items() if not k.startswith("_")}
    canned |= {"tax_year": "2027", "returning_client": "yes",
               "life_changes": ["none"], "life_changes_detail": ""}
    ans = tmp_path / "a.json"
    ans.write_text(json.dumps(canned), encoding="utf-8")
    cli.main(["returning", "--engagement", last_year, "--store", str(store),
              "--answers", str(ans)])

    assert (store / last_year / "record.json").read_text(encoding="utf-8") == before
