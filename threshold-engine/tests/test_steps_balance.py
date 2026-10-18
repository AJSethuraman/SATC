"""Question 20 of the round 2 commercial docket (the firm, 18 Oct 2026,
"agreed with the recommendation"): a label explains a jump only when its
change could have caused it. Every entry of config/reporting-changes.json
says, from its own source, whether it can step a book's balance in a single
quarter (``steps_balance``) and why (``steps_balance_why``); only a reporting
change marked true carries a series across windows the jump left out
(question 16). Where the source does not say, it is false.
"""
import copy
import json

import pytest

from conftest import ROOT
from threshold_engine import reporting_changes as RC
from threshold_engine.peers import books, run
from threshold_engine.series import read_csv, read_left_out
from test_left_out import build_kw, cache_of, keybank_ci
from test_reporting_changes import good, refused

REGISTRY = ROOT / "config" / "reporting-changes.json"
CHANGES, EVENTS = RC.load_all(REGISTRY)


# ---- the registry in the repository --------------------------------------------------------------------

def test_every_entry_says_whether_it_can_step_a_balance_and_why():
    """Expected from the docket: the NDFI revision, FAS 166/167 and the 2011
    auto split true; the 2009Q1 'Secured by real estate, clarified' (new loans
    only) and the COVID past-due rules false. Every other entry was read from
    its own source; where the source does not say, false."""
    got = {c["name"]: c["steps_balance"] for c in CHANGES}
    assert got == {
        "Construction, nonfarm and lease splits": False,
        "Loans classified as trading": False,
        "Secured by real estate, clarified": False,
        "Securitizations back on the books (FAS 166 and 167)": True,
        "NDFI loans split out of other loans": True,
        "Construction loans after completion": False,
        "Auto loans get their own line": True,
        "Real estate breakdown for the whole bank": False,
        "CECL: purchased credit-deteriorated loans": False,
        "COVID-19 deferrals not reported as past due": False,
        "Troubled debt restructuring captions replaced": False,
        "NDFI and margin-loan revision": True,
    }
    assert {e["name"]: e["steps_balance"] for e in EVENTS} == {
        "Revolving-line drawdowns": True, "Paycheck Protection Program loans": True}
    for c in CHANGES + EVENTS:
        assert c["steps_balance_why"].startswith("Its source"), c["name"]
    secured = next(c for c in CHANGES if c["name"] == "Secured by real estate, clarified")
    assert "new loans only" in secured["steps_balance_why"]
    # A false entry whose source is silent says so.
    for name in ("Loans classified as trading", "Construction loans after completion",
                 "CECL: purchased credit-deteriorated loans"):
        assert "not settled, so no" in next(c for c in CHANGES if c["name"] == name)["steps_balance_why"], name


def test_can_step_keeps_only_the_changes_marked_true():
    assert [c["name"] for c in RC.can_step(CHANGES)] == [
        "Securitizations back on the books (FAS 166 and 167)", "NDFI loans split out of other loans",
        "Auto loans get their own line", "NDFI and margin-loan revision"]


# ---- the refusals ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("over, says", [
    ({"steps_balance": "yes"}, "steps_balance must be true or false"),
    ({"steps_balance": 1}, "steps_balance must be true or false"),
    ({"steps_balance": None}, "steps_balance must be true or false"),
    ({"steps_balance_why": ""}, "steps_balance_why must say why"),
    ({"steps_balance_why": "  "}, "steps_balance_why must say why"),
    ({"steps_balance_why": "two\nlines"}, "steps_balance_why must say why"),
    ({"steps_balance_why": None}, "steps_balance_why must say why"),
])
def test_a_bad_answer_is_refused_by_name(tmp_path, over, says):
    raw = good()
    raw["changes"][0].update(steps_balance=True, steps_balance_why="Its source says so.")
    raw["changes"][0].update(over)
    msg = refused(raw, tmp_path)
    assert "change 1 (A change)" in msg and says in msg, msg


def test_both_keys_are_required_on_a_change_and_on_an_event(tmp_path):
    for key in ("steps_balance", "steps_balance_why"):
        raw = good()
        raw["changes"][0].update(steps_balance=False, steps_balance_why="Its source does not say.")
        del raw["changes"][0][key]
        assert "change 1 (A change) is missing %r" % key in refused(raw, tmp_path)
    raw = good()
    raw["changes"][0].update(steps_balance=False, steps_balance_why="Its source does not say.")
    ev = copy.deepcopy(raw["changes"][0])
    ev["name"] = "An event"
    del ev["steps_balance"]
    raw["events"] = [ev]
    assert "event 1 (An event) is missing 'steps_balance'" in refused(raw, tmp_path)


# ---- only a true change carries a series across --------------------------------------------------------

def registry_with(tmp_path, name, value):
    raw = json.loads(REGISTRY.read_text(encoding="utf-8"))
    hit = [c for c in raw["changes"] if c["name"] == name]
    assert len(hit) == 1
    hit[0]["steps_balance"] = value
    p = tmp_path / ("registry-%s.json" % value)
    p.write_text(json.dumps(raw), encoding="utf-8")
    return p


@pytest.mark.parametrize("value, first", [(True, "2006-03-31"), (False, "2026-03-31")])
def test_keybanks_ci_continues_across_the_ndfi_windows_only_while_the_change_can_step_a_balance(tmp_path, value,
                                                                                                 first):
    """KeyBank's C&I fell 28.6% in 2024Q4, the NDFI and margin-loan revision.
    Marked true (its source moves every margin loan out of C&I at one report
    date), the series runs from 2006 across those windows; the same entry
    marked false, it starts after them, as any unexplained jump does."""
    kw = build_kw(tmp_path, cache_of(tmp_path, keybank_ci()), "2005Q1", "2026Q2", ["C&I"], False)
    kw["reporting_changes"] = registry_with(tmp_path, "NDFI and margin-loan revision", value)
    run.build(tmp_path / "peers.xlsx", **kw)
    path = tmp_path / "series" / "c-i_keybank_net.csv"
    assert read_csv(path)[0].date == first
    assert bool(read_left_out(path)) is value


def test_a_jump_in_a_quarter_only_a_false_change_names_breaks_the_series(tmp_path):
    """KeyBank's C&I up 30% in 2009Q1, a quarter 'Secured by real estate,
    clarified' names for C&I. Its source applies the test to new loans only,
    so it cannot step a balance in one quarter: the series starts after the
    jump's windows. The NDFI windows are still carried across."""
    d = json.loads(json.dumps(keybank_ci()))
    k = 1.3 * d["20081231"][0]["LNCI"] / d["20090331"][0]["LNCI"]
    for q, rows in d.items():
        if q >= "20090331":
            for r in rows:
                r["LNCI"] = r["LNCI"] * k
    rows = books.bank_book(d, "17534", "C&I", 0.25, 0, True, acquired=[], stated=())
    assert {r["quarter"] for r in rows if r["why"] == books.WHY_JUMP and "2009Q1" in r["jumped"]} == \
        {"2009Q1", "2009Q2", "2009Q3", "2009Q4", "2010Q1"}
    assert "2009Q1" in RC.labelled_quarters(CHANGES, "C&I", "net charge-offs")
    assert "2009Q1" not in RC.labelled_quarters(RC.can_step(CHANGES), "C&I", "net charge-offs")
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache_of(tmp_path, d), "2005Q1", "2026Q2", ["C&I"],
                                                   False))
    path = tmp_path / "series" / "c-i_keybank_net.csv"
    assert read_csv(path)[0].date == "2010-06-30"
    assert read_left_out(path) == ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
