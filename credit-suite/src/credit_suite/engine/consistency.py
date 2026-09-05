"""The vocabulary every data-consistency check answers in.

Two properties, and neither is optional.

**Every check reports its denominator.** "0 problems found" is the same
sentence whether the check examined 13,248 cells or none at all, and this
repository has shipped the second one more than once. So a result carries what
it looked at, every summary line prints it, and a check that examined nothing
answers ``NONE`` -- the type refuses to hold ``PASS`` over an empty
population, because a convention a caller can forget is not a guard.

**Unknown is a third answer.** ``PASS / FAIL / UNKNOWN``, never ``PASS /
FAIL``. ``mergers.read_mergers`` already keeps this distinction -- ``None``
for "nobody asked", ``{}`` for "asked, none found" -- and its docstring says
what collapsing them costs: *"a caller that collapses them is back to the
670"*. Where a fact cannot be established the check says so and the build
ships marked, rather than passing quietly.

Only ``FAIL`` blocks. An ``UNKNOWN`` that refused the build would train the
operator to bypass the gate, and an ``UNKNOWN`` that passed silently is the
hole it exists to name -- so it ships, loudly, and is reported.

Built 5 September 2026 from ``docs/prd-data-consistency-flags.md``.
"""

from __future__ import annotations

import calendar
import dataclasses
from datetime import date
from typing import Iterable, Mapping, Sequence

#: Every observation the check looked at agreed with it.
PASS = "PASS"
#: At least one observation contradicted it. This, and only this, blocks.
FAIL = "FAIL"
#: The check could not be settled -- the record it needed was not available,
#: or the population holds something the design deliberately left open.
UNKNOWN = "UNKNOWN"
#: Nothing was examined. Not a pass. Never reported as "ok".
NONE = "NONE"

#: How many findings a summary line prints before it says how many it dropped.
#: A summary that names 2,000 cells is not read, and one that names none is
#: not actionable.
MAX_NAMED = 12


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """One check's answer, with the population it was measured over.

    ``examined`` is the denominator and it is not optional. ``failed`` and
    ``unknown`` are counts, not lengths of ``findings`` -- a check may
    legitimately count 2,000 breaches and name twelve of them.
    """

    check: str
    verdict: str
    examined: int
    failed: int = 0
    unknown: int = 0
    findings: tuple = ()
    unit: str = "observations"

    def __post_init__(self) -> None:
        if self.verdict == PASS and self.examined == 0:
            raise ValueError(
                "%s claimed PASS over an empty population. A check that "
                "examined nothing answers NONE: '0 problems found' from a "
                "check that compared nothing is the failure this type exists "
                "to make impossible." % self.check)
        if self.examined < 0 or self.failed < 0 or self.unknown < 0:
            raise ValueError("%s: negative count" % self.check)
        if self.verdict not in (PASS, FAIL, UNKNOWN, NONE):
            raise ValueError("%s: %r is not a verdict" % (self.check, self.verdict))

    @property
    def blocking(self) -> bool:
        """Only a FAIL refuses a build. UNKNOWN ships, marked."""
        return self.verdict == FAIL

    def summary(self) -> str:
        """One line, with the denominator in it, always."""
        if self.examined == 0:
            line = ("%s %s: nothing examined (0 %s)"
                    % (self.check, self.verdict, self.unit))
        else:
            agreed = self.examined - self.failed - self.unknown
            line = ("%s %s: %d of %d %s (%d failed, %d unknown)"
                    % (self.check, self.verdict, agreed, self.examined,
                       self.unit, self.failed, self.unknown))
        if self.findings:
            named = list(self.findings[:MAX_NAMED])
            if len(self.findings) > MAX_NAMED:
                named.append("%d more not named"
                             % (len(self.findings) - MAX_NAMED))
            line += " -- " + "; ".join(named)
        return line


def decide(check: str, examined: int, failures: Iterable[str] = (),
           unknowns: Iterable[str] = (), unit: str = "observations",
           note: str = "", failed: int | None = None,
           unknown: int | None = None) -> CheckResult:
    """Build a result from what was found. The verdict is not a judgement
    call: nothing examined is NONE, any failure is FAIL, any unsettled
    observation with no failure is UNKNOWN, everything else is PASS.

    ``failed`` and ``unknown`` override the counts when one finding stands for
    many observations -- "no previous run was recorded" is one sentence and it
    leaves every series in the run unsettled, and reporting that as 1 of 142
    would overstate what the check established.
    """
    failures = tuple(failures)
    unknowns = tuple(unknowns)
    findings = failures + unknowns
    if note:
        findings = findings + (note,)
    if examined == 0:
        verdict = NONE
        if not findings:
            findings = ("nothing was examined",)
    elif failures:
        verdict = FAIL
    elif unknowns:
        verdict = UNKNOWN
    else:
        verdict = PASS
    return CheckResult(check=check, verdict=verdict, examined=examined,
                       failed=len(failures) if failed is None else failed,
                       unknown=len(unknowns) if unknown is None else unknown,
                       findings=findings, unit=unit)


def landing_check(expected: int, landed: int, missing: Sequence[str] = (),
                  unit: str = "series", check: str = "C1") -> CheckResult:
    """C1 -- every pullable series must land.

    The Nebraska defect. Both runners shipped a gate that asked whether *at
    least one* series came back::

        return not (pullable > 0 and status.get("series_pulled", 0) == 0)

    One HTTP 500 on the Nebraska house-price index gave ``pulled = 141`` of
    142, an error recorded honestly in the status dict that nothing read, exit
    code 0, and a workbook on the desk with a state missing from it.

    Exact equality. There is nothing to tune, and the trade-off is stated: a
    transient 500 on one of 142 series now fails the whole run. That is the
    correct trade -- a monitor with a silent hole is worse than a monitor that
    did not ship -- so the refusal names the series so an operator can decide
    in ten seconds whether to rerun or to mark it dead in the seed.
    """
    if expected == 0:
        return CheckResult(
            check=check, verdict=NONE, examined=0, unit=unit,
            findings=("nothing was expected to land, so nothing was checked; "
                      "an empty seed or peer list is a configuration, not a "
                      "successful run",))
    failures: list[str] = []
    short = expected - landed
    if short > 0:
        named = [str(name) for name in missing][:MAX_NAMED]
        failures.extend(named)
        if short > len(named):
            failures.append("%d more not named" % (short - len(named)))
    elif short < 0:
        failures.append(
            "%d landed where %d were expected -- a slot landed twice, or the "
            "expected count was read from the wrong place" % (landed, expected))
    return CheckResult(
        check=check, verdict=FAIL if short != 0 else PASS, examined=expected,
        failed=abs(short), unknown=0, findings=tuple(failures), unit=unit)


def undetermined(check: str, reason: str, unit: str = "observations"
                 ) -> CheckResult:
    """A check that could not run at all. Not a pass, and not a failure."""
    return CheckResult(check=check, verdict=UNKNOWN, examined=0, unknown=1,
                       findings=(reason,), unit=unit)


# --------------------------------------------------------------------------
# C5 -- the date grid is regular
# --------------------------------------------------------------------------
#
# Promoted into the engine rather than left in one source, the way
# ``run_succeeded`` was: it is arithmetic on dates and a declared cadence and
# every monitor that lands a time series needs it. Keeping it here also keeps
# the FRED runner free of ``series_seed``, which the source-level checks
# import and the runner must not.

#: Months per step, by declared cadence. ``weekly`` steps in days instead.
STEP_MONTHS = {"quarterly": 3, "monthly": 1, "annual": 12}
STEP_DAYS = {"weekly": 7}


def _is_month_end(value: date) -> bool:
    return value.day == calendar.monthrange(value.year, value.month)[1]


def _iso(value) -> date:
    text = str(value)[:10]
    return date(int(text[0:4]), int(text[5:7]), int(text[8:10]))



def _is_month_end(value: date) -> bool:
    return value.day == calendar.monthrange(value.year, value.month)[1]


def _iso(value) -> date:
    text = str(value)[:10]
    return date(int(text[0:4]), int(text[5:7]), int(text[8:10]))


def date_grid(series_id: str, dates: Sequence, frequency: str,
              newest_first: bool = False) -> CheckResult:
    """C5 -- strictly ordered, unique, stepping by the declared cadence.

    ``newest_first`` is the workbook's own order; the pulled pandas index is
    oldest-first. It is a parameter rather than a guess because a check that
    infers which way round its input is cannot tell a reversed grid from a
    reversed reading of it.
    """
    order = list(dates)
    if newest_first:
        order = order[::-1]
    examined = len(order)
    if examined == 0:
        return decide("C5", 0, unit="observations",
                        note="%s landed no observations" % series_id)

    freq = (frequency or "").strip().lower()
    step_months = STEP_MONTHS.get(freq)
    step_days = STEP_DAYS.get(freq)
    if step_months is None and step_days is None:
        return decide(
            "C5", examined, (), unit="observations",
            unknowns=["%s declares frequency %r, which this check has no step "
                      "for -- the grid was not verified" % (series_id, frequency)])

    failures = []
    unknowns = []
    previous = None
    for value in order:
        try:
            current = _iso(value)
        except (TypeError, ValueError, IndexError):
            failures.append("%s: %r is not a date" % (series_id, value))
            continue
        if previous is not None:
            if current == previous:
                failures.append("%s: duplicate date %s"
                                % (series_id, current.isoformat()))
                continue
            if current < previous:
                failures.append(
                    "%s: dates out of order -- %s follows %s"
                    % (series_id, current.isoformat(), previous.isoformat()))
                previous = current
                continue
            if step_days is not None:
                gap = (current - previous).days
                unit, size = "days", step_days
            else:
                gap = ((current.year - previous.year) * 12
                       + current.month - previous.month)
                unit, size = "months", step_months
                # A grid is anchored to the period START (FRED's own dates,
                # 2026-04-01 for Q2) or to the period END (2026-06-30, which
                # is what the demo provider writes and what the FDIC panel
                # uses). Both are regular; requiring a matching day-of-month
                # called 4,678 steps irregular on the first workbook this was
                # pointed at, every one of them a September-to-December step.
                if not (current.day == previous.day
                        or (_is_month_end(previous) and _is_month_end(current))):
                    failures.append(
                        "%s: step from %s to %s lands on neither the same day "
                        "of the month nor a month end, so the grid is not "
                        "anchored" % (series_id, previous.isoformat(),
                                      current.isoformat()))
                    previous = current
                    continue
            if gap % size:
                failures.append(
                    "%s: step from %s to %s is %d %s, not a multiple of the "
                    "declared %s cadence"
                    % (series_id, previous.isoformat(), current.isoformat(),
                       gap, unit, freq))
            elif gap // size > 1:
                unknowns.append(
                    "%s: interior hole after %s -- %d periods with no "
                    "observation before %s. Legitimate for a survey that did "
                    "not ask; unverified here"
                    % (series_id, previous.isoformat(), gap // size - 1,
                       current.isoformat()))
        previous = current
    return decide("C5", examined, failures, unknowns, unit="observations")


def date_grid_all(grids: Mapping[str, tuple]) -> CheckResult:
    """Every series' grid, with the SERIES count as the denominator.

    ``grids`` maps a series id to ``(dates, frequency)``. Reported per series
    rather than per observation so the line reads "142 of 142 series", which
    is the number an operator can check against the seed.
    """
    failures = []
    unknowns = []
    for series_id, spec in sorted(grids.items()):
        dates, frequency = spec[0], spec[1]
        newest_first = spec[2] if len(spec) > 2 else False
        result = date_grid(series_id, dates, frequency, newest_first)
        # ONE finding per series, not one per broken step. Extending with
        # every finding reported "4,678 failed" against a denominator of 142.
        detail = result.findings[0] if result.findings else result.verdict
        if len(result.findings) > 1:
            detail += " (and %d more on this series)" % (len(result.findings) - 1)
        if result.verdict == FAIL:
            failures.append(detail)
        elif result.verdict in (UNKNOWN, NONE):
            unknowns.append(detail)
    return decide("C5", len(grids), failures, unknowns, unit="series")
