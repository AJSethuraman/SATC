"""A room's burst reaction names each body it catches (M3, 19 Sep 2026).

The firm read six identical lines "The ember-glass flares and the heat lashes
everything near the plinth." on one card (18 Sep 2026) and asked what had
happened: one wild swing, six bodies, one flavour line each, naming nobody.
Now every burst event says who it caught and for how much.
"""
from __future__ import annotations

import unittest

from arena import combat, rules
from arena.demo import load_manifests


class RoomReactionWording(unittest.TestCase):
    def setUp(self):
        self.manifests = load_manifests()
        self.state = rules.new_match_state(self.manifests, 7, 12)
        ids = [m.id for m in self.manifests]
        self.swinger, self.target, self.bystanders = ids[0], ids[1], ids[2:5]
        for aid in [self.swinger, self.target, *self.bystanders]:
            self.state["agents"][aid]["room"] = rules.VAULT_ROOM
        self.occupants = [combat.combatant_from_agent(self.state["agents"][aid]) for aid in [self.swinger, self.target, *self.bystanders]]
        self.occupants.append(combat.combatant_from_monster(self.state["monsters"]["crown_warden"]))

    def test_a_vault_burst_names_every_body_it_catches_and_the_amount(self):
        attacker = self.occupants[0]
        target = self.occupants[1]
        face = combat.wild_swing_face(combat.WILD_SWING_DIE)
        reaction, applied, effects = combat._room_wears_it(
            attacker, target, rules.VAULT_ROOM, self.occupants, {}, face, fell_through=False
        )
        self.assertEqual(reaction.effect_kind, "burst_damage")
        self.assertTrue(applied)
        caught = {e.target_id: e for e in effects}
        # everyone alive in the room but the swinger, the Warden included
        self.assertEqual(sorted(caught), sorted([self.target, *self.bystanders, "crown_warden"]))
        for e in effects:
            victim = next(b for b in self.occupants if b.id == e.target_id)
            self.assertTrue(e.public_text.startswith(reaction.flavor), e.public_text)
            self.assertIn(f" It catches {victim.name} for {reaction.amount}.", e.public_text)
            self.assertEqual(e.amount, reaction.amount)
        # six lines, six different sentences: no two alike
        self.assertEqual(len({e.public_text for e in effects}), len(effects))

    def test_the_other_reactions_already_name_who_they_touch(self):
        attacker, target = self.occupants[0], self.occupants[1]
        face = combat.wild_swing_face(combat.WILD_SWING_DIE)
        for room, who in (("threshold", target.name), ("ossuary_gate", attacker.name)):
            _, _, effects = combat._room_wears_it(attacker, target, room, self.occupants, {}, face, fell_through=False)
            self.assertTrue(effects, room)
            self.assertTrue(all(who in e.public_text for e in effects), [e.public_text for e in effects])


if __name__ == "__main__":
    unittest.main()
