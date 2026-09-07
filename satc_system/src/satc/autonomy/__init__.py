"""The autonomy ladder — see ``docs/AUTONOMY-CHARTER.md`` at the repo root, binding.

That document governs everything under this package and is updated in the same
commit as any decision that changes it (its own words, §0).

This module (:mod:`satc.autonomy.approval`) is the recorded fact of an owner's
decision on a rendered draft (charter §11 — "a gap in the foundation, named
rather than assumed"): what was rendered, what the owner says they sent, who
decided and when, byte-compared rather than judged. Nothing here computes a
streak, classifies a template as ``routine`` vs ``money_or_deadline``, checks
the preconditions gate, or sends anything — those are derived from the
approvals this module records (principle 3 — computed, never stored) and, if
built elsewhere in this package, are layered on top of it rather than inside
it.

NOTE FOR WHOEVER NEXT TOUCHES THIS FILE: other slices of the same charter
(the streak ladder, the preconditions gate, the trap drill) may land in this
same package and want their own names exported here too. Add to the imports
below rather than replacing them — this file's job is a plain re-export list,
so two slices landing the same week can both extend it without either one
overwriting the other's names.
"""

from satc.autonomy.approval import (
    Approval,
    ApprovalError,
    REASON_CODES,
    all_approvals,
    approval_id,
    approvals_for,
    hash_text,
    merge,
    record_approval,
    record_correction,
)
from satc.autonomy.traps import (
    DrillResult,
    SyntheticPractice,
    TrapResult,
    run_drill,
)

__all__ = [
    "Approval",
    "ApprovalError",
    "REASON_CODES",
    "all_approvals",
    "approval_id",
    "approvals_for",
    "hash_text",
    "merge",
    "record_approval",
    "record_correction",
    "DrillResult",
    "SyntheticPractice",
    "TrapResult",
    "run_drill",
]
