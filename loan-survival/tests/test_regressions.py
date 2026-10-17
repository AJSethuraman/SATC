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


# ---- second Codex review of PR 445 (reviewed 23a0e90)

def test_snapshot_unreadable_month_is_listed_and_does_not_fake_a_loan_leaving():
    rows = []
    for loan, months in (("L1", ["2024-01-31", "garbage", "2024-03-31"]), ("L2", ["2024-01-31", "2024-02-29", "2024-03-31"])):
        for m in months:
            rows.append(dict(loan_id=loan, month_end=m, dpd=0))
    sheets, used, dropped = do.snapshot_mode(pd.DataFrame(rows), _args(dpd_col="dpd"), pd.Timestamp("2024-03-31"))
    counts = sheets["RollCounts"].drop(columns="from (this month)")
    assert "Left file (no status)" not in counts.columns or int(counts["Left file (no status)"].sum()) == 0
    assert used == int(counts.to_numpy().sum()) == 2          # only L2's two transitions
    assert set(sheets["Excluded"]["loan_id"]) == {"L1"} and dropped == 3  # all three of L1's rows, with the reason


def test_column_names_with_a_percent_sign_survive_the_settings_file():
    text = "[columns]\norig_date = Open %\nchargeoff_date = CO date\n\n[test: util]\ncolumn = Utilization %\ncutoffs = 50\n"
    st = ls.Settings(text)
    assert st.cols["orig_date"] == "Open %" and st.tests[0][1]["column"] == "Utilization %"


def test_output_path_cannot_be_the_input_file(tmp_path):
    import pytest
    src = tmp_path / "loans.xlsx"
    pd.read_csv(ROOT / "sample" / "fake_book.csv").to_excel(src, index=False)
    before = src.read_bytes()
    with pytest.raises(ls.UserError, match="same file"):
        ls.run(src, None, src)
    assert src.read_bytes() == before


# ---- third Codex review of PR 445 (reviewed 17d95f0)

def test_blank_loan_ids_are_not_duplicates():
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv")
    raw.loc[:2, "loan_id"] = np.nan
    st = ls.Settings((ROOT / "sample" / "settings_example.ini").read_text())
    df, excluded = ls.prepare(raw, st)
    assert len(df) == len(raw) and len(excluded) == 0


def test_header_with_a_space_hash_survives_the_settings_file():
    import loan_survival_gui as g
    state = g.new_state()
    state["cols"] = {"orig_date": "Open Date", "chargeoff_date": "CO Date", "loan_id": "Loan #"}
    state["tests"] = [{"name": "t", "spec": {"column": "Rate ;fixed", "cutoffs": "5"}}]
    text = g.build_settings_text(state)
    assert ls.Settings(text).cols["loan_id"] == "Loan #" and ls.Settings(text).tests[0][1]["column"] == "Rate ;fixed"
    assert g.parse_settings_text(text)["cols"]["loan_id"] == "Loan #"


def test_inline_comment_after_a_number_is_refused_in_words():
    import pytest
    with pytest.raises(ls.UserError, match="own line"):
        ls.Settings("[settings]\nmin_at_risk = 30   ; stop showing a month below this\n")


def test_run_does_not_touch_files_already_in_the_output_folder(tmp_path):
    (tmp_path / "_chart_0.png").write_bytes(b"not mine")
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv")
    src = tmp_path / "book.csv"
    raw.to_csv(src, index=False)
    ls.run(src, (ROOT / "sample" / "settings_example.ini").read_text(), tmp_path / "out.xlsx")
    assert (tmp_path / "_chart_0.png").read_bytes() == b"not mine"


def test_model_column_with_numbers_stored_as_text_keeps_the_numbers():
    df = pd.DataFrame({"fico": pd.Series(["650", "700", "Y"], dtype=object)})
    X, _ = ls.model_terms(df, "fico per -50")
    assert X.iloc[0, 0] == 650 / -50 and X.iloc[1, 0] == 700 / -50 and X.iloc[2, 0] == 1 / -50


def test_xls_without_its_reader_says_what_to_do(monkeypatch, tmp_path):
    import pytest

    def no_xlrd(*a, **k):
        raise ImportError("Missing optional dependency 'xlrd'")
    monkeypatch.setattr(pd, "read_excel", no_xlrd)
    f = tmp_path / "old.xls"
    f.write_bytes(b"x")
    with pytest.raises(ls.UserError, match="xlsx"):
        ls.load(f)


# ---- fourth Codex review of PR 445 (reviewed 0f83681)

def test_snapshot_rows_with_no_loan_id_are_listed_not_dropped():
    rows = [dict(loan_id=l, month_end=m, dpd=0) for l in ("L1", None)
            for m in pd.date_range("2024-01-31", periods=3, freq="ME")]
    sheets, used, dropped = do.snapshot_mode(pd.DataFrame(rows), _args(dpd_col="dpd"), pd.Timestamp("2024-03-31"))
    assert used == 2 and dropped == 3
    assert "no loan id" in sheets["Excluded"]["exclusion_reason"].iloc[0].lower()


def _two_loans_with_a_charge_off_after_as_of():
    cols = "[columns]\nloan_id = loan_id\norig_date = orig_date\nchargeoff_date = chargeoff_date\nfirst_90_date = first_90_date\ndpd_asof = dpd_asof\n"
    st = ls.Settings(cols)
    df = pd.DataFrame({
        "loan_id": ["A", "B", "C"], "orig_date": pd.to_datetime(["2022-01-01"] * 3),
        "first_90_date": pd.to_datetime(["2023-01-31"] * 3),
        # A: charged off in the window. B: charged off AFTER as-of (not observable yet). C: after the window but before as-of
        "chargeoff_date": pd.to_datetime(["2023-03-31", "2025-01-31", "2024-06-30"]), "dpd_asof": [0, 0, 0]})
    return st, df, pd.Timestamp("2024-12-31")


def test_charge_off_after_as_of_is_not_reported_as_an_event():
    st, df, as_of = _two_loans_with_a_charge_off_after_as_of()
    _, tbl, _, _ = ls.bad_event_check(df, st, as_of)
    got = dict(zip(tbl.iloc[:, 0], tbl["loans"]))
    assert got.get("charged off after the window", 0) == 1       # C only; B had not happened by as-of
    assert got.get("cured (current at as-of)", 0) == 1            # B read as not charged off


def test_standalone_charge_off_after_as_of_is_not_reported_as_an_event():
    st, df, as_of = _two_loans_with_a_charge_off_after_as_of()
    df = df.rename(columns={"first_90_date": "first_90_date"}).assign(payoff_date=pd.NaT)
    sheets, _, _ = do.loan_mode(df.copy(), _args(), as_of)
    got = dict(zip(sheets["Outcomes"].iloc[:, 0], sheets["Outcomes"]["loans"]))
    assert got.get("charged off, but after the window", 0) == 1 and got.get("cured (current at as-of)", 0) == 1


def test_model_column_names_may_contain_spaces():
    import loan_survival_gui as g
    df = pd.DataFrame({"Credit Score": [650.0, 700.0], "Has Flag": ["Y", "N"]})
    X, labels = ls.model_terms(df, "Credit Score per -50, Has Flag")
    assert X.iloc[0, 0] == 650 / -50 and X.iloc[1, 1] == 0
    assert g.split_model("Credit Score per -50, Has Flag") == [("Credit Score", "50", "lower"), ("Has Flag", "", "higher")]
    assert g.model_term("Credit Score", "50", "lower") == "Credit Score per -50"


def test_all_missing_revenue_total_is_blank_not_zero():
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv")
    raw.loc[pd.to_datetime(raw.orig_date).dt.year == 2025, "net_revenue"] = np.nan
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.csv"
        raw.to_csv(p, index=False)
        r = ls.run(p, (ROOT / "sample" / "settings_example.ini").read_text(), Path(tmp) / "o.xlsx")
    t = r["tests"]
    g25 = t[(t.comparison == "origination year") & (t.group.astype(str) == "2025")].iloc[0]
    assert pd.isna(g25["net_revenue_total"]) and pd.isna(g25["net_revenue_per_1000"])


# ---- fifth Codex review of PR 445 (reviewed 9e93bf1)

def test_model_columns_offered_by_the_gui_match_what_the_engine_can_use():
    import loan_survival_gui as g
    df = pd.DataFrame({"Score": pd.Series(["650", "700", "N/A", "720", "680"] * 4, dtype=object),
                       "Revenue per 100": [1.5, 2.5, 3.5, 4.5, 5.5] * 4, "Plain": [1.5, 2.5, 3.5, 4.5, 5.5] * 4,
                       "Words": ["a", "b", "c", "d", "e"] * 4})
    offered = g.model_columns(df)
    assert "Score" in offered and "Plain" in offered
    assert "Revenue per 100" not in offered and "Words" not in offered


def test_dates_in_mixed_formats_are_all_read():
    s = pd.Series(["2024-01-31", "02/28/2024", "March 5, 2024", None])
    import loan_survival_gui as g
    assert g.date_problems(s) == (0, 3, 1)
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv", dtype=str)
    raw.loc[0, "orig_date"] = "02/28/2022"
    st = ls.Settings((ROOT / "sample" / "settings_example.ini").read_text())
    df, excluded = ls.prepare(raw, st)
    assert len(excluded) == 0 and df.loc[0, "orig_date"] == pd.Timestamp("2022-02-28")


def test_the_same_factor_twice_is_refused_and_found_by_full_name():
    import pytest
    import loan_survival_gui as g
    df = pd.DataFrame({"fico": [1.0, 2.0]})
    with pytest.raises(ls.UserError, match="twice"):
        ls.model_terms(df, "fico per -50, fico")
    assert g.model_has_column(["Credit Score per -50"], "Credit Score") and not g.model_has_column(["Credit Score per -50"], "Credit")


def test_a_comparison_that_could_not_be_tested_says_so():
    import tempfile
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv")
    text = "[columns]\nloan_id=loan_id\norig_date=orig_date\nchargeoff_date=chargeoff_date\n\n[test: one year only]\ngroup_by = year\norig_from = 2023-01-01\norig_to = 2023-12-31\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.csv"
        raw.to_csv(p, index=False)
        r = ls.run(p, text, Path(tmp) / "o.xlsx")
    t = r["tests"]
    assert len(t) == 1 and pd.isna(t["logrank_p"].iloc[0]) and "not testable" in t["reading"].iloc[0]


def test_excluded_sheet_shows_the_unreadable_text_not_a_blank():
    raw = pd.read_csv(ROOT / "sample" / "fake_book.csv", dtype=str)
    raw.loc[3, "orig_date"] = "TBD"
    st = ls.Settings((ROOT / "sample" / "settings_example.ini").read_text())
    _, excluded = ls.prepare(raw, st)
    assert list(excluded["orig_date"]) == ["TBD"] and "unparseable" in excluded["exclusion_reason"].iloc[0]
