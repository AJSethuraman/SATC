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

#: PRD §6.8: a blank grouping value is its own level, always last. A loan is
#: never dropped from a step for having no value; it is counted under this.
BLANK_LEVEL = "(blank)"


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
    measure_blank: int = 0           # snapshot outcome only: loans with no measure at as-of
    # twins of the share formulas
    a_blank_share: float | None = None
    b_blank_share: float | None = None
    both_share: float | None = None
    measure_blank_share: float | None = None


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
    strata: list = field(default_factory=list)          # list[Stratified], every outcome x confounder x scheme
    decompositions: list = field(default_factory=list)  # list[Decomposition], every outcome x dimension
    control: object = None                              # ControlObservation, for a contradiction rule
    models: list = field(default_factory=list)          # list[ModelResult], one per outcome


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
    # Each bucket is compared with the nearest bucket BELOW it that holds loans
    # (PRD §5.13: the read is over buckets with n > 0), so an empty bucket in
    # the middle cannot break the chain. The sheet keeps the same "last rate
    # seen" in its helper columns M–O. Adversarial finding 1, 19 Sep 2026.
    prev: GradientRow | None = rows[0] if rows and rows[0].rate is not None else None
    for i in range(1, len(rows)):
        b = rows[i]
        if prev is None or b.rate is None:
            g.diffs.append(None)
            g.nonoverlap.append(0)
        else:
            g.diffs.append(b.rate - prev.rate)
            g.nonoverlap.append(int(b.lo > prev.hi) + int(b.hi < prev.lo))
        if b.rate is not None:
            prev = b
    present = [d for d in g.diffs if d is not None]
    if not present:
        g.word = "no data"
    elif all(d == 0 for d in present):
        # every populated bucket carries the same rate (a book with no events
        # is the common case): there is no gradient to read, and saying "rises
        # at every step" would be false. Adversarial finding 2.
        g.word = "flat"
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
    snapshot = cfg.outcome.form == "snapshot"
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
        if snapshot:
            r.measure_blank += int(l.measure is None)
    rows = [by_q[q] for q in sorted(by_q)]
    for r in rows:
        r.a_blank_share = _twin_rate(r.loans, r.a_blank)
        r.b_blank_share = _twin_rate(r.loans, r.b_blank)
        r.both_share = _twin_rate(r.loans, r.both)
        r.measure_blank_share = _twin_rate(r.loans, r.measure_blank) if snapshot else None
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
    strata = []
    decomps = []
    for od in pop.outcomes:
        strata.extend(stratified(cfg, pop, od))
        decomps.extend(decomposition(cfg, pop, od))
    control = None
    if cfg.rule_type == "contradiction":
        both = [l for l in seasoned if l.rule_value is not None]
        fires = sum(1 for l in both if l.fires)
        control = ControlObservation(CubeRow("s7.both", "seasoned loans with both fields", len(both), fires))
        control.share = _twin_rate(len(both), fires)
    fits = [models(cfg, pop, od) for od in pop.outcomes]
    return PackData(seasoned=len(seasoned), unseasoned=len(pop.unseasoned), per_outcome=per,
                    unseasoned_by_quarter=dict(sorted(ubq.items())), bands=band_table(pop),
                    capture=capture(cfg, pop), band_counts=band_counts(cfg, pop), prevalence=prevalence(cfg, pop),
                    strata=strata, decompositions=decomps, control=control, models=fits)


# --------------------------------------------------------------------------
# Step 4 — stratified: the gradient inside every band, and the word
# --------------------------------------------------------------------------

@dataclass
class StratumBand:
    label: str
    flagged: CubeRow            # n = flagged loans in the band, events = a
    unflagged: CubeRow          # n = unflagged loans in the band, events = c
    buckets: list[GradientRow]  # the gradient inside this band
    # twins of the sheet's cells
    flagged_rate: float | None = None
    flagged_lo: float | None = None
    flagged_hi: float | None = None
    unflagged_rate: float | None = None
    unflagged_lo: float | None = None
    unflagged_hi: float | None = None
    gap_pts: float | None = None
    p: float = 0.0
    q: float = 0.0
    r: float = 0.0
    s: float = 0.0

    @property
    def abcd(self) -> tuple[int, int, int, int]:
        a = self.flagged.events
        b = self.flagged.n - a
        c = self.unflagged.events
        d = self.unflagged.n - c
        return a, b, c, d


@dataclass
class Stratified:
    outcome: OutcomeDef
    confounder: str
    scheme: str
    bands: list[StratumBand]
    crude: tuple[float | None, float | None, float | None] = (None, None, None)
    pooled: tuple[float | None, float | None, float | None] = (None, None, None)
    kept: float | None = None
    word: str = ""

    @property
    def block_key(self) -> str:
        return f"{self.outcome.key}.{self.confounder}.{self.scheme}"


def _levels_with_blank(labels: list[str], loans: list[Loan], field: str) -> list[str]:
    """PRD §6.8: `(blank)` is a level of its own, always last — present only
    when some loan actually has no value, so a clean book shows no empty row.
    Adversarial findings 3, 4 and 6, 19 Sep 2026: without it, loans with a
    blank left steps 4 and 5 with no row, the 'whole population' crude ratio
    changed from block to block, and the pack failed its own check."""
    if any(l.values.get(field) is None for l in loans):
        return labels + [BLANK_LEVEL]
    return labels


def _band_of(l: Loan, field: str, edges: tuple[float, ...] | None, labels: list[str]) -> int | None:
    v = l.values.get(field)
    if v is None:
        return len(labels) - 1 if labels and labels[-1] == BLANK_LEVEL else None
    if edges is None:
        try:
            return labels.index(str(v))
        except ValueError:
            return None
    return bucket_index(v, edges)


def stratified(cfg: Config, pop: Population, outcome: OutcomeDef) -> list[Stratified]:
    out: list[Stratified] = []
    seasoned_both = [l for l in pop.seasoned if l.rule_value is not None]
    z = stats.z_for_confidence(cfg.confidence)
    key = outcome.key
    for c in cfg.confounders:
        schemes: dict[str, tuple[float, ...] | None] = dict(c.schemes) if c.schemes else {"levels": None}
        for sname, edges in schemes.items():
            if edges is None:
                levels: dict[str, int] = {}
                for l in seasoned_both:
                    v = l.values.get(c.field)
                    if v is not None:
                        levels[str(v)] = levels.get(str(v), 0) + 1
                labels = [k for k, _ in sorted(levels.items(), key=lambda kv: (-kv[1], kv[0]))]
            else:
                labels = bucket_labels(edges)
            labels = _levels_with_blank(labels, seasoned_both, c.field)
            bands: list[StratumBand] = []
            for i, lab in enumerate(labels):
                members = [l for l in seasoned_both if _band_of(l, c.field, edges, labels) == i]
                fl = [l for l in members if l.fires]
                un = [l for l in members if not l.fires]
                a = sum(int(l.events.get(key, False)) for l in fl)
                cc = sum(int(l.events.get(key, False)) for l in un)
                prefix = f"s4.{key}.{c.name}.{sname}.{i}"
                band = StratumBand(lab, CubeRow(f"{prefix}.flagged", f"{lab} flagged", len(fl), a),
                                   CubeRow(f"{prefix}.unflagged", f"{lab} unflagged", len(un), cc), [])
                band.flagged_rate = _twin_rate(len(fl), a)
                band.flagged_lo, band.flagged_hi = _twin_interval(len(fl), a, cfg)
                band.unflagged_rate = _twin_rate(len(un), cc)
                band.unflagged_lo, band.unflagged_hi = _twin_interval(len(un), cc, cfg)
                if band.flagged_rate is not None and band.unflagged_rate is not None:
                    band.gap_pts = (band.flagged_rate - band.unflagged_rate) * 100.0
                n = len(members)
                aa, bb, cc2, dd = band.abcd
                if n:
                    band.p = (aa + dd) / n
                    band.q = (bb + cc2) / n
                    band.r = aa * dd / n
                    band.s = bb * cc2 / n
                # the gradient inside the band
                counts = [[0, 0] for _ in pop.bucket_labels]
                for l in members:
                    counts[l.bucket][0] += 1
                    counts[l.bucket][1] += int(l.events.get(key, False))
                for j, blab in enumerate(pop.bucket_labels):
                    nn, xx = counts[j]
                    gr = GradientRow(CubeRow(f"{prefix}.bucket{j}", f"{lab} | {blab}", nn, xx))
                    gr.rate = _twin_rate(nn, xx)
                    gr.lo, gr.hi = _twin_interval(nn, xx, cfg)
                    band.buckets.append(gr)
                bands.append(band)
            st = Stratified(outcome=outcome, confounder=c.name, scheme=sname, bands=bands)
            tot = [0, 0, 0, 0]
            for band in bands:
                for k2, v in enumerate(band.abcd):
                    tot[k2] += v
            st.crude = stats.crude_odds_ratio(*tot, z)
            st.pooled = stats.mantel_haenszel([band.abcd for band in bands], z)
            if st.crude[0] is not None and st.pooled[0] is not None and st.crude[0] != 1.0:
                st.kept = stats.math.log(st.pooled[0]) / stats.math.log(st.crude[0])
            st.word = stats.survives_word(st.crude, st.pooled, cfg.survives_threshold)
            if not bands:
                # nothing to stratify on: no seasoned loan with both rule fields
                # carries a value. The sheet writes no formula over an empty
                # range (adversarial finding 16) and the word says so.
                st.word = "no data"
            out.append(st)
    return out


# --------------------------------------------------------------------------
# Step 5 — decomposition: where it concentrates
# --------------------------------------------------------------------------

@dataclass
class DecompRow:
    label: str
    flagged: CubeRow
    unflagged: CubeRow
    flagged_rate: float | None = None
    flagged_lo: float | None = None
    flagged_hi: float | None = None
    unflagged_rate: float | None = None
    unflagged_lo: float | None = None
    unflagged_hi: float | None = None
    gap_pts: float | None = None
    multiple: float | None = None
    share: float | None = None          # this level's flagged events over all flagged events


@dataclass
class Decomposition:
    outcome: OutcomeDef
    dimension: str
    rows: list[DecompRow]


def _dimension_levels(cfg: Config, pop: Population, name: str):
    """(level-of-loan function, ordered labels) for a decompose_by name."""
    seasoned_both = [l for l in pop.seasoned if l.rule_value is not None]
    if name == "origination_year":
        years = sorted({l.year for l in seasoned_both})
        return (lambda l: str(l.year)), [str(y) for y in years]
    for c in cfg.confounders:
        if c.name == name:
            if c.schemes:
                sname, edges = next(iter(c.schemes.items()))
                labels = bucket_labels(edges)
                return (lambda l, f=c.field, e=edges, lab=labels: BLANK_LEVEL if l.values.get(f) is None else lab[bucket_index(l.values[f], e)]), \
                    _levels_with_blank(labels, seasoned_both, c.field)
            levels: dict[str, int] = {}
            for l in seasoned_both:
                v = l.values.get(c.field)
                if v is not None:
                    levels[str(v)] = levels.get(str(v), 0) + 1
            labels = [k for k, _ in sorted(levels.items(), key=lambda kv: (-kv[1], kv[0]))]
            return (lambda l, f=c.field: BLANK_LEVEL if l.values.get(f) is None else str(l.values[f])), \
                _levels_with_blank(labels, seasoned_both, c.field)
    for c in cfg.controls:
        if c.name == name:
            if c.derived == "origination_year":
                years = sorted({l.year for l in seasoned_both})
                return (lambda l: str(l.year)), [str(y) for y in years]
            levels = {}
            for l in seasoned_both:
                v = l.values.get(c.field)
                if v is not None:
                    levels[str(v)] = levels.get(str(v), 0) + 1
            labels = [k for k, _ in sorted(levels.items(), key=lambda kv: (-kv[1], kv[0]))]
            return (lambda l, f=c.field: BLANK_LEVEL if l.values.get(f) is None else str(l.values[f])), \
                _levels_with_blank(labels, seasoned_both, c.field)
    raise KeyError(name)


def decomposition(cfg: Config, pop: Population, outcome: OutcomeDef) -> list[Decomposition]:
    out: list[Decomposition] = []
    seasoned_both = [l for l in pop.seasoned if l.rule_value is not None]
    key = outcome.key
    total_flagged_events = sum(int(l.events.get(key, False)) for l in seasoned_both if l.fires)
    for dim in cfg.decompose_by:
        level_of, labels = _dimension_levels(cfg, pop, dim)
        rows: list[DecompRow] = []
        for i, lab in enumerate(labels):
            members = [l for l in seasoned_both if level_of(l) == lab]
            fl = [l for l in members if l.fires]
            un = [l for l in members if not l.fires]
            a = sum(int(l.events.get(key, False)) for l in fl)
            c = sum(int(l.events.get(key, False)) for l in un)
            prefix = f"s5.{key}.{dim}.{i}"
            r = DecompRow(lab, CubeRow(f"{prefix}.flagged", f"{dim}={lab} flagged", len(fl), a),
                          CubeRow(f"{prefix}.unflagged", f"{dim}={lab} unflagged", len(un), c))
            r.flagged_rate = _twin_rate(len(fl), a)
            r.flagged_lo, r.flagged_hi = _twin_interval(len(fl), a, cfg)
            r.unflagged_rate = _twin_rate(len(un), c)
            r.unflagged_lo, r.unflagged_hi = _twin_interval(len(un), c, cfg)
            if r.flagged_rate is not None and r.unflagged_rate is not None:
                r.gap_pts = (r.flagged_rate - r.unflagged_rate) * 100.0
                r.multiple = None if r.unflagged_rate == 0 else r.flagged_rate / r.unflagged_rate
            r.share = None if total_flagged_events == 0 else a / total_flagged_events
            rows.append(r)
        rows.sort(key=lambda r: (-r.flagged.events, r.label))
        out.append(Decomposition(outcome=outcome, dimension=dim, rows=rows))
    return out


# --------------------------------------------------------------------------
# Step 7 — the control observation, from the config and the counts alone
# --------------------------------------------------------------------------

@dataclass
class ControlObservation:
    both: CubeRow                       # n = seasoned loans with both fields, events = rule fires
    share: float | None = None


# --------------------------------------------------------------------------
# Step 6 — the model: design matrices from the question file, then the fits
# --------------------------------------------------------------------------

from . import model as _model   # noqa: E402  (kept near its use)


@dataclass
class ModelResult:
    outcome: OutcomeDef
    m1: _model.Fit
    m2: _model.Fit
    tree: _model.TreeResult
    used: int                         # loans in the design (seasoned, both fields, every predictor present)
    excluded_blank: int               # seasoned loans with both fields but a blank predictor
    skipped: list[str]                # confounders skipped because their field is already a control
    seconds: float = 0.0


def _reference(levels: dict[str, int]) -> str:
    return sorted(levels.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _design(cfg: Config, loans: list[Loan], outcome: OutcomeDef, with_confounders: bool):
    """Column names, rows (with a leading 1.0), y, reference levels, skipped."""
    names: list[str] = ["flag"]
    columns: list = [lambda l: 1.0 if l.fires else 0.0]
    references: dict[str, str] = {}
    skipped: list[str] = []
    control_fields = {c.field for c in cfg.controls if c.field}

    def add_categorical(name: str, key):
        levels: dict[str, int] = {}
        for l in loans:
            v = key(l)
            levels[v] = levels.get(v, 0) + 1
        ref = _reference(levels)
        references[name] = ref
        for lev, _ in sorted(levels.items(), key=lambda kv: (-kv[1], kv[0])):
            if lev == ref:
                continue
            names.append(f"{name}={lev}")
            columns.append(lambda l, k=key, lv=lev: 1.0 if k(l) == lv else 0.0)

    for c in cfg.controls:
        if c.derived == "origination_year":
            add_categorical(c.name, lambda l: str(l.year))
        elif c.as_ == "log":
            names.append(f"{c.name} (log)")
            columns.append(lambda l, f=c.field: stats.math.log(l.values[f]))
        elif c.as_ == "linear":
            names.append(c.name)
            columns.append(lambda l, f=c.field: float(l.values[f]))
        elif c.as_ == "bands":
            labels = bucket_labels(c.edges)
            add_categorical(c.name, lambda l, f=c.field, e=c.edges, lab=labels: lab[bucket_index(l.values[f], e)])
        else:
            add_categorical(c.name, lambda l, f=c.field: str(l.values[f]))
    if with_confounders:
        for conf in cfg.confounders:
            if conf.field in control_fields:
                skipped.append(f"{conf.name} (its field {conf.field} is already a control)")
                continue
            if conf.schemes:
                sname, edges = next(iter(conf.schemes.items()))
                labels = bucket_labels(edges)
                add_categorical(conf.name, lambda l, f=conf.field, e=edges, lab=labels: lab[bucket_index(l.values[f], e)])
            else:
                add_categorical(conf.name, lambda l, f=conf.field: str(l.values[f]))
    rows = [[1.0] + [col(l) for col in columns] for l in loans]
    y = [int(l.events.get(outcome.key, False)) for l in loans]
    return names, rows, y, references, skipped


def models(cfg: Config, pop: Population, outcome: OutcomeDef) -> ModelResult:
    import time
    t0 = time.perf_counter()
    needed = [c.field for c in cfg.controls if c.field] + [c.field for c in cfg.confounders]
    both = [l for l in pop.seasoned if l.rule_value is not None]
    loans = [l for l in both if all(l.values.get(f) is not None for f in needed)]
    excluded = len(both) - len(loans)
    z = stats.z_for_confidence(cfg.confidence)
    if not loans:
        empty = _model.Fit(label="M1", terms=[], intercept=0.0, loans=0, events=0, coefficients=0, epp=None,
                           warning=None, estimable=False, reason="not estimable (no seasoned loans with every predictor present)")
        empty2 = _model.Fit(**{**empty.__dict__, "label": "M2"})
        return ModelResult(outcome=outcome, m1=empty, m2=empty2,
                           tree=_model.TreeResult(leaves=[], overall_rate=None, first_split=None, loans=0, events=0),
                           used=0, excluded_blank=excluded, skipped=[], seconds=time.perf_counter() - t0)
    n1, x1, y, ref1, _ = _design(cfg, loans, outcome, False)
    m1 = _model.fit_logistic(x1, y, n1, "M1", z)
    m1.references = ref1
    n2, x2, _, ref2, skipped = _design(cfg, loans, outcome, True)
    m2 = _model.fit_logistic(x2, y, n2, "M2", z)
    m2.references = ref2
    m2.skipped = skipped
    # the tree: the rule value plus every M2 predictor in its raw form
    features: list[tuple[str, str, list[str] | None]] = [("rule value", "numeric", None)]
    trows: list[dict] = []
    cat_levels: dict[str, dict[str, int]] = {}
    specs = []
    for c in cfg.controls:
        if c.derived == "origination_year":
            specs.append((c.name, "categorical", lambda l: str(l.year)))
        elif c.as_ in ("log", "linear", "bands"):
            specs.append((c.name, "numeric", lambda l, f=c.field: float(l.values[f])))
        else:
            specs.append((c.name, "categorical", lambda l, f=c.field: str(l.values[f])))
    for conf in cfg.confounders:
        if conf.field in {c.field for c in cfg.controls if c.field}:
            continue
        if conf.schemes:
            specs.append((conf.name, "numeric", lambda l, f=conf.field: float(l.values[f])))
        else:
            specs.append((conf.name, "categorical", lambda l, f=conf.field: str(l.values[f])))
    for l in loans:
        row = {"rule value": float(l.rule_value)}
        for name, kind, key in specs:
            v = key(l)
            row[name] = v
            if kind == "categorical":
                cat_levels.setdefault(name, {})[v] = cat_levels.setdefault(name, {}).get(v, 0) + 1
        trows.append(row)
    for name, kind, _ in specs:
        if kind == "numeric":
            features.append((name, "numeric", None))
        else:
            levels = [k for k, _ in sorted(cat_levels.get(name, {}).items(), key=lambda kv: (-kv[1], kv[0]))]
            features.append((name, "categorical", levels))
    tree = _model.grow_tree(trows, y, features, cfg.model["tree_depth"], cfg.model["min_leaf_loans"],
                            cfg.model["min_leaf_events"])
    return ModelResult(outcome=outcome, m1=m1, m2=m2, tree=tree, used=len(loans), excluded_blank=excluded,
                       skipped=skipped, seconds=time.perf_counter() - t0)
