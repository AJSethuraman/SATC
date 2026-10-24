"""The two faults the second pass found in how this feed is CHECKED.

Both are about the machinery rather than the numbers, and both were invisible
from the delivered file, which is why they lasted.

**One resolver.** A citation may name a line under two versions of the Call
Report -- `RIAD4638-RIAD4608 (031: RIAD4645+RIAD4646-RIAD4617-RIAD4618)` means
"this line, or that expression on the 031". The balance path resolved it
correctly; the quarterly-flow path carried its own copy of the citation and its
own evaluator that read the expression literally, so on a bank filing the 041
it found nothing and published *the bank did not report this line*. Zions
Bancorporation was told that in 38 of its 40 quarters. All 63 values tie.

**A tool that cannot be imported is not a tool.** The move to the Forge on
7 September 2026 left `NAME = SB / "..."` above `SB = workdir()` in nine tools,
so each raised NameError before it ran a line. Nothing caught it because the
standing run starts downstream of all nine -- on the rows they had written
before the move. A check that is skipped is not a check that passed.
"""
import ast
import pathlib
import re

import pytest

from credit_suite.sources.fdic import filing as F
from credit_suite.sources.fdic import provenance_seed as PS

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools" / "tieout"

#: The citation in the seed that carries both versions of the form, and the
#: field it belongs to. Quoted here rather than imported so that changing the
#: seed has to change this test too.
NTCIQ = "RIAD4638-RIAD4608 (031: RIAD4645+RIAD4646-RIAD4617-RIAD4618)"

#: A bank filing the 041 reports C&I charge-offs and recoveries on one line
#: each; a bank filing the 031 splits both by where the borrower is.
FACTS_041 = {"RIAD4638": 17875000, "RIAD4608": 9487000,
             "RIAD4646": 0, "RIAD4618": 0}
FACTS_031 = {"RIAD4645": 644000000, "RIAD4646": 101000000,
             "RIAD4617": 64000000, "RIAD4618": 60000000}


def test_the_seed_still_carries_both_forms_for_the_split_line():
    assert PS.ALL_ROWS, "the seed is empty"
    cited = {r[0]: r[3] for r in PS.ALL_ROWS}
    assert cited["NTCIQ"] == NTCIQ, (
        "NTCIQ's citation no longer names both versions of the form. The 031 "
        "expression alone reports every 041 filer as not having filed the line")


@pytest.mark.parametrize("facts, expected, used", [
    (FACTS_041, 17875000 - 9487000, "RIAD4638-RIAD4608"),
    (FACTS_031, 644000000 + 101000000 - 64000000 - 60000000,
     "RIAD4645+RIAD4646-RIAD4617-RIAD4618"),
])
def test_one_citation_resolves_on_either_version_of_the_form(facts, expected, used):
    got = F.filed_dollars(facts, F.parse_mdrm(NTCIQ))
    assert got is not None, (
        "the citation resolved to nothing on a filing that carries the line -- "
        "this is the shape that published 63 values as not filed")
    assert got[0] == expected
    assert got[1] == used, (
        "the row must cite the line actually read on THIS filing, or a bank "
        "filing the 041 is handed the 031's codes to look up on its own form")


def test_a_missing_line_is_still_a_refusal_and_not_a_partial_sum():
    """The alternative falling through must not become "add what is there"."""
    half = {"RIAD4645": 5, "RIAD4646": 3}          # no recoveries, no 041 line
    assert F.filed_dollars(half, F.parse_mdrm(NTCIQ)) is None


def test_lenient_keeps_the_form_the_bank_actually_filed():
    """Leniency is for an acquired bank's absent lines, not for the wrong form.

    An 031 filer with no non-U.S. lending does not file RIAD4646 at all. That
    branch must still be the one used -- summing the 041's two absent lines to
    zero instead would silently make a merger adjustment vanish.
    """
    sparse = {"RIAD4645": 900, "RIAD4617": 100}
    total, used, absent = F.filed_dollars(sparse, F.parse_mdrm(NTCIQ),
                                          lenient=True)
    assert total == 800
    assert "RIAD4645" in used and set(absent) == {"4646", "4618"}


def test_the_flow_path_has_no_citation_table_of_its_own():
    """`verify_bank_history` must name WHICH fields are flows and no more.

    It used to carry the expressions as well, copied from the seed, and the
    copy went stale in the one way that mattered.
    """
    src = (TOOLS / "verify_bank_history.py").read_text(encoding="utf-8")
    assert "FLOW_EXPR = {" not in src, (
        "the flow path is carrying its own citations again; read them from "
        "provenance_seed, which this file already calls the source of truth")
    assert re.search(r"^FLOW_FIELDS\s*=\s*\(", src, re.M), (
        "which fields are quarterly flows is a fact about the form and has to "
        "stay written down somewhere")


def test_no_capital_ratio_ties_on_a_hundred_times_the_rounding_it_needs():
    """The filing prints six decimals, the FDIC four: 0.00005 is the most that
    honest rounding can produce. The tolerance was 0.005, and the one value
    that used the room was a real disagreement."""
    src = (TOOLS / "verify_bank_history.py").read_text(encoding="utf-8")
    m = re.search(r"^CAPITAL_TOL\s*=\s*([0-9.]+)", src, re.M)
    assert m, "the capital tolerance must be named, not inlined at a call site"
    assert float(m.group(1)) <= 0.0005, (
        "a tolerance this loose hides differences rather than rounding")


def _workdir_order(path):
    """(line where SB is assigned, lines above it that already use SB)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    assign = next((i for i, l in enumerate(lines)
                   if re.match(r"^SB\s*=\s*workdir\(\)", l)), None)
    if assign is None:
        return None, []
    names = [re.match(r"^([A-Z_]+)\s*=\s*SB\s*/", l).group(1)
             for l in lines if re.match(r"^[A-Z_]+\s*=\s*SB\s*/", l)]
    early = [(i + 1, l) for i, l in enumerate(lines[:assign])
             if re.match(r"^[A-Z_]+\s*=\s*SB\s*/", l)
             or any(re.match(r"^%s\b" % nm, l) for nm in names)]
    return assign + 1, early


@pytest.mark.parametrize("tool", sorted(TOOLS.glob("*.py")),
                         ids=lambda p: p.name)
def test_every_tool_can_at_least_be_imported(tool):
    """It parses, and nothing reads the working folder before it is resolved.

    Nine of these raised NameError on the first line that touched `SB`. The
    tools that produce the evidence were dead for a day and the standing run
    stayed green over the rows they had written earlier.
    """
    ast.parse(tool.read_text(encoding="utf-8"))
    assign, early = _workdir_order(tool)
    assert not early, (
        "%s uses the working folder at line(s) %s, above `SB = workdir()` on "
        "line %s -- it raises NameError before it runs"
        % (tool.name, [i for i, _ in early], assign))
