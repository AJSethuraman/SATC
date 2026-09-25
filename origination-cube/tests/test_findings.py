"""One test per finding from the VBA review (docs/vba-findings.md).

Each test names the finding and would go red if the VBA's behaviour came
back. Findings 9 and 10 and the platform notes have no test: they cannot
occur in Python (UsedRange, shared error numbers, ArrayList/.NET, Mid
shadowing, where Worksheet_Change lives).
"""

import pytest

from conftest import cube, row, table
from origination_cube import config as cfgmod
from origination_cube import engine


def test_finding_1_a_blank_is_not_a_zero_in_a_median(book):
    book.append(row(7, "", "A", 100, 0, 0))
    book.append(row(8, None, "A", 100, 0, 0))
    res = engine.run(cube(), table(book))
    total = res.total.medians["score_median"]
    # six real scores: 600, 600, 700, 700, 600, 700 -> 650. Zero-filled
    # blanks (the VBA) would give 600.
    assert total.median == 650
    assert total.left_out == 2
    assert res.left_out["score_median"][("SCORE", "blank")] == 2


def test_finding_2_an_empty_cell_is_never_an_index_or_a_reading():
    assert engine.index_of(None, 0.02) is None
    assert engine.index_of(0.03, None) is None
    assert engine.index_of(0.03, 0.0) is None
    bench = cfgmod.Benchmark(min_units=1, worse_at=1.25, better_at=0.8)
    assert engine.reading_of(None, 100, bench) is None


def test_finding_2_a_cell_with_no_balance_reads_nothing(book):
    # every loan in channel C has a blank balance: its rate cannot exist
    book.append(row(7, 600, "C", "", 1, 10))
    res = engine.run(cube(), table(book))
    s = res.grids[0].cell("under 650", "C").rates["gco"]
    assert s.rate is None and s.vs_topline is None and s.vs_median is None
    assert s.reading_topline is None and s.reading_median is None   # never "better than benchmark"
    assert s.left_out == 1


def test_finding_3_an_unanswered_question_stops_the_run():
    with pytest.raises(cfgmod.ConfigError) as exc:
        cube(dimensions=[{"name": "chan", "field": "[CONFIRM: which column is the channel?]"}])
    assert "dimensions[0].field" in str(exc.value)


def test_finding_3_a_broken_setting_stops_the_run_rather_than_passing():
    # the VBA read a #REF! gate as 0 and passed; here a malformed benchmark refuses
    for bad in ({"min_units": "#REF!", "worse_at": 1.25, "better_at": 0.8},
                {"min_units": 30, "worse_at": None, "better_at": 0.8},
                {"min_units": 30, "worse_at": 0.8, "better_at": 1.25}):
        with pytest.raises(cfgmod.ConfigError):
            cube(benchmark=bad)


def test_finding_4_text_in_a_sumnum_column_is_left_out_of_top_and_bottom(book):
    book.append(row(7, 600, "A", 5000, 0, "#N/A"))
    res = engine.run(cube(), table(book))
    t = res.total.rates["gco"]
    # clean book: 150 / 2000. The VBA added 0 on top and 5000 underneath: 150 / 7000.
    assert t.num == 150 and t.den == 2000
    assert t.rate == pytest.approx(0.075)
    assert t.left_out == 1
    assert res.left_out["gco"][("GCO", "not a number")] == 1
    # the same row still counts where it is readable
    assert res.total.rates["bad"].den == 7000


def test_finding_4_a_flag_that_is_not_0_or_1_is_counted_not_guessed(book):
    book.append(row(7, 600, "A", 100, 2, 0))
    res = engine.run(cube(), table(book))
    assert res.left_out["bad"][("BAD", "flag not 0 or 1")] == 1
    assert res.total.rates["bad"].den == 2000


def test_finding_5_columns_are_found_by_name_not_position(book):
    a = engine.run(cube(), table(book))
    shuffled = ["GCO", "BAD", "ID", "BAL", "CHAN", "SCORE"]
    b = engine.run(cube(), table(book, columns=shuffled))
    assert a.total.rates["gco"].rate == b.total.rates["gco"].rate
    assert [g.cells.keys() for g in a.grids] == [g.cells.keys() for g in b.grids]


def test_finding_5_a_column_that_is_not_there_is_refused_by_name(book):
    with pytest.raises(engine.ColumnsMissing) as exc:
        engine.run(cube(dimensions=[{"name": "chan", "field": "CHANNEL"}]), table(book))
    assert "`CHANNEL`" in str(exc.value) and "dimension chan" in str(exc.value)


def test_finding_6_an_optional_measure_that_is_absent_is_skipped_visibly(book):
    measures = cube().raw["measures"] + [{"name": "ranr", "mode": "sumnum", "value": "RANR", "per": "BAL",
                                          "optional": True}]
    res = engine.run(cube(measures=measures), table(book))
    assert "ranr" not in [m.name for m in res.measures]
    assert any("measure ranr skipped" in w for w in res.warnings)


def test_finding_6_a_required_measure_that_is_absent_is_refused(book):
    measures = cube().raw["measures"] + [{"name": "ranr", "mode": "sumnum", "value": "RANR", "per": "BAL"}]
    with pytest.raises(engine.ColumnsMissing):
        engine.run(cube(measures=measures), table(book))


def test_finding_7_warnings_reach_the_screen(tmp_path, capsys):
    from origination_cube import cli, synth
    cfg, data = synth.write(tmp_path, n=300)
    text = cfg.read_text().replace("key: LOAN_NBR\n", "")
    cfg.write_text(text)
    assert cli.main(["run", str(cfg), "--data", str(data)]) == 0
    out = capsys.readouterr().out
    assert "WARNINGS" in out and "no `key:` line" in out


def test_finding_8_thresholds_have_no_default():
    with pytest.raises(cfgmod.ConfigError) as exc:
        cube(benchmark={"min_units": 30, "worse_at": 1.25})
    assert "better_at" in str(exc.value)
    with pytest.raises(cfgmod.ConfigError) as exc:
        cube(benchmark=None)
    assert "missing line `benchmark:`" in str(exc.value)


def test_finding_8_building_without_comparisons_is_said_in_the_file(book):
    res = engine.run(cube(benchmark="none"), table(book))
    s = res.grids[0].cell("under 650", "A").rates["gco"]
    assert s.reading_topline is None and s.vs_median is None
    assert s.vs_topline is not None          # the ratio needs no threshold


def test_finding_8_a_misspelled_setting_is_refused_not_ignored():
    with pytest.raises(cfgmod.ConfigError) as exc:
        cube(benchmark={"min_units": 30, "worse_at": 1.25, "better_at": 0.8, "wrose_at": 1.5})
    assert "wrose_at" in str(exc.value)
