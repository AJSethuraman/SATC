"""The ladder: the counts each step needs, and Python's twin of each formula.

Every number the workbook shows is a formula over the count cube. This module
produces the cube rows and, beside them, the values Python computes for the
same cells with the same arithmetic (`stats.py`), so the `_check` tab can
compare them. Slices 1–2 carry step 3, the gradient, once per outcome; later
slices add the other steps here in the same shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import stats
from .config import Config
from .ingest import BLANK
from .population import Loan, OutcomeDef, Population, bucket_index, bucket_labels


@dataclass
class CubeRow:
    block: str
    label: str
    n: int
    events: int


@dataclass
class GradientRow:
    cube: CubeRow
    # Python twins of the formula cells on 3_Gradient
    rate: float | None = None
    lo: float | None = None
    hi: float | None = None
    gap_pts: float | None = None
    multiple: float | None = None


@dataclass
class Gradient:
    outcome: OutcomeDef
    rows: list[GradientRow]
    base: GradientRow
    with_both: int
    blank_either: int
    diffs: list[float | None] = field(default_factory=list)     # adjacent rate differences
    nonoverlap: list[int] = field(default_factory=list)         # per adjacent pair, 0/1/2
    word: str = ""
    nonoverlap_count: int = 0


@dataclass
class BandTable:
    """For a graded measure outcome: loans per rule bucket per measure band."""
    band_labels: list[str]
    rows: list[tuple[str, list[int]]]     # (bucket label, counts per band)
    shares: list[list[float | None]]      # Python twins of the share formulas


@dataclass
class CaptureRow:
    quarter: str
    loans: int
    unseasoned: int
    a_blank: int
    b_blank: int
    both: int
    # twins of the share formulas
    a_blank_share: float | None = None
    b_blank_share: float | None = None
    both_share: float | None = None


@dataclass
class BandCount:
    confounder: str
    scheme: str
    labels: list[str]
    counts: list[int]           # seasoned loans per band (blank field excluded)
    blank: int


@dataclass
class PrevalenceRow:
    quarter: str
    capture: CubeRow            # n = seasoned loans, events = both present
    flag: CubeRow               # n = both present, events = fires
    capture_rate: float | None = None
    capture_lo: float | None = None
    capture_hi: float | None = None
    flag_rate: float | None = None
    flag_lo: float | None = None
    flag_hi: float | None = None


@dataclass
class Facts:
    outcome: OutcomeDef
    seasoned: int
    events: int
    unseasoned: int


@dataclass
class PackData:
    seasoned: int
    unseasoned: int
    per_outcome: list[tuple[Facts, Gradient]]
    unseasoned_by_quarter: dict[str, int]
    bands: BandTable | None = None
    capture: list[CaptureRow] = field(default_factory=list)
    band_counts: list[BandCount] = field(default_factory=list)
    prevalence: list[PrevalenceRow] = field(default_factory=list)


def _twin_rate(n: int, x: int) -> float | None:
    return None if n == 0 else x / n


def _twin_interval(n: int, x: int, cfg: Config) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    lo, hi = stats.interval(x, n, cfg.confidence, cfg.method)
    return lo, hi


def gradient(cfg: Config, pop: Population, outcome: OutcomeDef) -> Gradient:
    seasoned = pop.seasoned
    both = [l for l in seasoned if l.rule_value is not None]
    blank_either = len(seasoned) - len(both)
    labels = pop.bucket_labels
    counts = [[0, 0] for _ in labels]
    base_n = base_x = 0
    key = outcome.key
    for l in both:
        ev = int(l.events.get(key, False))
        counts[l.bucket][0] += 1
        counts[l.bucket][1] += ev
        if not l.fires:
            base_n += 1
            base_x += ev
    base = GradientRow(CubeRow(f"s3.{key}.base", "rule does not fire", base_n, base_x))
    base.rate = _twin_rate(base_n, base_x)
    base.lo, base.hi = _twin_interval(base_n, base_x, cfg)
    rows: list[GradientRow] = []
    for i, lab in enumerate(labels):
        n, x = counts[i]
        r = GradientRow(CubeRow(f"s3.{key}.bucket{i}", lab, n, x))
        r.rate = _twin_rate(n, x)
        r.lo, r.hi = _twin_interval(n, x, cfg)
        if r.rate is not None and base.rate is not None:
            r.gap_pts = (r.rate - base.rate) * 100.0
            r.multiple = None if base.rate == 0 else r.rate / base.rate
        rows.append(r)
    g = Gradient(outcome=outcome, rows=rows, base=base, with_both=len(both), blank_either=blank_either)
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        if a.rate is None or b.rate is None:
            g.diffs.append(None)
            g.nonoverlap.append(0)
        else:
            g.diffs.append(b.rate - a.rate)
            g.nonoverlap.append(int(b.lo > a.hi) + int(b.hi < a.lo))
    present = [d for d in g.diffs if d is not None]
    if not present:
        g.word = "no data"
    elif all(d >= 0 for d in present):
        g.word = "monotonic increasing"
    elif all(d <= 0 for d in present):
        g.word = "monotonic decreasing"
    else:
        g.word = "not monotonic"
    g.nonoverlap_count = sum(g.nonoverlap)
    return g


def band_table(pop: Population) -> BandTable | None:
    if not pop.measure_edges:
        return None
    edges = pop.measure_edges
    blabels = bucket_labels(edges)
    rows: list[tuple[str, list[int]]] = []
    shares: list[list[float | None]] = []
    seasoned_both = [l for l in pop.seasoned if l.rule_value is not None and l.measure is not None]
    for i, lab in enumerate(pop.bucket_labels):
        counts = [0] * len(blabels)
        for l in seasoned_both:
            if l.bucket == i:
                counts[bucket_index(l.measure, edges)] += 1
        total = sum(counts)
        rows.append((lab, counts))
        shares.append([None if total == 0 else c / total for c in counts])
    return BandTable(band_labels=blabels, rows=rows, shares=shares)


def capture(cfg: Config, pop: Population) -> list[CaptureRow]:
    by_q: dict[str, CaptureRow] = {}
    for l in pop.loans:
        r = by_q.get(l.quarter)
        if r is None:
            r = by_q[l.quarter] = CaptureRow(l.quarter, 0, 0, 0, 0, 0)
        r.loans += 1
        r.unseasoned += int(not l.seasoned)
        a_blank = l.a is BLANK
        b_blank = l.b is BLANK
        r.a_blank += int(a_blank)
        r.b_blank += int(b_blank)
        r.both += int(not a_blank and not b_blank)
    rows = [by_q[q] for q in sorted(by_q)]
    for r in rows:
        r.a_blank_share = _twin_rate(r.loans, r.a_blank)
        r.b_blank_share = _twin_rate(r.loans, r.b_blank)
        r.both_share = _twin_rate(r.loans, r.both)
    return rows


def band_counts(cfg: Config, pop: Population) -> list[BandCount]:
    out: list[BandCount] = []
    seasoned = pop.seasoned
    for c in cfg.confounders:
        if not c.schemes:
            levels: dict[str, int] = {}
            blank = 0
            for l in seasoned:
                v = l.values.get(c.field)
                if v is None:
                    blank += 1
                else:
                    levels[str(v)] = levels.get(str(v), 0) + 1
            ordered = sorted(levels.items(), key=lambda kv: (-kv[1], kv[0]))
            out.append(BandCount(c.name, "levels", [k for k, _ in ordered], [n for _, n in ordered], blank))
            continue
        for sname, edges in c.schemes.items():
            labels = bucket_labels(edges)
            counts = [0] * len(labels)
            blank = 0
            for l in seasoned:
                v = l.values.get(c.field)
                if v is None:
                    blank += 1
                else:
                    counts[bucket_index(v, edges)] += 1
            out.append(BandCount(c.name, sname, labels, counts, blank))
    return out


def prevalence(cfg: Config, pop: Population) -> list[PrevalenceRow]:
    by_q: dict[str, list[int]] = {}      # quarter -> [seasoned, both, fires]
    for l in pop.seasoned:
        s = by_q.setdefault(l.quarter, [0, 0, 0])
        s[0] += 1
        if l.rule_value is not None:
            s[1] += 1
            s[2] += int(bool(l.fires))
    rows: list[PrevalenceRow] = []
    for q in sorted(by_q):
        seasoned, both, fires = by_q[q]
        r = PrevalenceRow(q, CubeRow(f"s2.{q}.capture", f"{q} capture", seasoned, both),
                          CubeRow(f"s2.{q}.flag", f"{q} flag", both, fires))
        r.capture_rate = _twin_rate(seasoned, both)
        r.capture_lo, r.capture_hi = _twin_interval(seasoned, both, cfg)
        r.flag_rate = _twin_rate(both, fires)
        r.flag_lo, r.flag_hi = _twin_interval(both, fires, cfg)
        rows.append(r)
    return rows


def run(cfg: Config, pop: Population) -> PackData:
    seasoned = pop.seasoned
    per: list[tuple[Facts, Gradient]] = []
    for od in pop.outcomes:
        facts = Facts(outcome=od, seasoned=len(seasoned),
                      events=sum(1 for l in seasoned if l.events.get(od.key, False)),
                      unseasoned=len(pop.unseasoned))
        per.append((facts, gradient(cfg, pop, od)))
    ubq: dict[str, int] = {}
    for l in pop.unseasoned:
        ubq[l.quarter] = ubq.get(l.quarter, 0) + 1
    return PackData(seasoned=len(seasoned), unseasoned=len(pop.unseasoned), per_outcome=per,
                    unseasoned_by_quarter=dict(sorted(ubq.items())), bands=band_table(pop),
                    capture=capture(cfg, pop), band_counts=band_counts(cfg, pop), prevalence=prevalence(cfg, pop))
