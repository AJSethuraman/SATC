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
