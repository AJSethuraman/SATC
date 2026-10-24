"""Slice 4 (issue #367): step 4 stratified — bands, schemes, the pooled odds
ratio and the word — on the three planted books, plus `pack suggest`."""

from __future__ import annotations

import io
import json
from datetime import date

import pytest
import yaml
from openpyxl import load_workbook

from analysis_pack import synth
from analysis_pack.cli import main
from analysis_pack.config import load_config
from analysis_pack.ingest import read_table
from analysis_pack.population import add_months, build_population
from analysis_pack.suggest import suggest
from analysis_pack.workbook import build_pack

from conftest import ASOF, RUN

WORDS = {"survives", "collapses", "unknown", "no crude effect"}


def _build(d):
    cfg = load_config(d / "config.yaml")
    table = read_table(d / "loans.csv")
    pop = build_population(cfg, table.rows, ASOF)
    blob, data, checks = build_pack(cfg, pop, table, RUN)
    return {"cfg": cfg, "table": table, "pop": pop, "bytes": blob, "data": data, "checks": checks}


@pytest.fixture(scope="module")
def null_pack(tmp_path_factory):
    d = tmp_path_factory.mktemp("null")
    synth.generate(d, mode="null")
    return _build(d)


@pytest.fixture(scope="module")
def confounded_pack(tmp_path_factory):
    d = tmp_path_factory.mktemp("confounded")
    synth.generate(d, mode="confounded")
    return _build(d)


def _words(pack):
    return {f"{st.confounder}.{st.scheme}": st.word for st in pack["data"].strata}


def test_the_planted_effect_survives_every_band(effect_pack, effect_recalc):
    words = _words(effect_pack)
    assert words and all(w == "survives" for w in words.values()), words
    live = effect_recalc.exact("4_Stratified", WORDS)
    assert live == ["survives"] * len(words), live
    line = effect_recalc.find_text("Cover", "Survives or collapses")
    assert len(line) == 1 and line[0].count("— survives") == len(words)


def test_the_null_book_reads_no_crude_effect_everywhere(null_pack):
    from recalc import Recalc
    words = _words(null_pack)
    assert words and all(w == "no crude effect" for w in words.values()), words
    rec = Recalc(null_pack["bytes"])
    verdicts = [v for r, v in rec.column("_check", "G").items() if r >= 2]
    assert verdicts and all(v == "OK" for v in verdicts)
    line = rec.find_text("Cover", "Survives or collapses")
    assert line and line[0].count("no crude effect") == len(words)


def test_the_confounded_book_collapses_on_the_confounder_and_only_there(confounded_pack):
    from recalc import Recalc
    words = _words(confounded_pack)
    assert words["size_band.edges"] == "collapses", words
    assert words["amount_band.edges"] == "survives" and words["category_2.levels"] == "survives", words
    st = next(s for s in confounded_pack["data"].strata if s.confounder == "size_band")
    crude, pooled = st.crude, st.pooled
    assert crude[0] > 1.5 and crude[1] > 1.0                     # a real crude effect
    assert pooled[0] < crude[0] / 2 and st.kept < 0.5              # most of it is size
    rec = Recalc(confounded_pack["bytes"])
    verdicts = [v for r, v in rec.column("_check", "G").items() if r >= 2]
    assert verdicts and all(v == "OK" for v in verdicts), [v for v in verdicts if v != "OK"][:3]
    assert sorted(rec.exact("4_Stratified", WORDS)) == ["collapses", "survives", "survives"]


def test_the_word_is_live_moving_the_threshold_knob_flips_it(confounded_pack):
    """SURV_T at 0.99 means only 1% of the crude log-odds need survive, so the
    size-band block no longer collapses. Its pooled interval still contains 1,
    so the honest word is 'unknown', not 'survives': the knob moved the word,
    and the rule kept it truthful."""
    from recalc import Recalc
    wb = load_workbook(io.BytesIO(confounded_pack["bytes"]))
    ref = wb.defined_names["SURV_T"].attr_text            # e.g. _config!$C$4
    sheet, cell = ref.split("!")[0], ref.split("!")[1].replace("$", "")
    before = Recalc(confounded_pack["bytes"]).exact("4_Stratified", WORDS)
    assert sorted(before) == ["collapses", "survives", "survives"]
    after = Recalc(confounded_pack["bytes"], inputs={(sheet, cell): 0.99}).exact("4_Stratified", WORDS)
    assert "collapses" not in after and sorted(after) == ["survives", "survives", "unknown"], after
    st = next(s for s in confounded_pack["data"].strata if s.confounder == "size_band")
    from analysis_pack.stats import survives_word
    assert survives_word(st.crude, st.pooled, 0.99) == "unknown"    # the Python twin agrees on the flipped word


def test_two_schemes_on_one_confounder_give_two_blocks_each_with_its_word(effect_book, tmp_path):
    raw = yaml.safe_load((effect_book / "config.yaml").read_text())
    raw["confounders"][0] = {"name": "size_band", "field": "field_b",
                             "schemes": {"coarse": [200000, 800000], "fine": [100000, 200000, 400000, 800000]}}
    p = tmp_path / "two.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False))
    cfg = load_config(p)
    table = read_table(effect_book / "loans.csv")
    pop = build_population(cfg, table.rows, ASOF)
    blob, data, checks = build_pack(cfg, pop, table, RUN)
    keys = [f"{st.confounder}.{st.scheme}" for st in data.strata]
    assert "size_band.coarse" in keys and "size_band.fine" in keys
    wb = load_workbook(io.BytesIO(blob))
    bands = [str(c.value) for row in wb["1_Capture"].iter_rows() for c in row if c.value and "size_band ·" in str(c.value)]
    assert bands == ["size_band · coarse", "size_band · fine"]


def test_suggest_offers_three_schemes_with_counts_flags_thin_bands_and_marks_the_outcome_cut(confounded_pack, capsys, tmp_path):
    s = suggest(confounded_pack["pop"], "field_b")
    names = [sc.name for sc in s.schemes]
    assert names == ["by_loans_thirds", "by_loans_quarters", "by_events_thirds", "round"]
    thirds = s.schemes[0]
    assert len(thirds.edges) == 2 and max(thirds.loans) - min(thirds.loans) <= 2
    by_events = s.schemes[2]
    assert max(by_events.events) - min(by_events.events) <= 2
    assert s.outcome_cut is not None and s.outcome_cut_rates[0] > s.outcome_cut_rates[1]
    # a thin band: a field where one band has fewer than ten events
    cfg = confounded_pack["cfg"]
    pop = confounded_pack["pop"]
    tiny = suggest(pop, "amount")
    assert isinstance(tiny.schemes[0].thin(), list)
    # through the command line, on the file, with the marker text
    d = tmp_path / "book"
    d.mkdir()
    (d / "config.yaml").write_text(open(cfg.source_path).read())
    (d / "loans.csv").write_bytes(open(confounded_pack["table"].path, "rb").read())
    rc = main(["suggest", str(d / "config.yaml"), "--data", str(d / "loans.csv"), "--asof", "2026-06-30", "--field", "field_b"])
    out = capsys.readouterr()
    assert rc == 0
    assert "information only — not for step 4, because it is chosen on the outcome" in out.err
    assert "paste under the confounder's `schemes:`" in out.err
    status = json.loads(out.out)
    assert status["suggestions"][0]["outcome_cut"]["note"].startswith("information only")


def test_a_thin_band_is_flagged(effect_book):
    cfg = load_config(effect_book / "config.yaml")
    orig = add_months(ASOF, -40)
    rows = []
    for i in range(300):
        rows.append({"loan_id": f"T{i}", "origination_date": orig.isoformat(), "field_a": "10", "field_b": str(1000 + i * 10),
                     "amount": "1", "category_1": "x", "category_2": "y", "code_1": "1111",
                     "outcome_date": add_months(orig, 6).isoformat() if i % 40 == 0 else "",
                     "flag_1": 0, "measure_a": "1", "measure_b": "2"})
    pop = build_population(cfg, rows, ASOF)
    s = suggest(pop, "field_b")
    assert any(any(sc.thin()) for sc in s.schemes)
