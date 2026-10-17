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
    assert {(x["key"], x["reading"]) for x in c["rows"]} == set(a) | set(b)
    for x in c["rows"]:
        k = (x["key"], x["reading"])
        assert x["a"]["rating"] == a[k]["rating"] and x["b"]["rating"] == b[k]["rating"]
        assert x["move"] == b[k]["rating"] - a[k]["rating"]          # above zero: higher under the what-if
        assert x["a"]["history_from"] < x["b"]["history_from"]       # three years is shorter than the full history
    t = c["totals"]
    assert t["compared"] == len(c["rows"]) == sum(map(sum, c["matrix"]))
    assert t["same"] + t["higher"] + t["lower"] == t["compared"]
    assert any(x["move"] for x in c["rows"])                         # the fixture moves at least one reading
    for x in c["rows"]:
        assert c["matrix"][x["a"]["rating"] - 1][x["b"]["rating"] - 1] >= 1


def test_the_same_settings_twice_differ_nowhere(cache):  # noqa: F811
    ra, rb = _runs(cache)
    c = compare(ra, rb, "a.json", "b.json")
    assert not any(s["differs"] for s in c["settings"])
    assert all(x["move"] == 0 for x in c["rows"]) and c["totals"]["same"] == c["totals"]["compared"]
    assert "the same answers, so every rating is the same" in "\n".join(lines(c, 6))


def test_a_reading_one_side_did_not_ask_for_says_so_rather_than_failing(cache):  # noqa: F811
    ra, rb = _runs(cache, {}, {"change_for": []})
    c = compare(ra, rb, "a.json", "b.json")
    only = [x for x in c["rows"] if x["move"] is None]
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
    out = "\n".join(lines(c, 6))
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
