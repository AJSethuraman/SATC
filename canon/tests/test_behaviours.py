"""The standing behaviours, checked rather than admired.

A skill file is a claim about how a session conducts itself. Nothing compares
the claim to the file, so the file drifts: a behaviour loses its incident and
becomes a slogan, or a fourteenth arrives with nothing behind it. That is the
one bug shape this whole repository exists to close (S31), and a document about
it is not exempt.

WHAT THIS CANNOT CHECK, said rather than implied: whether a session actually
behaves this way. No test reaches that. These hold the shape of the file.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CANON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANON))

SKILL = CANON / "skills" / "how-we-work" / "SKILL.md"
TEXT = SKILL.read_text(encoding="utf-8")

# PROSE ASSERTIONS RUN AGAINST THE UNWRAPPED TEXT. A sentence in a Markdown
# file wraps wherever it wraps, and a test that fails because a phrase crossed
# a line break has found nothing -- it just costs a cycle and trains whoever
# hits it to reach for the assertion rather than the file.
FLAT = " ".join(TEXT.split())

HEAD = re.compile(r"^## (\d+) · (.+)$", re.M)


def _behaviours() -> list[tuple[str, str, str]]:
    """(number, title, body) for each numbered behaviour."""
    out = []
    heads = list(HEAD.finditer(TEXT))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(TEXT)
        out.append((h.group(1), h.group(2), TEXT[h.end():end]))
    return out


def test_all_thirteen_are_here_and_numbered_without_a_gap():
    """The count is stated in the file's own first line. This is the thing
    that compares the claim to the content."""
    got = _behaviours()
    assert [n for n, _, _ in got] == [str(i) for i in range(1, 14)]
    assert "Thirteen behaviours" in TEXT


def test_every_behaviour_says_what_to_do():
    """`**Do:**` is what makes one checkable rather than admirable. A
    behaviour without it is an observation, and an observation changes nothing.
    """
    for number, title, body in _behaviours():
        assert "**Do:**" in body, f"{number} · {title} says nothing to do"


def test_every_behaviour_carries_the_incident_behind_it():
    """Same rule as a tenet: a rule with a body count gets followed, a rule
    that sounds wise gets skimmed."""
    for number, title, body in _behaviours():
        assert "**Incident:**" in body, f"{number} · {title} has no incident"
        incident = body.split("**Incident:**", 1)[1].strip()
        assert len(incident.split()) >= 15, \
            f"{number} · {title} has an incident too thin to be a citation"


def test_the_skill_is_written_to_load_without_being_asked_for():
    """Acceptance for this slice. The description is what the harness matches
    on, so it has to name the ordinary work, not just the skill's own name."""
    front = TEXT.split("---")[1]
    assert "name: how-we-work" in front
    for ordinary in ("build", "review", "report", "check", "test"):
        assert ordinary in front.lower(), f"the description never mentions {ordinary}"
    assert "not only when asked" in front


def test_the_file_separates_what_is_available_from_what_is_loaded():
    """Behaviour 7: earn the claim, or don't make it.

    Installing the plugin makes this skill available everywhere — observed. It
    does not follow that a session picks it up on its own, which is a separate
    claim and still an unenforced one. The file has to hold both apart, and
    name the way to load it by hand when it did not fire.
    """
    assert "observed on 4 September 2026" in FLAT, "the observed half is stated"
    assert "not a guarantee the harness enforces" in FLAT, "the unobserved half too"
    assert "/canon:how-we-work" in FLAT, "no way given to load it by hand"


def test_voice_is_named_as_a_behaviour_not_a_personality():
    assert "Voice is a standing behaviour, not a personality" in FLAT
    assert "perform certainty it does not have" in FLAT


def test_these_are_distinguished_from_the_tenets():
    """Two files of numbered rules invite being conflated, and then one gets
    edited as if it were the other."""
    assert "These are not the tenets" in FLAT
    assert "TENETS.md" in TEXT
