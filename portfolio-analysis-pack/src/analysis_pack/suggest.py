"""`pack suggest`: band cut points proposed from the data, with the counts
each would produce, so the person writing the question file chooses with
the numbers in view. Nothing here writes to the file.

Three schemes are offered for a numeric field (PRD §6.6): equal-count by
loans (thirds and quarters, the percentiles), equal-count by events (each
band holds about the same number of outcome events, which is what keeps the
intervals narrow), and the nearest round numbers to the equal-count-by-loans
thirds. A fourth number is printed as information only and marked as such:
the single cut at which the outcome rate changes most (the first split a
tree would make). Choosing bands on the outcome and then testing whether the
effect survives inside them reads stronger than it is, so it is not offered
as a scheme.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .ingest import Bad, is_blank, parse_number
from .population import Population, bucket_index, bucket_labels, fmt_edge

THIN_EVENTS = 10


@dataclass
class SchemeSuggestion:
    name: str
    edges: tuple[float, ...]
    labels: list[str]
    loans: list[int]
    events: list[int]

    def thin(self) -> list[bool]:
        return [e < THIN_EVENTS for e in self.events]


@dataclass
class Suggestion:
    field: str
    outcome_key: str
    outcome_label: str
    loans: int
    events: int
    schemes: list[SchemeSuggestion]
    outcome_cut: float | None
    outcome_cut_rates: tuple[float | None, float | None]


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _round_nice(x: float) -> float:
    """Snap to the nearest of 1, 2, 2.5, 5 x 10^k."""
    if x <= 0:
        return x
    k = math.floor(math.log10(x))
    base = 10 ** k
    candidates = [m * base for m in (1, 2, 2.5, 5, 10)]
    return min(candidates, key=lambda c: abs(c - x))


def _dedupe(edges: list[float]) -> tuple[float, ...]:
    out: list[float] = []
    for e in edges:
        if not out or e > out[-1]:
            out.append(e)
    return tuple(out)


def _counts(pairs: list[tuple[float, int]], edges: tuple[float, ...]) -> tuple[list[int], list[int]]:
    k = len(edges) + 1
    loans = [0] * k
    events = [0] * k
    for v, e in pairs:
        i = bucket_index(v, edges)
        loans[i] += 1
        events[i] += e
    return loans, events


def suggest(pop: Population, field: str, outcome_key: str | None = None) -> Suggestion:
    od = pop.outcomes[0] if outcome_key is None else next(o for o in pop.outcomes if o.key == outcome_key)

    def numeric(l) -> float | None:
        # a confounder or control was typed when the population was built; any
        # other column (the rule's own fields, say) is read from the raw row on
        # demand (PRD §6.6 "--field COL on demand"; adversarial finding 13)
        v = l.values.get(field) if field in l.values else parse_number(l.raw.get(field))
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    pairs = [(v, int(l.events.get(od.key, False))) for l in pop.seasoned for v in (numeric(l),) if v is not None]
    if not pairs:
        text_values = sum(1 for l in pop.seasoned if not is_blank(l.raw.get(field)))
        if text_values:
            raise ValueError(f"`{field}` is not a numeric column; band cut points need numbers (adversarial finding 14)")
        raise ValueError(f"no seasoned loan carries a numeric value in `{field}`")
    pairs.sort(key=lambda t: t[0])
    vals = [v for v, _ in pairs]
    total_events = sum(e for _, e in pairs)
    schemes: list[SchemeSuggestion] = []

    def add(name: str, edges: tuple[float, ...]):
        if not edges:
            return
        loans, events = _counts(pairs, edges)
        schemes.append(SchemeSuggestion(name, edges, bucket_labels(edges), loans, events))

    thirds = _dedupe([_quantile(vals, 1 / 3), _quantile(vals, 2 / 3)])
    quarters = _dedupe([_quantile(vals, 0.25), _quantile(vals, 0.5), _quantile(vals, 0.75)])
    add("by_loans_thirds", thirds)
    add("by_loans_quarters", quarters)
    # equal events: walk the sorted pairs and cut where cumulative events cross the thirds
    if total_events >= 3:
        cuts = []
        cum = 0
        targets = [total_events / 3, 2 * total_events / 3]
        ti = 0
        for v, e in pairs:
            cum += e
            while ti < len(targets) and cum >= targets[ti]:
                cuts.append(v)
                ti += 1
        add("by_events_thirds", _dedupe(cuts))
    add("round", _dedupe([_round_nice(e) for e in thirds]))

    # the outcome-driven cut: the split that most reduces Gini impurity (information only)
    best_cut, best_gain, best_rates = None, 0.0, (None, None)
    n = len(pairs)
    p_all = total_events / n
    gini_all = 2 * p_all * (1 - p_all)
    candidates = sorted(set(_quantile(vals, q / 200) for q in range(1, 200)))
    cum_n = cum_e = 0
    idx = 0
    for cut in candidates:
        while idx < n and pairs[idx][0] < cut:
            cum_n += 1
            cum_e += pairs[idx][1]
            idx += 1
        if cum_n == 0 or cum_n == n:
            continue
        p_lo = cum_e / cum_n
        p_hi = (total_events - cum_e) / (n - cum_n)
        gini = (cum_n / n) * 2 * p_lo * (1 - p_lo) + ((n - cum_n) / n) * 2 * p_hi * (1 - p_hi)
        gain = gini_all - gini
        if gain > best_gain:
            best_gain, best_cut, best_rates = gain, cut, (p_lo, p_hi)
    return Suggestion(field=field, outcome_key=od.key, outcome_label=od.label, loans=n, events=total_events,
                      schemes=schemes, outcome_cut=best_cut, outcome_cut_rates=best_rates)


def render_text(s: Suggestion) -> str:
    lines = [f"{s.field}: {s.loans:,} seasoned loans with a value, {s.events:,} events ({s.outcome_label})"]
    for sc in s.schemes:
        lines.append(f"  {sc.name}: edges [{', '.join(fmt_edge(e) for e in sc.edges)}]")
        for lab, n, e, thin in zip(sc.labels, sc.loans, sc.events, sc.thin()):
            rate = f"{e / n:.2%}" if n else "—"
            lines.append(f"      {lab:<24} loans {n:>8,}  events {e:>6,}  rate {rate:>8}{'   thin' if thin else ''}")
    if s.outcome_cut is not None:
        lo, hi = s.outcome_cut_rates
        lines.append(f"  information only — not for step 4, because it is chosen on the outcome: the {s.outcome_label} "
                     f"rate changes most at {fmt_edge(s.outcome_cut)} ({lo:.2%} below, {hi:.2%} at or above)")
    lines.append("  paste under the confounder's `schemes:`")
    for sc in s.schemes:
        lines.append(f"      {sc.name}: [{', '.join(f'{e:g}' for e in sc.edges)}]")
    return "\n".join(lines)
