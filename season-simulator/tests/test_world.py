"""The world is a script: seeded, replayable, obviously fake."""

from __future__ import annotations

import re

import pytest

from season_sim import world

TIN_SHAPED = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{2}-\d{7}\b|\b\d{9}\b")


def test_the_same_seed_writes_the_same_world():
    assert world.build(42).to_json() == world.build(42).to_json()


def test_a_different_seed_writes_a_different_world():
    assert world.build(42).to_json() != world.build(43).to_json()


def test_the_world_round_trips_through_world_json():
    w = world.build(7)
    assert world.World.from_json(w.to_json()).to_json() == w.to_json()


@pytest.mark.parametrize("seed", [1, 42, 2027])
def test_names_are_obviously_fake_and_nothing_is_tin_shaped(seed):
    w = world.build(seed)
    for c in w.clients:
        assert re.fullmatch(r"(Testclient|Simulated) [A-Z][a-z]+ \d{3}.*", c.name), c.name
        assert c.email.endswith("@example.invalid")
    assert not TIN_SHAPED.search(w.to_json())


@pytest.mark.parametrize("n", [8, 12, 60, 75])
def test_the_mix_scales_and_every_k1_client_has_its_partnership(n):
    w = world.build(3, clients=n)
    assert len(w.clients) == n
    by = w.by_id()
    for c in w.clients:
        if c.archetype == "k1_gated":
            assert c.partnership and by[c.partnership].archetype == "partnership"


def test_billing_door_alternates_by_seed_parity_unless_named():
    assert world.build(42).billing_door == "satc"
    assert world.build(7).billing_door == "client_documents"
    assert world.build(7, billing_door="satc").billing_door == "satc"


def test_a_restricted_world_keeps_what_a_client_depends_on():
    w = world.build(42)
    gated = next(c for c in w.clients if c.archetype == "k1_gated")
    kept = {c.sim_id for c in w.restricted({gated.sim_id}).clients}
    assert kept == {gated.sim_id, gated.partnership}


def test_scenario_says_it_is_invented():
    sc = world.load_scenario()
    assert "INVENTED" in sc["label"]
    assert sum(sc["mix"].values()) == sc["clients"]
