"""Deals are recorded, never enforced (PRD §5.19–21, built 18 Sep 2026).

An offer becomes offer_made with an id; an accept the round after strikes it;
an offer nobody answers lapses at the end of the next round; a break is
judged at the end of each round against that round's committed events and is
a public deal_broken naming who broke what; nothing is prevented. The digest
carries a character's own offers and standing deals, and every break to
everyone. What cannot be recorded is deal_lost with the reason, no penalty.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from arena import deals, rules, scoring
from arena.demo import load_manifests
from arena.engine import ArenaEngine
from arena.models import AgentAction
from arena.providers import MockDecisionProvider, ProviderResult
from arena.rng import HashRNG
from arena.storage import ArenaStore, canonical_json

EMPTY = {"kind": None, "to": None, "type": None, "rounds": None, "item": None,
         "destination": None, "by_round": None, "offer_id": None}


def offer(to, type_, **terms):
    return {**EMPTY, "kind": "offer", "to": to, "type": type_, **terms}


def accept(offer_id):
    return {**EMPTY, "kind": "accept", "offer_id": offer_id}


class Scripted(MockDecisionProvider):
    """Everyone guards where they stand; the deal slot follows a script keyed
    by (round, agent id). Nothing else about the mock is used."""

    def __init__(self, script):
        self.script = script

    def decide(self, manifest, prompt, observation):
        result = super().decide(manifest, prompt, observation)
        action = json.loads(result.raw_output)
        round_no = observation["public_state"]["round"]
        action.update({"action": "guard", "target": None, "destination": None, "item": None, "tile": None, "fallback": None})
        action["deal"] = self.script.get((round_no, manifest.id))
        raw = canonical_json(action)
        return ProviderResult(raw, result.input_tokens, len(raw) // 4, "mock", "scripted")


class DealTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifests = load_manifests()
        self.ids = sorted(m.id for m in self.manifests)
        self._stores = []

    def tearDown(self):
        for store in self._stores:
            store.close()
        self.temp.cleanup()

    def run_match(self, provider, rounds, name="m.db", seed=5):
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, provider, max_rounds=rounds, parallel_agents=False)
        match_id = engine.run(self.manifests, seed=seed)
        return engine, store.replay_bundle(match_id)

    def engine(self, name="unit.db", seed=7, round_no=1):
        store = ArenaStore(self.root / name)
        self._stores.append(store)
        engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=False)
        engine.match_id = "unit"
        engine.manifests = {m.id: m for m in self.manifests}
        engine.state = rules.new_match_state(self.manifests, seed)
        engine.state["status"] = "running"
        engine.state["round"] = round_no
        engine.state["act"] = rules.act_for_round(round_no)
        engine.rng = HashRNG(seed)
        return engine

    def events(self, bundle_or_engine, kind):
        if isinstance(bundle_or_engine, dict):
            rows = bundle_or_engine["events"]
        else:
            rows = bundle_or_engine.store.events_for_match(bundle_or_engine.match_id)
        return [e for e in sorted(rows, key=lambda e: e.get("seq", e.get("ordinal", 0))) if e["event_type"] == kind]

    def strike(self, engine, from_id, to_id, type_, made_round, **terms):
        """A standing deal, recorded the way the engine records it."""
        state = engine.state
        state["agents"][to_id]["room"] = state["agents"][from_id]["room"]
        recorded, why = deals.record_offer(state, made_round, from_id, offer(to_id, type_, **terms))
        self.assertIsNone(why, why)
        struck, why = deals.record_accept(state, made_round + 1, to_id, recorded["id"])
        self.assertIsNone(why, why)
        return struck


class OffersAndAcceptances(DealTestCase):
    def test_an_offer_is_recorded_struck_the_round_after_and_the_digest_shows_it_to_the_parties_only(self):
        a, b, c = self.ids[:3]
        script = {
            (1, a): offer(b, "truce", rounds=2),
            (2, b): accept(f"offer-r1-{a}"),
            (2, c): accept(f"offer-r1-{a}"),  # not made to c
        }
        engine, bundle = self.run_match(Scripted(script), rounds=4)
        made = self.events(bundle, "offer_made")
        self.assertEqual(len(made), 1)
        self.assertEqual((made[0]["round_no"], made[0]["actor_id"], made[0]["target_id"]), (1, a, b))
        self.assertEqual(made[0]["payload"]["offer"]["id"], f"offer-r1-{a}")
        self.assertIn("a truce of 2 rounds", made[0]["public_text"])
        struck = self.events(bundle, "deal_struck")
        self.assertEqual(len(struck), 1)
        self.assertEqual((struck[0]["round_no"], struck[0]["actor_id"], struck[0]["target_id"]), (2, b, a))
        self.assertEqual(struck[0]["payload"]["deal"]["term_end"], 3)  # rounds 2 and 3
        lost = self.events(bundle, "deal_lost")
        self.assertEqual([(e["actor_id"], e["payload"]["reason"]) for e in lost], [(c, "that offer was not made to you")])
        self.assertFalse(self.events(bundle, "offer_lapsed"))
        self.assertFalse(self.events(bundle, "deal_broken"))
        # the ledger at the end: the truce ran its two rounds unbroken and is kept
        final = bundle["snapshots"][-1]["state"]
        self.assertEqual(final["deals"]["struck"][f"offer-r1-{a}"]["status"], "kept")
        self.assertEqual(final["deals"]["offers"][f"offer-r1-{a}"]["status"], "struck")
        # the digest at the start of round 2: b sees the offer, c does not, both see no breaks
        start2 = next(s["state"] for s in bundle["snapshots"] if s["round_no"] == 2 and s["phase"] == "start")
        for who, sees in ((a, True), (b, True), (c, False)):
            obs = rules.visible_observation(deepcopy(start2), who, "lorekeeper", [])
            block = obs["deals"]
            self.assertEqual([o["id"] for o in block["offers"]], [f"offer-r1-{a}"] if sees else [], who)
            if sees:
                self.assertEqual(block["offers"][0]["yours"], who == a)
            self.assertEqual(block["standing"], [])
            self.assertEqual(block["breaks"], [])
            self.assertIn(b if who != b else a, block["can_offer_to"])
            self.assertNotIn(who, block["can_offer_to"])
        # and at the start of round 3 the deal stands for both parties
        start3 = next(s["state"] for s in bundle["snapshots"] if s["round_no"] == 3 and s["phase"] == "start")
        for who, other, role in ((a, b, "offerer"), (b, a, "acceptor")):
            standing = rules.visible_observation(deepcopy(start3), who, "lorekeeper", [])["deals"]["standing"]
            self.assertEqual([(d["with"], d["you_are"], d["term_end"]) for d in standing], [(other, role, 3)])
        self.assertEqual(rules.visible_observation(deepcopy(start3), c, "lorekeeper", [])["deals"]["standing"], [])
        # the offer, the acceptance and the loss are public in the replay's decisions
        public = [d["action"]["deal"] for d in bundle["decisions"] if d["action"].get("deal")]
        self.assertEqual(len(public), 3)

    def test_an_offer_nobody_answers_lapses_at_the_end_of_the_next_round(self):
        a, b = self.ids[:2]
        engine, bundle = self.run_match(Scripted({(1, a): offer(b, "share_item", item="healing_tonic", by_round=3)}), rounds=3)
        lapsed = self.events(bundle, "offer_lapsed")
        self.assertEqual([(e["round_no"], e["actor_id"], e["target_id"]) for e in lapsed], [(2, a, b)])
        self.assertEqual(bundle["snapshots"][-1]["state"]["deals"]["offers"][f"offer-r1-{a}"]["status"], "lapsed")
        # too late to accept in round 3
        engine, bundle = self.run_match(
            Scripted({(1, a): offer(b, "share_item", item="healing_tonic", by_round=3), (3, b): accept(f"offer-r1-{a}")}),
            rounds=3, name="late.db",
        )
        lost = self.events(bundle, "deal_lost")
        self.assertEqual([(e["actor_id"], e["payload"]["reason"]) for e in lost], [(b, "that offer is lapsed")])

    def test_what_cannot_be_recorded_is_lost_with_the_reason_and_no_penalty(self):
        a, b = self.ids[:2]
        engine = self.engine()
        state = engine.state
        state["agents"][b]["room"] = rules.VAULT_ROOM
        cases = [
            (offer("nobody", "truce", rounds=2), "no such character to offer it to"),
            (offer(a, "truce", rounds=2), "no such character to offer it to"),
            (offer(b, "truce", rounds=2), "the other party is not in the room to hear it"),
            (offer(self.ids[2], "share_item", item="unobtainium", by_round=5), "no such item"),
            (offer(self.ids[2], "escort", destination="attic", by_round=5), "no such room"),
            (offer(self.ids[2], "escort", destination="vault", by_round=1), "by_round has to be a later round"),
            (offer(self.ids[2], "escort", destination="vault", by_round=999), "by_round is after the last round"),
            (accept("offer-r0-nobody"), "no such offer"),
        ]
        for raw, reason in cases:
            with self.subTest(reason):
                recorded, why = (deals.record_offer(state, 1, a, raw) if raw["kind"] == "offer"
                                 else deals.record_accept(state, 1, a, raw["offer_id"]))
                self.assertIsNone(recorded)
                self.assertEqual(why, reason)
        # one offer per round, and the same round cannot answer it
        recorded, why = deals.record_offer(state, 1, a, offer(self.ids[2], "truce", rounds=2))
        self.assertIsNone(why)
        self.assertEqual(deals.record_offer(state, 1, a, offer(self.ids[3], "truce", rounds=2))[1], "one offer per round")
        self.assertEqual(deals.record_accept(state, 1, self.ids[2], recorded["id"])[1], "an offer is answered the round after it is made")
        self.assertEqual(deals.record_accept(state, 2, self.ids[3], recorded["id"])[1], "that offer was not made to you")
        state["agents"][a]["status"] = "eliminated"
        self.assertEqual(deals.record_accept(state, 2, self.ids[2], recorded["id"])[1], "the offerer is out of the match")
        # through the engine: a lost deal is an event and never a score
        state["agents"][a]["status"] = "active"
        engine._emit_deal(1, a, AgentAction.from_dict({"action": "guard", "target": None, "destination": None, "item": None,
                                                       "tile": None, "speech": {"mode": "silent", "to": None, "text": ""},
                                                       "note": {"objective": "", "reads": []}, "deal": offer("nobody", "truce", rounds=1),
                                                       "fallback": None}).deal)
        lost = self.events(engine, "deal_lost")
        self.assertEqual(lost[-1]["payload"]["reason"], "no such character to offer it to")
        self.assertEqual(state["agents"][a]["score"], 0)


class Breaks(DealTestCase):
    def test_an_attack_on_a_truce_partner_is_a_public_break_and_nothing_is_prevented(self):
        a, b, c = self.ids[:3]
        round_no = rules.ACT_I_LAST_ROUND + 2  # rivals may attack from act II
        engine = self.engine(round_no=round_no)
        state = engine.state
        deal = self.strike(engine, a, b, "truce", round_no - 1, rounds=3)
        self.assertEqual(deal["term_end"], round_no + 2)
        state["agents"][a]["tile"], state["agents"][b]["tile"] = [1, 1], [2, 1]
        hp_before = state["agents"][b]["hp"]
        engine._resolve_action(a, AgentAction(action="attack", target=b))
        self.assertTrue(engine._round_events)
        engine._end_round_upkeep(round_no)
        broken = self.events(engine, "deal_broken")
        self.assertEqual(len(broken), 1)
        self.assertEqual((broken[0]["actor_id"], broken[0]["target_id"]), (a, b))
        self.assertEqual(broken[0]["payload"]["broken_by"], a)
        self.assertIn("breaks the deal", broken[0]["public_text"])
        self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "broken")
        self.assertLessEqual(state["agents"][b]["hp"], hp_before)  # the swing landed or missed; nothing stopped it
        # everyone reads the break, party or not; nobody is scored for it
        for who in (a, b, c):
            block = rules.visible_observation(deepcopy(state), who, "lorekeeper", [])["deals"]
            self.assertEqual([(x["broken_by"], x["against"]) for x in block["breaks"]], [([a], [b])])
            self.assertEqual(block["standing"], [])
        self.assertEqual(state["agents"][a]["score"], 0)
        # a second round: a broken deal is not broken twice
        engine._round_events = []
        engine._resolve_action(a, AgentAction(action="attack", target=b))
        engine._end_round_upkeep(round_no + 1)
        self.assertEqual(len(self.events(engine, "deal_broken")), 1)

    def test_a_truce_runs_out_kept_and_an_attack_after_the_term_is_no_break(self):
        a, b = self.ids[:2]
        round_no = rules.ACT_I_LAST_ROUND + 2
        engine = self.engine(round_no=round_no)
        deal = self.strike(engine, a, b, "truce", round_no - 1, rounds=1)
        self.assertEqual(deal["term_end"], round_no)
        engine._end_round_upkeep(round_no)
        self.assertEqual(engine.state["deals"]["struck"][deal["id"]]["status"], "kept")
        engine.state["round"] = round_no + 1
        engine.state["agents"][a]["tile"], engine.state["agents"][b]["tile"] = [1, 1], [2, 1]
        engine._round_events = []
        engine._resolve_action(a, AgentAction(action="attack", target=b))
        engine._end_round_upkeep(round_no + 1)
        self.assertFalse(self.events(engine, "deal_broken"))

    def test_a_share_handed_over_is_kept_and_one_not_handed_over_by_its_round_is_a_break(self):
        a, b = self.ids[:2]
        engine = self.engine(round_no=3)
        state = engine.state
        deal = self.strike(engine, a, b, "share_item", 2, item="healing_tonic", by_round=4)
        rules.inventory_add(state, a, "healing_tonic")
        engine._resolve_action(a, AgentAction(action="give", target=b, item="healing_tonic"))
        engine._end_round_upkeep(3)
        self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "kept")
        self.assertFalse(self.events(engine, "deal_broken"))
        # the same promise, never kept
        engine = self.engine(name="unkept.db", round_no=3)
        state = engine.state
        deal = self.strike(engine, a, b, "share_item", 2, item="healing_tonic", by_round=4)
        engine._end_round_upkeep(3)
        self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "standing")
        state["round"] = 4
        engine._round_events = []
        engine._end_round_upkeep(4)
        broken = self.events(engine, "deal_broken")
        self.assertEqual([(e["actor_id"], e["target_id"], e["round_no"]) for e in broken], [(a, b, 4)])
        self.assertIn("never handed over the", broken[0]["public_text"])

    def test_an_escort_kept_by_arriving_together_and_broken_by_whoever_is_absent(self):
        a, b = self.ids[:2]
        engine = self.engine(round_no=3)
        state = engine.state
        deal = self.strike(engine, a, b, "escort", 2, destination="ironwood_gate", by_round=5)
        state["agents"][a]["room"] = state["agents"][b]["room"] = "ironwood_gate"
        engine._end_round_upkeep(3)
        self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "kept")
        # only a arrives: b broke it; a did not
        engine = self.engine(name="absent.db", round_no=5)
        state = engine.state
        deal = self.strike(engine, a, b, "escort", 2, destination="ironwood_gate", by_round=5)
        state["agents"][a]["room"] = "ironwood_gate"
        engine._end_round_upkeep(5)
        broken = self.events(engine, "deal_broken")
        self.assertEqual([(e["actor_id"], e["target_id"]) for e in broken], [(b, a)])
        self.assertEqual(state["deals"]["struck"][deal["id"]]["broken_by"], [b])
        # neither arrives: both broke it, one event each
        engine = self.engine(name="both.db", round_no=5)
        deal = self.strike(engine, a, b, "escort", 2, destination="ironwood_gate", by_round=5)
        engine._end_round_upkeep(5)
        broken = self.events(engine, "deal_broken")
        self.assertEqual(sorted((e["actor_id"], e["target_id"]) for e in broken), [(a, b), (b, a)])
        self.assertEqual(engine.state["deals"]["struck"][deal["id"]]["broken_by"], [a, b])

    def test_a_death_ends_a_deal_without_a_break_unless_the_partner_did_it(self):
        a, b = self.ids[:2]
        engine = self.engine(round_no=3)
        deal = self.strike(engine, a, b, "truce", 2, rounds=6)
        engine.state["agents"][b]["status"] = "eliminated"
        engine._end_round_upkeep(3)
        self.assertEqual(engine.state["deals"]["struck"][deal["id"]]["status"], "void")
        self.assertFalse(self.events(engine, "deal_broken"))
        # the partner's own killing blow inside the truce is the break, judged before the death
        round_no = rules.ACT_I_LAST_ROUND + 2
        engine = self.engine(name="killer.db", round_no=round_no)
        state = engine.state
        deal = self.strike(engine, a, b, "truce", round_no - 1, rounds=6)
        state["agents"][a]["tile"], state["agents"][b]["tile"] = [1, 1], [2, 1]
        state["agents"][b]["hp"] = 1
        state["agents"][a]["power"] = 20  # lands and kills, whatever the die
        engine._resolve_action(a, AgentAction(action="attack", target=b))
        engine._end_round_upkeep(round_no)
        if state["agents"][b]["status"] != "active":
            self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "broken")
            self.assertEqual(len(self.events(engine, "deal_broken")), 1)
        else:  # the d20 missed; still a break, still standing over a living partner
            self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "broken")


class TheCrownByHand(DealTestCase):
    def test_the_crown_can_be_handed_over_as_a_transfer_that_scores_nothing(self):
        """The deal path (PRD §10, D8's mechanics): a gift resets attunement,
        counts as a transfer, pays neither hand, and keeps a share_item deal."""
        a, b = self.ids[:2]
        engine = self.engine(round_no=10)
        state = engine.state
        state["monsters"]["crown_warden"]["hp"] = 0
        rules.crown_unlock(state, 9)
        rules.floor_remove(state, rules.VAULT_ROOM, rules.CROWN_ITEM_ID)
        rules.inventory_add(state, a, rules.CROWN_ITEM_ID)
        rules.crown_to_carrier(state, a)
        state["crown"]["attunement_rounds"] = 2
        for who in (a, b):
            state["agents"][who]["room"] = rules.VAULT_ROOM
        transfers = state["crown"]["transfers"]
        deal = self.strike(engine, a, b, "share_item", 9, item=rules.CROWN_ITEM_ID, by_round=10)
        obs = rules.visible_observation(deepcopy(state), a, "lorekeeper", [])
        self.assertTrue(any(e["action"] == "give" and e["item"] == rules.CROWN_ITEM_ID and e["target"] == b for e in obs["legal_actions"]))
        engine._resolve_action(a, AgentAction(action="give", target=b, item=rules.CROWN_ITEM_ID))
        self.assertEqual(state["crown"]["carrier_id"], b)
        self.assertEqual(state["crown"]["attunement_rounds"], 0)
        self.assertEqual(state["crown"]["transfers"], transfers + 1)
        self.assertNotIn(rules.CROWN_ITEM_ID, state["agents"][a]["inventory"])
        self.assertIn(rules.CROWN_ITEM_ID, state["agents"][b]["inventory"])
        taken = self.events(engine, "crown_taken")
        self.assertEqual(taken[-1]["actor_id"], b)
        self.assertEqual(taken[-1]["payload"]["via"], "given")
        self.assertEqual(taken[-1]["payload"]["points"], 0)
        for who in (a, b):
            self.assertNotIn("crown_taken", [r["category"] for r in engine.store.score_rows(engine.match_id, who)] if hasattr(engine.store, "score_rows") else [])
            self.assertEqual(state["agents"][who]["score"], 0)
        self.assertTrue(rules.crown_ledger_ok(state))
        engine._end_round_upkeep(10)
        self.assertEqual(state["deals"]["struck"][deal["id"]]["status"], "kept")


class TheMockDeals(DealTestCase):
    def test_the_mock_offers_accepts_and_breaks_so_the_seam_carries_every_event(self):
        """Seam 1: a whole mock match produces offers, acceptances, lapses and
        breaks, and the audit still validates."""
        engine, bundle = self.run_match(MockDecisionProvider(), rounds=rules.ACT_I_LAST_ROUND + 6, seed=52, name="mock.db")
        kinds = {e["event_type"] for e in bundle["events"]}
        for kind in ("offer_made", "deal_struck", "offer_lapsed"):
            self.assertIn(kind, kinds)
        self.assertTrue(self._stores[-1].verify_audit(engine.match_id)["valid"])
        final = bundle["snapshots"][-1]["state"]
        self.assertTrue(final["deals"]["offers"])
        self.assertTrue(final["deals"]["struck"])
        # every struck deal came from an offer made to its acceptor the round before or earlier
        for did, deal in final["deals"]["struck"].items():
            offer_rec = final["deals"]["offers"][did]
            self.assertEqual(offer_rec["status"], "struck")
            self.assertLess(offer_rec["made_round"], deal["struck_round"])


if __name__ == "__main__":
    unittest.main()


class AnAcceptThatNamesTheOfferer(DealTestCase):
    def test_to_and_type_on_an_accept_ride_along_and_must_match_the_offer(self):
        """The real match of 19 Sep 2026 lost turns to guard for an accept
        that named the offerer; now it is accepted, and one that names the
        wrong offerer or type is lost with the reason, never a penalty."""
        a, b, c = self.ids[:3]
        engine = self.engine()
        state = engine.state
        recorded, why = deals.record_offer(state, 1, a, offer(b, "truce", rounds=2))
        self.assertIsNone(why)
        self.assertEqual(deals.record_accept(state, 2, b, recorded["id"], {**accept(recorded["id"]), "to": c})[1], f"that offer was made by {a}, not {c}")
        self.assertEqual(deals.record_accept(state, 2, b, recorded["id"], {**accept(recorded["id"]), "type": "escort"})[1], "that offer is a truce, not a escort")
        struck, why = deals.record_accept(state, 2, b, recorded["id"], {**accept(recorded["id"]), "to": a, "type": "truce"})
        self.assertIsNone(why)
        self.assertEqual(struck["status"], "standing")
        # through the contract and the engine, as a brain sends it
        script = {(1, a): offer(b, "truce", rounds=2), (2, b): {**accept(f"offer-r1-{a}"), "to": a, "type": "truce"}}
        _, bundle = self.run_match(Scripted(script), rounds=3, name="clear.db")
        self.assertEqual(len(self.events(bundle, "deal_struck")), 1)
        self.assertFalse([d for d in bundle["decisions"] if d["validity"] != "valid"])
