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


def test_a_shown_series_is_never_rated_has_no_direction_and_says_why_it_needs_care():
    from threshold_engine.macro.catalog import SHOWN
    assert SHOWN and all(s.shown and not s.rated and s.stress is None for s in SHOWN)
    assert all(s.care and s.change_in in ("points", "percent") for s in SHOWN)
    assert not {s.key for s in SHOWN} & {i.key for i in RATED}
    assert [s for s in SERIES if s.shown] == SHOWN


def test_the_settings_ask_nothing_about_a_shown_series():
    # The firm's settings stay complete: a question about a shown series would make them refuse.
    from threshold_engine.macro.catalog import SHOWN
    from threshold_engine.macro.settings import open_readings, template
    asked = {k for k, _ in open_readings("all")} | set(template()["directions"]["answer"])
    assert asked and not asked & {s.key for s in SHOWN}


def test_the_licensed_part_of_the_group_is_named_with_its_reason():
    from threshold_engine.macro.catalog import NOT_SHOWN, SHOWN
    named = dict(NOT_SHOWN)
    for what in ("University of Michigan consumer sentiment", "Atlanta Fed wage growth tracker",
                 "Atlanta Fed home ownership affordability"):
        assert named[what].startswith("licensed")
    assert not any("Michigan" in s.publisher or "Atlanta" in s.publisher for s in SHOWN)
    # A licence that asks for wording gets it carried with the series.
    sce = next(s for s in SHOWN if s.source == "nyfed_sce")
    assert sce.credit.startswith("Source: Survey of Consumer Expectations") and "FRBNY disclaims" in sce.credit
