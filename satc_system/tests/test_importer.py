"""Tests for the smart client importer (:mod:`satc.intake.importer`) and the
service-level import seam (:mod:`satc.intake.service`).

The importer turns a roster (CSV upload, Drake export, or a single typed entry)
into previewed :class:`ParsedClient` rows: detecting person vs business, inferring
the entity/return type, normalizing the SSN/EIN, and flagging likely duplicates.
Nothing is created until ``commit_import`` runs against the store.

Service tests use a fresh :class:`SATCStore` rooted at pytest's ``tmp_path``. That
store does NOT auto-seed, so the existing-client list starts empty and dedup only
fires on rows we feed it.
"""

from __future__ import annotations

from satc.intake import importer
from satc.intake.importer import ParsedClient
from satc.intake.service import commit_import, existing_client_index, preview_import
from satc.persistence import SATCStore


# ---------------------------------------------------------------------------
# parse_one / detection
# ---------------------------------------------------------------------------

def test_parse_one_detects_business_scorp_from_llc():
    pc = importer.parse_one(name="Reyes Studio LLC")
    assert pc.kind == "business"
    assert pc.entity_type == "SCORP"
    assert pc.display_name == "Reyes Studio LLC"


def test_parse_one_detects_partnership_from_llp_and_ampersand():
    pc = importer.parse_one(name="Smith & Jones Partners LLP")
    assert pc.kind == "business"
    assert pc.entity_type == "PARTNERSHIP"


def test_parse_one_detects_person_as_individual():
    pc = importer.parse_one(name="Dana Reyes")
    assert pc.kind == "person"
    assert pc.entity_type == "INDIVIDUAL"
    assert pc.first_name == "Dana"
    assert pc.last_name == "Reyes"


def test_looks_like_business_true_for_inc():
    assert importer.looks_like_business("Acme Inc") is True


def test_looks_like_business_false_for_person():
    assert importer.looks_like_business("Dana Reyes") is False


# ---------------------------------------------------------------------------
# TIN normalization
# ---------------------------------------------------------------------------

def test_parse_one_normalizes_tin_to_digits_and_last4():
    pc = importer.parse_one(name="Dana Reyes", tin="123-45-6789")
    assert pc.tin == "123456789"
    assert pc.tin_last4 == "6789"


# ---------------------------------------------------------------------------
# parse_csv — template + flexible headers
# ---------------------------------------------------------------------------

def test_parse_csv_template_yields_two_clients_with_correct_kinds():
    parsed = importer.parse_csv(importer.CSV_TEMPLATE)
    assert len(parsed) == 2

    dana, studio = parsed
    assert dana.kind == "person"
    assert dana.entity_type == "INDIVIDUAL"
    assert dana.tin, "person row should carry a normalized TIN"

    assert studio.kind == "business"
    assert studio.entity_type == "SCORP"
    assert studio.tin, "business row should carry a normalized TIN"


def test_parse_csv_flexible_headers_first_last_ssn_state():
    text = "First,Last,SSN,State\nDana,Reyes,123-45-6789,OH\n"
    parsed = importer.parse_csv(text)
    assert len(parsed) == 1

    pc = parsed[0]
    assert pc.kind == "person"
    assert pc.first_name == "Dana"
    assert pc.last_name == "Reyes"
    assert pc.tin == "123456789"
    assert pc.state == "OH"


# ---------------------------------------------------------------------------
# entity_type column override
# ---------------------------------------------------------------------------

def test_entity_type_column_forces_partnership_without_name_hint():
    # "Quiet Meadow" has no business token; the explicit type column drives it.
    text = "name,type\nQuiet Meadow,partnership\n"
    parsed = importer.parse_csv(text)
    assert len(parsed) == 1

    pc = parsed[0]
    assert pc.kind == "business"
    assert pc.entity_type == "PARTNERSHIP"


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------

def test_parse_csv_marks_repeat_row_within_batch_as_duplicate():
    text = "name,tin\nDana Reyes,111111111\nDana Reyes,222222222\n"
    parsed = importer.parse_csv(text)
    assert len(parsed) == 2
    assert parsed[0].status == "new"
    assert parsed[1].status == "duplicate"


def test_parse_csv_marks_match_against_existing_as_duplicate():
    text = "name\nDana Reyes\n"
    parsed = importer.parse_csv(text, existing=[("Dana Reyes", "6789")])
    assert parsed[0].status == "duplicate"


# ---------------------------------------------------------------------------
# issues / review
# ---------------------------------------------------------------------------

def test_short_tin_records_issue_and_marks_review():
    text = "name,tin\nDana Reyes,12345\n"
    parsed = importer.parse_csv(text)
    pc = parsed[0]
    assert pc.status == "review"
    assert pc.issues, "a 5-digit TIN should record an issue"
    assert any("5" in issue for issue in pc.issues)


def test_duplicate_status_wins_over_review():
    # A short-TIN row that also duplicates an existing client stays "duplicate".
    text = "name,tin\nDana Reyes,12345\n"
    parsed = importer.parse_csv(text, existing=[("Dana Reyes", "")])
    pc = parsed[0]
    assert pc.status == "duplicate"
    assert pc.issues, "the issue is still recorded even when deduped"


# ---------------------------------------------------------------------------
# service integration — preview_import / commit_import over a temp store
# ---------------------------------------------------------------------------

def test_preview_import_returns_parsed_clients_with_empty_existing(tmp_path):
    store = SATCStore(tmp_path)
    # SATCStore does NOT auto-seed, so there are no existing clients to dedup against.
    assert existing_client_index(store) == []

    parsed = preview_import(store, csv_text=importer.CSV_TEMPLATE)
    assert all(isinstance(pc, ParsedClient) for pc in parsed)
    assert len(parsed) == 2
    assert all(pc.status == "new" for pc in parsed)


def test_commit_import_creates_non_duplicate_clients(tmp_path):
    store = SATCStore(tmp_path)
    parsed = preview_import(store, csv_text=importer.CSV_TEMPLATE)
    non_dup = [pc for pc in parsed if pc.status != "duplicate"]

    before = len(store.load_mart().public_clients)
    created = commit_import(store, parsed)
    after = len(store.load_mart().public_clients)

    assert len(created) == len(non_dup)
    assert after - before == len(non_dup)

    # The freshly imported names show up in the vault.
    names = set(store.names().values())
    assert "Dana Reyes" in names
    assert "Reyes Studio LLC" in names

    # The business client's public projection is not an individual.
    entity_types = {pc.entity_type for pc in store.load_mart().public_clients}
    assert any(et != "INDIVIDUAL" for et in entity_types)


def test_commit_import_skips_duplicate_rows_unless_included(tmp_path):
    store = SATCStore(tmp_path)
    text = "name\nDana Reyes\nDana Reyes\n"
    parsed = preview_import(store, csv_text=text)
    assert [pc.status for pc in parsed] == ["new", "duplicate"]

    # By default the duplicate is skipped.
    created = commit_import(store, parsed)
    assert len(created) == 1

    # With include_duplicates=True the duplicate is created too.
    created_again = commit_import(store, parsed, include_duplicates=True)
    assert len(created_again) == 2
