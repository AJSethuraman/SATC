"""The window's rules, without the window: every field the bank must state
starts empty, Run refuses in words until each is stated, the form becomes
exactly the arguments workbook.build takes, and Run writes the workbook and
opens it. One test opens the real window where there is a display, and skips
with the reason where there is not."""
import json
import re
import runpy
import subprocess
import time
import sys
import urllib.parse
from pathlib import Path

import pytest
from openpyxl import load_workbook

from threshold_engine.workbook import SET_TOP

from conftest import DATA, ROOT
from threshold_engine import keybank_style as K
from threshold_engine import launcher
from threshold_engine.launcher import Form, PeerForm
from threshold_engine.peers import fdic
from threshold_engine.peers import run as peers_run

CARDS, MORTGAGE = DATA / "cards_nco_ttm.csv", DATA / "mortgage_nco_ttm.csv"
PEERS = DATA / "peers"
ROSTER = ROOT / "config" / "peers.json"
MERGERS = PEERS / "mergers_roster.json"
ABSORPTIONS = PEERS / "absorptions_none.json"


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


def peers_filled(tmp_path, **over) -> PeerForm:
    """A Peers form with every field stated: the earlier peer build's settings
    (tests/data/peers/expected_books.json "rules"), card only. The cache
    folder exists (empty), so Build's fields are complete."""
    (tmp_path / "cache").mkdir(exist_ok=True)
    f = PeerForm()
    vals = dict(cache=str(tmp_path / "cache"), roster=str(ROSTER), first="2006Q1", last="2026Q2",
                products=["Credit card"], delinquency="no", mergers_pull="no", mergers_since="", refresh="no",
                out=str(tmp_path / "peers.xlsx"), series_dir=str(tmp_path / "series"),
                mergers_file=str(MERGERS), absorptions_file=str(ABSORPTIONS), extra_acquisitions="6672=2022Q2", industry_combined="none",
                jump="0.25", acquisition_share="0.05", min_book="1000000", exempt_self="yes", pack="all", min_banks="5", rank_by="net",
                last_n="20", min_obs="12", base_quarter="2019Q4", index_min_book="500000",
                lagged_years="2019 2025", lag_years="2", normalisation_years="2019 2025", mix_base_year="2019")
    vals.update(over)
    for k, v in vals.items():
        setattr(f, k, v)
    return f


class FakeFDIC:
    """Stands in for the FDIC API (the shape test_peers_cli.py fakes): the
    financials rows of the REPDTE asked for, history rows, every URL kept.
    Nothing here touches the network."""

    def __init__(self, data, history=()):
        self.data, self.history, self.urls = data, list(history), []

    def __call__(self, url):
        self.urls.append(url)
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        offset, limit = int(q["offset"][0]), int(q["limit"][0])
        rows = self.history if url.startswith(fdic.HISTORY_URL) else self.data[q["filters"][0].split(":")[1]]
        return {"data": [{"data": r} for r in rows[offset:offset + limit]], "meta": {"total": len(rows)}}


@pytest.fixture(scope="module")
def roster_2006():
    return json.loads((PEERS / "roster_2006.json").read_text())


def lay_out_cache(folder, data):
    """A pull's cache, written straight from a fixture."""
    folder.mkdir(exist_ok=True)
    for q, rows in data.items():
        (folder / ("q%s.json" % q)).write_text(json.dumps(rows), encoding="utf-8")
    return folder


def no_network(url):
    raise AssertionError("a test tried to fetch %s" % url)


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
    assert load_workbook(out.path)["Assess"].cell(SET_TOP + 1, 14).value == "Mortgage (1st lien) - US & PR"


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
    # The shared reader now refuses the row in words, naming the file and row
    # (the Codex review, 13 Oct 2026); before, the window caught a TypeError.
    assert out.lines == ["The build refused: short.csv, row 2: a row needs both a date and a value "
                         "(it has: 2020-01-01)"]


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


def test_peers_is_no_longer_coming_next():
    """Round 2 (V1-ROUND2-SPEC.md, section C): the Peers step is usable, so
    the 'coming next' state and its pointer to the command line are gone."""
    assert not hasattr(launcher, "COMING")
    assert "not in the window yet" not in launcher.__doc__.lower()
    assert "peers/run.py" in launcher.__doc__


def test_the_rail_counts_what_each_step_still_wants_peers_included(tmp_path):
    s = launcher.steps(Form(), PeerForm())
    assert [x.name for x in s] == ["Series", "Measure", "Settings", "Build", "Peers"]
    assert [x.mark for x in s] == ["todo"] * 5
    assert [x.sub for x in s] == ["1 to fill in", "5 to fill in", "7 to fill in", "1 to fill in", "29 to fill in"]
    s = launcher.steps(filled(tmp_path), peers_filled(tmp_path))
    assert [x.mark for x in s] == ["done"] * 5 and s[4].sub == "Complete"
    s = launcher.steps(filled(tmp_path), peers_filled(tmp_path, jump=""))
    assert [x.mark for x in s] == ["done"] * 4 + ["todo"] and s[4].sub == "1 to fill in"


# ---- Run


def test_run_writes_the_workbook_with_workbook_build_and_opens_it(tmp_path, opened):
    out = launcher.run(filled(tmp_path))
    assert out.ok, out.lines
    assert out.path == tmp_path / "t.xlsx" and out.path.is_file()
    assert re.fullmatch(r"Wrote %s: Credit card, Mortgage, \d+ quarters\." % re.escape(str(out.path)),
                        out.lines[0]) and len(out.lines) == 1
    assert opened == [out.path]
    wb = load_workbook(out.path)
    assert wb.sheetnames[:2] == ["Assess", "Thresholds"]
    st = wb["Assess"]
    assert [st.cell(SET_TOP, 14).value, st.cell(SET_TOP + 1, 14).value] == ["Credit card", "Mortgage"]
    assert [st.cell(SET_TOP, c).value for c in (15, 16, 17, 18)] == [0.5, 1.0, 2.5, "worse"]


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


# ---- Peers: every field empty until stated


def test_every_peer_field_starts_empty():
    f = PeerForm()
    assert f.products == []
    for k, v in vars(f).items():
        if k != "products":
            assert v == "", k


def test_an_empty_peer_form_names_every_field_and_pull_and_build_are_refused():
    f = PeerForm()
    pull, build = launcher.peer_problems(f, "pull"), launcher.peer_problems(f, "build")
    assert len(pull) == 7 and len(build) == 27 and len(launcher.peer_problems(f, "both")) == 29
    said = "\n".join(build)
    for flag in ("--cache", "--roster", "--first", "--last", "--products", "--delinquency", "--series-dir",
                 "--mergers", "--absorptions", "--extra-acquisitions", "--industry-combined", "--jump",
                 "--acquisition-share", "--min-book",
                 "--exempt-self", "--pack", "--min-banks", "--rank-by", "--last-n", "--min-obs",
                 "--base-quarter", "--index-min-book", "--lagged-years", "--lag-years",
                 "--normalisation-years", "--mix-base-year"):
        assert flag in said, flag
    assert "peer workbook goes" in said
    assert all(p.startswith("Peers: ") for p in pull + build)
    for x in ("--cache", "--first", "--last", "--products", "--delinquency", "--mergers", "--refresh"):
        assert x in "\n".join(pull), x
    out = launcher.peer_pull(f, pull=lambda **kw: pytest.fail("pulled from an empty form"))
    assert not out.ok and out.lines == ["Pull is waiting for:"] + pull
    out = launcher.peer_build(f, build=lambda **kw: pytest.fail("built from an empty form"))
    assert not out.ok and out.lines == ["Build is waiting for:"] + build


def test_a_complete_peer_form_becomes_runs_arguments_exactly(tmp_path):
    f = peers_filled(tmp_path)
    assert launcher.peer_problems(f, "both") == []
    assert launcher.peer_arguments(f, "pull") == dict(
        cache=tmp_path / "cache", first="2006Q1", last="2026Q2", products=["Credit card"], delinquency=False,
        mergers_since=None, refresh=False)
    assert launcher.peer_arguments(f, "build") == dict(
        out=tmp_path / "peers.xlsx", cache=tmp_path / "cache", roster=ROSTER, series_dir=tmp_path / "series",
        first="2006Q1", last="2026Q2", products=["Credit card"], mergers=MERGERS, absorptions=ABSORPTIONS, acquisition_share=0.05,
        extra_acquisitions=["6672=2022Q2"], industry_combined=[], jump=0.25, min_book=1000000.0,
        exempt_self=True, pack="all", min_banks=5, rank_by="net", last_n=20, min_obs=12, base_quarter="2019Q4",
        index_min_book=500000.0, lagged_years=[2019, 2025], lag_years=2, normalisation_years=[2019, 2025],
        mix_base_year=2019, delinquency=False)


def test_the_arguments_are_exactly_what_run_takes_so_the_window_cannot_drift(tmp_path):
    """Every keyword run.pull and run.build take, say aside, and no other:
    the same two functions `peers pull` and `peers build` call."""
    import inspect
    f = peers_filled(tmp_path)
    for action, fn in (("pull", peers_run.pull), ("build", peers_run.build)):
        params = set(inspect.signature(fn).parameters) - {"say"}
        assert set(launcher.peer_arguments(f, action)) == params, action


def test_the_delinquency_choice_is_stated_never_assumed(tmp_path):
    for action in ("pull", "build"):
        p = launcher.peer_problems(peers_filled(tmp_path, delinquency=""), action)
        assert p == ["Peers: choose whether delinquency and nonaccrual are included (--delinquency)."], p
        p = launcher.peer_problems(peers_filled(tmp_path, delinquency="maybe"), action)
        assert len(p) == 1 and "--delinquency" in p[0]
        assert launcher.peer_arguments(peers_filled(tmp_path, delinquency="yes"), action)["delinquency"] is True
        assert launcher.peer_arguments(peers_filled(tmp_path, delinquency="no"), action)["delinquency"] is False


def test_each_yes_or_no_reaches_run_as_the_bank_stated_it(tmp_path):
    for attr in ("exempt_self",):
        for said, value in (("yes", True), ("no", False)):
            assert launcher.peer_arguments(peers_filled(tmp_path, **{attr: said}), "build")[attr] is value,                 (attr, said)
    for said, value in (("yes", True), ("no", False)):
        assert launcher.peer_arguments(peers_filled(tmp_path, refresh=said), "pull")["refresh"] is value


def test_the_merger_record_is_a_stated_choice_and_its_date_a_real_date(tmp_path):
    a = launcher.peer_arguments(peers_filled(tmp_path, mergers_pull="yes", mergers_since="2005-10-01"), "pull")
    assert a["mergers_since"] == "2005-10-01"
    for over, words in ((dict(mergers_pull=""), "whether Pull also fetches the merger record"),
                        (dict(mergers_pull="yes"), "(--mergers) is empty"),
                        (dict(mergers_pull="yes", mergers_since="2005/10/01"), "like 2005-10-01"),
                        (dict(mergers_pull="yes", mergers_since="2005-02-30"), "like 2005-10-01"),
                        (dict(mergers_pull="no", mergers_since="2005-10-01"), "choose Yes or clear the date"),
                        (dict(refresh=""), "--refresh")):
        p = launcher.peer_problems(peers_filled(tmp_path, **over), "pull")
        assert len(p) == 1 and words in p[0], (over, p)
        assert launcher.peer_problems(peers_filled(tmp_path, **over), "build") == []   # Pull's alone


def test_none_states_an_empty_list_and_blank_never_does(tmp_path):
    a = launcher.peer_arguments(peers_filled(tmp_path, extra_acquisitions="NONE", industry_combined="none"),
                                "build")
    assert a["extra_acquisitions"] == [] and a["industry_combined"] == []
    for attr in ("extra_acquisitions", "industry_combined"):
        p = launcher.peer_problems(peers_filled(tmp_path, **{attr: "  "}), "build")
        assert len(p) == 1 and "nothing is stated" in p[0] and "write none" in p[0], p
    a = launcher.peer_arguments(peers_filled(tmp_path, extra_acquisitions="6672=2022Q2, 628=2008Q4",
                                             industry_combined="Other consumer+Auto; Credit card + Mortgage"),
                                "build")
    assert a["extra_acquisitions"] == ["6672=2022Q2", "628=2008Q4"]
    assert a["industry_combined"] == ["Other consumer+Auto", "Credit card + Mortgage"]


@pytest.mark.parametrize("over, words", [
    (dict(first="2006-03"), "like 2006Q1"),
    (dict(last="2026Q5"), "like 2006Q1"),
    (dict(first="2027Q1"), "comes before the first"),
    (dict(products=[]), "tick at least one product"),
    (dict(products=["Boats"]), "must be distinct"),
    (dict(jump="-0.1"), "0 or more"),
    (dict(jump="nan"), "must be a number"),
    (dict(min_book="inf"), "must be a number"),
    (dict(min_banks="0"), "1 or more"),
    (dict(min_banks="2.5"), "whole number"),
    (dict(last_n="0"), "1 or more"),
    (dict(min_obs="x"), "whole number"),
    (dict(lag_years="-1"), "0 or more"),
    (dict(lagged_years="2019 twenty"), "whole years"),
    (dict(lagged_years="2019 ²"), "whole years"),          # isdigit() passes it; int() cannot read it
    (dict(normalisation_years="2019 ٢٠٢٥"), "whole years"),
    (dict(index_min_book="-1"), "0 or more"),
    (dict(normalisation_years="2019"), "exactly 2 years"),
    (dict(mix_base_year="2019.5"), "whole number"),
    (dict(base_quarter="2019-12-31"), "like 2006Q1"),
    (dict(extra_acquisitions="6672-2022Q2"), "CERT=YYYYQn"),
    (dict(industry_combined="Auto"), "two or more products"),
    (dict(industry_combined="Auto+Auto"), "two or more products"),
    (dict(industry_combined="Auto+Boats"), "two or more products"),
    (dict(pack="some"), "the pack"),
    (dict(rank_by="both"), "ranked by"),
    (dict(exempt_self="true"), "--exempt-self"),
    (dict(out="peers.csv"), ".xlsx"),
])
def test_a_wrong_peer_value_is_said_in_words_and_build_refused(tmp_path, over, words):
    f = peers_filled(tmp_path, **over)
    p = launcher.peer_problems(f, "build")
    assert len(p) == 1 and words in p[0] and p[0].startswith("Peers: "), p
    out = launcher.peer_build(f, build=lambda **kw: pytest.fail("built with %r" % over))
    assert not out.ok and out.lines == ["Build is waiting for:"] + p


def test_the_paths_are_checked_for_what_each_press_does_with_them(tmp_path):
    """Pull may create the cache folder; Build reads only what is in it."""
    f = peers_filled(tmp_path, cache=str(tmp_path / "new-cache"))
    assert launcher.peer_problems(f, "pull") == []
    p = launcher.peer_problems(f, "build")
    assert len(p) == 1 and "is not there; Pull fills it first" in p[0]
    (tmp_path / "a-file").write_text("x")
    f = peers_filled(tmp_path, cache=str(tmp_path / "a-file"))
    assert "is a file, not a folder" in launcher.peer_problems(f, "pull")[0]
    for attr in ("roster", "mergers_file"):
        p = launcher.peer_problems(peers_filled(tmp_path, **{attr: str(tmp_path / "gone.json")}), "build")
        assert len(p) == 1 and "gone.json, is not there" in p[0], p
    p = launcher.peer_problems(peers_filled(tmp_path, series_dir=str(tmp_path / "a-file")), "build")
    assert len(p) == 1 and "--series-dir" in p[0] and "not a folder" in p[0]
    p = launcher.peer_problems(peers_filled(tmp_path, out=str(tmp_path / "nowhere" / "p.xlsx")), "build")
    assert len(p) == 1 and "is not there" in p[0]


def test_ticking_keeps_the_builds_product_order_and_refuses_an_unknown_product():
    f = PeerForm()
    launcher.tick(f, "Auto", True)
    launcher.tick(f, "Credit card", True)
    launcher.tick(f, "Credit card", True)
    assert f.products == ["Credit card", "Auto"]
    launcher.tick(f, "Auto", False)
    assert f.products == ["Credit card"]
    with pytest.raises(ValueError):
        launcher.tick(f, "Boats", True)
    assert launcher.PEER_PRODUCTS == tuple(peers_run.books.PRODUCTS)


# ---- Peers: Pull and Build call peers/run.py, and say what came back


def test_pull_hands_run_pull_the_forms_arguments_and_says_what_it_said(tmp_path):
    got, heard = [], []

    def fake(say, **kw):
        got.append(kw)
        say("Cache %s: 1 quarter" % kw["cache"])
        say("Filers in 2026Q2: 16")
        return {}
    f = peers_filled(tmp_path, mergers_pull="yes", mergers_since="2005-10-01", delinquency="yes")
    out = launcher.peer_pull(f, pull=fake, say=heard.append)
    assert out.ok and out.path == tmp_path / "cache"
    assert got == [launcher.peer_arguments(f, "pull")] and got[0]["mergers_since"] == "2005-10-01"
    assert out.lines == heard == ["Cache %s: 1 quarter" % (tmp_path / "cache"), "Filers in 2026Q2: 16"]


def test_pull_and_build_call_peers_run_by_default(tmp_path, monkeypatch, opened):
    """The window does not hold its own copy: with nothing passed, Pull calls
    peers.run.pull and Build peers.run.build, the functions cli.py calls."""
    called = []
    monkeypatch.setattr(peers_run, "pull", lambda say, **kw: called.append(("pull", kw)))
    monkeypatch.setattr(peers_run, "build", lambda say, **kw: called.append(("build", kw)))
    f = peers_filled(tmp_path)
    assert launcher.peer_pull(f).ok and launcher.peer_build(f).ok
    assert called == [("pull", launcher.peer_arguments(f, "pull")), ("build", launcher.peer_arguments(f, "build"))]
    assert opened == [tmp_path / "peers.xlsx"]


def test_a_real_pull_through_run_fills_the_cache_from_a_fake_fdic(tmp_path, monkeypatch, roster_2006):
    fake = FakeFDIC(roster_2006, [{"CHANGECODE": 223, "ACQ_CERT": "6672", "EFFDATE": "2019-01-15",
                                    "OUT_CERT": "1"}])
    monkeypatch.setattr(fdic, "urllib_fetch", fake)
    f = peers_filled(tmp_path, cache=str(tmp_path / "c"), first="2025Q3", last="2026Q2",
                     mergers_pull="yes", mergers_since="2005-10-01")
    heard = []
    out = launcher.peer_pull(f, say=heard.append)
    assert out.ok, out.lines
    assert sorted(p.name for p in (tmp_path / "c").glob("q*.json")) == [
        "q20250930.json", "q20251231.json", "q20260331.json", "q20260630.json"]
    assert json.loads((tmp_path / "c" / "mergers.json").read_text()) == {"6672": ["2019-03-31"]}
    assert heard == out.lines and any("4 fetched" in x for x in out.lines)
    assert "Filers in 2026Q2: 16" in out.lines


def test_a_failed_fetch_and_a_refused_pull_are_words(tmp_path, monkeypatch):
    def broken(url):
        raise OSError("connection refused")
    monkeypatch.setattr(fdic, "urllib_fetch", broken)
    real = fdic.pull
    monkeypatch.setattr(fdic, "pull", lambda *a, **k: real(*a, sleep=lambda s: None, **k))
    out = launcher.peer_pull(peers_filled(tmp_path, first="2026Q2", last="2026Q2"))
    assert not out.ok and out.lines == ["The pull stopped: connection refused"]

    def refuses(say, **kw):
        say("Cache: started")
        raise ValueError("the quarter is not published")
    out = launcher.peer_pull(peers_filled(tmp_path), pull=refuses)
    assert not out.ok and out.lines == ["Cache: started", "The pull refused: the quarter is not published"]


def test_a_real_build_through_run_writes_the_peer_workbook_and_opens_it(tmp_path, monkeypatch, opened,
                                                                         roster_2006):
    monkeypatch.setattr(fdic, "urllib_fetch", no_network)
    lay_out_cache(tmp_path / "cache", roster_2006)
    f = peers_filled(tmp_path)
    out = launcher.peer_build(f)
    assert out.ok, out.lines
    assert out.path == tmp_path / "peers.xlsx" and opened == [out.path]
    assert out.lines[0].startswith("Wrote %s: Credit card" % out.path)
    wb = load_workbook(out.path)
    assert wb.sheetnames[:2] == ["Pack", "Peers"]
    assert sorted(p.name for p in (tmp_path / "series").glob("*.csv")) == sorted(
        "credit-card_%s_%s.csv" % (who, kind) for who in ("pack-composite", "keybank", "industry")
        for kind in ("gross", "net"))


def test_build_with_delinquency_yes_writes_the_delinquency_series(tmp_path, monkeypatch, opened, roster_2006):
    """The window's yes reaches run.build: per measure and basis, the pack
    composite, the bank and the industry. The cache joins the two public
    fixtures, 2017Q1 to 2026Q2, card only."""
    monkeypatch.setattr(fdic, "urllib_fetch", no_network)
    dq = json.loads((PEERS / "delinquency_roster.json").read_text())
    merged = {}
    for q, rows in dq.items():
        co = {r["CERT"]: r for r in roster_2006[q]}
        merged[q] = [dict(co[r["CERT"]], **r) for r in rows]
    lay_out_cache(tmp_path / "cache", merged)
    out = launcher.peer_build(peers_filled(tmp_path, first="2017Q1", delinquency="yes"), open_after=False)
    assert out.ok, out.lines
    names = {p.name for p in (tmp_path / "series").glob("credit-card_*_delinquency-*.csv")}
    assert names and all(n.split("_")[1] in ("pack-composite", "keybank", "industry") for n in names)
    for m in ("30-89", "90-plus-accruing", "nonaccrual", "90-plus-incl-nonaccrual", "30-plus-incl-nonaccrual"):
        assert "credit-card_industry_delinquency-%s_quarter-end.csv" % m in names, m
    assert any(x.startswith("Delinquency, Credit card:") for x in out.lines)
    assert "Delinquency" in load_workbook(out.path).sheetnames
    assert opened == []                                      # open_after=False


def test_a_refusal_from_the_build_and_a_locked_workbook_are_words(tmp_path, monkeypatch, opened):
    monkeypatch.setattr(fdic, "urllib_fetch", no_network)
    out = launcher.peer_build(peers_filled(tmp_path))         # an empty cache folder
    assert not out.ok and len(out.lines) == 1
    assert out.lines[0].startswith("The build refused:") and "peers pull" in out.lines[0]

    def locked(say, **kw):           # as os.replace raises it: the .part, then the file it was moving onto
        part = kw["out"].with_name("peers.part.xlsx")
        raise PermissionError(13, "Access is denied", str(part), 5, str(kw["out"]))
    out = launcher.peer_build(peers_filled(tmp_path), build=locked)
    assert not out.ok and out.lines == ["Couldn't write peers.xlsx: it may be open in Excel. Close it and "
                                        "press Build again."]
    assert opened == []

    def unnamed(say, **kw):
        raise PermissionError(13, "Permission denied")
    out = launcher.peer_build(peers_filled(tmp_path), build=unnamed)
    assert not out.ok and len(out.lines) == 1
    assert "peers.xlsx or a file in the series folder" in out.lines[0]


def _not_replaced(step, stuck=()):
    err = OSError("%s could not be replaced" % step)
    err.not_replaced, err.stuck = step, list(stuck)
    return err


def test_a_locked_series_file_is_named_and_nothing_changed_said(tmp_path):
    """run._commit puts every file in place together or not at all. A series
    file open in Excel is named, not the workbook, and the words say the
    earlier files are as they were, or which could not be put back."""
    def locked(say, **kw):
        say("Read the cache")
        raise _not_replaced(kw["series_dir"] / "credit-card_pack-composite_net.csv")
    out = launcher.peer_build(peers_filled(tmp_path), build=locked)
    assert not out.ok and out.lines == [
        "Read the cache",
        "Couldn't write the series file credit-card_pack-composite_net.csv: it may be open "
        "in Excel. Close it and press Build again.",
        "Nothing was changed: peers.xlsx and the series files are as they were."]

    def stuck(say, **kw):
        raise _not_replaced(kw["out"], [kw["out"]])
    out = launcher.peer_build(peers_filled(tmp_path), build=stuck)
    assert out.lines[0] == "Couldn't write peers.xlsx: it may be open in Excel. Close it and press Build again."
    assert out.lines[1].startswith("These could not be put back as they were") and "peers.xlsx" in out.lines[1]

    def elsewhere(say, **kw):
        raise PermissionError(13, "Access is denied", str(tmp_path / "cache" / "q20260630.json"))
    out = launcher.peer_build(peers_filled(tmp_path), build=elsewhere)
    assert not out.ok and out.lines == ["The build was denied access to %s. Check that it can be read and "
                                        "written from here, and press Build again."
                                        % (tmp_path / "cache" / "q20260630.json")]


@pytest.mark.skipif(sys.platform != "win32", reason="an open file blocks os.replace onto it only on Windows")
def test_a_series_file_really_held_open_is_the_one_named(tmp_path, monkeypatch, roster_2006):
    monkeypatch.setattr(fdic, "urllib_fetch", no_network)
    lay_out_cache(tmp_path / "cache", roster_2006)
    f = peers_filled(tmp_path)
    assert launcher.peer_build(f, open_after=False).ok
    held = tmp_path / "series" / "credit-card_pack-composite_net.csv"
    assert held.is_file()
    f.min_banks = "6"
    with open(held):
        out = launcher.peer_build(f, open_after=False)
    assert not out.ok
    assert ("Couldn't write the series file credit-card_pack-composite_net.csv: it may be open in Excel. "
            "Close it and press Build again.") in out.lines, out.lines
    assert "Nothing was changed: peers.xlsx and the series files are as they were." in out.lines, out.lines
    assert not any(x.startswith("Couldn't write peers.xlsx") for x in out.lines), out.lines


def test_a_pull_denied_its_cache_folder_is_words_never_a_traceback(tmp_path):
    def denied(say, **kw):
        raise PermissionError(13, "Access is denied", str(kw["cache"]))
    f = peers_filled(tmp_path, cache=str(tmp_path / "locked-cache"))
    out = launcher.peer_pull(f, pull=denied)
    assert not out.ok and out.lines == [
        "The pull couldn't write to %s: permission was denied. Choose a cache folder you can write to and "
        "press Pull again." % (tmp_path / "locked-cache")]


def test_a_missing_add_on_keeps_pull_and_build_off(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "missing_addons", lambda: ["openpyxl"])
    f = peers_filled(tmp_path)
    for press, kw in ((launcher.peer_pull, "pull"), (launcher.peer_build, "build")):
        out = press(f, **{kw: lambda **k: pytest.fail("ran without openpyxl")})
        assert not out.ok and "lacks openpyxl" in out.lines[0]


# ---- Peers: one press at a time, and a status line


def test_a_second_press_while_one_runs_is_refused_in_words():
    assert launcher.peer_refusal(None, "pull") is None and launcher.peer_refusal(None, "build") is None
    assert launcher.peer_refusal("pull", "pull") == \
        "Pull is still running. Wait for it to finish before pressing Pull."
    assert launcher.peer_refusal("pull", "build") == \
        "Pull is still running. Wait for it to finish before pressing Build."
    assert launcher.peer_refusal("build", "pull") == \
        "Build is still running. Wait for it to finish before pressing Pull."
    for busy, action in ((None, "run"), ("fetch", "pull")):
        with pytest.raises(ValueError):
            launcher.peer_refusal(busy, action)


def test_the_status_line_says_what_is_running_and_its_latest_line():
    assert launcher.status_words("pull", []) == "Pulling from the FDIC... this takes a little while."
    assert launcher.status_words("build", ["a", "Wrote x"]) == \
        "Building the peer workbook... this takes a little while. Latest: Wrote x"
    assert launcher.finished_words("pull", launcher.Outcome(True, [])) == "Pull finished."
    assert launcher.finished_words("build", launcher.Outcome(False, ["no"])) == \
        "Build did not finish; the reason is below."


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
        assert str(w["step_Peers"].cget("fg")).upper() == launcher.INK      # no longer greyed out
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


def test_the_window_presses_through_the_peers_step_with_a_fake_pull(tmp_path, opened, monkeypatch, roster_2006):
    """The real window: Peers opens, Pull and Build stay off until their
    fields are stated, Pull runs on a worker thread against a fake FDIC (no
    network) with a status line, a second press while it runs is refused in
    words, then Build writes the peer workbook from that cache and opens it."""
    tk = pytest.importorskip("tkinter", reason="tkinter is not installed with this Python")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip("no display to open a window on: %s" % exc)
    fake = FakeFDIC(roster_2006)
    monkeypatch.setattr(fdic, "urllib_fetch", fake)

    def settle(w, key="peer_busy"):
        for _ in range(1200):
            root.update()
            if not w[key]:
                return
            time.sleep(0.05)
        pytest.fail("the press never finished")
    try:
        w = launcher.window(root)
        w["show"]("Peers")
        root.update()
        assert w["page"] == "Peers"
        assert str(w["pull"].cget("state")) == "disabled" and str(w["build"].cget("state")) == "disabled"
        assert w["peers"] == PeerForm()                                     # nothing filled in
        f = peers_filled(tmp_path, cache=str(tmp_path / "cache-new"))
        for k in ("cache", "first", "last"):
            w["peer_var_" + k].set(getattr(f, k))
        w["peer_product_Credit card"].set(True)
        root.update()
        assert str(w["pull"].cget("state")) == "disabled"                   # three choices still wanted
        for k in ("delinquency", "mergers_pull", "refresh"):
            w["peer_var_" + k].set(getattr(f, k))
        root.update()
        assert str(w["pull"].cget("state")) == "normal"
        assert str(w["build"].cget("state")) == "disabled"
        assert launcher.peer_arguments(w["peers"], "pull")["products"] == ["Credit card"]

        w["pull"].invoke()
        assert w["peer_busy"] == "pull" and str(w["pull"].cget("state")) == "disabled"
        assert w["peer_status"].cget("text").startswith("Pulling from the FDIC")
        w["press_peer"]("build")                                             # one that slips past the buttons
        assert w["peer_status"].cget("text") == \
            "Pull is still running. Wait for it to finish before pressing Build."
        settle(w)
        assert w["peer_outcome"].ok, w["peer_outcome"].lines
        assert len(list((tmp_path / "cache-new").glob("q*.json"))) == 82 and len(fake.urls) == 82
        assert w["peer_status"].cget("text") == "Pull finished."
        assert "82 fetched" in w["peer_result"].cget("text")

        for k in ("roster", "out", "series_dir", "mergers_file", "absorptions_file", "extra_acquisitions",
                  "industry_combined", "jump", "acquisition_share", "min_book", "min_banks", "last_n", "min_obs", "base_quarter", "index_min_book",
                  "lagged_years", "lag_years", "normalisation_years", "mix_base_year"):
            w["peer_var_" + k].set(getattr(f, k))
        for k in ("exempt_self", "pack", "rank_by"):
            w["peer_var_" + k].set(getattr(f, k))
        root.update()
        assert str(w["build"].cget("state")) == "normal"
        assert str(w["step_Peers"].master.winfo_children()[1].cget("text")) == "Complete"
        monkeypatch.setattr(fdic, "urllib_fetch", no_network)               # Build reads the cache only
        w["build"].invoke()
        assert w["peer_busy"] == "build"
        settle(w)
        assert w["peer_outcome"].ok, w["peer_outcome"].lines
        assert (tmp_path / "peers.xlsx").is_file() and opened == [tmp_path / "peers.xlsx"]
        assert len(list((tmp_path / "series").glob("*.csv"))) == 6
        assert w["peer_status"].cget("text") == "Build finished."
        assert w["peer_result"].cget("text").startswith("Wrote %s" % (tmp_path / "peers.xlsx"))
    finally:
        root.destroy()


def test_the_peers_window_is_never_left_jammed_and_its_status_line_moves(tmp_path, monkeypatch):
    """A stray character in a year field is words, not a raise in the field's
    trace. A press that fails before its worker starts frees the window
    again, so the next press is not refused as 'still running'. And the
    status line follows what a running press says, while it runs."""
    import threading
    tk = pytest.importorskip("tkinter", reason="tkinter is not installed with this Python")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip("no display to open a window on: %s" % exc)
    raised = []
    root.report_callback_exception = lambda *exc: raised.append(exc[1])
    try:
        w = launcher.window(root)
        w["show"]("Peers")
        f = peers_filled(tmp_path)
        for k in ("cache", "first", "last", "roster", "out", "series_dir", "mergers_file", "absorptions_file", "extra_acquisitions", "acquisition_share",
                  "industry_combined", "jump", "min_book", "min_banks", "last_n", "min_obs", "base_quarter",
                  "index_min_book", "lagged_years", "lag_years", "normalisation_years", "mix_base_year",
                  "delinquency", "mergers_pull", "refresh", "exempt_self", "pack", "rank_by"):
            w["peer_var_" + k].set(getattr(f, k))
        w["peer_product_Credit card"].set(True)
        root.update()
        assert str(w["build"].cget("state")) == "normal"
        w["peer_var_lagged_years"].set("2019 \u00b2")
        root.update()
        assert raised == [] and str(w["build"].cget("state")) == "disabled"
        assert "--lagged-years" in "\n".join(launcher.peer_problems(w["peers"], "build"))
        w["peer_var_lagged_years"].set("2019 2025")
        root.update()
        assert str(w["build"].cget("state")) == "normal"

        def no_thread(*a, **kw):
            raise RuntimeError("can't start new thread")
        monkeypatch.setattr(launcher.threading, "Thread", no_thread)
        w["build"].invoke()
        assert w["peer_busy"] is None
        assert w["peer_status"].cget("text") == "Build did not finish; the reason is below."
        assert "can't start new thread" in w["peer_result"].cget("text")
        assert str(w["build"].cget("state")) == "normal" and str(w["pull"].cget("state")) == "normal"
        monkeypatch.undo()

        go, said_it = threading.Event(), threading.Event()

        def slow_pull(pf, say=None):
            say("Fetched 2006Q1")
            said_it.set()
            go.wait(30)
            return launcher.Outcome(True, ["Fetched 2006Q1"])
        monkeypatch.setattr(launcher, "peer_pull", slow_pull)
        w["pull"].invoke()
        assert said_it.wait(10)
        try:
            for _ in range(200):                          # the wait loop looks every 200 ms
                root.update()
                if "Latest: Fetched 2006Q1" in w["peer_status"].cget("text"):
                    break
                time.sleep(0.05)
            assert w["peer_status"].cget("text") == \
                "Pulling from the FDIC... this takes a little while. Latest: Fetched 2006Q1"
            assert w["peer_busy"] == "pull"
        finally:
            go.set()
        for _ in range(200):
            root.update()
            if w["peer_busy"] is None:
                break
            time.sleep(0.05)
        assert w["peer_status"].cget("text") == "Pull finished." and raised == []
    finally:
        root.destroy()
