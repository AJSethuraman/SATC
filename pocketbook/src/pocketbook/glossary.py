"""Glossary: every term the tabs use, one a row, with an example in this book's own figures.

The firm, 2 Oct 2026, after explaining the grids' figures to their boss: "Maybe a nice glossary of terms in the
workbook should be there". Written by every Set up and every Run, right after Start here. Its examples use the
whole book's figures from the last Run (`figures`, kept on _found so Set up can write them again); before the first
Run they are made up, and the note says so. Where a tab already words a definition, the words here are that tab's.

Nothing here is a formula: the figures are the Run's, so a line changed on Control since does not move them.
"""

from __future__ import annotations

import json

from . import house

SHEET = "Glossary"
#: _found's key for the figures, as JSON: what Set up writes the examples from after a Run
FOUND_KEY = "glossary"
TERM, MEANS, EXAMPLE = 2, 3, 4
HEADS = ("Term", "What it means", "Example")
WIDTHS = {1: 2, TERM: 24, MEANS: 62, EXAMPLE: 62}
#: the note's line, before and after the first Run
MADE_UP = "Made up until the first Run. Each Run puts this book's own figures here."
FROM_RUN = "This book's own figures, for the whole book, from the last Run ({stamp})."
#: the generic book before the first Run (the firm's own example: "the book keeps $4.45 per $100 booked")
GENERIC = {"booked": 40_000_000, "gco": 880_000, "ranr": 1_780_000, "contrib": 2_660_000, "loans": 3_000,
           "bad": 312, "bad_den": 3_000}


def _usd(v: float) -> str:
    return f"${v:,.0f}" if v >= 0 else f"-${-v:,.0f}"


def per100(rate: float) -> str:
    """A rate as dollars per $100 booked: 0.0445 is "$4.45"."""
    v = rate * 100
    return f"${v:.2f}" if v >= 0 else f"-${-v:.2f}"


def _keeps(rate: float) -> str:
    """"keeps $4.45", or "loses $0.50" when RANR is below nought."""
    return f"keeps {per100(rate)}" if rate >= 0 else f"loses {per100(-rate)}"


def _rest(total, c) -> float | None:
    den = total.den - c.den
    return (total.num - c.num) / den if den else None


def figures(res, names: dict[str, str]) -> dict:
    """The whole book's figures from a Run, and the pockets the examples name: plain numbers and words only, so
    they keep as JSON on _found. A figure the Run has no measure for is left out, and its example is the made-up
    one."""
    from . import engine
    t = res.total.rates
    out: dict = {"loans": res.rows}
    if getattr(res, "book_size", None) is not None and res.book_size.booked:
        out["booked"], out["booked_loans"] = res.book_size.booked, res.book_size.loans
    elif "ranr_rate" in t:
        out["booked"] = t["ranr_rate"].den
    for key, m in (("gco", "gco_rate"), ("ranr", "ranr_rate"), ("contrib", "contribution_rate")):
        if m in t and t[m].rate is not None:
            out[key], out[f"{key}_rate"] = t[m].num, t[m].rate
    if "outcome_loans" in t and t["outcome_loans"].den:
        out["bad"], out["bad_den"] = int(t["outcome_loans"].num), int(t["outcome_loans"].den)
    b = res.config.benchmark
    if b is not None:
        out.update(min_units=b.min_units, worse_at=b.worse_at, better_at=b.better_at, confidence=b.confidence,
                   shuffles=b.shuffles)
    grids = [g for g in getattr(res, "grids", []) if g.band in names and g.dimension in names]
    if grids:
        g = grids[0]
        pockets = list(g.inner())
        out["grid"] = {"name": f"{names[g.band]} x {names[g.dimension]}", "pockets": len(pockets),
                       "bands": len({b_ for (b_, _), _ in pockets}), "segments": len({d for (_, d), _ in pockets})}
        n = sum(1 for g_ in grids for _ in g_.inner())
        if "gco_rate" in t:
            out["worse_material"] = {"n": sum(1 for g_ in grids for _, c in g_.inner()
                                              if engine.worse_and_material(c.rates["gco_rate"])), "of": n}

    def label(g, b_, d):
        seg = f"{names[g.dimension]} {d}" if str(d).replace(".", "").isdigit() else str(d)
        return {"band": f"{names[g.band]} {b_}", "band_col": names[g.band], "seg": seg,
                "seg_col": names[g.dimension], "seg_value": str(d)}

    # the pocket furthest above the rest of the book on GCOs, in dollars, and the one furthest short on RANR
    for key, m, sign in (("gco_pocket", "gco_rate", 1), ("ranr_pocket", "ranr_rate", -1)):
        if m not in t or t[m].rate is None:
            continue
        best = None
        for g in grids:
            for (b_, d), c in g.inner():
                s = c.rates[m]
                rest = _rest(t[m], s)
                if s.rate is None or rest is None or not s.units:
                    continue
                over = sign * (s.num - rest * s.den)
                if best is None or over > best[0]:
                    best = (over, g, b_, d, s, rest, c.rows)
        if best and best[0] > 0:
            _, g, b_, d, s, rest, loans = best
            out[key] = {**label(g, b_, d), "loans": loans, "rate": s.rate, "rest": rest}
    once = (getattr(res, "once", {}) or {}).get("gco_rate")
    if once is not None and once.pockets:
        out["once"] = {"dollars": once.dollars, "loans": once.loans, "pockets": once.pockets}
    fv = getattr(res, "filter_values", None)
    if fv and res.config.filter_by:
        out["filter"] = {"col": res.config.filter_by, "value": str(fv[0]), "picked": True}
    elif "gco_pocket" in out:
        p = out["gco_pocket"]
        out["filter"] = {"col": p["seg_col"], "value": p["seg_value"], "picked": False}
    # the band column with the most loans marked missing, and how many: the (marked missing) row's example
    gone = [(g.cells[(engine.MISSING_RULE_LABEL, engine.ALL)].rows, names[g.band]) for g in grids
            if (engine.MISSING_RULE_LABEL, engine.ALL) in g.cells]
    if gone:
        n, col = max(gone, key=lambda x: x[0])
        out["missing"] = {"col": col, "loans": n}
    dates = getattr(res, "dates", None)
    if dates is not None and getattr(dates.first, "year", None) and getattr(dates.last, "year", None):
        out["years"] = [dates.first.year, dates.last.year]
    return out


def _pocket(p: dict) -> str:
    return f"{p['band']} / {p['seg']}"


def rows(f: dict | None) -> list[tuple[str, str, str]]:
    """Every term, in the firm's order: (term, what it means, its example). `f` is `figures`' dict, or None before
    the first Run."""
    from . import engine, stats
    from .choices import NO_DATE
    run = f is not None
    f = f or {}
    g = {**GENERIC, **f}
    gco_r = g.get("gco_rate", GENERIC["gco"] / GENERIC["booked"])
    ranr_r = g.get("ranr_rate", GENERIC["ranr"] / GENERIC["booked"])
    contrib_r = g.get("contrib_rate", GENERIC["contrib"] / GENERIC["booked"])
    real = lambda *keys: run and all(k in f for k in keys)          # noqa: E731
    out = []

    out.append(("Booked / Booked $",
                "The dollars committed when the loan was made. For cards, the credit line.",
                f"This book booked {_usd(f['booked'])} over {f.get('booked_loans', f['loans']):,} loans."
                if real("booked") else
                "A $10,000 loan books $10,000. A card with a $5,000 line books $5,000."))
    # the firm, 2 Oct 2026: "booked dollar averages so more easily demonstrate how line assignments look in pockets"
    bl = f.get("booked_loans") if run else None
    avg = f["booked"] / bl if bl and real("booked") else None
    out.append(("Avg line / × book",
                "Avg line: the average committed line per loan, booked dollars over loans. × book beside it compares "
                "a pocket's average line with the whole book's.",
                f"This book's average line is {_usd(avg)}. A pocket averaging {_usd(avg * 1.24)} is 1.24× book."
                if avg else
                "A pocket averaging $6,200 a line, in a book averaging $5,000, is 1.24× book."))
    out.append(("GCOs ($)",
                "Gross charge-off dollars: what was written off on a loan, before any recoveries.",
                f"This book's GCOs came to {_usd(f['gco'])}: {per100(gco_r)} per $100 booked." if real("gco") else
                f"GCOs of {_usd(GENERIC['gco'])} on {_usd(GENERIC['booked'])} booked: {per100(gco_r)} per $100 "
                f"booked."))
    out.append(("RANR",
                "Risk-adjusted net revenue: what a loan kept after its losses. For cards: interest, fees and "
                "interchange, less rewards and charge-offs.",
                f"This book's RANR came to {_usd(f['ranr'])}. The book {_keeps(ranr_r)} per $100 booked."
                if real("ranr") else
                f"RANR of {_usd(GENERIC['ranr'])} on {_usd(GENERIC['booked'])} booked: the book {_keeps(ranr_r)} "
                f"per $100 booked."))
    out.append(("RANR + GCOs",
                "RANR with the GCOs added back: what the loans brought in before their losses.",
                f"This book made {per100(contrib_r)} per $100 booked before losses, and {_keeps(ranr_r)} after "
                f"them." if real("contrib", "ranr") else
                f"A book making {per100(contrib_r)} per $100 booked before losses, and losing {per100(gco_r)}, "
                f"{_keeps(ranr_r)}."))
    out.append(("Rate (GCOs ÷ Booked, RANR ÷ Booked)",
                "Dollars per $100 booked, so a small pocket can sit beside a big one. A rate of 2.20% is $2.20 per "
                "$100 booked.",
                f"This book's GCOs ÷ Booked is {gco_r * 100:.2f}%: {per100(gco_r)} lost per $100 booked."
                if real("gco") else
                f"GCOs ÷ Booked of {gco_r * 100:.2f}%: {per100(gco_r)} lost per $100 booked."))
    p = f.get("ranr_pocket") if run else None
    out.append(("Points (pts)",
                "The gap between two rates, in percentage points. -3.00 pts keeps $3 less per $100 booked than "
                "the comparison.",
                f"{_pocket(p)} {_keeps(p['rate'])} per $100 booked; the rest of the book {_keeps(p['rest'])}. "
                f"That is {(p['rate'] - p['rest']) * 100:+.2f} pts." if p else
                "A pocket keeping $1.45 per $100 booked, beside a rest keeping $4.45, is -3.00 pts."))
    p = f.get("gco_pocket") if run else None
    out.append(("× book / × rest of book",
                "A rate over its comparison's: × book over the whole book's, × rest of book over every other "
                "loan's. 2.00× means twice the GCOs per booked dollar.",
                f"{_pocket(p)} loses {per100(p['rate'])} per $100 booked: {p['rate'] / gco_r:.2f}× book and "
                f"{p['rate'] / p['rest']:.2f}× rest of book." if p and real("gco_rate") and p["rest"] else
                "A pocket losing $4.40 per $100 booked, in a book losing $2.20, is 2.00× book."))
    out.append(("Rest of book / rest of band",
                "What a pocket is compared with: every other loan in the book, or every other loan in its band. "
                "Judged against on Control picks which.",
                f"For {_pocket(p)}, the rest of band is every other {p['band']} loan. The rest of book is every "
                f"other loan." if p else
                "For SCORE 620 - 679 / Direct, the rest of band is every other SCORE 620 - 679 loan."))
    out.append(("Bad loan",
                "A loan whose outcome column reads yes, as Yes means on Columns sets it.",
                f"{f['bad']:,} of this book's {f['bad_den']:,} loans went bad: {f['bad'] / f['bad_den']:.1%}."
                if real("bad", "bad_den") else
                f"{GENERIC['bad']:,} of {GENERIC['bad_den']:,} loans went bad: "
                f"{GENERIC['bad'] / GENERIC['bad_den']:.1%}."))
    out.append(("Band",
                "A range of one number column. Band edges on Columns set where each starts; a column with few "
                "values gets one band per value.",
                f"{p['band']} is one band of {p['band_col']}." if p else "SCORE 620 - 679 is one band of SCORE."))
    out.append(("Segment",
                "One value of a category column, such as one channel.",
                f"{p['seg']} is one segment of {p['seg_col']}." if p else "Direct is one segment of SOURCE."))
    out.append(("Pocket",
                "One band of one column within one segment of another: the loans in both.",
                f"{_pocket(p)}: the {p['loans']:,} loans in {p['band']} that are also {p['seg']}." if p else
                "SCORE 620 - 679 / Direct: the loans in SCORE 620 - 679 that are also Direct."))
    gr = f.get("grid") if run else None
    out.append(("Grid",
                "Every band of one column crossed with every segment of another: one pocket for each pair that has "
                "loans.",
                f"{gr['name']}: {gr['bands']} bands by {gr['segments']} segments, {gr['pockets']} pockets." if gr
                else "SCORE x SOURCE: 5 bands by 3 segments, 15 pockets."))
    fl = f.get("filter") if run else None
    out.append(("Filter / Only loans where",
                "Shows Grids and Summary on only the loans with one value of the Filter by column. × book is still "
                "against the whole book.",
                (f"Only loans where {fl['col']} is {fl['value']}: the grid on those loans alone." if fl["picked"]
                 else f"Filter by {fl['col']} in the launcher, then pick {fl['value']}: the grid on those loans "
                      f"alone.") if fl else
                "Filter by SOURCE in the launcher, then pick Direct: the grid on Direct loans alone."))
    yrs = f.get("years") if run else None
    out.append(("Origination year",
                f"The year in the origination date column. {NO_DATE} holds the loans without a readable date.",
                f"This book's loans were made from {yrs[0]} to {yrs[1]}. Pick one year under Only loans where to "
                f"see it alone." if yrs else
                "Pick 2023 under Only loans where to see only the loans made in 2023."))
    wm = f.get("worse_material") if run else None
    out.append(("Worse and material",
                "Worse: at least Worse at times its comparison, with a p-value under the bar on Control. Material: "
                "its dollars above share reach the materiality line on Control.",
                f"At the last Run, {wm['n']:,} of {wm['of']:,} pockets were worse and material on GCOs." if wm else
                "4 of 81 pockets worse and material: those 4 pass both, and Start here lists them."))
    conf = g.get("confidence", 0.95)
    out.append(("Borderline",
                "The p-value is within the shuffle's own margin of the bar, so another Run could read it the other "
                "way. The verdict stands; the flag warns.",
                f"Worse? reads Yes · {stats.borderline_words(0.048, conf)}: under the {1 - conf:.0%} bar, but close "
                f"enough to turn on another Run."))
    sh = int(g.get("shuffles") or 10_000)
    out.append(("Shuffle test / p-value",
                "A p-value is how often chance alone would give a gap this big. The shuffle test deals the loans "
                "out at random, many times, and counts.",
                f"The loans are shuffled {sh:,} times. A p-value of 0.02 means about {round(sh * 0.02):,} of those "
                f"shuffles gave a gap at least as big."))
    mu = f.get("min_units") if run else None
    out.append(("Fewest loans in a pocket",
                "A pocket with fewer loans gets the exact test instead of the usual one. On Grids its cells are "
                "grey and not coloured.",
                f"At the last Run it was {mu:,.0f}: a pocket of fewer loans is grey on Grids."
                if isinstance(mu, (int, float)) else "Set at 30: a pocket of 20 loans is grey on Grids."))
    w = f.get("worse_at") if run else None
    b = f.get("better_at") if run else None
    out.append(("Worse at / Better at",
                "Worse at: how many times its comparison's rate a pocket must reach to read worse. Better at: how low "
                "it must fall to read better. Both are on Control.",
                f"At the last Run, worse at {w:.2f}× and better at {b:.2f}×. Against the book's {per100(gco_r)} "
                f"per $100 booked, worse needs {per100(gco_r * w)}." if w and b and real("gco_rate") else
                f"Worse at 1.25×: against {per100(gco_r)} per $100 booked, a pocket needs {per100(gco_r * 1.25)} to "
                f"read worse."))
    o = f.get("once") if run else None
    out.append(("Dollars above their share (each loan once)",
                "What pockets lost above their comparison's rate. Every loan sits in every grid, so each is counted "
                "once, in the pocket where it is furthest above its share.",
                f"At the last Run: {_usd(o['dollars'])} of GCOs above share, over {o['loans']:,} loans in "
                f"{o['pockets']:,} pockets worse and material." if o else
                "A loan in two worse pockets, $900 above share in one and $400 in the other, counts $900."))
    out.append(("Lifetime-to-date",
                "RANR and GCOs are over each loan's life so far, not per year. An older loan has had longer to bring "
                "in revenue and to charge off.",
                f"So compare vintages within a year: a {yrs[0]} loan has had longer than a {yrs[1]} one." if yrs
                else "So compare vintages within a year: a 2021 loan has had longer than a 2024 one."))
    out.append(("Months to charge-off",
                "For a loan that charged off, the calendar months from its origination date to its charge-off "
                "date. The day of the month is ignored.",
                "Made 15 Jan 2023, charged off 3 Mar 2024: 14 months. 31 Jan to 1 Feb is 1 month."))
    out.append(("Odd values",
                "Values that may be codes rather than real numbers: one value far more often than any other, or "
                "negatives in a column that's mostly positive.",
                "A score of -9999 on many loans is a code for no score. Answer Missing under Treat as on Columns."))
    mi = f.get("missing") if run else None
    out.append((f"{engine.MISSING_RULE_LABEL} / {engine.BLANK_LABEL}",
                f"Where a loan goes when it can't sit in a band. {engine.BLANK_LABEL}: the cell was empty. "
                f"{engine.MISSING_RULE_LABEL}: a value answered Missing.",
                f"{mi['loans']:,} loans sit in {mi['col']} {engine.MISSING_RULE_LABEL}: their value was answered "
                f"Missing. They are still counted." if mi else
                f"A score of -9999 answered Missing sits in SCORE {engine.MISSING_RULE_LABEL}, not in a band, and is "
                f"still counted."))
    return out


def stored(wb, found: str) -> dict | None:
    """The figures the last Run kept on _found, or None before the first Run."""
    if found not in wb.sheetnames:
        return None
    for a, b in wb[found].iter_rows(min_row=1, max_col=2, values_only=True):
        if a == FOUND_KEY and b:
            try:
                return json.loads(b)
            except ValueError:
                return None
    return None


def write(wb, f: dict | None, stamp: str | None = None) -> None:
    """The Glossary tab, afresh, right after Start here."""
    from openpyxl.styles import Alignment, Border, Font, Side
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    at = wb.sheetnames.index("Start here") + 1 if "Start here" in wb.sheetnames else 0
    ws = wb.create_sheet(SHEET, at)
    for c, w in WIDTHS.items():
        ws.column_dimensions[house._letter(c)].width = w
    house.title_band(ws, SHEET, "Every term the tabs use, in plain words, with an example.", TERM, EXAMPLE,
                     tab=house.TAB_RECORD)
    r = house.method_note(ws, 3, TERM, EXAMPLE, [
        ("Examples", MADE_UP if f is None else FROM_RUN.format(stamp=stamp) if stamp else
         FROM_RUN.replace(" ({stamp})", "")),
        ("Not live", "A line changed on Control after a Run moves the result tabs, not these examples."),
    ])
    house.header(ws, r, TERM, list(HEADS), centre_from=len(HEADS))
    head = r
    rule = Border(bottom=Side(style="thin", color=house.ROW_RULE))
    chars = {c: int(WIDTHS[c] * 1.15) for c in (TERM, MEANS, EXAMPLE)}      # as house.method_note reckons a line
    for term, means, example in rows(f):
        r += 1
        for col, v in ((TERM, term), (MEANS, means), (EXAMPLE, example)):
            c = ws.cell(row=r, column=col, value=v)
            c.font = Font(name="Calibri", size=10, bold=col == TERM, color=house.INK_TEXT)
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border = rule
        lines = max(house.lines_at(v, chars[col]) for col, v in ((TERM, term), (MEANS, means), (EXAMPLE, example)))
        ws.row_dimensions[r].height = 14 * lines + 4
    ws.freeze_panes = f"A{head + 1}"
    ws.print_title_rows = f"{head}:{head}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
