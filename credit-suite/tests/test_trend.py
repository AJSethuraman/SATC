"""tools/trend.py: the arithmetic, the polarity, and the engine agreement.

Shipped without tests on 4 September 2026, hand-verified against raw cells,
and said so on the docket. This is the debt paid. The last test is the one
that matters: the derived metrics the tool reports must equal what the
engine's own ``metric_value`` produces, because that is the whole design --
a trend must not be able to disagree with a dashboard.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import monitorbuild                                    # noqa: E402
import trend as T                                      # noqa: E402


def series(values, bank="X", cert="1"):
    periods = ["2026-%02d-01" % (12 - i) for i in range(len(values))]  # newest first
    return T.Series(bank=bank, cert=cert, periods=periods, values=list(values))


# --------------------------------------------------------------------------
# Series arithmetic
# --------------------------------------------------------------------------

def test_latest_skips_missing_quarters():
    assert series([None, 1.5, 1.2]).latest == 1.5


def test_change_is_now_minus_then_and_needs_enough_data():
    s = series([1.45, 1.40, 1.30, 1.28, 1.25])
    assert s.change(4) == pytest.approx(0.20)
    assert s.change(8) is None


def test_run_length_is_signed_and_stops_at_the_first_reversal():
    assert series([5, 4, 3, 2, 4, 1]).run_length() == 3        # three straight rises
    assert series([1, 2, 3, 4, 5]).run_length() == -4          # four straight falls
    assert series([3, 3, 2]).run_length() == 0                 # flat latest move
    assert series([1, 2]).run_length() == 0                    # too little data


# --------------------------------------------------------------------------
# Panel and polarity
# --------------------------------------------------------------------------

def panel(metric, **banks):
    p = T.Panel(metric=metric)
    for name, vals in banks.items():
        p.series[name] = series(vals, bank=name)
    return p


def test_peer_median_change_is_the_median_of_the_moves():
    p = panel("NCLNLSR", A=[2, 0, 0, 0, 1], B=[0, 0, 0, 0, 1], C=[3, 0, 0, 0, 0])
    assert p.peer_median_change(4) == statistics.median([1, -1, 3])


def test_deteriorating_reads_polarity_not_direction():
    """Equity falling is bad; noncurrent loans falling is good. Same arithmetic,
    opposite verdicts -- and the tool declares which rather than guessing."""
    worse_up = panel("NCLNLSR", A=[1.5, 0, 0, 0, 1.0], B=[0.5, 0, 0, 0, 1.0])
    worse_down = panel("EQV", A=[1.5, 0, 0, 0, 1.0], B=[0.5, 0, 0, 0, 1.0])
    assert [r[1].bank for r in T.deteriorating(worse_up, 4)] == ["A"]
    assert [r[1].bank for r in T.deteriorating(worse_down, 4)] == ["B"]


def test_a_metric_with_no_declared_polarity_gets_no_verdict():
    assert T.deteriorating(panel("LNATRESR", A=[9, 0, 0, 0, 1]), 4) == []


def test_worse_by_is_signed_so_bigger_is_always_worse():
    p = panel("EQV", A=[1.0, 0, 0, 0, 2.0], B=[1.9, 0, 0, 0, 2.0], C=[2.0, 0, 0, 0, 2.0])
    # moves: A -1.0, B -0.1, C 0.0; median -0.1. A is worse than peers by 0.9.
    rows = {r[1].bank: r[3] for r in T.deteriorating(p, 4)}
    assert rows["A"] == pytest.approx(0.9)


def test_sparkline_is_oldest_to_newest_and_never_crashes_on_gaps():
    assert len(T.spark([3, None, 2, 1])) == 3
    assert T.spark([1]) == ""
    assert T.spark([2, 2, 2]) == "---"


# --------------------------------------------------------------------------
# Against the real workbook: the engine agreement
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def demo_panels():
    """Both readings taken INSIDE the context: `built_monitor` deletes its
    scratch directory on exit, so a path handed out of it points at nothing."""
    with monitorbuild.built_monitor("fdic") as (workbook, _stdout):
        path = Path(workbook)
        return T.read_panel(path), T.read_panel(path, derive=False)


def test_every_dashboard_metric_is_trendable_not_just_the_raw_fields(demo_panels):
    """28 of the 53 metrics are formula-derived. The first version of the tool
    silently trended 25 and looked complete."""
    panels, _raw = demo_panels
    for metric in ("PD3089R", "TEXAS", "NTCONOTQ_BOOK", "UNINSDEPR", "CRECONR"):
        assert metric in panels, "%s is not trendable" % metric
        n = len([v for v in next(iter(panels[metric].series.values())).values
                 if v is not None])
        assert n > 1, "%s has only %d quarter(s); the derive loop broke again" % (metric, n)


def test_derived_metrics_equal_the_engines_own_definition(demo_panels):
    """The design guarantee. If this fails, a trend can contradict a dashboard
    and nothing says which is right."""
    from credit_suite.sources.fdic.engine_api import metric_value
    panels, raw = demo_panels
    bank = next(iter(panels["TEXAS"].series))
    for metric in ("TEXAS", "PD3089R", "LNDEPR", "NTCONOTQ_BOOK", "CRECONR"):
        tool = panels[metric].series[bank]
        for index in range(len(tool.periods)):
            fields = {name: p.series[bank].values[index]
                      for name, p in raw.items() if bank in p.series}
            assert tool.values[index] == pytest.approx(metric_value(metric, fields)), (
                metric, tool.periods[index])


# --------------------------------------------------------------------------
# The merger flag: a quarterly flow that spans a merger is not a quarter
# --------------------------------------------------------------------------

MERGER = {"4297": [{"bank": "Capital One NA", "effective": "2022-10-03",
                    "quarter": "2022-12-31", "out_name": "Capital One Bank (USA), NA",
                    "why": "quarter ending 2022-12-31 spans a merger"}]}


def merger_panels():
    """Two quarters of Capital One: the 670 and the quarter before it."""
    p3 = T.Panel(metric="P3CONOTH_BOOK")
    nco = T.Panel(metric="NTCONOTQ_BOOK")
    bal = T.Panel(metric="LNCONOTH")
    for name, panel, values in (("P3CONOTH_BOOK", p3, [21.5, 21.0]),
                                ("NTCONOTQ_BOOK", nco, [35.3, 670.41]),
                                ("LNCONOTH", bal, [3_970, 3_173])):
        panel.series["Capital One NA"] = T.Series(
            bank="Capital One NA", cert="4297",
            periods=["2023-03-31", "2022-12-31"], values=list(values))
    return {"P3CONOTH_BOOK": p3, "NTCONOTQ_BOOK": nco, "LNCONOTH": bal}


def test_the_670_is_blanked_because_the_quarter_spans_a_merger():
    """Capital One absorbed its card bank on 3 October 2022. The FDIC derives
    a quarterly flow by subtracting the previous quarter's year-to-date, which
    across a merger spans two banks -- so December's 'quarter' is not one."""
    panels = merger_panels()
    blanked = T.apply_merger_flags(panels, MERGER)
    assert panels["NTCONOTQ_BOOK"].series["Capital One NA"].values == [35.3, None]
    assert [(b[1], b[2]) for b in blanked] == [("NTCONOTQ_BOOK", "2022-12-31")]
    assert "merger" in blanked[0][3]


def test_only_the_flow_is_blanked_not_the_balances_or_the_arrears():
    """A 30-89 rate is a point in time: correct as at the date, describing a
    larger bank. Blanking it would hide a real number."""
    panels = merger_panels()
    T.apply_merger_flags(panels, MERGER)
    assert panels["P3CONOTH_BOOK"].series["Capital One NA"].values == [21.5, 21.0]
    assert panels["LNCONOTH"].series["Capital One NA"].values == [3_970, 3_173]


def test_a_bank_with_no_merger_keeps_every_quarter():
    panels = merger_panels()
    panels["NTCONOTQ_BOOK"].series["Capital One NA"].cert = "9999"
    assert T.apply_merger_flags(panels, MERGER) == []


def test_no_merger_record_blanks_nothing_and_says_so():
    """`None` is not `{}`. Nobody asked is not the same as none found, and a
    caller that collapses them is back to charting the 670."""
    panels = merger_panels()
    assert T.apply_merger_flags(panels, None) == []
    assert panels["NTCONOTQ_BOOK"].series["Capital One NA"].values == [35.3, 670.41]


def test_every_quarterly_flow_metric_is_covered_and_nothing_else():
    """The list is the engine's, so a metric added there is flagged here
    without anyone remembering to."""
    flows = T.flow_metrics()
    assert "NTCONOTQ_BOOK" in flows and "NTLNLSQR" in flows
    assert "P3CONOTH_BOOK" not in flows and "TEXAS" not in flows
    assert all(m.endswith("_BOOK") or m == "NTLNLSQR" for m in flows)
