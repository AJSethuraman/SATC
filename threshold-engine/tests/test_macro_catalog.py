"""The catalog: every series traceable to the research, and no direction guessed."""
import pathlib

from threshold_engine.macro.catalog import BY_KEY, DERIVED, HIGHER, LOWER, RATED, SERIES, STATES

REPORT = (pathlib.Path(__file__).resolve().parents[1] / "docs" / "macro" / "reports"
          / "Macro risk indicators for lending.md")


def test_keys_are_unique():
    assert len(BY_KEY) == len(SERIES)


def test_every_series_names_its_publisher_licence_and_start():
    for s in SERIES:
        assert s.publisher and s.licence and s.starts and s.unit, s.key
        assert s.group in ("consumer", "commercial", "both"), s.key
        assert s.frequency in ("daily", "weekly", "monthly", "quarterly"), s.key


def test_every_series_cites_a_section_the_report_really_has():
    text = REPORT.read_text("utf-8").replace("–", "-")
    for s in SERIES + DERIVED:
        assert "## " + s.report in text, (s.key, s.report)


def test_a_direction_is_either_stated_or_left_to_the_firm_with_a_reason():
    for s in SERIES + DERIVED:
        assert s.stress in (HIGHER, LOWER, None), s.key
        if s.stress is None and s.rated:
            assert "firm sets" in s.note, s.key   # says so, rather than leaving a silent blank


def test_all_fifty_states_and_dc():
    assert len(STATES) == 51 and len(set(STATES)) == 51
    assert all(("unemployment_" + st.lower()) in BY_KEY for st in STATES)


def test_every_rated_series_says_how_its_change_is_counted_and_whether_its_level_is_rated():
    for s in RATED:
        assert s.change_in in ("points", "percent"), s.key
        if s.position:      # not rated on its place in history: says why, and is a level that grows
            assert "says nothing" in s.position and s.change_in == "percent", s.key


def test_a_derived_reading_is_built_from_two_series_the_catalog_pulls():
    for d in DERIVED:
        assert len(d.inputs) == 2 and all(k in BY_KEY for k in d.inputs), d.key
        assert d.key not in BY_KEY and d.how, d.key
    assert len(RATED) == len([s for s in SERIES if s.rated]) + len(DERIVED)
