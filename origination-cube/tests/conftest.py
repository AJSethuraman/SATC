"""Helpers: a Table built in memory and a cube file built from a dict, so a
test states its rows and its settings in one place."""

from __future__ import annotations

import copy

import pytest

from origination_cube import config as cfgmod
from origination_cube.ingest import Table

BASE = {
    "name": "t",
    "schema_version": 1,
    "key": "ID",
    "booked": "BAL",
    "outcome": "BAD",
    "gco": "GCO",
    "ranr": "RANR",
    "bands": [{"name": "score", "field": "SCORE", "edges": [650]}],
    "dimensions": [{"name": "chan", "field": "CHAN"}],
    "measures": [
        {"name": "loans", "mode": "count"},
        {"name": "score_median", "mode": "median", "value": "SCORE"},
    ],
    "benchmark": {"min_units": 2, "min_events": 1, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95,
                  "power": 0.8, "compare_to": "topline", "many_tests": "none", "materiality": "none"},
}


def cube(**overrides):
    raw = copy.deepcopy(BASE)
    for k, v in overrides.items():
        if v is None:
            raw.pop(k, None)
        else:
            raw[k] = v
    return cfgmod.parse(raw)


def table(rows, columns=None):
    columns = columns or list(rows[0].keys())
    return Table(path="(test)", sha256="", columns=columns, rows=rows, kind="csv")


def row(i, score, chan, bal, bad, gco, ranr=0):
    return {"ID": f"L{i}", "SCORE": score, "CHAN": chan, "BAL": bal, "BAD": bad, "GCO": gco, "RANR": ranr}


@pytest.fixture
def book():
    """Two channels, two score bands, round numbers a person can check."""
    return [
        row(1, 600, "A", 100, 1, 50),
        row(2, 600, "A", 100, 0, 0),
        row(3, 700, "A", 200, 0, 0),
        row(4, 700, "B", 200, 0, 0),
        row(5, 600, "B", 400, 1, 100),
        row(6, 700, "B", 1000, 0, 0),
    ]


@pytest.fixture(autouse=True)
def _memory_in_tmp(tmp_path, monkeypatch):
    """No test may read or write the real ~/.origination-cube memory."""
    monkeypatch.setenv("CUBE_MEMORY", str(tmp_path / "memory.yaml"))


#: The shuffle count a cube file gets when it doesn't name one, for tests that aren't about the
#: shuffle test: 2,000 instead of the production 10,000, so the suite stays quick. 2,000 still lets a
#: p-value print as small as 0.0005, small enough to clear the allowance for many tests in a grid of 60
#: pockets. Tests about the shuffle test set their own count, and
#: test_perm.test_the_production_default_runs_end_to_end runs the real 10,000 through the workbook.
TEST_SHUFFLES = 2_000
from origination_cube import perm as _perm                                       # noqa: E402

#: what a cube file with no `shuffles:` line runs with outside the tests, read before any test changes it
PRODUCTION_SHUFFLES = _perm.SHUFFLES


@pytest.fixture(autouse=True)
def _fewer_shuffles(monkeypatch):
    monkeypatch.setattr(_perm, "SHUFFLES", TEST_SHUFFLES)
