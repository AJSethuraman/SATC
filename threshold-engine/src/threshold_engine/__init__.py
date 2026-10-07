"""Objective risk thresholds from any continuous signal.

Feed it a dated series -- a charge-off rate, a delinquency rate, a weighted
average probability of default -- and it finds the series' normal level and its
stress episodes, decides whether the worst episode is an outlier, and proposes
cutoffs for a rating scale. Every choice that is the bank's is a required
input; the engine never fills one in, and refuses rather than guess.

    from threshold_engine import Measure, Settings, run
"""
from .engine import Episode, Measure, Refused, Result, Settings, run, score
from .series import Point

__all__ = ["Episode", "Measure", "Point", "Refused", "Result", "Settings",
           "run", "score"]
