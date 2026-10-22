"""What if (W12): two sets of settings on one pull, side by side. Each must be
complete, nothing is chosen, and every reading reports both ratings and what
each was measured against."""
import json

import pytest

from threshold_engine.macro import __main__ as M
from threshold_engine.macro import rate as R
from threshold_engine.macro.compare import compare, lines
from threshold_engine.macro.settings import check, template

from test_macro_rate import cache  # noqa: F401  (the fixture: a pull on disk)
from test_macro_settings import answered


def _runs(cache, a=None, b=None):  # noqa: F811
    pull = R.Pull(cache)
    ra = R.rate_all(cache, check(answered(**(a or {}))), pull=pull)
    rb = R.rate_all(cache, check(answered(**(b or {}))), pull=pull)
    return ra, rb


def test_every_reading_is_reported_with_both_ratings_and_the_move_between_them(cache):  # noqa: F811
    ra, rb = _runs(cache, {"history": "full"}, {"history": {"years": 3}})
    c = compare(ra, rb, "settings.json", "what-if.json")
    assert [s["name"] for s in c["settings"] if s["differs"]] == ["history"]
    differ = next(s for s in c["settings"] if s["differs"])
    assert (differ["a"], differ["b"]) == ("full history", "the last 3 years")
    a = {(r["key"], r["reading"]): r for r in ra["ratings"]}
    b = {(r["key"], r["reading"]): r for r in rb["ratings"]}
    rated = [x for x in c["rows"] if x["a"] or x["b"]]       # the rest: rated under neither (a partial pull)
    assert {(x["key"], x["reading"]) for x in rated} == set(a) | set(b)
    for x in rated:
        k = (x["key"], x["reading"])
        assert x["a"]["rating"] == a[k]["rating"] and x["b"]["rating"] == b[k]["rating"]
        assert x["move"] == b[k]["rating"] - a[k]["rating"]          # above zero: higher under the what-if
        assert x["a"]["history_from"] < x["b"]["history_from"]       # three years is shorter than the full history
    t = c["totals"]
    assert t["compared"] == len(rated) == sum(map(sum, c["matrix"]))
    assert t["same"] + t["higher"] + t["lower"] == t["compared"]
    assert any(x["move"] for x in rated)                             # the fixture moves at least one reading
    for x in rated:
        assert c["matrix"][x["a"]["rating"] - 1][x["b"]["rating"] - 1] >= 1


def test_the_same_settings_twice_differ_nowhere(cache):  # noqa: F811
    ra, rb = _runs(cache)
    c = compare(ra, rb, "a.json", "b.json")
    assert not any(s["differs"] for s in c["settings"])
    assert all(x["move"] == 0 for x in c["rows"] if x["a"]) and c["totals"]["same"] == c["totals"]["compared"]
    assert "the same answers, so every rating is the same" in "\n".join(lines(c))


def test_a_reading_one_side_did_not_ask_for_says_so_rather_than_failing(cache):  # noqa: F811
    ra, rb = _runs(cache, {}, {"change_for": []})
    c = compare(ra, rb, "a.json", "b.json")
    only = [x for x in c["rows"] if x["move"] is None and (x["a"] or x["b"])]
    assert only and all(x["reading"] == "change" and x["b"] is None for x in only)
    assert {x["why_missing"] for x in only} == {"not asked for by these settings"}
    assert c["totals"]["only_a"] == len(only) and c["totals"]["only_b"] == 0
    names = {s["setting"]: s for s in c["settings"]}
    assert names["Also rated on their change"]["b"] == "none"
    # a direction the what-if no longer asks for reads "not asked", not a blank
    assert any(s["name"] == "directions" and s["b"] == "not asked" for s in c["settings"])


def test_runs_of_two_different_pulls_are_not_compared(cache):  # noqa: F811
    ra, rb = _runs(cache)
    with pytest.raises(ValueError, match="different pulls"):
        compare(ra, dict(rb, vintage="2026-10-14"), "a.json", "b.json")


def test_the_printout_names_each_reading_that_moves_with_both_percentiles(cache):  # noqa: F811
    ra, rb = _runs(cache, {"history": "full"}, {"history": {"years": 3}})
    c = compare(ra, rb, "settings.json", "what-if.json")
    out = "\n".join(lines(c))
    assert "History each reading is measured against: full history -> the last 3 years" in out
    moved = [x for x in c["rows"] if x["move"]]
    for x in moved:
        assert "%d -> %d" % (x["a"]["rating"], x["b"]["rating"]) in out
        assert "%.1f%%" % x["b"]["percentile"] in out


def _files(tmp_path, b):
    a_path, b_path = tmp_path / "settings.json", tmp_path / "what-if.json"
    a_path.write_text(json.dumps(answered()))
    b_path.write_text(json.dumps(b))
    return str(a_path), str(b_path)


def test_a_what_if_with_a_gap_is_refused_naming_its_file_and_the_gap(cache, tmp_path, capsys):  # noqa: F811
    a, b = _files(tmp_path, template())
    assert M.main(["rate", "--cache", str(cache), "--settings", a, "--compare", b]) == 2
    err = capsys.readouterr().err
    assert "REFUSED: the what-if settings in %s" % b in err and "cutoffs: not answered" in err


def test_compare_prints_what_differs_and_writes_the_what_if_tab_second(cache, tmp_path, capsys):  # noqa: F811
    openpyxl = pytest.importorskip("openpyxl")
    a, b = _files(tmp_path, answered(history={"years": 3}))
    out = tmp_path / "book.xlsx"
    assert M.main(["rate", "--cache", str(cache), "--settings", a, "--compare", b, "--workbook", str(out)]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("What if: what-if.json against settings.json, both from the pull of 2026-10-15.")
    assert openpyxl.load_workbook(out).sheetnames[:3] == ["Ratings", "What if", "States"]
    assert M.main(["rate", "--cache", str(cache), "--settings", a, "--compare", b, "--json"]) == 0
    got = json.loads(capsys.readouterr().out)
    assert got["compare"]["b"] == "what-if.json" and got["ratings"]


def test_a_reading_the_what_if_does_not_rate_gives_the_what_ifs_own_reason(cache):  # noqa: F811
    from threshold_engine.macro.settings import template as T
    directions = {k: {r: "lower is worse" for r in v} for k, v in T()["directions"]["answer"].items()}
    directions["cpi"]["change"] = "not rated"
    ra, rb = _runs(cache, {}, {"directions": directions})
    c = compare(ra, rb, "a.json", "b.json")
    row = next(x for x in c["rows"] if x["key"] == "cpi" and x["reading"] == "change")
    assert row["b"] is None and row["move"] is None
    assert row["why_missing"] == "the firm chose not to rate it"


def test_a_change_over_a_different_horizon_is_printed_with_both_horizons(cache):  # noqa: F811
    # Codex on #452: the printout named a 12-month rating "change over 6 months".
    ra, rb = _runs(cache, {"change_months": 6}, {"change_months": 12})
    c = compare(ra, rb, "a.json", "b.json")
    assert c["months"] == [6, 12]
    out = lines(c)
    moved = [x for x in c["rows"] if x["move"] and x["reading"] == "change"]
    assert moved                                    # CPI's change moves in the fixture
    for x in moved:
        row = next(line for line in out if x["title"] + "," in line)
        assert "change over 6 months; what if: over 12 months" in row
    assert not any("change over 6 months " in line and "what if" not in line for line in out)


def test_a_reading_neither_run_rates_is_reported_with_each_runs_reason(cache):  # noqa: F811
    # Codex on #452: a change only the what-if asked for, of a series not in the pull, was left out entirely.
    ra, rb = _runs(cache, {"change_for": []}, {})
    c = compare(ra, rb, "a.json", "b.json")
    rated = {(x["key"], x["reading"]) for x in ra["ratings"] + rb["ratings"]}
    asked = {(x["key"], x["reading"]) for x in ra["not_rated"] + rb["not_rated"]}
    neither = [x for x in c["rows"] if x["a"] is None and x["b"] is None]
    assert {(x["key"], x["reading"]) for x in neither} == asked - rated
    whatif_only = [x for x in neither if x["why_a"] == "not asked for by these settings"]
    assert whatif_only and all(x["reading"] == "change" and "not in the pull" in x["why_b"] for x in whatif_only)
    assert c["totals"]["neither"] == len(neither) and all(x["move"] is None for x in neither)
    out = "\n".join(lines(c))
    assert "%d under neither." % len(neither) in out
    assert "not rated under either: as you have it, not asked for by these settings; under the what-if, not in " \
           "the pull" in out
    assert c["totals"]["only_a"] + c["totals"]["only_b"] == sum(1 for x in c["rows"] if (x["a"] is None) !=
                                                                (x["b"] is None))


def test_a_change_rated_on_one_side_only_is_printed_with_that_sides_horizon_only(cache):  # noqa: F811
    # Codex on #452: "change over 6 months; what if: over 12 months ... rated as you have it only" named the
    # horizon of a side that made no rating.
    from threshold_engine.macro.settings import template as T
    off = {k: {r: "lower is worse" for r in v} for k, v in T()["directions"]["answer"].items()}
    off["cpi"]["change"] = "not rated"
    for a, b, said, unsaid in (({"change_months": 6}, {"change_months": 12, "directions": off},
                                "change over 6 months", "12 months"),
                               ({"change_months": 6, "directions": off}, {"change_months": 12},
                                "change (what if: over 12 months)", "6 months")):
        c = compare(*_runs(cache, a, b), "a.json", "b.json")
        line = next(x for x in lines(c) if x.startswith("  ..") and "Consumer prices, all items," in x)
        assert said in line and unsaid not in line, line


def test_a_change_neither_run_rates_names_the_horizon_of_the_settings_that_asked_for_it(cache):  # noqa: F811
    # Codex on #452: a change only the what-if asked for, and could not rate, was labelled with both horizons.
    c = compare(*_runs(cache, {"change_for": [], "change_months": 6}, {"change_months": 12}), "a.json", "b.json")
    asked_b = [x for x in c["rows"] if x["a"] is None and x["b"] is None and x["reading"] == "change"
               and x["why_a"] == "not asked for by these settings"]
    assert asked_b
    out = lines(c)
    for x in asked_b:
        line = next(r for r in out if r.startswith("  ..") and x["title"] + ", change" in r)
        assert "change (what if: over 12 months)" in line and "6 months" not in line, line


def test_two_runs_that_read_different_bytes_of_one_pull_are_not_compared(cache):  # noqa: F811
    # Codex on #452: the same settings, a file changed between the runs, and moves the settings did not make.
    ra = R.rate_all(cache, check(answered()))
    with open(R.Pull(cache).folder / "fred-UNRATE.csv", "a") as fh:
        fh.write("2026-10-01,2.0\n")
    rb = R.rate_all(cache, check(answered()))
    with pytest.raises(ValueError, match="different bytes of the pull of 2026-10-15 \\(fred-UNRATE.csv"):
        compare(ra, rb, "a.json", "b.json")
