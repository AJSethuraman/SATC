"""Mode B slice 1 (issue #73): product-conformance schema + indirect-auto tracer.

Recalc-verified against the hand-tallied expectations documented in the
samples fixture; Seam 2 (re-ingest) and Seam 3 (PII, stricter: zero person
names, no loan numbers in exports) covered alongside.
"""

import json

import pytest
import yaml

from credit_review import build_engagement_workbook, ingest_workbook, workbook_bytes
from credit_review.config import ConfigError, load_engagement, load_program
from credit_review.config_mode_b import load_samples
from credit_review.linesheet import CLEAR_FLAG, OPEN_FLAG
from credit_review.workbook import (
    ENGAGEMENTS_DIR,
    PROGRAMS_DIR,
    build_demo_retail_workbook,
)

from recalc import Recalc

PS = "PS_indirect_auto"
# Grid geometry: banner(2) + header(1) -> files start at row 4; 10 files.
GRID = {n: 4 + i for i, n in enumerate(
    ["AU-10021", "AU-10485", "AU-11102", "AU-11760", "AU-12233", "AU-12904",
     "AU-13311", "AU-13977", "AU-14520", "AU-15084"])}


@pytest.fixture(scope="module")
def built():
    wb, program, engagement, samples = build_demo_retail_workbook()
    return wb, Recalc(workbook_bytes(wb)), program, engagement


def _analytics_rows(ws):
    return {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 1).value and ws.cell(r, 8).value}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def test_mode_b_program_loads_and_builds(built):
    wb, _, program, _ = built
    assert program.review_mode == "product_conformance"
    assert [p["id"] for p in program.products] == ["indirect_auto"]
    # library tests resolved onto the product
    tests = {t["id"]: t for t in program.products[0]["tests"]}
    assert tests["dti_within_policy"]["kind"] == "computed"
    assert tests["reg_z_disclosures_present"]["class"] == "compliance"
    assert wb.sheetnames == ["Cover", "PS_indirect_auto", "Products", "Data Mart",
                             "Findings", "_config", "_map"]
    assert wb["_map"].sheet_state == "hidden"


def test_sample_plan_has_both_methods(built):
    _, _, _, engagement = built
    segments = engagement.overlay_products["indirect_auto"]["sample_plan"]["segments"]
    methods = {s["method"] for s in segments}
    assert methods == {"random", "judgmental"}
    strata = [s["stratum"] for s in segments if s["method"] == "random"]
    assert {"commitment": ">$25k"} in strata and {"commitment": "<=$25k"} in strata


def test_person_name_keys_are_refused(tmp_path, built):
    _, _, program, engagement = built
    data = yaml.safe_load(
        (ENGAGEMENTS_DIR / "demo_retail_samples.yaml").read_text(encoding="utf-8"))
    data["products"]["indirect_auto"]["files"][0]["borrower_name"] = "A Person"
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError, match="loan number only"):
        load_samples(p, program.products, engagement.overlay_products)


def test_unknown_segment_and_bad_attestation_are_refused(tmp_path, built):
    _, _, program, engagement = built
    base = yaml.safe_load(
        (ENGAGEMENTS_DIR / "demo_retail_samples.yaml").read_text(encoding="utf-8"))
    bad = yaml.safe_load(yaml.safe_dump(base))
    bad["products"]["indirect_auto"]["files"][0]["segment"] = "not_a_segment"
    p = tmp_path / "seg.yaml"
    p.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="sample plan"):
        load_samples(p, program.products, engagement.overlay_products)
    bad2 = yaml.safe_load(yaml.safe_dump(base))
    bad2["products"]["indirect_auto"]["files"][0]["income_verified"] = "yes"
    p2 = tmp_path / "att.yaml"
    p2.write_text(yaml.safe_dump(bad2), encoding="utf-8")
    with pytest.raises(ConfigError, match="attestation"):
        load_samples(p2, program.products, engagement.overlay_products)


# ---------------------------------------------------------------------------
# Grid: computed tests + FRINGE
# ---------------------------------------------------------------------------
def test_computed_tests_fire_on_the_right_files(built):
    _, rc, _, _ = built
    # dti column D-attr -> test col G (dti_within_policy is first test)
    assert rc.value(PS, f"G{GRID['AU-11760']}") == "fail"     # dti 47%
    assert rc.value(PS, f"G{GRID['AU-10021']}") == "pass"
    assert rc.value(PS, f"I{GRID['AU-12233']}") == "fail"     # ltv 128%
    assert rc.value(PS, f"H{GRID['AU-14520']}") == "pass"     # score 668 >= floor
    assert rc.value(PS, f"J{GRID['AU-14520']}") == "pass"     # term 72 <= 72


def test_fringe_flag_marks_the_buy_box_edge_only(built):
    _, rc, _, _ = built
    fringe = {n: rc.value(PS, f"P{r}") for n, r in GRID.items()}
    assert fringe["AU-14520"] == "FRINGE" and fringe["AU-15084"] == "FRINGE"
    # out-of-box files are conformance fails, not fringe
    assert fringe["AU-11760"] in ("", None)    # dti 47% is outside, not edge
    assert fringe["AU-12233"] in ("", None)    # ltv 128% is outside
    assert fringe["AU-10021"] in ("", None)


def test_fails_helper_counts_row_failures(built):
    _, rc, _, _ = built
    assert rc.value(PS, f"O{GRID['AU-11760']}") == 2   # dti + income
    assert rc.value(PS, f"O{GRID['AU-15084']}") == 0


# ---------------------------------------------------------------------------
# Analytics: rate vs tolerance, compliance per-occurrence
# ---------------------------------------------------------------------------
def test_rates_and_flags_match_hand_tally(built):
    wb, rc, _, _ = built
    rows = _analytics_rows(wb[PS])
    expected = {
        "DTI within policy": (10, 1, 0.10, OPEN_FLAG),
        "Score at/above floor": (10, 0, 0.0, CLEAR_FLAG),
        "LTV within policy": (10, 1, 0.10, OPEN_FLAG),
        "Term within policy": (10, 0, 0.0, CLEAR_FLAG),
        "Credit report reviewed": (10, 0, 0.0, CLEAR_FLAG),
        "Income verified": (10, 2, 0.20, OPEN_FLAG),
        "Contract docs complete": (10, 1, 0.10, CLEAR_FLAG),   # 10% not > 10%
        "Reg Z disclosures present": (10, 1, 0.10, OPEN_FLAG), # per-occurrence
    }
    for label, (n, fails, rate, flag) in expected.items():
        r = rows[label]
        assert rc.value(PS, f"D{r}") == n, label
        assert rc.value(PS, f"E{r}") == fails, label
        assert rc.value(PS, f"F{r}") == pytest.approx(rate), label
        assert rc.value(PS, f"H{r}") == flag, label


def test_urccp_closed_end_classification(built):
    wb, rc, _, _ = built
    ws = wb[PS]
    labels = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)
              if ws.cell(r, 1).value}
    sub = labels["Substandard (>=90 DPD)"]
    loss = labels["Loss (>=120 DPD)"]
    assert rc.value(PS, f"B{sub}") == 130
    assert rc.value(PS, f"C{sub}") == 2250000
    assert rc.value(PS, f"B{loss}") == 60
    assert rc.value(PS, f"C{loss}") == 1150000


# ---------------------------------------------------------------------------
# Findings + roll-up
# ---------------------------------------------------------------------------
def test_findings_aggregates(built):
    wb, rc, _, _ = built
    fnd = wb["Findings"]
    labels = {fnd.cell(r, 1).value: r for r in range(1, fnd.max_row + 1)
              if fnd.cell(r, 1).value and not str(fnd.cell(r, 1).value).startswith("Open")}
    def agg(label):
        return rc.value("Findings", f"B{labels[label]}")
    assert agg("policy") == 2          # dti + ltv rates over tolerance
    assert agg("documentation") == 1   # income verified
    assert agg("compliance") == 1      # Reg Z, per-occurrence
    assert agg("rating") == 0          # not a Mode B class
    assert agg("high") == 2 and agg("medium") == 2
    assert agg("indirect_auto") == 4
    assert agg("TOTAL open") == 4
    assert rc.value("Findings", f"B{labels['Substandard $ (portfolio)']}") == 2250000
    assert rc.value("Findings", f"B{labels['Loss $ (portfolio)']}") == 1150000


def test_products_rollup(built):
    _, rc, _, _ = built
    assert rc.value("Products", "B4") == 2400
    assert rc.value("Products", "D4") == 10
    assert rc.value("Products", "E4") == pytest.approx(10 / 2400)
    assert rc.value("Products", "F4") == 4
    assert rc.value("Products", "G4") == 2250000
    assert rc.value("Products", "H4") == 1150000
    assert rc.value("Products", "I4") == pytest.approx(3400000 / 38000000)


# ---------------------------------------------------------------------------
# Seam 2: re-ingest · Seam 3: PII
# ---------------------------------------------------------------------------
def test_reingest_round_trip(tmp_path):
    wb, *_ = build_demo_retail_workbook()
    path = tmp_path / "retail.xlsx"
    path.write_bytes(workbook_bytes(wb))
    mart, findings = ingest_workbook(path)
    assert mart.engagement_id == "DEMO-2026-RET-01"
    assert [r["mart_id"] for r in mart.rows] == ["DEMO-2026-RET-01-P01"]
    row = mart.rows[0]
    assert row["product"] == "indirect_auto"
    assert row["substandard_dollars"] == 2250000
    assert row["loss_dollars"] == 1150000
    assert row["open_findings"] == 4
    assert findings.open_by_class == {"policy": 2, "documentation": 1, "compliance": 1}
    assert findings.total_open == 4
    assert findings.classified_dollars == 3400000   # URCCP: substandard + loss
    # de-identified: no loan numbers anywhere in the export
    dumped = json.dumps(mart.rows) + json.dumps(findings.records)
    for number in ("AU-10021", "AU-11760", "AU-14520"):
        assert number not in dumped


def test_mode_b_artifacts_carry_no_person_names_or_tins(built):
    wb, _, _, _ = built
    import io, re, zipfile
    data = workbook_bytes(wb)
    text = ""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith(".xml"):
                text += z.read(name).decode("utf-8", errors="ignore")
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", text)
    assert not re.search(r"\b\d{9}\b", text)
    # the Mode A synthetic borrowers must never bleed into Mode B artifacts
    for name in ("Blue Heron", "Maple Street", "Prairie Rose"):
        assert name not in text
    raw = (ENGAGEMENTS_DIR / "demo_retail_samples.yaml").read_text(encoding="utf-8")
    assert "name" not in yaml.safe_load(raw)["products"]["indirect_auto"]["files"][0]


def test_determinism():
    b1 = workbook_bytes(build_demo_retail_workbook()[0])
    b2 = workbook_bytes(build_demo_retail_workbook()[0])
    assert b1 == b2
