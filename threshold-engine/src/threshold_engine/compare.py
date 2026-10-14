"""Two series of the same measure, side by side: the cross-check.

The firm, 13 Oct 2026: every industry series from the FDIC, "Fed kept as a
cross-check". The two are built differently (the Federal Reserve's release
averages four seasonally adjusted quarterly rates and dates each at the
quarter's first day; the FDIC series here are four quarters' flows over four
quarter-end balances, dated at the quarter's end), so they are matched by
calendar quarter and the differences are stated as facts. Nothing here
decides how close is close enough: no tolerance, no verdict.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .series import Point, read_csv


def by_quarter(points: Sequence[Point], name: str) -> Dict[str, float]:
    """``{'YYYYQn': value}``. Any date in a quarter names that quarter, so a
    series dated at the quarter's first day meets one dated at its end. Two
    points in one quarter are refused: the series is not quarterly."""
    out: Dict[str, float] = {}
    for p in points:
        y, m = int(p.date[:4]), int(p.date[5:7])
        q = "%dQ%d" % (y, (m - 1) // 3 + 1)
        if q in out:
            raise ValueError("%s has two values in %s (%s): compare takes quarterly series" % (name, q, p.date))
        out[q] = p.value
    return out


def compare(a: Sequence[Point], b: Sequence[Point], a_name: str = "A", b_name: str = "B") -> dict:
    """Facts on ``a`` less ``b`` over the quarters both hold:
    ``{quarters, first, last, only_a, only_b, mean, mean_abs, max_abs, max_at,
    rows}``, ``rows`` being ``(quarter, a, b, a - b)`` oldest first. Refused
    when the two share no quarter."""
    qa, qb = by_quarter(a, a_name), by_quarter(b, b_name)
    both = sorted(set(qa) & set(qb), key=lambda q: (int(q[:4]), q[5]))
    if not both:
        raise ValueError("%s and %s share no quarter, so there is nothing to compare" % (a_name, b_name))
    rows = [(q, qa[q], qb[q], qa[q] - qb[q]) for q in both]
    worst = max(rows, key=lambda r: abs(r[3]))
    return {"quarters": len(rows), "first": both[0], "last": both[-1],
            "only_a": sorted(set(qa) - set(qb)), "only_b": sorted(set(qb) - set(qa)),
            "mean": sum(r[3] for r in rows) / len(rows),
            "mean_abs": sum(abs(r[3]) for r in rows) / len(rows),
            "max_abs": abs(worst[3]), "max_at": worst[0], "rows": rows}


def report(c: dict, a_name: str, b_name: str, every: bool) -> str:
    """The facts as lines of text; ``every`` adds one line per quarter."""
    lines = ["%s less %s, %d quarters in both, %s to %s" % (a_name, b_name, c["quarters"], c["first"], c["last"]),
             "  mean difference %+.3f; mean absolute difference %.3f; largest %.3f, in %s"
             % (c["mean"], c["mean_abs"], c["max_abs"], c["max_at"])]
    for name, only in ((a_name, c["only_a"]), (b_name, c["only_b"])):
        if only:
            lines.append("  only in %s: %d quarters, %s to %s" % (name, len(only), only[0], only[-1]))
    if every:
        lines.append("  quarter     %12s %12s   difference" % (a_name[:12], b_name[:12]))
        lines += ["  %-10s %12.3f %12.3f %+12.3f" % r for r in c["rows"]]
    return "\n".join(lines)


def files(a_path, b_path, every: bool) -> str:
    """``compare`` on two ``date,value`` files, named by their paths."""
    a, b = read_csv(a_path), read_csv(b_path)
    return report(compare(a, b, str(a_path), str(b_path)), str(a_path), str(b_path), every)


__all__: List[str] = ["by_quarter", "compare", "report", "files"]
