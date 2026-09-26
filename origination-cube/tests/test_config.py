"""The cube file refuses rather than defaults, and says the line to add."""

import pytest

from conftest import cube
from origination_cube import config as cfgmod


def test_the_base_file_is_accepted():
    c = cube()
    assert [m.name for m in c.measures] == ["outcome_loans", "outcome_booked", "gco_rate", "ranr_rate",
                                            "contribution_rate", "loans", "score_median"]
    assert [m.mode for m in c.measures] == ["flagwt", "flagwt", "sumnum", "sumnum", "sumnum", "count", "median"]


@pytest.mark.parametrize("line", ["bands", "dimensions", "benchmark", "name", "key", "booked", "outcome", "gco",
                                  "ranr"])
def test_each_required_line_is_refused_with_the_line_to_add(line):
    with pytest.raises(cfgmod.ConfigError) as exc:
        cube(**{line: None})
    assert f"missing line `{line}:`" in str(exc.value)


def test_unknown_top_line_is_refused():
    with pytest.raises(cfgmod.ConfigError, match="unknown line `weigth:`"):
        cube(weigth="BAL")


def test_edges_must_rise():
    with pytest.raises(cfgmod.ConfigError, match="must rise"):
        cube(bands=[{"name": "score", "field": "SCORE", "edges": [700, 650]}])


def test_the_core_rates_are_built_from_the_required_lines():
    """The firm's minimum: a yes/no outcome, GCO, RANR, the booked amount and a key."""
    c = cube()
    by = {m.name: m for m in c.measures}
    assert by["outcome_loans"].label() == "COUNT(loans where BAD = 1) / COUNT(loans)"
    assert by["outcome_booked"].label() == "SUM(BAL where BAD = 1) / SUM(BAL)"
    assert by["gco_rate"].label() == "SUM(GCO) / SUM(BAL)"
    assert by["ranr_rate"].label() == "SUM(RANR) / SUM(BAL)"
    assert all(m.core and not m.optional for m in c.measures[:4])


def test_an_outcome_can_be_any_value_made_yes_or_no():
    c = cube(outcome={"field": "DECISION", "is": "AUTO"})
    assert c.measures[0].label() == "COUNT(loans where DECISION = 'AUTO') / COUNT(loans)"


def test_a_core_name_cannot_be_reused():
    with pytest.raises(cfgmod.ConfigError, match="taken by a core rate"):
        cube(measures=[{"name": "gco_rate", "mode": "count"}])


def test_a_rate_names_its_own_denominator():
    with pytest.raises(cfgmod.ConfigError, match="needs `per:`"):
        cube(measures=[{"name": "gco", "mode": "sumnum", "value": "GCO"}])


def test_unknown_mode_is_refused():
    with pytest.raises(cfgmod.ConfigError, match="mode"):
        cube(measures=[{"name": "x", "mode": "average", "value": "GCO"}])


def test_names_must_be_unique():
    with pytest.raises(cfgmod.ConfigError, match="more than once"):
        cube(dimensions=[{"name": "score", "field": "CHAN"}])


def test_every_problem_is_listed_at_once():
    with pytest.raises(cfgmod.ConfigError) as exc:
        cube(bands=None, dimensions=None, benchmark=None)
    assert len(exc.value.problems) == 3


def test_median_does_not_reconcile_and_says_so():
    m = [m for m in cube().measures if m.mode == "median"][0]
    assert not m.reconciles and "does not add up" in m.label()


def test_the_example_file_loads():
    from pathlib import Path
    cfgmod.load(Path(__file__).parents[1] / "configs" / "examples" / "origination_cube.yaml")
