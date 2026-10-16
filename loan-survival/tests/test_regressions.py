"""Regression tests for the Codex review of PR 445. Each one was red before its fix."""
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import delinquency_outcomes as do  # noqa: E402
import loan_survival as ls  # noqa: E402

AS_OF = pd.Timestamp("2026-09-30")


def _args(**kw):
    base = dict(id_col="loan_id", first90_col="first_90_date", co_col="chargeoff_date", pif_col="payoff_date",
                dpd_col="dpd_asof", month_col="month_end", status_col="", co_values=["CO"], pif_values=["PIF"],
                window=12, proxy_min_co_share=0.6, proxy_min_lead=3, skip_warn=0.2)
    base.update(kw)
    return Namespace(**base)


def _measure(sheets, name):
    return sheets["Verdict"].set_index("measure").loc[name, "value"]


def test_charge_off_with_90_after_it_counts_as_skipping_90():
    df = pd.DataFrame({
        "loan_id": ["A", "B", "C"],
        "first_90_date": ["2024-01-31", "2025-06-30", None],
        "chargeoff_date": ["2024-05-31", "2025-03-31", "2024-02-29"],  # B: 90+ date recorded after the charge-off
        "payoff_date": [None, None, None], "dpd_asof": [0, 0, 0]})
    sheets, _, _ = do.loan_mode(df, _args(), AS_OF)
    assert _measure(sheets, "charge-offs (all time) that never hit 90+ first") == 2
    assert abs(_measure(sheets, "as a share of all charge-offs") - 2 / 3) < 1e-12


def test_malformed_loan_dates_are_excluded_not_read_as_blank():
    df = pd.DataFrame({
        "loan_id": ["A", "B", "C"],
        "first_90_date": ["2024-01-31", "2024-01-31", "2024-01-31"],
        "chargeoff_date": ["2024-05-31", "not a date", None],
        "payoff_date": [None, None, None], "dpd_asof": [0, 0, 0]})
    sheets, used, excl = do.loan_mode(df, _args(), AS_OF)
    assert used == 2 and excl == 1
    ex = sheets["Excluded"]
    assert list(ex["loan_id"]) == ["B"] and "chargeoff_date" in ex["exclusion_reason"].iloc[0]


def test_economics_per_1000_uses_rows_with_both_values():
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv")
    yr = pd.to_datetime(raw.orig_date).dt.year
    i_no_amt = raw.index[yr == 2022][0]
    i_no_rev = raw.index[yr == 2022][1]
    raw.loc[i_no_amt, "amount"] = np.nan   # has revenue, no amount: would inflate the ratio
    raw.loc[i_no_rev, "net_revenue"] = np.nan  # has amount, no revenue: would dilute it
    both = raw.net_revenue.notna() & raw.amount.notna()
    ref = raw[both & (yr == 2022)]
    expected = ref.net_revenue.sum() / ref.amount.sum() * 1000
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.csv"
        raw.to_csv(p, index=False)
        r = ls.run(p, (ROOT / "sample" / "settings_example.ini").read_text(), Path(tmp) / "o.xlsx")
    t = r["tests"]
    got = t[(t.comparison == "origination year") & (t.group.astype(str) == "2022")]["net_revenue_per_1000"].iloc[0]
    assert abs(got - expected) < 1e-9, (got, expected)


def test_snapshot_transitions_used_matches_the_matrix_denominator():
    rows = []
    for loan, dpds in (("L1", [0, None, 0]), ("L2", [0, 0, 0])):
        for m, d in zip(pd.date_range("2024-01-31", periods=3, freq="ME"), dpds):
            rows.append(dict(loan_id=loan, month_end=m, dpd=d))
    sheets, used, dropped = do.snapshot_mode(pd.DataFrame(rows), _args(dpd_col="dpd"), pd.Timestamp("2024-03-31"))
    counts = sheets["RollCounts"].drop(columns="from (this month)")
    assert used == int(counts.to_numpy().sum()) == 2
    assert dropped == 2 and "Excluded" in sheets
