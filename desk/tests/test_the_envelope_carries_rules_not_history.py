"""The question envelope carries the rules an answerer acts on, and nothing else.

SARCIA PILOT 2, 25 SEPTEMBER 2026. The envelope was 6,082 characters to deliver
an 87-character question, and 45 per cent of it was the history of how each rule
was learned. The platform echoes a trigger's prompt back several times on every
create and fire, so each question cost the ASKING session roughly 20,000
characters of context. Occam, already near a full context, sent three questions
of seven and stopped, and gave cost as one of its two reasons.

So the envelope was cut to its rules, 6,082 -> 2,990, and every rule it stated is
still stated — the other envelope tests pin each one. What left was the story.

THE CAP IS HALF WHAT IT WAS, AND THAT IS NOT A NUMBER PICKED FOR TASTE: it is the
line the pilot's evidence drew. Growing past it is allowed. It has to be
deliberate — raise this figure in the same commit and say what the extra words
buy the answerer.
"""
from __future__ import annotations

import relay

ME = "session_" + "a" * 20
BEFORE = 6_082
CAP = BEFORE // 2          # 3,041


def _envelope() -> str:
    return relay.as_prompt(relay.ask(
        "hand tools are bought for the trade during the year - are they "
        "deducted or capitalized?", reply_to=ME))


def test_the_envelope_is_at_most_half_what_it_was():
    size = len(_envelope())
    assert size <= CAP, (
        f"the question envelope is {size:,} characters, over {CAP:,}. Every "
        f"character is echoed back into the asking session several times per "
        f"question; at {BEFORE:,} the asker stopped sending after three.")


def test_no_incident_narrative_has_crept_back():
    """The markers of a story rather than a rule. Each one was in the old
    envelope; none of them tells an answerer what to do."""
    body = _envelope()
    for story in ("WHY THIS PARAGRAPH EXISTS", "measured 8 September",
                  "Forge-Occam ran a real", "0 passages against 8",
                  "11 September 2026"):
        assert story not in body, (
            f"{story!r} is history, and the envelope carries rules. The reason "
            f"belongs in relay.py's docstrings or in a test.")
