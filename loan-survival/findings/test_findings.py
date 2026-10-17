"""Adversarial findings against loan_survival.py, 17 Oct 2026. Every test here FAILS against the engine as it stands.

Each test asserts the behaviour the project's own rules call for (CLAUDE.md non-negotiables, the design decisions in
the brief) and was run and watched fail. No source was changed. Ordered by rank:

    1. a figure is wrong, or a refusal is missing       (test names start with test_r1_)
    2. misleading or unauditable                         (test_r2_)
    3. robustness                                        (test_r3_)

Run from loan-survival/:  python -m pytest -q findings/test_findings.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import loan_survival as ls  # noqa: E402

BOOK = ROOT / "sample" / "fake_book.csv"
COLS = ("[columns]\nloan_id=loan_id\norig_date=orig_date\nchargeoff_date=chargeoff_date\n"
        "first_90_date=first_90_date\npayoff_date=payoff_date\n")
CO_ONLY = "\n[settings]\nbad_event = chargeoff\n"
VINTAGE = "\n[test: v]\ngroup_by = year\n"


def _run(tmp_path, raw, text, suffix=".csv"):
    """Write `raw` as a loan file, run the engine on it, return (summary, every sheet of the workbook)."""
    src = tmp_path / f"book{suffix}"
    if suffix == ".csv":
        raw.to_csv(src, index=False)
    else:
        raw.to_excel(src, index=False)
    out = tmp_path / "out.xlsx"
    r = ls.run(src, text, out)
    return r, pd.read_excel(out, sheet_name=None)


def _book():
    return pd.read_csv(BOOK)


# ============================================================================ rank 1: a figure is wrong, or a refusal is missing

def test_r1_excel_serial_dates_are_not_read_as_1970(tmp_path):
    """A charge-off column holding Excel serial numbers (General-formatted cells, as an .xlsx exported from a core system
    often has) must be read as the dates they are, or excluded as unreadable with the number shown. Today every serial
    becomes 1970-01-01 00:00:00.000045, every charged-off loan is excluded as 'chargeoff_date before origination', the
    bad rate of every vintage is 0%, and the Excluded sheet shows a 1970 date the file never contained.
    Non-negotiable 5: never invent a value. Confidence: high."""
    raw = _book().head(200).copy()
    raw["chargeoff_date"] = [(pd.Timestamp(d) - pd.Timestamp("1899-12-30")).days if pd.notna(d) else np.nan
                             for d in raw["chargeoff_date"]]
    true_bads = int(raw["chargeoff_date"].notna().sum())
    r, s = _run(tmp_path, raw, COLS + CO_ONLY + VINTAGE, suffix=".xlsx")
    ex = s["Excluded"]
    shown = pd.to_datetime(ex.get("chargeoff_date", pd.Series(dtype=object)), errors="coerce")
    assert not (shown.dt.year == 1970).any(), "the audit trail shows a 1970 date that is not in the file"
    assert int(r["tests"]["bads_to_date"].sum()) == true_bads or "unparseable" in " ".join(ex["exclusion_reason"].astype(str))


def test_r1_one_future_dated_typo_does_not_give_young_vintages_a_36_month_figure(tmp_path):
    """With as_of left to 'the latest date in the file', one payoff date typed as 2062 makes every loan observed to
    2062. The 2024 and 2025 vintages, which have at most 33 months of history, then show a cum_bad_m36 that was blank
    before the typo (0.147 and 0.055 on the fake book). The run should refuse an as-of after today, exclude the row, or
    leave the unrelated figures unchanged; it does none. Non-negotiables 4 and 5. Confidence: medium-high (the as-of is
    in the RunLog, but the figures on the Tests sheet are wrong without any note on that sheet)."""
    raw = _book().astype({"payoff_date": "object"})
    raw.loc[0, "payoff_date"] = "2062-01-01"
    try:
        r, s = _run(tmp_path, raw, COLS + CO_ONLY + VINTAGE)
    except ls.UserError:
        return
    t = r["tests"].assign(group=lambda d: d["group"].astype(str)).set_index("group")
    excluded_ids = set(s["Excluded"].get("loan_id", pd.Series(dtype=object)).astype(str))
    assert raw.loc[0, "loan_id"] in excluded_ids or np.isnan(t.loc["2025", "cum_bad_m36"]), \
        f"2025 vintage got cum_bad_m36 = {t.loc['2025', 'cum_bad_m36']:.3f} from 33 months of history"


def test_r1_a_day_first_date_column_is_not_read_in_two_conventions():
    """In a dd/mm/yyyy file, '25/02/2024' can only be day-first and is read so; '01/03/2024' is read month-first
    (3 January). One column, two conventions, and no refusal. Here loan A opened 1 March and charged off 15 March
    (0 months on book) but is given 2 months. When a column holds values that are only readable day-first, the
    ambiguous ones must follow or be excluded as ambiguous. Confidence: medium-high (docstring says slashes are
    month-first; the engine still mixes the two within one column without saying so)."""
    b = pd.DataFrame([dict(loan_id="A", orig_date="01/03/2024", chargeoff_date="15/03/2024"),
                      dict(loan_id="B", orig_date="25/02/2024", chargeoff_date="28/02/2025")])
    st = ls.Settings("[columns]\nloan_id=loan_id\norig_date=orig_date\nchargeoff_date=chargeoff_date\n")
    try:
        df, ex = ls.prepare(b, st)
    except ls.UserError:
        return
    L = ls.add_time_event(df, st, pd.Timestamp("2026-09-30"), ["chargeoff_date"]).set_index("loan_id")
    assert "A" not in L.index or L.loc["A", "_time"] == 0, f"loan A: {L.loc['A', ['orig_date', 'chargeoff_date', '_time']].tolist()}"


def test_r1_cutoff_backtest_p_value_is_the_two_group_test(tmp_path):
    """A cutoff backtest asks 'below the cutoff vs at or above'. When the column has blanks the engine adds a third
    group ('fico missing') and the log-rank p on every row is the three-group, two-degree-of-freedom test, not the
    question asked: on the fake book with 40 blank FICOs and charge-off as the bad event, p = 5.1e-28 reported vs
    3.0e-28 for below-vs-above (statistic 125.7 on 2 df vs 121.5 on 1 df). Confidence: medium-high."""
    raw = _book()
    raw.loc[raw.index[:40], "fico"] = np.nan
    r, _ = _run(tmp_path, raw, COLS + CO_ONLY + "\n[test: c]\ncolumn = fico\ncutoffs = 700\norig_to = 2022-12-31\n")
    reported = float(r["tests"]["logrank_p"].iloc[0])
    st = ls.Settings(COLS)
    df, _ = ls.prepare(raw, st)
    L = ls.add_time_event(df, st, r["as_of"], ["chargeoff_date"])
    L = L[(L["orig_date"] <= "2022-12-31") & L["fico"].notna()]
    _, dof, two_group = ls.logrank(L["_time"].to_numpy(), L["_event"].to_numpy(), np.where(L["fico"] < 700, "lo", "hi"))
    assert abs(reported - two_group) <= 1e-9 * two_group, \
        f"sheet p={reported:.3e} (a {2}-degree-of-freedom test), below-vs-above p={two_group:.3e} ({dof} degree)"


def test_r1_unreadable_net_revenue_is_not_silently_left_out_of_the_total(tmp_path):
    """100 loans with net revenue written '$1,234.00' cannot be read as numbers. The total on the Tests sheet is the sum
    of the other loans, nothing is excluded or noted, and the group's 'loans' still counts all of them. Expected: the
    true total, or those loans listed as unreadable, or a refusal. Non-negotiable 5. Confidence: medium-high."""
    raw = _book().astype({"net_revenue": "object"})
    true_total = raw[pd.to_datetime(raw["orig_date"]).dt.year == 2021]["net_revenue"].sum()
    raw.loc[raw.index[:100], "net_revenue"] = [f"${v:,.2f}" for v in raw["net_revenue"][:100]]
    try:
        r, s = _run(tmp_path, raw, COLS + "net_revenue=net_revenue\namount=amount\n" + CO_ONLY + VINTAGE)
    except ls.UserError:
        return
    t = r["tests"].assign(group=lambda d: d["group"].astype(str)).set_index("group")
    assert abs(t.loc["2021", "net_revenue_total"] - true_total) < 1e-6 or r["rows_excluded"] >= 100, \
        f"total {t.loc['2021', 'net_revenue_total']:,.2f} vs {true_total:,.2f}, excluded {r['rows_excluded']}"


# ============================================================================ rank 2: misleading or unauditable

def test_r2_a_charge_off_dated_after_payoff_is_not_silently_a_good_loan(tmp_path):
    """The bad-event check drops a loan whose charge-off is dated after its payoff as a row that 'cannot also have
    happened' (its own comment). The Tests and Curves sheets then count the same loan as one that never went bad,
    censored at payoff, and the Excluded sheet does not list it. One row, two treatments, neither stated. Expected:
    excluded with a reason, or counted as bad; not quietly good. Confidence: medium (the design says 'censored at
    payoff', but it also says the inconsistent row is left out of every figure)."""
    raw = _book().astype({"chargeoff_date": "object"})
    i = raw.index[raw["payoff_date"].notna()][0]
    raw.loc[i, "chargeoff_date"] = str((pd.Timestamp(raw.loc[i, "payoff_date"]) + pd.DateOffset(months=2)).date())
    base, _ = _run(tmp_path, _book(), COLS + CO_ONLY + VINTAGE)
    r, s = _run(tmp_path, raw, COLS + CO_ONLY + VINTAGE)
    listed = raw.loc[i, "loan_id"] in set(s["Excluded"].get("loan_id", pd.Series(dtype=object)).astype(str))
    counted_bad = int(r["tests"]["bads_to_date"].sum()) == int(base["tests"]["bads_to_date"].sum()) + 1
    assert listed or counted_bad


def test_r2_a_comparison_that_covers_no_loans_still_appears_in_the_output(tmp_path):
    """A [test: ...] whose window or conditions match no loans produces no rows at all: the test's name is simply
    absent from the Tests sheet, with no note and no refusal. A reader cannot tell a test that ran and found nothing
    from one that was never in the settings. Confidence: medium-high."""
    try:
        r, s = _run(tmp_path, _book(), COLS + CO_ONLY + "\n[test: nobody]\ngroup_by = year\norig_from = 2030-01-01\n" + VINTAGE)
    except ls.UserError:
        return
    assert "nobody" in set(s["Tests"]["test"].astype(str))


def test_r2_the_95_percent_range_for_a_group_with_no_bads_is_not_zero_to_zero():
    """20 loans, no bad event: the Curves sheet reports cum_bad_lo95 = cum_bad_hi95 = 0.0, a 95% range of 0% to 0%.
    The log(-log) Greenwood range is undefined at S = 1 (SciPy's ecdf returns NaN there); an examiner reading 'upper
    bound 0% from 20 loans' is being told something no method supports. Expected: blank, or an upper bound above 0.
    Confidence: medium-high."""
    km = ls.kaplan_meier(np.full(20, 10), np.zeros(20, int))
    hi = km.loc[km["month_on_book"] == 10, "cum_bad_hi95"].iloc[0]
    assert np.isnan(hi) or hi > 0, f"upper 95% bound reported as {hi}"


def test_r2_duplicate_ids_that_disagree_are_refused_not_picked_by_file_order(tmp_path):
    """Two rows with one loan id, one charged off and one not: the first in the file wins. The same loans in a
    different order give a different bad count (8 vs 9 here). The snapshot mode refuses two rows for one loan rather
    than pick between them (test_two_snapshot_rows_for_one_loan_and_month_are_refused_not_picked_between); loan mode
    should do the same when the copies disagree. Confidence: medium."""
    d = _book().head(100).astype({"chargeoff_date": "object"})
    extra = d.iloc[[0]].copy()
    extra["chargeoff_date"] = "2023-01-15"
    bads = []
    for frame in (pd.concat([d, extra]), pd.concat([extra, d])):
        try:
            r, _ = _run(tmp_path, frame, COLS + CO_ONLY + VINTAGE)
        except ls.UserError:
            return
        bads.append(int(r["tests"]["bads_to_date"].sum()))
    assert bads[0] == bads[1], f"bad count depends on row order: {bads}"


def test_r2_net_revenue_per_loan_can_be_reconciled_from_its_own_row(tmp_path):
    """net_revenue_per_loan is the mean over loans with a revenue value; 'loans' counts every loan in the group. With
    500 blank revenues, 2021 shows total 1,461,639, loans 1,500, per loan 1,462 (total / loans is 974). Nothing on the
    row gives the denominator used. Expected: per_loan = total / loans, or a column with the count of loans that had
    a revenue value. Non-negotiable 4. Confidence: medium-low."""
    raw = _book()
    raw.loc[raw.index[:500], "net_revenue"] = np.nan
    r, _ = _run(tmp_path, raw, COLS + "net_revenue=net_revenue\namount=amount\n" + CO_ONLY + VINTAGE)
    t = r["tests"].assign(group=lambda d: d["group"].astype(str)).set_index("group")
    row = t.loc["2021"]
    has_count = any("revenue" in c and ("loans" in c or "count" in c or c.startswith("n_")) for c in t.columns
                    if c not in ("net_revenue_total", "net_revenue_per_loan", "net_revenue_per_1000"))
    assert has_count or abs(row["net_revenue_per_loan"] * row["loans"] - row["net_revenue_total"]) < 1e-6


@pytest.mark.parametrize("extra", [
    "\n[test: v]\ngroup_by = year\norig_too = 2022-12-31\n",      # window silently not applied
    "\n[test: v]\ngroup_by = year\nwhere_ = fico >= 700\n",       # condition silently not applied
    "\n[settings]\nmin_at_rsk = 5000\n[test: v]\ngroup_by = year\n",  # default 30 silently used
])
def test_r2_a_misspelt_setting_is_refused_not_ignored(tmp_path, extra):
    """A key the engine does not know ('orig_too', 'where_', 'min_at_rsk') is ignored and the run proceeds on the
    default, so the comparison the person wrote is not the one that ran. The RunLog records the typo verbatim, which
    is the only tell. Expected: a refusal naming the unknown key. Confidence: medium."""
    with pytest.raises(ls.UserError):
        _run(tmp_path, _book(), COLS + CO_ONLY + extra)


# ============================================================================ rank 3: robustness

@pytest.mark.parametrize("extra,what", [
    ("\n[test: a]\ngroup_by = year\n[test: a]\ngroup_by = year\n", "two tests with one name"),
    ("\n[test: c]\ncolumn = fico\ncutoffs = 640,,660\n", "an empty cutoff"),
    ("\n[test: s]\nsplit_date = 2024-01-01, 2024-01-01\n", "a split date given twice"),
    ("\n[test: s]\nsplit_date = whenever\n", "a split date that is not a date"),
    ("\n[data]\nas_of = 2026-09-31\n[test: v]\ngroup_by = year\n", "an as-of date that does not exist"),
    ("\n[test: v]\ngroup_by = year\norig_from = soon\n", "an origination window that is not a date"),
])
def test_r3_a_settings_mistake_is_refused_in_words(tmp_path, extra, what):
    """Each of these settings mistakes escapes as a raw exception (DuplicateSectionError, ValueError, DateParseError)
    instead of a UserError. The CLI prints a traceback; the window says 'The run stopped unexpectedly'. Confidence:
    high that it crashes; the expectation is the brief's 'refuses in plain words'."""
    with pytest.raises(ls.UserError):
        _run(tmp_path, _book(), COLS + CO_ONLY + extra)


def test_r3_an_empty_loan_file_is_refused_in_words(tmp_path):
    """A file with a header and no rows dies in the RunLog with 'NaTType does not support strftime'. Confidence: high."""
    with pytest.raises(ls.UserError):
        _run(tmp_path, _book().head(0), COLS + CO_ONLY + VINTAGE)


def test_r3_a_windows_1252_csv_is_read_or_refused_in_words(tmp_path):
    """A CSV saved by Excel on Windows with an accented character (cp1252) raises UnicodeDecodeError. Bank extracts
    are often cp1252. Expected: read it, or refuse in words. Confidence: high."""
    src = tmp_path / "book.csv"
    _book().head(50).assign(note="caf\xe9").to_csv(src, index=False, encoding="cp1252")
    try:
        ls.run(src, COLS + CO_ONLY + VINTAGE, tmp_path / "out.xlsx")
    except ls.UserError:
        return
    except UnicodeDecodeError as e:
        pytest.fail(f"raw UnicodeDecodeError: {e}")


def test_r3_a_header_with_trailing_whitespace_can_be_mapped(tmp_path):
    """A header 'orig_date ' (trailing space, common in extracts) appears in the window's dropdowns, is written to the
    settings as 'orig_date = orig_date ', and the engine strips the value, so the column can never be mapped: 'Mapped
    column(s) not found in file'. Expected: match the header as the file has it, or strip both sides. Confidence:
    medium-high."""
    raw = _book().rename(columns={"orig_date": "orig_date "})
    cols = "[columns]\nloan_id=loan_id\norig_date=orig_date \nchargeoff_date=chargeoff_date\n"
    r, _ = _run(tmp_path, raw, cols + CO_ONLY + VINTAGE)
    assert r["rows_used"] == len(raw)


def test_r3_orig_to_includes_a_loan_opened_on_that_day_with_a_time_of_day(tmp_path):
    """orig_to = 2022-12-31 is compared as midnight, so a loan whose origination carries a time (2022-12-31 09:00,
    as an Excel datetime can) falls out of the window with no note: 2,999 loans instead of 3,000. Dates are days
    here (months_between ignores the time). Confidence: medium."""
    raw = _book().astype({"orig_date": "object"})
    raw.loc[0, "orig_date"] = "2022-12-31 09:00:00"
    want = int((pd.to_datetime(_book()["orig_date"]) <= "2022-12-31").sum()) + 1  # loan 0 opened in 2021, now moved to 2022-12-31
    r, _ = _run(tmp_path, raw, COLS + CO_ONLY + "\n[test: v]\ngroup_by = year\norig_to = 2022-12-31\n")
    assert int(r["tests"]["loans"].sum()) == want


def test_r3_a_model_scale_of_zero_is_refused(tmp_path):
    """'fico per 0' divides the column by zero; every value becomes inf, which is not 'missing', so no row is dropped
    and the fit fails. The sheet then says 'this factor may separate bad loans perfectly, or there are too few bads',
    which is not what happened. Expected: a refusal naming the scale. Confidence: medium-high."""
    with pytest.raises(ls.UserError):
        _run(tmp_path, _book(), COLS + CO_ONLY + "\n[test: m]\nmodel = fico per 0\n")


def test_r3_a_factor_with_one_value_is_named_as_such(tmp_path):
    """A model factor that is the same for every loan cannot be estimated. The sheet blames perfect separation or too
    few bads, and the 'together' fit of the other factor fails with 'two factors may say the same thing'. Expected: a
    refusal, or a reading that says the factor has one value. Confidence: medium."""
    raw = _book()
    raw["const"] = 1
    try:
        _, s = _run(tmp_path, raw, COLS + CO_ONLY + "\n[test: m]\nmodel = const, fico\n")
    except ls.UserError:
        return
    reading = str(s["Models"].set_index("variable").loc["const", "reading"]).lower()
    assert "one value" in reading or "constant" in reading or "same for every" in reading, reading


def test_r3_cutoffs_on_a_column_that_is_not_numeric_are_refused(tmp_path):
    """cutoffs on a Y/N column puts every loan in '<col> missing' and reports one group, 'not testable', instead of
    saying the column is not numeric. Confidence: medium-high."""
    with pytest.raises(ls.UserError):
        _run(tmp_path, _book(), COLS + CO_ONLY + "\n[test: c]\ncolumn = income_gt_sales\ncutoffs = 1\n")


def test_r3_a_source_column_named_exclusion_reason_does_not_break_the_excluded_sheet(tmp_path):
    """If the loan file already has a column called 'exclusion_reason', the first exclusion crashes with
    'cannot insert exclusion_reason, already exists'. Confidence: high."""
    raw = _book()
    raw["exclusion_reason"] = "from the source"
    raw.loc[0, "orig_date"] = np.nan
    r, _ = _run(tmp_path, raw, COLS + CO_ONLY + VINTAGE)
    assert r["rows_excluded"] == 1
