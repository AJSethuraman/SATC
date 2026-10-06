"""The asking skill says send every question, then wait — never stop sending.

SARCIA PILOT 2, 25 September 2026. The doer wrote seven questions, sent three
and stopped, and named the line it followed: "Then end your turn [...] Do not
poll." That line is about WAITING for an answer. It was read as "stop sending",
and four questions were left written and unsent. The same doer had also been
creating triggers without firing them, so its earlier messages may never have
reached anyone.

A skill is prose an agent executes (see `test_the_skills_call_functions_that_
exist.py`), so the wording that failed is pinned here the way a behaviour would
be: the corrected instruction must be present, and the one it replaced must not
come back.
"""
from __future__ import annotations

from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
ASK = (SKILLS / "ask-desk" / "SKILL.md").read_text(encoding="utf-8")
BE = (SKILLS / "be-the-desk" / "SKILL.md").read_text(encoding="utf-8")


def test_it_says_send_everything_before_ending_the_turn():
    assert "Send everything first. Then end your turn." in ASK
    assert "never means stop sending" in ASK


def test_it_says_created_is_not_sent():
    assert "created AND fired" in ASK
    assert "Created alone goes nowhere" in ASK


def test_it_teaches_the_batch_and_how_to_read_one():
    for needed in ("relay.ask_many(", "relay.batch_prompt(", "relay.read_batch(",
                   "got.missing"):
        assert needed in ASK, f"ask-desk no longer shows {needed}"


def test_one_question_per_envelope_is_gone():
    """The rule that made every question cost a whole envelope."""
    assert "**4 · One question per envelope.**" not in ASK


def test_the_desk_is_told_how_to_answer_a_batch():
    assert "A request may carry several questions" in BE
    assert "do not retype it" in BE
