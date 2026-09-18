"""The board page (tools/replay_board.py) is the referee's board, or it refuses.

Built from a mock match so the suite needs no committed bundle. Proves:
the derived timeline matches every round-end snapshot; the checker can
fail (a mutated delta is caught); the page carries no private note; every
body has a token; the command line works.
"""
from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import replay_board  # noqa: E402
from arena.brains import load_brains  # noqa: E402
from arena.engine import ArenaEngine  # noqa: E402
from arena.providers import MockDecisionProvider  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402

HOUSE = ROOT / "brains" / "house"


def mock_bundle(tmp: Path, seed: int = 52) -> dict:
    store = ArenaStore(tmp / "board.db")
    engine = ArenaEngine(store, MockDecisionProvider(), parallel_agents=True)
    match_id = engine.run(load_brains(str(HOUSE)), seed=seed)
    bundle = store.replay_bundle(match_id)
    store.close()
    return bundle


class BoardIsTheRefereesBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = Path(tempfile.mkdtemp(prefix="board-"))
        cls.bundle = mock_bundle(cls.tmp)
        cls.start, cls.frames = replay_board.build_timeline(cls.bundle)

    def test_every_round_end_matches_the_snapshot(self):
        self.assertEqual(replay_board.verify(self.bundle, self.start, self.frames), [])
        rounds = {s["round_no"] for s in self.bundle["snapshots"] if s["phase"] == "end"}
        self.assertGreaterEqual(len(rounds), 3, "a mock match short enough to prove nothing")

    def test_the_checker_can_fail(self):
        frames = copy.deepcopy(self.frames)
        moved = next(f for f in frames if f["type"] in ("move", "step"))
        aid = moved["actor"]
        moved["delta"].setdefault("agents", {}).setdefault(aid, {})["tile"] = [0, 0]
        moved["delta"]["agents"][aid]["hp"] = 1
        problems = replay_board.verify(self.bundle, self.start, frames)
        self.assertTrue(any(aid in p for p in problems), problems)

    def test_everyone_thinks_at_once_before_anyone_speaks_or_moves(self):
        page = replay_board.build(self.bundle)
        events = sorted(self.bundle["events"], key=lambda e: e["seq"])
        notes_by_round = {}
        for e in events:
            if e["event_type"] == "note_written":
                notes_by_round.setdefault(e["round_no"], []).append(e)
        self.assertTrue(notes_by_round, "the mock wrote no notes, so this proves nothing")
        thinks = [f for f in self.frames if f["type"] == "everyone_thinks"]
        # one moment per round, holding every plan of that round in the order written
        self.assertEqual([f["round"] for f in thinks], sorted(notes_by_round))
        for f in thinks:
            notes = notes_by_round[f["round"]]
            self.assertEqual([t["who"] for t in f["thoughts"]], [n["actor_id"] for n in notes])
            self.assertEqual([t["objective"] for t in f["thoughts"]], [n["payload"]["note"]["objective"] for n in notes])
            # and every plan reaches its character through the frame's delta
            for t in f["thoughts"]:
                self.assertEqual(f["delta"]["agents"][t["who"]]["note"]["objective"], t["objective"])
        # it comes before any line spoken or action taken in its round
        for f in thinks:
            same_round = [x for x in self.frames if x["round"] == f["round"] and x["type"] not in ("round_started", "act_started", "room_contracting")]
            self.assertIs(same_round[0], f, [x["type"] for x in same_round[:3]])
        self.assertFalse([f for f in self.frames if f["type"] == "note_written"])
        # the secret aim each carries is named from the manifest, with the engine's own wording
        for aid, a in self.start["agents"].items():
            self.assertTrue(a["secret"], aid)
            self.assertTrue(a["secret_text"].endswith("."), a["secret_text"])
        # the dice reach the page on the cards (the firm asked to see them rolled), never as steps of their own
        self.assertFalse([f for f in self.frames if f["type"] == "dice_roll"])
        self.assertNotIn('id="think"', page)
        types = {f["type"] for f in self.frames}
        self.assertFalse(types & replay_board.SKIP, types & replay_board.SKIP)

    def test_every_body_has_a_token_and_every_line_spoken_is_there(self):
        page = replay_board.build(self.bundle)
        for aid in self.start["agents"]:
            self.assertIn(f'id="tok-{aid}"', page)
            self.assertIn(f'id="card-{aid}"', page)
        for mid in self.start["monsters"]:
            self.assertIn(f'id="tok-{mid}"', page)
        spoken = [e["payload"]["speech"] for e in self.bundle["events"] if e["event_type"] == "agent_speech"]
        self.assertTrue(spoken)
        said = [f["speech"] for f in self.frames if f["type"] == "agent_speech"]
        self.assertEqual(said, spoken)
        self.assertIn("<title>", page)
        self.assertLess(len(page.encode()), 16 * 1024 * 1024)

    def test_following_one_character_gives_one_card_per_round_with_thought_said_did_and_happened(self):
        turns = replay_board.build_turns(self.start, self.frames)
        rounds = sorted({f["round"] for f in self.frames if f["round"] >= 1})
        events = sorted(self.bundle["events"], key=lambda e: e["seq"])
        self.assertEqual(set(turns), set(self.start["agents"]))
        for aid, cards in turns.items():
            self.assertEqual([c["round"] for c in cards], rounds)
            for c in cards:
                rnd = c["round"]
                notes = [e for e in events if e["event_type"] == "note_written" and e["round_no"] == rnd and e["actor_id"] == aid]
                said = [e for e in events if e["event_type"] == "agent_speech" and e["round_no"] == rnd and e["actor_id"] == aid]
                self.assertEqual(c["thought"], notes[0]["payload"]["note"]["objective"] if notes else "")
                self.assertEqual(c["said"], said[0]["payload"]["speech"] if said else None)
                # what they did is the round's action frames for them, in order, each carrying the referee's line
                did_frames = [f for f in self.frames if f["round"] == rnd and f["actor"] == aid and f["type"] in replay_board.DID]
                self.assertEqual(c["did"], [f["text"] for f in did_frames])
                did_events = [e for e in events if e["round_no"] == rnd and e["actor_id"] == aid and e["event_type"] in replay_board.DID
                              and not (e["event_type"] == "item_taken" and e["target_id"] == "ember_crown")]
                self.assertEqual(len(did_frames), len(did_events))
                for text, e in zip(c["did"], did_events):
                    self.assertTrue(text.startswith(e["public_text"]), (text, e["public_text"]))
                hits_on_me = [e["public_text"] for e in events if e["round_no"] == rnd and e["event_type"] == "attack_hit" and e["target_id"] == aid]
                for text in hits_on_me:
                    self.assertIn(text, c["happened"])
                self.assertEqual(self.frames[c["end"]]["round"], rnd)
                # the card's HP is the referee's HP at the end of the round
                snap = next(s for s in self.bundle["snapshots"] if s["round_no"] == rnd and s["phase"] == "end")
                self.assertEqual(c["hp_after"], snap["state"]["agents"][aid]["hp"])
                self.assertEqual(c["status_after"], snap["state"]["agents"][aid]["status"])
        # something was said and something was done, or the mock proved nothing
        self.assertTrue(any(c["said"] for cards in turns.values() for c in cards))
        self.assertTrue(any(c["did"] for cards in turns.values() for c in cards))
        page = replay_board.build(self.bundle)
        self.assertIn('data-follow=""', page)
        for aid in self.start["agents"]:
            self.assertIn(f'data-follow="{aid}"', page)

    def test_the_story_runs_in_match_order_one_character_at_a_time(self):
        turns = replay_board.build_turns(self.start, self.frames)
        story = replay_board.build_story(self.start, self.frames, turns)
        rounds = sorted({f["round"] for f in self.frames if f["round"] >= 1})
        # rounds never go backwards, and every round has its cards
        self.assertEqual([e["round"] for e in story], sorted(e["round"] for e in story))
        self.assertEqual(sorted({e["round"] for e in story if e["kind"] == "turn"}), rounds)
        for rnd in rounds:
            entries = [e for e in story if e["round"] == rnd and e["kind"] == "turn"]
            order_frame = next((f for f in self.frames if f["round"] == rnd and f["type"] == "initiative_order"), None)
            active = [aid for aid, cards in turns.items() if not next(c for c in cards if c["round"] == rnd)["out_before"]]
            # one card per character still in the match, in the order the referee rolled
            self.assertEqual(sorted(e["who"] for e in entries), sorted(active))
            if order_frame and order_frame.get("order"):
                expected = [a for a in order_frame["order"] if a in active] + [a for a in active if a not in order_frame["order"]]
                self.assertEqual([e["who"] for e in entries], expected)
            for e in entries:
                # the board stands at that character's last action of the round, or at the thinking moment
                bf = self.frames[e["board"]]
                self.assertEqual(bf["round"], rnd)
                did = [i for i, f in enumerate(self.frames) if f["round"] == rnd and f.get("actor") == e["who"] and f["type"] in replay_board.DID]
                self.assertEqual(e["board"], did[-1] if did else next(i for i, f in enumerate(self.frames) if f["round"] == rnd and f["type"] == "everyone_thinks"))
            # a monster that struck appears in the vault's beat for the round
            monster_blows = [f["text"] for f in self.frames if f["round"] == rnd and f.get("actor") in self.start["monsters"] and f["type"] in ("attack_hit", "attack_miss")]
            vault = [e for e in story if e["round"] == rnd and e["kind"] == "vault"]
            for text in monster_blows:
                self.assertIn(text, vault[0]["texts"])
        self.assertEqual(story[-1]["kind"], "end")
        self.assertEqual(story[0]["kind"], "scene")
        page = replay_board.build(self.bundle)
        self.assertIn('data-follow="*"', page)
        self.assertIn('setMode("*")', page)
        # voices come from the browser's own speech and nothing leaves the machine: no audio host, no key
        self.assertIn('id="voice"', page)
        self.assertIn("speechSynthesis", page)
        self.assertNotIn("api.elevenlabs", page)
        self.assertNotIn("audio/", page)

    def test_every_die_the_referee_rolled_for_a_character_is_on_their_card_with_what_it_decided(self):
        turns = replay_board.build_turns(self.start, self.frames, self.bundle)
        events = sorted(self.bundle["events"], key=lambda e: e["seq"])
        rolled = {}
        for e in events:
            if e["event_type"] == "dice_roll":
                rolled.setdefault((e["round_no"], e["actor_id"]), []).append(e["payload"]["proof"])
        self.assertTrue(rolled, "the mock rolled nothing, so this proves nothing")
        seen = 0
        for aid, cards in turns.items():
            for c in cards:
                proofs = rolled.get((c["round"], aid), [])
                self.assertEqual([(d["sides"], d["result"]) for d in c["dice"]], [(p["sides"], p["result"]) for p in proofs])
                seen += len(c["dice"])
                for d in c["dice"]:
                    self.assertIn(f"d{d['sides']} = {d['result']}", d["text"])
        self.assertGreater(seen, 0)
        # a to-hit die says what it was against and whether it hit, from the attack it decided
        hits = [e for e in events if e["event_type"] in ("attack_hit", "attack_miss") and e["actor_id"] in self.start["agents"]]
        self.assertTrue(hits)
        for e in hits[:10]:
            th = e["payload"]["tohit"]
            card = next(c for c in turns[e["actor_id"]] if c["round"] == e["round_no"])
            die = next(d for d in card["dice"] if d["kind"] == "tohit" and d["result"] == th["roll"] and d["target"] == e["target_id"])
            self.assertIn(f"against {th['dc']['value']}", die["text"])
            self.assertIn("hit" if th["hit"] else "miss", die["text"].rsplit(":", 1)[-1])
        # a monster's dice ride on the vault's beat
        story = replay_board.build_story(self.start, self.frames, turns, self.bundle)
        for e in [x for x in story if x["kind"] == "vault"]:
            expected = [(p["sides"], p["result"]) for mid in self.start["monsters"] for p in rolled.get((e["round"], mid), [])]
            self.assertEqual([(d["sides"], d["result"]) for d in e["dice"]], expected)
        page = replay_board.build(self.bundle)
        self.assertIn('id="t-dice"', page)

    def test_the_opening_explains_the_rules_and_the_vaults_own(self):
        scene = replay_board.build_scene(self.bundle, self.start)
        first = self.bundle["snapshots"][0]["state"]
        self.assertEqual([n["name"] for n in scene["npcs"]], [m["name"] for m in first["monsters"].values()])
        for n in scene["npcs"]:
            mo = next(m for m in first["monsters"].values() if m["name"] == n["name"])
            self.assertEqual((n["hp"], n["power"], n["armor"], n["reach"]), (mo["max_hp"], mo["power"], mo["armor"], mo["reach"]))
        rules = " ".join(scene["rules"])
        from arena import combat, models, scoring
        self.assertIn(f"against {combat.DC_BASE} +", rules)
        self.assertIn(f"secret aim met {scoring.SCORING['secret_objective']}", rules)
        self.assertIn(f"+{replay_board.GUARD_BONUS} against", rules)
        for bname, bd in models.BUILDS.items():
            self.assertEqual(scene["builds"][bname]["hp"], bd["max_hp"])
            self.assertEqual(scene["builds"][bname]["moves"], 1 + bd["speed"])
        for a in scene["eight"]:
            self.assertIn(f"{scene['builds'][a['build']]['hp']} HP", a["stats"])

    def test_a_room_reaction_reads_as_one_line_naming_everyone_it_caught(self):
        # the engine logs one event per body a room's burst reaches, all worded alike and naming nobody;
        # the swinger's card folds them into one line, and each victim's card says whose swing it was
        ids = list(self.start["agents"])
        a, v1, v2, v3 = ids[0], ids[1], ids[2], ids[3]
        n = {k: self.start["agents"][k]["name"] for k in ids}
        flare = "The ember-glass flares and the heat lashes everything near the plinth."
        frames = [{"seq": 1, "round": 1, "type": "attack_miss", "actor": a, "target": v1, "text": f"{n[a]} swings at {n[v1]}, misses, and the arena takes it personally.", "delta": {}}]
        for i, v in enumerate((v1, v2, v3)):
            frames.append({"seq": 2 + i, "round": 1, "type": "wild_swing_room_reaction", "actor": a, "target": v, "amount": 1,
                           "base_text": flare, "text": f"{flare} It catches {n[v]} for 1.",
                           "delta": {"agents": {v: {"hp": self.start["agents"][v]["hp"] - 1}}}})
        turns = replay_board.build_turns(self.start, frames)
        card = turns[a][0]
        self.assertEqual(card["did"], [frames[0]["text"], f"{flare} It catches {n[v1]} for 1, {n[v2]} for 1, {n[v3]} for 1."])
        for v in (v1, v2, v3):
            caught = f"{flare} It catches {n[v]} for 1. From {n[a]}'s wild swing."
            # the one swung at also sees the miss on their card; the bystanders see only the burst
            self.assertEqual(turns[v][0]["happened"], [frames[0]["text"], caught] if v == v1 else [caught])
            self.assertEqual(turns[v][0]["hp_after"], self.start["agents"][v]["hp"] - 1)
        # and the timeline names the victim on such a frame when the record carries one
        for f in self.frames:
            if f["type"] == "wild_swing_room_reaction" and f.get("base_text"):
                self.assertIn(" It catches ", f["text"])

    def test_the_scene_is_set_from_the_record_and_nothing_else(self):
        scene = replay_board.build_scene(self.bundle, self.start)
        first = self.bundle["snapshots"][0]["state"]
        self.assertEqual([r["name"] for r in scene["rooms"]], [first["rooms"][k]["name"] for k in ("threshold", "ironwood_gate", "ossuary_gate", "vault", "egress")])
        for r in scene["rooms"]:
            self.assertEqual(r["desc"], first["rooms"][r["id"]]["description"])
        self.assertTrue(any(str(self.bundle["match"]["max_rounds"]) in t for t in scene["rules"]))
        for s in first["contraction"]["schedule"]:
            self.assertTrue(any(f"round {s['round']}" in t for t in scene["rules"]), s)
        self.assertEqual([a["who"] for a in scene["eight"]], list(self.start["agents"]))
        wants = {p["manifest"]["id"]: p["manifest"]["wants"] for p in self.bundle["participants"]}
        for a in scene["eight"]:
            self.assertTrue(wants[a["who"]].startswith(a["wants"].rstrip(".")), (a["wants"], wants[a["who"]][:80]))
            self.assertEqual(a["secret"], self.start["agents"][a["who"]]["secret"])
        page = replay_board.build(self.bundle)
        for r in scene["rooms"]:
            self.assertIn(r["desc"].split(".")[0], page)

    def test_rooms_are_drawn_to_the_engine_grid(self):
        from arena import grid
        page = replay_board.build(self.bundle)
        for room, g in grid.ROOM_GRIDS.items():
            self.assertIn(f'id="floor-{room}"', page)
            tiles = re.findall(rf'<rect class="tile[^"]*" x="[^"]+" y="[^"]+" width="{replay_board.TILE - 2}"', page)
        self.assertEqual(len(tiles), sum(g["w"] * g["h"] for g in grid.ROOM_GRIDS.values()))
        for room, props in grid.ROOM_PROPS.items():
            for prop in props.values():
                self.assertIn(prop["name"], page)

    def test_the_command_line_writes_the_same_page_and_refuses_a_bad_bundle(self):
        src = self.tmp / "bundle.json"
        src.write_text(json.dumps(self.bundle), encoding="utf-8")
        out = self.tmp / "board.html"
        self.assertEqual(replay_board.main([str(src), str(out), "--note", "Played under the July ending rule."]), 0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("Played under the July ending rule.", text)
        bad = copy.deepcopy(self.bundle)
        end = next(s for s in bad["snapshots"] if s["phase"] == "end")
        first = next(iter(end["state"]["agents"].values()))
        first["hp"] = first["hp"] + 99
        src.write_text(json.dumps(bad), encoding="utf-8")
        self.assertEqual(replay_board.main([str(src), str(self.tmp / "bad.html")]), 2)
        self.assertFalse((self.tmp / "bad.html").exists())


if __name__ == "__main__":
    unittest.main()
