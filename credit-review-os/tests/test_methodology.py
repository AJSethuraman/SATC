"""Slice 6 (issue #65): the _methodology crosswalk + engagement evidence.

Every program element appears in the crosswalk with a non-empty citation; the
engagement's coverage/scope, independence attestation, and findings-to-board
reporting populate from the overlay; _readme carries the pin-cite caveat and
the PII notes.
"""

import pytest

from credit_review import build_demo_workbook, load_program, workbook_bytes
from credit_review.config import ConfigError
from credit_review.methodology import PII_NOTES, PIN_CITE_CAVEAT
from credit_review.workbook import PROGRAMS_DIR

from recalc import Recalc

# The canonical program elements a defensible review program must prove out.
REQUIRED_ELEMENTS = {
    "risk_rating_framework", "independent_rating_validation", "exception_tracking",
    "evidence_currency", "appraisal_validity", "sampling_scope", "independence",
    "findings_reporting",
}


@pytest.fixture(scope="module")
def built():
    wb, program, engagement, loans = build_demo_workbook()
    return wb, program, engagement, loans


def test_crosswalk_covers_every_element_with_citation(built):
    _, program, _, _ = built
    elements = {e["element"] for e in program.crosswalk}
    assert REQUIRED_ELEMENTS <= elements
    for entry in program.crosswalk:
        assert entry["requirement"].strip(), entry["element"]
        assert entry["source"].strip(), entry["element"]


def test_methodology_tab_renders_the_full_crosswalk(built):
    wb, program, _, _ = built
    ws = wb["_methodology"]
    col_a = [str(ws.cell(r, 1).value or "") for r in range(1, ws.max_row + 1)]
    for entry in program.crosswalk:
        assert entry["element"] in col_a, entry["element"]
        r = col_a.index(entry["element"]) + 1
        assert ws.cell(r, 3).value == entry["requirement"]
        assert ws.cell(r, 4).value == entry["source"]


def test_coverage_scope_populates_and_computes_live(built):
    wb, _, engagement, loans = built
    ws = wb["_methodology"]
    rows = {str(ws.cell(r, 1).value or ""): r for r in range(1, ws.max_row + 1)}
    assert ws.cell(rows["Portfolio (dollars)"], 2).value == 42000000
    assert ws.cell(rows["Reviewed (count)"], 2).value == len(loans) == 4
    assert ws.cell(rows["Sampling basis"], 2).value == engagement.scope["sample_basis"]
    # reviewed-$ and coverage-% are live formulas over the Master roll-up
    assert str(ws.cell(rows["Reviewed (dollars, live)"], 2).value).startswith("=SUM(Master!")
    rc = Recalc(workbook_bytes(wb))
    reviewed = rc.value("_methodology", f"B{rows['Reviewed (dollars, live)']}")
    assert reviewed == 1750000 + 900000 + 2600000 + 800000
    coverage = rc.value("_methodology", f"B{rows['Coverage (% of portfolio $)']}")
    assert coverage == pytest.approx(6050000 / 42000000)


def test_independence_attestation_populates(built):
    wb, _, engagement, _ = built
    ws = wb["_methodology"]
    rows = {str(ws.cell(r, 1).value or ""): r for r in range(1, ws.max_row + 1)}
    assert ws.cell(rows["Reviewer"], 2).value == "SATC"
    assert ws.cell(rows["Independent"], 2).value == "Yes"
    assert "lending authority" in ws.cell(rows["Basis"], 2).value


def test_reporting_section_and_pin_cite_caveat(built):
    wb, _, _, _ = built
    text = " ".join(str(c.value) for row in wb["_methodology"].iter_rows()
                    for c in row if c.value)
    assert "Findings-to-board reporting" in text
    assert PIN_CITE_CAVEAT in text


def test_readme_carries_caveat_and_pii_notes(built):
    wb, _, _, _ = built
    text = " ".join(str(c.value) for row in wb["_readme"].iter_rows()
                    for c in row if c.value)
    assert PIN_CITE_CAVEAT in text
    assert PII_NOTES in text


def test_uncited_crosswalk_entry_fails_validation(tmp_path):
    import yaml
    base = yaml.safe_load((PROGRAMS_DIR / "c_and_i.yaml").read_text(encoding="utf-8"))
    base["crosswalk"].append({"element": "orphan", "requirement": "something",
                              "source": ""})
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(base), encoding="utf-8")
    with pytest.raises(ConfigError, match="cited"):
        load_program(p)
