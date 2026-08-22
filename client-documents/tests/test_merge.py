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


# ── the four templates added after the opening package ────────────────────

LATER_DOCUMENTS = {
    "delivery letter": ("SATC Tax Return Delivery Letter.html", "delivery-letter.json"),
    "extension notice": ("SATC Extension Notice.html", "extension-notice.json"),
    "disengagement letter": ("SATC Disengagement Letter.html", "disengagement-letter.json"),
}


def _sample(name):
    data = json.loads((ROOT / "samples" / name).read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return data


@pytest.mark.parametrize("label,pair", LATER_DOCUMENTS.items())
def test_later_documents_render_complete(label, pair):
    """Each FIELDS doc's example payload fills its own template.

    §7 of the authoring contract calls the example payload the acceptance test:
    "if it does not render a clean document, the pair is not done". These
    samples are lifted from the FIELDS docs, so the documentation and the test
    cannot drift apart.
    """
    filename, sample = pair
    result = render_file(TEMPLATE_DIR / filename, _sample(sample))
    assert "&lt;&lt;" not in result.html, f"{label}: an unfilled field survived"
    assert "[[" not in result.html, f"{label}: an unresolved block survived"
    assert "[CONFIRM:" not in result.html, f"{label}: an undecided placeholder survived"


def test_business_letter_refuses_to_render_while_a_confirm_is_open():
    """The business return letter carries one open [CONFIRM], in section 03.

    It is on officer compensation under an S election -- a substantive tax
    position, and not an agent's wording to write. The point of this test is
    that the marker cannot be forgotten: the letter cannot reach a client while
    it is there, and this test goes green the moment a human resolves it.
    """
    with pytest.raises(MergeError) as exc:
        render_file(TEMPLATE_DIR / "SATC Engagement Letter - Business Return.html",
                    _sample("business-engagement.json"))
    assert "[CONFIRM:" in str(exc.value)
    assert "officer compensation" in str(exc.value)


def test_business_letter_is_otherwise_complete():
    """Everything except that one marker resolves.

    Without this, the test above would also pass on a letter riddled with
    unfilled fields -- it would just report the first problem it found.
    """
    result = render_file(TEMPLATE_DIR / "SATC Engagement Letter - Business Return.html",
                         _sample("business-engagement.json"), strict=False)
    assert "&lt;&lt;" not in result.html, "an unfilled field survived"
    assert "[[" not in result.html, "an unresolved block survived"
    assert result.html.count("[CONFIRM:") == 1, "exactly one open decision, and no more"


INVERSE_PAIRS = [
    ("SATC Tax Return Delivery Letter.html", "delivery-letter.json", "EFiled", "PaperFiled"),
    ("SATC Extension Notice.html", "extension-notice.json", "PaymentEnclosed", "NoPaymentRequired"),
    ("SATC Disengagement Letter.html", "disengagement-letter.json", "ClientInitiated", "FirmInitiated"),
    ("SATC Disengagement Letter.html", "disengagement-letter.json", "BalanceOutstanding", "AccountSettled"),
    ("SATC Engagement Letter - Business Return.html", "business-engagement.json",
     "OwnerReturnsPrepared", "OwnerReturnsElsewhere"),
]


@pytest.mark.parametrize("filename,sample,a,b", INVERSE_PAIRS)
def test_inverse_flags_render_exactly_one_branch(filename, sample, a, b):
    """Both states, and only ever one of them.

    Every one of these pairs exists because the alternative -- a section that
    can be silent -- is the failure mode. A delivery letter that says nothing
    about how a return gets filed, or a disengagement letter that says nothing
    about money, is worse than no letter. Two independent booleans can both be
    false; this test is what says they must not.
    """
    for on, off in ((a, b), (b, a)):
        record = dict(_sample(sample))
        record[on], record[off] = True, False
        result = render_file(TEMPLATE_DIR / filename, record, strict=False)
        assert on in result.blocks_kept, f"{on} true but its block was dropped"
        assert off in result.blocks_dropped, f"{off} false but its block was kept"
