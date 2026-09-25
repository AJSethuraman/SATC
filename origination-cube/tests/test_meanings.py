"""What each column means: suggested from names and values, obvious ones only,
and taught by confirming. The firm: "it won't and should not be able to guess
them all off the bat - but some are obvious."""

import pytest

from conftest import table
from origination_cube import meanings, memory


def _rows(n=400):
    out = []
    for i in range(n):
        out.append({
            "APP_NUM": f"A{i:06d}",
            "CREDIT_SCORE": 560 + (i * 7) % 290,
            "MODEL_7": 540 + (i * 11) % 300,                     # a custom score on the FICO scale, no name to go on
            "BANK_SCR": 1 + (i * 3) % 99,                       # a custom score on its own scale
            "DEBT_RATIO": 0.12 + (i % 40) / 100,                # a DTI written as a fraction
            "R_2": 55 + (i % 70),                               # an LTV written as a percentage, no name
            "OPEN_DT": f"2023-{1 + i % 12:02d}-{1 + i % 28:02d}",
            "SNAP": "2026-06-30",                               # one date on every row: the as-of date
            "NEW_LINE_LIMIT": 1000 + (i % 9) * 500,
            "TERM_MO": [36, 48, 60, 72][i % 4],
        })
    return out


def test_the_obvious_ones_are_suggested():
    got = {c: sg.means for c, sg in meanings.suggest(table(_rows())).items()}
    assert got["APP_NUM"] == "key"
    assert got["CREDIT_SCORE"] == "fico"
    assert got["BANK_SCR"] == "score"          # named like a score, not on the FICO scale
    assert got["DEBT_RATIO"] == "dti"
    assert got["OPEN_DT"] == "origination_date"
    assert got["SNAP"] == "as_of_date"
    assert got["NEW_LINE_LIMIT"] == "servicing"
    assert got["TERM_MO"] == "term"


def test_the_rest_are_left_for_us_to_say():
    got = meanings.suggest(table(_rows()))
    # a custom score on the FICO scale looks like FICO until taught, and says so
    assert got["MODEL_7"].means == "fico" and "confirm it as `score`" in got["MODEL_7"].why
    # a ratio with no name to go on is just a number to cut
    assert got["R_2"].means == "amount"


def test_what_we_confirm_is_remembered_and_outranks_the_guess(tmp_path):
    mpath = tmp_path / "mem.yaml"
    from origination_cube import config as cfgmod
    cfg = cfgmod.Config(name="x", key="APP_NUM", missing={}, bands=(), dimensions=(), measures=(), benchmark=None,
                        columns={"MODEL_7": ("score", None), "R_2": ("ltv", None)})
    memory.remember(cfg, mpath)
    got = meanings.suggest(table(_rows()), memory.load(mpath)["columns"])
    assert got["MODEL_7"].means == "score" and got["MODEL_7"].source == "remembered"
    assert got["R_2"].means == "ltv" and "you confirmed this" in got["R_2"].why


def test_a_remembered_meaning_that_no_longer_fits_says_check(tmp_path):
    mpath = tmp_path / "mem.yaml"
    from origination_cube import config as cfgmod
    cfg = cfgmod.Config(name="x", key="k", missing={}, bands=(), dimensions=(), measures=(), benchmark=None,
                        columns={"BANK_SCR": ("fico", None)})
    memory.remember(cfg, mpath)
    got = meanings.suggest(table(_rows()), memory.load(mpath)["columns"])
    assert got["BANK_SCR"].means == "fico" and "CHECK" in got["BANK_SCR"].why


def test_what_to_look_at_first_is_ranked_and_says_why():
    rows = _rows()
    for i, r in enumerate(rows):
        if i % 5 == 0:
            r["DEBT_RATIO"] = ""                     # 20% blank: left on purpose, or by accident?
    t = table(rows)
    looks = meanings.review(t, meanings.suggest(t))
    kinds = [rv.kind for rv in looks]
    assert kinds == sorted(kinds, key=meanings.REVIEW_ORDER.index)      # most urgent first
    assert kinds[0] == "cannot run"                  # no booked, outcome, gco, ranr in this extract
    blank = next(rv for rv in looks if rv.kind == "blanks")
    assert blank.column == "DEBT_RATIO" and "20% blank" in blank.says and "fix the extract" in blank.says
    assert any(rv.kind == "shape only" and rv.column == "R_2" for rv in looks)
    assert any(rv.kind == "values only" and rv.column == "MODEL_7" for rv in looks)


def test_a_misfire_shows_up_near_the_top(tmp_path):
    """A remembered meaning the values no longer fit is ranked second only to
    what stops the run: it is how a wrong lesson, or a misfiring rule, shows."""
    mpath = tmp_path / "mem.yaml"
    from origination_cube import config as cfgmod
    cfg = cfgmod.Config(name="x", key="k", missing={}, bands=(), dimensions=(), measures=(), benchmark=None,
                        columns={"BANK_SCR": ("fico", None)})
    memory.remember(cfg, mpath)
    t = table(_rows())
    looks = meanings.review(t, meanings.suggest(t, memory.load(mpath)["columns"]))
    first_non_blocking = next(rv for rv in looks if rv.kind != "cannot run")
    assert first_non_blocking.kind == "memory disagrees" and first_non_blocking.column == "BANK_SCR"
    assert "cube memory --forget BANK_SCR" in first_non_blocking.says


def test_stray_values_are_on_the_list(tmp_path):
    from origination_cube import synth
    from origination_cube.ingest import read_table
    t = read_table(synth.write_extract(tmp_path, n=2000))
    looks = meanings.review(t, meanings.suggest(t))
    stray = {rv.column for rv in looks if rv.kind == "stray values"}
    assert stray == {"BAD_FLAG", "GCO_AMT"}        # the planted 2 in the outcome, the planted #N/A in GCO
