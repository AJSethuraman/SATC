"""Turn a public loan file into a PocketBook extract, for the public-data rehearsal (docs/rehearsal-public-data-2026-09.md).

    python tools/public_extract.py sba-foia     RAW.csv  --out EXTRACT.csv --ranr neg-gco
    python tools/public_extract.py sba-national RAW.zip  --out EXTRACT.csv --ranr neg-gco
    python tools/public_extract.py lendingclub  RAW.csv  --out EXTRACT.csv --term 36 --issued 2008-01:2011-12

Three sources, each read one row at a time (the raw files run to 1.7 GB; PocketBook reads its extract whole, so the
columns and rows are cut HERE, before it does):

  sba-foia      SBA 7(a) FOIA loan-level file (data.sba.gov, U.S. Government Works). Real GCO; no loan number.
  sba-national  SBAnational.csv (Li, Mickel & Taylor 2018, JSE 26(1)), read straight out of the Kaggle zip. The
                file the paper's figures were computed on, so the rates tie out exactly.
  lendingclub   LendingClub accepted loans 2007-2018Q4 (Hugging Face / Kaggle mirror). GCO and RANR built from
                cash flows.

What it writes: the extract (CSV) and, beside it, `<extract>.manifest.yaml`: the source file and its SHA-256, every
row read, every row kept, every row left out BY REASON, and every derived column with the rule that made it and why.
Every derived column is labelled for what it is: `native` (the source's own value, renamed at most),
`constructed` (made because the source has none, e.g. a row key) or `rehearsal approximation` (a stand-in the bank's
extract would carry for real). The manifest is the record of the choice made before PocketBook saw the loans
(PocketBook runs every loan it is given: README, "Every loan in the extract is run").

Nothing is defaulted that is a judgment: the RANR stand-in for SBA (`--ranr`), and LendingClub's term and issue
window, must be named on the command line or the tool refuses (docs/DESIGN-PRINCIPLES.md 5). Borrower names,
street addresses, ZIP codes, bank names and free text are never written: PocketBook copies values into the workbook
(`_dots`, category labels), and these are real businesses and people.

A missing raw file is refused in words, exit code 2, and nothing is written. Standard library and PyYAML only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import re
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterator

NATIVE, CONSTRUCTED, APPROX = "native", "constructed", "rehearsal approximation"
RANR_CHOICES = ("neg-gco",)          # the only stand-in built; see RANR_NEG_GCO below and the report's decisions


class Refused(Exception):
    """The tool will not write an extract; the message says what to do instead."""


@dataclass(frozen=True)
class Derived:
    """One column of the extract: its name, what PocketBook should read it as, how it is made, and why."""
    name: str
    means: str            # the PocketBook meaning a person would give it on Columns (key, booked, outcome, ...)
    status: str           # NATIVE, CONSTRUCTED or APPROX
    rule: str
    why: str
    after_booking: str = ""   # set when the value is not known when the loan is booked, or depends on its outcome


@dataclass
class Counts:
    read: int = 0
    kept: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    blanked: dict[str, int] = field(default_factory=dict)       # a derived value left blank, by column and reason
    kept_by: dict[str, int] = field(default_factory=dict)       # rows kept, by the source status they were kept for
    terms: dict[str, list[int]] = field(default_factory=dict)   # outcome -> [loans with a term, of them whole years]
    unpercented: dict[str, int] = field(default_factory=dict)   # values written without their % sign, by column

    def keep(self, status: str) -> None:
        self.kept += 1
        self.kept_by[status] = self.kept_by.get(status, 0) + 1

    def drop(self, reason: str) -> None:
        self.dropped[reason] = self.dropped.get(reason, 0) + 1

    def blank(self, col: str, reason: str) -> None:
        k = f"{col}: {reason}"
        self.blanked[k] = self.blanked.get(k, 0) + 1

    def term(self, outcome: str, months: float | None) -> None:
        if months is None:
            return
        t = self.terms.setdefault(outcome, [0, 0])
        t[0] += 1
        t[1] += float(months).is_integer() and int(months) % 12 == 0


def number(text: str | None) -> float | None:
    """'$60,000.00 ', '1710600.0' or '' as a float, or None when blank or not a number."""
    if text is None:
        return None
    s = text.strip().replace("$", "").replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def plain(x: float) -> str:
    """A dollar figure as the extract writes it: no exponent, no trailing '.0' on whole numbers."""
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}"


# --------------------------------------------------------------------------
# SBA: rules the two SBA sources share (the JSE paper's own definitions)

#: The paper's "Recession" (JSE 26(1) p. 60, footnote 6, its SAS): daysterm = Term*30; xx = DisbursementDate + daysterm;
#: Recession = 1 if xx is from 1 Dec 2007 to 30 Jun 2009. That is the loan's scheduled END falling in the recession,
#: though the paper's text says "active during"; reproduced as written, so the rate ties out to its 31.21%.
RECESSION_FROM, RECESSION_TO = date(2007, 12, 1), date(2009, 6, 30)


def recession(disbursed: date | None, term_months: float | None) -> str | None:
    if disbursed is None or term_months is None:
        return None
    end = disbursed + timedelta(days=int(term_months) * 30)
    return "Y" if RECESSION_FROM <= end <= RECESSION_TO else "N"


def real_estate(term_months: float | None) -> str | None:
    """The paper's RealEstate (p. 60): a term of 240 months or more is backed by real estate."""
    if term_months is None:
        return None
    return "Y" if term_months >= 240 else "N"


def naics2(code: str | None) -> str | None:
    """The first two digits of a NAICS code (the paper's Table 3), or None for a blank or a 0 (SBAnational writes
    0 where no code was recorded)."""
    s = (code or "").strip()
    if not s or not s.isdigit() or int(s) == 0 or len(s) < 2:
        return None
    return s[:2]


#: Found in review of the rehearsal (29 Sep 2026): on both SBA files the recorded term depends on the outcome. Most paid
#: loans' terms are whole years and most charged-off loans' are not (the manifest's term_check counts it on every
#: extract), so the term as recorded carries information from after the loan was made. Whether it is the term approved
#: is not known. Anything built on it inherits that.
TERM_AFTER = ("Depends on the outcome in this file: see term_check. Whether this is the term as approved is not "
              "known, so a finding cut on it may be circular.")
INHERITS = "Built from the term, which depends on the outcome in this file (term_check): inherits it."


def ranr_derived(gco_col: str) -> Derived:
    return Derived(
        "RANR_NEG_GCO", "ranr", APPROX, f"-({gco_col})",
        "Revenue set to zero for every loan: an invented value, named with --ranr neg-gco because the files carry "
        "no fee or funding figures and no interest earned (the FOIA file does carry InitialInterestRate, the rate "
        "at approval, filled on most FY2009 rows; no interest proxy was built from it). RANR = 0 - GCO. "
        "Contribution before losses (RANR + GCO) is then 0 for every loan, and profit after losses is only the "
        "charge-off rate turned over: the profit tabs are NOT evidence on this extract (decision for the firm, "
        "report section 1).")


# --------------------------------------------------------------------------
# SBA 7(a) FOIA

FOIA_NEEDS = ("Program", "GrossApproval", "ApprovalDate", "ApprovalFY", "FirstDisbursementDate", "ProcessingMethod",
              "TermInMonths", "NaicsCode", "BorrState", "BusinessType", "BusinessAge", "LoanStatus",
              "GrossChargeOffAmount", "RevolverStatus", "JobsSupported", "CollateralInd", "SoldSecMrktInd")
#: kept as they are, under their own names: categories and numbers to cut by
FOIA_PASS = ("GrossApproval", "ApprovalDate", "ApprovalFY", "TermInMonths", "JobsSupported", "BorrState",
             "BusinessType", "BusinessAge", "ProcessingMethod", "RevolverStatus", "CollateralInd", "SoldSecMrktInd",
             "GrossChargeOffAmount")
FOIA_PAID, FOIA_CHGOFF = "P I F", "CHGOFF"          # as the data writes them (its dictionary says "PIF")
#: passed-through columns whose value is not known when the loan is booked (found in review, 29 Sep 2026)
FOIA_AFTER = {
    "TermInMonths": TERM_AFTER,
    "SoldSecMrktInd": "Set when the loan is sold on the secondary market, after it is made (data dictionary: 'static "
                      "field once it is sold'). Not known at booking: do not cut by it.",
}


def foia_columns(prefix: str) -> list[Derived]:
    return [
        Derived("ROW_KEY", "key", CONSTRUCTED, f"'{prefix}-' + the data row's number in the file (1 = first loan)",
                "The FOIA file has no loan number. A key made from the file and its row identifies the row for this "
                "rehearsal only; it is not a loan number and matches nothing at SBA or the lender."),
        Derived("GrossApproval", "booked", NATIVE, "GrossApproval", "The approved amount: the only loan amount in the "
                "file. It is approved, not disbursed, which overstates a revolving line that was never fully drawn."),
        Derived("CHGOFF_FLAG", "outcome", NATIVE, f"1 if LoanStatus is '{FOIA_CHGOFF}', 0 if '{FOIA_PAID}'; any other "
                "status is left out of the extract and counted",
                "Only loans whose outcome is known are kept, as the paper does. CANCLD never disbursed, and EXEMPT is "
                "an active loan whose status SBA withholds (FOIA Exemption 4), so neither has an outcome. A 0/1 column "
                "is written because PocketBook's `is:` takes one value."),
        Derived("GrossChargeOffAmount", "gco", NATIVE, "GrossChargeOffAmount",
                "SBA's own figure: 'Total loan balance charged off (includes guaranteed and non-guaranteed portion of "
                "loan)' (data dictionary). A real GCO."),
        ranr_derived("GrossChargeOffAmount"),
        Derived("ApprovalDate", "origination_date", NATIVE, "ApprovalDate (ISO, read by PocketBook as written)",
                "The date SBA approved the loan: the nearest thing to an origination date in the file."),
        Derived("NAICS2", "category", APPROX, "the first two digits of NaicsCode; blank where NaicsCode is blank",
                "The paper's Table 3 reads industry at two digits. Cut by as a category (PocketBook would read a "
                "number with more than 12 values as an amount to band). Codes 31-33, 44-45 and 48-49 are left "
                "separate, as the paper's table gives them."),
        Derived("REAL_ESTATE", "category", APPROX, "'Y' if TermInMonths >= 240, else 'N'; blank if no term",
                "The paper's own definition of 'backed by real estate' (p. 60): only real-estate loans run 20 years or "
                "more. A proxy for collateral the file does not record.", INHERITS),
        Derived("RECESSION", "category", APPROX, "'Y' if FirstDisbursementDate + TermInMonths x 30 days falls from "
                "2007-12-01 to 2009-06-30, else 'N'; blank if either is blank",
                "The paper's SAS for 'Recession' (footnote 6), reproduced as written: it is the scheduled end date "
                "falling in the recession, although the paper's text says 'active during'.", INHERITS),
    ] + [Derived(c, "(as Set up reads it)", NATIVE, c, "Passed through for cutting by.", FOIA_AFTER.get(c, ""))
         for c in FOIA_PASS if c not in ("GrossApproval", "ApprovalDate", "GrossChargeOffAmount")]


def foia_prefix(path: Path) -> str:
    m = re.search(r"FY(\d{2})(\d{2})_FY(\d{2})(\d{2})|FY(\d{2})(\d{2})_(Present)", path.name)
    if not m:
        return "SBA7A"
    if m.group(7):
        return f"FY{m.group(6)}P"
    return f"FY{m.group(2)}{m.group(4)}"


def foia(rows: Iterator[dict], counts: Counts, prefix: str) -> Iterator[dict]:
    for i, r in enumerate(rows, 1):
        counts.read += 1
        status = (r.get("LoanStatus") or "").strip()
        if status not in (FOIA_PAID, FOIA_CHGOFF):
            counts.drop(f"LoanStatus {status or '(blank)'}: no known outcome")
            continue
        gco = number(r.get("GrossChargeOffAmount"))
        if gco is None:
            counts.drop("GrossChargeOffAmount blank or not a number")
            continue
        term = number(r.get("TermInMonths"))
        disb = _iso(r.get("FirstDisbursementDate"))
        out = {"ROW_KEY": f"{prefix}-{i:07d}", "CHGOFF_FLAG": "1" if status == FOIA_CHGOFF else "0",
               "RANR_NEG_GCO": plain(-gco) if gco else "0"}
        for c in FOIA_PASS:
            out[c] = (r.get(c) or "").strip()
        out["NAICS2"] = naics2(r.get("NaicsCode")) or ""
        if not out["NAICS2"]:
            counts.blank("NAICS2", "NaicsCode blank")
        out["REAL_ESTATE"] = real_estate(term) or ""
        if not out["REAL_ESTATE"]:
            counts.blank("REAL_ESTATE", "TermInMonths blank")
        out["RECESSION"] = recession(disb, term) or ""
        if not out["RECESSION"]:
            counts.blank("RECESSION", "FirstDisbursementDate or TermInMonths blank")
        counts.keep(f"LoanStatus {status}")
        counts.term(out["CHGOFF_FLAG"], term)
        yield out


def _iso(text: str | None) -> date | None:
    s = (text or "").strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None
    except ValueError:
        return None


# --------------------------------------------------------------------------
# SBAnational (the paper's own file)

NAT_NEEDS = ("LoanNr_ChkDgt", "State", "NAICS", "ApprovalDate", "ApprovalFY", "Term", "NoEmp", "NewExist",
             "UrbanRural", "RevLineCr", "LowDoc", "DisbursementDate", "DisbursementGross", "MIS_Status",
             "ChgOffPrinGr", "GrAppv")
NAT_PASS = ("LoanNr_ChkDgt", "State", "Term", "NoEmp", "NewExist", "UrbanRural", "RevLineCr", "LowDoc",
            "DisbursementGross", "ChgOffPrinGr", "GrAppv")


def nat_columns() -> list[Derived]:
    return [
        Derived("LoanNr_ChkDgt", "key", NATIVE, "LoanNr_ChkDgt", "SBA's loan number with its check digit."),
        Derived("DisbursementGross", "booked", NATIVE, "DisbursementGross, as written ('$60,000.00 ')",
                "The amount disbursed; the paper's Table 4 reads loan size from it. Passed through with its dollar "
                "sign, commas and trailing space, which PocketBook parses: part of the rehearsal.",
                "Disbursed, not approved: known only as the loan is drawn, and on a revolving line it can pass the "
                "approval (GrAppv), more often on the lines that charged off. Not the amount at booking."),
        Derived("CHGOFF_FLAG", "outcome", NATIVE, "1 if MIS_Status is 'CHGOFF', 0 if 'P I F'; a blank status is "
                "left out and counted", "The paper's Default (Table 1b): 1 if CHGOFF, 0 if PIF."),
        Derived("ChgOffPrinGr", "gco", NATIVE, "ChgOffPrinGr, as written", "Charged-off principal: the file's GCO."),
        ranr_derived("ChgOffPrinGr"),
        Derived("APPROVAL_DATE", "origination_date", APPROX,
                "ApprovalDate ('28-Feb-97', %d-%b-%y) written as ISO, its century chosen so the date falls in "
                "ApprovalFY (US federal year: October to September); blank when neither century does",
                "PocketBook reads no two-digit year, and '97' could be 1897 or 1997 by the digits alone; the file's "
                "own ApprovalFY settles it, and a date it cannot settle is blanked and counted, not guessed."),
        Derived("NAICS2", "category", APPROX, "the first two digits of NAICS; blank where NAICS is 0 or blank",
                "The paper's Table 3. SBAnational writes 0 where no code was recorded; it is not an industry."),
        Derived("REAL_ESTATE", "category", APPROX, "'Y' if Term >= 240, else 'N'", "The paper's RealEstate (p. 60).",
                INHERITS),
        Derived("RECESSION", "category", APPROX, "'Y' if DisbursementDate + Term x 30 days falls from 2007-12-01 to "
                "2009-06-30, else 'N'; blank if either is blank or the disbursement's century can't be settled",
                "The paper's SAS (footnote 6), as written. The disbursement date's two-digit year is read as the "
                "century that puts it nearest the approval date.", INHERITS),
    ] + [Derived(c, "(as Set up reads it)", NATIVE, c, "Passed through for cutting by.",
                 TERM_AFTER if c == "Term" else "")
         for c in NAT_PASS if c not in ("LoanNr_ChkDgt", "DisbursementGross", "ChgOffPrinGr")]


def fiscal_year(d: date) -> int:
    """The US federal fiscal year a date falls in: October starts the next one."""
    return d.year + 1 if d.month >= 10 else d.year


def two_digit(text: str | None) -> list[date]:
    """'28-Feb-97' read in both centuries, 1900s first; [] if it is not that shape."""
    s = (text or "").strip()
    try:
        d = datetime.strptime(s, "%d-%b-%y").date()
    except ValueError:
        return []
    out = []
    for century in (1900, 2000):
        try:
            out.append(d.replace(year=century + d.year % 100))
        except ValueError:                    # 29 Feb in a year that is a leap year in one century only (1900, 2000)
            pass
    return out


def approval_date(text: str | None, fy_text: str | None) -> tuple[date | None, str | None]:
    """The approval date whose fiscal year is ApprovalFY, or (None, why)."""
    both = two_digit(text)
    if not both:
        return None, "ApprovalDate not dd-Mon-yy"
    fy = (fy_text or "").strip()
    if not fy.isdigit():
        return None, "ApprovalFY not a plain year"
    fits = [d for d in both if fiscal_year(d) == int(fy)]
    if len(fits) != 1:
        return None, "neither century falls in ApprovalFY"
    return fits[0], None


def near(text: str | None, anchor: date | None) -> date | None:
    """A dd-Mon-yy date read in the century nearer `anchor`."""
    both = two_digit(text)
    if not both or anchor is None:
        return None
    return min(both, key=lambda d: abs((d - anchor).days))


def national(rows: Iterator[dict], counts: Counts) -> Iterator[dict]:
    for r in rows:
        counts.read += 1
        status = (r.get("MIS_Status") or "").strip()
        if status not in ("P I F", "CHGOFF"):
            counts.drop(f"MIS_Status {status or '(blank)'}: no known outcome")
            continue
        gco = number(r.get("ChgOffPrinGr"))
        if gco is None:
            counts.drop("ChgOffPrinGr blank or not a number")
            continue
        out = {c: (r.get(c) or "") for c in NAT_PASS}
        out["CHGOFF_FLAG"] = "1" if status == "CHGOFF" else "0"
        out["RANR_NEG_GCO"] = plain(-gco) if gco else "0"
        appr, why = approval_date(r.get("ApprovalDate"), r.get("ApprovalFY"))
        out["APPROVAL_DATE"] = appr.isoformat() if appr else ""
        if why:
            counts.blank("APPROVAL_DATE", why)
        out["NAICS2"] = naics2(r.get("NAICS")) or ""
        if not out["NAICS2"]:
            counts.blank("NAICS2", "NAICS 0 or blank")
        term = number(r.get("Term"))
        out["REAL_ESTATE"] = real_estate(term) or ""
        if not out["REAL_ESTATE"]:
            counts.blank("REAL_ESTATE", "Term blank")
        disb = near(r.get("DisbursementDate"), appr)
        out["RECESSION"] = recession(disb, term) or ""
        if not out["RECESSION"]:
            counts.blank("RECESSION", "DisbursementDate blank or its century unsettled, or Term blank")
        counts.keep(f"MIS_Status {status}")
        counts.term(out["CHGOFF_FLAG"], term)
        yield out


# --------------------------------------------------------------------------
# LendingClub

LC_BAD = ("Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off")
LC_GOOD = ("Fully Paid", "Does not meet the credit policy. Status:Fully Paid")
#: cut by: known when the loan was booked (the rehearsal brief's list). Servicing columns (last_*, total_rec_*,
#: recoveries, out_prncp*, hardship_*, settlement_*) are never written, so they cannot be cut by.
LC_CUTS = ("grade", "sub_grade", "term", "home_ownership", "purpose", "verification_status", "emp_length",
           "application_type", "addr_state", "fico_range_low", "dti", "revol_util", "annual_inc", "int_rate",
           "inq_last_6mths")
LC_CASH = ("funded_amnt", "total_pymnt", "total_rec_prncp", "collection_recovery_fee")
LC_NEEDS = ("id", "loan_status", "issue_d") + LC_CASH + LC_CUTS
#: the line LendingClub's own download (LoanStats3a.csv) carries above its header. Skipped and recorded, never read
#: as the header (the revived rehearsal, 3 Oct 2026: the copy reachable from the sandbox was LendingClub's own file)
LC_PREAMBLE = "Notes offered by Prospectus"
#: columns LendingClub's own download writes as "10.65%" and the mirrors as 10.65. PocketBook reads a value with a %
#: sign as not a number (ingest.parse_number), so the sign is taken off and every value so changed is counted; the
#: number itself is not changed
LC_PERCENT = ("int_rate", "revol_util")


#: the key made when the file's own ids are blank (--row-key): LendingClub's later public downloads blank id and
#: member_id on every row
LC_ROW_KEY = Derived("ROW_KEY", "key", CONSTRUCTED, "'LC-' + the data row's number in the file (1 = first row "
                     "under the header)", "This copy of the file has every id blank. A key made from the file and its "
                     "row identifies the row for this rehearsal only; it is not LendingClub's loan id.")


def lc_columns(absent: tuple[str, ...] = (), row_key: bool = False) -> list[Derived]:
    cols = [c for c in _lc_columns() if c.name not in absent]
    return [LC_ROW_KEY if row_key and c.name == "id" else c for c in cols]


def _lc_columns() -> list[Derived]:
    return [
        Derived("id", "key", NATIVE, "id", "LendingClub's loan id."),
        Derived("funded_amnt", "booked", NATIVE, "funded_amnt", "The amount funded."),
        Derived("BAD", "outcome", APPROX, f"1 if loan_status is one of {list(LC_BAD)}; 0 if one of {list(LC_GOOD)}; "
                "any other status (Current, Late, In Grace Period, blank) is left out and counted",
                "Terminal statuses only, as the paper does: a loan still running has no outcome yet."),
        Derived("GCO_APPROX", "gco", APPROX, "funded_amnt - total_rec_prncp when BAD is 1, else 0",
                "Principal outstanding when the loan charged off, gross of recoveries: the nearest a noteholder's file "
                "comes to a gross charge-off. LendingClub's own charge-off figure is not in the file."),
        Derived("RANR_APPROX", "ranr", APPROX, "total_pymnt - funded_amnt - collection_recovery_fee",
                "Lifetime cash to the noteholder less the principal lent and the collection fee: interest + late fees "
                "+ recoveries - GCO_APPROX (the identity held on every sampled row in recon). BEFORE LendingClub's "
                "servicing fee and any cost of funds, neither of which is in the file, so it overstates a bank's RANR."),
        Derived("ISSUE_DATE", "origination_date", APPROX, "issue_d ('Dec-2015') written as the 1st of that month",
                "PocketBook reads no month-year date. The day is added, not known: every loan reads as made on the 1st."),
    ] + [Derived(c, "(as Set up reads it)", NATIVE, c, "Known at booking; passed through for cutting by.")
         for c in LC_CUTS]


def lc_window(text: str) -> tuple[date, date]:
    m = re.fullmatch(r"(\d{4})-(\d{2}):(\d{4})-(\d{2})", text or "")
    if not m:
        raise Refused(f"--issued must read YYYY-MM:YYYY-MM (e.g. 2008-01:2011-12), not {text!r}")
    a, b = date(int(m.group(1)), int(m.group(2)), 1), date(int(m.group(3)), int(m.group(4)), 1)
    if b < a:
        raise Refused(f"--issued runs backwards: {text}")
    return a, b


def lendingclub(rows: Iterator[dict], counts: Counts, term: int, window: tuple[date, date],
                absent: tuple[str, ...] = (), row_key: bool = False) -> Iterator[dict]:
    want_term = f"{term} months"
    for i, r in enumerate(rows, 1):
        counts.read += 1
        rid = (r.get("id") or "").strip()
        if row_key:
            # every id is blank in this copy: a loan row is one with a blank id and a status; a line of text in the
            # id column ("Loans that do not meet the credit policy", the totals) is not a loan
            if rid or not (r.get("loan_status") or "").strip():
                counts.drop("not a loan row (the file's summary lines)")
                continue
        elif not rid.isdigit():
            counts.drop("id blank: no key (if every id is blank, name --row-key)" if not rid and
                        (r.get("loan_status") or "").strip() else "not a loan row (the file's summary lines)")
            continue
        try:
            issued = datetime.strptime((r.get("issue_d") or "").strip(), "%b-%Y").date()
        except ValueError:
            counts.drop("issue_d blank or not Mon-YYYY")
            continue
        if not (window[0] <= issued <= window[1]):
            counts.drop("issued outside the window")
            continue
        if (r.get("term") or "").strip() != want_term:
            counts.drop(f"term not {want_term}")
            continue
        status = (r.get("loan_status") or "").strip()
        if status in LC_BAD:
            bad = 1
        elif status in LC_GOOD:
            bad = 0
        else:
            counts.drop(f"loan_status {status or '(blank)'}: no outcome yet")
            continue
        cash = {c: number(r.get(c)) for c in LC_CASH}
        if any(v is None for v in cash.values()):
            counts.drop("a cash-flow column blank or not a number")
            continue
        gco = cash["funded_amnt"] - cash["total_rec_prncp"] if bad else 0.0
        ranr = cash["total_pymnt"] - cash["funded_amnt"] - cash["collection_recovery_fee"]
        out = {**({"ROW_KEY": f"LC-{i:07d}"} if row_key else {"id": rid}), "funded_amnt": (r.get("funded_amnt") or "").strip(), "BAD": str(bad),
               "GCO_APPROX": f"{gco:.2f}", "RANR_APPROX": f"{ranr:.2f}", "ISSUE_DATE": issued.isoformat()}
        for c in LC_CUTS:
            if c not in absent:
                out[c] = (r.get(c) or "").strip()
                if c in LC_PERCENT and out[c].endswith("%"):
                    out[c] = out[c][:-1].strip()
                    counts.unpercented[c] = counts.unpercented.get(c, 0) + 1
        counts.keep(f"loan_status {status}")
        yield out


# --------------------------------------------------------------------------
# Reading, writing, the manifest


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def open_rows(path: Path, member: str | None = None, preamble: str | None = None,
              skipped: list[str] | None = None) -> tuple[list[str], Iterator[dict], Callable[[], None]]:
    """The header and a row iterator over a CSV, or over one CSV inside a zip. A first line starting with
    `preamble` is not the header: it is skipped, and appended to `skipped` so the manifest can say so."""
    if path.suffix.lower() == ".zip":
        z = zipfile.ZipFile(path)
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        name = member or (names[0] if len(names) == 1 else None)
        if name is None or name not in z.namelist():
            raise Refused(f"{path.name} holds {len(names)} CSV files ({', '.join(names)}); name one with --member")
        f = io.TextIOWrapper(z.open(name), encoding="utf-8-sig", newline="")
        closer = lambda: (f.close(), z.close())
    else:
        f = path.open(encoding="utf-8-sig", newline="")
        closer = f.close
    lines: Iterator[str] = f
    if preamble:
        first = f.readline()
        if first.startswith(preamble):
            if skipped is not None:
                skipped.append(first.strip())
        else:
            lines = itertools.chain([first], f)
    reader = csv.DictReader(lines)
    return [c.strip() for c in (reader.fieldnames or [])], reader, closer


def convert(source: str, raw: Path, out: Path, ranr: str | None = None, term: int | None = None,
            issued: str | None = None, member: str | None = None, absent: tuple[str, ...] = (),
            row_key: bool = False) -> dict:
    """Write the extract and its manifest; return the manifest. Raises Refused, writing nothing, when a choice is
    missing or the raw file isn't there or isn't the source named."""
    raw = Path(raw)
    if not raw.exists():
        raise Refused(f"{raw} isn't there. The raw public files live outside git (see the rehearsal report); "
                      f"download it to that path first.")
    if source in ("sba-foia", "sba-national"):
        if ranr is None:
            raise Refused(f"--ranr is a judgment and is not defaulted: the SBA files carry no revenue. Choose one of "
                          f"{', '.join(RANR_CHOICES)} (what each means: docs/rehearsal-public-data-2026-09.md).")
        if ranr not in RANR_CHOICES:
            raise Refused(f"--ranr {ranr!r} isn't built; choose one of {', '.join(RANR_CHOICES)}.")
    if source == "lendingclub" and (term is None or issued is None):
        raise Refused("--term and --issued choose which loans run and are not defaulted (the paper used "
                      "--term 36 --issued 2008-01:2011-12).")
    absent = tuple(absent or ())
    if (absent or row_key) and source != "lendingclub":
        raise Refused("--absent and --row-key are for the lendingclub source only")
    off_list = [c for c in absent if c not in LC_CUTS]
    if off_list:
        raise Refused(f"--absent names only columns kept for cutting by ({', '.join(LC_CUTS)}), not "
                      f"{', '.join(off_list)}: the key, the outcome and the cash flows are never optional")
    skipped: list[str] = []
    header, rows, close = open_rows(raw, member, preamble=LC_PREAMBLE if source == "lendingclub" else None,
                                    skipped=skipped)
    counts = Counts()
    try:
        if source == "sba-foia":
            needs, cols = FOIA_NEEDS, foia_columns(foia_prefix(raw))
        elif source == "sba-national":
            needs, cols = NAT_NEEDS, nat_columns()
        elif source == "lendingclub":
            there = [c for c in absent if c in header]
            if there:
                raise Refused(f"--absent {', '.join(there)}: {raw.name} has it; leave it off --absent")
            needs, cols = tuple(c for c in LC_NEEDS if c not in absent), lc_columns(absent, row_key)
            window = lc_window(issued)
        else:
            raise Refused(f"unknown source {source!r}")
        missing = [c for c in needs if c not in header]
        if missing:
            raise Refused(f"{raw.name} isn't a {source} file: it has no {', '.join(missing)}")
        it = (foia(rows, counts, foia_prefix(raw)) if source == "sba-foia" else national(rows, counts)
              if source == "sba-national" else lendingclub(rows, counts, term, window, absent, row_key))
        names = [c.name for c in cols]
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.name + ".part")
        try:
            with tmp.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=names, extrasaction="raise")
                w.writeheader()
                for r in it:
                    w.writerow(r)
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)       # a run that failed half way leaves nothing that looks like an extract
    finally:
        close()
    manifest = {
        "source": source, "raw_file": raw.name, "raw_sha256": sha256_of(raw), "raw_bytes": raw.stat().st_size,
        "extract": out.name, "extract_sha256": sha256_of(out), "written": datetime.now().isoformat(timespec="seconds"),
        "choices": {k: v for k, v in (("ranr", ranr), ("term", term), ("issued", issued),
                                      ("absent", list(absent) or None), ("row_key", row_key or None))
                    if v is not None},
        **({"preamble_skipped": skipped} if skipped else {}),
        **({"absent_from_raw": f"{', '.join(absent)}: not in this raw file, so not in the extract and not "
                               f"offered for cutting by"} if absent else {}),
        "rows_read": counts.read, "rows_kept": counts.kept, "rows_kept_by_status": dict(sorted(counts.kept_by.items())),
        "rows_left_out_by_reason": dict(sorted(counts.dropped.items())),
        "derived_values_left_blank": dict(sorted(counts.blanked.items())),
        **({"percent_sign_removed": {"rule": "a trailing % sign taken off; the number is not changed",
                                     "values": dict(sorted(counts.unpercented.items()))}} if counts.unpercented else {}),
        "columns": [{"name": c.name, "read_as": c.means, "status": c.status, "rule": c.rule, "why": c.why,
                     **({"after_booking": c.after_booking} if c.after_booking else {})} for c in cols],
        "note": "Every column marked 'rehearsal approximation' or 'constructed' is a stand-in for the rehearsal, "
                "not a figure a bank extract would carry. A column with 'after_booking' is not known when the loan "
                "is booked, or depends on its outcome.",
    }
    if counts.terms:
        manifest["term_check"] = term_check(counts.terms)
    if counts.read != counts.kept + sum(counts.dropped.values()):
        raise AssertionError("rows read != rows kept + rows left out")         # pragma: no cover - a coding error
    import yaml
    manifest_path(out).write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=110),
                                  encoding="utf-8")
    return manifest


def term_check(terms: dict[str, list[int]]) -> dict:
    """The share of each outcome's terms that are whole years (a multiple of 12 months). A term fixed when the loan
    is made should not care how the loan ended; on both SBA files paid loans' terms were 82-87% whole years and
    charged-off loans' 9-11% (review, 29 Sep 2026). Counted and shown, never judged here: the reader decides."""
    return {
        "why": "A term set when the loan is made should read the same whatever the outcome. If the shares below differ "
               "widely by outcome, the term depends on the outcome, and findings cut on it (or on columns built "
               "from it) may be circular.",
        "by_outcome": {f"outcome {k}": {"loans_with_a_term": n, "whole_years": w,
                                        "share_whole_years": round(w / n, 4) if n else None}
                       for k, (n, w) in sorted(terms.items())},
    }


def manifest_path(extract: Path) -> Path:
    return extract.with_name(extract.name + ".manifest.yaml")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="public_extract", description=__doc__.split("\n\n")[0])
    p.add_argument("source", choices=("sba-foia", "sba-national", "lendingclub"))
    p.add_argument("raw", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ranr", help="SBA only: the RANR stand-in (%s); a judgment, never defaulted" % ", ".join(RANR_CHOICES))
    p.add_argument("--term", type=int, help="LendingClub only: the term in months to keep (e.g. 36)")
    p.add_argument("--issued", help="LendingClub only: YYYY-MM:YYYY-MM, the issue months to keep")
    p.add_argument("--member", help="the CSV inside a zip, when it holds more than one")
    p.add_argument("--absent", default="", help="LendingClub only: comma-separated columns kept for cutting by that "
                   "this raw file does not carry (LendingClub's own LoanStats3a.csv has no fico_range_low); "
                   "named, never assumed")
    p.add_argument("--row-key", action="store_true", help="LendingClub only: this copy has every id blank; key "
                   "each loan by its row in the file (ROW_KEY), as the SBA FOIA file is")
    a = p.parse_args(argv)
    try:
        m = convert(a.source, a.raw, a.out, ranr=a.ranr, term=a.term, issued=a.issued, member=a.member,
                    absent=tuple(c.strip() for c in a.absent.split(",") if c.strip()), row_key=a.row_key)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {a.out}: {m['rows_kept']:,} of {m['rows_read']:,} rows kept")
    for why, k in m["rows_left_out_by_reason"].items():
        print(f"  left out {k:>9,}  {why}")
    for why, k in m["derived_values_left_blank"].items():
        print(f"  blank    {k:>9,}  {why}")
    print(f"manifest: {manifest_path(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
