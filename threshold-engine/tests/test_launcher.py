"""The window's rules, without the window: every field the bank must state
starts empty, Run refuses in words until each is stated, the form becomes
exactly the arguments workbook.build takes, and Run writes the workbook and
opens it. One test opens the real window where there is a display, and skips
with the reason where there is not."""
import re
import runpy
import subprocess
import time
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

from conftest import DATA, ROOT
from threshold_engine import keybank_style as K
from threshold_engine import launcher
from threshold_engine.launcher import Form

CARDS, MORTGAGE = DATA / "cards_nco_ttm.csv", DATA / "mortgage_nco_ttm.csv"


@pytest.fixture(autouse=True)
def opened(monkeypatch):
    """Opening the workbook would start Excel; here it only notes the path."""
    got = []
    monkeypatch.setattr(launcher, "open_file", lambda p: got.append(Path(p)))
    return got


def filled(tmp_path, **over) -> Form:
    """A form with every field stated, at the settings agreed for cards."""
    f = Form()
    launcher.add_files(f, [str(CARDS), str(MORTGAGE)])
    launcher.set_label(f, 0, "Credit card")
    launcher.set_label(f, 1, "Mortgage")
    vals = dict(name="NCO", unit="%", direction="higher_is_worse", smoothing="1", floor_at_zero="yes",
                moderate_halfwidth="0.5", low_step="1", high_z="2.5", on_the_line="worse",
                percentiles="50 75 90 95", horizon="4", min_history="41", half_lives="10",
                out=str(tmp_path / "t.xlsx"))
    vals.update(over)
    for k, v in vals.items():
        setattr(f, k, v)
    return f


# ---- nothing is filled in for the bank


def test_every_field_starts_empty():
    f = Form()
    assert f.series == []
    for k, v in vars(f).items():
        if k != "series":
            assert v == "", k


def test_an_empty_form_names_every_required_field_and_run_is_refused(monkeypatch):
    called = []
    out = launcher.run(Form(), build=lambda **kw: called.append(kw))
    assert not out.ok and called == []
    assert out.lines[0] == "Run is waiting for:"
    said = "\n".join(out.lines)
    for words in ("add at least one CSV", "name is empty", "unit is empty", "higher or lower",
                  "smoothing", "at or below zero", "half-width", "Moderate-Low step", "High's z",
                  "exactly on a line", "percentiles", "horizon", "minimum history", "where the workbook goes"):
        assert words in said, words
    assert "half-lives" not in said                     # the one optional field
    assert len(out.lines) - 1 == 14


def test_the_problems_come_in_step_order():
    steps = [p.split(":")[0] for p in launcher.problems(Form())]
    assert steps == sorted(steps, key=launcher.STEPS.index)


def test_each_field_left_out_is_named_and_refuses(tmp_path):
    for attr, words in (("name", "name is empty"), ("direction", "higher or lower"),
                        ("floor_at_zero", "at or below zero"), ("high_z", "High's z"),
                        ("on_the_line", "on a line"), ("min_history", "minimum history"), ("out", "goes")):
        f = filled(tmp_path, **{attr: ""})
        p = launcher.problems(f)
        assert len(p) == 1 and words in p[0], (attr, p)
        with pytest.raises(launcher.Refused):
            launcher.arguments(f)


def test_a_series_without_a_label_is_refused(tmp_path):
    f = filled(tmp_path)
    launcher.set_label(f, 1, "  ")
    assert launcher.problems(f) == ["Series: give mortgage_nco_ttm.csv a product label."]


# ---- what the form becomes


def test_a_complete_form_becomes_the_builds_arguments(tmp_path):
    f = filled(tmp_path)
    assert launcher.problems(f) == []
    assert launcher.arguments(f) == dict(
        out=tmp_path / "t.xlsx", series=[("Credit card", CARDS), ("Mortgage", MORTGAGE)], name="NCO", unit="%",
        direction="higher_is_worse", frequency="quarterly", smoothing=1, floor_at_zero=True,
        moderate_halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse", half_lives=(10.0,),
        percentiles=(50.0, 75.0, 90.0, 95.0), horizon=4, min_history=41)


def test_no_floor_and_no_half_lives_are_stated_values_not_gaps(tmp_path):
    a = launcher.arguments(filled(tmp_path, floor_at_zero="no", half_lives="", percentiles="50, 90"))
    assert a["floor_at_zero"] is False and a["half_lives"] == () and a["percentiles"] == (50.0, 90.0)


@pytest.mark.parametrize("over, words", [
    (dict(smoothing="1.5"), "whole number"),
    (dict(smoothing="0"), "1 or more"),
    (dict(moderate_halfwidth="-0.1"), "0 or more"),
    (dict(moderate_halfwidth="abc"), "must be a number"),
    (dict(low_step="0.5"), "larger than Moderate's half-width"),
    (dict(high_z="0"), "above 0"),
    (dict(percentiles="90 50"), "rise"),
    (dict(percentiles="50 100"), "between 0 and 100"),
    (dict(percentiles="fifty"), "numbers separated"),
    (dict(horizon="0"), "1 or more"),
    (dict(min_history="1"), "2 or more"),
    (dict(half_lives="-3"), "half-life"),
    (dict(direction="sideways"), "higher or lower"),
    (dict(out="x.csv"), ".xlsx"),
    (dict(percentiles="0 50"), "between 0 and 100"),
    (dict(percentiles="50 50 90"), "rise"),
    (dict(half_lives="0"), "half-life"),
])
def test_a_wrong_value_is_said_in_words(tmp_path, over, words):
    p = launcher.problems(filled(tmp_path, **over))
    assert len(p) == 1 and words in p[0], p


@pytest.mark.parametrize("attr, text", [
    ("high_z", "nan"), ("high_z", "inf"), ("high_z", "1e309"), ("moderate_halfwidth", "nan"),
    ("low_step", "inf"), ("half_lives", "inf"), ("half_lives", "10 nan"), ("percentiles", "50 nan 90"),
])
def test_nan_and_infinity_are_not_numbers(tmp_path, attr, text):
    """NaN passes every comparison, so before this it cleared every range
    check and Run wrote a blank into the bank's Settings tab."""
    f = filled(tmp_path, **{attr: text})
    p = launcher.problems(f)
    assert len(p) == 1 and p[0].startswith("Settings:") and repr(text) in p[0], p
    out = launcher.run(f, build=lambda **kw: pytest.fail("built with %s=%s" % (attr, text)))
    assert not out.ok


def test_an_upper_case_xlsx_name_is_an_xlsx_file(tmp_path):
    assert launcher.problems(filled(tmp_path, out=str(tmp_path / "T.XLSX"))) == []


def test_an_existing_folder_named_xlsx_is_not_a_file_name(tmp_path, opened):
    (tmp_path / "dir.xlsx").mkdir()
    f = filled(tmp_path, out=str(tmp_path / "dir.xlsx"))
    p = launcher.problems(f)
    assert len(p) == 1 and p[0].startswith("Build:") and "is a folder" in p[0], p
    out = launcher.run(f, build=lambda **kw: pytest.fail("built into a folder"))
    assert not out.ok and "open in Excel" not in "\n".join(out.lines)


def test_the_output_folder_must_exist(tmp_path):
    p = launcher.problems(filled(tmp_path, out=str(tmp_path / "nowhere" / "t.xlsx")))
    assert len(p) == 1 and "is not there" in p[0]


def test_two_series_with_one_label_are_refused(tmp_path):
    f = filled(tmp_path)
    launcher.set_label(f, 1, "Credit card")
    assert launcher.problems(f) == ["Series: two files share the label 'Credit card'; each product needs its own."]


def test_labels_differing_only_in_capitals_are_refused(tmp_path):
    """The workbook finds a product with Excel's MATCH, which ignores capitals;
    'credit card' picked on Assess showed Credit card's bands and line."""
    f = filled(tmp_path)
    launcher.set_label(f, 1, "credit card")
    assert launcher.problems(f) == ["Series: the labels 'Credit card' and 'credit card' are one label to "
                                    "Excel, which ignores capitals; each product needs its own."]


def test_labels_are_compared_and_handed_on_without_their_spaces(tmp_path):
    f = filled(tmp_path)
    launcher.set_label(f, 0, "  Credit card ")
    assert launcher.arguments(f)["series"] == [("Credit card", CARDS), ("Mortgage", MORTGAGE)]
    launcher.set_label(f, 1, "Credit card  ")
    assert launcher.problems(f) == ["Series: two files share the label 'Credit card'; each product needs its own."]


@pytest.mark.parametrize("label", ["=Mortgage", 'Card "A"', "Cards, US"])
def test_a_label_the_workbook_cannot_hold_is_refused(tmp_path, label):
    """'=' made the label a formula and a double quote broke the Assess
    dropdown, so Excel would not open the file; a comma split the dropdown's
    entry in two, neither matching a product."""
    f = filled(tmp_path)
    launcher.set_label(f, 1, label)
    assert launcher.problems(f) == ["Series: the label %r can't be used: a label may not begin with '=' or "
                                    "hold a comma or a double quote." % label]


def test_a_label_may_hold_other_punctuation(tmp_path, opened):
    f = filled(tmp_path)
    launcher.set_label(f, 1, "Mortgage (1st lien) - US & PR")
    assert launcher.problems(f) == []
    out = launcher.run(f)
    assert out.ok, out.lines
    assert load_workbook(out.path)["Settings"].cell(7, 1).value == "Mortgage (1st lien) - US & PR"


def test_a_csv_without_the_date_value_header_is_refused_before_run(tmp_path):
    bad = tmp_path / "noheader.csv"
    bad.write_text("2020-01-01,1\n2020-04-01,2\n", encoding="utf-8")
    f = filled(tmp_path)
    f.series.append(("Other", str(bad)))
    assert launcher.problems(f) == ["Series: noheader.csv must begin with the header line date,value."]
    out = launcher.run(f, build=lambda **kw: pytest.fail("built without a header"))
    assert out.lines == ["Run is waiting for:", "Series: noheader.csv must begin with the header line date,value."]


def test_a_row_missing_its_value_is_words_from_run_not_a_traceback(tmp_path):
    short = tmp_path / "short.csv"
    short.write_text("date,value\n2020-01-01\n", encoding="utf-8")
    f = filled(tmp_path)
    f.series.append(("Other", str(short)))
    assert launcher.problems(f) == []
    out = launcher.run(f, open_after=False)                          # the real build
    assert not out.ok and len(out.lines) == 1
    assert out.lines[0].startswith("The build couldn't read a series (TypeError") and "every row" in out.lines[0]


def test_a_missing_column_raised_inside_the_build_is_words(tmp_path):
    def keyerror(**kw):
        raise KeyError("date")
    out = launcher.run(filled(tmp_path), build=keyerror)
    assert not out.ok and out.lines[0].startswith("The build couldn't read a series (KeyError")


def test_a_file_gone_since_it_was_added_is_refused(tmp_path):
    f = filled(tmp_path)
    f.series.append(("Gone", str(tmp_path / "gone.csv")))
    assert launcher.problems(f) == ["Series: %s is not there any more." % (tmp_path / "gone.csv")]


def test_adding_the_same_file_twice_lists_it_once_and_says_so():
    f = Form()
    assert launcher.add_files(f, [str(CARDS)]) == []
    assert launcher.add_files(f, [str(CARDS), str(MORTGAGE)]) == ["cards_nco_ttm.csv is already listed."]
    assert [p for _, p in f.series] == [str(CARDS), str(MORTGAGE)]
    assert [lbl for lbl, _ in f.series] == ["", ""]        # labels are the bank's to give
    launcher.remove(f, 0)
    assert [p for _, p in f.series] == [str(MORTGAGE)]


# ---- the rail


def test_peers_points_to_the_command_line_that_builds_it_today():
    """The peer commands exist in cli.py; the window no longer says the peer
    workbook is still being built."""
    words = launcher.COMING["Peers"]
    assert "peers pull" in words and "peers build" in words
    assert "being built" not in launcher.__doc__ and "peers pull" in launcher.__doc__


def test_the_rail_counts_what_each_step_still_wants_and_peers_is_coming(tmp_path):
    s = launcher.steps(Form())
    assert [x.name for x in s] == ["Series", "Measure", "Settings", "Build", "Peers"]
    assert [x.mark for x in s] == ["todo"] * 4 + ["coming"]
    assert [x.sub for x in s] == ["1 to fill in", "5 to fill in", "7 to fill in", "1 to fill in", "Coming next"]
    s = launcher.steps(filled(tmp_path))
    assert [x.mark for x in s] == ["done"] * 4 + ["coming"]


# ---- Run


def test_run_writes_the_workbook_with_workbook_build_and_opens_it(tmp_path, opened):
    out = launcher.run(filled(tmp_path))
    assert out.ok, out.lines
    assert out.path == tmp_path / "t.xlsx" and out.path.is_file()
    assert re.fullmatch(r"Wrote %s: Credit card, Mortgage, \d+ quarters\." % re.escape(str(out.path)),
                        out.lines[0]) and len(out.lines) == 1
    assert opened == [out.path]
    wb = load_workbook(out.path)
    assert wb.sheetnames[:2] == ["Thresholds", "Settings"]
    st = wb["Settings"]
    assert [st.cell(6, 1).value, st.cell(7, 1).value] == ["Credit card", "Mortgage"]
    assert [st.cell(6, c).value for c in (8, 9, 10, 11)] == [0.5, 1.0, 2.5, "worse"]


def test_run_hands_the_build_exactly_the_forms_arguments(tmp_path, opened):
    got = []

    def fake(**kw):
        got.append(kw)
        return {"path": kw["out"], "products": [s for s, _ in kw["series"]], "quarters": 9}
    f = filled(tmp_path)
    out = launcher.run(f, build=fake, open_after=False)
    assert out.ok and out.lines == ["Wrote %s: Credit card, Mortgage, 9 quarters." % (tmp_path / "t.xlsx")]
    assert got == [launcher.arguments(f)] and opened == []


def test_a_refusal_from_the_build_is_words(tmp_path):
    def refuses(**kw):
        raise ValueError("Mortgage has two observations in one quarter")
    out = launcher.run(filled(tmp_path), build=refuses)
    assert not out.ok and out.lines == ["The build refused: Mortgage has two observations in one quarter"]


def test_a_workbook_open_in_excel_is_said_so(tmp_path):
    def locked(**kw):
        raise PermissionError(13, "Permission denied")
    out = launcher.run(filled(tmp_path), build=locked)
    assert not out.ok and "open in Excel" in out.lines[0]


def test_too_little_history_for_the_backtest_comes_back_from_the_real_build(tmp_path):
    out = launcher.run(filled(tmp_path, min_history="400"))
    assert not out.ok and out.lines[0].startswith("The build refused:") and "min_history" in out.lines[0]


def test_a_workbook_that_cannot_be_opened_from_here_says_where_it_is(tmp_path, monkeypatch):
    def no_program(p):
        raise OSError(2, "No application is associated")
    monkeypatch.setattr(launcher, "open_file", no_program)
    said = launcher.open_workbook(tmp_path / "t.xlsx")
    assert "Couldn't open t.xlsx" in said and str(tmp_path) in said


# ---- add-ons, colours, the double-click file


def test_a_missing_add_on_keeps_run_off_and_says_how_to_get_it(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "missing_addons", lambda: ["openpyxl"])
    out = launcher.run(filled(tmp_path), build=lambda **kw: pytest.fail("built without openpyxl"))
    assert not out.ok and "lacks openpyxl" in out.lines[0] and "pip install openpyxl" in out.lines[0]
    monkeypatch.undo()
    assert launcher.missing_addons() == [] and launcher.addon_words([]) == ""


def test_the_launcher_loads_on_a_machine_without_openpyxl():
    """openpyxl blocked in a fresh Python: the launcher still imports and
    says what is missing, so the window can open and explain."""
    code = ("import sys; sys.modules['openpyxl'] = None; sys.path.insert(0, %r)\n"
            "import importlib.util as u; u.find_spec = lambda n, *a: None if n == 'openpyxl' else 1\n"
            "from threshold_engine import launcher\n"
            "print(launcher.missing_addons())" % str(ROOT / "src"))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "['openpyxl']"


def test_the_windows_colours_are_the_house_tokens():
    for name in ("INK", "KEY_RED", "CRIMSON", "PAPER", "CANVAS", "MIST", "STONE", "SLATE"):
        assert getattr(launcher, name) == "#" + getattr(K, name), name


def test_thresholds_pyw_starts_the_window(monkeypatch):
    started = []
    monkeypatch.setattr(launcher, "main", lambda: started.append(True))
    runpy.run_path(str(ROOT / "Thresholds.pyw"), run_name="__main__")
    assert started == [True]
    runpy.run_path(str(ROOT / "Thresholds.pyw"), run_name="imported")
    assert started == [True]                                 # only when it is the program itself


# ---- the window itself, where there is a display


def test_the_window_opens_follows_the_form_and_closes(tmp_path, opened, monkeypatch):
    tk = pytest.importorskip("tkinter", reason="tkinter is not installed with this Python")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip("no display to open a window on: %s" % exc)
    try:
        w = launcher.window(root)
        root.update()
        assert w["page"] == "Series"
        assert str(w["step_Peers"].cget("fg")).upper() == launcher.STONE    # greyed: coming next
        w["show"]("Peers")
        assert w["page"] == "Series"                                         # and it does not open
        w["show"]("Build")
        root.update()
        assert str(w["run"].cget("state")) == "disabled"
        f = filled(tmp_path)
        w["form"].series[:] = f.series
        w["show"]("Measure")
        for k in ("name", "unit", "smoothing"):
            w["var_" + k].set(getattr(f, k))
        w["var_direction"].set("higher_is_worse")
        w["var_floor_at_zero"].set("yes")
        w["show"]("Settings")
        for k in ("moderate_halfwidth", "low_step", "high_z", "percentiles", "horizon", "min_history"):
            w["var_" + k].set(getattr(f, k))
        w["var_on_the_line"].set("worse")
        w["show"]("Build")
        assert str(w["run"].cget("state")) == "disabled"                     # the output path is still wanted
        w["var_out"].set(f.out)
        root.update()
        assert str(w["run"].cget("state")) == "normal"
        assert launcher.arguments(w["form"])["out"] == tmp_path / "t.xlsx"
        runs = []
        real_run = launcher.run
        monkeypatch.setattr(launcher, "run", lambda form: (runs.append(1), real_run(form))[1])
        w["run"].invoke()
        assert w["busy"] and str(w["run"].cget("state")) == "disabled"      # no second press while it builds
        w["press_run"]()                                                     # nor one that slips past the button
        for _ in range(600):
            root.update()
            if not w["busy"]:
                break
            time.sleep(0.05)
        assert w["outcome"].ok, w["outcome"].lines
        assert runs == [1]
        assert (tmp_path / "t.xlsx").is_file() and opened == [tmp_path / "t.xlsx"]
        assert w["result"].cget("text").startswith("Wrote ")
    finally:
        root.destroy()
