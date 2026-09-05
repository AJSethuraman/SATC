"""A document the client opens carries its own name, not the template's.

E4 FROM THE WALK OF 5 SEPTEMBER 2026.

All three finished PDFs in the signing pack carried the source template's title:

    SAT-C Engagement Letter - Raghavan - 2025.pdf   →  "SATC — tax preparation
                                                        engagement letter (template)"
    SAT-C Fee Estimate - Raghavan - 2025.pdf        →  "SATC — fee estimate (template)"
    SAT-C Onboarding Letter - Raghavan - 2025.pdf   →  "SATC — new client
                                                        onboarding letter (template)"

A PDF's `/Title` is not decoration. It is what the reader shows in its title
bar, what Windows shows under **File → Properties**, and what several mail
clients show when the attachment is previewed. **A client opening the letter
they are being asked to sign saw it described as a template.**

The FILENAMES were exactly right, which is what makes this the one identifier
nobody rewrote — somebody built `output_name` carefully and the `<title>` sat
three inches away inheriting from the source. None of the three named the client
or the engagement either, so three documents from three different clients were
indistinguishable once open.

WHERE THE FIX GOES, and why it is not at the callers. `merge.render` is where a
template stops being a template: `sending`, `previewing`, `cli render` and the
browser all pass through it. A rewrite in any one of those is a fix on one door
— which is the shape E2 had just finished being (a guard on the door that was
walked, and none on the four beside it).
"""
from __future__ import annotations

import pathlib
import re

import pytest

import merge

TEMPLATES = pathlib.Path(__file__).resolve().parents[2] / "satc-handoff" / "04-TEMPLATES"

RECORD = {"ClientFullName": "Priya Raghavan", "_season": "2025",
          "EngagementRef": "2026-0007"}


def _title(html_text):
    m = re.search(r"(?is)<title>(.*?)</title>", html_text)
    return m.group(1) if m else None


# ── the denominator ───────────────────────────────────────────────────────────

def test_the_templates_are_where_this_says_they_are():
    """Without templates on disk every assertion below is vacuous."""
    assert TEMPLATES.is_dir(), TEMPLATES
    assert list(TEMPLATES.glob("SATC *.html"))


def test_the_templates_do_call_themselves_templates():
    """The precondition. If they stopped, this whole file proves nothing."""
    marked = [p.name for p in TEMPLATES.glob("SATC *.html")
              if "(template)" in (_title(p.read_text(encoding="utf-8")) or "")]
    assert marked, "no template titles say (template); the defect cannot recur"


# ── the fix ───────────────────────────────────────────────────────────────────

def test_the_word_template_does_not_survive_rendering():
    """THE DEFECT."""
    out = merge._retitle(
        "<title>SATC — tax preparation engagement letter (template)</title>", RECORD)
    assert "(template)" not in out, (
        "the client is being asked to sign something titled a template")


def test_the_title_says_whose_it_is():
    got = _title(merge._retitle("<title>SATC — fee estimate (template)</title>", RECORD))
    assert "Priya Raghavan" in got
    assert "2025" in got
    assert "2026-0007" in got, "the reference ties the letter to the estimate and invoice"


def test_what_the_document_is_survives():
    """Naming the client must not cost the document's own name."""
    got = _title(merge._retitle("<title>SATC — fee estimate (template)</title>", RECORD))
    assert got.startswith("SATC — fee estimate")


def test_a_missing_field_is_dropped_rather_than_printed_empty():
    """An honest short title beats `SATC — invoice —  — `."""
    got = _title(merge._retitle("<title>SATC — invoice (template)</title>",
                                {"ClientFullName": "Priya Raghavan"}))
    assert got == "SATC — invoice — Priya Raghavan"


def test_a_name_with_an_ampersand_is_escaped():
    """Rule 1 of this module: a client named "Ross & Sons" must not break the page."""
    got = _title(merge._retitle("<title>SATC — invoice (template)</title>",
                                {"ClientFullName": "Ross & Sons"}))
    assert "&amp;" in got


def test_a_document_with_no_title_is_left_alone():
    body = "<p>no title here</p>"
    assert merge._retitle(body, RECORD) == body


# ── through the real function, on the real templates ──────────────────────────

@pytest.mark.parametrize("name", [
    "SATC Engagement Letter - Tax Preparation.html",
    "SATC Fee Estimate.html",
    "SATC Onboarding Letter.html",
])
def test_render_itself_retitles(name):
    """Asserted through `render`, not `_retitle`.

    A helper that works and is never called is exactly the defect this replaces
    — a correct `output_name` sitting next to a `<title>` nobody rewrote.
    """
    source = (TEMPLATES / name).read_text(encoding="utf-8")
    assert "(template)" in (_title(source) or ""), f"{name} is not marked; test vacuous"

    result = merge.render(source, RECORD, strict=False)
    got = _title(result.html)
    assert "(template)" not in got, f"{name} still ships as a template"
    assert "Priya Raghavan" in got
