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
    assert [p["id"] for p in program.products] == ["indirect_auto", "credit_card",
                                                   "heloc"]
    # library tests resolved onto the product; card overrides the knob key
    auto_tests = {t["id"]: t for t in program.products[0]["tests"]}
    assert auto_tests["dti_within_policy"]["kind"] == "computed"
    assert auto_tests["reg_z_disclosures_present"]["class"] == "compliance"
    card_tests = {t["id"]: t for t in program.products[1]["tests"]}
    assert "[POL dti_ceiling_card]" in card_tests["dti_within_policy"]["when"]
    assert card_tests["dti_within_policy"]["class"] == "policy"   # inherited
    assert wb.sheetnames == ["Cover", "PS_indirect_auto", "PS_credit_card",
                             "PS_heloc", "Products", "Data Mart", "Findings",
                             "_methodology", "_config", "_readme", "_map"]
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
    # grid: A loan, B segment, C-G attrs (balance first), tests from H
    assert rc.value(PS, f"H{GRID['AU-11760']}") == "fail"     # dti 47%
    assert rc.value(PS, f"H{GRID['AU-10021']}") == "pass"
    assert rc.value(PS, f"J{GRID['AU-12233']}") == "fail"     # ltv 128%
    assert rc.value(PS, f"I{GRID['AU-14520']}") == "pass"     # score 668 >= floor
    assert rc.value(PS, f"K{GRID['AU-14520']}") == "pass"     # term 72 <= 72


def test_fringe_flag_marks_the_buy_box_edge_only(built):
    _, rc, _, _ = built
    fringe = {n: rc.value(PS, f"S{r}") for n, r in GRID.items()}
    assert fringe["AU-14520"] == "FRINGE" and fringe["AU-15084"] == "FRINGE"
    # out-of-box files are conformance fails, not fringe
    assert fringe["AU-11760"] in ("", None)    # dti 47% is outside, not edge
    assert fringe["AU-12233"] in ("", None)    # ltv 128% is outside
    assert fringe["AU-10021"] in ("", None)


def test_fails_helper_counts_row_failures(built):
    _, rc, _, _ = built
    assert rc.value(PS, f"R{GRID['AU-11760']}") == 2   # dti + income
    assert rc.value(PS, f"R{GRID['AU-15084']}") == 1   # Reg Z
    assert rc.value(PS, f"R{GRID['AU-12904']}") == 0


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
    # Hand-tallied across all three products (see the samples fixture header)
    assert agg("policy") == 6          # auto dti+ltv, card score+dti, heloc dti+cltv
    assert agg("documentation") == 2   # auto income, card re-aging
    assert agg("compliance") == 2      # auto Reg Z, heloc flood (per-occurrence)
    assert agg("rating") == 0          # not a Mode B class
    assert agg("high") == 6 and agg("medium") == 4
    assert agg("indirect_auto") == 4
    assert agg("credit_card") == 3
    assert agg("heloc") == 3
    assert agg("TOTAL open") == 10
    assert rc.value("Findings", f"B{labels['Substandard $ (portfolio)']}") \
        == 2250000 + 285000 + 780000
    assert rc.value("Findings", f"B{labels['Loss $ (portfolio)']}") \
        == 1150000 + 40000 + 95000


def test_products_rollup(built):
    _, rc, _, _ = built
    # row 4 = indirect_auto, 5 = credit_card, 6 = heloc
    assert rc.value("Products", "B4") == 2400
    assert rc.value("Products", "D4") == 10
    assert rc.value("Products", "E4") == pytest.approx(10 / 2400)
    assert rc.value("Products", "F4") == 4
    assert rc.value("Products", "G4") == 2250000
    assert rc.value("Products", "H4") == 1150000
    assert rc.value("Products", "I4") == pytest.approx(3400000 / 38000000)
    assert rc.value("Products", "F5") == 3
    assert rc.value("Products", "G5") == 285000     # open-end Substandard >=90
    assert rc.value("Products", "H5") == 40000      # open-end Loss >=180 only
    assert rc.value("Products", "F6") == 3
    assert rc.value("Products", "G6") == 780000     # resi qualifying >=90 w/ LTV>60%
    assert rc.value("Products", "H6") == 95000      # resi Loss = keyed writedowns
    # coverage in dollars beside coverage in count (OCC documentation basis)
    assert rc.value("Products", "J4") == 212000
    assert rc.value("Products", "K4") == pytest.approx(212000 / 38000000)
    assert rc.value("Products", "J5") == 38000
    assert rc.value("Products", "J6") == 545000


def test_dual_basis_delinquency_rates(built):
    wb, rc, _, _ = built
    ws = wb[PS]
    rows = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 1).value}
    # count basis in B, dollar basis in C -- both always shown
    r30 = rows["30+ DPD rate"]
    assert rc.value(PS, f"B{r30}") == pytest.approx(400 / 2400)
    assert rc.value(PS, f"C{r30}") == pytest.approx(6600000 / 38000000)
    r90 = rows["90+ DPD rate"]
    assert rc.value(PS, f"B{r90}") == pytest.approx(130 / 2400)
    assert rc.value(PS, f"C{r90}") == pytest.approx(2250000 / 38000000)
    card = wb["PS_credit_card"]
    crows = {card.cell(r, 1).value: r for r in range(1, card.max_row + 1)
             if card.cell(r, 1).value}
    c90 = crows["90+ DPD rate"]
    assert rc.value("PS_credit_card", f"B{c90}") == pytest.approx(175 / 5765)
    assert rc.value("PS_credit_card", f"C{c90}") == pytest.approx(285000 / 10015000)


def test_timeliness_attestations_stay_silent_with_no_applicable_files(built):
    wb, rc, _, _ = built
    rows = _analytics_rows(wb[PS])
    for label in ("Bankruptcy charge-off within 60 days",
                  "Fraud charge-off within 90 days"):
        r = rows[label]
        assert rc.value(PS, f"D{r}") == 0            # all na in the demo sample
        assert rc.value(PS, f"H{r}") in ("", None)   # no phantom finding


# ---------------------------------------------------------------------------
# Seam 2: re-ingest · Seam 3: PII
# ---------------------------------------------------------------------------
def test_reingest_round_trip(tmp_path):
    wb, *_ = build_demo_retail_workbook()
    path = tmp_path / "retail.xlsx"
    path.write_bytes(workbook_bytes(wb))
    mart, findings = ingest_workbook(path)
    assert mart.engagement_id == "DEMO-2026-RET-01"
    assert [r["mart_id"] for r in mart.rows] == [
        "DEMO-2026-RET-01-P01", "DEMO-2026-RET-01-P02", "DEMO-2026-RET-01-P03"]
    by_product = {r["product"]: r for r in mart.rows}
    assert by_product["indirect_auto"]["substandard_dollars"] == 2250000
    assert by_product["indirect_auto"]["open_findings"] == 4
    assert by_product["credit_card"]["loss_dollars"] == 40000
    assert by_product["heloc"]["substandard_dollars"] == 780000
    assert by_product["indirect_auto"]["sample_dollars"] == 212000
    assert findings.open_by_class == {"policy": 6, "documentation": 2, "compliance": 2}
    assert findings.total_open == 10
    assert findings.classified_dollars == 3315000 + 1285000   # URCCP: sub + loss
    # de-identified: no loan numbers anywhere in the export
    dumped = json.dumps(mart.rows) + json.dumps(findings.records)
    for number in ("AU-10021", "AU-11760", "CC-2593", "HE-7515"):
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


# ---------------------------------------------------------------------------
# Slice 2 (#74): fringe-vs-core, segment analytics, floor validation
# ---------------------------------------------------------------------------
def _label_rows(ws):
    return {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 1).value}


def test_fringe_vs_core_norms_block(built):
    wb, rc, _, _ = built
    rows = _label_rows(wb[PS])
    # auto: both fringe files fail >=1 (income; Reg Z) vs 3 of 8 core files
    assert rc.value(PS, f"B{rows['Fringe files (n)']}") == 2
    assert rc.value(PS, f"B{rows['Fringe fail-any rate']}") == pytest.approx(1.0)
    assert rc.value(PS, f"B{rows['Core fail-any rate']}") == pytest.approx(3 / 8)
    assert rc.value(PS, f"B{rows['Gap (fringe - core)']}") == pytest.approx(0.625)
    assert rc.value(
        PS, f"B{rows['Fringe above margin?']}") == OPEN_FLAG
    # card: fringe files are clean -> negative gap -> no flag
    card_rows = _label_rows(wb["PS_credit_card"])
    assert rc.value("PS_credit_card",
                    f"B{card_rows['Fringe fail-any rate']}") == pytest.approx(0.0)
    assert rc.value(
        "PS_credit_card",
        f"B{card_rows['Fringe above margin?']}") == CLEAR_FLAG


def test_segment_analytics_by_stratum(built):
    wb, rc, _, _ = built
    ws = wb[PS]
    seg_rows = {ws.cell(r, 1).value: r for r in range(1, ws.max_row + 1)
                if ws.cell(r, 1).value in ("rand_large", "rand_small", "judg_fringe")}
    # stratified random 90/10: both strata sampled to plan; analytics live
    assert rc.value(PS, f"D{seg_rows['rand_large']}") == 5
    assert rc.value(PS, f"E{seg_rows['rand_large']}") == 2      # AU-11760, AU-12233
    assert rc.value(PS, f"F{seg_rows['rand_large']}") == pytest.approx(2 / 5)
    assert rc.value(PS, f"D{seg_rows['rand_small']}") == 3
    assert rc.value(PS, f"E{seg_rows['rand_small']}") == 1      # AU-13311
    assert rc.value(PS, f"D{seg_rows['judg_fringe']}") == 2
    assert rc.value(PS, f"E{seg_rows['judg_fringe']}") == 2


def test_urccp_open_end_and_residential_branches(built):
    wb, rc, _, _ = built
    card = _label_rows(wb["PS_credit_card"])
    assert rc.value("PS_credit_card", f"B{card['Substandard (>=90 DPD)']}") == 175
    assert rc.value("PS_credit_card", f"C{card['Substandard (>=90 DPD)']}") == 285000
    assert rc.value("PS_credit_card", f"B{card['Loss (>=180 DPD)']}") == 25
    assert rc.value("PS_credit_card", f"C{card['Loss (>=180 DPD)']}") == 40000
    heloc = _label_rows(wb["PS_heloc"])
    assert rc.value("PS_heloc",
                    f"C{heloc['Substandard (qualifying >=90 DPD)']}") == 780000
    assert rc.value("PS_heloc", f"C{heloc['Loss (writedowns)']}") == 95000


def test_heloc_attestation_with_no_applicable_files_stays_silent(built):
    wb, rc, _, _ = built
    ws = wb["PS_heloc"]
    rows = _analytics_rows(ws)
    r = rows["180-day writedown evidenced"]
    assert rc.value("PS_heloc", f"D{r}") == 0        # all na -> n = 0
    assert rc.value("PS_heloc", f"H{r}") in ("", None)   # no rate -> no finding


def test_urccp_floor_cannot_be_loosened(tmp_path):
    program = load_program(PROGRAMS_DIR / "retail.yaml")
    base = yaml.safe_load(
        (ENGAGEMENTS_DIR / "demo_retail_engagement.yaml").read_text(encoding="utf-8"))
    base["products"]["indirect_auto"]["classification_overrides"] = \
        {"loss_from_dpd": 180}   # later than the closed-end 120-day floor
    base["samples"] = str(ENGAGEMENTS_DIR / "demo_retail_samples.yaml")
    p = tmp_path / "loose.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    engagement = load_engagement(p)
    samples = load_samples(engagement.samples_path, program.products,
                           engagement.overlay_products)
    with pytest.raises(ConfigError, match="LOOSEN"):
        build_engagement_workbook(program, engagement, samples)


def test_urccp_clock_may_be_tightened(tmp_path):
    program = load_program(PROGRAMS_DIR / "retail.yaml")
    base = yaml.safe_load(
        (ENGAGEMENTS_DIR / "demo_retail_engagement.yaml").read_text(encoding="utf-8"))
    base["products"]["indirect_auto"]["classification_overrides"] = \
        {"substandard_from_dpd": 60}   # stricter than URCCP: allowed
    base["samples"] = str(ENGAGEMENTS_DIR / "demo_retail_samples.yaml")
    p = tmp_path / "tight.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    engagement = load_engagement(p)
    samples = load_samples(engagement.samples_path, program.products,
                           engagement.overlay_products)
    wb = build_engagement_workbook(program, engagement, samples)
    rc = Recalc(workbook_bytes(wb))
    rows = _label_rows(wb[PS])
    # 60-89 bucket now joins Substandard: 90 + 130 = 220 / $1.45M + $2.25M
    assert rc.value(PS, f"B{rows['Substandard (>=60 DPD)']}") == 220
    assert rc.value(PS, f"C{rows['Substandard (>=60 DPD)']}") == 3700000


def test_methodology_and_readme_mode_b(built):
    wb, rc, program, _ = built
    ws = wb["_methodology"]
    text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    assert "65 FR 36903" in text                      # URCCP cited
    assert "retail_classification" in text
    assert "fringe_analysis" in text
    assert "rand_large" in text and "judg_fringe" in text   # sampling design
    assert "90/10 allocation" in text
    for entry in program.crosswalk:
        assert entry["element"] in text
    rows = {str(ws.cell(r, 1).value): r for r in range(1, ws.max_row + 1)}
    cov = rows["indirect_auto"]
    assert rc.value("_methodology", f"D{cov}") == pytest.approx(10 / 2400)
    readme = " ".join(str(c.value) for row in wb["_readme"].iter_rows()
                      for c in row if c.value)
    assert "no individual-person names" in readme
