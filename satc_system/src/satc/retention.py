"""When an engagement ended, and therefore when its records may be destroyed.

THE PROMISE, in all four engagement letters and signed by clients:

    "We keep copies of your records and our work papers for seven years, after
     which they are destroyed."

The letters never said seven years from WHAT. The firm settled it on 4 September
2026 — **from the end of the engagement** — and then said the obvious next
thing: *"you can look at the engagement letter, it outlines the end of the
engagement."* It does, and it is not what anybody would guess.

    "Either of us may end this engagement in writing at any time. You are
     responsible for fees for work done up to that point. Our engagement
     otherwise concludes when we deliver the completed returns to you or, for
     e-filed returns, when you sign the authorization and we transmit them —
     NOT when the return is accepted."
        -- SATC Engagement Letter (Tax Preparation) §09, and the same clause in
           the Business Return and C Corporation letters.

So there are three endings, and two things that are emphatically not endings:

  1. ENDED IN WRITING, by either party, on the date of the notice. It beats
     everything else, including work still in progress.
  2. TRANSMITTED, for an e-filed return: the client signs the authorization AND
     the firm transmits. BOTH. A signed 8879 sitting in a drawer has not ended
     anything, and a transmission without a signature should never have
     happened.
  3. DELIVERED, for a return that is not e-filed: the completed returns reach
     the client.

  NOT ACCEPTANCE. The letter says so in as many words. An IRS acknowledgement
  can arrive days later or never; hanging a seven-year destruction clock on it
  would start the clock on a date the firm does not control and sometimes never
  receives.

  NOT PAYMENT. It appears nowhere in the clause. Fees are owed for work done —
  that is a debt, not a duration. An unpaid engagement still ends, and its
  records are still owed seven years of keeping.

BOOKKEEPING IS A DIFFERENT SHAPE and this is the part that would have been got
wrong by analogy. Its letter has no "concludes when" at all:

    "Either of us may end this engagement on <<NoticePeriod>> written notice."

A bookkeeping engagement is a rolling one. Nothing about it concludes on its
own, so **written notice is the only ending it has** — and until someone records
that notice, its records have no clock start and cannot be disposed of at all.
That is the correct behaviour, not a gap to paper over: silence means keep.

WHAT THIS MODULE DOES NOT DO. It never returns a date it had to guess. Every
answer is derived from a fact somebody recorded — a delivery, a transmission, a
written notice — and when there is no such fact the answer is ``None`` with a
reason, which the caller shows rather than defaults away. Nothing here deletes
anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal

# The firm's promise, in years. Contractual, not a setting: changing it means
# changing four engagement letters that clients have signed.
RETENTION_YEARS = 7

Basis = Literal["written_notice", "transmitted", "delivered"]

# How each basis reads to a person, for a disposal list somebody has to trust.
BASIS_LABEL: dict[str, str] = {
    "written_notice": "ended in writing",
    "transmitted": "e-filed return transmitted",
    "delivered": "completed returns delivered",
}


@dataclass(frozen=True)
class Ended:
    """When an engagement ended and on what fact — never on an inference."""

    on: date
    basis: Basis

    @property
    def label(self) -> str:
        return BASIS_LABEL[self.basis]

    def destroy_not_before(self, years: int = RETENTION_YEARS) -> date:
        """The earliest date the promise allows destruction.

        Whole years off the ending date. 29 February is stepped back to the 28th
        rather than raising -- a leap-day ending is not a reason to refuse to
        answer, and moving a destruction date one day LATER is the safe
        direction.
        """
        try:
            return self.on.replace(year=self.on.year + years)
        except ValueError:                      # 29 Feb -> non-leap year
            return self.on.replace(year=self.on.year + years, day=28)


@dataclass(frozen=True)
class Undetermined:
    """No ending has been recorded. Carries what is missing, for a person."""

    why: str


def engagement_ended(
    *,
    ended_in_writing_on: date | None = None,
    transmitted_on: date | None = None,
    authorization_signed: bool = False,
    delivered_on: date | None = None,
    is_rolling: bool = False,
) -> Ended | Undetermined:
    """The date this engagement ended, per the letter the client signed.

    Every argument is a FACT SOMEBODY RECORDED. None of them is inferred here,
    and the absence of all of them is an answer -- ``Undetermined`` -- not a
    default.

    ``is_rolling`` marks a bookkeeping engagement, which has no "concludes
    when": written notice is its only ending.
    """
    # 1. WRITTEN NOTICE BEATS EVERYTHING. "Either of us may end this engagement
    #    in writing at any time" -- at any time includes mid-return, so a
    #    delivery that happened afterwards does not un-end it.
    if ended_in_writing_on is not None:
        return Ended(ended_in_writing_on, "written_notice")

    if is_rolling:
        return Undetermined(
            "a bookkeeping engagement ends only on written notice, and none is "
            "recorded. Its letter has no 'concludes when' clause, so until the "
            "notice is recorded these records have no disposal date.")

    # 2. E-FILED: SIGNED AND TRANSMITTED. Both, in the letter's own order.
    if transmitted_on is not None and authorization_signed:
        return Ended(transmitted_on, "transmitted")
    if transmitted_on is not None and not authorization_signed:
        return Undetermined(
            "the return was transmitted but no signed authorization is on "
            "record. The letter ends the engagement when the client signs AND "
            "the firm transmits, so this is either a missing record or a "
            "return that should not have gone.")

    # 3. DELIVERED, for anything not e-filed.
    if delivered_on is not None:
        return Ended(delivered_on, "delivered")

    return Undetermined(
        "nothing that ends an engagement has been recorded — no written "
        "notice, no transmission, no delivery.")


def due_for_disposal(items: Iterable[tuple[str, Ended]], *,
                     today: date | None = None,
                     years: int = RETENTION_YEARS) -> list[tuple[str, date]]:
    """Which engagements are past their promised keeping period, oldest first.

    REPORTS; NEVER DESTROYS. The firm promised destruction at seven years and
    nothing in this repository destroys anything on a schedule -- that gap is
    recorded rather than quietly closed by a function nobody reviewed.
    """
    now = today or date.today()
    out = [(ref, e.destroy_not_before(years)) for ref, e in items
           if e.destroy_not_before(years) <= now]
    return sorted(out, key=lambda pair: pair[1])
