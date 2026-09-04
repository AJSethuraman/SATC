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
