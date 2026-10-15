"""The Summary tab: every series' latest quarter and rating on one page.

Each product and measure has one set of lines (Thresholds), set from the
history of the source picked on Decide; every source's latest quarter is
rated on those lines.

Claude Design's round 2 (docs/design/round-2/README.md, "Summary"): two
panels side by side, each a row per first and second part (product, then
measure) and a pair of columns (latest, rating) per value of the third part
(source). The products are dealt into the left panel until it holds at least
half the rows; the rest go to the right panel, with "Needs your attention"
under them.

Generic by construction. Nothing here names a product, a measure or a bank.
The source columns come in the book's order, except that a ``compare`` pair
leads: ``compare[0]`` (the bank) first, at the larger size and in bold, then
the points between it and ``compare[1]`` (the peer group), then
``compare[1]``, then every other source. Without a compare pair the first
source the book uses leads and there is no points column. "Needs your
attention" is about the leading source.

Every number is a live reference to its product and measure's row on
Thresholds (thresholds_tab.py), so it follows what is typed on Decide; nothing is computed here but the points
between the compare pair and the attention block's ordering. The attention
block uses INDEX/MATCH over hidden helper columns rather than FILTER/SORTBY:
it looks the same, it needs no dynamic-array metadata in the file, and the
test engine (``formulas``) can recalculate it.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter as L

from . import keybank_style as K
from .thresholds_tab import NOT_PICKED

TITLE = "Summary"
GROUP, HEAD, FIRST = 4, 5, 6                 # group headers, column labels, first body row
ATTENTION_ROWS = 5                           # the 4s and 5s listed by name; the rest are counted
INK, SLATE = K.INK_TEXT, K.SLATE
#: The Thresholds cells Summary reads for each series, by meaning
#: (thresholds_tab.refs): the latest quarter and value, the rating as a number
#: and in words, the row's refusal ("Refused: ...", blank when the lines
#: stand) and the source its lines are set from (blank until one is picked).
TH_READ = ("quarter", "value", "rating", "rating_text", "refusal", "lines_from")

# Widths in Excel units, from the hand-off's pixels ((px - 5) / 7).
W_PRODUCT, W_MEASURE = 17.0, 29.6
W_LEAD_LATEST, W_LEAD_RATING, W_POINTS = 8.1, 17.9, 7.6
W_LATEST, W_RATING = 6.7, 15.0
W_GUTTER, W_EDGE = 2.71, 1.57


def _order(values):
    out = []
    for v in values:
        if v not in out:
            out.append(v)
    return out


def _side(style, color):
    return Side(style=style, color=color)


def sources_in_order(cols: Sequence[str], compare: Optional[Tuple[str, str]]) -> List[str]:
    """The compare pair first (the bank, then its peer group), then the rest
    in the book's order."""
    if not compare:
        return list(cols)
    return [compare[0], compare[1]] + [c for c in cols if c not in compare]


def split_panels(blocks: Sequence[Tuple[str, int]]) -> Tuple[List[str], List[str]]:
    """Deal whole product blocks into the left panel until it holds at least
    half the rows; the rest go right. ``blocks`` is (product, rows) in order."""
    total = sum(n for _, n in blocks)
    left, held = [], 0
    for p, n in blocks:
        if held * 2 >= total:
            break
        left.append(p)
        held += n
    return left, [p for p, _ in blocks if p not in left]


def layout(labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]],
           compare: Optional[Tuple[str, str]]) -> dict:
    """Where everything sits on Summary, for the builder, the tests and the
    walkthrough: the sources in order, each source's (latest, rating) offsets
    within a panel, the two panels' first columns, and for each label the
    row and columns of its latest value and rating."""
    rows = _order((parts[lab][0], parts[lab][1]) for lab in labels)
    srcs = sources_in_order(_order(parts[lab][2] for lab in labels), compare)
    products = _order(a for a, _ in rows)
    left, right = split_panels([(p, sum(1 for a, _ in rows if a == p)) for p in products])
    # Within a panel: product, measure, then latest and rating per source,
    # with the points after the leading source's pair (0-based offsets).
    offs, c = {}, 2
    for i, s in enumerate(srcs):
        offs[s] = (c, c + 1)
        c += 2
        if i == 0 and compare:
            offs["points"] = c
            c += 1
    width = c
    panels = [2, 2 + width + 1]                     # B, then past a one-column gutter
    placed, ends = {}, []
    for base, prods in zip(panels, (left, right)):
        r = FIRST
        for p in prods:
            for pm in (x for x in rows if x[0] == p):
                placed[pm] = (r, base)
                r += 1
        ends.append(r - 1)
    cells = {}
    for lab in labels:
        r, base = placed[tuple(parts[lab][:2])]
        a, b = offs[parts[lab][2]]
        cells[lab] = (r, base + a, base + b)
    return {"rows": rows, "sources": srcs, "offsets": offs, "width": width, "panels": panels, "left": left,
            "right": right, "last_col": panels[1] + width - 1, "placed": placed, "ends": ends, "cells": cells}


def build(wb, *, name: str, unit: str, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]],
          part_names: Sequence[str], absent: Sequence[dict], compare: Optional[Tuple[str, str]],
          notes: Sequence[str], refs: Dict[str, Dict[str, str]]) -> dict:
    """Add the Summary tab. ``absent`` and ``notes`` are the book's own words,
    printed as given; nothing is said about a missing series that the book
    did not say. ``refs`` gives each label's cells on Thresholds by meaning
    (``thresholds_tab.refs``)."""
    ws = wb.create_sheet(TITLE)
    missing = [lab for lab in labels if any(k not in refs.get(lab, {}) for k in TH_READ)]
    if missing:
        raise ValueError("Summary needs the Thresholds cells of %s" % ", ".join(missing[:3]))

    def th(col, lab):
        return refs[lab][col]

    p0, p1, _ = part_names
    lay = layout(labels, parts, compare)
    rows, srcs, offs, width = lay["rows"], lay["sources"], lay["offsets"], lay["width"]
    panel_left, left, right, last_col = lay["panels"], lay["left"], lay["right"], lay["last_col"]
    lead = srcs[0]
    by = {parts[lab]: lab for lab in labels}

    ws.sheet_properties.tabColor = K.TAB_WORK
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 100

    lead_rows = [(a, b) for a, b in rows if (a, b, lead) in by]
    first_lead = by[lead_rows[0] + (lead,)] if lead_rows else labels[0]
    ws["B1"] = '="%s · where each series stands, "&%s' % (name.replace('"', '""'), th("quarter", first_lead))
    ws["B1"].font = Font(name="Arial", size=16, bold=True, color=K.INK)
    ws["B1"].alignment = Alignment(vertical="bottom")
    ws["B2"] = ("Each rating places the latest quarter on its %s and %s's one set of lines, from 1 Low to 5 High. "
                "The lines are set on Decide from the history of the %s picked there."
                % (p0.lower(), p1.lower(), part_names[2].lower()))
    ws["B2"].font = Font(name="Calibri", size=11, color=SLATE)
    for col in range(2, last_col + 1):
        ws.cell(2, col).border = Border(bottom=_side("medium", K.KEY_RED))
    for r_, h in ((1, 25.5), (2, 15), (3, 6), (GROUP, 16.5), (HEAD, 16.5)):
        ws.row_dimensions[r_].height = h

    def short(s):
        """The compare peer's name up to its first space or bracket: 'Peer
        group (15 banks)' heads its points column as 'vs Peer'."""
        return s.split(" (")[0].split(" ")[0]

    lab_font = Font(name="Arial", size=9, bold=True, color=SLATE)
    for base in panel_left:
        col = lambda off: base + off                # noqa: E731
        for i, s in enumerate(srcs):
            a, b = offs[s]
            lead_ = i == 0
            span_end = offs["points"] if lead_ and compare else b
            fill_ = K.solid(K.INK if lead_ else K.SLATE)
            top = _side("medium", K.KEY_RED if lead_ else K.SLATE)
            ws.merge_cells(start_row=GROUP, start_column=col(a), end_row=GROUP, end_column=col(b))
            for cc in range(a, span_end + 1):
                cell = ws.cell(GROUP, col(cc))
                cell.fill = fill_
                cell.border = Border(top=top, left=_side("thin", "7A766F") if (cc == a and i > 1) else None)
            h = ws.cell(GROUP, col(a), s)
            h.font = Font(name="Arial", size=10, bold=True, color=K.PAPER)
            h.alignment = Alignment(vertical="center", indent=0)
            if lead_ and compare:
                v = ws.cell(GROUP, col(offs["points"]), "vs %s" % short(compare[1]))
                v.font = Font(name="Arial", size=9, bold=True, color=K.PAPER)
                v.alignment = Alignment(horizontal="right", vertical="center")
        heads = {0: p0, 1: p1}
        for s in srcs:
            heads[offs[s][0]] = "Latest"
            heads[offs[s][1]] = "Rating"
        if compare:
            heads[offs["points"]] = "Points"
        for off in range(width):
            cell = ws.cell(HEAD, col(off), heads.get(off))
            cell.font = lab_font
            cell.border = Border(bottom=_side("medium", K.INK))
            numeric = off >= 2 and (off == offs.get("points") or any(off == offs[s][0] for s in srcs))
            cell.alignment = Alignment(horizontal="right" if numeric else "left", vertical="center")

    hair = _side("thin", "EFEBE4")
    ink = _side("thin", K.INK)
    placed, ends = lay["placed"], lay["ends"]
    for base, prods in zip(panel_left, (left, right)):
        for p in prods:
            for k, (a_, b_) in enumerate(x for x in rows if x[0] == p):
                r = placed[(a_, b_)][0]
                top = ink if k == 0 else hair
                for off in range(width):
                    ws.cell(r, base + off).border = Border(top=top)
                pr = ws.cell(r, base, a_)
                pr.font = Font(name="Calibri", size=12, bold=True, color=INK)
                pr.alignment = Alignment(vertical="center")
                me = ws.cell(r, base + 1, b_)
                me.font = Font(name="Calibri", size=11, color=INK)
                me.alignment = Alignment(vertical="center", shrink_to_fit=True)
                for i, s in enumerate(srcs):
                    a, b = offs[s]
                    lab = by.get((a_, b_, s))
                    big = i == 0
                    f_val = Font(name="Calibri", size=13 if big else 11, bold=big, color=INK if big else SLATE)
                    val = ws.cell(r, base + a, '=IF(ISNUMBER({v}),{v},"")'.format(v=th("value", lab)) if lab else None)
                    val.number_format = "0.00"
                    val.font = f_val
                    val.alignment = Alignment(horizontal="right", vertical="center")
                    rt = ws.cell(r, base + b, '=%s&""' % th("rating_text", lab) if lab else "Not in this workbook")
                    rt.font = Font(name="Calibri", size=13 if big else 11, bold=big, color=INK if big else SLATE)
                    rt.alignment = Alignment(horizontal="left", vertical="center", indent=0, shrink_to_fit=True)
                if compare:
                    x, y = (L(base + offs[s][0]) for s in compare)
                    d = ws.cell(r, base + offs["points"], '=IF(AND(ISNUMBER({x}{r}),ISNUMBER({y}{r})),{x}{r}-{y}{r},"")'
                                .format(x=x, y=y, r=r))
                    d.number_format = "+0.00;-0.00;0.00"
                    d.font = Font(name="Calibri", size=11, color=SLATE)
                    d.alignment = Alignment(horizontal="right", vertical="center")
                    d.border = Border(top=top, right=_side("thin", K.STONE))
                ws.row_dimensions[r].height = 19.5
    for base, e in zip(panel_left, ends):
        if e >= FIRST:
            for off in range(width):
                cell = ws.cell(e, base + off)
                cell.border = Border(top=cell.border.top, right=cell.border.right, bottom=_side("medium", K.INK))

    # Rating cells: the rating's fill; Refused in crimson on canvas; a series
    # the book does not have in slate italics.
    rating_cols = [L(base + offs[s][1]) for base in panel_left for s in srcs]
    end = max(ends)
    rng = " ".join("%s%d:%s%d" % (c_, FIRST, c_, end) for c_ in rating_cols)
    anchor = "%s%d" % (rating_cols[0], FIRST)
    _rating_rules(ws, rng, anchor)
    # A product's name is written on every row and shown only on the first of
    # its block (filters and formulas still see it).
    for base in panel_left:
        pc = L(base)
        ws.conditional_formatting.add("%s%d:%s%d" % (pc, FIRST, pc, end), FormulaRule(
            formula=['AND(%s%d<>"",%s%d=%s%d)' % (pc, FIRST, pc, FIRST, pc, FIRST - 1)],
            font=Font(color=K.PAPER)))

    # ---- Hidden helpers: one row per leading-source series, for the block ----
    hc = last_col + 3                               # past the right panel and a spare column
    hcols = {k: hc + i for i, k in enumerate(("name", "rating", "latest", "quarter", "refused", "order",
                                                         "row", "unpicked"))}
    hr0 = FIRST
    hr1 = hr0 + max(len(lead_rows), 1) - 1
    rng_h = lambda k: "$%s$%d:$%s$%d" % (L(hcols[k]), hr0, L(hcols[k]), hr1)    # noqa: E731
    for i, (a_, b_) in enumerate(lead_rows):
        r = hr0 + i
        lab = by[(a_, b_, lead)]
        ws.cell(r, hcols["name"], "%s · %s" % (a_, b_))
        ws.cell(r, hcols["rating"], '=IF(ISNUMBER({k}),{k},0)'.format(k=th("rating", lab)))
        ws.cell(r, hcols["latest"], '=IF(ISNUMBER({v}),{v},0)'.format(v=th("value", lab)))
        ws.cell(r, hcols["quarter"], "=%s&\"\"" % th("quarter", lab))
        ws.cell(r, hcols["refused"], '=IF({m}<>"",1,0)'.format(m=th("refusal", lab)))
        ws.cell(r, hcols["unpicked"], '=IF({d}="",1,0)'.format(d=th("lines_from", lab)))
        # Its place in the list: rated 4 or 5, the higher rating first, then
        # the higher latest value, then the order on this tab.
        ws.cell(r, hcols["order"], ('=IF({R}{r}>=4,COUNTIFS({RR},">"&{R}{r})+COUNTIFS({RR},{R}{r},{LL},">"&{V}{r})'
                                    '+COUNTIFS({RR},{R}{r},{LL},{V}{r},{OO},"<"&{r})+1,"")')
                .format(R=L(hcols["rating"]), V=L(hcols["latest"]), r=r, RR=rng_h("rating"), LL=rng_h("latest"),
                        OO=rng_h("row")))
        ws.cell(r, hcols["row"], r)
    for k in range(len(hcols)):
        ws.column_dimensions[L(hc + k)].hidden = True
    hot = 'COUNTIF(%s,">=4")' % rng_h("rating")
    refused = "SUM(%s)" % rng_h("refused")
    unpicked = "SUM(%s)" % rng_h("unpicked")

    ws.cell(1, last_col, '="%s: "&%s&" rated 4 or 5 · "&%s&" refused · "&%s&" with no source picked"'
            % (lead.replace('"', '""'), hot, refused, unpicked))
    ws.cell(1, last_col).font = Font(name="Arial", size=12, bold=True, color=K.INK)
    ws.cell(1, last_col).alignment = Alignment(horizontal="right", vertical="bottom")

    # ---- Needs your attention, under the right panel ----
    base = panel_left[1]
    c_name, c_chip, c_text = base, base + offs[lead][1], base + offs[lead][1] + 1
    r = (ends[1] + 2) if right else FIRST
    head = ws.cell(r, base, "Needs your attention · %s" % lead)
    head.font = Font(name="Arial", size=11, bold=True, color=K.INK)
    head.alignment = Alignment(vertical="bottom")
    for off in range(width):
        ws.cell(r, base + off).border = Border(bottom=_side("medium", K.INK))
    ws.row_dimensions[r].height = 19.5
    attention = {"head": r, "rows": [], "more": None, "refused": None}
    pct = unit == "%"
    for k in range(1, ATTENTION_ROWS + 1):
        r += 1
        at = "MATCH(%d,%s,0)" % (k, rng_h("order"))
        pick = lambda key: "INDEX(%s,%s)" % (rng_h(key), at)              # noqa: E731
        ws.cell(r, c_name, "=IFERROR(%s,\"\")" % pick("name")).font = Font(name="Calibri", size=11, color=INK)
        chip = ws.cell(r, c_chip, '=IFERROR({k}&" "&CHOOSE({k},"Low","Moderate-Low","Moderate","Moderate-High",'
                                  '"High"),"")'.format(k=pick("rating")))
        chip.font = Font(name="Calibri", size=13, bold=True, color=INK)
        chip.alignment = Alignment(vertical="center", shrink_to_fit=True)
        ws.cell(r, c_text, '=IFERROR(TEXT({v},"0.00")&"{u} in "&{q},"")'.format(
            v=pick("latest"), q=pick("quarter"), u="%" if pct else (" " + unit if unit else ""))).font = \
            Font(name="Calibri", size=11, color=SLATE)
        attention["rows"].append(r)
    r += 1
    ws.cell(r, c_name, '=IF({h}>{n},"and "&({h}-{n})&" more rated 4 or 5","")'.format(h=hot, n=ATTENTION_ROWS)
            ).font = Font(name="Calibri", size=11, color=SLATE)
    attention["more"] = r
    r += 1
    ws.cell(r, c_name, '={s}&" of {n} {lead} series"'.format(s=refused, n=len(lead_rows), lead=lead.replace('"', '""'))
            ).font = Font(name="Calibri", size=11, color=INK)
    ref = ws.cell(r, c_chip, '=IF({s}>0,"Refused","None refused")'.format(s=refused))
    ref.font = Font(name="Calibri", size=13, bold=True, color=SLATE)
    ws.cell(r, c_text, '=IF({s}>0,"Each Check on Decide states the reason and the fix.","")'.format(s=refused)).font = \
        Font(name="Calibri", size=11, color=SLATE)
    attention["refused"] = r
    for rr in range(attention["head"] + 1, r + 1):
        ws.row_dimensions[rr].height = 19.5
        for off in range(width):
            ws.cell(rr, base + off).border = Border(bottom=_side("thin", K.MIST))
    _rating_rules(ws, "%s%d:%s%d" % (L(c_chip), attention["rows"][0], L(c_chip), r),
                  "%s%d" % (L(c_chip), attention["rows"][0]))

    # ---- The book's words, under both panels ----
    r = max(ends + [r]) + 2
    told = ["Rating: where the latest quarter falls on its %s and %s's lines, set on Decide from the history of "
            "one %s." % (p0.lower(), p1.lower(), part_names[2].lower()),
            "%s: no %s has been picked on Decide to set that row's lines yet." % (NOT_PICKED, part_names[2].lower())]
    if compare:
        told.append("Points: %s's latest value minus the latest value of %s, in the measure's units. A positive "
                    "value means %s is higher." % (compare[0], compare[1], compare[0]))
    told.append("Refused: the settings do not fit the series. Its Check on Decide states the reason and the fix. "
                "No rating is shown in its place.")
    told += ["Not in this workbook: " + a["why"] for a in absent]
    told += list(notes)
    for i, t in enumerate(told):
        cell = ws.cell(r + i, 2, t)
        cell.font = Font(name="Calibri", size=11, color=SLATE)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r + i, start_column=2, end_row=r + i, end_column=last_col)
    notes_at = r

    ws.column_dimensions["A"].width = W_EDGE
    for base in panel_left:
        ws.column_dimensions[L(base)].width = W_PRODUCT
        ws.column_dimensions[L(base + 1)].width = W_MEASURE
        for i, s in enumerate(srcs):
            a, b = offs[s]
            ws.column_dimensions[L(base + a)].width = W_LEAD_LATEST if i == 0 else W_LATEST
            ws.column_dimensions[L(base + b)].width = W_LEAD_RATING if i == 0 else W_RATING
        if compare:
            ws.column_dimensions[L(base + offs["points"])].width = W_POINTS
    ws.column_dimensions[L(panel_left[1] - 1)].width = W_GUTTER
    # Note rows: one 15 pt line per line of text at the notes' merged width.
    chars = sum(ws.column_dimensions[L(c_)].width for c_ in range(2, last_col + 1))
    for i, t in enumerate(told):
        ws.row_dimensions[notes_at + i].height = 15 * max(1, -(-len(t) // int(chars)))
    ws.freeze_panes = "A%d" % FIRST
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    # The left panel's columns (the right panel's are these plus width + 1).
    columns = {s: (2 + offs[s][0], 2 + offs[s][1]) for s in srcs}
    if compare:
        columns["points"] = 2 + offs["points"]
    return {"sheet": TITLE, "first": FIRST, "last": end, "sources": srcs, "panels": panel_left,
            "columns": columns, "placed": placed, "rows": rows, "attention": attention, "notes": notes_at,
            "cells": lay["cells"], "helpers": hcols, "count": ws.cell(1, last_col).coordinate}


def _rating_rules(ws, rng, anchor):
    for k in range(5):
        ws.conditional_formatting.add(rng, FormulaRule(formula=['LEFT(%s,1)="%d"' % (anchor, k + 1)],
                                                       fill=K.solid(K.RATING_FILL[k]), font=Font(color=K.INK)))
    ws.conditional_formatting.add(rng, FormulaRule(formula=['%s="Refused"' % anchor], fill=K.solid(K.CANVAS),
                                                   font=Font(bold=True, color=K.CRIMSON)))
    ws.conditional_formatting.add(rng, FormulaRule(formula=['OR(%s="Not in this workbook",%s="%s")'
                                                            % (anchor, anchor, NOT_PICKED)],
                                                   font=Font(italic=True, color=SLATE)))
