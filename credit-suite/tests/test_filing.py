"""The filing tie-out: filed XBRL lines against what the workbook landed.

Offline. The network fetch is exercised at the desk; what is tested here is
everything that turns an XBRL into a verdict, against a hand-built instance
whose numbers are the ones Capital One (CERT 4297) actually filed for
2026-06-30 -- so all four lessons that module carries are asserted, not
described.
"""
from __future__ import annotations

import pytest

from credit_suite.sources.fdic import filing as F

CONTEXT = "CI_112837_2026-06-30"


def instance(**facts):
    body = "".join('<cc:%s contextRef="%s" unitRef="USD" decimals="0">%d</cc:%s>\n'
                   % (code, CONTEXT, value, code) for code, value in facts.items())
    return ("""<?xml version="1.0" encoding="utf-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:cc="http://www.ffiec.gov/xbrl/call/concepts">
<xbrli:context id="%s"><xbrli:entity/></xbrli:context>
<xbrli:context id="CI_112837_2026-03-31"><xbrli:entity/></xbrli:context>
<cc:RCFD2170 contextRef="CI_112837_2026-03-31" unitRef="USD" decimals="0">1</cc:RCFD2170>
<cc:RCON9999 contextRef="%s" unitRef="pure">N/A</cc:RCON9999>
%s</xbrl>""" % (CONTEXT, CONTEXT, body)).encode("utf-8")


# Capital One's filed lines, in dollars. Every number here is real.
XBRL = instance(RCFD1407=5_033_000_000, RCFD1403=1_789_000_000,
                RCFD2122=457_432_000_000, RCON2122=449_650_000_000,
                RCFD3123=22_966_000_000, RCFD2170=662_157_000_000,
                RCON2200=512_450_000_000, RCFN2200=150_000_000,
                RCFD1763=36_643_000_000, RCFD1764=486_000_000)

# What the FDIC API returned and the workbook landed, in thousands.
LANDED = {"NCLNLS": 6_822_000.0, "LNLSGR": 457_432_000.0, "LNATRES": 22_966_000.0,
          "ASSET": 662_157_000.0, "DEP": 512_600_000.0, "LNCI": 37_129_000.0,
          "EQV": 15.0, "NTCRCDQ": 3_001_000.0}

# The provenance map's own MDRM column, verbatim shapes.
EXPRESSIONS = {"ASSET": "RCON2170 (RCFD2170 031)", "LNLSGR": "RCON2122",
               "NCLNLS": "1407+1403", "LNATRES": "RCON3123",
               "DEP": "RCON2200 (+RCFN2200 031)",
               "LNCI": "RCON1766 (031: RCFD1763+1764)",
               "EQV": "RCFD3210",                          # a ratio field with a line code
               "NTCRCDQ": "B514-B515",                     # a flow
               "NCLNLSR": "1407,1403 / 2122",              # a ratio expression
               "EEFFR": "100 x (4093 - C232)"}             # a formula

UNITS = {k: "USD_thousands" for k in LANDED}
UNITS["EQV"] = "pct"


def facts():
    return F.parse_facts(XBRL, "2026-06-30")


# --------------------------------------------------------------------------
# parsing the instance
# --------------------------------------------------------------------------

def test_facts_come_from_the_report_period_only():
    f = facts()
    assert f["RCFD2170"] == 662_157_000_000        # not the prior quarter's 1
    assert "RCON9999" not in f                      # non-numeric is not a fact
    assert "RCFN2200" in f                          # the foreign-office prefix is read


# --------------------------------------------------------------------------
# lesson 1: units
# --------------------------------------------------------------------------

def test_the_filing_is_dollars_and_the_workbook_is_thousands():
    value, used = F.filed_value(facts(), F.parse_mdrm("RCON2170 (RCFD2170 031)"))
    assert value == 662_157_000 and used == "RCFD2170"


# --------------------------------------------------------------------------
# lesson 2: consolidated first
# --------------------------------------------------------------------------

def test_consolidated_wins_over_domestic_for_an_031_filer():
    """Capital One's domestic loans are 449.65 bn; consolidated 457.43 bn, which
    is what the FDIC publishes. Following a bare RCON code lands wrong."""
    assert F.filed_value(facts(), F.parse_mdrm("RCON2122")) == (457_432_000, "RCFD2122")


def test_domestic_is_the_fallback_when_there_is_no_consolidated_line():
    only = {"RCON2122": 449_650_000_000}
    assert F.filed_value(only, F.parse_mdrm("RCON2122")) == (449_650_000, "RCON2122")


# --------------------------------------------------------------------------
# lesson 3: the parentheticals are instructions
# --------------------------------------------------------------------------

def test_a_plus_parenthetical_adds_the_foreign_office_line_when_present():
    """DEP ties only with RCFN2200 added: 512,450,000 + 150,000."""
    value, used = F.filed_value(facts(), F.parse_mdrm("RCON2200 (+RCFN2200 031)"))
    assert value == 512_600_000
    assert used == "RCON2200+RCFN2200"


def test_a_plus_parenthetical_is_silently_absent_for_a_bank_with_no_such_line():
    domestic_only = {"RCON2200": 158_480_379_000}
    assert F.filed_value(domestic_only, F.parse_mdrm("RCON2200 (+RCFN2200 031)")) == (
        158_480_379, "RCON2200")


def test_an_031_alternative_is_tried_first_and_used_when_it_resolves():
    value, used = F.filed_value(facts(), F.parse_mdrm("RCON1766 (031: RCFD1763+1764)"))
    assert value == 37_129_000
    assert used == "RCFD1763+RCFD1764"


def test_an_031_alternative_falls_back_when_it_does_not_resolve():
    domestic = {"RCON1766": 37_374_689_000}
    assert F.filed_value(domestic, F.parse_mdrm("RCON1766 (031: RCFD1763+1764)")) == (
        37_374_689, "RCON1766")


def test_a_sum_names_every_code_it_used():
    assert F.filed_value(facts(), F.parse_mdrm("1407+1403")) == (6_822_000, "RCFD1407+RCFD1403")


def test_a_partial_sum_is_refused_not_reported():
    """One missing term must not produce a smaller number that looks right."""
    assert F.filed_value({"RCFD1407": 5_033_000_000}, F.parse_mdrm("1407+1403")) == (None, "")


@pytest.mark.parametrize("expr,primary,alt,opt", [
    # RCON / RCFD in the map are the convention, resolved consolidated-first;
    # they parse to a bare term. RCFN is a genuinely different line and stays.
    ("RCON2170 (RCFD2170 031)", [(1, "2170", None)], [], []),
    ("5369+B528-3123", [(1, "5369", None), (1, "B528", None), (-1, "3123", None)], [], []),
    ("F055+F056+F057+F058", [(1, "F055", None), (1, "F056", None), (1, "F057", None), (1, "F058", None)], [], []),
    ("RCON2200 (+RCFN2200 031)", [(1, "2200", None)], [], [(1, "2200", "RCFN")]),
    ("RCON1766 (031: RCFD1763+1764)", [(1, "1766", None)], [(1, "1763", None), (1, "1764", None)], []),
])
def test_the_mdrm_column_parses_into_primary_alternative_and_optional(expr, primary, alt, opt):
    e = F.parse_mdrm(expr)
    assert (e.primary, e.alternative, e.optional) == (primary, alt, opt)


@pytest.mark.parametrize("expr", ["1407,1403 / 2122", "100 x (4093 - C232)", "", "derived"])
def test_ratios_formulas_and_prose_are_not_line_expressions(expr):
    assert F.parse_mdrm(expr) is None


# --------------------------------------------------------------------------
# lesson 4: units and flows are skipped with a reason, never tied
# --------------------------------------------------------------------------

def test_tie_reports_verdicts_and_skips_ratios_and_flows_with_reasons():
    rows = {r.field: r for r in F.tie(facts(), LANDED, EXPRESSIONS, units=UNITS)}
    assert {f for f, r in rows.items() if r.verdict == "TIES"} == {
        "ASSET", "LNLSGR", "NCLNLS", "LNATRES", "DEP", "LNCI"}
    assert rows["EQV"].verdict.startswith("SKIPPED: a ratio")
    assert rows["NTCRCDQ"].verdict.startswith("SKIPPED: a quarterly flow")
    assert "NCLNLSR" not in rows and "EEFFR" not in rows   # not line expressions at all


def test_a_ratio_is_never_reported_as_a_fifteen_billion_difference():
    """Before units were honoured, EQV = 15 (percent) was tied to RCFD3210 and
    reported as DIFFERS by -98,720,985. That is a category error dressed as a
    finding."""
    rows = {r.field: r for r in F.tie(facts(), LANDED, EXPRESSIONS, units=UNITS)}
    assert "DIFFERS" not in rows["EQV"].verdict


def test_a_real_difference_is_named_with_its_size():
    wrong = dict(LANDED, LNLSGR=449_650_000.0)         # the domestic line's figure
    row = {r.field: r for r in F.tie(facts(), wrong, EXPRESSIONS, units=UNITS)}["LNLSGR"]
    assert row.verdict == "DIFFERS by -7,782,000"


def test_a_line_absent_from_the_filing_says_so():
    assert F.tie({}, LANDED, {"ASSET": "RCON2170"}, units=UNITS)[0].verdict == "NOT IN FILING"


def test_the_facsimile_url_is_the_shape_the_provenance_tab_already_uses():
    assert F.facsimile_page("4297", "2026-06-30") == (
        "https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx"
        "?ds=call&idType=fdiccert&id=4297&date=06302026")


def test_the_c_and_i_past_due_rows_carry_the_031_codes():
    """A tie-out found these pointing at the form 041 codes.

    KeyBank files form 031, which splits commercial and industrial loans into
    4.a (US addressees) and 4.b (non-US). The map cited 1606/1607/1608, which
    are the 041 codes, so all three came back NOT IN FILING while the landed
    values were sitting in RCFD1251/1252/1253 on the filing. The C&I *balance*
    row had carried the 031 alternative all along; the past-due rows had not.
    """
    from credit_suite.sources.fdic import provenance_seed as PROV

    rows = {r[0]: r for r in PROV.ALL_ROWS}
    for field, primary, alt in (("P3CI", "1606", "1251"),
                                ("P9CI", "1607", "1252"),
                                ("NACI", "1608", "1253")):
        mdrm = rows[field][3]
        assert mdrm == "RCON%s (031: RCFD%s+%s)" % (primary, alt, int(alt) + 3), field
        expression = F.parse_mdrm(mdrm)
        assert [t[1] for t in expression.alternative] == [alt, str(int(alt) + 3)], field
        assert [t[1] for t in expression.primary] == [primary], field
