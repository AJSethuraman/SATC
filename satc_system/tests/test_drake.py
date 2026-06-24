"""Tests for the Drake preparer-set parser, comms generator, and data-mart seed."""

from __future__ import annotations

from decimal import Decimal

from satc.drake import (
    build_delivery_summary,
    parse_preparer_set,
    render_cover_letter,
    render_delivery_email,
    seed_data_mart,
    summary_lines,
)
from satc.fixtures import synthetic_mart, synthetic_preparer_set_text


def _ps():
    return parse_preparer_set(synthetic_preparer_set_text(),
                              client_id="SATC-001000", tax_year=2024)


def test_parses_filing_instructions_per_jurisdiction():
    ps = _ps()
    by_juris = {fi.jurisdiction: fi for fi in ps.filing_instructions}
    assert set(by_juris) == {"US", "OH", "MI"}
    assert by_juris["US"].balance_due == 1767.0
    assert by_juris["OH"].refund == 300.0
    # Michigan is paper-filed with a mail-to address.
    assert by_juris["MI"].filing_method == "paper"
    assert "Lansing" in by_juris["MI"].mail_to


def test_parses_comparison_and_carryovers_with_provenance():
    ps = _ps()
    current = next(c for c in ps.comparison if c.year == 2024)
    assert current.values["wages"] == 145000.0
    assert current.values["agi"] == 202236.0
    kinds = {c.kind for c in ps.carryovers}
    assert {"CAP_LOSS_LT", "CHARITABLE", "STATE_OVERPAYMENT_APPLIED"} <= kinds
    # Every staged field carries the worksheet title as provenance.
    assert ps.staged is not None
    assert all(f.provenance.source_ref.worksheet_title for f in ps.staged.fields)
    # Parsed values are STAGED (must pass the gate before they are trusted).
    assert all(f.status == "STAGED" for f in ps.staged.fields)


def test_delivery_summary_aggregates_multi_state_and_paper_branch():
    summary = build_delivery_summary(_ps())
    assert summary.net_balance_due == 1767.0 + 245.0
    assert summary.net_refund == 300.0
    lines = "\n".join(summary_lines(summary))
    assert "Federal" in lines and "Ohio" in lines and "Michigan" in lines
    assert "PAPER FILED" in lines
    assert "Lansing" in lines  # paper-file mail-to surfaced to the client


def test_email_and_cover_letter_are_drafts_with_merge_fields():
    summary = build_delivery_summary(_ps())
    email = render_delivery_email(summary, salutation="Jordan", preparer_name="A. Sethuraman")
    assert "DRAFT" in email
    assert "8879" in email                      # signature instruction present
    assert "Jordan" in email                    # merge field filled
    assert "{" not in email                     # no unfilled placeholders
    letter = render_cover_letter(summary, salutation="Jordan")
    assert "Complex work, made clear" in letter


def test_seed_populates_mart_line_items_and_carryforwards():
    mart = synthetic_mart()
    before_li = len(mart.line_items)
    before_cf = len(mart.carryforwards)
    added = seed_data_mart(mart, _ps())
    assert added >= 1
    # Comparison wages for 2024 are now record-level data in the mart.
    assert any(li.line_code == "wages" and li.amount == Decimal("145000")
               for li in mart.line_items)
    assert len(mart.line_items) >= before_li
    assert len(mart.carryforwards) >= before_cf
