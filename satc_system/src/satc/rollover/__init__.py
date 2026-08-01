"""ROLLOVER — turning last year into this year's starting point.

A returning client is not a blank page. They sent a stack of documents last
year, and the overwhelming majority of it will repeat. Two things follow, and
they are the highest-leverage automated-junior moves in the whole system:

* **The opening request list.** Last year's documents become this year's
  expected list, so the client is asked for what they actually sent rather than
  a generic checklist.
* **The omission diff.** What was in hand last year and has no counterpart this
  year. Tick-and-tie cannot catch this — you cannot tie out a document that
  never arrived — so it is the one gap a purely arithmetic review leaves open.

Both are deterministic set operations over the document register. No model, no
judgment, nothing written: the output is a list of QUESTIONS to put to a client,
because a missing document is not a finding. People close accounts.
"""

from __future__ import annotations

from satc.rollover.diff import (
    IN_HAND,
    OUTSTANDING,
    DocumentKind,
    OmissionReport,
    as_questions,
    omission_diff,
    opening_request_list,
)

__all__ = [
    "IN_HAND",
    "OUTSTANDING",
    "DocumentKind",
    "OmissionReport",
    "as_questions",
    "omission_diff",
    "opening_request_list",
]
