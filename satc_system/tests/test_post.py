"""The last hop: confirmed intake values post onto the return + data mart."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")
pytest.importorskip("flask")

from satc.app.state import AppState  # noqa: E402
from satc.fixtures import create_sample_folder  # noqa: E402
from satc.ids import line_item_key, return_key  # noqa: E402

RK = return_key("SATC-001000", 2024, "1040", "US")


def test_confirmed_intake_posts_line_items(tmp_path):
    folder = create_sample_folder(tmp_path / "docs")
    state = AppState()
    state.run_intake(str(folder))            # reads + auto-confirms HIGH-confidence
    summary = state.post_confirmed()

    assert summary["return_key"] == RK
    assert summary["posted"] >= 2

    items = {li.line_item_key: li for li in state.mart.line_items if li.return_key == RK}
    assert float(items[line_item_key(RK, "1040", "1a")].amount) == 98000.0   # wages
    assert float(items[line_item_key(RK, "1040", "2b")].amount) == 1200.0    # interest
    # Posted facts keep a source-document provenance (never unsourced).
    assert items[line_item_key(RK, "1040", "1a")].provenance.source_kind == "SOURCE_DOC"


def test_posting_is_idempotent(tmp_path):
    folder = create_sample_folder(tmp_path / "docs")
    state = AppState()
    state.run_intake(str(folder))
    state.post_confirmed()
    before = len([li for li in state.mart.line_items if li.return_key == RK])
    state.post_confirmed()                   # re-post the same confirmed values
    after = len([li for li in state.mart.line_items if li.return_key == RK])
    assert before == after


def test_no_full_tin_reaches_the_mart(tmp_path):
    folder = create_sample_folder(tmp_path / "docs")
    state = AppState()
    state.run_intake(str(folder))
    state.post_confirmed()
    blob = " ".join((li.text_value or "") + str(li.amount) for li in state.mart.line_items)
    assert "400551234" not in blob and "400-55-1234" not in blob
