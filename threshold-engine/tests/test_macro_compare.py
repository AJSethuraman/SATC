"""What if (W12): two sets of settings on one pull, side by side. Each must be
complete, nothing is chosen, and every reading reports how it reads under each
and what it was measured against."""
import json

import pytest

from threshold_engine.macro import __main__ as M
from threshold_engine.macro import readings as R
from threshold_engine.macro.compare import compare, lines
from threshold_engine.macro.readings import DIRECTIONS
from threshold_engine.macro.settings import check, template

from test_macro_readings import cache  # noqa: F401  (the fixture: a pull on disk)
from test_macro_settings import answered


def _runs(cache, a=None, b=None):  # noqa: F811
    pull = R.Pull(cache)
    ra = R.read_all(cache, check(answered(**(a or {}))), pull=pull)
    rb = R.read_all(cache, check(answered(**(b or {}))), pull=pull)
    return ra, rb


def test_every_change_is_reported_with_both_directions_and_the_move_between_them(cache):  # noqa: F811
    ra, rb = _runs(cache, {"history": "full"}, {"history": {"years": 3}})
    c = compare(ra, rb, "settings.json", "what-if.json")
    assert [s["name"] for s in c["settings"] if s["differs"]] == ["history"]
    differ = next(s for s in c["settings"] if s["differs"])
    assert (differ["a"], differ["b"]) == ("full history", "the last 3 years")
    a = {(r["key"], r["reading"]): r for r in ra["readings"]}
    b = {(r["key"], r["reading"]): r for r in rb["readings"]}
    read = [x for x in c["rows"] if x["a"] and x["b"]]
    assert {(x["key"], x["reading"]) for x in read} == set(a) & set(b)
    for x in read:
        k = (x["key"], x["reading"])
        assert x["a"]["history_from"] < x["b"]["history_from"]       # three years is shorter than the full history
        if x["reading"] == "change":
            assert (x["a"]["direction"], x["b"]["direction"]) == (a[k]["direction"], b[k]["direction"])
            assert x["move"] == DIRECTIONS.index(b[k]["direction"]) - DIRECTIONS.index(a[k]["direction"])
        else:
            assert x["move"] is None and x["a"]["percentile"] == a[k]["percentile"]
    t = c["totals"]
    changes = [x for x in read if x["reading"] == "change"]
    assert t["compared"] == len(changes) == sum(map(sum, c["matrix"]))
    assert t["same"] + t["up"] + t["down"] == t["compared"]
    for x in changes:
        assert c["matrix"][DIRECTIONS.index(x["a"]["direction"])][DIRECTIONS.index(x["b"]["direction"])] >= 1


def test_the_same_settings_twice_differ_nowhere(cache):  # noqa: F811
    ra, rb = _runs(cache)
    c = compare(ra, rb, "a.json", "b.json")
    assert not any(s["differs"] for s in c["settings"])
    assert all(x["move"] == 0 for x in c["rows"] if x["a"] and x["reading"] == "change")
    assert c["totals"]["same"] == c["totals"]["compared"] > 0
    assert "the same answers, so every reading is the same" in "\n".join(lines(c))


def test_leaving_quarters_out_is_a_what_if_like_any_other(cache):  # noqa: F811
    ra, rb = _runs(cache, {"history": "full"}, {"history": "full", "left_out": ["2026Q3"]})
    c = compare(ra, rb, "settings.json", "pandemic.json")
    differ = next(s for s in c["settings"] if s["differs"])
    assert (differ["setting"], differ["a"], differ["b"]) == ("Quarters left out", "none", "2026Q3")
    u = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "change")
    # The fixture's jump to 9% in July 2026 is all of 2026 Q3: left out, the latest change is June's, Stable.
    assert (u["a"]["direction"], u["b"]["direction"], u["move"]) == ("Increasing", "Stable", -1)
    assert u["b"]["date"] == "2026-06-01"


def test_runs_of_two_different_pulls_are_not_compared(cache):  # noqa: F811
    ra, rb = _runs(cache)
    with pytest.raises(ValueError, match="different pulls"):
        compare(ra, dict(rb, vintage="2026-10-14"), "a.json", "b.json")


def test_the_printout_names_each_change_that_moves_with_both_typical_moves(cache):  # noqa: F811
    ra, rb = _runs(cache, {"history": "full"}, {"history": "full", "left_out": ["2026Q3"]})
    c = compare(ra, rb, "settings.json", "what-if.json")
    out = "\n".join(lines(c))
    assert "Quarters left out: none -> 2026Q3" in out
    moved = [x for x in c["rows"] if x["move"]]
    assert moved
    for x in moved:
        assert "%s -> %s" % (x["a"]["direction"], x["b"]["direction"]) in out
        assert "%+.1f of" % x["b"]["movement"] in out


def _files(tmp_path, b):
    a_path, b_path = tmp_path / "settings.json", tmp_path / "what-if.json"
    a_path.write_text(json.dumps(answered()))
    b_path.write_text(json.dumps(b))
    return str(a_path), str(b_path)


def test_a_what_if_with_a_gap_is_refused_naming_its_file_and_the_gap(cache, tmp_path, capsys):  # noqa: F811
    a, b = _files(tmp_path, template())
    assert M.main(["read", "--cache", str(cache), "--settings", a, "--compare", b]) == 2
    err = capsys.readouterr().err
    assert "REFUSED: the what-if settings in %s" % b in err and "normal_width: not answered" in err


def test_compare_prints_what_differs_and_writes_the_what_if_tab_after_the_dashboard(cache, tmp_path, capsys):  # noqa: F811,E501
    openpyxl = pytest.importorskip("openpyxl")
    a, b = _files(tmp_path, answered(history={"years": 3}))
    out = tmp_path / "book.xlsx"
    assert M.main(["read", "--cache", str(cache), "--settings", a, "--compare", b, "--workbook", str(out)]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("What if: what-if.json against settings.json, both from the pull of 2026-10-15.")
    assert openpyxl.load_workbook(out).sheetnames[:4] == ["Overview", "Dashboard", "What if", "Unemployment"]
    assert M.main(["read", "--cache", str(cache), "--settings", a, "--compare", b, "--json"]) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["compare"]["b"] == "what-if.json" and got["readings"]


def test_a_change_one_side_cannot_read_gives_that_sides_own_reason(cache):  # noqa: F811
    ra, rb = _runs(cache, {}, {"change_months": 400})       # no series in the fixture is 400 months long
    c = compare(ra, rb, "a.json", "b.json")
    row = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "change")
    assert row["b"] is None and row["move"] is None and row["a"]
    assert row["why_missing"].startswith("no change over 400 months can be counted")
    assert c["totals"]["only_a"] >= 1


def test_a_change_over_a_different_horizon_is_printed_with_both_horizons(cache):  # noqa: F811
    # Codex on #452: the printout named a 12-month reading "change over 6 months".
    ra, rb = _runs(cache, {"change_months": 6}, {"change_months": 12})
    c = compare(ra, rb, "a.json", "b.json")
    assert c["months"] == [6, 12]
    out = lines(c)
    moved = [x for x in c["rows"] if x["move"] and x["reading"] == "change"]
    assert moved                                    # the mortgage rate's change moves in the fixture
    for x in moved:
        row = next(line for line in out if x["title"] + "," in line)
        assert "change over 6 months; what if: over 12 months" in row
    assert not any("change over 6 months " in line and "what if" not in line for line in out
                   if not line.startswith("  .."))


def test_a_change_read_on_one_side_only_is_printed_with_that_sides_horizon_only(cache):  # noqa: F811
    # Codex on #452: a line named the horizon of a side that read nothing.
    for a, b, said, unsaid in (({"change_months": 6}, {"change_months": 400}, "change over 6 months", "400 months"),
                               ({"change_months": 400}, {"change_months": 12}, "change (what if: over 12 months)",
                                "400 months")):
        c = compare(*_runs(cache, a, b), "a.json", "b.json")
        line = next(x for x in lines(c) if x.startswith("  ..") and "Unemployment rate, change" in x)
        assert said in line and unsaid not in line.split(" only; ")[0], line


def test_a_reading_neither_run_reads_is_reported_with_each_runs_reason(cache):  # noqa: F811
    # Codex on #452: a reading neither run could read was left out entirely.
    ra, rb = _runs(cache)
    c = compare(ra, rb, "a.json", "b.json")
    neither = [x for x in c["rows"] if x["a"] is None and x["b"] is None]
    assert {(x["key"], x["reading"]) for x in neither} == {(x["key"], x["reading"]) for x in ra["not_read"]}
    assert c["totals"]["neither"] == len(neither) and all(x["move"] is None for x in neither)
    out = "\n".join(lines(c))
    assert "%d under neither." % len(neither) in out
    assert "read under neither: as you have it, not in the pull of 2026-10-15" in out


def test_two_runs_that_read_different_bytes_of_one_pull_are_not_compared(cache):  # noqa: F811
    # Codex on #452: the same settings, a file changed between the runs, and moves the settings did not make.
    ra = R.read_all(cache, check(answered()))
    with open(R.Pull(cache).folder / "fred-UNRATE.csv", "a") as fh:
        fh.write("2026-10-01,2.0\n")
    rb = R.read_all(cache, check(answered()))
    with pytest.raises(ValueError, match="different bytes of the pull of 2026-10-15 \\(fred-UNRATE.csv"):
        compare(ra, rb, "a.json", "b.json")
