"""Finishing an interview: the gates, the record, the engagement.

**One engine, two front doors.** A human clicks through the web UI; automation
calls the CLI or this module directly. Both must pass the same gates, because a
control that lives in one front door is a control the other silently skips.

This module exists because they did not. Every rule below used to live inside
`cli._finish` -- the terminal's own code path -- so anything driving the
interview any other way got none of them:

* a HARD NO would not have stopped an engagement being created,
* `decision: no` would still have created one,
* the record would have had no `LetterDate`, `_season` or `_return_type`, so
  every document it fed would have failed to render or rendered wrong,
* nothing would have been priced.

`finish()` returns an `Outcome` -- a decision, not a printed message. The CLI
renders it as text, a web view renders it as a page, a test asserts on it. None
of them can reach the engagement store without going through the gates first,
because creating the engagement is inside this function and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import engagements
import interview as iv
import pricing

# Which federal form implies which kind of engagement. Drives which opening
# package a record gets, so a wrong answer here is a wrong letter.
RETURN_TYPE = {"1040": "individual", "1120S": "s_corp",
               "1065": "partnership", "1120": "c_corp"}


@dataclass
class Outcome:
    """What finishing the interview decided.

    `status` is the machine-readable answer and the only thing a caller should
    branch on:

    * `created`   -- gates passed, engagement written, `ref` and `record` set
    * `refused`   -- a HARD NO was flagged; nothing was written
    * `declined`  -- the decision question was not 'yes'; nothing was written
    * `error`     -- the fee schedule is malformed; nothing was written

    Only `created` writes anything. The other three are all "nothing was
    written", deliberately distinct: refusing work, declining it, and being
    unable to price it are three different things to a reader.
    """
    status: str
    reason: str = ""
    blockers: list[str] = field(default_factory=list)
    # Things a human should look at, which are not things that stop anything.
    # Computed on every outcome including the refused ones: a flag that only
    # appears when everything else went well is a flag nobody sees on the day
    # it matters.
    flags: list[str] = field(default_factory=list)
    ref: str | None = None
    path: Path | None = None
    record: dict | None = None
    overridden: bool = False

    @property
    def created(self) -> bool:
        return self.status == "created"

    @property
    def exit_code(self) -> int:
        """What a shell should see. `declined` is 0: deciding not to take work
        is the interview working, not failing."""
        return 0 if self.status in ("created", "declined") else 1


def compose_record(answers: dict, *, today: date | None = None) -> dict:
    """Interview answers -> the merge fields, minus the fee lines.

    Split out from `finish` so a caller can see what a record WOULD be without
    creating anything -- a web UI previewing before it commits, a test.
    """
    record = iv.compose(answers)
    record["LetterDate"] = (today or date.today()).strftime("%B %-d, %Y")
    record["_season"] = str(answers.get("tax_year") or "")
    record["_return_type"] = RETURN_TYPE.get(answers.get("federal_form"), "individual")
    record["_billable_counts"] = iv.billable_counts(answers)
    return record


def finish(answers: dict, *, store: Path | None = None, ref: str | None = None,
           fee_schedule=None, override_hard_no: bool = False,
           today: date | None = None) -> Outcome:
    """Run the gates, and create the engagement only if they all pass.

    The order is deliberate. Work the firm does not take is refused before the
    decision is consulted, because a HARD NO is not a judgement call; the
    decision is consulted before anything is composed, because composing a
    record for work nobody is doing is wasted; and pricing runs before the
    store is touched, so a malformed fee schedule cannot leave a half-made
    engagement behind.
    """
    blockers = iv.hard_no(answers)
    flags = iv.review_flags(answers)
    if blockers:
        if not override_hard_no:
            return Outcome(
                status="refused", blockers=blockers, flags=flags,
                reason="This is work the firm does not take. firm-settings.yaml "
                       "lists it under `hard_no` and the interview schema marks "
                       "the options themselves. Override only if the list is "
                       "wrong, not because this one feels like an exception.")
        # An override is recorded on the outcome so it reaches whatever is
        # reading -- a flag that can be set silently is a flag that means
        # nothing.
        overridden = True
    else:
        overridden = False

    decision = answers.get("decision")
    if decision != "yes":
        return Outcome(
            status="declined", blockers=blockers, overridden=overridden,
            flags=flags,
            reason=f"The decision was {decision!r}, not 'yes'. Nothing was "
                   f"created -- that is what the decision question is for.")

    record = compose_record(answers, today=today)

    # Priced before the store is touched. Any amount the firm has not set
    # carries its [CONFIRM] to the line and then to the total, so the estimate
    # refuses to render rather than quoting a client nothing for a service.
    try:
        schedule = pricing.load(fee_schedule) if fee_schedule else None
        record.update(pricing.price(answers, schedule))
    except pricing.PricingError as exc:
        return Outcome(status="error", blockers=blockers, overridden=overridden,
                       flags=flags,
                       reason=f"fee schedule: {exc}")

    store = store or engagements.STORE
    ref, path = engagements.create(record, ref=ref, store=store)
    engagements.save_answers(answers, ref, store)
    return Outcome(status="created", ref=ref, path=path, record=record,
                   blockers=blockers, overridden=overridden, flags=flags)
