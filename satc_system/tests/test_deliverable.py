"""The fact that something went OUT — the one the practice was not recording.

Its absence made three separate things refuse. These tests guard the fix AND
the refusals that must survive it: a recorded delivery is now a conclusion, and
an unrecorded one is still not.
"""

from datetime import date

import pytest

from satc.models.actor import Actor
from satc.models.deliverable import (
    Deliverable,
    DeliveryError,
    delivery_of,
    merge,
    record_delivery,
)

OWNER = Actor.owner()
SENT = date(2026, 3, 20)


def a_delivery(*, actor=OWNER, **kw) -> Deliverable:
    args = dict(client_id="CL-1", tax_year=2025, kind="return_for_review",
                delivered_on=SENT, channel="portal", return_key="CL-1-2025-1040")
    args.update(kw)
    return record_delivery(actor=actor, **args)


# --- how we know ------------------------------------------------------------

def test_a_delivery_records_what_when_how_and_on_whose_say_so():
    sent = a_delivery()
    assert sent.delivered_on == SENT
    assert sent.channel == "portal"
    assert sent.delivered_by == OWNER.handle
    assert "draft return" in sent.describe()
    assert "portal" in sent.describe()


def test_recording_a_return_as_delivered_must_say_which_return():
    """Otherwise nothing can tell the federal from the state, and the job it
    belongs to cannot be moved."""
    with pytest.raises(DeliveryError) as refusal:
        a_delivery(return_key="")
    assert "WHICH return" in str(refusal.value)


def test_an_organizer_needs_no_return_because_it_belongs_to_a_client_year():
    assert a_delivery(kind="organizer", return_key="").kind == "organizer"


def test_a_model_cannot_record_that_work_was_delivered():
    """Delivery stops the prep clock, starts the signature chase and makes the
    work billable. A model asserting it would assert the one thing nobody could
    check from the file afterwards."""
    from satc.models.actor import ActorRefused

    with pytest.raises(ActorRefused):
        a_delivery(actor=Actor.model("SATC-Assistant"))


def test_recording_the_same_delivery_twice_records_it_once():
    ledger, added = merge([], [a_delivery()])
    assert len(added) == 1
    ledger, added = merge(ledger, [a_delivery()])
    assert added == []
    assert len(ledger) == 1


def test_an_organizer_is_not_the_return_going_out():
    assert a_delivery().is_the_return
    assert not a_delivery(kind="organizer", return_key="").is_the_return


def test_the_delivery_that_counts_is_the_first_not_the_latest():
    """A return re-sent in June was still delivered in April, and the promise
    was kept or missed then."""
    first = a_delivery(delivered_on=date(2026, 4, 1))
    again = a_delivery(delivered_on=date(2026, 6, 9))
    found = delivery_of([again, first], client_id="CL-1", tax_year=2025)
    assert found.delivered_on == date(2026, 4, 1)


def test_an_organizer_never_counts_as_the_return_being_delivered():
    only_organizer = [a_delivery(kind="organizer", return_key="")]
    assert delivery_of(only_organizer, client_id="CL-1", tax_year=2025) is None
