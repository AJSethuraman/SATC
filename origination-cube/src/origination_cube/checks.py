"""Check's newer lines: the pocket budget and coverage (fix 3.16), the family
count (fix 3.17), the product mix (fix 3.18), and the pre-spec (fix 3.15, in
confirmatory.py). Each returns (label, words) rows; book._check adds them after
its own, in one call, so nothing here moves a line Check already has.

The budget and the family count are docs/statistics.md B9:

    "Budget. From A4: at the suggested floor a testable pocket needs 5 expected
    bad loans, so the most pockets an extract can test is `expected bad loans
    / 5` (8,000 loans at 7.13% -> 114; 60,000 at 1.2% -> 144), and fewer in
    practice because loans never spread evenly. Print it beside the pocket count
    ..., and the coverage - the share of loans and dollars that sit in testable
    pockets."

    "Family count. How many grid x rate x comparison families the run contains
    (A2), with one line saying that a single red across many families is weak
    evidence."

The budget is printed per grid: every grid cuts the whole book again, so each
grid's pockets share the same bad loans, and each grid is held to the budget on
its own. The total across grids is printed beside it for the record, not
compared with the budget.

Testable means at or above fewest losses: since fix 3.7 a pocket below fewest
loans gets the exact test, so fewest losses is the only floor that stops a test.
"""

from __future__ import annotations

from . import confirmatory, engine
from .ingest import is_blank

#: A2 and A4: the expected bad loans a pocket needs at the suggested floor.
PER_POCKET = 5
OUTCOME = "outcome_loans"                  # the yes/no outcome, share of loans: what the budget counts
BOOKED = "outcome_booked"                  # its bottom is the booked amount: what the dollar coverage counts
COMPARISONS = (("p_book", "the rest of the book"), ("p_band", "the rest of its band"))


def _n(k: int, word: str) -> str:
    return f"{k:,} {word}" + ("" if k == 1 else "s")


def attach(book, about: dict | None, res) -> None:
    """After the engine has run: what the later lines need from the workbook.
    The band edges typed on Columns (the Prevalence tab's bands for a column
    that isn't cut), and the pre-spec's state (confirmatory.py). Never raises
    for a pre-spec: a problem reading one is a line on Check, not a failed run."""
    about = about or {}
    res.typed_edges = dict(about.get("_typed_edges") or {})
    res.prespec = confirmatory.state(book, about, res)


def rows(res) -> list[tuple[str, str]]:
    """Every newer Check line, in order: the pre-spec first (it says what this
    run is held to), then the budget and coverage, the families, the pockets alone in
    their band, the products."""
    return (confirmatory.check_rows(res) + budget_rows(res) + family_rows(res) + alone_rows(res)
            + product_rows(res))


# --------------------------------------------------------------------------
# 3.16 The pocket budget and coverage


def names(res) -> dict[str, str]:
    """A grid's band and segment names as the extract names them (book._names)."""
    cfg = res.config
    out = {b.name: b.field for b in cfg.bands}
    out.update({d.name: d.field for d in cfg.dimensions})
    if cfg.split:
        out.update({f"{d.name} / {cfg.split[0]}": f"{d.field} / {cfg.split[0]}" for d in cfg.dimensions})
    return out


def budget(res) -> tuple[int, int] | None:
    """(the book's bad loans, the most pockets they can test), or None when the
    run has no yes/no outcome or no settings to test with."""
    if res.config.benchmark is None or OUTCOME not in res.total.rates:
        return None
    bad = int(round(res.total.rates[OUTCOME].num))
    return bad, bad // PER_POCKET


def coverage(res, grid) -> tuple[int, int, float, float]:
    """(pockets, testable pockets, share of loans in them, share of booked dollars in them)."""
    floor = res.config.benchmark.min_events
    cells = [c for _, c in grid.inner()]
    ok = [c for c in cells if c.rates[OUTCOME].events >= floor]
    loans = sum(c.rows for c in cells)
    dollars = sum(c.rates[BOOKED].den for c in cells) if BOOKED in res.total.rates else 0.0
    share_d = (sum(c.rates[BOOKED].den for c in ok) / dollars) if dollars else 0.0
    return len(cells), len(ok), (sum(c.rows for c in ok) / loans if loans else 0.0), share_d


def budget_rows(res) -> list[tuple[str, str]]:
    got = budget(res)
    if got is None:
        return []
    bad, most = got
    floor = res.config.benchmark.min_events
    nm = names(res)
    out = [("Pocket budget", f"At most {most:,} pockets per grid can be tested: at the suggested floor a pocket "
                             f"needs to expect {PER_POCKET} bad loans, and the book has {bad:,} ({bad:,} ÷ "
                             f"{PER_POCKET} = {most:,}). Fewer in practice, since loans never spread evenly. Each "
                             f"grid cuts the whole book again, so each grid is held to this on its own.")]
    over = []
    grids = [(g, "") for g in res.grids] + [(g, "Three-way: ") for g in res.three_way]
    total = 0
    for g, kind in grids:
        n, ok, loans, dollars = coverage(res, g)
        total += n
        head = f"{kind}{nm.get(g.band, g.band)} x {nm.get(g.dimension, g.dimension)}"
        out.append((f"Pockets: {head}", f"{_n(n, 'pocket')}, against a budget of {most:,}. {ok:,} "
                                        f"{'has' if ok == 1 else 'have'} at least {floor:,} bad loans and can be "
                                        f"tested, holding {loans:.0%} of the loans and {dollars:.0%} of the booked "
                                        f"dollars."))
        if n > most:
            over.append((head, n))
    out.append(("Pockets in all", f"{_n(total, 'pocket')} across {_n(len(grids), 'grid')}. Testable means at least "
                                  f"{floor:,} bad loans (fewest losses): that is the only floor that stops a test "
                                  f"now, since a pocket under fewest loans gets the exact test."))
    for head, n in over:
        out.append(("Warning", f"{head} has {n:,} pockets, more than the {most:,} this book can test. Most will "
                               f"have too few bad loans to say anything: use fewer bands or segments."))
    return out


# --------------------------------------------------------------------------
# 3.17 The families of tests


def families(res) -> list[tuple[str, str, str, str, int]]:
    """Every family the allowance for many tests works within (A2): one grid,
    one rate, one comparison, holding at least one test. (kind, grid, rate,
    comparison, tests). The pocket grids and the three-way grids each compare a
    pocket with the rest of the book and with the rest of its band; the split's
    halves are compared with each other, a family per grid and rate."""
    out = []
    rates = [m for m in res.measures if m.is_rate]
    for kind, grids in (("grids", res.grids), ("three-way grids", res.three_way)):
        for g in grids:
            for m in rates:
                for attr, words in COMPARISONS:
                    k = sum(1 for _, c in g.inner() if getattr(c.rates[m.name], attr) is not None)
                    if k:
                        out.append((kind, f"{g.band} x {g.dimension}", m.name, words, k))
    for g in res.grids:
        for m in rates:
            k = sum(1 for got in g.split_compare.values() if m.name in got and got[m.name][1] is not None)
            if k:
                out.append(("split halves", f"{g.band} x {g.dimension}", m.name, "the other half", k))
    return out


def family_rows(res) -> list[tuple[str, str]]:
    b = res.config.benchmark
    if b is None:
        return []
    fam = families(res)
    n, tests = len(fam), sum(f[4] for f in fam)
    if not n:
        return [("Families of tests", "none: nothing was tested")]
    parts = []
    for kind in ("grids", "three-way grids", "split halves"):
        mine = [f for f in fam if f[0] == kind]
        if not mine:
            continue
        g, r, c = (len({f[i] for f in mine}) for i in (1, 2, 3))
        grids = _n(g, "grid") if kind != "three-way grids" else _n(g, "three-way grid")
        if g * r * c != len(mine):
            parts.append(f"{len(mine):,} on the {kind}")
        elif kind == "split halves":
            parts.append(f"{grids} x {_n(r, 'rate')} for the split's halves")
        else:
            parts.append(f"{grids} x {_n(r, 'rate')} x {_n(c, 'comparison')}")
    out = [("Families of tests", f"{n:,}, holding {tests:,} tests: {'; '.join(parts)}. A family is one grid, one "
                                 f"rate and one comparison (against the rest of the book, the rest of its band, "
                                 f"or the other half).")]
    if b.many_tests == "none":
        out.append(("Reading a single red", f"No allowance for many tests is in use, so each of the {tests:,} tests "
                                            f"stands alone: a single red among them is weak evidence."))
    else:
        out.append(("Reading a single red", f"Each family gets its own allowance for many tests, not one for the "
                                            f"whole run. So a single red across {n:,} families is weak evidence."))
    return out


def alone_rows(res) -> list[tuple[str, str]]:
    """Under the rest of its band, the pockets with nothing else in their band: each was compared with
    the rest of the book instead (the firm, 26 Sep 2026). Counted once, whatever the rate."""
    k = sum(1 for g in (*res.grids, *res.three_way) for _, c in g.inner() if any(s.alone for s in c.rates.values()))
    if not k:
        return []
    return [("Alone in its band", f"{_n(k, 'pocket')} had no other pocket in its band, so "
                                  f"{'it was' if k == 1 else 'they were'} compared with the rest of the book.")]


# --------------------------------------------------------------------------
# 3.18 Products mixed in a pocket


def product_rows(res) -> list[tuple[str, str]]:
    """A warning for each column marked Credit product that holds more than one
    product among the loans run and is not a band or segment: profit per dollar
    is then compared across products. Warn only; the firm decides."""
    from .prevalence import rows_run
    cfg = res.config
    marked = [c for c, (means, _) in (cfg.columns or {}).items() if means == "product"]
    if not marked:
        return []
    cut = {b.field for b in cfg.bands} | {d.field for d in cfg.dimensions}
    out = []
    for col in marked:
        if col in cut:
            continue
        rule = cfg.missing.get(col)
        seen = sorted({engine.classify_text(r.get(col), rule) for r in rows_run(res) if not is_blank(r.get(col))})
        if len(seen) < 2:
            continue
        some = ", ".join(seen[:4]) + (f" and {len(seen) - 4:,} more" if len(seen) > 4 else "")
        split = (f" It splits the pockets, so only the Three-way tab keeps products apart."
                 if cfg.split and cfg.split[0] == col else "")
        out.append(("Warning", f"{col} holds {len(seen):,} credit products ({some}) and isn't a band or segment, "
                               f"so profit per booked dollar is compared across products. A pocket can read "
                               f"better or worse just for holding more of one.{split}"))
    return out
