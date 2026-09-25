"""The cube file refuses rather than defaults, and says the line to add."""

import pytest

from conftest import cube
from origination_cube import config as cfgmod


def test_the_base_file_is_accepted():
    c = cube()
    assert [m.mode for m in c.measures] == ["flagwt", "sumnum", "count", "median"]


@pytest.mark.parametrize("line", ["bands", "dimensions", "measures", "benchmark", "name"])
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
