"""The Scouting tab (Goal 2 item 9), and what Record, the Log and the launcher say about scouting.

House style as the result tabs (the redesign's phases 2 to 4): the title band, one folding "How this tab works" note
that says every test and choice once (tenet T1), tiles, then the results on rows: every candidate ranked, its
importance with and without the held-fixed columns, its suggested bins and reference, the candidates it moves with,
and whether it is proposed. Under the table: the held-fixed columns' own importance, the pre-spec as written, and the
shape behind each proposed candidate's bins.

Nothing here is live: scouting is worked out at the Run, and the tab says so.
"""

from __future__ import annotations

import math

from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.styles import Alignment, Border, Font, Side

from . import engine, house, scout

SHEET = scout.SHEET
INK, SLATE = house.INK_TEXT, house.SLATE
FIRST, LAST = 2, 10
(S_NAME, S_RANK, S_IMP, S_HELD, S_BINS, S_REF, S_PART, S_PROP, S_WHY) = range(2, 11)
WIDTHS = {1: 2, S_NAME: 22, S_RANK: 6, S_IMP: 13, S_HELD: 17, S_BINS: 34, S_REF: 16, S_PART: 24, S_PROP: 11,
          S_WHY: 22}
IMP_FMT = "0.0000"
YES, NO = "Yes", "No"


def _cell(ws, r, c, v=None, *, bold=False, color=INK, h="center", fmt=None, size=10, wrap=False):
    x = ws.cell(row=r, column=c, value=v)
    x.font = Font(name="Calibri", bold=bold, size=size, color=color)
    x.alignment = Alignment(horizontal=h, vertical="center", wrap_text=wrap)
    if fmt:
        x.number_format = fmt
    return x


def _held(sc) -> str:
    return " and ".join(sc.hold)


def _bins_words(c) -> str:
    if not c.bins:
        return ""
    return "; ".join(c.groups)


def _partners(c) -> str:
    return ", ".join(f"{n} ({r:+.2f})" for n, r in c.partners)


def _imp(v):
    return None if v is None or not math.isfinite(v) else round(v, 6)


def _method(sc, stamp: str) -> list[tuple[str, str]]:
    held = _held(sc)
    n = len(sc.candidates)
    auc = f"{sc.auc:.3f}" if sc.auc is not None else "not worked out"
    out = [
        ("What it is", f"Scouting: which of the {n} candidates the book leans on, and where each one bends. It "
                       f"nominates; it never confirms (statistics.md B7). The confirmation is the New variables tab, "
                       f"on loans scouting never read."),
        ("Found on", f"{sc.n_dev:,} development loans made {sc.development.text()}, {sc.n_dev_bad:,} of them bad: the "
                     f"first {sc.share:.0%} of the loans by origination date. The {sc.n_held_back:,} loans made after "
                     f"them are held back. Only their dates were read here, to draw the line and to name the "
                     f"holdout's range; their outcomes and every other value were not."
                     + (f" Left out: {'; '.join(f'{v:,} with {k}' for k, v in sc.left_out.items())}."
                        if sc.left_out else "")),
        ("Candidates", "The columns ticked Test it in the launcher, and every new column made on Columns (one column "
                       "divided by another), each fed in as a column in its own right. A category is given one "
                       "number per value, in the order of its values."),
        ("The forest", f"A random forest: {scout.TREES} trees, each leaf at least {scout.LEAF} loans, seed "
                       f"{scout.SEED}, grown by scikit-learn {sc.version}. Each tree splits the loans wherever a cut "
                       f"best separates bad from good, and the forest averages their votes. It writes no formula and "
                       f"assumes no shape. The same extract gives the same forest; another version of scikit-learn "
                       f"may not."),
        ("Importance", f"How far the forest's AUC drops when the column is shuffled, on loans it did not train on. "
                       f"AUC is the chance a random bad loan scores above a random good one; 0.5 is a coin flip. The "
                       f"development loans are cut into {scout.FOLDS} runs by date; each run is scored by a forest "
                       f"grown on the other two, with {scout.REPEATS} shuffles of each column, and the drops are "
                       f"averaged. The forest's own AUC is {auc}. It is a ranking: no direction, no size and no "
                       f"range, and it leans towards columns with many distinct values."),
    ]
    if sc.hold:
        auc_h = f"{sc.auc_held:.3f}" if sc.auc_held is not None else "not worked out"
        out.append(("With and without", f"Importance is from a forest given the candidates alone. The next column "
                                         f"is from a forest given {held} as well (AUC {auc_h}): a candidate that "
                                         f"drops there was mostly telling you {held}. Their own importance is under "
                                         f"the table."))
    else:
        out.append(("With and without", "No column was chosen to Hold fixed in the launcher, so there is one "
                                         "forest, with the candidates alone."))
    floor = f"{sc.floor:.4f}" if sc.floor is not None else "not worked out"
    out += [
        ("Noise floor", f"{floor}: the largest importance any candidate reached in the same forests grown on the "
                        f"development loans with their outcomes shuffled among them, so that no column could matter "
                        f"({sc.draws:,} tries). It is what a column scores by chance."),
        ("Proposed?", "Yes for a number column whose importance is above the noise floor, with the held-fixed columns "
                      "in the forest or without them, and whose shape bends somewhere to cut. A category is ranked "
                      "and not proposed: the pre-spec cuts a number at its bins."),
        ("Suggested bins", f"From the shape: the forest's bad rate with the column set to one value for every loan "
                           f"(partial dependence, on {scout.PD_ROWS:,} development loans drawn by seed), over the "
                           f"column's own percentiles, from a forest grown on every development loan"
                           + (f" with {held} in it" if sc.hold else "") + f". A cut goes where the curve steps by at "
                           f"least {scout.STEP:.0%} of its average, largest step first, each group holding at least "
                           f"{scout.MIN_SHARE:.0%} of the loans, at most {scout.MAX_GROUPS} groups. Inside each step "
                           f"the edge sits where the forest itself split the column most, rounded to two figures. "
                           f"The shapes are under the table."),
        ("Reference", "The group holding the development loans' median value: the ordinary case, which every other "
                      "group is compared with."),
        ("Correlated with", f"Candidates, and held-fixed number columns, whose values rise and fall together with "
                            f"this one: a rank correlation (Spearman's) of {scout.CORRELATED:.1f} or more either way, "
                            f"on the development loans with both. Importance splits between such columns, and the "
                            f"shape of one can borrow the other's."),
        ("The pre-spec", "PocketBook writes the pre-spec from the proposed candidates beside the workbook, when there "
                         "is none, and the confirmation reads it. One that is there already is confirmed as it "
                         "stands: an edit is yours to make, and Record logs it. The file is under the table."),
        ("As of", f"The last Run, {stamp}. Nothing here follows Control until the next Run."),
    ]
    return out


def write(wb, res, stamp: str = "") -> None:
    sc = getattr(res, "scout", None)
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    if sc is None:
        return
    ws = wb.create_sheet(SHEET)
    for c, w in WIDTHS.items():
        ws.column_dimensions[house._letter(c)].width = w
    held = _held(sc)
    house.title_band(ws, SHEET, f"Which of the {len(sc.candidates) or 'ticked'} candidates does the book lean on, "
                                f"and where does each one bend? On the development loans only.", FIRST, LAST,
                     tab=house.TAB_RESULT)
    if sc.problem:
        r = house.method_note(ws, 3, FIRST, LAST, [("Not run", f"Scouting couldn't be run: {sc.problem}.")])
        _finish(ws, r)
        return
    r = house.method_note(ws, 3, FIRST, LAST, _method(sc, stamp or "as of the last Run"))

    # the tiles
    tiles = [("Outcome", sc.outcome, S_NAME, S_RANK),
             ("Candidates · proposed", f"{len(sc.candidates)} · {len(sc.proposed)} proposed", S_IMP, S_HELD),
             ("Held fixed", " · ".join(sc.hold) or "Nothing", S_BINS, S_BINS),
             ("Noise floor", sc.floor, S_REF, S_REF),
             ("Development loans", f"{sc.n_dev:,} · {sc.n_dev_bad:,} bad", S_PART, S_WHY)]
    for label, value, a, b in tiles:
        house.tile(ws, r, a, b, label, value, fmt=IMP_FMT if label == "Noise floor" else None,
                   top=house.KEY_RED if label.startswith("Candidates") else house.INK)
    r += 3
    _cell(ws, r, FIRST, f"Worked out at the last Run, {stamp or 'as of the last Run'}, on the development loans. "
                        f"Ranked by the larger of the two importances.", color=SLATE, h="left", size=9)
    r += 2

    # the table
    head = r
    house.header(ws, head, FIRST, ["Candidate", "Rank", "Importance", f"{held} held fixed" if sc.hold else
                                   "Held fixed", "Suggested bins", "Reference", "Correlated with", "Proposed?",
                                   "Why"], centre_from=1)
    for c in range(FIRST, LAST + 1):
        ws.cell(row=head, column=c).alignment = Alignment(
            horizontal="left" if c in (S_NAME, S_BINS, S_PART, S_WHY) else "center", vertical="center",
            wrap_text=True)
    ws.row_dimensions[head].height = 30
    r = head + 1
    first_row = r
    for c in sc.candidates:
        vals = {S_RANK: c.rank, S_NAME: c.name, S_IMP: _imp(c.importance),
                S_HELD: _imp(c.importance_held) if sc.hold else "Nothing held",
                S_BINS: _bins_words(c) or ("" if c.kind == scout.NUMBER else "Each value"),
                S_REF: c.reference or "", S_PART: _partners(c), S_PROP: YES if c.proposed else NO, S_WHY: c.why}
        for col, v in vals.items():
            _cell(ws, r, col, v, bold=col in (S_NAME, S_PROP) and c.proposed,
                  h="left" if col in (S_NAME, S_BINS, S_PART, S_WHY) else "center",
                  fmt=IMP_FMT if col in (S_IMP, S_HELD) and isinstance(v, float) else None,
                  color=INK if c.proposed or col in (S_NAME,) else SLATE)
        for col in range(FIRST, LAST + 1):
            ws.cell(row=r, column=col).border = Border(bottom=Side(style="thin", color=house.ROW_RULE))
        if c.proposed:
            p = ws.cell(row=r, column=S_PROP)
            p.fill = house.fill(house.POSITIVE_BG)
            p.font = Font(name="Calibri", bold=True, size=10, color=house.POSITIVE)
        ws.row_dimensions[r].height = 18
        r += 1
    last_row = r - 1
    ws.freeze_panes = f"A{head + 1}"
    r += 1

    if sc.held:
        house.section(ws, r, FIRST, LAST, f"Held fixed, for comparison: their own importance with the candidates")
        r += 1
        house.sub_header(ws, r, FIRST, ["Column", "", "Importance"], centre_from=2)
        r += 1
        for name, v in sc.held:
            _cell(ws, r, S_NAME, name, h="left")
            _cell(ws, r, S_IMP, _imp(v), fmt=IMP_FMT)
            r += 1
        r += 1

    # the pre-spec
    house.section(ws, r, FIRST, LAST, "The pre-spec")
    r += 1
    for line in file_words(sc):
        r = _line(ws, r, line)
    if sc.path is not None and sc.path.is_file():
        r += 1
        for line in sc.path.read_text(encoding="utf-8").splitlines():
            ws.merge_cells(start_row=r, start_column=S_NAME, end_row=r, end_column=LAST)
            _cell(ws, r, S_NAME, line, h="left", size=9).font = Font(name="Consolas", size=9, color=INK)
            r += 1
    r += 1

    # the shapes behind the proposed candidates' bins
    for c in sc.proposed:
        r = _shape(ws, c, r)
    _finish(ws, r)
    # no print titles (K, the firm, 27 Sep 2026): repeated on every printed page, the candidates' header sat over the
    # pre-spec file where it starts
    _ = first_row, last_row


def _line(ws, r: int, text: str) -> int:
    ws.merge_cells(start_row=r, start_column=S_NAME, end_row=r, end_column=LAST)
    x = _cell(ws, r, S_NAME, text, h="left", wrap=True)
    x.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws.row_dimensions[r].height = 15.0 * max(1, math.ceil(len(text) / 150)) + 4
    return r + 1


def curve_format(curve) -> str:
    """How a curve's values are shown: whole numbers with thousands for a column in the hundreds and up (a debt of
    733.1264 dollars read as that, on the walk of 27 Sep 2026), up to four places for a ratio."""
    top = max((abs(x) for x, _ in curve), default=0)
    return "#,##0" if top >= 100 else "0.####"


def _shape(ws, c, r: int) -> int:
    """One proposed candidate's curve: its values and the forest's bad rate, and a chart of them with the edges."""
    house.section(ws, r, FIRST, LAST, f"{c.name}: the forest's bad rate as {c.name} moves (cut at "
                                      f"{', '.join(scout._num(x) for x in c.bins)})")
    r += 1
    house.sub_header(ws, r, FIRST, [c.name, "", "Bad rate"], centre_from=2)
    r += 1
    top = r
    fmt = curve_format(c.curve)
    for x, p in c.curve:
        _cell(ws, r, S_NAME, x, h="left", fmt=fmt)
        _cell(ws, r, S_IMP, p, fmt="0.0%")
        r += 1
    ch = ScatterChart()
    ch.title = f"{c.name}: the forest's bad rate"
    ch.style = 13
    ch.x_axis.title = c.name
    ch.y_axis.title = "Bad rate"
    ch.y_axis.number_format = "0%"
    ch.y_axis.majorGridlines = None
    ch.legend = None
    s = Series(Reference(ws, min_col=S_IMP, min_row=top, max_row=r - 1),
               Reference(ws, min_col=S_NAME, min_row=top, max_row=r - 1), title="Bad rate")
    s.graphicalProperties.line.solidFill = house.INK
    s.marker.symbol = "circle"
    s.marker.size = 4
    ch.series.append(s)
    ch.height, ch.width = 7.0, 16.0
    ws.add_chart(ch, f"{house._letter(S_BINS)}{top}")
    return max(r, top + 15) + 1


def _finish(ws, last_row: int) -> None:
    ws.print_area = f"B1:{house._letter(LAST)}{last_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


# --------------------------------------------------------------------------
# What the other places say


def file_words(sc) -> list[str]:
    """The pre-spec's line or two: written, kept, or none."""
    if sc.path is None:
        return ["Scouting proposed no candidate, so no pre-spec was written and nothing was confirmed."]
    name = sc.path.name
    if sc.action == scout.WROTE:
        return [f"Written by this Run: {name}, beside the workbook, fingerprint {sc.fingerprint}, before any "
                f"held-back loan was tested. Edit it if you like; Record logs every change."]
    if sc.action == scout.SAME:
        return [f"{name} was already beside the workbook, and says what this Run's scouting proposes. It was "
                f"confirmed as it stands (fingerprint {sc.fingerprint})."]
    out = [f"{name} was already beside the workbook, so it was confirmed as it stands (fingerprint "
           f"{sc.fingerprint}) and not written again. Delete it to have the next Run write this proposal."]
    if sc.differs:
        out.append("Where it differs from this Run's proposal: " + "; ".join(sc.differs) + ".")
    elif not sc.proposed:
        out.append("This Run's scouting proposed no candidate.")
    return out


def log_lines(res) -> list[str]:
    """The Log's line for scouting, ahead of any held-back result (record, don't block)."""
    sc = getattr(res, "scout", None)
    if sc is None:
        return []
    if sc.problem:
        return [f"Scouting couldn't be run: {sc.problem}."]
    head = (f"Scouting on {sc.n_dev:,} development loans made {sc.development.text()} (the {sc.n_held_back:,} held "
            f"back not read): {len(sc.proposed)} of {len(sc.candidates)} candidates proposed"
            + (f" ({', '.join(c.name for c in sc.proposed)})" if sc.proposed else "") + ".")
    if sc.path is None:
        return [head + " No pre-spec written."]
    if sc.action == scout.WROTE:
        return [head + f" Wrote the pre-spec {sc.path.name} on {sc.written_on.isoformat()}: fingerprint "
                       f"{sc.fingerprint}."]
    return [head + f" Kept the pre-spec {sc.path.name} as it stands: fingerprint {sc.fingerprint}"
                   + (f", {len(sc.differs)} difference{'s' if len(sc.differs) != 1 else ''} from the proposal"
                      if sc.differs else "") + "."]


def check_rows(res) -> list[tuple[str, str]]:
    """Record's lines on scouting."""
    sc = getattr(res, "scout", None)
    if sc is None:
        return []
    if sc.problem:
        return [("Scouting", f"Couldn't be run: {sc.problem}.")]
    out = [("Scouting", f"{len(sc.candidates)} candidates on {sc.n_dev:,} development loans made "
                        f"{sc.development.text()}; {len(sc.proposed)} proposed"
                        + (f": {', '.join(c.name for c in sc.proposed)}" if sc.proposed else "") + ". See the "
                        f"Scouting tab."),
           ("Scouting held back", f"{sc.n_held_back:,} loans made {sc.holdout.text()}: none of their outcomes or "
                                  f"values was read by scouting."),
           ("Scouting's pre-spec", " ".join(file_words(sc)))]
    out.append(("Tests: scouting", f"A random forest (scikit-learn {sc.version}, {scout.TREES} trees, leaves of at "
                                   f"least {scout.LEAF}, seed {scout.SEED}) ranking by permutation importance, "
                                   f"cross-fitted in {scout.FOLDS} runs by date, against a noise floor from shuffled "
                                   f"outcomes; bins from partial dependence and the forest's own splits."))
    return out


def launcher_lines(res) -> list[str]:
    return log_lines(res)
