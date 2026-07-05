"""Seam 1 — delinquency normalization, both-basis rates, URCCP branches."""

import math

import pandas as pd
import pytest

from popbench import contract, delinquency, mapping


def _confirm(headers):
    props = mapping.propose(headers)
    cols = []
    for p in props:
        if not p.field_id:
            continue
        unit = contract.UNIT_FRACTION if p.needs_unit else None
        cols.append(mapping.ColumnMap(p.header, p.field_id, unit))
    return mapping.confirm(cols)


def _normalize(df, status_map=None):
    m = _confirm(list(df.columns))
    return delinquency.normalize(df, m, status_map=status_map)


# --- the three delinquency forms all reach the same canonical bucket -------

def test_dpd_days_binning():
    df = pd.DataFrame({"loan_id": ["a", "b", "c", "d"],
                       "current_balance": [1.0, 1.0, 1.0, 1.0],
                       "dpd_days": [0, 45, 100, 200]})
    out, recs = _normalize(df)
    assert out["dpd_bucket_canon"].tolist() == [
        "current", "dpd_30_59", "dpd_90_119", "dpd_180_plus"]
    assert out["dpd_min"].tolist() == [0.0, 30.0, 90.0, 180.0]
    assert recs and recs[0].rule == "bucketize_dpd_days"


def test_aging_label_mapping():
    df = pd.DataFrame({"loan_id": ["a", "b", "c"],
                       "current_balance": [1.0, 1.0, 1.0],
                       "dpd_bucket": ["Current", "30-59", "180+"]})
    out, _ = _normalize(df)
    assert out["dpd_bucket_canon"].tolist() == ["current", "dpd_30_59", "dpd_180_plus"]


def test_status_code_mapping_requires_declaration():
    df = pd.DataFrame({"loan_id": ["a", "b"],
                       "current_balance": [1.0, 1.0],
                       "dpd_status": ["CURR", "B2"]})
    with pytest.raises(ValueError, match="DELQ_STATUS"):
        _normalize(df)   # no status_map declared
    out, _ = _normalize(df, status_map={"CURR": "current", "B2": "dpd_60_89"})
    assert out["dpd_bucket_canon"].tolist() == ["current", "dpd_60_89"]


# --- delinquency rates on BOTH bases ---------------------------------------

def test_delinquency_rates_dollar_and_count_hand_tallied():
    df = pd.DataFrame({
        "loan_id": ["1", "2", "3", "4"],
        "current_balance": [10000.0, 20000.0, 30000.0, 40000.0],
        "dpd_days": [0, 45, 100, 130],
    })
    out, _ = _normalize(df)
    rates = delinquency.delinquency_rates(out)
    assert rates["n"] == 4 and rates["total_balance"] == 100000.0
    cum = {r.label: r for r in rates["cumulative"]}
    # 30+: loans 2,3,4 -> count 3/4 = .75, $90k/$100k = .90
    r30 = cum["30+ DPD (cumulative)"]
    assert r30.count == 3 and math.isclose(r30.count_rate, 0.75)
    assert math.isclose(r30.dollar_rate, 0.90)
    # 90+: loans 3,4 -> count .50, dollars .70 (dollar != count -> why both ship)
    r90 = cum["90+ DPD (cumulative)"]
    assert math.isclose(r90.count_rate, 0.50) and math.isclose(r90.dollar_rate, 0.70)


# --- URCCP classification per branch ---------------------------------------

def _classified(rows_by_structure):
    frames = []
    for struct, loans in rows_by_structure.items():
        f = pd.DataFrame(loans)
        f["structure"] = struct
        frames.append(f)
    df = pd.concat(frames, ignore_index=True)
    out, _ = _normalize(df)
    return {r.structure: r for r in delinquency.classify_urccp(out)}


def test_urccp_closed_and_open_end():
    res = _classified({
        "closed_end": {
            "loan_id": ["c1", "c2", "c3", "c4"],
            "current_balance": [10000.0, 20000.0, 30000.0, 40000.0],
            "dpd_days": [0, 45, 100, 130],
        },
        "open_end": {
            "loan_id": ["o1", "o2"],
            "current_balance": [50000.0, 60000.0],
            "dpd_days": [200, 90],
        },
    })
    # Closed: Substandard >=90 -> c3,c4 (count 2, $70k); Loss >=120 -> c4 ($40k).
    ce = res["closed_end"]
    assert ce.substandard_count == 2 and math.isclose(ce.substandard_dollars, 70000.0)
    assert ce.loss_count == 1 and math.isclose(ce.loss_dollars, 40000.0)
    # Open: Substandard >=90 -> o1,o2 ($110k); Loss >=180 -> o1 ($50k).
    oe = res["open_end"]
    assert oe.substandard_count == 2 and math.isclose(oe.substandard_dollars, 110000.0)
    assert oe.loss_count == 1 and math.isclose(oe.loss_dollars, 50000.0)


def test_urccp_residential_ltv_qualifier():
    res = _classified({
        "residential_secured": {
            "loan_id": ["h1", "h2"],
            "current_balance": [70000.0, 80000.0],
            "dpd_days": [95, 100],
            "ltv": [0.75, 0.50],
        },
    })
    h = res["residential_secured"]
    # Only h1 qualifies: >=90 DPD AND LTV > 60%.
    assert h.substandard_count == 1 and math.isclose(h.substandard_dollars, 70000.0)
    assert h.loss_dollars is None   # writedown is an attestation, not computed


def test_bank_policy_may_tighten_closed_end_loss_clock():
    res_default = _classified({"closed_end": {
        "loan_id": ["a"], "current_balance": [100.0], "dpd_days": [100]}})
    assert res_default["closed_end"].loss_count == 0   # 100 < 120 floor
    # Tighten loss to 90: now the same loan is Loss.
    df = pd.DataFrame({"loan_id": ["a"], "current_balance": [100.0],
                       "dpd_days": [100], "structure": ["closed_end"]})
    out, _ = _normalize(df)
    rows = delinquency.classify_urccp(out, overrides={"loss_from_dpd": 90})
    assert rows[0].loss_count == 1


# --- feature gating --------------------------------------------------------

def test_urccp_refuses_without_structure():
    df = pd.DataFrame({"loan_id": ["a"], "current_balance": [1.0], "dpd_days": [0]})
    out, _ = _normalize(df)
    with pytest.raises(delinquency.FeatureUnavailable, match="structure"):
        delinquency.classify_urccp(out)


def test_delinquency_refuses_without_any_signal():
    m = mapping.confirm([mapping.ColumnMap("loan_id", "loan_id"),
                         mapping.ColumnMap("current_balance", "current_balance")])
    with pytest.raises(delinquency.FeatureUnavailable, match="delinquency"):
        delinquency.delinquency_form(m)
