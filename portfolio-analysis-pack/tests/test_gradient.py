"""Seam 1: the built pack, recalculated, against what was planted."""

from __future__ import annotations

import csv
from datetime import date

from analysis_pack.config import load_config
from analysis_pack.ingest import read_table
from analysis_pack.population import add_months, build_population, months_between
from analysis_pack.workbook import build_pack

from conftest import ASOF, RUN


def test_the_planted_gradient_reads_monotonic_increasing(effect_recalc, effect_pack):
    assert effect_pack["data"].per_outcome[0][1].word == "monotonic increasing"
    words = effect_recalc.find_text("3_Gradient", "monotonic")
    assert words == ["monotonic increasing"], words


def test_the_cover_answer_line_follows_the_gradient_word(effect_recalc):
    lines = effect_recalc.find_text("Cover", "Gradient:")
    assert len(lines) == 1
    assert lines[0].startswith("Gradient: yes.")


def test_every_check_row_agrees_and_the_cover_counts_them(effect_recalc, effect_pack):
    g = effect_recalc.column("_check", "G")
    assert len(g) == len(effect_pack["checks"]) + 1          # + the header row
    verdicts = [v for r, v in g.items() if r >= 2]
    assert verdicts and all(v == "OK" for v in verdicts), [v for v in verdicts if v != "OK"]
    n = len(verdicts)
    cover = effect_recalc.find_text("Cover", "formula checks agree")
    assert cover == [f"{n} of {n} formula checks agree (see _check)"]


def test_bucket_rates_are_the_cube_counts_divided(effect_recalc, effect_pack):
    g = effect_pack["data"].per_outcome[0][1]
    loans = effect_recalc.column("3_Gradient", "B")
    events = effect_recalc.column("3_Gradient", "C")
    rates = effect_recalc.column("3_Gradient", "D")
    rows = sorted(r for r in loans if r in events and r in rates and isinstance(loans[r], (int, float)))
    assert len(rows) == len(g.rows) + 1
    for r, gr in zip(rows[:len(g.rows)], g.rows):
        assert loans[r] == gr.cube.n and events[r] == gr.cube.events
        if gr.cube.n:
            assert abs(rates[r] - gr.cube.events / gr.cube.n) < 1e-12


def test_a_23_month_loan_is_unseasoned_at_a_24_month_window(tmp_path, effect_book):
    cfg = load_config(effect_book / "config.yaml")
    rows = [
        {"loan_id": "A", "origination_date": add_months(ASOF, -24).isoformat(), "field_a": "10", "field_b": "5",
         "amount": "1", "category_1": "x", "category_2": "y", "code_1": "1111", "outcome_date": ""},
        {"loan_id": "B", "origination_date": add_months(ASOF, -23).isoformat(), "field_a": "10", "field_b": "5",
         "amount": "1", "category_1": "x", "category_2": "y", "code_1": "1111", "outcome_date": ""},
    ]
    pop = build_population(cfg, rows, ASOF)
    by = {l.loan_id: l for l in pop.loans}
    assert by["A"].seasoned and by["A"].months_on_book == 24
    assert not by["B"].seasoned and by["B"].months_on_book == 23
    assert months_between(date(2024, 6, 30), ASOF) == 24
    assert months_between(date(2024, 7, 1), ASOF) == 23


def test_an_event_after_the_window_is_not_an_event_and_a_blank_side_leaves_the_table(effect_book):
    cfg = load_config(effect_book / "config.yaml")
    orig = add_months(ASOF, -40)
    rows = [
        {"loan_id": "IN", "origination_date": orig.isoformat(), "field_a": "10", "field_b": "5", "amount": "1",
         "category_1": "x", "category_2": "y", "code_1": "1111", "outcome_date": add_months(orig, 24).isoformat()},
        {"loan_id": "OUT", "origination_date": orig.isoformat(), "field_a": "10", "field_b": "5", "amount": "1",
         "category_1": "x", "category_2": "y", "code_1": "1111", "outcome_date": add_months(orig, 25).isoformat()},
        {"loan_id": "BLANK", "origination_date": orig.isoformat(), "field_a": "", "field_b": "5", "amount": "1",
         "category_1": "x", "category_2": "y", "code_1": "1111", "outcome_date": ""},
    ]
    pop = build_population(cfg, rows, ASOF)
    by = {l.loan_id: l for l in pop.loans}
    assert by["IN"].events["o1"] and not by["OUT"].events["o1"]
    assert by["BLANK"].rule_value is None and by["BLANK"].bucket is None
    from analysis_pack import ladder
    g = ladder.gradient(cfg, pop, pop.outcomes[0])
    assert g.with_both == 2 and g.blank_either == 1


def test_the_planted_odds_ratio_is_visible_in_the_flagged_versus_base_rates(effect_pack):
    """Slice 6 fits the model; here the raw contrast already carries the plant."""
    g = effect_pack["data"].per_outcome[0][1]
    flagged_n = sum(r.cube.n for r in g.rows[2:])          # buckets at or above the flag line (ratio > 1.0)
    flagged_x = sum(r.cube.events for r in g.rows[2:])
    p1 = flagged_x / flagged_n
    p0 = g.base.rate
    crude_or = (p1 / (1 - p1)) / (p0 / (1 - p0))
    planted = effect_pack["planted"]["true_marginal_flag_odds_ratio"]
    assert planted > 1.5
    assert abs(crude_or - planted) / planted < 0.35, (crude_or, planted)
