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
    "unbilled_work",          # delivered to the client, and never billed at all
    "invoice_overdue",        # issued, unpaid, past its due date
    "invoice_unissued",       # a draft bill that was never sent
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

_BILLABLE_STAGES = ("delivered", "complete")
"""The stages at which the work has left the building. Billing happens at
DELIVERY, not at filing — waiting for the ACK is how a bill gets forgotten."""


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


def _billable_jobs(jobs, *, client_id: str) -> list:
    return [j for j in jobs
            if j.client_id == client_id and j.stage in _BILLABLE_STAGES]


def _bills_raised(invoices, *, client_id: str, tax_year: int) -> list:
    """The bills that exist for this client-year — issued, or a draft with something on it."""
    return [inv for inv in invoices
            if inv.client_id == client_id and inv.tax_year == tax_year
            and (inv.is_issued or inv.lines)]


def unbilled_work(jobs, invoices=(), *, client_id: str,
                  tax_year: int) -> ProposedAction | None:
    """Work that reached the client with more of it delivered than billed.

    Not a late payment — money the practice never asked for. A return that was
    delivered and never invoiced is the one failure here that nothing else
    surfaces: the client is happy, the file looks finished, and the fee is gone.

    One row per client-year, never one per job. A client with three delivered
    jobs and no invoice has one problem, not three.

    THE STAND-DOWN COMPARES SIZE, NOT EXISTENCE. Invoicing here is piecemeal by
    design (see billing/invoice.py) — an engagement produces several bills as
    work happens, so ONE SMALL INVOICE IS THE NORMAL CASE, not the billed case.
    Treating any invoice as covering everything is how three completed jobs and
    one $450 bill for the 1040 leave the rental and the payroll fee unmentioned
    by anything, ever again.

    Nothing here claims to know WHICH job a line paid for — no such fact is
    recorded (principle 2). What it does know is a lower bound: N invoice lines
    cannot cover more than N jobs. It stands down only where coverage is
    possible, and speaks up where coverage is arithmetically impossible.
    """
    delivered = [j for j in _billable_jobs(jobs, client_id=client_id)
                 if _job_year(j) == tax_year]
    if not delivered:
        return None

    raised = _bills_raised(invoices, client_id=client_id, tax_year=tax_year)
    covered = sum(len(inv.lines) for inv in raised)
    short = len(delivered) - covered
    if short <= 0:
        # Every delivered job could be on one of these lines, and each bill has
        # its own row from the two proposers below. Two rows both saying "this
        # year is not paid for" is how a queue becomes noise (principle 13).
        return None

    closed = [j for j in delivered if j.stage == "complete"]
    labels = sorted({_job_label(j) for j in delivered})
    state = 'complete' if closed else 'delivered'
    if not raised:
        why = (f"{', '.join(labels)} for {tax_year} "
               f"{'is' if len(delivered) == 1 else 'are'} {state} and there is no "
               f"invoice at all — the work has gone to the client unbilled.")
    else:
        why = (f"{', '.join(labels)} for {tax_year} "
               f"{'is' if len(delivered) == 1 else 'are'} {state}. The "
               f"{_plural(len(raised), 'invoice', 'invoices')} for {tax_year} "
               f"{'carries' if len(raised) == 1 else 'carry'} "
               f"{_plural(covered, 'line', 'lines')}, which cannot cover "
               f"{_plural(len(delivered), 'job', 'jobs')} — at least "
               f"{_plural(short, 'job has', 'jobs have')} never been billed.")
    return ProposedAction(
        action_id=action_id("unbilled_work", client_id, str(tax_year)),
        kind="unbilled_work", client_id=client_id,
        title=(f"Bill the {tax_year} work" if not raised
               else f"Finish billing the {tax_year} work"),
        why=why,
        # A file closed without ever being billed is money already lost; a
        # delivery that just happened is simply the next thing to do.
        urgency="urgent" if closed else "soon",
        evidence=tuple(j.job_id for j in delivered))


def undated_work(jobs, *, client_id: str) -> ProposedAction | None:
    """Delivered work whose year the practice genuinely cannot read.

    A job with no ``tax_year`` and a ``period_key`` nobody here can parse used
    to fall out of every year's comparison and be surfaced by nothing. That is
    the silent drop principle 1 exists to forbid: no fact, so the slot is marked
    VISIBLY, not guessed and not discarded.

    Filed under its own id rather than folded into a year's row, because
    assigning it to a year is the one thing we have just said we cannot do.
    """
    undated = [j for j in _billable_jobs(jobs, client_id=client_id)
               if _job_year(j) is None]
    if not undated:
        return None
    periods = sorted({str(getattr(j, "period_key", "") or "").strip() or "(blank)"
                      for j in undated})
    return ProposedAction(
        action_id=action_id("unbilled_work", client_id, "undated"),
        kind="unbilled_work", client_id=client_id,
        title=f"{_plural(len(undated), 'delivered job has', 'delivered jobs have')} no readable year",
        why=(f"{', '.join(sorted({_job_label(j) for j in undated}))} "
             f"{'has' if len(undated) == 1 else 'have'} left the building carrying no "
             f"tax year and a period of {', '.join(periods[:4])} — SATC cannot say which "
             f"year to check them against, so nothing else will ever ask whether they "
             f"were billed. Check them by hand."),
        urgency="soon",
        evidence=tuple(j.job_id for j in undated))


def invoice_overdue(invoices, *, client_id: str, today: date,
                    chase_after_days: int = 14,
                    serious_after_days: int = 45) -> list[ProposedAction]:
    """Issued, unpaid, and past its due date — one row per invoice.

    Separate rows because separate invoices are separate facts: different
    numbers, different amounts, different dates, and the client will ask about
    one of them by number.

    The two thresholds are FIRM POLICY with nothing statutory behind them
    (principle 4). An invoice four days past due is usually sitting in somebody's
    inbox; treating that as a collection problem is how a client learns to
    ignore what you send.
    """
    out: list[ProposedAction] = []
    for inv in invoices:
        if inv.client_id != client_id or not inv.is_overdue(today):
            continue
        late = (today - inv.due_on).days
        if late >= serious_after_days:
            urgency: Urgency = "overdue"
        elif late >= chase_after_days:
            urgency = "urgent"
        else:
            urgency = "soon"
        out.append(ProposedAction(
            action_id=action_id("invoice_overdue", client_id, str(inv.invoice_id)),
            kind="invoice_overdue", client_id=client_id,
            title=f"Invoice {inv.invoice_id} unpaid — {_amount(inv)}",
            why=(f"Invoice {inv.invoice_id} for {_amount(inv)} ({inv.tax_year} work) "
                 f"was due {inv.due_on:%b %d} and is {_plural(late, 'day', 'days')} "
                 f"unpaid."),
            urgency=urgency, due=inv.due_on, template_key="invoice_cover",
            # The draft has to be about THIS invoice. Handing the comms screen
            # only the client and the year lets it pick the newest bill, and a
            # client then reads a covering note whose number and amount are not
            # the ones this row named.
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
