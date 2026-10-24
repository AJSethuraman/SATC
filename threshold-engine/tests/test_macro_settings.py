"""The firm's settings: every one required, the recommendation never read, every gap named at once."""
import json
import pathlib

import pytest

from threshold_engine.macro import settings as S
from threshold_engine.macro.__main__ import main
from threshold_engine.macro.catalog import BY_KEY, DERIVED_BY_KEY

TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "macro" / "settings-template.json"


def answered(**over):
    """A complete settings dict. These are test inputs, not the firm's answers."""
    t = S.template()
    values = {"history": {"years": 20}, "change_months": 6, "normal_width": 1.5, "left_out": [], "axis_cut": 0,
              "show_sahm": False, "compare_p": 0.05, "compare_leads": [-12, 0, 6, 12, 24], "compare_starts": 4,
              "compare_min_pairs": 6}
    values.update(over)
    for k, v in values.items():
        t[k]["answer"] = v
    return t


def problems(raw):
    with pytest.raises(S.Refused) as e:
        S.check(raw)
    return str(e.value)


def test_an_empty_template_is_refused_naming_every_question():
    msg = problems(S.template())
    for name, *_ in S.QUESTIONS:
        assert "%s: not answered" % name in msg
    assert "nothing is read" in msg


def test_the_recommendation_is_never_read_as_an_answer():
    t = S.template()
    assert t["normal_width"]["recommended"] == 1 and t["normal_width"]["answer"] is None
    assert "normal_width: not answered" in problems(t)       # every recommendation present, every answer empty


def test_a_complete_answer_is_read_exactly():
    s = S.check(answered(left_out=["2020Q2-2021Q2", "2008Q4"], axis_cut=1))
    assert s == {"history": {"years": 20}, "change_months": 6, "normal_width": 1.5,
                 "left_out": [["2008Q4", "2008Q4"], ["2020Q2", "2021Q2"]], "axis_cut": 1.0, "show_sahm": False,
                 "compare_p": 0.05, "compare_leads": [-12, 0, 6, 12, 24], "compare_starts": 4,
                 "compare_min_pairs": 6}
    assert len(S.left_out_set(s["left_out"])) == 6               # 2020Q2 to 2021Q2 is five quarters, and 2008Q4


@pytest.mark.parametrize("name,value,says", [
    ("compare_p", 0, "above 0 and below 1"),
    ("compare_p", 1, "above 0 and below 1"),
    ("compare_leads", [], "different whole numbers"),
    ("compare_leads", [0, 0], "different whole numbers"),
    ("compare_leads", [6.0], "different whole numbers"),
    ("compare_starts", 5, "1, 2 or 4"),
    ("compare_starts", 3, "first of a quarter"),          # Jan, May, Sep: a quarterly series has none in two
    ("compare_starts", True, "1, 2 or 4"),
    ("compare_min_pairs", 3, "at least 4"),
    ("history", {"years": 0}, "above 0"),
    ("history", "all", "\"full\" or"),
    ("change_months", 12.0, "whole number"),
    ("change_months", True, "whole number"),
    ("normal_width", 0, "above 0"),
    ("normal_width", "1", "above 0"),
    ("normal_width", True, "above 0"),
    ("left_out", "2020Q2", "need a list"),
    ("left_out", ["2020Q5"], "'2020Q5' is not a quarter"),
    ("left_out", ["2021Q2-2020Q2"], "whose first quarter comes first"),
    ("left_out", ["2020-Q2"], "is not a quarter"),
    ("left_out", [2020], "is not a quarter"),
    ("axis_cut", 11, "from 0 to 10"),
    ("axis_cut", -1, "from 0 to 10"),
    ("show_sahm", "yes", "true or false"),
])
def test_an_unusable_answer_is_refused_with_what_is_needed(name, value, says):
    assert says in problems(answered(**{name: value}))


def test_a_typo_is_caught_and_a_setting_the_tool_no_longer_has_says_why():
    # A settings file written before 22 Oct 2026 still holds the rating questions: refused, each with its reason,
    # rather than read as if the cut-offs still meant something.
    t = answered()
    t["colour"] = {"answer": "red"}
    t["cutoffs"] = {"answer": [50, 75, 90, 95]}
    t["directions"] = {"answer": {}}
    msg = problems(t)
    assert "colour: not a setting the tool has" in msg
    assert "cutoffs: no longer a setting: the tool no longer rates" in msg
    assert "directions: no longer a setting" in msg


def test_every_series_carries_its_change_and_its_level_only_where_its_place_means_something():
    assert S.readings_of(BY_KEY["unemployment"]) == ("position", "change")
    assert S.readings_of(BY_KEY["cpi"]) == ("change",)                 # a level that climbs over the decades
    assert S.readings_of(DERIVED_BY_KEY["mortgage_spread"]) == ("position", "change")


def test_a_quarter_is_named_for_the_months_it_holds():
    assert [S.quarter_of(d) for d in ("2020-01-01", "2020-03-31", "2020-04-01", "2020-12-31")] == [
        "2020Q1", "2020Q1", "2020Q2", "2020Q4"]
    assert S.quarter_label(S.quarter_index("2021Q4") + 1) == "2022Q1"


def test_the_template_is_never_written_over_a_file(tmp_path):
    out = tmp_path / "s.json"
    S.write_template(out)
    assert json.loads(out.read_text())["normal_width"]["answer"] is None
    with pytest.raises(S.Refused, match="never written over"):
        S.write_template(out)


def test_read_refuses_from_the_command_line_with_exit_2(tmp_path, capsys):
    out = tmp_path / "s.json"
    S.write_template(out)
    assert main(["read", "--cache", str(tmp_path), "--settings", str(out)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("REFUSED: the settings are not complete") and "normal_width: not answered" in err


def test_the_template_in_the_docs_is_the_one_the_tool_writes():
    assert json.loads(TEMPLATE.read_text("utf-8")) == S.template()


SETTINGS = TEMPLATE.with_name("settings.json")

#: The firm's answers and where each came from. 16 Oct 2026: "Good with those recommendations" (history, the
#: horizon and the Sahm reading). 22 Oct 2026: "Typical move (Recommended)", whose option read "The median change
#: plus or minus one typical move ... the width is a setting you can change"; "None yet" for the quarters left
#: out; and "I will take recommended ways of viewing", the recommendation being the axis that leaves a spike off.
#: 23 Oct 2026, "As the Excel version (Recommended)": the Dashboard's test, as the comparison built in Excel ran it.
FIRM = {"history": "full", "change_months": 12, "show_sahm": True, "normal_width": 1, "left_out": [],
        "axis_cut": 1, "compare_p": 0.05, "compare_leads": [-24, -18, -12, -6, 0, 6, 12, 18, 24, 30, 36],
        "compare_starts": 4, "compare_min_pairs": 6}


def test_the_firms_settings_are_complete_and_are_what_they_said():
    raw = json.loads(SETTINGS.read_text("utf-8"))
    S.check(raw)
    assert {name: raw[name]["answer"] for name, *_ in S.QUESTIONS} == FIRM


def test_every_settings_file_in_the_docs_is_read_so_each_example_still_runs():
    # A new question left the 30-year what-if refusing (Codex on #472): every file the docs offer must be read.
    for path in sorted(SETTINGS.parent.glob("*.json")):
        if path != TEMPLATE:
            S.load(path)
