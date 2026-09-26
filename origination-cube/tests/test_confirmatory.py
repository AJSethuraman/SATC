"""A run held to a pre-spec (NEXT-GOAL 3.15): the file is named on Control,
read and refused by that cell, echoed on Check with the git commit it came
from, compared with what the run used line by line, and every run that touched
the holdout is marked in the Log and counted on Check. The holdout's loans are
counted here by hand from the extract."""

import csv
import shutil
import subprocess
from datetime import date

import pytest
import yaml
from openpyxl import load_workbook

from conftest import cube, table
from origination_cube import book, confirmatory, control, engine, prespec, synth
from test_book import _answer
from test_book_dates import _check, _columns, _control

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed on this machine")

SPEC = {"prespec": 1, "written": "2026-09-26", "column": "INCOME_TO_SALES", "bins": [0.1, 0.25, 0.5, 1.0, 2.0],
        "reference": "0.25 - 0.49", "strata": ["FICO", "CHANNEL"], "window_months": 18, "confidence": 0.95,
        "holdout": {"from": "2024-01-01", "to": "2024-12-31"},
        "development": {"from": "2022-01-01", "to": "2023-12-31"}}


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                           "-c", "commit.gpgsign=false", *args], cwd=repo, check=True, capture_output=True,
                          text=True).stdout.strip()


def _spec(folder, commit=True, **changes):
    """The pre-spec, beside the workbook, committed in a repository of its own."""
    f = folder / "prespec.yaml"
    f.write_text(yaml.safe_dump({**SPEC, **changes}, sort_keys=False), encoding="utf-8")
    if commit:
        if not (folder / ".git").exists():
            git(folder, "init", "-q")
        git(folder, "add", f.name)
        git(folder, "commit", "-q", "-m", "pre-spec")
    return f


def _held(b, path):
    wb = load_workbook(b)
    ws = wb[control.SHEET]
    row = control.row_of(ws, control.PRESPEC_KEY)
    ws.cell(row=row, column=control.CHOOSE_COL).value = path
    wb.save(b)
    return f"Control!C{row}"


def _ready(tmp_path, monkeypatch, n=3000):
    """The dated book, INCOME / SALES made on Control and splitting the pockets, cut only by FICO and
    CHANNEL, with the pre-spec's window: every setting the pre-spec says except the ones it can't."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    x = synth.write_extract(tmp_path / "x", n=n, dated=True)
    b = book.set_up(x).book
    _answer(b)
    _control(b, window_months="18 months of being made", as_of="The latest date in the extract (suggested)",
             **{"derived|1": ("INCOME_TO_SALES", "INCOME", "SALES")})
    book.set_up(x)
    _columns(b, "INCOME_TO_SALES", C_SPLIT="Yes", C_EDGES="0.1; 0.25; 0.5; 1; 2")
    for c in ("ORIG_BAL", "REV_DEBT", "ASSET_CLASS", "INCOME", "SALES"):
        _columns(b, c, C_CUT="No")
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)
    return x, b


def _log(b) -> list[str]:
    ws = load_workbook(b)["Log"]
    return [ws.cell(row=r, column=2).value for r in range(book.LOG_FIRST, ws.max_row + 1)
            if ws.cell(row=r, column=2).value]


def _warnings(chk) -> list[str]:
    w = chk.get("Warning", [])
    return w if isinstance(w, list) else [w]


@needs_git
def test_a_run_held_to_a_committed_pre_spec_echoes_it_says_where_it_differs_and_counts_the_holdout(
        tmp_path, monkeypatch):
    x, b = _ready(tmp_path, monkeypatch)
    f = _spec(x.parent)
    head = git(x.parent, "rev-parse", "HEAD")
    _held(b, "prespec.yaml")                                    # its name alone: it sits beside the workbook
    ran = book.run(b)
    assert ran.ok, ran.lines
    chk = _check(b)
    assert chk["Pre-spec"] == str(f.resolve())
    assert chk["Pre-spec commit"].startswith(f"{head[:12]}, committed ")
    says = chk["What the pre-spec says"].splitlines()
    assert "column: INCOME_TO_SALES" in says and "holdout: 2024-01-01 to 2024-12-31" in says
    assert "reference: 0.25 - 0.49" in says and "strata: FICO, CHANNEL" in says and "window_months: 18" in says

    # what the run could follow, it did: the column, its bins (typed on Columns), the strata, the window and
    # the confidence. What it couldn't: its reference is each pocket's low half, and its loans run from
    # 2021, not only the holdout's
    with open(x, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    latest = max(max(r["ORIG_DATE"] for r in rows), max(r["BAD_DATE"] for r in rows))
    kept = sorted(r["ORIG_DATE"] for r in rows if _months(r["ORIG_DATE"], latest) >= 18)
    devs = [w for w in _warnings(chk) if w.startswith(confirmatory.DEVIATES)]
    assert devs == [
        'Deviates from pre-spec: The reference group is "the low half of each pocket", which is not one of its '
        'bins\' groups in this run; the pre-spec says "0.25 - 0.49".',
        f"Deviates from pre-spec: The holdout is {kept[0]} to {kept[-1]} in this run; the pre-spec says "
        f"2024-01-01 to 2024-12-31."]

    # the holdout, counted by hand: every loan in the extract made in 2024, both ends included
    held = sorted(r["ORIG_DATE"] for r in rows if "2024-01-01" <= r["ORIG_DATE"] <= "2024-12-31")
    assert held
    assert chk["Holdout"] == (f"{len(held):,} of this extract's loans were made in the holdout (2024-01-01 to "
                              f"2024-12-31), the first on {held[0]} and the last on {held[-1]}. This run touched "
                              f"the holdout.")
    assert chk["Runs that touched the holdout"] == "1 in this workbook's Log, this one included"
    log = _log(b)
    assert log[1] == f"Deviates from pre-spec prespec.yaml (commit {head[:12]}): 2 places, listed on Check."
    assert log[2] == f"Touched the holdout: {len(held):,} loans made {held[0]} to {held[-1]}."
    assert log[1] in ran.lines and "Runs that touched the holdout, in this workbook's Log: 1." in ran.lines
    ran_yaml = b.with_name(f"{b.stem} - what ran.yaml").read_text(encoding="utf-8")
    assert f"# pre-spec: {f.resolve()} ({head[:12]}, committed " in ran_yaml
    assert f"# Touched the holdout: {len(held):,} loans made" in ran_yaml

    # Control strays from the pre-spec in one more place: said, and counted; the holdout count goes up
    _control(b, confidence="90%")
    assert book.run(b).ok
    chk = _check(b)
    devs = [w for w in _warnings(chk) if w.startswith(confirmatory.DEVIATES)]
    assert "Deviates from pre-spec: Confidence is 90% in this run; the pre-spec says 95%." in devs and len(devs) == 3
    assert chk["Runs that touched the holdout"] == "2 in this workbook's Log, this one included"
    assert _log(b)[1] == f"Deviates from pre-spec prespec.yaml (commit {head[:12]}): 3 places, listed on Check."

    # the pre-spec edited after its commit: said on Check and in the Log, and the run doesn't count
    f.write_text(f.read_text(encoding="utf-8") + "# an afterthought\n", encoding="utf-8")
    assert book.run(b).ok
    chk = _check(b)
    assert chk["Pre-spec commit"].endswith("; edited since that commit, so the file read here isn't the one "
                                           "committed")
    assert ("This run doesn't count as the pre-specified one until the pre-spec is committed, unchanged."
            in _warnings(chk))
    assert _log(b)[1].startswith(f"Deviates from pre-spec prespec.yaml (commit {head[:12]}, edited since)")
    assert chk["Runs that touched the holdout"] == "3 in this workbook's Log, this one included"


def _months(start: str, end: str) -> int:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day)


@needs_git
def test_a_pre_spec_the_run_cannot_use_is_refused_by_its_cell(tmp_path, monkeypatch):
    x, b = _ready(tmp_path, monkeypatch, n=1500)
    cell = _held(b, str(tmp_path / "nowhere.yaml"))
    ran = book.run(b)
    assert not ran.ok
    assert any(f"{cell}: there's no pre-spec file at {tmp_path / 'nowhere.yaml'}. Fix the path, or clear the cell"
               in line for line in ran.lines), ran.lines
    _spec(x.parent, bins=[0.5, 0.1], confidence=95)
    _held(b, f'"{x.parent / "prespec.yaml"}"')                # pasted with the quotes Windows adds
    ran = book.run(b)
    assert not ran.ok
    said = [line for line in ran.lines if cell in line]
    assert any('in the pre-spec prespec.yaml, "bins:" must rise' in s for s in said), said
    assert any('in the pre-spec prespec.yaml, "confidence:" must be a share between 0.5 and 1' in s for s in said)
    assert all("`" not in s for s in said)
    assert "Couldn't run" in _log(b)[0] and any(cell in line for line in _log(b))
    # Set up again keeps the path
    book.set_up(x)
    ws = load_workbook(b)[control.SHEET]
    assert control.read_prespec(ws) == (str(x.parent / "prespec.yaml"), cell)
    # and a blank cell is a run with no pre-spec
    _held(b, None)
    assert book.run(b).ok
    chk = _check(b)
    assert "Pre-spec" not in chk and "Holdout" not in chk
    assert not any(line.startswith(("Deviates", "Follows", confirmatory.HOLDOUT_MARK)) for line in _log(b))


@needs_git
def test_without_an_origination_date_the_holdout_is_said_unchecked(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    x = synth.write_extract(tmp_path / "x", n=1500)
    b = book.set_up(x).book
    _answer(b)
    f = _spec(x.parent, commit=False)
    _held(b, str(f))
    ran = book.run(b)
    assert ran.ok, ran.lines
    chk = _check(b)
    assert chk["Pre-spec commit"] == "not in a git repository, so not committed: a pre-spec only counts once it " \
                                     "is committed"
    assert chk["Holdout"] == ("Couldn't be checked: no column is marked Origination date on Columns. The holdout "
                              "is 2024-01-01 to 2024-12-31.")
    assert chk["Runs that touched the holdout"] == "0 in this workbook's Log before this one, which couldn't be checked"
    devs = [w for w in _warnings(chk) if w.startswith(confirmatory.DEVIATES)]
    assert devs[0] == 'Deviates from pre-spec: The column tested is not set in this run; the pre-spec says ' \
                      '"INCOME_TO_SALES".'
    assert "Deviates from pre-spec: The outcome window is not set in this run; the pre-spec says 18 months." in devs
    log = _log(b)
    assert log[1].startswith("Deviates from pre-spec prespec.yaml (not committed): ")
    assert log[2] == "Holdout not checked: no column is marked Origination date on Columns."


# --------------------------------------------------------------------------
# What the run used, worked out from the engine's result


def _dated_rows(dates):
    return [{"ID": f"L{i}", "SCORE": 600 + 50 * (i % 3), "CHAN": "AB"[i % 2], "BAL": 100, "BAD": i % 2,
             "GCO": 50 * (i % 2), "RANR": 3, "R": 0.1 * (i % 20), "ORIG": d} for i, d in enumerate(dates)]


def test_a_run_whose_loans_all_sit_in_the_holdout_used_the_holdout():
    ps = prespec.parse({**SPEC, "column": "R"})
    inside = ["2024-01-01", "2024-06-30", "2024-12-31"] * 4
    res = engine.run(cube(origination_date="ORIG"), table(_dated_rows(inside)))
    assert confirmatory.run_range(res, ps) is ps.holdout
    res = engine.run(cube(origination_date="ORIG"), table(_dated_rows(inside + ["2025-01-01"])))
    assert confirmatory.run_range(res, ps) == prespec.DateRange(date(2024, 1, 1), date(2025, 1, 1))
    assert confirmatory.run_range(engine.run(cube(), table(_dated_rows(inside))), ps) is None


def test_a_band_column_tested_is_left_out_of_the_strata_and_its_edges_are_the_bins():
    ps = prespec.parse({**SPEC, "column": "R", "strata": ["CHAN"]})
    bands = [{"name": "r", "field": "R", "edges": [0.1, 0.25, 0.5, 1.0, 2.0]},
             {"name": "score", "field": "SCORE", "edges": [650]}]
    res = engine.run(cube(bands=bands, origination_date="ORIG"),
                     table(_dated_rows(["2024-03-01"] * 30)))
    used = confirmatory.in_use(res, ps)
    assert used["column"] == "R" and used["bins"] == [0.1, 0.25, 0.5, 1.0, 2.0]
    assert used["strata"] == ["SCORE", "CHAN"] and used["reference"] == "the rest of the book"
    assert used["window_months"] is None and used["confidence"] == 0.95 and used["holdout"] is ps.holdout
    assert prespec.deviations(ps, used, where="in this run") == [
        "The reference group is `the rest of the book`, which is not one of its bins' groups in this run; the "
        "pre-spec says `0.25 - 0.49`.",
        "Pockets are cut by SCORE, CHAN in this run; the pre-spec says CHAN.",
        "The outcome window is not set in this run; the pre-spec says 18 months."]
