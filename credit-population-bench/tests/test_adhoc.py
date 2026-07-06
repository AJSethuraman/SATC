"""Seam 2 — ad-hoc tail passthrough + channel/state slice dimensions."""

import pandas as pd
import pytest

from popbench import cohorts, mapping, strata
from popbench.cleaning import validate_and_clean
from popbench.cohorts import Cohort, Rule


def _clean(df):
    props = mapping.propose(list(df.columns))
    m = mapping.confirm([mapping.ColumnMap(p.header, p.field_id)
                         for p in props if p.field_id])
    return validate_and_clean(df, m)


def _frame():
    return pd.DataFrame({
        "Account No": ["A1", "A2", "A3", "A4"],
        "Current Balance": [10000, 20000, 30000, 40000],
        "Orig FICO": [700, 640, 720, 660],
        "Channel": ["direct", "indirect", "indirect", "branch"],
        "Tradelines": [2, 5, 1, 8],          # ad-hoc numeric
        "Cosigner": ["Y", "N", "N", "Y"],    # ad-hoc string
    })


def test_channel_maps_to_canonical():
    props = {p.header: p for p in mapping.propose(list(_frame().columns))}
    assert props["Channel"].field_id == "channel"
    assert props["Tradelines"].field_id is None    # ad-hoc, not canonical
    assert props["Cosigner"].field_id is None


def test_adhoc_columns_are_retained_and_typed():
    clean, records = _clean(_frame())
    assert "Tradelines" in clean.columns and "Cosigner" in clean.columns
    # numeric-looking ad-hoc column coerced to numeric...
    assert pd.api.types.is_numeric_dtype(clean["Tradelines"])
    # ...and recorded in the cleaning audit.
    assert any(r.rule == "coerce_adhoc_numeric" and r.column == "Tradelines" for r in records)


def test_group_by_channel_and_adhoc_dim():
    clean, _ = _clean(_frame())
    strat = strata.group_by(clean, "channel")
    by = {c.value: c.count for c in strat.cells}
    assert by["indirect"] == 2 and by["direct"] == 1
    assert strat.reconciles
    # group-by an ad-hoc string dimension works too
    strat2 = strata.group_by(clean, "Cosigner")
    assert {c.value for c in strat2.cells} == {"Y", "N"}


def test_cohort_over_adhoc_numeric_field():
    clean, _ = _clean(_frame())
    # "tradelines < 3" — the original grill example, over an ad-hoc tail field
    coh = Cohort("thin", "thin file", (Rule("Tradelines", "<", 3),))
    assert int(cohorts.compile_mask(clean, coh).sum()) == 2   # A1(2), A3(1)


def test_slice_dimensions_lists_optional_and_adhoc_only():
    clean, _ = _clean(_frame())
    dims = set(strata.slice_dimensions(clean))
    assert "channel" in dims and "Tradelines" in dims and "Cosigner" in dims
    assert "current_balance" not in dims and "fico_orig" not in dims
