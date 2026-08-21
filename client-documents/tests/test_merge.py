"""The merge engine, tested against the real templates.

The claim under test is the one the templates make about themselves: a document
either comes out complete, or it does not come out at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from merge import MergeError, render, render_file  # noqa: E402

TEMPLATE_DIR = ROOT.parent / "satc-handoff" / "04-TEMPLATES"
OPENING_PACKAGE = {
    "tax letter": "SATC Engagement Letter - Tax Preparation.html",
    "fee estimate": "SATC Fee Estimate.html",
    "onboarding letter": "SATC Onboarding Letter.html",
}


@pytest.fixture(scope="module")
def record():
    data = json.loads((ROOT / "samples" / "tax-opening-package.json").read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return data


# ── the whole point ───────────────────────────────────────────────────────

@pytest.mark.parametrize("label,filename", OPENING_PACKAGE.items())
def test_opening_package_renders_complete(record, label, filename):
    """One record fills all three documents with nothing left unresolved."""
    result = render_file(TEMPLATE_DIR / filename, record)
    assert "&lt;&lt;" not in result.html, f"{label}: an unfilled field survived"
    assert "[[" not in result.html, f"{label}: an unresolved block survived"
    assert "[CONFIRM:" not in result.html, f"{label}: an undecided placeholder survived"


def test_shared_values_are_identical_across_the_package(record):
    """The reason to generate the three together is that they cannot disagree."""
    rendered = {k: render_file(TEMPLATE_DIR / v, record).html for k, v in OPENING_PACKAGE.items()}
    for shared in ("2027-0114", "February 3, 2027", "418 Rockwell Street"):
        present = [k for k, h in rendered.items() if shared in h]
        assert len(present) >= 2, f"{shared!r} should appear in the package, found in {present}"


def test_materials_deadline_matches_across_documents(record):
    """The organizer's field doc calls a mismatch here its most likely bug."""
    deadline = record["MaterialsDeadline"]
    for label, filename in OPENING_PACKAGE.items():
        html = render_file(TEMPLATE_DIR / filename, record).html
        if "deadline" in html.lower() or label != "fee estimate":
            pass  # only the letter and onboarding print it
    tax = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    onb = render_file(TEMPLATE_DIR / OPENING_PACKAGE["onboarding letter"], record).html
    assert deadline in tax and deadline in onb


# ── failure is loud ───────────────────────────────────────────────────────

def test_missing_field_raises_rather_than_shipping(record):
    holed = dict(record)
    del holed["ClientLetterName"]
    with pytest.raises(MergeError) as e:
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], holed)
    assert "ClientLetterName" in str(e.value)


def test_confirm_placeholder_cannot_reach_a_client(record):
    undecided = dict(record)
    undecided["ReturnInstruction"] = "[CONFIRM: how do they return it?]"
    with pytest.raises(MergeError) as e:
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], undecided)
    assert "CONFIRM" in str(e.value)


def test_a_list_must_be_a_list(record):
    broken = dict(record)
    broken["LineItems"] = "Federal Form 1040 — $450"
    with pytest.raises(MergeError):
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], broken)


# ── behaviour of the markers ──────────────────────────────────────────────

def test_conditional_block_is_dropped_when_false(record):
    joint = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    assert "Maria Reyes" in joint

    single = dict(record, JointReturn=False)
    single.pop("SpouseName")
    out = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], single)
    assert "Maria Reyes" not in out.html
    assert "JointReturn" in out.blocks_dropped
    assert "both spouses" not in out.html.lower(), "the joint-representation note should go too"


def test_each_repeats_once_per_item(record):
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], record).html
    for item in record["LineItems"]:
        assert item["Service"] in html
    assert html.count("$450") >= 1


def test_empty_detail_renders_empty_not_none(record):
    """The field docs are explicit: an empty Item.Detail is '', never 'None'."""
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], record).html
    assert "Solon municipal return" in html
    assert ">None<" not in html


# ── escaping ──────────────────────────────────────────────────────────────

def test_values_are_escaped(record):
    ampersand = dict(record, ClientFullName="Ross & Sons")
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], ampersand).html
    assert "Ross &amp; Sons" in html
    assert "Ross & Sons" not in html


def test_a_value_cannot_inject_markup(record):
    hostile = dict(record, ClientLetterName='<script>alert(1)</script>')
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], hostile).html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# ── the proof chrome never ships ──────────────────────────────────────────

def test_field_chrome_is_stripped(record):
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    assert 'class="f"' not in html, "merge-field styling should not reach a client"
    assert 'class="cond"' not in html, "conditional markers should not reach a client"


def test_screen_only_reference_block_is_removed(record):
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    assert 'class="ref"' not in html
    assert "Merge fields" not in html, "the field documentation must never reach a client"
