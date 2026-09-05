"""Provenance seed -- PROVENANCE_MAP_FDIC.md rendered as workbook data.

Build-time source of the `_provenance` tab (TEMPLATE_CONTRACT.md sec 12):
one row per landed FIELD and per derived METRIC, mapping each workbook value
to where it appears in the bank's actual FILED Call Report (schedule + line /
caption + MDRM), with the honesty flag carried per row:

    [V]        code verified against the FFIEC's own CDR bulk-file captions
    [~]        line number from the 041 layout / match by caption on the
               facsimile (or a component not captured in the tie-out map)
    UNVERIFIED stated, not verified

No public FDIC field->MDRM crosswalk exists -- PROVENANCE_MAP_FDIC.md (built
from the FFIEC forms + the Fed MDRM dictionary + the CDR bulk files) is the
citation of record, and this module is its verbatim transcription. Nothing
here is invented: fields whose MDRM row is NOT in the map say so and carry
[~] with a match-by-caption instruction.

The runner does NOT import this module -- `--tieout` reads the rendered
_provenance tab out of the workbook (the workbook is the source of truth).
Pure ASCII (L3).
"""
from __future__ import annotations

from credit_suite.sources.fdic import engine_api as R

# --------------------------------------------------------------------------
# Tab header block (citations of record + the official-rendering URLs).
# --------------------------------------------------------------------------
FACSIMILE_PATTERN = ("https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx"
                     "?ds=call&idType=fdiccert&id={CERT}&date={MMDDYYYY}")
UBPR_PATTERN = ("https://cdr.ffiec.gov/Public/ViewFacsimileDirect.aspx"
                "?ds=ubpr&reptype=1&idType=fdiccert&id={CERT}")
BANKFIND_PATTERN = ("https://banks.data.fdic.gov/bankfind-suite/bankfind/"
                    "details/{CERT}")

PREAMBLE = [
    "PROVENANCE / TIE-OUT MAP -- where every workbook value appears in the "
    "bank's actual filed Call Report.",
    "",
    "CITATIONS OF RECORD: FFIEC 031/041/051 forms (schedule + item + MDRM "
    "printed per field) | Fed MDRM dictionary (federalreserve.gov/apps/mdrm/)"
    " | FFIEC UBPR User's Guide (ratio concepts) | FFIEC CDR bulk data files "
    "(2023Q1 captions) | PROVENANCE_MAP_FDIC.md (the assembled crosswalk -- "
    "no public FDIC field->MDRM crosswalk exists).",
    "",
    "OPEN THE FILED DOCUMENT (keyed by CERT, which this template already "
    "uses):",
    "  Call Report facsimile: " + FACSIMILE_PATTERN,
    "  UBPR cross-check:      " + UBPR_PATTERN,
    "  BankFind pull check:   " + BANKFIND_PATTERN,
    "  Interactive fallback:  cdr.ffiec.gov/public/ManageFacsimiles.aspx",
    "",
    "TWO-STEP TIE-OUT: API value <-> BankFind institution page (pull check) "
    "<-> CDR facsimile schedule/line (filing check). From PowerShell: "
    "python runner.py -w <book>.xlsm --tieout <CERT> [REPDTE] (--demo "
    "prints labeled demo values with the same provenance columns).",
    "A BARE RCON CODE, READ FOR A BANK WITH FOREIGN OFFICES (form 031): try the "
    "RCFD twin first -- the FDIC's totals are the consolidated ones. Where a "
    "row shows (RCFDxxxx 031) that twin tied live for CERT 17534 at 2026-06-30; "
    "where it says the code is RCON on 031 too, that is what tied.",
    "MDRM PREFIXES: RCON (domestic) / RCFD (consolidated, 031 filers) / "
    "RIAD (income) / RCOA-RCFA (RC-R). RIAD amounts are calendar-YTD: the "
    "FDIC's quarterly variants are DIFFERENCED -- Q2-Q4 values tie to (this "
    "quarter's YTD minus prior quarter's YTD).",
    "RC-N STRUCTURE (verified): col A = 30-89 days still accruing (P3*), "
    "col B = 90+ still accruing (P9*), col C = nonaccrual (NA*); each API "
    "triple is one row read across; P9* EXCLUDES nonaccrual (disjoint). "
    "051 printed item numbers are [~] -- match by caption.",
    "FLAGS: [V] = MDRM verified against FFIEC captions | [~] = match by "
    "caption on the facsimile (041 line number / component not in the map) "
    "| UNVERIFIED = stated. Ratio recomputations tie to ~rounding (FDIC "
    "annualization/differencing).",
]

HEADER = ["field", "schedule", "line / caption", "MDRM", "flag", "notes",
          "what it is"]

# --------------------------------------------------------------------------
# Per-FIELD rows (every landed RAW_FIELD + informational DEPINS) --
# transcribed from PROVENANCE_MAP_FDIC.md sections A-F.
# --------------------------------------------------------------------------
FIELD_ROWS = [
    # ---- A. balances (Schedule RC and related) ----
    ("ASSET", "RC 12", "Total assets", "RCON2170 (RCFD2170 031)", "[V]", ""),
    ("DEP", "RC 13.a (+13.b 031)",
     "Deposits in domestic (+foreign) offices",
     "RCON2200 (+RCFN2200 031)", "[V]",
     "FDIC DEP includes foreign for 031 filers"),
    ("LNLSGR", "RC-C Pt I 12",
     "Total loans & leases HFI+HFS, net of unearned", "RCON2122 (RCFD2122 031)", "[V]",
     "= RC 4.a + 4.b"),
    ("LNLSNET", "RC 4.a+4.b-4.c",
     "HFS (5369) + HFI (B528) - allowance (3123)",
     "5369+B528-3123", "[V]", "FDIC-computed; no single filed line"),
    ("BRO", "RC-E Mem 1.b", "Total brokered deposits", "RCON2365", "[V]", "RCON on form 031 too -- no consolidated twin; tied live for CERT 17534 (2026-06-30)"),
    ("EQ", "RC 27.a", "Total bank equity capital", "RCON3210 (RCFD3210 031)", "[V]",
     "excludes minority interest (RC 28 / G105)"),
    ("NCLNLS", "RC-N 9 cols B+C",
     "Total loans 90+ still accruing + nonaccrual", "1407+1403", "[V]",
     "the NCLNLSR numerator"),
    ("LNATRES", "RC 4.c", "Allowance for credit losses on loans & leases",
     "RCON3123 (RCFD3123 031)", "[V]",
     "legacy transfer-risk add-on UNVERIFIED; 3123 is the tie-out line"),
    ("P3LNLS", "RC-N 9 col A", "Total loans 30-89 days, still accruing",
     "RCON1406 (RCFD1406 031)", "[V]", ""),
    ("DEPUNINS", "RC-O Mem 2", "Estimated uninsured deposits", "RCON5597",
     "[V]",
     "FILED only by banks >= $1B (961/4,724 in 2023Q1); below that the API "
     "value is an FDIC ESTIMATE -- not tie-able; null renders BLANK, "
     "never 0; RCON on form 031 too -- no consolidated twin; tied live for CERT 17534 (2026-06-30)"),
    ("DEPINS", "RC-O Mem 1", "Insured-deposit components",
     "F049,F045,F051/F052,F047/F048", "[V]",
     "FDIC-computed estimate; formula UNVERIFIED, components verified. NOT "
     "fetched by this workbook (informational row)"),
    ("OTHBFHLB", "RC-M 5.a.(1)(a)-(d)", "FHLB advances by maturity",
     "F055+F056+F057+F058", "[V]",
     "sum of four maturity lines; F059 structured advances is an of-which "
     "-- do NOT add"),
    # ---- B. loan categories (Schedule RC-C Part I, $ outstanding) ----
    ("LNRECONS", "RC-C Pt I 1.a.(1)+(2)",
     "1-4 fam construction + other construction/land",
     "F158+F159 (domestic)", "[V]",
     "DOMESTIC offices only. The FDIC publishes RC-C real-estate balances from the domestic column; the consolidated column differs at every bank with foreign real-estate lending, and citing it reported 18 false differences across six banks on 5 Sep 2026."),
    ("LNRENRES", "RC-C Pt I 1.e.(1)+(2)",
     "Owner-occupied + other nonfarm nonresidential",
     "F160+F161 (domestic)", "[V]", "DOMESTIC offices only. The FDIC publishes RC-C real-estate balances from the domestic column; the consolidated column differs at every bank with foreign real-estate lending, and citing it reported 18 false differences across six banks on 5 Sep 2026."),
    ("LNREMULT", "RC-C Pt I 1.d", "Multifamily (5+)", "1460 (domestic)", "[V]",
     "DOMESTIC offices only. The FDIC publishes RC-C real-estate balances from the domestic column; the consolidated column differs at every bank with foreign real-estate lending, and citing it reported 18 false differences across six banks on 5 Sep 2026. The (RCFD1460 031) twin added on 4 Sep was verified against one bank whose two columns happen to be equal."),
    ("LNRERES", "RC-C Pt I 1.c.(1)+(2)(a)+(2)(b)",
     "HELOC + 1st lien + junior lien",
     "1797+5367+5368 (domestic)", "[V]", "DOMESTIC offices only. The FDIC publishes RC-C real-estate balances from the domestic column; the consolidated column differs at every bank with foreign real-estate lending, and citing it reported 18 false differences across six banks on 5 Sep 2026."),
    ("LNCI", "RC-C Pt I 4", "Commercial & industrial",
     "RCON1766 (031: RCFD1763+1764)", "[V]", ""),
    ("LNCRCD", "RC-C Pt I 6.a", "Credit cards", "RCONB538 (RCFDB538 031)", "[V]", ""),
    ("LNAUTO", "RC-C Pt I 6.c", "Automobile loans", "RCONK137 (RCFDK137 031)", "[V]",
     "*AUTO fields exist from 2011 only"),
    ("LNCONOTH", "RC-C Pt I 6.d", "Other consumer", "RCONK207 (RCFDK207 031)", "[V]",
     "6.b B539 revolving credit plans is a SEPARATE line"),
    # ---- C. past-due / nonaccrual DOLLAR triples, consumer + C&I ----
    # These were landed as the FDIC's ratio TWINS until 5 September 2026.
    # The twins divide by TOTAL ASSETS, so they could not be compared with
    # each other or with the thresholds (#268); the dollars are landed
    # instead and every rate is computed over its own book. The MDRM codes
    # below are the numerators the twin rows already carried.
    ("P3CRCD", "RC-N 5.a col A", "Cards 30-89 still accruing",
     "B575", "[V]", ""),
    ("P9CRCD", "RC-N 5.a col B", "Cards 90+ still accruing",
     "B576", "[V]", "col B excludes nonaccrual"),
    ("NACRCD", "RC-N 5.a col C", "Cards nonaccrual",
     "B577", "[V]", ""),
    ("P3AUTO", "RC-N 5.b col A", "Auto 30-89 still accruing",
     "K213", "[V]", "*AUTO fields exist from 2011 only"),
    ("P9AUTO", "RC-N 5.b col B", "Auto 90+ still accruing",
     "K214", "[V]", ""),
    ("NAAUTO", "RC-N 5.b col C", "Auto nonaccrual",
     "K215", "[V]", ""),
    ("P3RERES", "RC-N 1.c (3 rows) col A", "Resi 30-89 still accruing (HELOC + 1st + junior)",
     "5398+C236+C238", "[V]", ""),
    ("P9RERES", "RC-N 1.c (3 rows) col B", "Resi 90+ still accruing (3 rows)",
     "5399+C237+C239", "[V]", ""),
    ("NARERES", "RC-N 1.c (3 rows) col C", "Resi nonaccrual (3 rows)",
     "5400+C229+C230", "[V]", ""),
    ("P3RELOC", "RC-N 1.c.(1) col A", "HELOC 30-89 still accruing",
     "5398", "[V]", "the HELOC component row of the resi composite"),
    ("P9RELOC", "RC-N 1.c.(1) col B", "HELOC 90+ still accruing",
     "5399", "[V]", ""),
    ("NARELOC", "RC-N 1.c.(1) col C", "HELOC nonaccrual",
     "5400", "[V]", ""),
    ("P3CI", "RC-N 4 col A", "C&I 30-89 still accruing",
     "RCON1606 (031: RCFD1251+1254)", "[V]",
     "031 splits C&I into 4.a US / 4.b non-US; the 041 code 1606 does not resolve for an 031 filer. Codes read off KeyBank's own filed 031 (CERT 17534, 2026-06-30) and tied: RCFD1251 32,260 + RCFD1254 0."),
    ("P9CI", "RC-N 4 col B", "C&I 90+ still accruing",
     "RCON1607 (031: RCFD1252+1255)", "[V]",
     "031 splits 4.a/4.b; codes tied live for CERT 17534"),
    ("NACI", "RC-N 4 col C", "C&I nonaccrual",
     "RCON1608 (031: RCFD1253+1256)", "[V]",
     "031 splits 4.a/4.b; codes tied live for CERT 17534"),
    ("LNRELOC", "RC-C Pt I 1.c.(1)", "Home equity lines (the HELOC component of resi)",
     "1797 (domestic)", "[V]",
     "landed for #268 so the HELOC rates have a book to stand on. DOMESTIC offices only. The FDIC publishes RC-C real-estate balances from the domestic column; the consolidated column differs at every bank with foreign real-estate lending, and citing it reported 18 false differences across six banks on 5 Sep 2026."),
    # ---- C. past-due / nonaccrual DOLLAR triples (Schedule RC-N) ----
    ("P3RECONS", "RC-N 1.a.(1)+(2) col A",
     "Construction 30-89 still accruing (2 rows)", "F172+F173", "[V]", ""),
    ("P9RECONS", "RC-N 1.a.(1)+(2) col B",
     "Construction 90+ still accruing (2 rows)", "F174+F175", "[V]", ""),
    ("NARECONS", "RC-N 1.a.(1)+(2) col C", "Construction nonaccrual (2 rows)",
     "F176+F177", "[V]", ""),
    ("P3RENRES", "RC-N 1.e.(1)+(2) col A",
     "Nonfarm nonres 30-89 still accruing (2 rows)", "F178+F179", "[V]", ""),
    ("P9RENRES", "RC-N 1.e.(1)+(2) col B",
     "Nonfarm nonres 90+ still accruing (2 rows)", "F180+F181", "[V]", ""),
    ("NARENRES", "RC-N 1.e.(1)+(2) col C",
     "Nonfarm nonres nonaccrual (2 rows)", "F182+F183", "[V]", ""),
    ("P3REMULT", "RC-N 1.d col A", "Multifamily 30-89 still accruing",
     "RCON3499", "[V]", "RCON on form 031 too -- no consolidated twin; tied live for CERT 17534 (2026-06-30)"),
    ("P9REMULT", "RC-N 1.d col B", "Multifamily 90+ still accruing",
     "RCON3500", "[V]", "RCON on form 031 too -- no consolidated twin; tied live for CERT 17534 (2026-06-30)"),
    ("NAREMULT", "RC-N 1.d col C", "Multifamily nonaccrual", "RCON3501",
     "[V]", "RCON on form 031 too -- no consolidated twin; tied live for CERT 17534 (2026-06-30)"),
    ("P3CONOTH", "RC-N 5.c col A", "Other consumer 30-89 still accruing",
     "K216", "[V]", "tied live against all 12 banks' filed Call Reports, 2026-06-30"),
    ("P9CONOTH", "RC-N 5.c col B", "Other consumer 90+ still accruing",
     "K217", "[V]", "tied live against all 12 banks' filed Call Reports, 2026-06-30"),
    ("NACONOTH", "RC-N 5.c col C", "Other consumer nonaccrual",
     "K218", "[V]", "tied live against all 12 banks' filed Call Reports, 2026-06-30"),
    # ---- D. quarterly net charge-off flows (Schedule RI-B Part I) ----
    # Written FLAT and RIAD-prefixed, deliberately. The expression parser
    # has no notion of a bracketed group and returns None for anything it
    # cannot rebuild character-for-character, and a bare code resolves
    # against RCFD/RCON only -- right for a balance-sheet line, useless for
    # an income-statement one. Every row here cited a line the software
    # could not follow until 5 Sep 2026, and nothing noticed because the
    # tie-out skips flows with a stated reason, so the expression was never
    # exercised. A citation nobody follows is a citation nobody checks.
    # RIAD cols: A = YTD charge-offs, B = YTD recoveries; NT* = DR-CR;
    # quarterly Q variants are DIFFERENCED YTD (Q2-Q4). 8-char truncation
    # verified: NTRECONQ, never NTRECONSQ.
    ("NTCRCDQ", "RI-B Pt I 5.a cols A-B", "Credit card NCO (qtr differenced)",
     "RIADB514-RIADB515", "[V]", "quarterly = YTD differenced (Q2-Q4)"),
    ("NTAUTOQ", "RI-B Pt I 5.b cols A-B", "Automobile NCO (qtr differenced)",
     "RIADK129-RIADK133", "[V]", ""),
    ("NTRECONQ", "RI-B Pt I 1.a.(1)+(2) cols A-B",
     "Construction NCO (qtr differenced)",
     "RIADC891+RIADC893-RIADC892-RIADC894", "[V]",
     "8-char truncated name (NTRECONQ, never NTRECONSQ)"),
    # 4638/4608 are not on form 031, which every bank in this workbook
    # files. The correct expression sat in this row's NOTE while the expression
    # the software reads pointed at a line that does not exist on their form.
    # Moved into the 031-alternative syntax so it resolves for either form.
    ("NTCIQ", "RI-B Pt I 4 cols A-B", "C&I NCO (qtr differenced)",
     "RIAD4638-RIAD4608 (031: RIAD4645+RIAD4646-RIAD4617-RIAD4618)", "[V]",
     "C&I is split by borrower on 031: 4.a U.S. addressees and 4.b non-U.S.; "
     "US-only understated ten of twelve banks. Tied live against all 12 "
     "banks' filed Call Reports, 2026-06-30"),
    ("NTCONOTQ", "RI-B Pt I 5.c cols A-B",
     "Other consumer NCO (qtr differenced)", "RIADK205-RIADK206", "[V]",
     "tied live against all 12 banks' filed Call Reports, 2026-06-30"),
    ("NTRERESQ", "RI-B Pt I 1.c.(1)+1.c.(2) cols A-B",
     "Resi NCO (qtr differenced)",
     "RIAD5411+RIADC234+RIADC235-RIAD5412-RIADC217-RIADC218", "[V]",
     "revolving open-end plus closed-end first and junior liens; tied live against all 12 banks' filed Call Reports, 2026-06-30"),
    # The FDIC publishes no quarterly variant of this field: the API
    # returns NTRENRES (year-to-date) and no NTRENREQ, so the column is blank
    # for every bank. The citation records where the number WOULD come from.
    ("NTRENREQ", "RI-B Pt I 1.e.(1)+(2) cols A-B",
     "Nonfarm nonres NCO (qtr differenced)",
     "RIADC895+RIADC897-RIADC896-RIADC898", "[~]",
     "owner-occupied plus other nonfarm nonresidential. NOT PUBLISHED by the "
     "FDIC as a quarterly field -- lands blank for all 12 banks; the filing "
     "carries the components and they were checked, 2026-06-30"),
    ("NTREMULQ", "RI-B Pt I 1.d cols A-B",
     "Multifamily NCO (qtr differenced)", "RIAD3588-RIAD3589", "[V]",
     "8-char truncated name; tied live against all 12 banks' filed Call Reports, 2026-06-30"),
    # ---- E. securities (Schedule RC-B line 8, four columns) ----
    ("SCHA", "RC-B 8 col A", "HTM securities, amortized cost", "RCON1754 (RCFD1754 031)",
     "[V]",
     "tie to RC-B; RC 2.a JJ34 is net of ACL post-CECL and DIFFERS"),
    ("SCHF", "RC-B 8 col B", "HTM securities, fair value", "RCON1771 (RCFD1771 031)",
     "[V]", ""),
    ("SCAA", "RC-B 8 col C", "AFS securities, amortized cost", "RCON1772 (RCFD1772 031)",
     "[V]", ""),
    ("SCAF", "RC-B 8 col D", "AFS securities, fair value", "RCON1773 (RCFD1773 031)",
     "[V]", "= RC 2.b; equity securities excluded (RC 2.c JA22)"),
    # ---- F. FDIC-computed / filed ratios (direct core metrics) ----
    ("NCLNLSR", "FDIC-computed ratio", "100 x (1407+1403)/2122",
     "1407,1403 / 2122", "[V]", "all components filed"),
    ("NTLNLSQR", "FDIC-computed ratio",
     "100 x annualized qtr (4635-4605 differenced) / RC-K avg loans",
     "4635,4605 / 3360", "[V]", "ties to ~rounding (annualization)"),
    ("LNATRESR", "FDIC-computed ratio", "100 x 3123/2122", "3123 / 2122",
     "[V]", ""),
    ("LNRESNCR", "FDIC-computed ratio", "100 x 3123/(1407+1403)",
     "3123 / 1407,1403", "[V]", ""),
    ("RBC1AAJ", "FILED: RC-R Pt I 31", "Leverage ratio", "RCOA7204 (031: RCFA7204)", "[V]",
     "filed directly by all banks incl. CBLR electors"),
    ("RBCRWAJ", "FILED: RC-R Pt I ~51", "Total capital ratio", "RCOA7205 (031: RCFA7205)",
     "[V]", "BLANK for CBLR electors (null, never 0); Tier1 = 7206"),
    ("EQV", "FDIC-computed ratio", "100 x 3210/2170", "3210 / 2170", "[V]",
     ""),
    ("ROAQ", "FDIC-computed ratio",
     "100 x annualized qtr RIAD4340 (RI 14, differenced) / RC-K avg assets",
     "4340 / 3368", "[V]", "ties to ~rounding"),
    ("NIMY", "FDIC-computed ratio",
     "100 x annualized RIAD4074 / avg earning assets", "4074 / (RC-K)",
     "[V]", "avg earning assets FDIC-computed from RC-K"),
    ("EEFFR", "FDIC-computed ratio", "100 x (4093 - C232) / (4074 + 4079)",
     "4093,C232 / 4074,4079", "[~]",
     "C232 is RI 7.c.(2) by 041 layout -- match by caption"),
]

_FIELD_BY_ID = {r[0]: r for r in FIELD_ROWS}


def _flag_join(*ids):
    """Weakest-link flag across component field rows."""
    flags = [_FIELD_BY_ID[i][4] for i in ids if i in _FIELD_BY_ID]
    if any(f == "UNVERIFIED" for f in flags):
        return "UNVERIFIED"
    if any(f == "[~]" for f in flags):
        return "[~] comp."
    return "[V] comp."


def _mdrm_of(fid):
    return _FIELD_BY_ID[fid][3] if fid in _FIELD_BY_ID else "?"


def metric_rows():
    """One provenance row per DERIVED metric (a direct metric's id IS a
    landed field, so its field row above already serves as its provenance
    row). Derived rows carry the exact formula + the component MDRMs."""
    rows = [
        ("PD3089R", "derived: P3LNLS/LNLSGR*100",
         "RC-N 9 col A over RC-C Pt I 12", "1406 / 2122", "[V] comp.",
         "no API ratio field exists"),
        ("TEXAS", "derived VARIANT: NCLNLS/(EQ+LNATRES)*100",
         "RC-N 9 cols B+C over RC 27.a + RC 4.c",
         "(1407+1403) / (3210+3123)", "[V] comp.",
         "canonical adds OREO and nets intangibles -- ORE/INTAN UNVERIFIED"),
        ("LNDEPR", "derived: LNLSNET/DEP*100",
         "RC 4.a+4.b-4.c over RC 13", "(5369+B528-3123) / 2200",
         "[V] comp.", ""),
        ("BRODEPR", "derived: BRO/DEP*100", "RC-E Mem 1.b over RC 13",
         "2365 / 2200", "[V] comp.", "BRO null -> blank, never 0"),
        ("CRECONR", "derived PROXY: (LNRECONS+LNRENRES+LNREMULT)/"
         "(EQ+LNATRES)*100", "RC-C Pt I 1.a+1.e+1.d over RC 27.a + RC 4.c",
         "(F158+F159+F160+F161+1460) / (3210+3123)", "[V] comp.",
         "guidance uses total RBC; documented proxy denominator"),
        ("UNRLZCAPR",
         "derived: ((SCHA-SCHF)+(SCAA-SCAF))/(EQ+LNATRES)*100",
         "RC-B 8 cols A-D over RC 27.a + RC 4.c",
         "((1754-1771)+(1772-1773)) / (3210+3123)", "[V] comp.",
         "both legs COMPUTED (no named unrealized field); EQCCOMPI is the "
         "YTD OCI FLOW, not AOCI stock -- not used"),
    ]
    for mid, (num, den, mult) in sorted(R.PACK_RATIOS.items()):
        nrow = _FIELD_BY_ID.get(num)
        drow = _FIELD_BY_ID.get(den)
        rows.append((
            mid,
            f"derived: {num}/{den}*{mult}",
            f"{nrow[1] if nrow else '?'} over {drow[1] if drow else '?'}",
            f"({_mdrm_of(num)}) / ({_mdrm_of(den)})",
            _flag_join(num, den),
            ("annualized x4 quarterly flow (NTLNLSQR convention)"
             if mult == 400 else "") +
            (" null numerator -> blank, never 0" if num == "DEPUNINS"
             else ""),
        ))
    return rows


ALL_ROWS = FIELD_ROWS + metric_rows()


if __name__ == "__main__":
    ids = {r[0] for r in ALL_ROWS}
    # every landed field and every registered metric has a provenance row
    missing_f = [f for f in R.RAW_FIELDS if f not in ids]
    missing_m = [m for m in R.METRICS if m not in ids]
    assert not missing_f, f"fields without provenance: {missing_f}"
    assert not missing_m, f"metrics without provenance: {missing_m}"
    for r in ALL_ROWS:
        assert len(r) == 6, r
        assert all(ord(c) < 128 for c in "".join(map(str, r))), r[0]
    print(f"{len(FIELD_ROWS)} field rows + {len(metric_rows())} metric rows "
          f"-- every field/metric covered, ASCII clean")
