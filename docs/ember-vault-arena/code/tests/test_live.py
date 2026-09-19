"""The live page (M4, PRD §5.35–38, built 19 Sep 2026): the engine says when
a round has ended; the local server serves the board's data for the
completed rounds after a given one, a stream of round events, and the page
itself; the page plays a running match one round behind the referee and
keeps going as rounds arrive. Everything here runs a real mock match on a
real store while a real HTTP server serves it."""
from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arena import rules  # noqa: E402
from arena.demo import load_manifests  # noqa: E402
from arena.engine import ArenaEngine  # noqa: E402
from arena.providers import MockDecisionProvider  # noqa: E402
from arena.server import ArenaHTTPServer  # noqa: E402
from arena.storage import ArenaStore  # noqa: E402
from tools import replay_board  # noqa: E402


class SlowMock(MockDecisionProvider):
    """The mock, a little slower, so a match is under way while a client watches."""

    def __init__(self, delay: float):
        self.delay = delay

    def decide(self, manifest, prompt, observation):
        time.sleep(self.delay)
        return super().decide(manifest, prompt, observation)


class TheEngineSaysWhenARoundHasEnded(unittest.TestCase):
    def test_on_start_and_on_round_fire_in_order_after_the_snapshot_is_committed(self):
        with tempfile.TemporaryDirectory() as d:
            store = ArenaStore(Path(d) / "cb.db")
            engine = ArenaEngine(store, MockDecisionProvider(), max_rounds=3, parallel_agents=False)
            seen: list = []
            engine.on_start = lambda mid: seen.append(("start", mid, store.rounds_complete(mid)))
            engine.on_round = lambda n: seen.append(("round", n, store.rounds_complete(engine.match_id), store.match_status(engine.match_id)))
            match_id = engine.run(load_manifests(), seed=4)
            store.close()
        self.assertEqual(seen[0], ("start", match_id, 0))
        self.assertEqual([s[1] for s in seen[1:]], [1, 2, 3])
        for _, n, complete, status in seen[1:]:
            self.assertEqual(complete, n)  # the end snapshot is already there when the presenter hears of it
            self.assertEqual(status, "running")


class TheBoardSlicedByCompletedRounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        store = ArenaStore(Path(cls.tmp.name) / "s.db")
        engine = ArenaEngine(store, MockDecisionProvider(), max_rounds=6, parallel_agents=True)
        cls.match_id = engine.run(load_manifests(), seed=52)
        cls.bundle = store.replay_bundle(cls.match_id)
        store.close()
        cls.full_start, cls.full_frames = replay_board.build_timeline(cls.bundle)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_running_match_shows_only_its_completed_rounds_and_no_end(self):
        running = replay_board.trim_bundle(self.bundle, 4)
        self.assertEqual(running["match"]["status"], "running")
        self.assertIsNone(running["match"]["winner_agent_id"])
        data = replay_board.live_data(running, 0)
        self.assertEqual(data["rounds_complete"], 4)
        self.assertEqual(data["status"], "running")
        self.assertIsNone(data["winner"])
        self.assertEqual(sorted({f["round"] for f in data["frames"]}), [0, 1, 2, 3, 4])
        self.assertFalse([e for e in data["story"] if e["kind"] == "end"])
        self.assertEqual(data["story"][0]["kind"], "scene")
        self.assertTrue(all(c["round"] <= 4 for cards in data["turns"].values() for c in cards))
        self.assertIn("start", data)
        self.assertIn("scene", data)
        # the frames are the full record's prefix, index for index
        self.assertEqual(data["frames"], self.full_frames[: len(data["frames"])])

    def test_the_rounds_after_a_point_continue_the_page_s_own_list(self):
        first = replay_board.live_data(self.bundle, 0)
        more = replay_board.live_data(self.bundle, 4)
        self.assertNotIn("start", more)
        self.assertEqual(sorted({f["round"] for f in more["frames"]}), [5, 6])
        self.assertEqual(more["status"], "completed")
        self.assertTrue(more["winner"])
        prefix = [f for f in first["frames"] if f["round"] <= 4]
        self.assertEqual(prefix + more["frames"], self.full_frames)
        self.assertEqual([e["kind"] for e in more["story"]][-1], "end")
        self.assertTrue(all(e.get("round", 0) > 4 for e in more["story"]))
        for who, cards in more["turns"].items():
            self.assertEqual([c["round"] for c in cards], [5, 6])
            # a card's board index points into the concatenated list, not past it
            for c in cards:
                self.assertLess(c["end"], len(prefix) + len(more["frames"]))
                self.assertGreaterEqual(c["end"], len(prefix))

    def test_the_live_page_carries_its_pull_urls_and_what_it_already_has(self):
        live = {"match_id": self.match_id, "board": "/b", "sse": "/s", "poll_ms": 100}
        page = replay_board.build(replay_board.trim_bundle(self.bundle, 3), live=live)
        self.assertIn('"live":{', page)
        self.assertIn('"after":3', page)
        self.assertIn('"status":"running"', page)
        self.assertIn("Live. ", page)
        self.assertIn("EventSource", page)
        self.assertLess(len(page.encode()), 16 * 1024 * 1024)


class TheServerServesARunningMatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "live.db"
        self.serving = ArenaStore(self.path)
        self.server = ArenaHTTPServer(("127.0.0.1", 0), self.serving, stream_interval=0.05)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.serving.close()
        self.tmp.cleanup()

    def get(self, path, timeout=10):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status, resp.getheader("Content-Type", ""), body

    def test_the_board_arrives_round_by_round_never_ahead_of_the_referee_and_the_stream_says_when(self):
        manifests = load_manifests()
        holder: dict = {}
        started = threading.Event()

        def play():
            store = ArenaStore(self.path)
            engine = ArenaEngine(store, SlowMock(0.01), max_rounds=5, parallel_agents=False)
            engine.on_start = lambda mid: (holder.__setitem__("id", mid), started.set())
            engine.run(manifests, seed=9)
            store.close()

        runner = threading.Thread(target=play, daemon=True)
        runner.start()
        self.assertTrue(started.wait(20))
        match_id = holder["id"]
        # the page itself, mid-match
        status, ctype, body = self.get(f"/live/{match_id}")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"__REPLAY__", body)
        self.assertIn(b'"live":{', body)
        # pull the board as the rounds end
        after, got, seen_rc = 0, [], []
        deadline = time.time() + 60
        while time.time() < deadline:
            status, ctype, body = self.get(f"/api/matches/{match_id}/board?after={after}")
            self.assertEqual(status, 200, body[:200])
            data = json.loads(body)
            self.assertLessEqual(data["rounds_complete"], self.serving.rounds_complete(match_id))
            self.assertLessEqual(data["rounds_complete"], 5)
            if data["rounds_complete"] > after:
                self.assertTrue(all(f["round"] > after or (after == 0 and f["round"] == 0) for f in data["frames"]))
                got.extend(data["frames"])
                seen_rc.append(data["rounds_complete"])
                after = data["rounds_complete"]
            if data["status"] == "completed":
                break
            time.sleep(0.05)
        runner.join(30)
        self.assertEqual(seen_rc, sorted(seen_rc))
        self.assertEqual(after, 5)
        # what arrived in pieces is the whole record's board
        full = self.serving.replay_bundle(match_id, reveal=True)
        _, frames = replay_board.build_timeline(full)
        self.assertEqual([f["seq"] for f in got], [f["seq"] for f in frames])
        # the stream on a finished match: a round event and then done
        status, ctype, body = self.get(f"/api/matches/{match_id}/live", timeout=10)
        self.assertEqual(status, 200)
        self.assertIn("text/event-stream", ctype)
        text = body.decode()
        self.assertIn("event: round", text)
        self.assertIn("event: done", text)
        self.assertIn('"rounds_complete": 5', text)

    def test_the_presenter_sees_the_notes_mid_match_and_the_public_replay_does_not(self):
        store = ArenaStore(self.path)
        engine = ArenaEngine(store, MockDecisionProvider(), max_rounds=2, parallel_agents=False)
        engine.run(load_manifests(), seed=3)
        match_id = engine.match_id
        # freeze it as if still running: the store keeps status running until finalize; simulate by reading the two views
        public = store.replay_bundle(match_id)          # completed: revealed
        self.assertFalse(public["redacted"])
        running_public = store.replay_bundle(match_id, reveal=False)
        self.assertTrue(running_public["redacted"])
        notes_public = [e for e in running_public["events"] if e["event_type"] == "note_written"]
        self.assertTrue(notes_public)
        self.assertTrue(all("note" not in (e["payload"] or {}) or not (e["payload"].get("note") or {}).get("objective") for e in notes_public))
        shown = replay_board.live_data(store.replay_bundle(match_id, reveal=True), 0)
        thinks = [f for f in shown["frames"] if f["type"] == "everyone_thinks"]
        self.assertTrue(thinks and all(t["objective"] for t in thinks[0]["thoughts"]))
        store.close()


if __name__ == "__main__":
    unittest.main()
