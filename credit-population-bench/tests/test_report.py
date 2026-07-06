"""Seam 1/4 — the HTML workpaper export renders all lenses and leaks no PII."""

from satc_credit_core import pii

from popbench.cli import demo_report_html


def test_report_has_all_sections():
    h = demo_report_html()
    for section in ("Delinquency distribution", "URCCP classification",
                    "Vintage analysis", "Derived cohorts", "Judgmental sample",
                    "OCC documentation", "NON-EXTRAPOLABLE", "risk gradient"):
        assert section in h, f"missing section: {section}"
    # both bases are labeled
    assert "count %" in h and "dollar %" in h


def test_report_is_deterministic():
    assert demo_report_html() == demo_report_html()


def test_report_carries_no_tin_pattern():
    # demo identities are synthetic loan numbers; a runtime report MAY carry PII,
    # but the shipped/demo one must not.
    pii.assert_no_tin(demo_report_html(), "demo workpaper")
