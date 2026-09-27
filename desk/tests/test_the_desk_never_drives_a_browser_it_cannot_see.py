"""The desk looks things up over HTTP from where it runs, never in someone's browser.

27 September 2026, desk trial 1. The brief said "go and look, with Chrome on
the Forge". Forge-Desk read that as permission to use the Claude in Chrome
tools, called them with `createIfEmpty: true`, and a new window opened on the
firm's PRIMARY DESKTOP and went to an eCFR page. The firm: *"why in the world
was my primary desktop used to go to the eCFR site and not the forge"*. It never
checked which machine the extension was attached to, and it did not need a
browser at all: the same regulation came over the eCFR API minutes later.

So the skills say so, and this holds them to it -- a rule that lives only in
one brief is gone the next time the brief is written differently.
"""
from __future__ import annotations

import pathlib

HERE = pathlib.Path(__file__).resolve().parents[1]
SKILLS = HERE / "skills"


def _read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_the_searcher_is_told_to_fetch_over_http():
    s = _read("run-down-a-question")
    assert "## How you look: over HTTP, from where you run" in s
    assert "api/versioner/v1/full/" in s and "Accept-Encoding" in s


def test_the_searcher_is_told_which_tools_it_may_not_drive():
    s = _read("run-down-a-question")
    for tool in ("Claude in Chrome", "computer use"):
        assert tool in s, tool
    assert "list_connected_browsers" in s
    assert "createIfEmpty" in s


def test_no_skill_says_the_desk_has_a_browser():
    """ask-desk told every asker "It runs on the Forge with a browser" -- the
    sentence that made a browser sound like the desk's own tool."""
    for skill in SKILLS.iterdir():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert "with a browser" not in text, skill.name
