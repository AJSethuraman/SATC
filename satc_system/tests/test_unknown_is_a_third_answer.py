"""A question nobody asked is not a question answered "no".

THE DEFECT, found by walking the product on 5 September 2026. The Personal 1040
core interview asks thirteen Yes/No questions, and the template read:

    <input type="radio" name="q_{{ q.id }}" value="no" {{ 'checked' if ans != 'yes' }}>

`ans != 'yes'` is true for an absent answer, so **every question the preparer did
not touch was submitted as a definite No.** I completed an interview for an
invented client and set exactly two answers. The printed internal checklist --
the sheet that goes in the file -- then read:

    Marketplace health insurance coverage?              No
    Digital asset or crypto activity?                   No
    Foreign accounts or foreign financial assets?       No

She was never asked. Three of the thirteen are tagged `(risk)` by the product
itself, and on foreign accounts and digital assets a wrong "no" is not a blank --
it is an answer with its own penalty regime, given on the client's behalf by a
form.

AND ITS CONSEQUENCE, which is the more dangerous half. Risk flags are raised by
`generate_risk_flags` from questions answered YES. With every question defaulting
to No, the engagement's **0 RISK FLAGS** tile and the checklist's *"No risk flags
generated."* were true by construction on any interview where nobody deliberately
ticked one. Name the input that makes that number red: somebody choosing Yes, and
nothing else. A green produced by the absence of an answer rather than the
presence of a safe one.

The firm, asked whether to add a third answer: *"Add it, start unanswered."*

The other application already had this right -- `Take it on?` offers
**Yes / No / Undecided**.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.intake.outputs import _unanswered_risk_questions
from satc.intake.workflows import load_workflow

WORKFLOW = "personal_1040_core"


@pytest.fixture()
def client():
    return create_app().test_client()


def _risk_question_ids():
    return [q.id for q in load_workflow(WORKFLOW).questions if getattr(q, "risk_flag", "")]


def test_the_workflow_really_does_carry_risk_questions():
    """The denominator. Every assertion below is worthless if this is empty."""
    assert len(_risk_question_ids()) >= 3


def test_the_form_offers_three_answers_and_pre_selects_none(client):
    cid = next(p.client_id for p in STATE.mart.public_clients
               if str(getattr(p, "entity_type", "")) == "INDIVIDUAL")
    r = client.get(f"/intake/new?client={cid}&workflow={WORKFLOW}&mode=new")
    body = r.get_data(as_text=True)

    assert "Not asked" in body, "there is no third answer"
    # The defect in one string: a No that is checked because nothing else is.
    assert "value=\"no\" checked" not in body.replace("' ", '" ').replace("'", '"'), (
        "a No is pre-selected on an interview nobody has answered yet")


def test_the_route_does_not_invent_answers_it_was_not_given(client):
    """The OTHER half of the defect, and it needs its own guard.

    Fixing the template stops the browser sending `no` for untouched rows. It
    would buy nothing if the route then filled the gaps in itself -- so this
    posts the form the way the fixed screen posts it, with only the answered
    field present, and checks that the risk questions come back absent rather
    than defaulted.

    Driven through `/intake/new` rather than by calling the producer with a
    hand-built dict: a dict written by the test proves only that the test can
    leave a key out. (An earlier draft did exactly that and passed with the
    template defect still in place.)
    """
    cid = next(p.client_id for p in STATE.mart.public_clients
               if str(getattr(p, "entity_type", "")) == "INDIVIDUAL")
    risky = _risk_question_ids()

    client.post("/intake/new", data={
        "client": cid, "workflow_key": WORKFLOW, "tax_year": "2031",
        "mode": "new", "q_stateReturnNeeded": "yes",
    })
    STATE.reload()

    job = next((j for j in STATE.store.load_jobs()
                if j.client_id == cid and j.tax_year == 2031
                and j.workflow_key == WORKFLOW), None)
    assert job is not None, "the engagement was not created at all"

    for qid in risky:
        assert job.intake_answers.get(qid) in (None, ""), (
            f"{qid} came back as {job.intake_answers.get(qid)!r} and nobody answered it")


def test_the_printed_checklist_does_not_put_words_in_the_client_s_mouth():
    """The sheet that goes in the file must not show an answer as theirs."""
    from satc.intake.outputs import format_answer

    assert format_answer("yes") == "Yes"
    assert format_answer("no") == "No"
    assert format_answer(None) == "No answer"
    assert format_answer("") == "No answer"


def test_the_risk_section_says_how_many_were_never_asked():
    """"No risk flags generated." on its own is the green that cannot go red."""
    from satc.intake.outputs import _render_risk_flags
    from satc.models.work import Job

    workflow = load_workflow(WORKFLOW)
    job = Job(job_id="J1", client_id="C", workflow_key=WORKFLOW, tax_year=2031,
              intake_answers={}, risk_flags=[])

    html = _render_risk_flags(job, workflow)
    assert "were not answered" in html
    assert "not a clean bill of health" in html
    for label in _unanswered_risk_questions(job, workflow):
        assert label in html, "it counted them without saying which"


def test_a_fully_answered_interview_gets_a_clean_bill_and_says_so():
    """The control. Answering every risk question NO is a real all-clear, and it
    has to read differently from nobody having asked."""
    from satc.intake.outputs import _render_risk_flags
    from satc.models.work import Job

    workflow = load_workflow(WORKFLOW)
    answered = {qid: "no" for qid in _risk_question_ids()}
    job = Job(job_id="J2", client_id="C", workflow_key=WORKFLOW, tax_year=2031,
              intake_answers=answered, risk_flags=[])

    html = _render_risk_flags(job, workflow)
    assert "every risk question was answered" in html
    assert "were not answered" not in html


def test_a_raised_flag_still_reads_as_a_raised_flag():
    """The other control: the guard must not swallow a real flag."""
    from satc.intake.outputs import _render_risk_flags
    from satc.models.work import Job

    workflow = load_workflow(WORKFLOW)
    answered = {qid: "no" for qid in _risk_question_ids()}
    job = Job(job_id="J3", client_id="C", workflow_key=WORKFLOW, tax_year=2031,
              intake_answers=answered, risk_flags=["Foreign account reporting"])

    html = _render_risk_flags(job, workflow)
    assert "Foreign account reporting" in html
