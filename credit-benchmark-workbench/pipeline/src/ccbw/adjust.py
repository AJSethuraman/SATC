"""Size-distortion & survivorship adjustment engine.

The analytical problem (first-class, not a footnote): the EDGAR universe is
public companies. They skew far larger than private middle-market borrowers,
and they are survivors -- failed and acquired firms drop out of the panel.
Raw public benchmarks therefore (a) overstate stability (dispersion too
narrow), (b) understate how quickly small borrowers get into trouble at a
given leverage (tolerance thresholds too loose), and (c) overstate margins
achievable at middle-market scale (scale economies, pricing power).

The engine converts each raw distribution into a private-middle-market-
adjusted distribution via three documented, tunable transformations applied
per size bucket:

1. **Dispersion widening** -- percentiles are spread away from the median by
   a bucket-specific multiplier. Smaller borrowers carry more idiosyncratic,
   single-customer, key-person and geographic concentration risk; the
   observed public dispersion is a lower bound on private dispersion.
2. **Median shift** -- a direction-aware shift of the center: for
   higher-is-riskier metrics the prudent center moves down for leverage
   tolerance purposes is expressed via thresholds; for margins the median is
   haircut (private MM firms rarely hold public-company margins at scale).
3. **Survivorship tail extension** -- the risky-side tail (p90 for
   higher-is-riskier, p10 for lower-is-riskier) is pushed further out by a
   fraction of the IQR. The missing left-tail companies (the ones that
   defaulted or were distress-sold out of the public universe) lived in that
   tail; the adjusted distribution puts it back.

Every adjusted figure is published *next to* its raw source with the
parameters used, because this layer is judgment calibration: it is the
analytically contestable core a challenge function will be questioned on,
and it must be inspectable and tunable, never silent.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass

from .metrics import HIGHER_RISK, LOWER_RISK, METRICS


@dataclass
class BucketAdjustment:
    """Tunable parameters for one size bucket."""
    # Multiplier on each percentile's distance from the median.
    dispersion_widening: float
    # Haircut applied to medians of lower-is-riskier '%' metrics (margins),
    # in percentage points.
    margin_haircut_pp: float
    # Shift applied to medians of lower-is-riskier 'x' metrics (coverage),
    # in turns (negative = expected coverage lower at small scale because
    # private credit prices wider than public debt).
    coverage_shift_x: float
    # Fraction of the raw IQR added beyond the risky-side tail percentile to
    # reinstate the survivorship-censored tail.
    survivorship_tail_extension: float
    rationale: str = ""


DEFAULT_PARAMS: dict[str, BucketAdjustment] = {
    "lmm": BucketAdjustment(
        dispersion_widening=1.40,
        margin_haircut_pp=2.0,
        coverage_shift_x=-0.50,
        survivorship_tail_extension=0.20,
        rationale=(
            "Smallest band: greatest size gap vs. public comps (public names "
            "in this EBITDA band are rare and unrepresentative -- often "
            "broken IPOs or micro-caps), heaviest idiosyncratic risk, owner "
            "dependence, customer concentration; survivorship censoring most "
            "severe because small public failures delist fastest."),
    ),
    "cmm": BucketAdjustment(
        dispersion_widening=1.25,
        margin_haircut_pp=1.0,
        coverage_shift_x=-0.25,
        survivorship_tail_extension=0.12,
        rationale=(
            "Core band: moderate size gap; private credit's main market. "
            "Public small-caps in this band are usable comps but still "
            "survivors with better capital access than private peers."),
    ),
    "umm": BucketAdjustment(
        dispersion_widening=1.10,
        margin_haircut_pp=0.5,
        coverage_shift_x=-0.10,
        survivorship_tail_extension=0.06,
        rationale=(
            "Upper band overlaps genuine public mid-caps; adjustments are "
            "small but non-zero -- private UMM names still lack public "
            "equity-market access as a deleveraging valve."),
    ),
    "large": BucketAdjustment(
        dispersion_widening=1.00,
        margin_haircut_pp=0.0,
        coverage_shift_x=0.0,
        survivorship_tail_extension=0.0,
        rationale=(
            "Context-only band: this IS the public universe; no adjustment. "
            "Never use as a direct private comp."),
    ),
}

PCTS = ("p10", "p25", "p50", "p75", "p90")


def adjust_distribution(stats: dict, direction: str, unit: str,
                        params: BucketAdjustment) -> dict:
    """Apply the three transformations to one {p10..p90, n} dict."""
    med = stats["p50"]

    # 2. Median shift (direction- and unit-aware)
    shifted_med = med
    if direction == LOWER_RISK and unit == "%":
        shifted_med = med - params.margin_haircut_pp
    elif direction == LOWER_RISK and unit == "x":
        shifted_med = med + params.coverage_shift_x

    # 1. Dispersion widening around the (shifted) median
    out = {"n": stats["n"]}
    for p in PCTS:
        out[p] = shifted_med + (stats[p] - med) * params.dispersion_widening

    # 3. Survivorship tail extension on the risky side
    iqr = abs(stats["p75"] - stats["p25"])
    ext = params.survivorship_tail_extension * iqr * params.dispersion_widening
    if direction == HIGHER_RISK:
        out["p90"] += ext
    else:
        out["p10"] -= ext

    # Keep ordering sane for ratio-like metrics (widening can push the safe
    # tail of a skewed distribution through zero, e.g. leverage p10 < 0).
    if direction == HIGHER_RISK and unit in ("x", "days") and stats["p10"] >= 0:
        out["p10"] = max(out["p10"], 0.0)
    return out


def adjustment_note(direction: str, unit: str, params: BucketAdjustment) -> str:
    parts = [f"dispersion widened x{params.dispersion_widening:.2f} around the median"]
    if direction == LOWER_RISK and unit == "%":
        parts.append(f"median haircut {params.margin_haircut_pp:.1f}pp")
    if direction == LOWER_RISK and unit == "x":
        parts.append(f"median shifted {params.coverage_shift_x:+.2f}x")
    tail = "p90" if direction == HIGHER_RISK else "p10"
    if params.survivorship_tail_extension:
        parts.append(
            f"survivorship: risky tail ({tail}) extended by "
            f"{params.survivorship_tail_extension:.0%} of IQR")
    return ("Raw public distribution -> private-MM adjusted: "
            + "; ".join(parts)
            + ". Parameters are judgment calibration (tunable); see "
              "methodology memo §adjustment-engine.")


def apply_adjustments(
    benchmarks: dict,
    params: dict[str, BucketAdjustment] | None = None,
) -> dict:
    """Return a deep-copied benchmark library with an 'adjusted' block and
    an 'adjustment_note' added beside every 'current'/'baseline'/'trend'
    raw block. The raw numbers are never modified."""
    params = params or DEFAULT_PARAMS
    out = copy.deepcopy(benchmarks)
    for seg in out["segments"].values():
        for bkey, bucket in seg["buckets"].items():
            p = params[bkey]
            for mkey, m in bucket["metrics"].items():
                direction, unit = m["direction"], m["unit"]
                m["adjusted"] = {
                    "current": adjust_distribution(m["current"], direction, unit, p)
                    if m["current"] else None,
                    "baseline_pre2020": adjust_distribution(
                        m["baseline_pre2020"], direction, unit, p)
                    if m["baseline_pre2020"] else None,
                }
                if m.get("trend"):
                    adj_trend = []
                    for t in m["trend"]:
                        stats = {"n": t["n"], "p10": t["p25"], "p25": t["p25"],
                                 "p50": t["p50"], "p75": t["p75"], "p90": t["p75"]}
                        a = adjust_distribution(stats, direction, unit, p)
                        adj_trend.append({"fy": t["fy"], "p50": a["p50"],
                                          "p25": a["p25"], "p75": a["p75"],
                                          "n": t["n"]})
                    m["adjusted"]["trend"] = adj_trend
                m["adjustment_note"] = adjustment_note(direction, unit, p)
    out["adjustment_params"] = {
        k: asdict(v) for k, v in params.items()
    }
    return out
