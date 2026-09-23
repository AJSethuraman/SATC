"""A version that comes from the code doing the work, not from a file about it.

THE DEFECT THIS ANSWERS HAS BITTEN FIVE TIMES. The Skill tool served a session
`desk/0.4.0/skills/ask-desk` on 8 September while the code was 0.9.x — five
releases back — and the version warning added in 0.7.3 to catch exactly that
lives in the SKILL.md that does not load. **A check cannot detect its own
staleness.** The desk that found it said where the check belongs:

    "That check must live in ask.py/relay.py, which IS current, or in the
     harness."

So `record.VERSION` is read from the manifest beside the module actually
imported, and it is stamped onto the two artifacts an agent always reads: the
brief it answers from, and the envelope it is sent. A skill claiming something
else is then visibly wrong rather than silently in charge.

WHAT THIS DOES NOT DO. It does not make a stale skill current, and it cannot —
nothing in this repository controls what the harness serves. It makes the
staleness VISIBLE at the moment it matters, which is the most this side can do.
"""
from pathlib import Path

import ask
import record
import relay

HERE = Path(__file__).resolve().parents[1]
ME = "session_01M1pBzTxE9u2xD6d8Yz57dV"


def test_the_version_is_the_manifest_beside_the_code():
    import json
    said = json.loads((HERE / ".claude-plugin" / "plugin.json")
                      .read_text(encoding="utf-8"))["version"]
    assert record.VERSION == said


def test_it_is_a_real_version_and_not_a_placeholder():
    parts = record.VERSION.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), record.VERSION


def test_a_missing_manifest_is_unknown_rather_than_an_error(monkeypatch, tmp_path):
    """A desk must not stop answering because a manifest moved. Empty says
    "unknown", which is honest; raising would make a cosmetic field fatal."""
    monkeypatch.setattr(record, "__file__", str(tmp_path / "record.py"))
    assert record._version() == ""


def test_the_brief_carries_it():
    """The brief is what an answerer reasons from — it is always read."""
    desk = record.load(HERE / "corpus")
    first = ask.brief("we bought a forklift", desk,
                      record.NOTHING_ON_FILE).splitlines()[0]
    assert record.VERSION in first, first


def test_the_envelope_carries_it_too():
    body = relay.as_prompt(relay.ask("a $10 bank charge", ME))
    assert f"Composed by desk {record.VERSION}" in body


def test_and_tells_the_desk_which_to_believe():
    """A version stamp nobody knows what to do with is decoration. The envelope
    says the message wins, because a stale skill cannot know it is stale."""
    body = relay.as_prompt(relay.ask("a $10 bank charge", ME))
    assert "follow THIS message" in body
    assert "a stale skill cannot know it is stale" in body


def test_the_record_name_survives_the_stamp():
    """A stamp that displaced the thing it annotates would be a regression.

    It read `# cash-and-bank`; `dec-kill` left one record and it is called
    `corpus`. What is being checked is that the version is APPENDED to the
    heading rather than replacing it, which is the same check either way.
    """
    desk = record.load(HERE / "corpus")
    first = ask.brief("q", desk, record.NOTHING_ON_FILE).splitlines()[0]
    assert first.startswith(f"# {desk.name}")
    assert record.VERSION in first, "the stamp is not on the heading at all"
