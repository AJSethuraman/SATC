"""The invoice screen says what it is applying, not only what was agreed.

THE DEFECT, found by walking the product on 5 September 2026. One screen, two
elements, contradicting each other about money.

Setting the rate plan to **Hardship — 60% off** with a recorded basis produced
totals reading:

    Full value of work            450.00
    Hardship rate applied 60%    -270.00
    Total due                     180.00

directly beneath a red line reading:

    "Nobody has priced this client yet — No rate plan agreed for 2025 — the
     practice default 'standard' applies until one is recorded."

**Both sentences were true.** `_set_header` writes the plan to the session
DRAFT; `rate_plan_for` reads the ENGAGEMENT. They answer different questions and
only one of them was on the screen -- the one that does NOT drive the totals. A
preparer who reads the warning and trusts it believes they are billing $450 and
is in fact billing $180.

It also made the refusal invisible: the message before a REJECTED "Set" (no
basis given) was identical to the message after an ACCEPTED one, so the screen
never told you which had happened.

WHAT IS NOT CHANGED. The engagement remains the place a standing rate is agreed,
and an invoice-only plan is still legitimate -- a one-off hardship on a single
bill is a real thing. The screen simply has to say that is what it is.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE


@pytest.fixture()
def client():
    return create_app().test_client()


def _a_client_id():
    return next(p.client_id for p in STATE.mart.public_clients
                if str(getattr(p, "entity_type", "")) == "INDIVIDUAL")


def _set_plan(client, *, plan_key, basis, tax_year="2025"):
    cid = _a_client_id()
    return client.post("/invoices/new", data={
        "action": "header", "client_id": cid, "tax_year": tax_year,
        "plan_key": plan_key, "plan_basis": basis, "plan_shown": "standard",
    }, follow_redirects=True)


def test_the_standard_case_still_reads_the_way_it_did(client):
    """The control. With nothing applied and nothing agreed, the old sentence is
    the right one and must survive."""
    r = _set_plan(client, plan_key="standard", basis="")
    body = r.get_data(as_text=True)
    assert "No rate plan agreed" in body
    assert "This invoice applies" not in body


def test_a_plan_the_engagement_never_agreed_is_named_as_such(client):
    """THE DEFECT. The screen must lead with what the totals actually use."""
    r = _set_plan(client, plan_key="hardship",
                  basis="Household income fell after a job loss")
    body = r.get_data(as_text=True)

    assert "This invoice applies" in body, (
        "the screen still shows only what the engagement agreed")
    assert "the totals below use it" in body


def test_it_still_says_what_the_engagement_records(client):
    """Saying the first fact must not swallow the second: an invoice-only rate is
    fine, and the preparer has to be able to see that it IS invoice-only."""
    r = _set_plan(client, plan_key="hardship",
                  basis="Household income fell after a job loss")
    body = r.get_data(as_text=True)

    assert "is not what the 2025 engagement records" in body
    assert "No rate plan agreed for 2025" in body
    assert "Agree it on the engagement" in body


def test_the_discount_and_the_warning_cannot_disagree_any_more(client):
    """The end state the walk was actually complaining about, on a real total.

    THIS TEST WAS DECORATIVE ON ITS FIRST DRAFT and the mutation run caught it.
    It was wrapped in `if "rate applied" in body:` -- and with no lines on the
    draft there are no totals at all, so the condition was false, the assertion
    never ran, and it passed against the defect it names. A conditional guard
    around the only assertion in a test is a test that can quietly do nothing.

    So it puts a real line on the invoice first, which is what makes the totals
    render, and asserts unconditionally.
    """
    _set_plan(client, plan_key="hardship",
              basis="Household income fell after a job loss")
    r = client.post("/invoices/new", data={
        "action": "add", "service_code": "return_1040", "quantity": "1",
    }, follow_redirects=True)
    body = r.get_data(as_text=True)

    assert "rate applied" in body.lower(), (
        "no discount is showing, so this test is not looking at the thing it names")
    assert "Nobody has priced this client yet" not in body, (
        "a discount is applied and the screen still says nobody has priced this client")
    assert "This invoice applies" in body
