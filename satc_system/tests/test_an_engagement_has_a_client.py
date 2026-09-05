"""An engagement belongs to somebody, and nothing used to check.

THE DEFECT, found by walking the product on 5 September 2026.

`/intake/plan` opens with its own instruction -- *"Pick a client first — a plan
is for somebody, and the rate plan and the filing history are read off them"* --
offers no control that picks one, and guarded only the tax year. Pressing
**Plan it** produced a correct, well-written refusal that named the missing YEAR
and said nothing about the missing CLIENT. Supply a year in the URL and the
guard was satisfied: the full plan rendered for nobody, with document requests
dated `Mar 25` and `Mar 26`, a cost section, statutory and firm-policy
deadlines, and *"Because you answered 'yes' to 'New SAT-C client?'"* against
answers no client ever gave.

**Generate this engagement** was live on that page. Pressing it created a real,
stored engagement -- `engagement-255234d6a1dfe4a1` -- belonging to no one, and
opened two document requests against it. The Documents badge went from 4 to 6,
so an orphan entered the practice's outstanding-documents count, and the rows
survived a sample-data clear because they were not sample data.

The engagement screen showed the hole in its own sentence:

    "the client's letters, estimate and invoices all carry YYYY-NNNN, while this
     system keys on , which a client is never shown."

and `/engagements` listed the row with an empty CLIENT column.

WHERE THE GUARD WENT. In `create_engagement_from_intake`, the single producer --
its own docstring calls itself "the moment a real client acquires one for the
year". A check on either view protects the door it is written on; a check on the
producer protects the record.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE


@pytest.fixture()
def client():
    return create_app().test_client()


def _engagement_client_ids():
    return [getattr(e, "client_id", "") for e in STATE.mart.engagements]


def test_the_producer_refuses_an_engagement_with_no_client():
    """The engine, not the view."""
    from satc.intake.service import create_engagement_from_intake

    with pytest.raises(ValueError, match="belongs to a client"):
        create_engagement_from_intake(
            STATE.store, client_id="", workflow_key="personal_1040_core",
            tax_year=2025, answers={})


def test_a_blank_that_is_only_whitespace_is_still_blank():
    """`"   "` is not a client id, and `if not client_id` alone would take it."""
    from satc.intake.service import create_engagement_from_intake

    with pytest.raises(ValueError, match="belongs to a client"):
        create_engagement_from_intake(
            STATE.store, client_id="   ", workflow_key="personal_1040_core",
            tax_year=2025, answers={})


def test_pressing_generate_with_no_client_creates_nothing(client):
    """THE DEFECT ITSELF, driven the way the walk drove it.

    Counted on the stored engagements rather than on the response, because what
    went wrong was a row coming into being -- not a page rendering badly.
    """
    before = len(STATE.mart.engagements)

    client.post("/intake/new", data={"client": "", "workflow_key": "personal_1040_core",
                                     "tax_year": "2025", "mode": "new"})
    STATE.reload()

    assert len(STATE.mart.engagements) == before, (
        "an engagement was created with no client chosen")
    assert "" not in _engagement_client_ids(), (
        "an engagement is on file with an empty client key")


def test_the_plan_screen_refuses_before_it_offers_the_button(client):
    """The year guard passed and the client guard did not exist.

    This is the exact URL the walk used: a year supplied, a client deliberately
    empty. It rendered the whole plan, with Generate live on it.
    """
    r = client.get("/intake/plan?client=&workflow=personal_1040_core&tax_year=2025")
    body = r.get_data(as_text=True)

    assert "Pick the client this engagement is for" in body
    assert "Generate this engagement" not in body, (
        "the screen offered to generate an engagement for nobody")


def test_the_screen_that_asks_for_a_client_now_offers_one(client):
    """It said "pick a client first" and gave you nothing to pick with.

    A refusal a person cannot act on is only half a refusal.
    """
    r = client.get("/intake/plan?client=&workflow=personal_1040_core&tax_year=2025")
    body = r.get_data(as_text=True)

    assert "— choose a client —" in body
    assert "Plan for them" in body


def test_a_real_client_still_gets_a_whole_plan(client):
    """The control. A guard that also blocks the everyday case is not a fix."""
    # An INDIVIDUAL, not simply the first client alphabetically: that is a
    # partnership, and `personal_1040_core` refuses it for a different and
    # correct reason -- which would make this control pass for the wrong cause.
    cid = next(p.client_id for p in STATE.mart.public_clients
               if str(getattr(p, "entity_type", "")) == "INDIVIDUAL")
    r = client.get(f"/intake/plan?client={cid}&workflow=personal_1040_core&tax_year=2025")
    body = r.get_data(as_text=True)

    assert "Pick the client this engagement is for" not in body
    assert "Generate this engagement" in body
