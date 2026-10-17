"""The Peer loan classes tab: what each peer's consumer book holds, from its
own 10-Q, so an "other consumer" rate can be read for what is in it.

The file it is built from (``config/peer-loan-classes.json``) states, per
bank, which of the filing's consumer classes counts as what (student,
unsecured, secured non-auto, mixed), with the filing's own words quoted and
where they are. Amounts are never typed in it: each class names the XBRL
members the filing tags it with, and the amount is read from the cached
filing (:mod:`peers.classes`). A class the filing prints but does not tag by
class may be given as printed, with its page; the tab marks it so, and the
tie-out checks it against the page.

Three tables, top to bottom:

- **Who holds what**: one row per bank. Student loans, unsecured loans and
  lines, secured non-auto and mixed other consumer, each the sum of the
  classes counted as that (live SUMIFS over the next table), or the finding
  in words where no class is; and whether the bank is a clean comparison for
  unsecured lending, with why.
- **Consumer classes as filed**: one row per class: the filer's own label,
  $ millions, what it is counted as, and the filing.
- **In the filing's words**: the quotes behind every finding."""
import json
from pathlib import Path
from typing import List

from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter as L

from .. import keybank_style as K
from . import classes as C

TITLE = "Peer loan classes"
#: What a class may be counted as, in the order the summary shows them.
KINDS = ("Student", "Unsecured or personal", "Secured non-auto", "Mixed other consumer", "Other")
SHOWN = KINDS[:4]
FINDINGS = ("student", "unsecured", "secured_non_auto")
COMPARISON = ("Clean", "Mixed", "Not comparable")
BANK_KEYS = ("short", "cik", "holding_company", "filing_url", "classes", "findings", "comparison")
CLASS_KEYS_TAGGED = ("members", "is")
CLASS_KEYS_PRINTED = ("name", "amount_musd", "where", "is")


def load(path) -> dict:
    """The loan classes file, checked: every key present, every kind and
    answer one of the allowed, every finding quoted with where it is."""
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    problems: List[str] = []
    for k in ("quarter", "banks"):
        if k not in spec:
            problems.append("the loan classes file has no %r" % k)
    if problems:
        raise C.Refused("; ".join(problems))
    C.quarter_end(spec["quarter"])
    seen = set()
    for b in spec["banks"]:
        who = b.get("short", "?")
        for k in BANK_KEYS:
            if k not in b:
                problems.append("%s: no %r" % (who, k))
        if who in seen:
            problems.append("%s is listed twice" % who)
        seen.add(who)
        for c in b.get("classes", []):
            keys = CLASS_KEYS_TAGGED if "members" in c else CLASS_KEYS_PRINTED
            missing = [k for k in keys if k not in c]
            if missing:
                problems.append("%s: a class lacks %s" % (who, ", ".join(missing)))
            if c.get("is") not in KINDS:
                problems.append("%s: a class is counted as %r, not one of %s" % (who, c.get("is"), ", ".join(KINDS)))
        for f in FINDINGS:
            x = b.get("findings", {}).get(f)
            if not isinstance(x, dict) or not all(x.get(k) for k in ("answer", "short", "quote", "where")):
                problems.append("%s: the %s finding needs an answer, a short form, the filing's words and where "
                                "they are" % (who, f.replace("_", " ")))
            elif len(x["short"]) > 24:
                problems.append("%s: the %s finding's short form is over 24 characters" % (who, f.replace("_", " ")))
        cmp_ = b.get("comparison", {})
        if cmp_.get("answer") not in COMPARISON or not cmp_.get("why"):
            problems.append("%s: comparison needs an answer (%s) and why" % (who, ", ".join(COMPARISON)))
    if problems:
        raise C.Refused("\n".join(problems))
    return spec


def rows(spec: dict, cache) -> List[dict]:
    """Every class with its amount: from the cached filing where tagged
    (refused if the members are not found), as printed otherwise."""
    period = C.quarter_end(spec["quarter"])
    out = []
    for b in spec["banks"]:
        record, facts, labs = C.read(cache, b["cik"], period)
        for c in b["classes"]:
            if "members" in c:
                key = tuple(sorted(c["members"]))
                if key not in facts:
                    raise C.Refused("%s: the filing %s has no amortized cost at %s for %s"
                                    % (b["short"], record["accession"], period, ", ".join(key)))
                # The name as the filing prints it where given: a filer's XBRL
                # label can differ (JPMorgan tags "Auto and other" with the
                # standard "Automobile Loan" member).
                name = c.get("name") or " / ".join(C.member_label(m, labs) for m in c["members"]
                                                   if "PortfolioSegment" not in m) or C.member_label(c["members"][0], labs)
                out.append(dict(bank=b["short"], name=name, musd=facts[key] / 1e6, kind=c["is"], how="tagged",
                                where=", ".join(c["members"]), record=record))
            else:
                out.append(dict(bank=b["short"], name=c["name"], musd=float(c["amount_musd"]), kind=c["is"],
                                how="printed", where=c["where"], record=record))
    return out


def _head(ws, row, heads, right=(), height=30):
    for i, h in enumerate(heads, start=1):
        c = ws.cell(row, i, h)
        c.fill = K.solid(K.MIST)
        c.font = Font(name="Arial", size=9, bold=True, color=K.INK)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right" if i in right else "left")
        c.border = Border(bottom=Side(style="thin", color=K.STONE))
    ws.row_dimensions[row].height = height


def _section(ws, row, text, ncols):
    c = ws.cell(row, 1, text)
    c.font = Font(name="Arial", size=11, bold=True, color=K.INK)
    for col in range(1, ncols + 1):
        ws.cell(row, col).border = Border(bottom=Side(style="medium", color=K.INK))
    ws.row_dimensions[row].height = 18


def write(ws, spec: dict, cache) -> dict:
    """Fill ``ws`` and return where things are (for the tests and the tie-out)."""
    body = Font(name="Calibri", size=11, color=K.INK_TEXT)
    bold = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT)
    note = Font(name="Calibri", size=10, color=K.SLATE)
    wrap = Alignment(wrap_text=True, vertical="top")
    hair = Border(bottom=Side(style="thin", color="EFEBE4"))
    cls = rows(spec, cache)
    period = C.quarter_end(spec["quarter"])
    ncols = 7
    ws.cell(1, 1, "%s · what each bank's consumer book holds" % TITLE).font = Font(name="Arial", size=14, bold=True,
                                                                                 color=K.INK)
    ws.cell(2, 1, "From each holding company's own quarterly filing with the SEC for the quarter ended %s: the "
                  "loan classes it reports, at amortized cost. The Call Report's other consumer line mixes these "
                  "classes; this tab says which a bank holds." % period).font = Font(name="Calibri", size=11,
                                                                                     color=K.SLATE)
    for col in range(1, ncols + 1):
        ws.cell(2, col).border = Border(bottom=Side(style="medium", color=K.KEY_RED))
    ws.row_dimensions[1].height = 25.5

    banks = spec["banks"]
    s1 = 4
    t2 = s1 + 2 + len(banks) + 2                      # the classes table's section row
    first, last = t2 + 2, t2 + 1 + len(cls)
    rng = lambda col: "$%s$%d:$%s$%d" % (col, first, col, last)            # noqa: E731

    _section(ws, s1, "Who holds what ($ millions, the sum of the classes counted as each)", ncols)
    _head(ws, s1 + 1, ["Bank", "Student loans", "Unsecured or personal loans and lines", "Secured non-auto",
                       "Other consumer, mixed", "For an unsecured comparison", "Why"], right=(2, 3, 4, 5), height=45)
    summary = {}
    for i, b in enumerate(banks):
        r = s1 + 2 + i
        summary[b["short"]] = r
        ws.cell(r, 1, b["short"]).font = bold
        for j, kind in enumerate(SHOWN):
            # Where no class is counted as this, the finding's short form; the
            # full answer and the filing's words are in the last table.
            words = {"Student": b["findings"]["student"]["short"],
                     "Unsecured or personal": b["findings"]["unsecured"]["short"],
                     "Secured non-auto": b["findings"]["secured_non_auto"]["short"],
                     "Mixed other consumer": "None"}[kind]
            c = ws.cell(r, 2 + j, '=IF(COUNTIFS({b},$A{r},{k},"{kind}")=0,"{w}",SUMIFS({m},{b},$A{r},{k},"{kind}"))'
                        .format(b=rng("A"), k=rng("D"), m=rng("C"), r=r, kind=kind, w=words.replace('"', '""')))
            c.number_format = "#,##0"
            c.font = body
            c.alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)
        ws.cell(r, 6, b["comparison"]["answer"]).font = bold
        ws.cell(r, 7, b["comparison"]["why"]).font = body
        ws.row_dimensions[r].height = 15 * max(1, -(-len(b["comparison"]["why"]) // 78)) + 3
        for col in range(1, ncols + 1):
            ws.cell(r, col).border = hair
            if col in (1, 6, 7):
                ws.cell(r, col).alignment = wrap

    _section(ws, t2, "Consumer classes as filed", ncols)
    _head(ws, t2 + 1, ["Bank", "Class, as the filing labels it", "$ millions", "Counted as", "Filing",
                       "How the amount was read", "Tagged with (XBRL members) or printed where"], right=(3,))
    where = {}
    for k, c in enumerate(cls):
        r = first + k
        rec = c["record"]
        vals = [c["bank"], c["name"], c["musd"], c["kind"],
                "%s filed %s" % (rec["form"], rec["filed"]),
                "Read from the filing's XBRL" if c["how"] == "tagged" else "As printed (not tagged by class)",
                c["where"]]
        for j, v in enumerate(vals, start=1):
            cell = ws.cell(r, j, v)
            cell.font = body
            cell.border = hair
            cell.alignment = Alignment(vertical="top", wrap_text=j in (2, 4, 7), horizontal="right" if j == 3 else "left")
        ws.cell(r, 3).number_format = "#,##0"
        ws.cell(r, 5).hyperlink = rec["url"]
        where.setdefault(c["bank"], []).append((r, c))

    t3 = last + 3
    _section(ws, t3, "In the filing's words", ncols)
    _head(ws, t3 + 1, ["Bank", "About", "The filing says", "", "", "", "Where"])
    r = t3 + 2
    quotes = []
    for b in banks:
        for f, about in (("student", "Student loans"), ("unsecured", "Unsecured or personal loans and lines"),
                         ("secured_non_auto", "Secured non-auto")):
            x = b["findings"][f]
            for col, v in ((1, b["short"]), (2, about)):
                ws.cell(r, col, v).font = body
                ws.cell(r, col).alignment = wrap
            ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=6)
            said = "Not stated in the 10-Q." if x["quote"] == "not stated" else "“%s”" % x["quote"]
            q = ws.cell(r, 3, said if x["answer"] == "None stated in the 10-Q"
                        else "%s. %s" % (x["answer"].rstrip("."), said))
            q.font = body
            q.alignment = wrap
            ws.cell(r, 7, x["where"]).font = note
            ws.cell(r, 7).alignment = wrap
            ws.row_dimensions[r].height = 15 * max(1, -(-(len(x["quote"]) + len(x["answer"])) // 80),
                                                   -(-len(x["where"]) // 70)) + 3
            quotes.append(r)
            r += 1
    ws.cell(r + 1, 1, "The amounts are the filings' own: each is read from the filing's XBRL by the members named, "
                      "or, where the filing does not tag a class, as printed on the page named. What each class "
                      "is counted as is a judgment, stated with the filing's words; the Glossary tab defines each "
                      "heading.").font = note
    for col, w in zip("ABCDEFG", (16, 40, 19, 20, 30, 30, 74)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B4"
    K.hide_gridlines(ws)
    return {"summary": summary, "classes": where, "first": first, "last": last, "quotes": quotes}
