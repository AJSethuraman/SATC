"""Three perspectives, one set of lines.

The firm, 13 Oct 2026: *"i want to get an industry perspective, competitive
perspective, and internal. all of this to somehow synthesize reasonable
thresholds."* This puts the three side by side, line by line, and takes each
line from the source the firm names for it. It never picks a source itself.

For one product and one measure, each perspective proposes the four lines
where ratings 2, 3, 4 and 5 begin:

    internal    the scale (``scale.scale``) on KeyBank's own history, as the
                internal import builds it. Most series start in 2014, so the
                only stress in them is the pandemic.
    industry    the same scale on the industry's history, which holds the
                2008-10 crisis, carried to the internal level by
                ``translation``: "median ratio" multiplies every industry line
                by the median of internal / industry over the quarters both
                hold; "none" takes the industry's lines as they are.
    peers       percentiles across the peers: each peer's median over the
                quarters the internal series holds, then the
                ``peer_percentiles`` of those medians, one per line, carried to
                the internal level by the median of internal / KeyBank filed
                over the quarters both hold (what the internal figures leave
                out, the filed ones keep).

``leads`` names, for each of the four lines, which perspective it is taken
from. The chosen lines must still run in order from 2 to 5; if they do not,
the result is refused and says which pair is out of order.

Beside the lines, the competitive check is stated as facts: KeyBank's filed
median over the same quarters, how many peers sit below it, and the rating the
latest internal quarter gets on the chosen lines. Nothing here says how bad a
rank is bad enough to act on.

Every setting is required. The scale's settings mean the same here as in the
workbook (``scale.py``).
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional, Sequence

from .scale import scale as _scale, score as _score
from .compare import by_quarter
from .series import Point

SOURCES = ("internal", "industry", "peers")
TRANSLATIONS = ("median ratio", "none")
LINES = ("2 Moderate-Low", "3 Moderate", "4 Moderate-High", "5 High")


def _q_order(q: str):
    return int(q[:4]), q[5]


#: scale.py's one refusal that is about line 5 alone.
HIGH_BEYOND_WORST = "High would begin beyond the worst"


def _lines(values: Sequence[float], direction, halfwidth, low_step, high_z, floor_at_zero) -> dict:
    """``scale.scale``, except that when the only objection is that High would
    begin beyond the worst quarter kept, lines 2-4 still stand and line 5 is
    None: a history with no stress in it (internal since 2014) can say where
    Moderate is, and cannot say where High begins. That is the gap the
    industry's history is there to fill."""
    out = _scale(list(values), direction, halfwidth, low_step, high_z, floor_at_zero)
    if out["refused"] and out["refused"].startswith(HIGH_BEYOND_WORST):
        sgn = 1 if direction == "higher_is_worse" else -1
        med, move = out["median"], out["typical_yearly_move"]
        out["bounds"] = [med - sgn * low_step * move, med - sgn * halfwidth * move,
                         med + sgn * halfwidth * move, None]
        out["refused"] = "line 5: " + out["refused"]
    return out


def _ratio(num: Dict[str, float], den: Dict[str, float]) -> dict:
    both = [q for q in num if q in den and den[q] > 0]
    if not both:
        return {"ratio": None, "quarters": 0}
    return {"ratio": statistics.median(num[q] / den[q] for q in both), "quarters": len(both),
            "first": min(both, key=_q_order), "last": max(both, key=_q_order)}


def _percentile(vals: Sequence[float], p: float) -> float:
    from .profile import percentile
    return percentile(list(vals), p)


def _check(direction, on_the_line, translation, peer_percentiles, leads):
    if direction not in ("higher_is_worse", "lower_is_worse"):
        raise ValueError("direction must be higher_is_worse or lower_is_worse, not %r" % (direction,))
    if on_the_line not in ("worse", "better"):
        raise ValueError("on the line must be worse or better, not %r" % (on_the_line,))
    if translation not in TRANSLATIONS:
        raise ValueError("translation must be one of %s, not %r" % (", ".join(TRANSLATIONS), translation))
    if isinstance(leads, str) or len(leads) != 4 or any(x not in SOURCES for x in leads):
        raise ValueError("leads names the source of each of the four lines (2, 3, 4, 5), each one of "
                         "%s, not %r" % (", ".join(SOURCES), leads))
    if peer_percentiles is not None:
        if len(peer_percentiles) != 4 or any(
                isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p)
                or not 0 <= p <= 100 for p in peer_percentiles):
            raise ValueError("peer percentiles are four numbers from 0 to 100, one per line, not %r"
                             % (peer_percentiles,))
        if any(b <= a for a, b in zip(peer_percentiles, peer_percentiles[1:])):
            raise ValueError("peer percentiles must rise from line 2 to line 5, not %r" % (peer_percentiles,))


def synthesize(internal: Sequence[Point], industry: Sequence[Point], filed: Optional[Sequence[Point]],
               peers: Dict[str, Sequence[Point]], *, direction: str, halfwidth: float, low_step: float,
               high_z: float, floor_at_zero: bool, on_the_line: str, translation: str,
               peer_percentiles: Optional[Sequence[float]], leads: Sequence[str]) -> dict:
    """The three candidates per line, the chosen lines, and the competitive
    check. ``filed`` and ``peers`` may be None / empty only when no line is
    led by peers and ``peer_percentiles`` is None: the peer candidate is then
    "not built", said so, never guessed.

    Returns ``{candidates: {source: {lines, refused, ...}}, chosen, leads,
    rating, latest, check, translation}``. Refused (``ValueError``) when a
    lead names a source with no lines, or the chosen lines are out of order."""
    _check(direction, on_the_line, translation, peer_percentiles, leads)
    if (peer_percentiles is None) != (not peers):
        raise ValueError("peer percentiles and peer series go together: give both, or neither "
                         "(then no line can be led by peers)")
    scale_args = (direction, halfwidth, low_step, high_z, floor_at_zero)
    qi, qx = by_quarter(internal, "the internal series"), by_quarter(industry, "the industry series")
    if not qi:
        raise ValueError("the internal series is empty")
    window = sorted(qi, key=_q_order)
    cand: Dict[str, dict] = {}

    own = _lines([qi[q] for q in window], *scale_args)
    cand["internal"] = {"lines": own["bounds"], "refused": own["refused"], "median": own["median"],
                        "quarters": len(window), "first": window[0], "last": window[-1]}

    ind = _lines([v for _, v in sorted(qx.items(), key=lambda kv: _q_order(kv[0]))], *scale_args)
    r = _ratio(qi, qx) if translation == "median ratio" else {"ratio": 1.0, "quarters": None}
    if translation == "median ratio" and r["ratio"] is None:
        cand["industry"] = {"lines": None, "refused": "the internal and industry series share no quarter, "
                            "so the industry cannot be translated", "ratio": None}
    else:
        cand["industry"] = {"lines": [None if b is None else b * r["ratio"] for b in ind["bounds"]]
                                     if ind["bounds"] else None,
                            "refused": ind["refused"], "ratio": r["ratio"], "ratio_quarters": r["quarters"],
                            "untranslated": ind["bounds"], "quarters": len(qx)}

    check = None
    if peers:
        qf = by_quarter(filed or [], "KeyBank's filed series")
        meds = {}
        for name, pts in peers.items():
            qp = by_quarter(pts, name)
            vals = [qp[q] for q in window if q in qp]
            meds[name] = statistics.median(vals) if vals else None
        held = sorted(v for v in meds.values() if v is not None)
        recon = _ratio(qi, qf)
        if not qf or recon["ratio"] is None:
            cand["peers"] = {"lines": None, "refused": "KeyBank's filed series shares no quarter with the "
                             "internal one, so peers cannot be carried to the internal level"}
        elif len(held) < 2:
            cand["peers"] = {"lines": None, "refused": "fewer than two peers hold any quarter of the "
                             "internal window"}
        else:
            raw = [_percentile(held, p) for p in peer_percentiles]
            if direction == "lower_is_worse":       # worse is lower: line 5 at the low end
                raw = [_percentile(held, 100 - p) for p in peer_percentiles]
            cand["peers"] = {"lines": [v * recon["ratio"] for v in raw], "refused": None,
                             "ratio": recon["ratio"], "ratio_quarters": recon["quarters"],
                             "untranslated": raw, "peers": len(held), "medians": meds}
        kb = [qf[q] for q in window if q in qf]
        if kb:
            kb_med = statistics.median(kb)
            below = sum(1 for v in held if v < kb_med)
            check = {"filed_median": kb_med, "peers": len(held), "below": below,
                     "worse_than": below if direction == "higher_is_worse" else len(held) - below
                     - sum(1 for v in held if v == kb_med)}
    else:
        cand["peers"] = {"lines": None, "refused": "not built: no peer series were given"}

    chosen = []
    for k, src in enumerate(leads):
        c = cand[src]
        if not c["lines"] or c["lines"][k] is None:
            raise ValueError("line %s is led by %s, which has no such line: %s"
                             % (LINES[k], src, c["refused"] or "not built"))
        chosen.append(c["lines"][k])
    s = 1 if direction == "higher_is_worse" else -1
    for k in range(3):
        if s * (chosen[k + 1] - chosen[k]) <= 0:
            raise ValueError("the chosen lines are out of order: %s (%s, %.4g) does not begin beyond %s "
                             "(%s, %.4g). Lead one of them from another source"
                             % (LINES[k + 1], leads[k + 1], chosen[k + 1], LINES[k], leads[k], chosen[k]))
    latest_q = window[-1]
    rating = _score(qi[latest_q], chosen, direction, on_the_line, floor_at_zero)
    return {"candidates": cand, "chosen": chosen, "leads": list(leads), "latest": (latest_q, qi[latest_q]),
            "rating": rating, "check": check, "translation": translation}


def report(r: dict, unit: str) -> str:
    """The result as plain lines: one row per line, the three candidates, the
    chosen value and where it came from; then the latest rating and the
    competitive check, as facts."""
    def f(v):
        return "none" if v is None else "%.3f" % v
    c = r["candidates"]
    out = ["%-16s %12s %12s %12s %12s  from" % ("Line", "internal", "industry", "peers", "chosen")]
    for k, name in enumerate(LINES):
        vals = [(c[s]["lines"] or [None] * 4)[k] for s in SOURCES]
        out.append("%-16s %12s %12s %12s %12s  %s" % (name, *map(f, vals), f(r["chosen"][k]), r["leads"][k]))
    for s in SOURCES:
        if c[s]["refused"]:
            out.append("%s: %s" % (s, c[s]["refused"]))
    ind = c["industry"]
    if r["translation"] == "median ratio" and ind.get("ratio") is not None:
        out.append("Industry translated: x %.3f, the median of internal / industry over %d quarters"
                   % (ind["ratio"], ind["ratio_quarters"]))
    if c["peers"].get("ratio") is not None:
        out.append("Peers translated: x %.3f, the median of internal / KeyBank filed over %d quarters; "
                   "%d peers" % (c["peers"]["ratio"], c["peers"]["ratio_quarters"], c["peers"]["peers"]))
    q, v = r["latest"]
    out.append("Latest internal quarter %s: %.3f%s, rating %d on the chosen lines" % (q, v, unit, r["rating"]))
    ch = r["check"]
    if ch:
        out.append("Competitive check: KeyBank's filed median %.3f%s over the internal window; it is worse "
                   "than %d of %d peers" % (ch["filed_median"], unit, ch["worse_than"], ch["peers"]))
    return "\n".join(out)


__all__: List[str] = ["SOURCES", "TRANSLATIONS", "LINES", "synthesize", "report"]
