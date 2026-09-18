"""Shared fixtures: the synthetic book, built once per session.

Every test starts where a person starts (tenet S32): a file on disk, the
question file beside it, and the command line. Nothing here hand-builds a
fixture the software never produced.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from analysis_pack import synth
from analysis_pack.config import load_config
from analysis_pack.ingest import read_table
from analysis_pack.population import build_population
from analysis_pack.workbook import build_pack

ASOF = date(2026, 6, 30)
RUN = date(2026, 9, 18)


@pytest.fixture(scope="session")
def effect_book(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("effect")
    synth.generate(d, seed=20260918, loans=40000, effect=2.0, mode="effect")
    return d


@pytest.fixture(scope="session")
def effect_pack(effect_book):
    cfg = load_config(effect_book / "config.yaml")
    table = read_table(effect_book / "loans.csv")
    pop = build_population(cfg, table.rows, ASOF)
    blob, data, checks = build_pack(cfg, pop, table, RUN)
    return {"cfg": cfg, "table": table, "pop": pop, "bytes": blob, "data": data, "checks": checks,
            "planted": json.loads((effect_book / "planted.json").read_text())}


@pytest.fixture(scope="session")
def effect_recalc(effect_pack):
    from recalc import Recalc
    return Recalc(effect_pack["bytes"])
