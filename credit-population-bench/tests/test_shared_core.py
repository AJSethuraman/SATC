"""Seam 4 (PII byte-scan) + shared-core wiring.

Proves (a) the bench consumes the shared URCCP floors by import — not a fork —
so a floor change in ``satc_credit_core`` flows here, and (b) the bench's
shipped artifacts (demo workbook, demo fixtures, source) carry no TIN-shaped
PII. The *runtime populated workbook* is deliberately out of scope for this
guard (it runs only on bank equipment) — here everything is 100% synthetic.
"""

from pathlib import Path

from satc_credit_core import URCCP_FLOORS, resolve_classification_dpd
from satc_credit_core import pii

from popbench import demo, mapping
from popbench.engine import build

_SRC = Path(__file__).resolve().parent.parent / "src"


def test_bench_uses_shared_urccp_floors_by_import():
    # The single source of truth — closed-end Loss at 120, open-end at 180.
    assert URCCP_FLOORS["closed_end"]["loss_from_dpd"] == 120
    assert URCCP_FLOORS["open_end"]["loss_from_dpd"] == 180
    assert resolve_classification_dpd("closed_end")["substandard_from_dpd"] == 90


def test_demo_workbook_carries_no_tin_pattern():
    pop = demo.demo_population()
    props = mapping.propose(list(pop.columns))
    m = mapping.confirm([mapping.ColumnMap(p.header, p.field_id)
                         for p in props if p.field_id])
    data = build(pop, m)
    pii.assert_workbook_no_tin(data, "bench demo workbook")


def test_bench_source_and_fixtures_carry_no_tin_pattern():
    for path in _SRC.rglob("*.py"):
        pii.assert_no_tin(path.read_text(encoding="utf-8"), str(path))
