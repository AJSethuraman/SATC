"""Leads found: the Dashboard's lead test run over every economic series against every bank credit series.

The firm, 23 Oct 2026, asked for "a mathematical and quick way to determine if any of these pass tests we care
about" and how it can be "done and shown in the book": every economic series against every bank series, the pairs
that hold first and then the near misses, with a line saying how many would hold by chance ("Economic vs bank",
"Holds, then near misses", "Yes" to the chance line).

The test is the Dashboard's, worked in Python on the same monthly changes its hidden tab holds, over every quarter
the two series share (the Dashboard opens on that span): one reading a year at each starting point, r and its pairs
at each; the effective pairs n x (1 - r1 r2) / (1 + r1 r2), never more than n, r1 and r2 each series' change against
its own a year earlier; p from Student's t on them, two-tailed, with its degrees of freedom cut to a whole number as
Excel's TDIST does; a lead tested only with a p at every starting point; the firm's level divided by the leads
tested; a lead holds when every starting point passes and they agree in sign. The lead spoken of is the strongest
that holds, else the strongest tested. A near miss: no lead holds, but the strongest has the same sign at every
starting point and passes at NEAR_FROM or more.

Changes are keyed by month number (year x 12 + month - 1), so a lead of L months is the key L on.
"""
import math

#: The chance line: each bank series shifted round its own span by these many whole years, and reversed in time,
#: so every link to an economic series is by chance while each keeps its own pattern from year to year.
SHIFTS = (4, 6, 8, 10)
#: Leads found lists a near miss from this many passing starting points. The firm, 24 Oct 2026, told that luck alone
#: gives up to 625 near misses and that 429 of the 825 found pass at only 1 of 4: "i think near miss of 2 or more is
#: fine". The Dashboard's line still states a lead passing at 1 of 4 as it is.
NEAR_FROM = 2


def pearson(xs, ys):
    """Pearson's r, None when there are fewer than two pairs or either side does not vary (CORREL's #DIV/0!)."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _betacf(a, b, x):
    """The continued fraction of the incomplete beta function (Numerical Recipes, 6.4)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)), -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1 + aa * d
            d = 1 / (d if abs(d) > tiny else tiny)
            c = 1 + aa / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1) < 1e-15:
            break
    return h


def _ibeta(a, b, x):
    """The regularised incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1 - front * _betacf(b, a, 1 - x) / b


def tdist2(t, df):
    """Excel's TDIST(t, df, 2): the two-tailed chance of a t at least this far from 0, df cut to a whole number;
    None when that leaves fewer than one degree of freedom (TDIST's #NUM!)."""
    df = int(df)
    if df < 1:
        return None
    return _ibeta(df / 2, 0.5, df / (df + t * t))


def year_apart(changes):
    """A series' change against its own a year (12 months) earlier, over every month that has both; None when
    there is no r to have, as the Dashboard leaves its cell blank."""
    pairs = [(v, changes[m + 12]) for m, v in changes.items() if m + 12 in changes]
    return pearson([a for a, _ in pairs], [b for _, b in pairs]) if pairs else None


def lead_test(first, second, leads, starts, p, min_pairs, years=None):
    """The Dashboard's lead table for two series' monthly changes ({month number: change}): one row per lead,
    {lead, rs, ns, ps, tested, avg, holds_in, same_sign, holds}, and the level each p was held to.

    ``years`` is the two series' year-apart correlations, when the caller has them already."""
    y1, y2 = years if years is not None else (year_apart(first), year_apart(second))
    at_start = [[(m, v) for m, v in first.items() if m % 12 == f * 12 // starts] for f in range(starts)]
    rows = []
    for lead in leads:
        rs, ns, ps = [], [], []
        for f in range(starts):
            xs, ys = [], []
            for m, v in at_start[f]:
                if m + lead in second:
                    xs.append(v)
                    ys.append(second[m + lead])
            n = len(xs)
            r = pearson(xs, ys)
            # None where the Dashboard's IFERROR leaves its cell blank, as when r1 x r2 is -1 (Codex on #473)
            e = (None if (r is None or y1 is None or y2 is None or 1 + y1 * y2 == 0)
                 else min(n, n * (1 - y1 * y2) / (1 + y1 * y2)))
            q = None
            if r is not None and e is not None and n >= min_pairs:
                q = tdist2(abs(r) * math.sqrt(max(e - 2, 0) / max(1 - r * r, 1e-12)), e - 2)
            rs.append(r)
            ns.append(n)
            ps.append(q)
        tested = min(ns) >= min_pairs and all(r is not None for r in rs) and all(q is not None for q in ps)
        rows.append({"lead": lead, "rs": rs, "ns": ns, "ps": ps, "tested": tested,
                     "avg": sum(rs) / starts if tested else None})
    tested = [row for row in rows if row["tested"]]
    level = p / max(len(tested), 1)
    for row in rows:
        if row["tested"]:
            row["holds_in"] = sum(1 for q in row["ps"] if q < level)
            row["same_sign"] = all(r > 0 for r in row["rs"]) or all(r < 0 for r in row["rs"])
            row["holds"] = row["holds_in"] == starts and row["same_sign"]
        else:
            row["holds_in"], row["same_sign"], row["holds"] = None, False, False
    return rows, level


def strongest(rows):
    """The lead the Dashboard speaks of: the strongest that holds, else the strongest tested (the first such in the
    order of the leads, as MATCH finds it); None when no lead is tested."""
    best, rank = None, -1
    for row in rows:
        if row["tested"]:
            mine = abs(row["avg"]) + (2 if row["holds"] else 0)
            if mine > rank:
                best, rank = row, mine
    return best


def verdict(row, near_from=NEAR_FROM):
    """'holds', 'near miss' (the same sign everywhere, passing at ``near_from`` starting points or more) or None."""
    if row is None:
        return None
    if row["holds"]:
        return "holds"
    if row["same_sign"] and row["holds_in"] >= near_from:
        return "near miss"
    return None


def screen(series, economic, bank, settings):
    """Every economic series against every bank series: [{economic, bank, verdict, row}] for each pair that holds
    or nearly does, and the number of pairs tried. ``series`` is {title: {month number: change}}."""
    leads, starts = settings["compare_leads"], settings["compare_starts"]
    p, min_pairs = settings["compare_p"], settings["compare_min_pairs"]
    years = {t: year_apart(series[t]) for t in economic + bank}
    found, tried = [], 0
    for a in economic:
        for b in bank:
            tried += 1
            rows, _ = lead_test(series[a], series[b], leads, starts, p, min_pairs, (years[a], years[b]))
            row = strongest(rows)
            said = verdict(row)
            if said:
                found.append({"economic": a, "bank": b, "verdict": said, "row": row})
    return found, tried


def scrambled(changes, how):
    """A series moved out of line in time: shifted round its own span by ``how`` whole years, each change keeping
    its calendar month, or (``how`` "reverse") mirrored across its span."""
    if not changes:
        return {}
    lo, hi = min(changes), max(changes)
    if how == "reverse":
        return {lo + hi - m: v for m, v in changes.items()}
    # Wrapped over whole years, so a reading keeps its month: over the span itself, a quarterly series' readings
    # would land in months no other series' readings are paired in, and nothing could ever hold.
    span = 12 * -(-(hi - lo + 1) // 12)
    # A shift of the whole span puts every reading back where it was: such a series moves half its span instead.
    shift = 12 * how % span or 12 * max(1, span // 24)
    return {lo + (m - lo + shift) % span: v for m, v in changes.items()}


def by_chance(series, economic, bank, settings):
    """How many pairs hold, and how many nearly do, with every bank series moved out of line in time:
    {how: {"holds": n, "near miss": n}}, for each shift in SHIFTS and the reversal."""
    out = {}
    for how in SHIFTS + ("reverse",):
        moved = dict(series)
        moved.update({b: scrambled(series[b], how) for b in bank})
        found, _ = screen(moved, economic, bank, settings)
        out[how] = {said: sum(1 for x in found if x["verdict"] == said) for said in ("holds", "near miss")}
    return out
