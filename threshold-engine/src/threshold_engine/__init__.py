"""Objective risk thresholds from any continuous signal.

Feed it dated series -- a charge-off rate, a delinquency rate, a weighted
average probability of default -- and it writes a workbook that sets the lines
a separate scoring file uses to rate each one 1 to 5. Every choice that is the
bank's is a required input; the tool never fills one in, and refuses rather
than guess. docs/WHAT-IT-DOES.md says what each part does.
"""
VERSION = "0.11.0"

from .scale import scale, score  # noqa: E402
from .series import Point  # noqa: E402

__all__ = ["Point", "VERSION", "scale", "score"]
