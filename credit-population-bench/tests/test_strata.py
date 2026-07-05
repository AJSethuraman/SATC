"""Seam 1 — band schemes (edges) and group-by per-cell metrics + reconciliation."""

import math

import pandas as pd

from popbench import bands, contract, mapping, strata
from popbench.cleaning import validate_and_clean


def _clean(df):
    props = mapping.propose(list(df.columns))
    cols = [mapping.ColumnMap(p.header, p.field_id,
                              contract.UNIT_FRACTION if p.needs_unit else None)
            for p in props if p.field_id]
    m = mapping.confirm(cols)
    clean, _ = validate_and_clean(df, m)
    return clean


# --- band edges (right-closed: edge value falls in the lower band) ----------

def test_cfpb_fico_band_edges():
    s = pd.Series([579, 580, 619, 620, 719, 720, 800])
    labels = bands.get_preset("fico_orig", "cfpb").assign(s).astype("object").tolist()
    assert labels == [
        "deep subprime (<=579)", "subprime (580-619)", "subprime (580-619)",
        "near-prime (620-659)", "prime (660-719)", "prime-plus (720-799)",
        "superprime (800+)"]


def test_y14q_fico_split():
    s = pd.Series([610, 620, 621, 800])
    labels = bands.get_preset("fico_orig", "y14q").assign(s).astype("object").tolist()
    assert labels == ["<=620", "<=620", ">620", ">620"]


def test_dti_default_edges():
    s = pd.Series([0.30, 0.36, 0.43, 0.49, 0.50])
    labels = bands.get_preset("dti", "default").assign(s).astype("object").tolist()
    assert labels == ["<=36%", "<=36%", "37-43%", "44-49%", "50%+"]


def test_custom_scheme_overrides_edges():
    sch = bands.custom("fico_orig", [660], ["subprime-ish", "prime-ish"])
    labels = sch.assign(pd.Series([600, 700])).astype("object").tolist()
    assert labels == ["subprime-ish", "prime-ish"]


# --- group-by partition + reconciliation ------------------------------------

def test_group_by_product_reconciles_to_population():
    from popbench import demo
    clean = _clean(demo.demo_population_full())
    strat = strata.group_by(clean, "product_type")
    assert strat.reconciles
    assert strat.total_count == 5
    assert math.isclose(strat.total_balance, 173000.0)  # 15+25+8+120+5 k
    by_val = {c.value: c for c in strat.cells}
    assert by_val["card"].count == 2 and math.isclose(by_val["card"].balance, 13000.0)
    assert by_val["auto"].count == 2 and by_val["heloc"].count == 1


def test_group_by_fico_band():
    from popbench import demo
    clean = _clean(demo.demo_population_full())
    strat = strata.group_by(clean, "fico", scheme=bands.get_preset("fico_orig", "cfpb"))
    by_val = {c.value: c.count for c in strat.cells}
    # FICOs 710,640,690,705,720 -> prime x3 (710,690,705), near-prime x1 (640),
    # prime-plus x1 (720)
    assert by_val["prime (660-719)"] == 3
    assert by_val["near-prime (620-659)"] == 1
    assert by_val["prime-plus (720-799)"] == 1
    assert strat.reconciles


def test_ltv_self_suppresses_on_unsecured_cells():
    from popbench import demo
    clean = _clean(demo.demo_population_full())
    strat = strata.group_by(clean, "structure")
    cells = {c.value: c for c in strat.cells}
    # closed_end / open_end are unsecured here -> no LTV rows -> WA-LTV is None.
    for unsecured in ("closed_end", "open_end"):
        wa = {w.attribute: w for w in cells[unsecured].wa}
        assert "ltv" not in wa or wa["ltv"].dollar_weighted is None
    # residential has an LTV -> WA-LTV present.
    res_wa = {w.attribute: w for w in cells["residential_secured"].wa}
    assert res_wa["ltv"].dollar_weighted == 0.82


def test_cardinality_guard_refuses_id_like_dimension():
    from popbench import demo
    clean = _clean(demo.demo_population_full())
    import pytest
    with pytest.raises(strata.CardinalityError):
        strata.group_by(clean, "loan_id", max_cardinality=2)
