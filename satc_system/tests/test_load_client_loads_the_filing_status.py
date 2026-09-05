""""Load client" loads the one field it promises to load.

THE DEFECT, found by walking the product on 5 September 2026. The withholding
estimator's first panel says:

    "Prefill the stable household info -- FILING STATUS -- from an existing
     client."

Filing status is the only field it names, and it was the one field it never set.
A client whose record holds `filing_status: 'Married filing jointly'` was
selected, **Load client** pressed, and the Household panel stayed on **Single**.

WHY. Two modules define `FILING_STATUSES` and they are different shapes:

    satc.app.intake_views       ["Single", "Married filing jointly", ...]
    satc.app.withholding_views  [("single", "Single"), ("married_jointly", ...)]

The interview stores the DISPLAY LABEL on the client record.
`_estimator_filing_status` knew estimator codes and Drake abbreviations, so every
label fell through both branches and returned "".

WHY IT MATTERS MORE THAN IT LOOKS. Filing status picks the brackets and the
standard deduction. Run as Single, a joint household gets $15,000 and the single
brackets instead of $30,000 and the joint ones -- and every figure on the screen
still ties out internally, because the arithmetic is correct and only the input
is wrong. That is the hardest kind of wrong answer to notice.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.app.withholding_views import _estimator_filing_status


@pytest.fixture()
def client():
    return create_app().test_client()


def test_every_status_the_interview_can_store_maps_to_something():
    """The interview's own list is the denominator: nothing it offers may fall
    through, because whatever it offers is what a client record will hold."""
    from satc.app.intake_views import FILING_STATUSES as INTERVIEW_STATUSES

    assert INTERVIEW_STATUSES, "no statuses to check -- the test proves nothing"
    for label in INTERVIEW_STATUSES:
        assert _estimator_filing_status(label), (
            f"the interview can store {label!r} and the estimator maps it to nothing")


def test_the_joint_label_maps_to_the_joint_code():
    """The exact value the walk found on a real record."""
    assert _estimator_filing_status("Married filing jointly") == "married_jointly"


def test_a_qualifying_surviving_spouse_gets_the_joint_brackets():
    """The interview offers a fifth status the estimator has no code for.

    QSS uses the joint brackets and the joint standard deduction, which is what
    the Drake mapping already does with the code "QSS" -- so the label must land
    in the same place rather than falling through to nothing.
    """
    assert _estimator_filing_status("Qualifying surviving spouse") == "married_jointly"
    assert _estimator_filing_status("QSS") == "married_jointly"


def test_the_shapes_it_already_understood_still_work():
    """The control. Codes and Drake abbreviations were never broken."""
    assert _estimator_filing_status("single") == "single"
    assert _estimator_filing_status("married_jointly") == "married_jointly"
    assert _estimator_filing_status("MFJ") == "married_jointly"
    assert _estimator_filing_status("HOH") == "head_of_household"
    assert _estimator_filing_status("") == ""
    assert _estimator_filing_status("not a filing status") == ""


def test_pressing_load_client_actually_prefills_it(client):
    """THE DEFECT, through the screen.

    Set a client's filing status the way the interview does, press Load client,
    and read the household back out of the session.
    """
    from flask import session

    cid = next(p.client_id for p in STATE.mart.public_clients
               if str(getattr(p, "entity_type", "")) == "INDIVIDUAL")
    STATE.set_filing_status(cid, "Married filing jointly")

    r = client.post("/withholding/from-client", data={"client_id": cid})
    body = r.get_data(as_text=True)

    assert "Prefilled filing status" in body, (
        "it reported no stored filing status for a client that has one")
    assert "Married filing jointly" in body

    with client.session_transaction() as sess:
        assert sess.get("wh_household", {}).get("filing_status") == "married_jointly", (
            "the estimator is still going to run this household as Single")


def test_a_client_with_nothing_on_file_still_says_so(client):
    """The other control: no stored status must not silently become a guess."""
    cid = next(p.client_id for p in STATE.mart.public_clients
               if str(getattr(p, "entity_type", "")) == "INDIVIDUAL")
    STATE.set_filing_status(cid, "")

    r = client.post("/withholding/from-client", data={"client_id": cid})
    assert "No stored filing status to prefill" in r.get_data(as_text=True)
