"""Two implementations of one rule, agreeing by luck rather than by wiring.

THE PATTERN THE DESK NAMED, 8 September 2026, after its FIFTH self-correction
of the week. It nearly reported a routing bug — a desk firing on zero matched
terms — then found it had written its own space-delimited matcher in a scratch
script instead of calling canon's `touches`. Run through the real one the match
was `receipts`, the paper kind. Its words:

    "the fifth time this week that approximating your matching code instead of
     calling it would have handed you a confident falsehood — the same root
     cause as the punctuation claim and the reversed-argument claim. I am
     reporting it because the pattern is now the finding."

    "If there is one guard to add on the desk side, it is making the real
     matcher the only reachable one."

AND THE PATTERN WAS INSIDE THIS REPOSITORY TOO. `domains._hits` re-implemented
the whole-word rule that `routing` and `engine` reach through
`load_record().touches`. Its own docstring claimed it was *"the same rule
`SUBJECTS.md` matches on and for the same recorded reason"* — asserting the
equivalence rather than depending on it.

**MEASURED BEFORE CHANGING ANYTHING: they agreed.** Ten probes across both
domains, zero divergences. So this was never a live bug — it was two copies of
one rule with nothing holding them together, which is the state every one of
those five near-misses started from.

DELEGATION IS TESTED, NOT TRUSTED. Asserting the two agree on a corpus would
pass forever while they drifted between the cases the corpus happens to hold.
This replaces the matcher and proves the classifier goes THROUGH it.
"""
from __future__ import annotations

import domains


def test_classify_goes_through_canons_matcher(monkeypatch):
    """Swap the real matcher for one that refuses everything. If `classify`
    still finds a domain, it is not using it."""
    import _canon
    real = _canon.load_record()

    class _Deaf:
        def __getattr__(self, name):
            return getattr(real, name)
        @staticmethod
        def touches(text, term):
            return False

    monkeypatch.setattr(_canon, "load_record", lambda: _Deaf())

    assert domains.classify("is an unexplained bank deposit taxable income?").domain is None, (
        "the classifier found a domain while the shared matcher was refusing "
        "everything — it is running its own copy of the rule")


def test_the_real_matcher_still_classifies():
    """The mirror: with nothing patched, the same question resolves."""
    assert domains.classify(
        "is an unexplained bank deposit taxable income?").domain is not None
