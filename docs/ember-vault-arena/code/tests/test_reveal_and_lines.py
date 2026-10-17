"""PRD §5.7: a dead character's private objective is revealed at the moment
of death, and once. PRD §5.6 and §5.27: a monster speaks a canned line when
it strikes, from its own table keyed by the round. PRD §5.8: a talker can be
attacked from act II; its death is a public event that pays nobody."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from arena import rules, world
from arena.demo import load_manifests, load_talkers
from arena.engine import ArenaEngine
from arena.providers import MockDecisionProvider
from arena.rng import HashRNG
from arena.storage import ArenaStore


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.roster = load_manifests() + load_talkers()
        self.ids = sorted(m.id for m in self.roster if m.kind == "character")
        self._stores = []

    def tearDown(self):
        for s in self._stores:
            s.close()
        self.temp.cleanup()

    def engine(self, name="u.db", round_no=3):
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=False)
        engine.match_id = "unit"
        engine.manifests = {m.id: m for m in self.roster}
        engine.state = rules.new_match_state(self.roster, 5)
        engine.state["status"] = "running"
        engine.state["round"] = round_no
        engine.state["act"] = rules.act_for_round(round_no)
        engine.rng = HashRNG(5)
        return engine

    def events(self, engine, kind):
        return [e for e in engine.store.events_for_match(engine.match_id) if e["event_type"] == kind]


class RevealAtDeath(Base):
    def test_a_death_reveals_the_objective_once_and_the_end_reveals_only_the_living(self):
        a, b = self.ids[:2]
        engine = self.engine(round_no=rules.ACT_I_LAST_ROUND + 2)
        engine._eliminate(b, "test", credited_to=a)
        reveals = self.events(engine, "objective_reveal")
        self.assertEqual([(e["actor_id"], e["payload"]["at"]) for e in reveals], [(b, "death")])
        self.assertEqual(reveals[0]["payload"]["objective"], engine.manifests[b].secret_objective)
        self.assertIn(reveals[0]["payload"]["objective"].replace("_", " "), reveals[0]["public_text"])
        elim = self.events(engine, "agent_eliminated")[0]
        self.assertEqual(elim["payload"]["kind"], "character")
        self.assertEqual(engine.state["agents"][a]["score"], 2)  # the killer is paid once
        engine.state["round"] = engine.max_rounds
        engine._finalize()
        reveals = self.events(engine, "objective_reveal")
        self.assertEqual(sum(1 for e in reveals if e["actor_id"] == b), 1)
        at_end = sorted(e["actor_id"] for e in reveals if e["payload"]["at"] == "end")
        self.assertEqual(at_end, [x for x in self.ids if x != b])
        self.assertFalse([e for e in reveals if e["actor_id"] in ("wick", "coin", "vesper")])


class MonsterLines(Base):
    def test_a_monster_speaks_its_round_line_when_it_strikes(self):
        a = self.ids[0]
        engine = self.engine(round_no=4)
        state = engine.state
        state["agents"][a]["room"] = "ironwood_gate"
        state["agents"][a]["tile"] = [2, 2]  # beside the guardian at [2,1]
        for other in self.ids[1:]:
            state["agents"][other]["room"] = "threshold"
        engine._monster_phase(4)
        lines = self.events(engine, "monster_line")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["actor_id"], "ironwood_guardian")
        self.assertEqual(lines[0]["payload"]["line"], world.monster_line("ironwood_guardian", 4))
        self.assertIn(world.MONSTERS["ironwood_guardian"]["lines"][3], lines[0]["public_text"])
        self.assertEqual(world.monster_line("ironwood_guardian", 6), world.MONSTERS["ironwood_guardian"]["lines"][0])
        for mid, m in world.MONSTERS.items():
            self.assertGreaterEqual(len(m["lines"]), 5, mid)


class TalkerDeath(Base):
    def test_a_talker_can_be_struck_from_act_ii_and_its_death_is_public_and_pays_nobody(self):
        a = self.ids[0]
        engine = self.engine(round_no=rules.ACT_I_LAST_ROUND + 1)
        engine._eliminate("wick", "test", credited_to=a)
        elim = self.events(engine, "agent_eliminated")[0]
        self.assertEqual(elim["payload"]["kind"], "talker")
        self.assertIn(", a talker,", elim["public_text"])
        self.assertEqual(elim["payload"]["scoring"]["points"], 0)
        self.assertEqual(engine.state["agents"][a]["score"], 0)
        self.assertEqual(engine.state["agents"][a]["direct_eliminations"], [])
        self.assertFalse(self.events(engine, "objective_reveal"))


if __name__ == "__main__":
    unittest.main()
