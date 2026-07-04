"""Tests for the extraction engine + staging/confirmation gate (Stage 1)."""

from __future__ import annotations

from decimal import Decimal

from satc.config import load_extraction_map
from satc.ingest import MAPPING_1040, MapExtractor, StagingGate
from satc.ingest.extractors.base import parse_money
from satc.fixtures import synthetic_documents


def _gate_from_synthetic() -> StagingGate:
    gate = StagingGate()
    for doc in synthetic_documents():
        cfg = load_extraction_map(doc["doc_key"])
        staged = MapExtractor(cfg).extract(
            document_id=doc["document_id"], client_id="SATC-001000",
            tax_year=2024, labeled_fields=doc["labeled"])
        gate.add(staged)
    return gate


def test_parse_money_conservative():
    assert parse_money("1,200.00")[0] == Decimal("1200.00")
    assert parse_money("(500)")[0] == Decimal("-500")
    amt, conf, _ = parse_money("see stub")
    assert amt is None and conf == "UNCERTAIN"


def test_sensitive_fields_are_masked_never_full():
    cfg = load_extraction_map("w2")
    staged = MapExtractor(cfg).extract(
        document_id="DOC-X", client_id="SATC-001000", tax_year=2024,
        labeled_fields={"Employer EIN": "31-0009999", "Employee SSN": "400-55-1234"})
    by_path = {f.field_path: f for f in staged.fields}
    assert by_path["w2.employer_ein"].value_text == "**-***9999"
    assert by_path["w2.employee_ssn"].value_text == "***-**-1234"
    # The full TIN must appear nowhere in the staged record.
    assert "0009999" not in by_path["w2.employer_ein"].value_text


def test_malformed_money_routes_to_review_not_guessed():
    gate = _gate_from_synthetic()
    qual = next(f for f in gate.all_fields() if f.field_path == "div.box1b_qualified")
    assert qual.status == "NEEDS_REVIEW"
    assert qual.value_amount is None


def test_auto_confirm_only_high_confidence():
    gate = _gate_from_synthetic()
    confirmed = gate.auto_confirm_high()
    assert confirmed > 0
    # The malformed field stays in review.
    assert any(f.field_path == "div.box1b_qualified" for f in gate.needs_review())
    # A clean money field is confirmed.
    wages = [f for f in gate.confirmed() if f.field_path == "w2.box1_wages"]
    assert wages


def test_aggregation_sums_two_w2s_into_wages():
    gate = _gate_from_synthetic()
    gate.auto_confirm_high()
    values = gate.to_line_values(MAPPING_1040)
    # 98,000 + 47,000 across two W-2s
    assert values["wages"] == 145000.0
    assert values["fed_wh_w2"] == 18000.0
    assert values["interest"] == 1200.0
    assert values["filing_status"] == "MFJ"
    # The unconfirmed qualified dividend did not flow through.
    assert "dividends_qual" not in values
