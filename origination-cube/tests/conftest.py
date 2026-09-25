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
    "bands": [{"name": "score", "field": "SCORE", "edges": [650]}],
    "dimensions": [{"name": "chan", "field": "CHAN"}],
    "measures": [
        {"name": "bad", "mode": "flagwt", "flag": "BAD", "per": "BAL"},
        {"name": "gco", "mode": "sumnum", "value": "GCO", "per": "BAL"},
        {"name": "loans", "mode": "count"},
        {"name": "score_median", "mode": "median", "value": "SCORE"},
    ],
    "benchmark": {"min_units": 1, "worse_at": 1.25, "better_at": 0.8},
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


def row(i, score, chan, bal, bad, gco):
    return {"ID": f"L{i}", "SCORE": score, "CHAN": chan, "BAL": bal, "BAD": bad, "GCO": gco}


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
