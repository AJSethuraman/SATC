"""A series continues across windows left out only for a labelled change.

The firm, 17 Oct 2026, on the commercial proposal's question 16 ("agreed
with the recommendation" on the docket form): when a labelled reporting
change trips the 25% jump (KeyBank's C&I in 2024Q4, the NDFI move), keep the
series going across it instead of starting it after the gap. KeyBank's C&I
charge-off history runs 2006 on, with the change labelled and its windows
left out. This changes how every series is written, consumer included.

What these tests hold: the windows stay out and are never filled; the file
declares them on a `left-out:` line; every reader takes that gap and no
other; every other reason a window is left out (an acquisition, the minimum
book, a jump in a quarter nothing names) breaks the series as before.
"""
import json
from pathlib import Path

import pytest

from conftest import ROOT
from threshold_engine import reporting_changes as RC
from threshold_engine.backtest import backtest
from threshold_engine.evidence import evidence
from threshold_engine.peers import books, delinquency as D, run
from threshold_engine.profile import profile
from threshold_engine.series import (Point, SeriesError, check, left_out_dates, left_out_line, read_csv,
                                     read_left_out, read_notes, smooth)

PEERS = ROOT / "tests" / "data" / "peers"
REGISTRY = ROOT / "config" / "reporting-changes.json"
CHANGES, EVENTS = RC.load_all(REGISTRY)


def qdates(first_year, n):
    out, y, q = [], first_year, 1
    for _ in range(n):
        out.append("%d-%s" % (y, ("03-31", "06-30", "09-30", "12-31")[q - 1]))
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


# ---- the reader: a declared gap, and no other --------------------------------------------------------------

def test_a_declared_gap_is_read_as_the_calendar_with_none_and_any_other_gap_is_refused():
    ds = qdates(2020, 8)
    pts = [Point(d, float(i)) for i, d in enumerate(ds) if d not in ds[3:5]]
    with pytest.raises(SeriesError, match="2020-09-30 is followed by 2021-06-30"):
        check(pts, "quarterly")
    cal = check(pts, "quarterly", ds[3:5])
    assert [p.date for p in cal] == ds
    assert [p.value for p in cal] == [0.0, 1.0, 2.0, None, None, 5.0, 6.0, 7.0]
    with pytest.raises(SeriesError, match="2020-09-30 is followed by 2021-06-30"):
        check(pts, "quarterly", ds[3:4])                        # half the gap declared is no declaration
    with pytest.raises(SeriesError, match="2020-03-31 is declared left out but holds a value"):
        check(pts, "quarterly", ds[3:5] + ds[:1])
    with pytest.raises(SeriesError, match="not between the first and last observation"):
        check(pts, "quarterly", ds[3:5] + ["2022-03-31"])
    with pytest.raises(SeriesError, match="only a quarterly series"):
        check(pts, "monthly", ds[3:5])


def test_the_left_out_line_round_trips_and_a_malformed_one_is_refused():
    line = left_out_line(["2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q2"], "Why.")
    assert line == "left-out: 2024Q4 to 2025Q4, 2026Q2. Why."
    key, text = line.split(": ", 1)
    assert left_out_dates([(key, text)]) == ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30",
                                             "2025-12-31", "2026-06-30"]
    assert left_out_dates([("note", "2024Q4. not a declaration")]) == []
    with pytest.raises(ValueError, match="must begin with its quarters"):
        left_out_dates([("left-out", "some quarters. Why.")])


def test_smoothing_never_averages_across_a_gap():
    ds = qdates(2020, 8)
    cal = [Point(d, None if i in (3, 4) else float(i)) for i, d in enumerate(ds)]
    assert [p.value for p in smooth(cal, 2)] == [0.5, 1.5, None, None, None, 5.5, 6.5]
    assert [p.value for p in smooth(cal, 1)] == [p.value for p in cal]
    with pytest.raises(SeriesError, match="no 4 periods in a row"):
        smooth([Point(d, None if i in (2, 5) else 1.0) for i, d in enumerate(ds)], 4)


def wave(n=48, gap=()):
    """A quarterly series with two stress spells, the quarters in ``gap`` (positions) left out."""
    ds = qdates(2010, n)
    vals = [1.0 + (3.0 if 8 <= i < 12 else 0) + (2.0 if 30 <= i < 34 else 0) + 0.01 * (i % 5) for i in range(n)]
    pts = [Point(d, v) for i, (d, v) in enumerate(zip(ds, vals)) if i not in gap]
    return pts, [ds[i] for i in gap]


def test_profile_counts_only_values_and_measures_a_year_on_the_calendar():
    pts, left = wave(gap=range(42, 45))
    pr = profile(pts, "x", "%", "higher_is_worse", "quarterly", 1, left)
    assert pr["coverage"]["observations"] == 45 and pr["coverage"]["left_out"] == left
    # The latest quarter's year-ago quarter (position 43) is left out: no change over the year.
    assert pr["latest"]["change_over_year"] is None
    pts2, left2 = wave(gap=range(40, 43))
    pr2 = profile(pts2, "x", "%", "higher_is_worse", "quarterly", 1, left2)
    full = profile(wave()[0], "x", "%", "higher_is_worse", "quarterly", 1)
    assert pr2["latest"]["change_over_year"] == pytest.approx(full["latest"]["change_over_year"])
    assert "left_out" not in full["coverage"]


def test_a_spell_is_never_carried_across_the_gap():
    pts, left = wave(gap=range(9, 11))                         # inside the first spell
    spells = profile(pts, "x", "%", "higher_is_worse", "quarterly", 1, left)["spells_worse_than_median"]
    first = [s for s in spells if s["peak"] > 3.5]               # the 2012 spell, cut in two by the gap
    assert [(s["start"], s["end"], s["note"], s["complete"]) for s in first] == [
        ("2012-03-31", "2012-06-30", "ends where quarters are left out", False),
        ("2012-12-31", "2013-03-31", "begins just after quarters left out", False)]


def test_evidence_and_backtest_run_across_the_gap_without_reading_it():
    pts, left = wave(gap=range(20, 23))
    ev = evidence(pts, "x", "%", "higher_is_worse", "quarterly", 1,
                  dict(halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse"), True, (5,), left)
    assert ev["scenarios"] and ev["recency"]
    for d in ev["departures"]:                                 # no bridge drawn over the gap
        assert not (d["bridge_from"] < left[0] < d["bridge_to"]), d
    bt = backtest(pts, "x", "%", "higher_is_worse", "quarterly", 1, (50, 75, 90, 95), 4, 12, True, (), left)
    tested = [p["date"] for p in bt["runs"][0]["periods"]]
    ds = qdates(2010, 48)
    # A period is tested only when it and the period 4 later on the calendar both hold a value.
    assert not set(tested) & set(left)
    assert not set(tested) & set(ds[16:19])                    # their horizon lands in the gap
    assert bt["runs"][0]["first_tested"] == ds[11] and bt["runs"][0]["last_tested"] == ds[43]
    with pytest.raises(SeriesError, match="expected one quarterly step"):
        backtest(pts, "x", "%", "higher_is_worse", "quarterly", 1, (50, 75, 90, 95), 4, 12, True)



def test_the_backtests_history_counts_values_not_calendar_quarters():
    """min_history is a count of values: a gap inside the first history
    pushes the first period tested later by the quarters it leaves out."""
    pts, left = wave(gap=range(5, 8))
    bt = backtest(pts, "x", "%", "higher_is_worse", "quarterly", 1, (50, 75, 90, 95), 4, 12, True, (), left)
    ds = qdates(2010, 48)
    assert bt["runs"][0]["first_tested"] == ds[14]             # positions 0-4 and 8-14: twelve values
    assert bt["runs"][0]["periods"][0]["date"] == ds[14]

# ---- the writer: which windows the series continues across --------------------------------------------------

def test_unbroken_tail_bridges_only_the_quarters_named_and_never_starts_or_ends_on_one():
    rows = [("2020Q1", 1.0), ("2020Q2", None), ("2020Q3", 2.0), ("2020Q4", None), ("2021Q1", 3.0),
            ("2021Q2", None)]
    assert run.unbroken_tail(rows) == ([("2021Q1", 3.0)], ["2020Q1", "2020Q2", "2020Q3", "2020Q4"], ["2021Q2"])
    tail, before, after = run.unbroken_tail(rows, {"2020Q4"})
    assert tail == [("2020Q3", 2.0), ("2020Q4", None), ("2021Q1", 3.0)]
    assert before == ["2020Q1", "2020Q2"] and after == ["2021Q2"]
    tail, before, after = run.unbroken_tail(rows, {"2020Q2", "2020Q4", "2021Q2"})
    assert tail[0] == ("2020Q1", 1.0) and tail[-1] == ("2021Q1", 3.0) and after == ["2021Q2"]
    tail, before, _ = run.unbroken_tail([("2020Q1", None), ("2020Q2", 1.0)], {"2020Q1"})
    assert tail == [("2020Q2", 1.0)] and before == ["2020Q1"]


def test_series_note_declares_the_gap_and_refuses_one_without_a_reason():
    tail = [("2020Q3", 2.0), ("2020Q4", None), ("2021Q1", 3.0)]
    lines = run.series_note(["a note"], tail, ["2020Q1"], [], "Because.")
    assert lines[1] == "left-out: 2020Q4. Because."
    with pytest.raises(ValueError, match="must say why"):
        run.series_note(["a note"], tail, [], [])


def keybank_ci():
    """KeyBank's C&I filings, 2005Q1 to 2026Q2, from the public FDIC cache (README)."""
    return json.loads((PEERS / "keybank_ci_2005.json").read_text(encoding="utf-8"))


def test_keybanks_ci_runs_from_2006_with_the_ndfi_windows_left_out():
    """KeyBank's C&I fell from $41.9bn to $29.9bn in 2024Q4 (-28.6%), the NDFI
    and margin-loan revision, which the registry names for C&I from 2024Q4 to
    2025Q2. Before, the series started at 2026Q1: two quarters."""
    rows = books.bank_book(keybank_ci(), "17534", "C&I", 0.25, 0, True, acquired=[])
    out = {r["quarter"]: (r["why"], r["jumped"], r["why_without_jump"]) for r in rows if not r["kept"]}
    left = ["2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4"]
    assert sorted(out) == left
    assert all(v == (books.WHY_JUMP, ["2024Q4"], None) for v in out.values())
    marks = RC.labelled_quarters(CHANGES, "C&I", "net charge-offs")
    assert run.bridged(rows, marks) == set(left)
    old = run.unbroken_tail([(r["quarter"], r["net_rate"]) for r in rows])
    assert [q for q, _ in old[0]] == ["2026Q1", "2026Q2"]
    tail, before, after = run.unbroken_tail([(r["quarter"], r["net_rate"]) for r in rows], run.bridged(rows, marks))
    assert tail[0][0] == "2006Q1" and tail[-1][0] == "2026Q2" and before == [] and after == []
    assert [q for q, v in tail if v is None] == left
    assert run.named_for(CHANGES, "C&I", "net charge-offs", ["2024Q4"]) == ["NDFI and margin-loan revision"]


def test_an_acquisition_or_the_minimum_book_still_breaks_the_series():
    data = keybank_ci()
    marks = RC.labelled_quarters(CHANGES, "C&I", "net charge-offs")
    bought = books.bank_book(data, "17534", "C&I", 0.25, 0, True, acquired=["20250331"])
    assert {r["quarter"]: r["why_without_jump"] for r in bought if r["quarter"] in ("2025Q1", "2025Q2")} == \
        {"2025Q1": books.WHY_ACQUIRED, "2025Q2": books.WHY_ACQUIRED}
    tail, before, _ = run.unbroken_tail([(r["quarter"], r["net_rate"]) for r in bought], run.bridged(bought, marks))
    assert tail[0][0] == "2026Q1"                       # the acquisition's windows reach 2025Q4: a break
    told = books.bank_book(data, "17534", "C&I", 0.25, 0, True, acquired=[], stated=["20250331"])
    assert run.unbroken_tail([(r["quarter"], r["net_rate"]) for r in told], run.bridged(told, marks))[0][0][0] == \
        "2026Q1"
    small = books.bank_book(data, "17534", "C&I", 0.25, 35e6, False, acquired=[])
    tail, _, _ = run.unbroken_tail([(r["quarter"], r["net_rate"]) for r in small], run.bridged(small, marks))
    assert all(v is not None for _, v in tail)          # a window under the minimum is never bridged
    # A jump in a quarter nothing names breaks it as before: the same move read as 2023Q4.
    assert run.bridged(books.bank_book(data, "17534", "C&I", 0.25, 0, True, acquired=[]), marks - {"2024Q4"}) == set()


def test_the_delinquency_average_continues_across_the_same_windows():
    rows = D.bank_delinquency(keybank_ci(), "17534", "C&I", "nonaccrual", 0.25, 0, True, acquired=[])
    marks = RC.labelled_quarters(CHANGES, "C&I", "nonaccrual")
    got = run.bridged(rows, marks, without="why_avg4_without_jump", quarter="q")
    assert got == {"2024Q4", "2025Q1", "2025Q2"}       # i-2..i: three averages hold the 2024Q4 move
    assert all(r["rate"] is not None for r in rows)    # a quarter-end rate is never blanked by the jump


def cache_of(tmp_path, data):
    cache = tmp_path / "cache"
    cache.mkdir()
    for q, rows in data.items():
        (cache / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    return cache


def build_kw(tmp_path, cache, first, last, products, delinquency, base="2019Q4", years=(2019, 2025)):
    m = tmp_path / "mergers.json"
    m.write_text("{}", encoding="utf-8")
    a = tmp_path / "absorptions.json"
    a.write_text("[]", encoding="utf-8")
    return dict(cache=cache, roster=ROOT / "config" / "peers.json", series_dir=tmp_path / "series",
                first=first, last=last, products=products, mergers=m, absorptions=a, extra_acquisitions=[],
                industry_combined=[], jump=0.25, acquisition_share=0.05, min_book=0, exempt_self=True,
                pro_forma=True, pack="all", min_banks=1, rank_by="net", last_n=4, min_obs=2, base_quarter=base,
                index_min_book=0, lagged_years=[years[0]], lag_years=1, normalisation_years=list(years),
                mix_base_year=years[0], delinquency=delinquency, reporting_changes=REGISTRY,
                stated_acquisitions=None, say=lambda line: None)


@pytest.fixture(scope="module")
def keybank_built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("kb")
    run.build(tmp / "peers.xlsx", **build_kw(tmp, cache_of(tmp, keybank_ci()), "2005Q1", "2026Q2", ["C&I"], True))
    return tmp


def test_the_build_writes_keybanks_ci_from_2006_and_declares_the_gap(keybank_built):
    path = keybank_built / "series" / "c-i_keybank_net.csv"
    pts = read_csv(path)
    assert pts[0].date == "2006-03-31" and pts[-1].date == "2026-06-30"
    assert not {p.date for p in pts} & {"2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"}
    assert read_left_out(path) == ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
    notes = dict(read_notes(path))
    assert notes["left-out"].startswith(
        "2024Q4 to 2025Q4. The jump left these windows out and nothing else would have: every move that tripped "
        "it (2024Q4) is in a quarter NDFI and margin-loan revision names for C&I, net charge-offs.")
    text = path.read_text(encoding="utf-8")
    assert "Written from" not in text                  # nothing before is dropped
    assert "# event: 2020Q1, Revolving-line drawdowns." in text
    assert "# event: 2020Q2 to 2021Q4, Paycheck Protection Program loans." in text
    dq = keybank_built / "series" / "c-i_keybank_delinquency-nonaccrual_four-quarter-average.csv"
    assert read_left_out(dq) == ["2024-12-31", "2025-03-31", "2025-06-30"]
    # The quarter-end basis has no gap to declare.
    assert read_left_out(keybank_built / "series" / "c-i_keybank_delinquency-nonaccrual_quarter-end.csv") == []


def test_the_workbook_reads_the_gapped_series_and_leaves_the_quarters_blank(keybank_built, tmp_path):
    from openpyxl import load_workbook
    from threshold_engine.workbook import build
    s = keybank_built / "series"
    out = tmp_path / "w.xlsx"
    r = build(out, [("C&I - Net - KeyBank", s / "c-i_keybank_net.csv"), ("C&I - Net - Industry", s / "c-i_industry_net.csv")],
              "C&I", "%", "higher_is_worse", "quarterly", 1, True, 0.5, 1.0, 2.5, "worse", (), (50, 75, 90, 95),
              4, 41)
    assert r["quarters"] == 83                         # the industry's first window is 2005Q4
    da = load_workbook(out)["Data"]
    rows = {da.cell(i, 1).value: da.cell(i, 2).value for i in range(2, da.max_row + 1)}
    assert rows["2006Q1"] is not None and rows["2024Q3"] is not None and rows["2026Q2"] is not None
    assert [rows[q] for q in ("2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4")] == [None] * 5


def test_a_consumer_series_continues_across_a_labelled_change_and_breaks_at_an_unlabelled_jump(tmp_path):
    """Card: a +60% book in 2010Q1, when FAS 166 and 167 brought securitized
    cards back on the books (labelled for credit card), and a +40% book in
    2014Q1, which nothing names."""
    data = {}
    ds = [d.replace("-", "") for d in qdates(2008, 32)]
    for k, q in enumerate(ds):
        bal = 1000.0 * (1.6 if q >= "20100331" else 1) * (1.4 if q >= "20140331" else 1)
        qn = (int(q[4:6]) - 1) // 3 + 1
        data[q] = [{"CERT": "17534", "REPDTE": q, "LNCRCD": bal, "DRCRCD": 10.0 * qn, "CRCRCD": 1.0 * qn,
                    "RSSDHCR": "1"}]
    rows = books.bank_book(data, "17534", "Credit card", 0.25, 0, True, acquired=[])
    marks = RC.labelled_quarters(CHANGES, "Credit card", "net charge-offs")
    assert run.bridged(rows, marks) == {"2010Q1", "2010Q2", "2010Q3", "2010Q4", "2011Q1"}
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache_of(tmp_path, data), "2008Q1", "2015Q4",
                                                   ["Credit card"], False, "2011Q4", (2011, 2013)))
    path = tmp_path / "series" / "credit-card_keybank_net.csv"
    pts = read_csv(path)
    # Starts after the 2014Q1 jump's windows (2014Q1 to 2015Q1), not after the 2010 ones.
    assert pts[0].date == "2015-06-30" and read_left_out(path) == []
    run.build(tmp_path / "peers2.xlsx", **dict(build_kw(tmp_path, tmp_path / "cache", "2008Q1", "2013Q4",
                                                        ["Credit card"], False, "2011Q4", (2011, 2013)),
                                               series_dir=tmp_path / "s2"))
    path = tmp_path / "s2" / "credit-card_keybank_net.csv"
    pts = read_csv(path)
    assert pts[0].date == "2009-03-31" and pts[-1].date == "2013-12-31"
    assert read_left_out(path) == ["2010-03-31", "2010-06-30", "2010-09-30", "2010-12-31", "2011-03-31"]
    assert "Securitizations back on the books (FAS 166 and 167) names for Credit card" in \
        dict(read_notes(path))["left-out"]


def test_a_jump_in_a_quarter_only_an_event_names_still_breaks_the_series(tmp_path):
    """Question 16 as agreed: "When a labeled reporting change trips the 25%
    jump ... keep the series going across it". Question 13's record says the
    2020 drawdowns and the PPP loans "are not reporting changes", and question
    15 agreed only to label them and leave out the windows the rule catches.
    So an event never keeps a series going. Here KeyBank's C&I book rises 30%
    in 2020Q3, a quarter only the PPP event names for C&I charge-offs."""
    d = json.loads(json.dumps(keybank_ci()))
    k = 1.3 * d["20200630"][0]["LNCI"] / d["20200930"][0]["LNCI"]     # 2020Q3 is +30% on 2020Q2
    for q, rows in d.items():
        if q >= "20200930":
            for r in rows:
                r["LNCI"] = r["LNCI"] * k
    rows = books.bank_book(d, "17534", "C&I", 0.25, 0, True, acquired=[])
    jumped = {r["quarter"] for r in rows if r["why"] == books.WHY_JUMP and "2020Q3" in r["jumped"]}
    assert jumped == {"2020Q3", "2020Q4", "2021Q1", "2021Q2", "2021Q3"}
    assert "2020Q3" not in RC.labelled_quarters(CHANGES, "C&I", "net charge-offs")     # no change names it
    assert "2020Q3" in RC.labelled_quarters(EVENTS, "C&I", "net charge-offs")          # the PPP event does
    run.build(tmp_path / "peers.xlsx", **build_kw(tmp_path, cache_of(tmp_path, d), "2005Q1", "2026Q2", ["C&I"],
                                                   True))
    s = tmp_path / "series"
    for name in ("c-i_keybank_net.csv", "c-i_keybank_gross.csv"):
        pts = read_csv(s / name)
        # Starts after the event's windows; the NDFI windows, a change's, are still bridged.
        assert pts[0].date == "2021-12-31", name
        assert read_left_out(s / name) == ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
        assert "Paycheck Protection" not in dict(read_notes(s / name))["left-out"]
    dq = s / "c-i_keybank_delinquency-nonaccrual_four-quarter-average.csv"
    assert not [x for x in read_left_out(dq) if x.startswith(("2020", "2021"))]
    assert read_csv(dq)[0].date >= "2021-03-31"

