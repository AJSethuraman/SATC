"""Config-driven OK / WATCH / ALERT, direction-aware.

The Python half of a pair. The workbook computes the same statuses by formula,
and the two must agree cell for cell -- which is why this is the only place the
rule is written on the Python side, and why the builder generates its formulas
from the same threshold cells rather than from a second copy of the rule.

Direction matters: most metrics are above-is-bad (noncurrent loans, charge-offs),
but capital, coverage and earnings run below-is-bad. Getting that backwards
turns a bank in trouble green.
"""

from __future__ import annotations

import math
from typing import Optional

from credit_suite.engine.config import Threshold

OK = "OK"
WATCH = "WATCH"
ALERT = "ALERT"
STALE = "STALE"


def status_for(value: Optional[float], threshold: Optional[Threshold]) -> str:
    """``direction='above'``: flag when ``value >= bound``; ``'below'``: ``<=``.

    A blank value is OK, never a flag: absence is surfaced by the staleness and
    error paths, and fabricating a flag out of a missing number is the worst
    thing this function could do.

    ALERT is tested before WATCH, so a value past both reports the worse one.
    """
    if value is None or threshold is None or (
            isinstance(value, float) and math.isnan(value)):
        return OK
    above = threshold.direction != "below"

    def hit(bound: Optional[float]) -> bool:
        if bound is None:
            return False
        return value >= bound if above else value <= bound

    if hit(threshold.alert):
        return ALERT
    if hit(threshold.watch):
        return WATCH
    return OK
