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

    def test_the_thinking_is_carried_but_off_until_switched_on_and_no_dice_reach_the_page(self):
        page = replay_board.build(self.bundle)
        notes = [e for e in sorted(self.bundle["events"], key=lambda e: e["seq"]) if e["event_type"] == "note_written"]
        self.assertTrue(notes, "the mock wrote no notes, so this proves nothing")
        private = [f for f in self.frames if f.get("private")]
        self.assertEqual([f["seq"] for f in private], [e["seq"] for e in notes])
        self.assertEqual([f["objective"] for f in private], [e["payload"]["note"]["objective"] for e in notes])
        # every plan is in the page data, behind a switch that opens off
        for f in private[:20]:
            if f["objective"]:
                self.assertIn(f["objective"], page)
        self.assertIn('id="think" class="toggle" aria-pressed="false"', page)
        self.assertIn("body.think-on .card .think { display: block; }", page)
        # the plan reaches each character's card through the delta, so the roster follows the round
        for f in private[:20]:
            self.assertEqual(f["delta"]["agents"][f["actor"]]["note"]["objective"], f["objective"])
        # and the secret aim each carries is named from the manifest, with the engine's own wording
        for aid, a in self.start["agents"].items():
            self.assertTrue(a["secret"], aid)
            self.assertTrue(a["secret_text"].endswith("."), a["secret_text"])
        self.assertNotIn("d20 =", page)
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
