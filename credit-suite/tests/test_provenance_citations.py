"""A citation the software cannot follow is not a citation.

Found 5 September 2026, when the firm asked whether the tie-out had really
covered every base data point. It had not, and the reason was in the map: eight
dollar fields per bank were never compared because the tie-out only checks
fields the map cites, and those eight were either uncited or cited in a form
nothing could read.

Three separate faults, all silent, all in rows already flagged ``[V]`` for
verified:

1. **Seven rows carried the literal text** ``(not in tie-out map)`` where the
   MDRM code belongs. The workbook landed a value and nothing recorded where it
   came from.

2. **Parentheses do not parse.** ``_terms`` refuses anything it cannot rebuild
   character-for-character and has no notion of a bracketed group, so
   ``(C891+C893) - (C892+C894)`` returned ``None``. Flat, it parses.

3. **A bare code resolves against RCFD then RCON only.** Right for a balance
   sheet line, useless for an income-statement one, which needs ``RIAD``. And
   the two capital ratios cited ``RCOA``, the form-041 prefix, on banks that
   file 031 -- so they found nothing on any of the twelve.

Every one of those rows was verified by a person reading captions on the form.
None had been verified against the parser that reads them. Both are worth
doing; only one was being done, and this file is the other one.

The fixture is one real filing, trimmed to the codes the map cites.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_suite.sources.fdic import filing as F               # noqa: E402
from credit_suite.sources.fdic import provenance_seed as PS     # noqa: E402

FIXTURE = (ROOT / "tests" / "fixtures"
           / "filing-17534-2026-06-30-cited-codes.json")


def _facts():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["facts"]


def _rows():
    return {row[0]: row for row in PS.ALL_ROWS}


#: A ratio is a formula over filed lines, not a filed line, and the map writes
#: it with "/" for a human to read. The parser is right to refuse those.
def _is_ratio(expr: str) -> bool:
    return "/" in expr


#: Fields the FDIC does not publish, so the workbook lands nothing for them.
#: The citation records where the number WOULD come from. Listed here so the
#: guard treats them as known-empty rather than as a hole nobody noticed.
NOT_PUBLISHED = {"NTRENREQ"}


def test_no_row_says_it_has_no_citation():
    """The literal text that hid eight fields from the tie-out."""
    naked = [r[0] for r in PS.ALL_ROWS if "not in tie-out map" in (r[3] or "")]
    assert not naked, (
        "these rows carry no MDRM code, so nothing can tie them and the tie-out "
        "walks straight past them: %s" % naked)


def test_every_row_carries_something_in_the_code_column():
    blank = [r[0] for r in PS.ALL_ROWS if not (r[3] or "").strip()]
    assert not blank, "rows with an empty citation: %s" % blank


@pytest.mark.parametrize("field", sorted(
    r[0] for r in PS.ALL_ROWS if not _is_ratio(r[3] or "")))
def test_a_non_ratio_citation_parses(field):
    """Catches the bracketed form, which returned None without a word."""
    expr = _rows()[field][3]
    assert F.parse_mdrm(expr) is not None, (
        "%s cites %r and the expression parser cannot read it, so the software "
        "silently skips the field. Write sums flat -- 'A+B-C-D', not "
        "'(A+B)-(C+D)'." % (field, expr))


@pytest.mark.parametrize("field", sorted(
    r[0] for r in PS.ALL_ROWS
    if not _is_ratio(r[3] or "") and r[0] not in NOT_PUBLISHED))
def test_a_non_ratio_citation_finds_its_line_on_a_real_filing(field):
    """Catches a citation that parses and then points at nothing.

    RIAD lines cited without their prefix, and the two capital ratios cited
    with the form-041 prefix on 031 filers, both got this far and then resolved
    to nothing on all twelve banks.
    """
    expr = _rows()[field][3]
    parsed = F.parse_mdrm(expr)
    assert parsed is not None
    value, used = F.filed_value(_facts(), parsed)
    assert value is not None, (
        "%s cites %r, which parses but matches no line on a real filed Call "
        "Report (KeyBank, 2026-06-30). An income-statement line needs its RIAD "
        "prefix; a capital line on form 031 is RCFA, not RCOA." % (field, expr))
    assert used, "%s resolved to a value with no code recorded" % field


def test_the_fixture_is_a_real_filing_and_says_so():
    """A fixture somebody wrote to make a test pass proves nothing."""
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert doc["cert"] == "17534" and doc["repdte"] == "2026-06-30"
    assert "cdr.ffiec.gov" in doc["_source"]
    assert len(doc["facts"]) > 100
    # Total assets, the one line anybody can check against the public record.
    assert doc["facts"]["RCFD2170"] == 188555486000


# --------------------------------------------------------------------------
# The fixture above is a recorded file, so it cannot prove that the parser
# still extracts a decimal from real XBRL -- reverting that fix left every
# test above green. This exercises the parser on bytes instead.
# --------------------------------------------------------------------------

#: A filed leverage ratio, as the FFIEC actually serves it: unitRef="PURE",
#: six decimals, and a FRACTION where the FDIC publishes a percentage.
XBRL_WITH_A_RATIO = b"""<?xml version="1.0"?>
<xbrl xmlns:cc="http://x" xmlns:xbrli="http://y">
  <xbrli:context id="CI_280110_2026-06-30"/>
  <cc:RCFD2170 contextRef="CI_280110_2026-06-30" unitRef="USD"
    decimals="0">188555486000</cc:RCFD2170>
  <cc:RCFA7204 contextRef="CI_280110_2026-06-30" unitRef="PURE"
    decimals="6">0.099169</cc:RCFA7204>
</xbrl>"""


def test_a_filed_ratio_survives_parsing():
    """Until 5 Sep 2026 the parser kept only whole numbers.

    Dollar amounts are whole numbers, so nothing dollar-denominated ever looked
    wrong and no test failed -- while every ratio in every filing was silently
    dropped before any tie-out could see it.
    """
    facts = F.parse_facts(XBRL_WITH_A_RATIO, "2026-06-30")
    assert facts.get("RCFA7204") == pytest.approx(0.099169), (
        "the filed leverage ratio was discarded by the fact parser; it keeps "
        "whole numbers only, and a ratio is not one")


def test_a_whole_number_is_still_an_int():
    """Widening the parser must not quietly turn every dollar into a float."""
    facts = F.parse_facts(XBRL_WITH_A_RATIO, "2026-06-30")
    assert facts["RCFD2170"] == 188555486000
    assert isinstance(facts["RCFD2170"], int)


def test_the_filing_states_the_ratio_as_a_fraction_not_a_percent():
    """A unit difference worth stating rather than silently scaling.

    The filing carries 0.099169 with unitRef="PURE"; the facsimile prints
    9.9169%; the FDIC publishes 9.9169 and so does the workbook. The tie is a
    factor of 100, and it is arithmetic somebody should see rather than a
    conversion buried in a parser.
    """
    facts = F.parse_facts(XBRL_WITH_A_RATIO, "2026-06-30")
    assert facts["RCFA7204"] < 1.0
    assert round(facts["RCFA7204"] * 100, 4) == 9.9169
