"""Has the ground moved under the record? Reports; never gates.

VERIFICATION AND FRESHNESS ARE DIFFERENT QUESTIONS. The engine grades against
stored text so CI stays deterministic and offline. This is the other half: it
reaches out, compares, and says what has drifted. Keeping them apart is what
stops a government website being down from turning a build red.

WHY THIS DOES NOT FAIL THE BUILD. A regulation being amended is not a defect, it
is a work item. Making it red would train people to ignore red, and the first
time it fired on a Friday afternoon it would be waved through -- after which it
fires forever and hides the next genuine failure behind it. This repository has
that scar already: a permanently-red check on `main` that had to be sidelined
because "after the third day nobody reads it".

TWO SIGNALS, BECAUSE ONE IS NOT ENOUGH. An amendment date catches a source that
changed. An age limit catches one that changed in a way no timestamp captured,
or a source that publishes no date at all -- and those are the entries most
likely to be quietly wrong.

WHAT IT REFUSES TO DO. An entry whose source could not be reached is reported as
UNCHECKED, never as fresh. A clean result over a source nobody could open is the
false pass this whole operation keeps being bitten by.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from record import Desk, Source

#: How long an entry may go unre-examined before it is flagged regardless of any
#: amendment date. Not a deadline -- a prompt to look.
DEFAULT_MAX_AGE_DAYS = 365


@dataclass(frozen=True)
class Finding:
    citation: str
    source_id: str
    checked: str
    why: str
    detail: str = ""


@dataclass
class Report:
    """What moved, what did not, and what could not be looked at."""
    amended: list[Finding] = field(default_factory=list)
    aged: list[Finding] = field(default_factory=list)
    unchecked: list[Finding] = field(default_factory=list)
    fresh: int = 0

    @property
    def total(self) -> int:
        return len(self.amended) + len(self.aged) + len(self.unchecked) + self.fresh

    def render(self) -> str:
        """Findings before green, and the gap stated in its own list."""
        out = [f"{self.total} entries checked for staleness"]
        for name, items in (("amended since checked", self.amended),
                            ("older than the age limit", self.aged)):
            out.append(f"  {name}: {len(items)}")
            out += [f"    {f.citation} — {f.detail or f.why}" for f in items]
        out.append(f"  fresh: {self.fresh}")
        out.append("")
        out.append(f"  NOT CHECKED: {len(self.unchecked)}")
        out += [f"    {f.citation} — {f.detail or f.why}" for f in self.unchecked]
        if not self.unchecked:
            out.append("    (none)")
        return "\n".join(out)


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def check(desk: Desk, amended_on, *, today: str | None = None,
          max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> Report:
    """Compare every stored passage against its source's current state.

    `amended_on` is any callable taking a Source and returning an ISO date, or
    None when it could not be established. Injected rather than imported so the
    suite never opens a socket, and so a source reachable only by a person can
    supply its date by hand.
    """
    today = today or date.today().isoformat()
    rep = Report()

    for p in desk.passages:
        src = desk.source(p.source_id)
        if not src.readable:
            rep.unchecked.append(Finding(
                p.citation, src.id, p.checked, "human_only",
                f"{src.title} is access={src.access!r}; only a person can confirm it",
            ))
            continue

        try:
            moved = amended_on(src)
        except Exception as exc:                       # a failure is not freshness
            rep.unchecked.append(Finding(
                p.citation, src.id, p.checked, "unreachable", str(exc)))
            continue

        if moved is None:
            # `continue`, not a fall-through. Without it an undated passage that
            # is ALSO past the age limit was appended twice -- once here and
            # once below -- so `total` overstated the denominator, and a report
            # whose own count is wrong is the failure this file exists to catch.
            rep.unchecked.append(Finding(
                p.citation, src.id, p.checked, "no amendment date published",
                f"{src.title} publishes no amendment date; age is the only "
                f"signal, and it is {_days(today, p.checked)} days old",
            ))
            continue
        if _days(moved, p.checked) > 0:
            rep.amended.append(Finding(
                p.citation, src.id, p.checked, "amended",
                f"amended {moved}, checked {p.checked}",
            ))
            continue

        age = _days(today, p.checked)
        if age > max_age_days:
            rep.aged.append(Finding(
                p.citation, src.id, p.checked, "aged",
                f"checked {p.checked}, {age} days ago",
            ))
        else:
            rep.fresh += 1

    return rep
