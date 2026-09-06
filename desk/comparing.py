"""Comparing our stored words with a publisher's — one set of rules, one copy.

WHY THIS IS A MODULE AND NOT A SECTION OF `tools/tieout.py`. Two things compare
our text against a source now: the corpus tie-out, which asks the question of all
531 passages on demand, and `proving`, which asks it of ONE answer at the moment
it is served. If each held its own folding table and its own reading of a marked
omission they would disagree within a week, and the two would report different
verdicts about the same passage with nothing comparing them — which is the shape
of nearly every real defect in this operation.

AND THERE IS A HARDER REASON, found on 6 September 2026. `proving` first reached
`tools/tieout.py` through a lazy import. That module fetches, so importing it
pulls in `ssl` — and this desk's `conftest.py` replaces the socket layer
outright, so the import raised `TypeError: function() argument 'code' must be
code, not str` from inside `ssl.py` and every test of `proving` failed for a
reason that had nothing to do with proving. The offline guard was right: a module
the engine's front door calls must not be able to reach the network by importing
something.

SO NOTHING HERE FETCHES OR IMPORTS ANYTHING THAT DOES. It is `re` and
`unicodedata`, and it is why the tests below can run at all.
"""
from __future__ import annotations

import re
import unicodedata

FOLD = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", " ": " ",
    "′": "'", "ﬁ": "fi", "ﬂ": "fl",
}

def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for bad, good in FOLD.items():
        text = text.replace(bad, good)
    return " ".join(text.split())


#: How a passage says it left something out. Chosen over a bare "..." because
#: that occurs inside real IRS prose, and over "…" because a passage carrying a
#: single character nobody can see is not marking anything to a reader.
ELLIPSIS = "[...]"


def _segments(text: str) -> list:
    """A stored passage split at its marked omissions.

    WHY A PASSAGE IS EVER ALLOWED TO OMIT ANYTHING. Publication 583 says the
    statement balance may not agree if the statement "Includes bank charges you
    did not enter in your books ... , or Does not include deposits made after
    the statement date". Two branches, opposite answers, one sentence — and
    #264 found that serving them as one entry is a defect, because a desk asked
    about an uncleared cheque gets handed the bank-charge branch as well.

    So the split is right. What was wrong until 6 September 2026 is that the
    second half stored the sentence's opening and then jumped to its own
    branch with NOTHING SAYING SO, and an answerer reading it had no way to know
    a branch had been removed. The firm, on the fourth docket: "Mark the
    omission."

    THE MARK MUST COST SOMETHING OR IT IS DECORATION. A tie-out compares our
    text against the publisher's, and an unmarked cut simply fails to be found
    — which is how this was discovered. A marked one is checked segment by
    segment, in order, so the mark buys honesty rather than an exemption.
    """
    return [x for x in (seg.strip() for seg in text.split(normalise(ELLIPSIS)))
            if x]


def elided_match(ours: str, live: str) -> tuple:
    """`(matched, first_segment_not_found)` for a passage with marked omissions.

    IN ORDER, AND THAT IS THE WHOLE STRICTNESS. Each segment is searched from
    where the last one ended, so a mark cannot reorder the source, cannot join
    two passages the document separates the other way round, and cannot cover a
    word changed inside a segment. Only the material BETWEEN segments is
    unchecked, which is exactly what the reader is being told to notice.

    Split out of `check` so it can be exercised without a network. `check`
    fetches, and this repository's desk suite replaces the socket layer
    outright -- so logic left inline there is logic no test can reach, and the
    guard would have been a claim about a function nobody could run.
    """
    pos = 0
    for seg in _segments(ours):
        at = live.find(seg, pos)
        if at < 0:
            return False, seg
        pos = at + len(seg)
    return True, ""
