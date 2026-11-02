"""The 2026 table holds the law as enacted -- checked against Rev. Proc. 2025-32.

`configs/crosswalk/federal/2026.yaml` was a TCJA-sunset test fixture until
17 October 2026, and the estimator ran every 2026 estimate on 2025 figures. It
now carries the 2026 figures. These are LITERALS from the revenue procedure and
the 2026 Form 1040-ES, held here so the file can disagree with them.

THE BRACKETS ARE CHECKED TWICE. Each table in Rev. Proc. 2025-32 sec. 4.01 also
prints the tax at the start of every band ("$11,600 plus 22% of the excess over
$100,800"). Running the brackets the file holds must reproduce every one of those
printed amounts, so a threshold mistyped in the file cannot pass -- that is a
second reading of the same document, not the file agreeing with itself.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from satc.withholding.engine import _bracket_tax
from satc.withholding.tax_data import load_tax_tables

D = Decimal

#: Rev. Proc. 2025-32 sec. 4.01: (threshold, tax printed at that threshold).
PRINTED = {
    "married_jointly": [(24800, "2480"), (100800, "11600"), (211400, "35932"),
                        (403550, "82048"), (512450, "116896"), (768700, "206583.50")],
    "head_of_household": [(17700, "1770"), (67450, "7740"), (105700, "16155"),
                          (201750, "39207"), (256200, "56631"), (640600, "191171")],
    "single": [(12400, "1240"), (50400, "5800"), (105700, "17966"),
               (201775, "41024"), (256225, "58448"), (640600, "192979.25")],
    "married_separately": [(12400, "1240"), (50400, "5800"), (105700, "17966"),
                           (201775, "41024"), (256225, "58448"), (384350, "103291.75")],
}


@pytest.mark.parametrize("status", sorted(PRINTED))
def test_the_brackets_reproduce_every_printed_amount(status):
    tables, _ = load_tax_tables(2026)
    brackets = tables.ordinary_brackets(status)
    assert [b.up_to for b in brackets[:-1]] == [D(t) for t, _ in PRINTED[status]]
    for threshold, printed in PRINTED[status]:
        assert _bracket_tax(D(threshold), brackets) == D(printed), (status, threshold)


def test_the_headline_figures():
    t, _ = load_tax_tables(2026)
    # Rev. Proc. 2025-32 sec. 4.14; Form 1040-ES (2026)
    assert [t.standard_deduction(s) for s in ("single", "married_jointly", "married_separately",
                                              "head_of_household")] == [D(16100), D(32200), D(16100), D(24150)]
    assert t.extra_standard_deduction("single") == D(2050)
    assert t.extra_standard_deduction("married_jointly") == D(1650)
    # sec. 4.03
    assert t.capital_gains_thresholds("married_jointly") == (D(98900), D(613700))
    assert t.capital_gains_thresholds("single") == (D(49450), D(545500))
    # sec. 4.05; Form 1040-ES (2026)
    assert (t.ctc_per_child, t.actc_max_per_child) == (D(2200), D(1700))
    assert t.ss_wage_base == D(184500)
    # IRC 164(b)(7)
    assert (t.salt_cap, t.salt_phasedown_threshold) == (D(40400), D(505000))
    assert t.est_tax_due_dates == ["2026-04-15", "2026-06-15", "2026-09-15", "2027-01-15"]
