"""Combined-PDF splitting: per-page classify, segment, split (non-destructive)."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")

from satc.fixtures.sample_docs import (  # noqa: E402
    TEXT_1099INT,
    TEXT_ENGAGEMENT,
    TEXT_W2,
    write_combined_pdf,
)
from satc.ingest import load_classifier, plan_split, sort_folder, split_to_dir  # noqa: E402
from satc.ingest.classify import UNCLASSIFIED, Classification  # noqa: E402
from satc.ingest.split import segment_pages  # noqa: E402


def _combined(tmp_path):
    p = tmp_path / "scan_stack.pdf"
    write_combined_pdf(p, [TEXT_W2, TEXT_1099INT, TEXT_ENGAGEMENT])
    return p


def test_plan_split_finds_each_form(tmp_path):
    segs = plan_split(_combined(tmp_path), load_classifier(has_key=False))
    assert [s.classification.label for s in segs] == ["W-2", "1099-INT", "Engagement letter"]
    assert all(s.start == s.end for s in segs)          # one page each


def test_continuation_page_attaches_to_preceding_form():
    w2 = Classification("W-2", "w2", "W-2", "HIGH", "text")
    intc = Classification("1099-INT", "1099int", "1099-INT", "HIGH", "text")
    segs = segment_pages([w2, UNCLASSIFIED, intc])       # a blank/illegible middle page
    assert len(segs) == 2
    assert (segs[0].start, segs[0].end) == (0, 1)        # blank page stayed with the W-2
    assert (segs[1].start, segs[1].end) == (2, 2)


def test_split_to_dir_writes_parts_and_keeps_original(tmp_path):
    src = _combined(tmp_path)
    parts = split_to_dir(src, tmp_path / "out", load_classifier(has_key=False))
    assert len(parts) == 3
    assert all(fp.exists() for _, fp in parts)
    assert src.exists()                                  # original untouched


def test_single_form_pdf_is_not_split(tmp_path):
    from satc.fixtures.sample_docs import write_text_form
    p = tmp_path / "just_a_w2.pdf"
    write_text_form(p, TEXT_W2)
    assert plan_split(p, load_classifier(has_key=False)) == []   # one form => no split


def test_sorter_splits_a_combined_pdf(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    write_combined_pdf(src / "scan_stack.pdf", [TEXT_W2, TEXT_1099INT, TEXT_ENGAGEMENT])
    plan = sort_folder(src, apply=True, classifier=load_classifier(has_key=False))

    rels = sorted(it.new_relpath for it in plan.items)
    assert any(r.startswith("W-2/") for r in rels)
    assert any(r.startswith("1099-INT/") for r in rels)
    assert all(it.pages is not None for it in plan.items)        # every item is a split part
    assert (src / "_SATC_Sorted" / "W-2").is_dir()


def test_intake_reads_a_combined_pdf(tmp_path):
    from satc.app.state import AppState
    src = tmp_path / "Clients" / "2024"
    src.mkdir(parents=True)
    write_combined_pdf(src / "scan_stack.pdf", [TEXT_W2, TEXT_1099INT, TEXT_ENGAGEMENT])

    summary = AppState().run_intake(str(src))
    assert summary["files_read"] == 2                    # W-2 + 1099-INT read; engagement filed
    assert any("split into 3" in n for n in summary["notes"])
