"""PROPOSED ACTIONS — the practice noticing things so the owner doesn't have to.

The whole point of the system, stated plainly: *you should never have to remember
that it is time to chase a 1099, that an 8879 has been sitting unsigned for two
weeks, or that a client's cutoff passed and they need extending.* The practice
knows all of that already — it is sitting in the document register, the clock,
and last year's return. Nobody was reading it.

This module reads it, and turns it into a queue of things that are **already
prepared** and need one decision each.

Three rules shape it:

1. **Deterministic first.** Almost every proposal here is a query, not a
   judgment: a document is outstanding, a deadline is 9 days away, a document
   that arrived last year hasn't this year. Doctrine rule 8 — remove the grind
   before asking a model to be smart. A local model gets the margin, not the
   bulk.
2. **Propose, never dispose.** Nothing here sends, signs, files, or writes. Each
   action carries a prepared draft and a reason; the owner clicks once. Sending
   stays a human act, and this is the machinery that makes that click cheap
   rather than the machinery that removes it.
3. **Idempotent.** ``action_id`` is derived from what the action is *about*, not
   when it was generated, so regenerating the queue produces the same ids and a
   dismissed action stays dismissed (doctrine rule 4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Literal

from satc.models.actor import INTAKE, Actor

ActionKind = Literal[
    "chase_documents",        # outstanding items, and it has been a while
    "prior_year_question",    # in hand last year, no trace this year
    "signature_outstanding",  # an 8879 is out and unsigned
    "deadline_approaching",   # a statutory date is close and the work is not done
    "extension_candidate",    # cutoff passed with the file incomplete
    "interview_invite",       # a client with no engagement for the year
    "deliver_return",         # the return is done and the client has not been told
    "unbilled_work",          # the work is finished and no bill accounts for it
    "invoice_overdue",        # issued, unpaid, past its due date
    "invoice_unissued",       # a draft bill that was never sent
    "credit_on_account",      # more money arrived than the invoice asked for
]

Urgency = Literal["overdue", "urgent", "soon", "routine"]

_URGENCY_ORDER = {"overdue": 0, "urgent": 1, "soon": 2, "routine": 3}


@dataclass(frozen=True, slots=True)
class ProposedAction:
    """One thing worth doing, with the reason and the draft already chosen."""

    action_id: str
    kind: ActionKind
    client_id: str
    title: str
    why: str
    """The EVIDENCE, in the owner's language. Never "the system suggests" — a
    proposal the owner cannot audit in one line is a proposal they have to redo."""

    urgency: Urgency = "routine"
    due: date | None = None
    template_key: str = ""
    """Which comms template drafts this. Empty when the action is not a message."""

    invoice_id: str = ""
    """WHICH invoice this row is about, when it is about one.

    Carried as its own field rather than left in :attr:`evidence` because a LINK
    needs one unambiguous value. Without it the screen can only say "this client,
    this year", and the comms draft then resolves its figures from whichever
    invoice is newest — so a row titled "Invoice 2026-0004 unpaid" opens a draft
    quoting a different number and a different amount. A figure in a
    client-facing draft that is not the fact the row asserts is principle 1.
    """

    evidence: tuple[str, ...] = ()
    proposed_by: Actor = INTAKE

    @property
    def is_from_model(self) -> bool:
        return self.proposed_by.is_model

    @property
    def has_draft(self) -> bool:
        return bool(self.template_key)

    def days_until(self, today: date) -> int | None:
        return None if self.due is None else (self.due - today).days


def action_id(kind: str, client_id: str, subject: str = "") -> str:
    """Stable identity: what it is ABOUT, never when it was generated.

    Regenerating the queue must produce the same ids, or a dismissed action
    reappears every refresh and the queue becomes noise the owner learns to
    ignore — which is the real failure mode for a tool like this.
    """
    parts = [kind, client_id, subject.strip().lower().replace(" ", "-")]
    return "/".join(p for p in parts if p)


def _urgency_from_days(days: int | None, *, soon: int = 30, urgent: int = 7) -> Urgency:
    if days is None:
        return "routine"
    if days < 0:
        return "overdue"
    if days <= urgent:
        return "urgent"
    if days <= soon:
        return "soon"
    return "routine"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one}" if n == 1 else f"{n} {many}"


def at_least(action: ProposedAction, urgency: Urgency, *,
             because: str = "") -> ProposedAction:
    """The same action, never quieter than ``urgency``.

    For the case where one row stands another down. Suppressing a duplicate is
    right; suppressing it into a calmer row is not — the practice ends up
    quieter about a worse situation than it would have been about a better one.
    The surviving row inherits the severity of the row it replaced, and says
    why it got louder, because an urgency the ``why`` cannot explain is a
    proposal the owner has to re-derive.
    """
    if _URGENCY_ORDER[urgency] >= _URGENCY_ORDER[action.urgency]:
        return action
    why = f"{action.why} {because}".strip() if because else action.why
    return replace(action, urgency=urgency, why=why)


# --- the individual proposers -------------------------------------------------
#
# Each takes plain records and returns zero or one action. Kept separate so a
# rule can be changed, tested, or switched off on its own.


def chase_outstanding(requested, *, client_id: str, tax_year: int,
                      today: date, stale_after_days: int = 3) -> ProposedAction | None:
    """Outstanding requests that have been sitting long enough to nudge.

    The 3-day default is FIRM POLICY with no citation behind it — a practitioner
    convention, not a rule. It is a parameter for exactly that reason.
    """
    outstanding = [r for r in requested
                   if r.client_id == client_id and r.is_open
                   and getattr(r, "tax_year", None) == tax_year]
    if not outstanding:
        return None

    oldest = min((r.requested_at for r in outstanding
                  if getattr(r, "requested_at", None)), default=None)
    waiting = (today - oldest).days if oldest else None
    if waiting is not None and waiting < stale_after_days:
        return None

    types = [r.doc_type for r in outstanding]
    since = f", the oldest asked {waiting} days ago" if waiting is not None else ""
    return ProposedAction(
        action_id=action_id("chase_documents", client_id, str(tax_year)),
        kind="chase_documents", client_id=client_id,
        title=f"Chase {_plural(len(outstanding), 'outstanding document', 'outstanding documents')}",
        why=f"{', '.join(types[:4])} still outstanding for {tax_year}{since}.",
        urgency="urgent" if (waiting or 0) >= 14 else "soon",
        template_key="missing_items", evidence=tuple(types))


def ask_prior_year_questions(received, requested=(), *, client_id: str, tax_year: int,
                             prior_year: int) -> ProposedAction | None:
    """Documents in hand last year with no trace this year.

    The highest-value proposal in the set, because nothing else in a tax review
    can find it: you cannot tie out a document that never arrived.
    """
    from satc.rollover import omission_diff

    report = omission_diff(received, requested, client_id=client_id,
                           prior_year=prior_year, current_year=tax_year)
    if not report.missing:
        return None
    types = [k.doc_type for k in report.missing]
    return ProposedAction(
        action_id=action_id("prior_year_question", client_id, str(tax_year)),
        kind="prior_year_question", client_id=client_id,
        title=f"Ask about {_plural(len(types), 'document', 'documents')} not seen this year",
        why=(f"{', '.join(types)} {'was' if len(types) == 1 else 'were'} on file for "
             f"{prior_year} with nothing for {tax_year} — not even requested."),
        urgency="soon", template_key="prior_year_check", evidence=tuple(types))


def chase_signature(requested, *, client_id: str, tax_year: int,
                    today: date) -> ProposedAction | None:
    """An e-file authorization that is out and not back.

    Called out separately from ordinary document chasing because nothing can be
    transmitted without it — an unsigned 8879 blocks the filing, not just the file.
    """
    pending = [r for r in requested
               if r.client_id == client_id and getattr(r, "tax_year", None) == tax_year
               and r.is_open and "8879" in str(r.doc_type)]
    if not pending:
        return None
    oldest = min((r.requested_at for r in pending
                  if getattr(r, "requested_at", None)), default=None)
    waiting = (today - oldest).days if oldest else None
    return ProposedAction(
        action_id=action_id("signature_outstanding", client_id, str(tax_year)),
        kind="signature_outstanding", client_id=client_id,
        title="Chase the signed 8879",
        why=(f"Form 8879 has been out {waiting} days and is not back — nothing can be "
             f"transmitted until it is." if waiting is not None
             else "Form 8879 is out and not back — nothing can be transmitted until it is."),
        urgency="urgent" if (waiting or 0) >= 7 else "soon",
        template_key="missing_items", evidence=("Form 8879",))


def deadline_pressure(obligations, *, client_id: str, today: date,
                      soon_days: int = 30) -> list[ProposedAction]:
    """Statutory deadlines close enough to matter, from the clock."""
    out: list[ProposedAction] = []
    for duty in obligations:
        if duty.client_id != client_id:
            continue
        days = duty.days_until(today)
        if days > soon_days:
            continue
        urgency = _urgency_from_days(days, soon=soon_days)
        when = ("was due" if days < 0 else "is due")
        assumed = " (from an unconfirmed assumption about this client)" if duty.is_assumed else ""
        out.append(ProposedAction(
            action_id=action_id("deadline_approaching", client_id,
                                f"{duty.form}-{duty.period_key}"),
            kind="deadline_approaching", client_id=client_id,
            title=f"{duty.form} for {duty.period_key} {when} {duty.due:%b %d}",
            why=(f"{duty.jurisdiction} {duty.form}, {duty.period_key}: "
                 f"{'overdue by ' + str(-days) + ' days' if days < 0 else str(days) + ' days away'}"
                 f"{assumed}."),
            urgency=urgency, due=duty.due, evidence=(duty.obligation_key,)))
    return out


def extension_candidate(requested, obligations, *, client_id: str, tax_year: int,
                        today: date) -> ProposedAction | None:
    """The firm cutoff has passed and the file is still incomplete.

    SATC proposes; it never decides. Filing an extension without the client's
    written authorization can destroy their reasonable-cause defence, so this is
    a flag and a conversation, not an action.
    """
    duty = next((o for o in obligations
                 if o.client_id == client_id and o.documents_due
                 and str(o.period_key) == str(tax_year)), None)
    if duty is None or duty.documents_due is None or today <= duty.documents_due:
        return None
    outstanding = [r for r in requested
                   if r.client_id == client_id and r.is_open
                   and getattr(r, "tax_year", None) == tax_year]
    if not outstanding:
        return None
    return ProposedAction(
        action_id=action_id("extension_candidate", client_id, str(tax_year)),
        kind="extension_candidate", client_id=client_id,
        title=f"Likely extension — {duty.form} {tax_year}",
        why=(f"Your cutoff was {duty.documents_due:%b %d} and "
             f"{_plural(len(outstanding), 'item is', 'items are')} still outstanding. "
             f"An extension needs the client's written authorisation before you file it."),
        urgency="urgent", due=duty.due,
        evidence=tuple(r.doc_type for r in outstanding))


def invite_to_interview(received, requested=(), *, client_id: str, tax_year: int,
                        has_engagement: bool) -> ProposedAction | None:
    """A client with nothing started for the year."""
    if has_engagement:
        return None
    this_year = [r for r in list(received) + list(requested)
                 if r.client_id == client_id and getattr(r, "tax_year", None) == tax_year]
    if this_year:
        return None
    return ProposedAction(
        action_id=action_id("interview_invite", client_id, str(tax_year)),
        kind="interview_invite", client_id=client_id,
        title=f"Nothing started for {tax_year}",
        why=f"No engagement and no {tax_year} documents on file.",
        urgency="routine", template_key="interview_invite")


# --- the money, which was the one thing the queue never mentioned -------------
#
# Everything above chases paper. None of it ever noticed that the paper was
# delivered and never charged for. Unbilled work does not announce itself: there
# is no client asking about it, no deadline attached to it, and no screen that
# goes red. It is the only failure mode here that costs the practice money
# directly, and it was invisible.

_FINISHED = "ready_to_deliver"
"""How far the practice can honestly say a job has got.

WHAT THIS USED TO BE, AND WHY IT COULD NOT STAY. These rows keyed on
``job.stage in ("delivered", "complete")`` — a field with no producer anywhere
in the app, so in the running system this whole section was dead code. The stage
is now DERIVED (:func:`satc.work.stage.derive_stage`), and the derivation
REFUSES to conclude ``delivered`` or ``complete``: the practice records no fact
for "the 8879 went out", and reading a finished task list as a delivery would be
a guess about the single step that matters most here — whether the client has
the return.

So billing cannot key on delivery, because delivery is not a fact this system
holds. ``ready_to_deliver`` — every internal task on the job settled, with
nothing outstanding that blocks prep — is the furthest-along thing that IS one.
It is a weaker claim than the old one, and every row built on it SAYS SO in its
own words rather than quietly asserting the stronger thing (principles 1 and 5).
Silence was the other option and it is worse: a year's work finished and never
billed is the one failure here that no other screen mentions.
"""


def _is_finished(job, readiness=None) -> bool:
    """Is every piece of internal work on this job settled?

    Asks the derivation, never ``job.stage``. Passing ``readiness`` matters:
    without it a job whose tasks are all ticked while a blocking W-2 is still
    outstanding reads as finished, and the queue then proposes billing for work
    that cannot actually have been done.
    """
    from satc.work.stage import derive_stage

    return derive_stage(job, readiness=readiness).stage == _FINISHED


def _job_label(job) -> str:
    """How the owner would name this job out loud."""
    label = (getattr(job, "engagement_type", "") or getattr(job, "workflow_key", "")
             or "Work")
    return str(label).replace("_", " ")


_YEAR_AT_START = re.compile(r"^(\d{4})(?!\d)")
"""A period key opens with its year, or it does not tell us one.

``period_key`` is the recurrence anchor and work.py's own examples for it are
``2025``, ``2026Q1`` and ``2026-03``. Reading only a bare ``2025`` dropped every
quarterly and monthly job — payroll and bookkeeping, which is exactly the
recurring, easily-forgotten billing this section exists to catch.

Deliberately anchored and deliberately narrow: ``20251`` is not a year followed
by something, it is a number nobody here can read, and guessing at it would be
principle 5 in reverse.
"""


def _job_year(job) -> int | None:
    """The year a job belongs to, or ``None`` when the practice cannot say.

    ``None`` is not "no year" — it is "we do not know", and the caller has to
    treat it as a question rather than silently dropping the job.
    """
    year = getattr(job, "tax_year", None)
    if year is not None:
        return int(year)
    found = _YEAR_AT_START.match(str(getattr(job, "period_key", "") or "").strip())
    return int(found.group(1)) if found else None


def _amount(invoice) -> str:
    return f"${invoice.total:,.2f}"


def _dollars(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _finished_on(job) -> date | None:
    """When the last piece of internal work on this job was settled.

    Read off the completion records, which carry a real timestamp, so a file
    that has sat finished and unbilled since January can be told apart from one
    that finished this morning. ``None`` when nothing on the job records a
    completion — and ``None`` stays ``None``: an age nobody wrote down is not an
    age of zero.
    """
    stamps = [t.completion.at for t in job.tasks
              if t.audience == "internal" and t.completion is not None]
    return max(stamps).date() if stamps else None


def _bills_raised(invoices, *, client_id: str, tax_year: int) -> list:
    """The bills that exist for this client-year — issued, or a draft with something on it."""
    return [inv for inv in invoices
            if inv.client_id == client_id and inv.tax_year == tax_year
            and (inv.is_issued or inv.lines)]


def balance_owed(invoice, payments=()) -> Decimal:
    """What is still owed on one invoice — from the LEDGER, not from a flag.

    Money arriving is a FACT; "paid" is a CONCLUSION computed from the payment
    ledger (principle 11b). So wherever the ledger has anything to say about an
    invoice, it decides: a fully settled invoice whose ``paid_on`` was never
    written is not chased, and a part-paid invoice is owed its BALANCE rather
    than its total. Chasing a client for money they already sent is the kind of
    confident wrong answer that costs the practice the client.

    ``paid_on`` is not ignored, because it is the only record the practice has
    of money that arrived before the ledger existed. It is the FALLBACK,
    consulted only when no payment on file names this invoice at all — never a
    veto over a ledger entry that contradicts it.
    """
    from satc.billing.payment import outstanding

    mine = [p for p in payments if p.invoice_id == invoice.invoice_id]
    if mine:
        return outstanding(invoice, mine)
    return Decimal("0.00") if invoice.is_paid else invoice.total


def _year_is_settled(raised, payments) -> bool:
    """Every bill raised for this client-year is out and paid in full.

    "Paid" is read off the ledger (:func:`balance_owed`), not off the flag —
    principle 11b. A year in this state produces no other money row anywhere on
    the screen, which is precisely why it is the dangerous one.
    """
    return all(inv.is_issued and balance_owed(inv, payments) == 0 for inv in raised)


def unbilled_work(jobs, invoices=(), payments=(), *, client_id: str,
                  tax_year: int, readiness=None, today: date | None = None,
                  cold_after_days: int = 30) -> ProposedAction | None:
    """Work the practice has finished that no bill on file accounts for.

    Not a late payment — money the practice never asked for. A return that was
    finished and never invoiced is the one failure here that nothing else
    surfaces: the client is happy, the file looks finished, and the fee is gone.

    FINISHED, NOT DELIVERED. This used to key on ``job.stage``, which nothing
    ever set, and the stage it wanted — ``delivered`` — is one the derivation
    refuses to reach because the practice records no delivery fact (see
    :data:`_FINISHED`). It now keys on the strongest claim available: every
    internal task on the job settled, with nothing outstanding that blocks prep.
    That is genuinely weaker, so every row below says which of the two it is
    asserting instead of letting the owner assume the stronger one.

    ``cold_after_days`` replaces the old ``complete`` stage as the loudness
    signal, on a fact that exists: how long ago the last task on the job was
    actually settled. FIRM POLICY, uncited — a month of finished work sitting
    unbilled is a practitioner's judgement, not a rule. With no ``today``, or
    with no completion recorded, no age is claimed at all.

    One row per client-year, never one per job. A client with three finished
    jobs and no invoice has one problem, not three.

    WHAT THE PRACTICE ACTUALLY KNOWS ABOUT COVERAGE. Nothing on file ties an
    invoice line to a job — no line carries a ``job_id`` and no job carries an
    invoice number (principle 2: that fact was never recorded, so it cannot be
    read). Counting lines against jobs was a proxy for that missing fact, and it
    was wrong in BOTH directions: one line for a package of work that produced
    two jobs invented a shortfall the practice does not have, and a line for a
    consultation "covered" a delivered return it had nothing to do with. A
    proxy that can invent either answer is not evidence.

    So this answers only what it can stand behind:

    * **No bill raised for the year at all.** Zero lines cannot cover anything.
      This is arithmetic, not judgment, and it is the whole reason the proposer
      exists. It says so, loudly.
    * **Bills exist and the year is not yet settled.** Whatever is unbilled is
      indistinguishable, from here, from what is merely unpaid — and the bill
      itself already has a row from :func:`invoice_unissued` or
      :func:`invoice_overdue`. Silence here, because a second row about the
      same year is how the owner learns to scroll past the queue (principle 13).
    * **Bills exist and the year is settled in full.** Now nothing else on the
      screen mentions this year at all, and the practice STILL cannot say
      whether every finished job was billed. Silence would be the confident
      wrong answer (principle 5), so it says the thing it actually knows: that
      it cannot tell, and why. Quietly — this is a look before closing the
      year, not an alarm.
    """
    finished = [j for j in jobs
                if j.client_id == client_id and _job_year(j) == tax_year
                and _is_finished(j, readiness)]
    if not finished:
        return None

    raised = _bills_raised(invoices, client_id=client_id, tax_year=tax_year)
    labels = sorted({_job_label(j) for j in finished})
    work = (f"{', '.join(labels)} for {tax_year} "
            f"{'is' if len(finished) == 1 else 'are'} finished — every task settled")

    # The one line that keeps the row honest. What the owner would otherwise
    # read into "finished and unbilled" is "delivered and unbilled", and that
    # is the stronger claim the practice cannot make.
    caveat = ("SATC records nothing for the return actually going out, so this "
              "is finished work, not confirmed delivery.")

    if not raised:
        ages = [_finished_on(j) for j in finished]
        oldest = min((a for a in ages if a is not None), default=None)
        sat = (today - oldest).days if (today is not None and oldest is not None) else None
        # Only when the practice actually wrote a completion down. No timestamp
        # is not an age of zero, and "settled today" said about a job nobody
        # recorded finishing is a fact invented out of an absence.
        aged = ("" if sat is None or sat < 0 else
                f" The last task on it settled "
                f"{'today' if sat == 0 else _plural(sat, 'day', 'days') + ' ago'}.")
        return ProposedAction(
            action_id=action_id("unbilled_work", client_id, str(tax_year)),
            kind="unbilled_work", client_id=client_id,
            title=f"Bill the {tax_year} work",
            why=(f"{work} and there is no invoice at all — nothing has been "
                 f"billed for {tax_year}.{aged} {caveat}"),
            # Work finished a month ago and still unbilled is money the practice
            # is losing track of; work finished this week is simply the next
            # thing to do. An age nobody recorded claims neither.
            urgency="urgent" if (sat is not None and sat >= cold_after_days) else "soon",
            evidence=tuple(j.job_id for j in finished))

    if not _year_is_settled(raised, payments):
        return None

    return ProposedAction(
        # A DIFFERENT assertion about the same year, so a different id. Standing
        # down "I cannot confirm this was all billed" must not also silence
        # "this was never billed at all" if a later finished job makes that true.
        action_id=action_id("unbilled_work", client_id, f"{tax_year}-coverage"),
        kind="unbilled_work", client_id=client_id,
        title=f"Check the {tax_year} billing before you close the year",
        why=(f"{work}, and the {_plural(len(raised), 'invoice', 'invoices')} for "
             f"{tax_year} {'is' if len(raised) == 1 else 'are'} issued and paid in "
             f"full. Nothing on file records which job any invoice line was for, "
             f"so SATC cannot confirm every finished job was billed — it can only "
             f"tell you it does not know. {caveat} Worth one look while the year "
             f"is fresh."),
        urgency="routine",
        evidence=tuple(j.job_id for j in finished))


def undated_work(jobs, *, client_id: str) -> ProposedAction | None:
    """Finished work whose year the practice genuinely cannot read.

    No ``readiness`` argument, and that is not an oversight: readiness is
    assessed per client-YEAR, and the year is precisely the thing missing here.
    Asking with a readiness borrowed from some other year would be inventing the
    fact this row exists to report.

    A job with no ``tax_year`` and a ``period_key`` nobody here can parse used
    to fall out of every year's comparison and be surfaced by nothing. That is
    the silent drop principle 1 exists to forbid: no fact, so the slot is marked
    VISIBLY, not guessed and not discarded.

    Filed under its own id rather than folded into a year's row, because
    assigning it to a year is the one thing we have just said we cannot do.

    NO BILL CAN STAND THIS ROW DOWN, and that is the trap. The check that would
    clear it — compare this job against that year's invoices — needs the year,
    and the year is the missing thing. So a job with an unreadable period that
    HAS in fact been billed used to sit in "Coming up" forever, and a row that
    can never go away is exactly the row that trains the owner to scroll past
    the queue (principle 13). It stays, because dropping it silently is worse,
    but it stays QUIET and it names the one act that resolves it (principle 10):
    record the year on the job, and every ordinary check starts working again.
    """
    undated = [j for j in jobs
               if j.client_id == client_id and _job_year(j) is None
               and _is_finished(j)]
    if not undated:
        return None
    periods = sorted({str(getattr(j, "period_key", "") or "").strip() or "(blank)"
                      for j in undated})
    return ProposedAction(
        action_id=action_id("unbilled_work", client_id, "undated"),
        kind="unbilled_work", client_id=client_id,
        title=f"{_plural(len(undated), 'delivered job has', 'delivered jobs have')} no readable year",
        why=(f"{', '.join(sorted({_job_label(j) for j in undated}))} "
             f"{'is' if len(undated) == 1 else 'are'} finished carrying no "
             f"tax year and a period of {', '.join(periods[:4])} — SATC cannot say which "
             f"year to check them against, so nothing else will ever ask whether they "
             f"were billed. Put a tax year on the job and this row goes away; until "
             f"then it has to be checked by hand."),
        # Deliberately the quietest setting there is. Nothing the practice can
        # record about billing will clear it, so it must not sit in a band that
        # implies a deadline it does not have.
        urgency="routine",
        evidence=tuple(j.job_id for j in undated))


def invoice_overdue(invoices, payments=(), *, client_id: str, today: date,
                    chase_after_days: int = 14,
                    serious_after_days: int = 45) -> list[ProposedAction]:
    """Issued, still owed, and past its due date — one row per invoice.

    Separate rows because separate invoices are separate facts: different
    numbers, different amounts, different dates, and the client will ask about
    one of them by number.

    WHAT IS OWED COMES FROM THE LEDGER, never from ``paid_on`` (principle 11b,
    and :func:`balance_owed`). Two things turn on that. A client who settled in
    full without anyone ticking the flag is not chased for money they already
    sent. And a client who paid part of it is chased for the BALANCE — the row
    says $150 is owed on a $450 invoice, because asking for $450 when $300 has
    arrived is the kind of letter that ends a relationship.

    The two thresholds are FIRM POLICY with nothing statutory behind them
    (principle 4). An invoice four days past due is usually sitting in somebody's
    inbox; treating that as a collection problem is how a client learns to
    ignore what you send.
    """
    out: list[ProposedAction] = []
    for inv in invoices:
        if inv.client_id != client_id or not inv.is_issued or inv.due_on is None:
            continue
        owed = balance_owed(inv, payments)
        if owed <= 0 or inv.due_on >= today:
            continue
        late = (today - inv.due_on).days
        if late >= serious_after_days:
            urgency: Urgency = "overdue"
        elif late >= chase_after_days:
            urgency = "urgent"
        else:
            urgency = "soon"
        part_paid = owed < inv.total
        if part_paid:
            title = f"Invoice {inv.invoice_id} part-paid — {_dollars(owed)} still owed"
            why = (f"Invoice {inv.invoice_id} for {_amount(inv)} ({inv.tax_year} work) "
                   f"was due {inv.due_on:%b %d}. "
                   f"{_dollars(inv.total - owed)} has been received against it and "
                   f"{_dollars(owed)} is still owed, {_plural(late, 'day', 'days')} "
                   f"past due.")
        else:
            title = f"Invoice {inv.invoice_id} unpaid — {_amount(inv)}"
            why = (f"Invoice {inv.invoice_id} for {_amount(inv)} ({inv.tax_year} work) "
                   f"was due {inv.due_on:%b %d} and is {_plural(late, 'day', 'days')} "
                   f"unpaid.")
        out.append(ProposedAction(
            action_id=action_id("invoice_overdue", client_id, str(inv.invoice_id)),
            kind="invoice_overdue", client_id=client_id,
            title=title, why=why,
            urgency=urgency, due=inv.due_on, template_key="invoice_cover",
            # The draft has to be about THIS invoice. Handing the comms screen
            # only the client and the year lets it pick the newest bill, and a
            # client then reads a covering note whose number and amount are not
            # the ones this row named.
            invoice_id=str(inv.invoice_id),
            evidence=(str(inv.invoice_id),)))
    return out


def credit_on_account(invoices, payments=(), *, client_id: str) -> list[ProposedAction]:
    """More money arrived against an invoice than the invoice asked for.

    THE ROW THAT EXISTED BECAUSE OF A FLOOR. :func:`balance_owed` stops at zero,
    which is right — an overpayment is a credit, not a debt owed to the practice,
    and letting it go negative would quietly cancel out what another client
    genuinely owes. But the floor also made the overpayment DISAPPEAR: the
    invoice is settled, so nothing chases it; it is issued, so it is not a draft;
    the year is paid in full, so no billing row mentions it. A client who sent
    $600 for a $450 bill was, everywhere on this screen, a client who was square.

    Money the practice is holding and did not ask for is not a quiet
    bookkeeping detail. It is either a refund or a credit against the next bill,
    and both are the OWNER's call, not this queue's — so the row names the
    amount, the invoice, and the two options, and stops there (principle 9).

    One row per invoice, like :func:`invoice_overdue`, because the client will
    raise it by number: "you've got an extra $150 against 2026-0003".
    """
    from satc.billing.payment import overpaid_by, paid_on_invoice

    out: list[ProposedAction] = []
    for inv in invoices:
        if inv.client_id != client_id:
            continue
        credit = overpaid_by(inv, payments)
        if credit <= 0:
            continue
        out.append(ProposedAction(
            action_id=action_id("credit_on_account", client_id, str(inv.invoice_id)),
            kind="credit_on_account", client_id=client_id,
            title=f"{_dollars(credit)} overpaid on invoice {inv.invoice_id}",
            why=(f"{_dollars(paid_on_invoice(inv, payments))} has arrived against "
                 f"invoice {inv.invoice_id}, which was for {_amount(inv)} — "
                 f"{_dollars(credit)} more than was billed. The invoice is settled, "
                 f"so nothing else here mentions it. Refund it or hold it against "
                 f"the next bill; the client is owed the conversation either way."),
            # Not a deadline, but not routine either: this is the client's money
            # sitting in the practice's account, and it gets more awkward to
            # raise the longer nobody does.
            urgency="soon",
            # No template. Refund or credit is a decision with a figure attached,
            # and pre-writing either one would be choosing for the owner.
            invoice_id=str(inv.invoice_id),
            evidence=(str(inv.invoice_id),)))
    return out


def invoice_unissued(invoices, *, client_id: str, today: date,
                     stale_after_days: int = 7,
                     urgent_after_days: int = 30) -> list[ProposedAction]:
    """A draft bill that was never sent.

    The same lost money as unbilled work, one step later and easier to miss —
    the invoice exists, so anything that counts invoices looks right. Nobody is
    waiting on it, because nobody outside this machine knows it was written.
    """
    out: list[ProposedAction] = []
    for inv in invoices:
        # A draft with no lines is not a bill someone forgot: there is nothing on
        # it, and issue() would refuse it anyway. Surfacing it would be a row
        # about zero dollars.
        if inv.client_id != client_id or inv.is_issued or not inv.lines:
            continue

        dated = [line.performed_on for line in inv.lines if line.performed_on]
        waiting = (today - max(dated)).days if dated else None
        if waiting is not None and waiting < stale_after_days:
            continue                       # billing in progress is not a problem

        if waiting is None:
            # No line carries a date, so the practice holds no fact about how
            # long this has sat. Say what is known and claim nothing more
            # (principle 1) — an invented age would read as evidence.
            urgency: Urgency = "routine"
            why = (f"Invoice {inv.invoice_id} for {_amount(inv)} ({inv.tax_year} work) "
                   f"is drafted and has never been issued — nothing has gone to "
                   f"the client.")
        else:
            urgency = "urgent" if waiting >= urgent_after_days else "soon"
            why = (f"Invoice {inv.invoice_id} for {_amount(inv)} ({inv.tax_year} work) "
                   f"has sat as a draft {_plural(waiting, 'day', 'days')} since the "
                   f"work was done — it has never been issued.")

        out.append(ProposedAction(
            action_id=action_id("invoice_unissued", client_id, str(inv.invoice_id)),
            kind="invoice_unissued", client_id=client_id,
            title=f"Issue invoice {inv.invoice_id} — {_amount(inv)}",
            why=why, urgency=urgency,
            # No template: the click here is *issuing the bill*, which fixes the
            # numbers permanently. That is the owner's decision on the billing
            # screen, not an email this queue can pre-write for them. The id
            # still travels, so the screen opens THAT invoice rather than making
            # the owner hunt for the draft the row is about.
            invoice_id=str(inv.invoice_id),
            evidence=(str(inv.invoice_id),)))
    return out


# --- the queue ----------------------------------------------------------------


@dataclass(slots=True)
class ActionQueue:
    """Everything worth doing, ordered by how much it hurts to leave."""

    actions: list[ProposedAction] = field(default_factory=list)
    generated_for: date | None = None

    def __len__(self) -> int:
        return len(self.actions)

    def by_urgency(self) -> list[tuple[str, list[ProposedAction]]]:
        groups: dict[str, list[ProposedAction]] = {}
        for a in self.actions:
            groups.setdefault(a.urgency, []).append(a)
        return [(u, groups[u]) for u in ("overdue", "urgent", "soon", "routine")
                if u in groups]

    def for_client(self, client_id: str) -> list[ProposedAction]:
        return [a for a in self.actions if a.client_id == client_id]

    def one_click(self) -> list[ProposedAction]:
        """Actions with a draft already prepared — the ones that cost a click."""
        return [a for a in self.actions if a.has_draft]

    def counts(self) -> dict[str, int]:
        """Aggregated for a small-context reader (doctrine rule 2).

        A model asking "what needs doing?" gets six numbers, not 200 rows.
        """
        out: dict[str, int] = {}
        for a in self.actions:
            out[a.kind] = out.get(a.kind, 0) + 1
        return out

    def summary_line(self) -> str:
        if not self.actions:
            return "Nothing needs you right now."
        drafted = len(self.one_click())
        overdue = sum(1 for a in self.actions if a.urgency == "overdue")
        bits = [f"{len(self.actions)} things need you"]
        if overdue:
            bits.append(f"{overdue} overdue")
        if drafted:
            bits.append(f"{drafted} already drafted")
        return " · ".join(bits) + "."


def sort_key(action: ProposedAction) -> tuple:
    return (_URGENCY_ORDER.get(action.urgency, 9),
            action.due or date.max, action.client_id, action.kind)
