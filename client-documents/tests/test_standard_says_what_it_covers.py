"""The Standard line on an invoice says what the price page says Standard covers.

It said "Schedules, but nothing that scales" -- shorthand nobody outside the
firm could read, on every estimate and invoice. The firm, 13 Oct 2026:
"absolutely not, what is this wording?" and "it's literally part of our
pricing? what's in standard". The words already existed, in `covers:`.

And the "quoted separately" note: "should only be there if required."
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pricing  # noqa: E402

TEMPLATE = Path(__file__).resolve().parents[2] / "satc-handoff" / "04-TEMPLATES" / "SATC Invoice.html"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def test_every_part_of_the_standard_detail_is_something_standard_covers():
    std = pricing.load()["base"]["1040"]["tiers"]["standard"]
    covers = " | ".join(_norm(c) for c in std["covers"])
    parts = [_norm(p) for p in std["detail"].split(",")]
    strays = [p for p in parts if p not in covers]
    assert not strays, f"the Standard line names things its covers list does not: {strays}"


def test_the_quoted_separately_note_is_conditional():
    html = TEMPLATE.read_text(encoding="utf-8")
    i = html.index("quoted separately")
    before = html[:i]
    assert before.rfind("[[IF BilledAboveEstimate]]") > before.rfind("[[END IF]]"), (
        "the note prints on every invoice, including ones billed at the estimate")


def test_a_bill_at_the_estimate_does_not_set_the_flag():
    import invoicing
    out = {"VarianceNote": ""}
    invoicing._check_variance(out, 525.0, "$525.00", "USD")
    assert "BilledAboveEstimate" not in out


def test_a_bill_above_the_estimate_sets_it():
    import invoicing
    out = {"VarianceNote": "A third city return was added."}
    invoicing._check_variance(out, 560.0, "$525.00", "USD")
    assert out.get("BilledAboveEstimate") is True
