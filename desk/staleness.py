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

from record import Desk, Source, RecordError

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

    # ASKED ONCE PER SOURCE, NOT ONCE PER PASSAGE. `amended_on` takes a Source and
    # answers a question about that source, but it was called inside the passage
    # loop -- so the shipped desk, whose 34 passages all cite S1, made 34
    # identical requests to one government site. Beyond the rate limit, it made
    # the answer non-deterministic: if the eleventh call failed where the tenth
    # succeeded, two passages of the SAME source landed in different buckets and
    # the report contradicted itself. One question, one answer, applied to all.
    seen: dict[str, tuple] = {}

    def amendment(src):
        if src.id not in seen:
            try:
                seen[src.id] = (amended_on(src), None)
            except Exception as exc:           # a failure is not freshness
                seen[src.id] = (None, exc)
        return seen[src.id]

    # EVERY PIECE OF AUTHORITY THE ENGINE MIGHT SERVE, NOT JUST THE STORED TEXT.
    # A desk answering through ratified positions -- which is REQUIRED of a
    # `human_only` or citation-only source, where a position is the desk's entire
    # knowledge of it -- has no passages at all, so this loop ran zero times and
    # the report read "0 entries checked" and "NOT CHECKED: 0" while the engine
    # served those positions daily. A staleness report that is silent about the
    # only authority a desk has is worse than none: it reads as a clean bill.
    #
    # A position carries `recorded` where a passage carries `checked` -- the day
    # the firm took it, which is the same question asked of a different kind of
    # authority -- and resolves to its source by citation prefix, which `load()`
    # has already proved unique.
    checkable = [(p.citation, desk.source(p.source_id), p.checked, "passage")
                 for p in desk.passages]
    checkable += [
        (q.citation,
         next((s for s in desk.sources if q.citation.startswith(s.citation_prefix)), None),
         q.recorded, "position")
        for q in desk.positions if not q.proposed
    ]

    for citation, src, checked, kind in checkable:
        if src is None:                                    # pragma: no cover
            raise RecordError(f"{citation!r} has no source; load() checks this")
        # `human_only` short-circuits a PASSAGE, whose freshness only re-reading
        # the source could establish -- and we may not read it. A POSITION is the
        # firm's own record: its age is knowable from the date they took it, and
        # a person can supply an amendment date through the callback, which the
        # contract has always permitted. Short-circuiting both meant a position
        # recorded years ago could only ever be reported "human_only", never aged
        # -- so the principal case this loop was widened for was the one case it
        # still did not check.
        if not src.readable and kind == "passage":
            rep.unchecked.append(Finding(
                citation, src.id, checked, "human_only",
                f"{src.title} is access={src.access!r}; only a person can confirm it",
            ))
            continue

        moved, failed = amendment(src)
        if failed is not None:
            rep.unchecked.append(Finding(
                citation, src.id, checked, "unreachable", str(failed)))
            continue

        if moved is None:
            # `continue`, not a fall-through. Without it an undated passage that
            # is ALSO past the age limit was appended twice -- once here and
            # once below -- so `total` overstated the denominator, and a report
            # whose own count is wrong is the failure this file exists to catch.
            rep.unchecked.append(Finding(
                citation, src.id, checked, "no amendment date published",
                f"{src.title} publishes no amendment date; age is the only "
                f"signal, and it is {_days(today, checked)} days old",
            ))
            continue
        if _days(moved, checked) > 0:
            rep.amended.append(Finding(
                citation, src.id, checked, "amended",
                f"amended {moved}, checked {checked}",
            ))
            continue

        age = _days(today, checked)
        if age > max_age_days:
            rep.aged.append(Finding(
                citation, src.id, checked, "aged",
                f"checked {checked}, {age} days ago",
            ))
        else:
            rep.fresh += 1

    return rep
