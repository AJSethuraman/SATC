"""Sort + re-label a folder: clean names, by-type buckets, originals untouched."""

from __future__ import annotations

import pytest

pytest.importorskip("reportlab")
pytest.importorskip("pypdf")

from satc.fixtures import create_sample_folder  # noqa: E402
from satc.fixtures.sample_docs import write_sample_w2  # noqa: E402
from satc.ingest import sort_folder  # noqa: E402


def test_plan_relabels_and_buckets_by_type(tmp_path):
    src = create_sample_folder(tmp_path / "in")
    plan = sort_folder(src, apply=False)

    by_relpath = {it.original_name: it.new_relpath for it in plan.items}
    # The W-2 is re-labeled with its employer; bucketed under its type.
    assert by_relpath["W2_Buckeye_Manufacturing.pdf"] == "W-2/W-2 - Buckeye Manufacturing LLC.pdf"
    assert by_relpath["1099INT_Heartland_Bank.pdf"].startswith("1099-INT/1099-INT - Heartland Bank")
    assert by_relpath["Engagement_Letter.pdf"].startswith("Engagement letter/")


def test_preview_does_not_touch_disk(tmp_path):
    src = create_sample_folder(tmp_path / "in")
    plan = sort_folder(src, apply=False)

    assert plan.applied is False
    assert not (src / "_SATC_Sorted").exists()
    assert all(not it.copied for it in plan.items)


def test_apply_copies_into_clean_tree_and_keeps_originals(tmp_path):
    src = create_sample_folder(tmp_path / "in")
    dest = tmp_path / "sorted"
    plan = sort_folder(src, dest, apply=True)

    assert plan.applied is True
    # Clean copies exist...
    assert (dest / "W-2" / "W-2 - Buckeye Manufacturing LLC.pdf").exists()
    assert (dest / "1099-INT").is_dir()
    # ...and every original is still right where it was.
    assert (src / "W2_Buckeye_Manufacturing.pdf").exists()
    assert (src / "Engagement_Letter.pdf").exists()


def test_misnamed_file_is_sorted_by_content(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    write_sample_w2(src / "scan0012.pdf")        # really a W-2
    plan = sort_folder(src, apply=False)

    item = next(it for it in plan.items if it.original_name == "scan0012.pdf")
    assert item.label == "W-2"
    assert item.method == "form fields"
    assert item.new_relpath == "W-2/W-2 - Buckeye Manufacturing LLC.pdf"
