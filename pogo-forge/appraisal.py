"""
Read exact IVs off a Pokemon GO appraisal screenshot.

No model and no OCR. The appraisal bars encode the IV directly: each bar runs
0 to 15 and is drawn in three equal segments split at 5 and 10. Measuring the
filled proportion of the track gives the value.

The segment gaps are the calibration. Because they're found rather than
assumed, nothing here depends on screen resolution, device or bar position —
only on the bars being drawn the way the game draws them.

A read is never returned on its own. `appraise()` reproduces the on-screen CP
and HP from the IVs it read; if no level reproduces both, it reports that the
read failed rather than handing back a confident wrong answer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

import costs

# A filled segment is strongly saturated; the empty track is a flat grey a
# little darker than the card behind it. Both are matched by relationship,
# not by exact RGB, so a theme or brightness shift doesn't break it.
MIN_SATURATION = 60          # fill vs grey
MAX_TRACK_SPREAD = 18        # how flat a grey the empty track is
MIN_BAR_WIDTH_FRAC = 0.15    # a bar spans at least this much of the image
MIN_BAR_HEIGHT = 4           # ignore hairlines
# Rows bridged when clustering scanlines into one bar. Resampling and JPEG
# artefacts make some scanlines fail the shape test, fragmenting a bar. The
# game draws the three bars roughly four bar-heights apart, so a bridge this
# small cannot merge two different bars at any usable resolution.
CLUSTER_BRIDGE = 15


class ReadFailed(Exception):
    pass


@dataclass
class BarRead:
    iv: int
    fill_px: float
    track_px: int
    segments: int
    raw: float          # unrounded IV, before snapping
    y: int

    @property
    def snap_distance(self) -> float:
        """How far the measurement sat from the integer it snapped to.

        Above about 0.25 the bar was probably clipped or occluded.
        """
        return abs(self.raw - self.iv)


def _row_masks(row: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split one row into (fill weight, bar membership).

    The empty track and the card behind it are both flat greys a few levels
    apart, so an absolute threshold can't separate them. Instead the row's own
    background is measured — it's whatever flat grey dominates the full width —
    and the track is the flat grey that sits darker than it.
    """
    p = row.astype(int)
    hi = p.max(axis=1)
    lo = p.min(axis=1)
    sat = hi - lo

    flat = sat <= MAX_TRACK_SPREAD
    if not flat.any():
        return np.zeros_like(sat, float), np.zeros(len(sat), bool)

    # The background is the brightest flat grey that occupies a real share of
    # the row. Taking the *most common* one fails on a bar with an IV of 0:
    # the empty track is then the largest flat grey in the row and would vote
    # itself the background, erasing the bar. The card is always drawn lighter
    # than the track, so brightest-and-substantial is the reliable choice.
    # Values are binned because compression spreads a flat grey over several
    # adjacent levels.
    binned = (hi[flat] // 4) * 4
    vals, counts = np.unique(binned, return_counts=True)
    substantial = vals[counts >= max(4, int(0.03 * len(sat)))]
    bg = int(substantial.max()) if substantial.size else int(vals[counts.argmax()])

    # A pixel belongs to the bar if it is either coloured (fill) or a flat grey
    # darker than the background (the empty track).
    track = flat & (hi < bg - 5) & (hi > 90)
    member = (sat > MAX_TRACK_SPREAD) & (hi > 120) | track

    # Pixels on the fill/track boundary are a blend of the two — anti-aliasing
    # at one scale, JPEG ringing at another. Counting them proportionally by
    # saturation keeps them inside the bar (so they can't punch a false gap)
    # and makes the measurement sub-pixel accurate instead of rounding them
    # arbitrarily to one side.
    weight = np.clip(sat / MIN_SATURATION, 0.0, 1.0) * member
    return weight, member


def _classify(px: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fill weight and bar membership for the whole image, row by row."""
    h, w, _ = px.shape
    weight = np.zeros((h, w), float)
    member = np.zeros((h, w), bool)
    for y in range(h):
        weight[y], member[y] = _row_masks(px[y])
    return weight, member


def _bands(mask: np.ndarray, min_width: int) -> list[tuple[int, int]]:
    """Contiguous row ranges where the mask is at least min_width wide."""
    counts = mask.sum(axis=1)
    out, start = [], None
    for y, c in enumerate(counts):
        if c >= min_width and start is None:
            start = y
        elif c < min_width and start is not None:
            if y - start >= MIN_BAR_HEIGHT:
                out.append((start, y - 1))
            start = None
    if start is not None and len(counts) - start >= MIN_BAR_HEIGHT:
        out.append((start, len(counts) - 1))
    return out


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous True spans as (start, end) inclusive."""
    out, start = [], None
    for x, on in enumerate(mask):
        if on and start is None:
            start = x
        elif not on and start is not None:
            out.append((start, x - 1))
            start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def _row_groups(fill_row: np.ndarray, member_row: np.ndarray,
                min_width: int, max_gap: int = 12) -> list[tuple]:
    """Every bar-shaped span in one row, as (left, right, fill, width, runs).

    Runs are merged across small gaps because the segment dividers are narrow.
    On a completely filled bar the dividers blur away entirely at low
    resolution or under video compression, so the number of runs is recorded
    but never required — a bar is identified by its geometry, not its
    segment count.
    """
    runs = _runs(member_row)
    if not runs:
        return []

    groups: list[list[tuple[int, int]]] = [[runs[0]]]
    for r in runs[1:]:
        if r[0] - groups[-1][-1][1] - 1 <= max_gap:
            groups[-1].append(r)
        else:
            groups.append([r])

    out = []
    for g in groups:
        left, right = g[0][0], g[-1][1]
        if right - left + 1 < min_width:
            continue
        cols = np.zeros(len(member_row), bool)
        for a, b in g:
            cols[a:b + 1] = True
        width = int(cols.sum())
        if width == 0:
            continue
        out.append((left, right, float((fill_row * cols).sum()), width, len(g)))
    return out


def read_bars(image: Image.Image) -> list[BarRead]:
    """Find the three appraisal bars and measure each one.

    Bars are identified geometrically: three horizontal spans of the same
    width, sharing the same left and right edge, stacked vertically. That
    holds at any resolution and survives compression, where the internal
    segment dividers do not.

    Every row is measured and the median scanline of each bar is taken, so a
    single bad row cannot move the answer.

    Returns them top to bottom, the order the game draws them: Attack,
    Defense, HP.
    """
    px = np.array(image.convert("RGB"))
    h, w, _ = px.shape
    fill, member = _classify(px)
    min_width = int(w * MIN_BAR_WIDTH_FRAC)
    tol = max(3, int(w * 0.02))

    clusters: list[dict] = []
    for y in range(h):
        for left, right, fsum, width, nruns in _row_groups(fill[y], member[y], min_width):
            for c in clusters:
                if (y - c["last_y"] <= CLUSTER_BRIDGE
                        and abs(left - c["left"]) <= tol
                        and abs(right - c["right"]) <= tol):
                    c["rows"].append(15.0 * fsum / width)
                    c["last_y"] = y
                    c["fill"].append(fsum)
                    c["width"].append(width)
                    c["runs"].append(nruns)
                    break
            else:
                clusters.append({"top": y, "last_y": y, "left": left,
                                 "right": right, "rows": [15.0 * fsum / width],
                                 "fill": [fsum], "width": [width],
                                 "runs": [nruns]})

    bars_all = [c for c in clusters if len(c["rows"]) >= MIN_BAR_HEIGHT]

    # A bar shows its two segment dividers unless it is so full that they blur
    # into the fill. Everything else in a screenshot that happens to be
    # bar-shaped — artwork, banners, the map — is usually one solid run.
    def plausible(c) -> bool:
        runs = float(np.median(c["runs"]))
        frac = float(np.median(c["fill"])) / max(1.0, float(np.median(c["width"])))
        return runs >= 2 or frac >= 0.93

    bars_all = [c for c in bars_all if plausible(c)]
    if len(bars_all) < 3:
        raise ReadFailed(
            "no appraisal bars found. Use the Appraise screen, with all three "
            "bars fully visible and unobstructed."
        )

    # The three bars are drawn identically and stacked at even intervals.
    # Score every candidate triple on how well it matches that, and take the
    # best. Junk in the frame does not line up this way.
    def geometry_score(t) -> float | None:
        lefts = [c["left"] for c in t]
        rights = [c["right"] for c in t]
        widths = [float(np.median(c["width"])) for c in t]
        if max(lefts) - min(lefts) > tol or max(rights) - min(rights) > tol:
            return None
        if max(widths) - min(widths) > 0.03 * max(widths):
            return None
        tops = sorted(c["top"] for c in t)
        g1, g2 = tops[1] - tops[0], tops[2] - tops[1]
        if min(g1, g2) <= 0:
            return None
        evenness = abs(g1 - g2) / max(g1, g2)
        if evenness > 0.25:
            return None
        # Prefer even spacing first, then the widest match.
        return evenness - max(widths) / (w * 1000)

    best, best_score = None, None
    for i in range(len(bars_all)):
        for j in range(i + 1, len(bars_all)):
            for k in range(j + 1, len(bars_all)):
                t = [bars_all[i], bars_all[j], bars_all[k]]
                sc = geometry_score(t)
                if sc is not None and (best_score is None or sc < best_score):
                    best, best_score = t, sc

    if best is None:
        raise ReadFailed(
            f"found {len(bars_all)} bar-shaped region(s) but no three of them "
            "line up as appraisal bars. Use the Appraise screen with all three "
            "bars fully visible and unobstructed."
        )

    best.sort(key=lambda c: c["top"])
    out: list[BarRead] = []
    for c in best:
        # Drop the first and last scanline: the top and bottom edge of a bar
        # is vertically anti-aliased and never measures the same as its body.
        rows = c["rows"][1:-1] if len(c["rows"]) > 4 else c["rows"]
        vals = sorted(rows)
        n = len(vals)
        # Spread across the middle half only: the topmost and bottommost rows
        # of a bar are vertically anti-aliased and always read a little off.
        if vals[(3 * n) // 4] - vals[n // 4] > 0.5:
            raise ReadFailed(
                f"the bar at y={c['top']} measured inconsistently across its "
                f"height ({vals[n // 4]:.2f} to {vals[(3 * n) // 4]:.2f}). "
                "Something may be covering it."
            )
        raw = vals[n // 2]
        out.append(BarRead(iv=int(round(raw)), fill_px=round(float(np.median(c["fill"])), 1),
                           track_px=int(np.median(c["width"])), segments=3,
                           raw=raw, y=c["top"]))
    return out


def appraise(image: Image.Image, species: str,
             cp: int | None = None, hp: int | None = None) -> dict:
    """Read the bars, then prove the reading against CP and HP.

    Supplying cp and hp is what turns a measurement into a verified answer.
    Without them the IVs are returned unverified and labelled as such.
    """
    bars = read_bars(image)
    ivs = tuple(b.iv for b in bars)
    shaky = [n for n, b in zip(("attack", "defense", "hp"), bars)
             if b.snap_distance > 0.25]

    result = {
        "ivs": list(ivs),
        "iv_percent": costs.iv_percent(ivs),
        "measurements": [
            {"stat": n, "iv": b.iv, "raw": round(b.raw, 2),
             "fill_px": b.fill_px, "track_px": b.track_px}
            for n, b in zip(("attack", "defense", "hp"), bars)
        ],
        "verified": False,
        "levels": [],
    }
    if shaky:
        result["warning"] = (
            "These bars didn't land cleanly on a whole number: "
            + ", ".join(shaky) + ". The bar may be clipped or covered."
        )

    if cp is None or hp is None:
        result["note"] = ("Unverified — enter the CP and HP from the same "
                          "screen and this can prove the reading.")
        return result

    # Any level that reproduces both numbers confirms the IV spread.
    matches = []
    for lv in costs.levels(1.0, costs.BEST_BUDDY_MAX):
        try:
            if costs.cp_at(species, ivs, lv) == cp and costs.hp_at(species, ivs[2], lv) == hp:
                matches.append(lv)
        except costs.Unknown as e:
            return {**result, "error": str(e)}

    result["levels"] = matches
    result["verified"] = bool(matches)
    if matches:
        result["note"] = (
            f"Confirmed: {ivs[0]}/{ivs[1]}/{ivs[2]} reproduces CP {cp} and HP {hp} "
            f"at level {matches[0]:g}"
            + (f" (also {', '.join(f'{m:g}' for m in matches[1:])})" if len(matches) > 1 else "")
            + "."
        )
    else:
        result["note"] = (
            f"Read {ivs[0]}/{ivs[1]}/{ivs[2]}, but no level reproduces both CP {cp} "
            f"and HP {hp}. Either the species is wrong, the numbers were mistyped, "
            "or a bar was misread. Don't trust this reading."
        )
    return result
