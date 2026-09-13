"""The gate pack (PRD §5.43-45): readable, anonymous, and scorable.

The 12 Sep 2026 model run committed its answer key inside the readers' folder,
so anyone browsing the pull request could read it; the key now sits beside the
pack and outside source control. The leak check that was done by hand on that
pack (no house name or id in any transcript or brain) is pinned here.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from arena.brains import load_brains
from tools import gate, score_gate

HOUSE = gate.ROOT / "brains" / "house"


def _pack(tmp: str) -> Path:
    args = SimpleNamespace(provider="mock", brains=str(HOUSE), seeds=1, first_seed=101,
                           rounds=1, build="scout", out=tmp)
    with contextlib.redirect_stdout(io.StringIO()):
        return gate.run(args)


class GatePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pack = _pack(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_key_is_beside_the_pack_and_not_in_it(self):
        self.assertFalse((self.pack / "KEY.json").exists())
        key_file = gate.key_path(self.pack)
        self.assertTrue(key_file.exists())

        self.assertEqual(key_file.parent, self.pack.parent)
        key = json.loads(key_file.read_text(encoding="utf-8"))
        numbers = key["letter_to_brain_number"]
        self.assertEqual(sorted(numbers), list("ABCDEFGH"))
        self.assertEqual(sorted(numbers.values()), list(range(1, 9)))
        # nothing a reader receives names the key file's contents
        for f in ("README.md", "ANSWER_SHEET.md"):
            self.assertNotIn("KEY.json", (self.pack / f).read_text(encoding="utf-8"))

    def test_no_house_name_or_id_reaches_a_reader(self):
        manifests = load_brains(str(HOUSE))
        tokens = set()
        for m in manifests:
            tokens.update({m.id, m.name})
            tokens.update(t for t in re.split(r"[\s\-_]+", m.name) if len(t) >= 4 and t.lower() not in gate.COMMON)
        readers_see = list((self.pack / "transcripts").glob("*.md")) + list((self.pack / "brains").glob("*.md"))
        self.assertEqual(len(readers_see), 16)
        for path in readers_see:
            text = path.read_text(encoding="utf-8")
            for token in tokens:
                self.assertIsNone(re.search(rf"\b{re.escape(token)}\b", text, re.I), f"{token!r} in {path.name}")

    def test_the_full_match_records_are_kept_beside_the_pack_and_not_in_it(self):
        """Every event and every round's state, one JSON per seed, with real
        names: beside the pack with the key, so a reader's pack stays blind
        and the firm can still replay a gate match in full."""
        replays = gate.replays_dir(self.pack)
        self.assertTrue(replays.is_dir())
        files = sorted(replays.glob("*.json"))
        self.assertEqual([f.name for f in files], ["101.json"])
        bundle = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(set(bundle) >= {"match", "events", "snapshots", "participants"}, True)
        self.assertEqual(bundle["match"]["seed"], 101)
        self.assertFalse(any(p.suffix == ".json" for p in self.pack.rglob("*") if "replay" in p.name.lower()))
        # and the pack folder itself holds no bundle
        self.assertFalse((self.pack / "replays").exists())

    def test_scorer_reads_the_key_beside_the_pack_and_inside_an_older_one(self):
        key = json.loads(gate.key_path(self.pack).read_text(encoding="utf-8"))["letter_to_brain_number"]
        perfect = self.pack / "reader_a.json"
        perfect.write_text(json.dumps(key), encoding="utf-8")
        wrong = self.pack / "reader_b.json"
        wrong.write_text(json.dumps({L: 1 for L in key}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = score_gate.main(["score_gate.py", str(self.pack), str(perfect), str(wrong)])
        self.assertEqual(code, 1)
        self.assertIn("reader A 8 of 8, reader B 1 of 8: FAIL", out.getvalue())
        # an older pack, key inside: still scores
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "20260912-034624-agent_sdk"
            old.mkdir()
            (old / "KEY.json").write_text(json.dumps({"letter_to_brain_number": key}), encoding="utf-8")
            self.assertEqual(score_gate.find_key(old), old / "KEY.json")
            self.assertEqual(score_gate.score(old, perfect)[0], 8)


def test_blind_read_page_carries_no_key_and_no_real_id(tmp_path):
    """The page a reader answers on is built from the pack alone. Nothing the
    key holds may reach it: not a brain number beside a letter, not a real
    character id (four letters or more; the anonymiser skips shorter tokens
    on purpose, so `fen` inside `fence` is not a leak)."""
    import json
    from tools import blind_read_page

    pack = gate.ROOT / "gate" / "20260912-034624-agent_sdk"
    key = json.loads(score_gate.find_key(pack).read_text(encoding="utf-8"))
    page = blind_read_page.build(pack, reader="test")
    assert "letter_to_brain" not in page and "letter_to_id" not in page
    for real_id in key["letter_to_id"].values():
        if len(real_id) >= 4:
            assert real_id.lower() not in page.lower(), real_id
    assert page.count("<details") == page.count("</details>") == 8
    assert len(re.findall(r'data-letter="[A-H]"', page)) == 64
    assert 'db.doc("reads/test")' in page
    out = tmp_path / "read.html"
    assert blind_read_page.main([str(pack), str(out), "--reader", "test"]) == 0
    assert out.read_text(encoding="utf-8") == page


def test_replay_page_interleaves_the_pack_and_carries_no_key(tmp_path):
    """The replay page re-joins the eight per-character transcripts by seed
    and round so a reader sees all eight in one moment. Same leak rule as
    the blind-read page: nothing the key holds may reach it."""
    import json
    from tools import replay_page

    pack = gate.ROOT / "gate" / "20260912-034624-agent_sdk"
    key = json.loads(score_gate.find_key(pack).read_text(encoding="utf-8"))
    matches = replay_page.interleave(pack)
    assert [m["seed"] for m in matches] == ["Seed 101", "Seed 102", "Seed 103"]
    assert all(len(m["rounds"]) == 6 for m in matches)
    # every round carries an entry for every letter: a dict while on the board, None once gone
    for m in matches:
        for r in m["rounds"]:
            assert set(r["chars"]) == set("ABCDEFGH")
    # 136 decisions across the pack: the gate's own count of answered calls
    assert sum(1 for m in matches for r in m["rounds"] for c in r["chars"].values() if c) == 136
    page = replay_page.build(pack, "https://example.invalid/read")
    assert "letter_to_brain" not in page and "letter_to_id" not in page
    for real_id in key["letter_to_id"].values():
        if len(real_id) >= 4:
            assert real_id.lower() not in page.lower(), real_id
    out = tmp_path / "replay.html"
    assert replay_page.main([str(pack), str(out), "--blind-read-url", "https://example.invalid/read"]) == 0
    assert out.read_text(encoding="utf-8") == page


def test_replay_page_from_a_bundle_shows_every_recorded_event_in_order(tmp_path):
    """From a full match record the page carries what the pack cannot: every
    move, swing, monster step and narration, in sequence, with a state strip
    at the end of each round. Checked on the mock's committed seed-52 bundle."""
    from tools import replay_page

    bundle = replay_page.load_bundle(gate.ROOT / "demo" / "replay.json")
    page = replay_page.build_from_bundle(bundle)
    rounds = sorted({e["round_no"] for e in bundle["events"] if e["round_no"] >= 1})
    assert page.count('<h2 class="round">') == len(rounds) == 12
    # public lines that are not speech, notes, dice or bookkeeping all appear, in order
    shown = [e["public_text"] for e in sorted(bundle["events"], key=lambda e: e["seq"])
             if e["event_type"] not in replay_page.SKIP | {"agent_speech", "note_written", "round_narration", "act_started"}]
    pos = -1
    for text in shown:
        nxt = page.find(replay_page.E(text), pos + 1)
        assert nxt > pos, text
        pos = nxt
    assert page.count('class="state"') == len(rounds)
    assert "Ironwood Guardian falls." in page
    assert page.count('class="ev dice"') == sum(1 for e in bundle["events"] if e["event_type"] == "dice_roll")
    winner = next(p["manifest"]["name"] for p in bundle["participants"] if p["manifest"]["id"] == bundle["match"]["winner_agent_id"])
    assert winner in page
    out = tmp_path / "full.html"
    assert replay_page.main([str(gate.ROOT / "demo" / "replay.json"), str(out)]) == 0
    assert out.read_text(encoding="utf-8") == page


if __name__ == "__main__":
    unittest.main()
