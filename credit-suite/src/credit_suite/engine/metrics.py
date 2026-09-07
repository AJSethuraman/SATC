"""The metric registry: named pure functions of the landed fields.

Every metric is defined once here on the Python side and once as an Excel
formula in the workbook, and the two must agree. The way that is guaranteed is
not a test but a construction: simple ratios live in a *declarative table* the
source supplies, and both the Python function and the Excel formula are
generated from that one table. A metric that cannot drift is better than a
metric whose drift is detected.

None-tolerant everywhere, and this is the rule that matters most: a missing or
null field yields ``None`` (a blank cell), **never zero**. A null uninsured-
deposit figure rendered as 0% would read as a bank with no uninsured deposits,
which is the opposite of unknown.
"""

from __future__ import annotations

from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple

Fields = Mapping[str, Optional[float]]
MetricFn = Optional[Callable[[Fields], Optional[float]]]
#: metric id -> (fields consumed, derived fn or None for a direct passthrough)
Registry = Dict[str, Tuple[Tuple[str, ...], MetricFn]]


class MetricError(Exception):
    """A `[SERIES]` row and the registry disagree. Config drift refuses, never guesses."""


def ratio(num: Optional[float], den: Optional[float],
          multiplier: float = 100.0) -> Optional[float]:
    """``num/den*multiplier`` -- None on any missing input or a zero denominator.

    Exactly the Excel form ``IF(OR(n="",d=""),"",IF(d=0,"",n/d*mult))``, which
    is the point: the blank and the divide-by-zero cases must land the same way
    in both languages.
    """
    if num is None or den is None or den == 0:
        return None
    return num / den * float(multiplier)


def total(*values: Optional[float]) -> Optional[float]:
    """None-propagating sum.

    A null component blanks the composite rather than understating it as zero.
    Summing a missing loan category as 0 quietly shrinks a concentration.
    """
    out = 0.0
    for value in values:
        if value is None:
            return None
        out += value
    return out


def ratio_fn(num: str, den: str, multiplier: float) -> Callable[[Fields], Optional[float]]:
    """Build the function for one row of a source's declarative ratio table."""
    def fn(fields: Fields) -> Optional[float]:
        return ratio(fields.get(num), fields.get(den), multiplier)
    return fn


def build_registry(direct: Sequence[str],
                   ratios: Mapping[str, Tuple[str, str, float]],
                   derived: Mapping[str, Tuple[Tuple[str, ...], MetricFn]]
                   ) -> Registry:
    """Assemble a source's registry from its three kinds of metric.

    ``direct``  -- the metric id IS a landed field, passed through.
    ``ratios``  -- the declarative table, which also drives the Excel formulas.
    ``derived`` -- the handful that need real code (multi-leg derivations).
    """
    registry: Registry = {name: ((name,), None) for name in direct}
    for name, (num, den, multiplier) in ratios.items():
        registry[name] = ((num, den), ratio_fn(num, den, multiplier))
    registry.update(derived)
    return registry


def metric_value(registry: Registry, metric_id: str,
                 fields: Fields) -> Optional[float]:
    """Latest-period fields -> one metric value, identical to the Excel formula."""
    consumed, fn = registry[metric_id]
    if fn is None:
        return fields.get(consumed[0])
    return fn(fields)


def validate_metrics(series: Sequence, registry: Registry,
                     landed_fields: Sequence[str]) -> None:
    """Every `[SERIES]` row must be a registered metric that agrees with the
    registry and consumes only fields the source actually lands."""
    known = ", ".join(sorted(registry))
    for row in series:
        if row.id not in registry:
            raise MetricError("Series '%s' is not a registered metric; known "
                              "metrics: %s." % (row.id, known))
        consumed, fn = registry[row.id]
        expected = "direct" if fn is None else "derived"
        if row.transform != expected:
            raise MetricError(
                "Series '%s' declares transform '%s' but the registry defines "
                "it as '%s'." % (row.id, row.transform, expected))
        for fname in consumed:
            if fname not in landed_fields:
                raise MetricError("Series '%s' consumes unlanded field '%s'."
                                  % (row.id, fname))
