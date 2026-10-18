"""The firm's settings: every one required, the recommendation never read, every gap named at once."""
import json
import pathlib

import pytest

from threshold_engine.macro import settings as S
from threshold_engine.macro.__main__ import main
from threshold_engine.macro.catalog import BY_KEY, DERIVED_BY_KEY, HIGHER, LOWER

TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "macro" / "settings-template.json"


def answered(**over):
    """A complete settings dict. These are test inputs, not the firm's answers."""
    t = S.template()
    values = {"cutoffs": [40, 60, 80, 97], "on_the_line": "better", "history": {"years": 20},
              "change_months": 6, "show_sahm": False, "change_for": "all",
              "directions": {k: {r: LOWER for r in v} for k, v in t["directions"]["answer"].items()}}
    values.update(over)
    for k, v in values.items():
        t[k]["answer"] = v
    return t


def problems(raw):
    with pytest.raises(S.Refused) as e:
        S.check(raw)
    return str(e.value)


def test_an_empty_template_is_refused_naming_every_question_and_every_open_direction():
    msg = problems(S.template())
    for name, *_ in S.QUESTIONS:
        if name != "directions":
            assert "%s: not answered" % name in msg
    for key, reading in S.open_readings("all"):
        assert "directions: %s %s: not answered" % (key, reading) in msg
    assert "nothing is rated" in msg


def test_the_recommendation_is_never_read_as_an_answer():
    t = S.template()
    assert t["cutoffs"]["recommended"] and t["cutoffs"]["answer"] is None
    msg = problems(t)       # every recommendation present, every answer empty
    assert "cutoffs: not answered" in msg


def test_a_complete_answer_is_read_exactly():
    s = S.check(answered())
    assert s["cutoffs"] == [40, 60, 80, 97] and s["on_the_line"] == "better"
    assert s["history"] == {"years": 20} and s["change_months"] == 6 and s["show_sahm"] is False
    assert s["directions"][("cpi", "change")] == LOWER
    assert ("unemployment", "position") not in s["directions"]     # the research states that one


@pytest.mark.parametrize("name,value,says", [
    ("cutoffs", [50, 75, 75, 95], "each above the last"),
    ("cutoffs", [50, 75, 90, 100], "between 0 and 100"),
    ("cutoffs", [50, 75, 90], "four numbers"),
    ("cutoffs", [True, 75, 90, 95], "four numbers"),
    ("on_the_line", "maybe", "\"worse\" or \"better\""),
    ("history", {"years": 0}, "above 0"),
    ("history", "all", "\"full\" or"),
    ("change_months", 12.0, "whole number"),
    ("change_months", True, "whole number"),
    ("show_sahm", "yes", "true or false"),
    ("change_for", ["unemployment", "nope"], "not series the tool rates: nope"),
])
def test_an_unusable_answer_is_refused_with_what_is_needed(name, value, says):
    assert says in problems(answered(**{name: value}))


def test_a_direction_the_research_states_cannot_be_overridden_and_a_typo_is_caught():
    t = answered()
    t["directions"]["answer"]["unemployment"] = {"position": LOWER}
    t["colour"] = {"answer": "red"}
    msg = problems(t)
    assert "unemployment: its direction is stated by the research" in msg
    assert "colour: not a setting the tool has" in msg


def test_a_direction_must_be_one_of_the_three():
    t = answered()
    t["directions"]["answer"]["cpi"]["change"] = "up is bad"
    assert "directions: cpi change: need one of" in problems(t)


def test_change_for_decides_which_readings_a_series_carries():
    assert S.readings_of(BY_KEY["unemployment"], "all") == ("position", "change")
    assert S.readings_of(BY_KEY["unemployment"], ["mortgage_rate"]) == ("position",)
    assert S.readings_of(BY_KEY["unemployment"], ["unemployment"]) == ("position", "change")
    # a level that climbs over the decades is rated on its change whatever the list says
    assert S.readings_of(BY_KEY["cpi"], []) == ("change",)
    assert S.readings_of(DERIVED_BY_KEY["mortgage_spread"], []) == ("position",)


def test_only_the_directions_that_will_be_used_are_asked_for():
    t = answered(change_for=[])
    del t["directions"]["answer"]["mortgage_rate"]["change"]       # not rated, so not needed
    s = S.check(t)
    assert ("mortgage_rate", "change") not in s["directions"]
    del t["directions"]["answer"]["mortgage_rate"]["position"]     # still rated, so still needed
    assert "directions: mortgage_rate position: not answered" in problems(t)


def test_the_template_is_never_written_over_a_file(tmp_path):
    out = tmp_path / "s.json"
    S.write_template(out)
    assert json.loads(out.read_text())["cutoffs"]["answer"] is None
    with pytest.raises(S.Refused, match="never written over"):
        S.write_template(out)


def test_rate_refuses_from_the_command_line_with_exit_2(tmp_path, capsys):
    out = tmp_path / "s.json"
    S.write_template(out)
    assert main(["rate", "--cache", str(tmp_path), "--settings", str(out)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("REFUSED: the settings are not complete") and "cutoffs: not answered" in err


def test_the_template_in_the_docs_is_the_one_the_tool_writes():
    assert json.loads(TEMPLATE.read_text("utf-8")) == S.template()


def test_every_open_direction_has_a_recommendation_and_every_recommendation_is_usable():
    rec = S.template()["directions"]["recommended"]
    assert sorted((k, r) for k, v in rec.items() for r in v) == sorted(S.open_readings("all"))
    assert all(v in (HIGHER, LOWER) for d in rec.values() for v in d.values())


SETTINGS = TEMPLATE.with_name("settings.json")


def test_the_firms_settings_are_complete_and_are_what_they_approved():
    # The firm, 16 Oct 2026: "Good with those recommendations". Each answer is
    # the recommendation the firm was shown beside it, in the same file.
    raw = json.loads(SETTINGS.read_text("utf-8"))
    S.check(raw)
    for name, *_ in S.QUESTIONS:
        assert raw[name]["answer"] == raw[name]["recommended"], name
