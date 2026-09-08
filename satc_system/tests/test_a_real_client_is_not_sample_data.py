"""A real client cannot be mistaken for the demo, and a TIN has to be one.

TWO DEFECTS FROM THE WALK OF 5 SEPTEMBER 2026, both at the moment a practice
creates its first real client.

D11 -- THE BANNER CAME BACK, AND THE BUTTON IT OFFERED WOULD HAVE DELETED THEM.

`next_client_id` allocated `max(present) + 1000` over the clients PRESENT. On a
fresh install that is right. After **Clear sample data & start clean** there are
none, so the maximum is 0 and the practice's very first real client was handed
`SATC-001000` -- a fixture id. Then:

  * `has_sample_data()` tests membership of the fixture ids, so the banner
    returned and sat directly above a real person: *"Showing built-in sample data
    ... these aren't your clients or real document reads."*
  * That banner offers **Clear sample data**, and `clear_sample_data()` deletes
    every client whose id is a fixture id. **The button the screen was inviting
    them to press would have deleted the client it was sitting on.**

Flooring the allocation above the fixture range fixes both at the source and
changes nothing on a fresh install, where the fixtures are present and already
set the maximum.

D12 -- `hello` WAS A SOCIAL SECURITY NUMBER.

`/clients/new` took it and created the client. Nothing checked the format,
nothing flagged the record, and `masking.mask_ssn` rendered it `***-**-****` --
so the client then LOOKED like somebody whose number is on file. A blank field is
an honest gap; a masked non-number is a gap wearing a disguise, on the one field
the entire vault exists to protect.
"""
from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import AppState
from satc.intake.service import checked_tin, next_client_id
from satc.persistence import SATCStore


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.fixture()
def state(tmp_path):
    """Its own store: these tests clear the sample data, which is durable."""
    return AppState(store=SATCStore(tmp_path / "store"))


def _fixture_ids():
    from satc.fixtures import synthetic_identities
    return {rec.client_id for rec in synthetic_identities()}


# ── D11 ───────────────────────────────────────────────────────────────────────

def test_there_are_fixture_ids_to_collide_with():
    """The denominator. With no fixtures the rest of this proves nothing."""
    assert _fixture_ids()


def test_a_new_client_after_a_clear_does_not_take_a_fixture_id(state):
    """THE DEFECT. The first real client used to be handed `SATC-001000`."""
    state.clear_sample_data()
    assert not state.mart.public_clients, "the clear did not clear"

    cid = next_client_id(state.store)
    assert cid not in _fixture_ids(), (
        f"the practice's first real client was allocated {cid}, which is a "
        f"fixture id -- so the demo banner returns and Clear would delete them")


def test_the_banner_stays_gone_once_the_samples_are_cleared(state):
    """What the preparer actually sees, driven through the real creation path."""
    state.clear_sample_data()
    assert not state.has_sample_data()

    state.create_person_client(first_name="Priya", last_name="Raghavan")
    assert not state.has_sample_data(), (
        "creating a real client made the app announce its data is fake again")


def test_clearing_again_cannot_delete_the_real_client(state):
    """The consequence that matters: the button the banner offers.

    Pressing Clear a second time must be a no-op, not a deletion.
    """
    state.clear_sample_data()
    cid = state.create_person_client(first_name="Priya", last_name="Raghavan")

    state.clear_sample_data()
    assert cid in [pc.client_id for pc in state.mart.public_clients], (
        "Clear sample data deleted a real client")


def test_a_fresh_install_still_numbers_the_way_it_did(state):
    """The control. The floor must not change a normal install's ids, where the
    fixtures are present and already set the maximum."""
    present = {pc.client_id for pc in state.mart.public_clients}
    assert present & _fixture_ids(), "no fixtures present; wrong precondition"
    assert next_client_id(state.store) not in present


# ── D12 ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["hello", "1234", "x123456789", "12345678", "abc-de-fghi"])
def test_a_tin_that_is_not_one_is_refused(bad):
    with pytest.raises(ValueError, match="nine digits"):
        checked_tin(bad, what="a Social Security number")


@pytest.mark.parametrize("good", ["123-45-6789", "123456789", "123 45 6789"])
def test_the_shapes_people_actually_type_are_accepted(good):
    assert checked_tin(good, what="a Social Security number") == good


def test_blank_stays_legitimate():
    """The box is optional, and a number that has not arrived yet is an ordinary
    state. Refusing a blank would push people to type something to get past it."""
    assert checked_tin("", what="a Social Security number") == ""
    assert checked_tin("   ", what="a Social Security number") == ""


def test_the_screen_refuses_and_keeps_what_was_typed(client):
    """A typo must not cost the half-filled form, or people learn to skip the box."""
    r = client.post("/clients/new", data={
        "kind": "person", "first_name": "Priya", "last_name": "Raghavan",
        "ssn": "hello", "email": "priya@example.invalid", "phone": "555-0100"})
    body = r.get_data(as_text=True)

    assert r.status_code == 200, "a typo took the form down"
    assert "is not a Social Security number" in body
    assert "nine digits" in body
    assert "Priya" in body and "Raghavan" in body, "the form was emptied"


def test_a_business_ein_is_held_to_the_same_rule():
    with pytest.raises(ValueError, match="an EIN"):
        checked_tin("not an ein", what="an EIN")
