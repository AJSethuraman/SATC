"""ACTIONS — what the practice would do next, already prepared.

The queue that answers "what needs me today?" without the owner having to
notice anything. Every entry carries its evidence in one line and, where it is
a message, a draft that is already written.

Nothing here sends, signs, files, or writes. It reduces a decision to one click
— it does not remove the decision. That is deliberate and permanent: sending
stays a human act, so the value has to come from making the click cheap.

Almost all of it is deterministic. A document is outstanding or it is not; a
deadline is nine days away or it is not; a 1099 arrived last year and hasn't
this year. Doctrine rule 8 — take the grind away from the human before asking a
model to be clever. A local model's budget goes on the margin: phrasing, and
the judgment calls the queue surfaces but cannot settle.
"""

from __future__ import annotations

from datetime import date

from satc.actions.propose import (
    ActionKind,
    ActionQueue,
    ProposedAction,
    Urgency,
    action_id,
    ask_prior_year_questions,
    at_least,
    chase_outstanding,
    chase_signature,
    credit_on_account,
    deadline_pressure,
    extension_candidate,
    invite_to_interview,
    invoice_overdue,
    invoice_unissued,
    sort_key,
    unbilled_work,
    undated_work,
)
from satc.models.readiness import assess

__all__ = [
    "ActionKind",
    "ActionQueue",
    "ProposedAction",
    "Urgency",
    "action_id",
    "build_queue",
    "sort_key",
]


def _carry_severity(money, jobs, invoices, payments, *, client_id: str, tax_year: int,
                    readiness=None, today: date | None = None):
    """Stand a row down without turning the volume down with it.

    A bill half-written and abandoned is STRICTLY WORSE than one never written:
    the work is out, the fee is unasked-for, and now the drafting is done too,
    so nobody will come back to it. Yet an undated draft demoted the year from
    "urgent — never billed" to "routine — a draft is sitting there", purely
    because the draft existed. The stand-down was there to remove a duplicate,
    not to downgrade the problem.

    Only the DRAFT rows inherit it. An issued invoice has actually asked the
    client for the money, and "five days past due" is genuinely a smaller
    problem than "never billed" — demoting that one is the right answer.

    THE QUESTION IS WHAT THE YEAR LOOKS LIKE WITHOUT *THIS DRAFT*, not what it
    looks like with the whole book thrown away. Dropping every invoice made the
    answer "nothing has ever been billed", so a year that was fully billed AND
    PAID escalated an unrelated draft to urgent — an escalation the settled
    invoice sitting beside it on the same screen flatly contradicts, and an
    urgency the ``why`` then could not explain. The bills that actually went out
    stay in the recomputation; only the drafts, which are the rows being
    weighed, come out of it.
    """
    issued = [inv for inv in invoices if inv.is_issued]
    stood_down = unbilled_work(jobs, issued, payments, client_id=client_id,
                               tax_year=tax_year, readiness=readiness, today=today)
    if stood_down is None:
        return money
    for_year = {str(inv.invoice_id) for inv in invoices
                if inv.client_id == client_id and inv.tax_year == tax_year}
    # "Finished", not "delivered": the derivation refuses to conclude delivery,
    # so a stand-down note that asserts it would smuggle the stronger claim back
    # in through the one sentence the owner actually reads.
    because = (f"The {tax_year} work behind it is already finished, and nothing "
               f"else in this queue is chasing that fee.")
    return [at_least(row, stood_down.urgency, because=because)
            if row.kind == "invoice_unissued" and row.invoice_id in for_year else row
            for row in money]


def build_queue(*, clients, requested=(), received=(), obligations=(),
                engaged_clients=(), jobs=(), invoices=(), payments=(),
                tax_year: int, today: date | None = None) -> ActionQueue:
    """Run every proposer over the practice and return the ordered queue.

    Takes plain records — no Flask, no STATE — so the whole queue is a pure
    function of the practice's data and one date. That is what makes it
    testable, and what makes "why is this here?" always answerable.

    ``payments`` is the LEDGER (``store.load_payments()``). It defaults to empty
    so every existing caller keeps working, and an empty ledger falls back to
    each invoice's own ``paid_on`` — but a caller that has the ledger and does
    not pass it will chase invoices that are already settled and ask for totals
    that are already part-paid. Principle 11b: the money rows are computed from
    what arrived, not from a flag.
    """
    today = today or date.today()
    engaged = set(engaged_clients)
    out: list[ProposedAction] = []

    for client_id in clients:
        signature = chase_signature(requested, client_id=client_id,
                                    tax_year=tax_year, today=today)
        if signature is not None:
            out.append(signature)

        chase = chase_outstanding(requested, client_id=client_id,
                                  tax_year=tax_year, today=today)
        # An 8879 chase already covers the outstanding list for this client; two
        # rows saying "chase them" is how a queue starts getting ignored.
        if chase is not None and signature is None:
            out.append(chase)

        prior = ask_prior_year_questions(received, requested, client_id=client_id,
                                         tax_year=tax_year, prior_year=tax_year - 1)
        if prior is not None:
            out.append(prior)

        extension = extension_candidate(requested, obligations, client_id=client_id,
                                        tax_year=tax_year, today=today)
        if extension is not None:
            out.append(extension)

        invite = invite_to_interview(received, requested, client_id=client_id,
                                     tax_year=tax_year,
                                     has_engagement=client_id in engaged)
        if invite is not None:
            out.append(invite)

        out.extend(deadline_pressure(obligations, client_id=client_id, today=today))

        # Money. Every proposer above chases paper; none of them ever noticed
        # that the paper went out and was never charged for.
        money = invoice_overdue(invoices, payments, client_id=client_id, today=today)
        money += invoice_unissued(invoices, client_id=client_id, today=today)
        # An overpayment is the one money fact with no chase attached, so it is
        # the one nothing else would ever surface.
        money += credit_on_account(invoices, payments, client_id=client_id)

        # Whether a job is FINISHED is derived from its tasks and from what is
        # still outstanding — never read off Job.stage, which nothing sets. A
        # job whose tasks are all ticked while a blocking document is still out
        # has not been done, and must not be proposed for billing.
        readiness = assess(requested, client_id=client_id, tax_year=tax_year)

        # unbilled_work stands down while a bill for the year is still unissued
        # or still owed, because that bill already has its own row here — a
        # client with an overdue invoice is not also told the year is unbilled
        # (one problem, one row, principle 13).
        unbilled = unbilled_work(jobs, invoices, payments, client_id=client_id,
                                 tax_year=tax_year, readiness=readiness, today=today)
        if unbilled is not None:
            money.append(unbilled)
        else:
            money = _carry_severity(money, jobs, invoices, payments,
                                    client_id=client_id, tax_year=tax_year,
                                    readiness=readiness, today=today)
        out.extend(money)

        # Finished work whose year nobody can read is not covered by any of
        # the above, because every one of them compares against a year.
        undated = undated_work(jobs, client_id=client_id)
        if undated is not None:
            out.append(undated)

    out.sort(key=sort_key)
    return ActionQueue(actions=out, generated_for=today)
