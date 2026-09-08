"""Make the plugin importable, and make "no network" a fact rather than a hope.

The engine grades against stored text and must never reach out. That is what
keeps CI deterministic and offline, and it is the reason freshness is a separate
job rather than something the grader does on the way past.

A comment saying so would be a claim. `no_network` is autouse, so every test in
this suite runs with the socket layer replaced by something that raises -- and
the test that proves the guard itself can fail is in `test_engine.py`, because a
check that has only ever passed is not evidence.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DESKS = ROOT / "desks"


class NetworkUsed(AssertionError):
    """Something in the suite tried to open a socket."""


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise NetworkUsed(
            "this suite must not touch the network: the engine grades against "
            "stored text, and freshness is the staleness check's job"
        )

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    return refuse


@pytest.fixture
def fixed_assets():
    import record
    return record.load(DESKS / "fixed-assets")


@pytest.fixture
def problem(fixed_assets):
    """A problem chosen by its conclusion, never by its position in the file.

    An earlier version took `problems[0]`, and regenerating the set moved a
    different example into that slot -- turning the answer a test called wrong
    into the right one. A fixture that depends on file order is a test that
    passes for the wrong reason on the day the record grows.
    """
    return next(p for p in fixed_assets.problems
                if p.answer == "must capitalize")


@pytest.fixture
def wrong_position(problem):
    """The other conclusion this desk can state. Derived, not hardcoded."""
    return ("not required to capitalize" if problem.answer == "must capitalize"
            else "must capitalize")


#: THE JUDGE, FOR TESTS THAT ARE ABOUT SOMETHING ELSE. Every desk declares
#: `Judged: required` (#346), so `ask.answer` refuses `not_judged` unless a
#: second reader has looked -- which is the point, and which would otherwise
#: mean every test of the RENDERING, the straddle note or the `alongside` block
#: silently became a test of the judge gate.
#:
#: IT QUOTES REAL WORDS FROM THE REAL TEXT, and that is not a convenience. The
#: engine's one check is that the judge's quotation is IN what they read; a
#: helper that returned a canned sentence would pass the gate only because the
#: check was not running, and every test using it would prove nothing. Pass the
#: text the judge is being handed -- the stored passage, or the fetched page
#: where one was fetched -- and this quotes the front of it.
def a_judgment(text, *, by="a-second-reader", supports=True):
    import judging
    words = " ".join(str(text).split())[:200]
    if not words:
        raise AssertionError(
            "a_judgment was handed no text; a judgment quoting nothing is not "
            "a judgment and the fixture is what is wrong, not the code")
    return judging.Judgment(by=by, supports=supports, because=words)


def answer_judged(question, desk_name, *, citation="", desks=DESKS, **kw):
    """`ask.answer` with a real second reader, for tests about something else.

    THE GATE IS REAL AND THIS DOES NOT SOFTEN IT. It looks the citation up in
    the desk's own record, quotes the front of that passage, and hands it in as
    a judgment -- so the engine's containment check runs for real on every call.
    What it removes is the need for a test about the STRADDLE NOTE to also be a
    test of the judge.

    WHERE NOTHING RESOLVES, NO JUDGMENT IS PASSED, and that is deliberate: the
    answer is about to be refused for a reason that has nothing to do with the
    judge, and inventing a quotation for a passage that does not exist would be
    the fixture asserting something the record does not say. A test that wanted
    a served answer and reaches this line will refuse `not_judged`, loudly.
    """
    import ask
    import record as _record
    text = ""
    if citation:
        desk = _record.load(Path(desks) / desk_name)
        backing = desk.authority_for(citation)
        if backing is not None:
            text = (getattr(backing[1], "text", "")
                    or getattr(desk.passage(citation), "text", "")
                    or getattr(backing[1], "position", ""))
    return ask.answer(question, desk_name, citation=citation, desks=desks,
                      judged=a_judgment(text) if text.strip() else None, **kw)
