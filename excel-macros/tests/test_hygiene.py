"""The hygiene macros, run in LibreOffice on a synthetic population with every problem planted on purpose.

The firm, 5 Oct 2026: "It'd be nice to be able to easily take a population and figure out basically how messed up it
is or how we can fix it." Every expected count here is worked out in Python from the same rows the workbook holds,
never typed in.
"""
from __future__ import annotations

import datetime as dt
import random

import pytest
from openpyxl import Workbook, load_workbook

from harness import Office

N = 300
HEADS = ["LOAN_ID", "FICO", "STATE", "ORIG_DT", "AMT_TXT", "FLAG_YN", "CONST", "FICO_COPY", "EMPTY", "NOTE"]
AUDIT_HEADS = ["Column", "Type found", "Blank", "Blank %", "Distinct", "Most common", "Numbers as text",
               "Dates as text", "Extra spaces", "Odd characters", "Same value in every row", "Same as column",
               "Keep?", "New name", "Flag: 1 when", "Notes"]


def population() -> list[list]:
    """N loans. Planted: two repeated loan ids, blank FICOs, states with stray spaces and a no-break space, dates
    stored as text, amounts stored as text, a Y/N flag in mixed case, a constant column, a column copying FICO, an
    empty column, and a note column of free text."""
    rnd = random.Random(20261005)
    rows = []
    for i in range(N):
        loan = 1000 + i if i not in (17, 230) else 1000 + i - 1          # rows 17 and 230 repeat the id before
        fico = None if i % 37 == 0 else rnd.randint(560, 820)
        state = rnd.choice(["OH", "NY", "TX", "CA"])
        if i % 41 == 0:
            state += " "
        if i == 99:
            state = "OH "
        day = dt.date(2023, 8, 1) + dt.timedelta(days=rnd.randint(0, 700))
        orig = day.isoformat() if i % 23 == 0 else dt.datetime(day.year, day.month, day.day)
        amt = str(rnd.randint(1, 90) * 500) if i % 3 else rnd.randint(1, 90) * 500
        flag = rnd.choice(["Y", "N", "y", "n", None]) if i % 5 else "Y"
        note = rnd.choice(["", "   ", "ok", "see file", "Ok"]) or None
        rows.append([loan, fico, state, orig, amt, flag, "USD", fico, None, note])
    return rows


def write_population(path) -> list[list]:
    rows = population()
    wb = Workbook()
    ws = wb.active
    ws.title = "use"
    ws.append(HEADS)
    for r in rows:
        ws.append(r)
    for r in range(2, N + 2):
        ws.cell(row=r, column=4).number_format = "yyyy-mm-dd"
    wb.save(path)
    return rows


def blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def text_of(v) -> str:
    return v if isinstance(v, str) else str(v)


@pytest.fixture(scope="session")
def office():
    o = Office()
    yield o
    o.close()


@pytest.fixture(scope="session")
def profiled(office, tmp_path_factory):
    d = tmp_path_factory.mktemp("hyg")
    rows = write_population(d / "in.xlsx")
    office.run(d / "in.xlsx", d / "profiled.xlsx", [("use", "HygieneProfile")])
    return {"dir": d, "rows": rows, "wb": load_workbook(d / "profiled.xlsx")}


def audit_rows(wb) -> dict[str, dict]:
    ws = wb["Column Audit"]
    heads = [c.value for c in ws[1]]
    out = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0]:
            out[r[0]] = dict(zip(heads, r))
    return out


def log_lines(wb) -> list[tuple]:
    ws = wb["Hygiene"]
    return [(r[0], r[1], r[2]) for r in ws.iter_rows(min_row=17, values_only=True) if r[0]]


def test_profile_writes_one_row_per_column_with_its_heads(profiled):
    ws = profiled["wb"]["Column Audit"]
    assert [c.value for c in ws[1]][:len(AUDIT_HEADS)] == AUDIT_HEADS
    assert list(audit_rows(profiled["wb"])) == HEADS


def test_profile_counts_blanks_and_distinct_values_as_python_does(profiled):
    got = audit_rows(profiled["wb"])
    for c, name in enumerate(HEADS):
        vals = [r[c] for r in profiled["rows"]]
        nonblank = [v for v in vals if not blank(v)]
        assert got[name]["Blank"] == sum(blank(v) for v in vals), name
        if name != "ORIG_DT":                       # dates are keyed by their text; checked apart below
            assert got[name]["Distinct"] == len({text_of(v) for v in nonblank}), name
        assert got[name]["Blank %"] == pytest.approx(sum(blank(v) for v in vals) / N), name


def test_profile_counts_text_problems_as_python_does(profiled):
    got = audit_rows(profiled["wb"])
    rows = profiled["rows"]
    col = {n: [r[i] for r in rows] for i, n in enumerate(HEADS)}

    def is_num_text(v):
        if not isinstance(v, str) or v.strip() == "":
            return False
        try:
            float(v.strip())
            return True
        except ValueError:
            return False
    assert got["AMT_TXT"]["Numbers as text"] == sum(is_num_text(v) for v in col["AMT_TXT"]) > 0
    assert got["ORIG_DT"]["Dates as text"] == sum(isinstance(v, str) for v in col["ORIG_DT"]) > 0
    # extra spaces: leading or trailing on a value, or a value that is only spaces
    spaced = lambda vs: sum(isinstance(v, str) and v != v.strip(" ") for v in vs)          # noqa: E731
    assert got["STATE"]["Extra spaces"] == spaced(col["STATE"]) > 0
    assert got["NOTE"]["Extra spaces"] == spaced(col["NOTE"]) > 0
    assert got["STATE"]["Odd characters"] == 1                                       # the no-break space
    assert got["NOTE"]["Odd characters"] == 0


def test_profile_tells_case_apart_and_lists_the_most_common(profiled):
    got = audit_rows(profiled["wb"])
    flags = [r[5] for r in profiled["rows"] if not blank(r[5])]
    assert got["FLAG_YN"]["Distinct"] == 4                                           # Y, N, y, n
    counts = sorted(((flags.count(v), v) for v in set(flags)), reverse=True)
    top = got["FLAG_YN"]["Most common"]
    assert top.startswith(f"{counts[0][1]} ({counts[0][0]})"), top
    assert top.count("(") == 3


def test_profile_finds_constant_empty_and_copied_columns(profiled):
    got = audit_rows(profiled["wb"])
    assert got["CONST"]["Same value in every row"] == "Yes"
    assert got["EMPTY"]["Same value in every row"] == "All blank"
    assert got["EMPTY"]["Type found"] == "Empty"
    assert got["FICO_COPY"]["Same as column"] == "FICO"
    assert all(got[n]["Same as column"] in (None, "") for n in HEADS if n != "FICO_COPY")
    assert got["FICO"]["Same value in every row"] in (None, "")


def test_profile_types(profiled):
    got = audit_rows(profiled["wb"])
    assert got["LOAN_ID"]["Type found"] == "Number"
    assert got["STATE"]["Type found"] == "Text"
    n_text = sum(isinstance(r[4], str) for r in profiled["rows"])
    assert got["AMT_TXT"]["Type found"] == f"Mixed: {N - n_text} number, {n_text} text"


def test_profile_leaves_the_source_alone_and_logs_what_it_did(profiled):
    ws = profiled["wb"]["use"]
    assert [c.value for c in ws[1]] == HEADS
    assert ws.max_row == N + 1
    assert ws.cell(row=2, column=1).value == profiled["rows"][0][0]
    log = log_lines(profiled["wb"])
    assert log[-1][1] == "Profile" and log[-1][2].startswith(f"Sheet use: {len(HEADS)} columns, {N} rows")
    assert profiled["wb"]["Hygiene"]["B3"].value == "use"


def decide(path, decisions: dict[str, tuple], key: str | None = "LOAN_ID") -> None:
    """Types decisions on Column Audit, as the analyst would: name -> (Keep?, New name, Flag)."""
    wb = load_workbook(path)
    ws = wb["Column Audit"]
    for r in range(2, ws.max_row + 1):
        name = ws.cell(row=r, column=1).value
        if name in decisions:
            keep, new, flag = decisions[name]
            ws.cell(row=r, column=13).value = keep
            ws.cell(row=r, column=14).value = new
            ws.cell(row=r, column=15).value = flag
    if key is not None:
        wb["Hygiene"]["B4"].value = key
    wb.save(path)


ALL = {"LOAN_ID": ("Keep", None, None), "FICO": ("Keep", "Score", None), "STATE": ("Keep", None, None),
       "ORIG_DT": ("Keep", None, None), "AMT_TXT": ("Drop", None, None), "FLAG_YN": ("Keep", "Flag", "Y"),
       "CONST": ("Drop", None, None), "FICO_COPY": ("Drop", None, None), "EMPTY": ("Drop", None, None),
       "NOTE": ("keep", None, None)}


@pytest.fixture(scope="session")
def built(office, profiled):
    d = profiled["dir"]
    p = d / "decided.xlsx"
    load_workbook(d / "profiled.xlsx").save(p)
    decide(p, ALL)
    office.run(p, d / "built.xlsx", [("use", "HygieneBuild")])
    return {"dir": d, "rows": profiled["rows"], "wb": load_workbook(d / "built.xlsx"), "path": d / "built.xlsx"}


def test_profile_again_keeps_the_decisions_typed(office, built):
    d = built["dir"]
    office.run(built["path"], d / "reprofiled.xlsx", [("use", "HygieneProfile")])
    got = audit_rows(load_workbook(d / "reprofiled.xlsx"))
    for name, (keep, new, flag) in ALL.items():
        assert (got[name]["Keep?"], got[name]["New name"], got[name]["Flag: 1 when"]) == (keep, new, flag), name


def test_build_writes_the_kept_columns_as_values_renamed_with_the_flag_made(built):
    ws = built["wb"]["Final Population"]
    heads = [c.value for c in ws[1]]
    assert heads == ["LOAN_ID", "Score", "STATE", "ORIG_DT", "Flag", "NOTE"]
    assert ws.max_row == N + 1
    src = built["rows"]
    for i in range(N):
        row = [ws.cell(row=i + 2, column=c).value for c in range(1, 7)]
        assert row[0] == src[i][0]
        assert row[1] == src[i][1]
        f = src[i][5]
        assert row[4] == (None if blank(f) else (1 if f.strip().upper() == "Y" else 0)), (i, f, row[4])
    # values, not formulas
    assert not any(isinstance(c.value, str) and c.value.startswith("=") for r in ws.iter_rows() for c in r)


def test_build_row_audit_lists_rows_with_blanks_and_repeated_keys(built):
    ws = built["wb"]["Row Audit"]
    src = built["rows"]
    kept = [0, 1, 2, 3, 5, 9]
    want_blank_rows = [i + 2 for i, r in enumerate(src) if any(blank(r[c]) for c in kept)]
    got_blank_rows = [r[0] for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    assert got_blank_rows == want_blank_rows
    dups = {r[5]: (r[6], r[7]) for r in ws.iter_rows(min_row=2, values_only=True) if r[5] is not None}
    ids = [r[0] for r in src]
    want = {str(v): ids.count(v) for v in set(ids) if ids.count(v) > 1}
    assert {str(k): v[1] for k, v in dups.items()} == want
    assert len(want) == 2


def test_build_stamps_what_it_did_and_says_current(built):
    ctl = built["wb"]["Hygiene"]
    src = built["rows"]
    assert load_workbook(built["path"], data_only=True)["Hygiene"]["B8"].value == "Current"
    assert ctl["B9"].value == N
    assert (ctl["B10"].value, ctl["B11"].value, ctl["B12"].value) == (6, 4, 1)
    kept = [0, 1, 2, 3, 5, 9]
    assert ctl["B13"].value == sum(any(blank(r[c]) for c in kept) for r in src)
    assert ctl["B14"].value == 2
    assert "from 'use'" in ctl["B7"].value
    log = log_lines(built["wb"])
    assert log[-1][1] == "Build" and log[-1][2].startswith(f"{N} rows; 6 columns kept, 4 dropped; 1 flags")
    assert "Flag: " in log[-1][2] and " ones, " in log[-1][2]


def test_a_changed_decision_makes_the_build_out_of_date(office, built):
    d = built["dir"]
    p = d / "changed.xlsx"
    load_workbook(built["path"]).save(p)
    decide(p, {"NOTE": ("Drop", None, None)}, key=None)
    office.run(p, d / "changed_out.xlsx", [])
    assert load_workbook(d / "changed_out.xlsx", data_only=True)["Hygiene"]["B8"].value.startswith("Out of date")


def test_build_refuses_while_a_column_has_no_decision_and_names_it(office, profiled):
    d = profiled["dir"]
    p = d / "half.xlsx"
    load_workbook(d / "profiled.xlsx").save(p)
    decide(p, {k: v for k, v in ALL.items() if k not in ("EMPTY", "NOTE")})
    office.run(p, d / "half_out.xlsx", [("use", "HygieneBuild")])
    wb = load_workbook(d / "half_out.xlsx")
    assert "Final Population" not in wb.sheetnames
    log = log_lines(wb)
    refused = [x for x in log if x[1] == "Build refused"]
    assert refused and "2 to fix first" in refused[-1][2]
    assert "EMPTY: no decision in Keep?" in refused[-1][2] and "NOTE: no decision in Keep?" in refused[-1][2]


def test_build_refuses_two_kept_columns_with_one_name(office, profiled):
    d = profiled["dir"]
    p = d / "clash.xlsx"
    load_workbook(d / "profiled.xlsx").save(p)
    decide(p, {**ALL, "STATE": ("Keep", "score", None)})
    office.run(p, d / "clash_out.xlsx", [("use", "HygieneBuild")])
    wb = load_workbook(d / "clash_out.xlsx")
    assert "Final Population" not in wb.sheetnames
    assert "score: two kept columns would share this name" in [x for x in log_lines(wb)
                                                              if x[1] == "Build refused"][-1][2]


def test_build_without_a_key_says_duplicates_were_not_checked(office, profiled):
    d = profiled["dir"]
    p = d / "nokey.xlsx"
    load_workbook(d / "profiled.xlsx").save(p)
    decide(p, ALL, key=None)
    office.run(p, d / "nokey_out.xlsx", [("use", "HygieneBuild")])
    wb = load_workbook(d / "nokey_out.xlsx")
    assert wb["Hygiene"]["B14"].value.startswith("Not checked")
    assert wb["Row Audit"]["F2"].value.startswith("Not checked")


def test_profile_refuses_on_its_own_sheets(office, profiled):
    d = profiled["dir"]
    office.run(d / "profiled.xlsx", d / "self.xlsx", [("Column Audit", "HygieneProfile")])
    log = log_lines(load_workbook(d / "self.xlsx"))
    assert log[-1][1] == "Profile said" and "Go to the sheet holding the population" in log[-1][2]
