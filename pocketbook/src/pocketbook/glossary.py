"""Glossary: every term the tabs use, one a row, with an example in this book's own figures.

The firm, 2 Oct 2026, after explaining the grids' figures to their boss: "Maybe a nice glossary of terms in the
workbook should be there". Written by every Set up and every Run, right after Start here. Its examples use the
whole book's figures from the last Run (`figures`, kept on _found so Set up can write them again); before the first
Run they are made up, and the note says so. Where a tab already words a definition, the words here are that tab's.

Nothing here is a formula: the figures are the Run's, so a line changed on Control since does not move them.

Its words follow pocketbook/VOICE.md; the test keeps the contract-word list and the 28-word sentence cap here.
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
MADE_UP = "The examples are illustrative until the first Run. Each Run replaces them with this book's own figures."
FROM_RUN = "The examples use this book's figures for the whole book, from the last Run ({stamp})."
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
    out["co_date"] = bool(getattr(res.config, "chargeoff_date", None))
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
                "The dollar amount committed at origination. For cards, this is the credit line.",
                f"This book booked {_usd(f['booked'])} over {f.get('booked_loans', f['loans']):,} loans."
                if real("booked") else
                "A $10,000 loan is booked at $10,000, and a card with a $5,000 line is booked at $5,000."))
    # the firm, 2 Oct 2026: "booked dollar averages so more easily demonstrate how line assignments look in pockets"
    bl = f.get("booked_loans") if run else None
    avg = f["booked"] / bl if bl and real("booked") else None
    out.append(("Avg line / Line × book",
                "Avg line is the average committed line per loan: booked dollars divided by the number of loans "
                "with a booked amount. Line × book is a pocket's average line divided by the whole book's.",
                f"This book's average line is {_usd(avg)}, so a pocket averaging {_usd(avg * 1.24)} shows 1.24× on "
                f"Line × book." if avg else
                "A pocket with an average line of $6,200, in a book averaging $5,000, shows 1.24× on Line × book."))
    out.append(("GCOs ($)",
                "Gross charge-off dollars: the amount written off on a loan, before any recoveries.",
                f"This book's GCOs totaled {_usd(f['gco'])}, or {per100(gco_r)} per $100 booked." if real("gco") else
                f"GCOs of {_usd(GENERIC['gco'])} on {_usd(GENERIC['booked'])} booked equal {per100(gco_r)} per $100 "
                f"booked."))
    out.append(("RANR",
                "Risk-adjusted net revenue: what a loan earned after its losses. For cards, this is interest, fees "
                "and interchange, less rewards and charge-offs.",
                f"This book's RANR came to {_usd(f['ranr'])}. The book {_keeps(ranr_r)} per $100 booked."
                if real("ranr") else
                f"RANR of {_usd(GENERIC['ranr'])} on {_usd(GENERIC['booked'])} booked means the book "
                f"{_keeps(ranr_r)} per $100 booked."))
    out.append(("RANR + GCOs",
                "RANR with GCOs added back, which shows what the loans earned before losses.",
                f"This book earned {per100(contrib_r)} per $100 booked before losses and {_keeps(ranr_r)} after "
                f"them." if real("contrib", "ranr") else
                f"A book that earns {per100(contrib_r)} per $100 booked before losses and loses {per100(gco_r)} "
                f"{_keeps(ranr_r)}."))
    out.append(("Rate (GCOs ÷ Booked, RANR ÷ Booked)",
                "Dollars per $100 booked: the dollar figure divided by booked dollars. A rate of 2.20% equals $2.20 "
                "per $100 booked.",
                f"This book's GCOs ÷ Booked is {gco_r * 100:.2f}%, or {per100(gco_r)} lost per $100 booked."
                if real("gco") else
                f"GCOs ÷ Booked of {gco_r * 100:.2f}% means {per100(gco_r)} lost per $100 booked."))
    p = f.get("ranr_pocket") if run else None
    out.append(("Points (pts)",
                "The difference between two rates, in percentage points. A pocket at -3.00 pts keeps $3 less per "
                "$100 booked than its comparison.",
                f"{_pocket(p)} {_keeps(p['rate'])} per $100 booked and the rest of the book {_keeps(p['rest'])}. "
                f"The difference is {(p['rate'] - p['rest']) * 100:+.2f} pts." if p else
                "A pocket that keeps $1.45 per $100 booked, against $4.45 for the rest of the book, is at -3.00 pts."))
    p = f.get("gco_pocket") if run else None
    out.append(("× book / × rest of book",
                "A pocket's rate as a multiple of its comparison's: × book against the whole book, × rest of book "
                "against all other loans. 2.00× means twice the GCOs per booked dollar.",
                f"{_pocket(p)} loses {per100(p['rate'])} per $100 booked, which is {p['rate'] / gco_r:.2f}× book and "
                f"{p['rate'] / p['rest']:.2f}× rest of book." if p and real("gco_rate") and p["rest"] else
                "A pocket that loses $4.40 per $100 booked, in a book that loses $2.20, is at 2.00× book."))
    out.append(("Rest of book / rest of band",
                "The group a pocket is compared with: either every other loan in the book or every other loan in "
                "its band. The Judged against setting on Control determines which.",
                f"For {_pocket(p)}, the rest of band is every other {p['band']} loan. The rest of book is every "
                f"other loan in the book." if p else
                "For SCORE 620 - 679 / Direct, the rest of band is every other SCORE 620 - 679 loan."))
    out.append(("Bad loan",
                "A loan flagged as bad in the outcome column, according to the Yes means setting on Columns.",
                f"{f['bad']:,} of this book's {f['bad_den']:,} loans went bad, a rate of "
                f"{f['bad'] / f['bad_den']:.1%}." if real("bad", "bad_den") else
                f"{GENERIC['bad']:,} of {GENERIC['bad_den']:,} loans went bad, a rate of "
                f"{GENERIC['bad'] / GENERIC['bad_den']:.1%}."))
    out.append(("Band",
                "A range of values in a numeric column. Band edges on Columns set where each band starts; a column "
                "with few distinct values gets one band per value.",
                f"{p['band']} is one band of {p['band_col']}." if p else "SCORE 620 - 679 is one band of SCORE."))
    out.append(("Segment",
                "A single value of a category column, such as one channel.",
                f"{p['seg']} is one segment of {p['seg_col']}." if p else "Direct is one segment of SOURCE."))
    out.append(("Pocket",
                "The loans that fall in both one band of a numeric column and one segment of a category column.",
                f"{_pocket(p)} contains the {p['loans']:,} loans in {p['band']} that are also in {p['seg']}." if p
                else "SCORE 620 - 679 / Direct contains the loans in SCORE 620 - 679 that are also in Direct."))
    gr = f.get("grid") if run else None
    out.append(("Grid",
                "Every band of one column crossed with every segment of another, giving one pocket for each "
                "combination that has loans.",
                f"{gr['name']} has {gr['bands']} bands by {gr['segments']} segments, for {gr['pockets']} pockets."
                if gr else "SCORE x SOURCE has 5 bands by 3 segments, for 15 pockets."))
    fl = f.get("filter") if run else None
    out.append(("Filter / Only loans where",
                "Restricts Grids and Summary to the loans with one value of the Filter by column. Up to three "
                "filters can be selected; only loans matching every selected value are then shown. × book is still "
                "measured against the whole book.",
                (f"With Only loans where {fl['col']} is {fl['value']}, the grid shows those loans alone."
                 if fl["picked"] else
                 f"Choose {fl['col']} as Filter by in the launcher, then select {fl['value']} to see the grid for "
                 f"those loans alone.") if fl else
                "Choose SOURCE as Filter by in the launcher, then select Direct to see the grid for Direct loans "
                "alone."))
    yrs = f.get("years") if run else None
    out.append(("Origination year",
                f"The year of the loan's origination date. Loans without a readable date are grouped under "
                f"{NO_DATE}.",
                f"This book's loans were originated from {yrs[0]} to {yrs[1]}. Select a year under Only loans where "
                f"to view that year alone." if yrs else
                "Select 2023 under Only loans where to view only the loans originated in 2023."))
    # the firm, 3 Oct 2026: "Could the summary tab have vintage graphs as well?"; chosen: "Pocket vs rest vs book"
    out.append(("Vintage",
                "The loans originated in a given year. Summary's vintage chart plots one row against the rest of "
                "the book and the whole book, with a point for each year.",
                f"Selecting a row on Summary draws three lines, with one point per year from {yrs[0]} to {yrs[1]}."
                if yrs else
                "Selecting SCORE 620 - 679 on Summary draws its line, the rest of the book's and the whole book's, "
                "from 2021 to 2024."))
    wm = f.get("worse_material") if run else None
    out.append(("Worse and material",
                "A pocket is worse when its rate is at least Worse at times its comparison's, with a p-value below "
                "the threshold on Control. It is material when its dollars above share reach the materiality "
                "threshold on Control.",
                f"At the last Run, {wm['n']:,} of {wm['of']:,} pockets were worse and material on GCOs." if wm else
                "If 4 of 81 pockets are worse and material, those 4 meet both tests and are listed on Start here."))
    conf = g.get("confidence", 0.95)
    out.append(("Borderline",
                f"The shuffle test's p-value is within {stats.BORDERLINE_SE:g} standard errors of the threshold on "
                f"Control, on either side. The reading is unchanged, and the flag is shown beside it.",
                f"A Worse? cell reading Yes · {stats.borderline_words(0.048, conf)} has a p-value under the "
                f"{1 - conf:.0%} threshold and within {stats.BORDERLINE_SE:g} standard errors of it."))
    sh = int(g.get("shuffles") or 10_000)
    out.append(("Shuffle test / p-value",
                "The shuffle test reassigns loans at random many times and counts the shuffles with a gap at least as "
                "large as the actual one. The p-value is (that count + 1) ÷ (shuffles + 1).",
                f"The loans are shuffled {sh:,} times. A p-value of 0.02 means that about {round(sh * 0.02):,} of "
                f"those shuffles produced a gap at least as large."))
    mu = f.get("min_units") if run else None
    out.append(("Fewest loans in a pocket",
                "A pocket with fewer loans than this is tested with the exact test rather than the usual one. Its "
                "cells on Grids are grey rather than coloured.",
                f"At the last Run the minimum was {mu:,.0f}, so any pocket with fewer loans is grey on Grids."
                if isinstance(mu, (int, float)) else
                "With the minimum set at 30, a pocket of 20 loans is grey on Grids."))
    w = f.get("worse_at") if run else None
    b = f.get("better_at") if run else None
    out.append(("Worse at / Better at",
                "Worse at is the multiple of its comparison's rate a pocket must reach to be read as worse. Better "
                "at is the multiple it must fall to in order to be read as better. Both are set on Control.",
                f"At the last Run, Worse at was {w:.2f}× and Better at was {b:.2f}×. Against the book's "
                f"{per100(gco_r)} per $100 booked, a pocket needed {per100(gco_r * w)} to be read as worse."
                if w and b and real("gco_rate") else
                f"With Worse at set to 1.25× and a comparison rate of {per100(gco_r)} per $100 booked, a pocket needs "
                f"{per100(gco_r * 1.25)} to be read as worse."))
    o = f.get("once") if run else None
    out.append(("Dollars above their share (each loan once)",
                "The losses pockets incurred above their comparison's rate. Because every loan appears in every "
                "grid, each loan is counted once, in the pocket where it is furthest above its share.",
                f"At the last Run, {_usd(o['dollars'])} of GCOs were above share, across {o['loans']:,} loans in "
                f"{o['pockets']:,} pockets that were worse and material." if o else
                "A loan in two worse pockets, $900 above share in one and $400 in the other, is counted at $900."))
    out.append(("Lifetime-to-date",
                "RANR and GCOs are totals from each loan's origination date to the date of the extract. They are "
                "not annualized.",
                f"A loan originated in {yrs[0]} carries every RANR and GCO dollar recorded from {yrs[0]} to the "
                f"extract date." if yrs
                else "A loan originated in 2021 carries every RANR and GCO dollar recorded from 2021 to the extract "
                     "date."))
    if not run or f.get("co_date", True):   # a book with no charge-off date column never shows the measure
        out.append(("Months to charge-off",
                    "For a loan that charged off, the number of calendar months from its origination date to its "
                    "charge-off date, ignoring the day of the month.",
                    "A loan originated on 15 Jan 2023 and charged off on 3 Mar 2024 counts 14 months. 31 Jan to 1 "
                    "Feb counts as 1 month."))
    out.append(("Odd values",
                "Values that may be codes rather than genuine numbers, such as one value far more frequent than any "
                "other, or negative values in a mostly positive column.",
                f"A score of -9999 on many loans is shown as an odd value. Missing under Treat as on Columns places "
                f"those loans in {engine.MISSING_RULE_LABEL}."))
    mi = f.get("missing") if run else None
    out.append((f"{engine.MISSING_RULE_LABEL} / {engine.BLANK_LABEL}",
                f"Where a loan is placed when it cannot be assigned to a band. {engine.BLANK_LABEL} means the cell "
                f"was empty, and {engine.MISSING_RULE_LABEL} means its value was set to Missing on Columns.",
                f"{mi['loans']:,} loans are in {mi['col']} {engine.MISSING_RULE_LABEL} because their value was set "
                f"to Missing. They are still counted." if mi else
                f"A score of -9999 set to Missing is placed in SCORE {engine.MISSING_RULE_LABEL} rather than a band, "
                f"and is still counted."))
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
    house.title_band(ws, SHEET, "Definitions of the terms used on the tabs, each with an example.", TERM, EXAMPLE,
                     tab=house.TAB_RECORD)
    r = house.method_note(ws, 3, TERM, EXAMPLE, [
        ("Examples", MADE_UP if f is None else FROM_RUN.format(stamp=stamp) if stamp else
         FROM_RUN.replace(" ({stamp})", "")),
        ("Not live", "A setting changed on Control after a Run updates the result tabs, but not these examples."),
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
