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

from dataclasses import dataclass, field
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


# --- the individual proposers -------------------------------------------------
#
# Each takes plain records and returns zero or one action. Kept separate so a
# rule can be changed, tested, or switched off on its own.


def chase_outstanding(documents, *, client_id: str, tax_year: int,
                      today: date, stale_after_days: int = 3) -> ProposedAction | None:
    """Outstanding requests that have been sitting long enough to nudge.

    The 3-day default is FIRM POLICY with no citation behind it — a practitioner
    convention, not a rule. It is a parameter for exactly that reason.
    """
    outstanding = [d for d in documents
                   if d.client_id == client_id and str(d.status) == "Requested"
                   and getattr(d, "tax_year", None) == tax_year]
    if not outstanding:
        return None

    oldest = min((d.as_of for d in outstanding if getattr(d, "as_of", None)), default=None)
    waiting = (today - oldest).days if oldest else None
    if waiting is not None and waiting < stale_after_days:
        return None

    types = [d.doc_type for d in outstanding]
    since = f", the oldest asked {waiting} days ago" if waiting is not None else ""
    return ProposedAction(
        action_id=action_id("chase_documents", client_id, str(tax_year)),
        kind="chase_documents", client_id=client_id,
        title=f"Chase {_plural(len(outstanding), 'outstanding document', 'outstanding documents')}",
        why=f"{', '.join(types[:4])} still outstanding for {tax_year}{since}.",
        urgency="urgent" if (waiting or 0) >= 14 else "soon",
        template_key="missing_items", evidence=tuple(types))


def ask_prior_year_questions(documents, *, client_id: str, tax_year: int,
                             prior_year: int) -> ProposedAction | None:
    """Documents in hand last year with no trace this year.

    The highest-value proposal in the set, because nothing else in a tax review
    can find it: you cannot tie out a document that never arrived.
    """
    from satc.rollover import omission_diff

    report = omission_diff(documents, client_id=client_id,
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


def chase_signature(documents, *, client_id: str, tax_year: int,
                    today: date) -> ProposedAction | None:
    """An e-file authorization that is out and not back.

    Called out separately from ordinary document chasing because nothing can be
    transmitted without it — an unsigned 8879 blocks the filing, not just the file.
    """
    pending = [d for d in documents
               if d.client_id == client_id and getattr(d, "tax_year", None) == tax_year
               and str(d.status) == "Requested"
               and "8879" in str(d.doc_type)]
    if not pending:
        return None
    oldest = min((d.as_of for d in pending if getattr(d, "as_of", None)), default=None)
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


def extension_candidate(documents, obligations, *, client_id: str, tax_year: int,
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
    outstanding = [d for d in documents
                   if d.client_id == client_id and str(d.status) == "Requested"
                   and getattr(d, "tax_year", None) == tax_year]
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
        evidence=tuple(d.doc_type for d in outstanding))


def invite_to_interview(documents, *, client_id: str, tax_year: int,
                        has_engagement: bool) -> ProposedAction | None:
    """A client with nothing started for the year."""
    if has_engagement:
        return None
    this_year = [d for d in documents
                 if d.client_id == client_id and getattr(d, "tax_year", None) == tax_year]
    if this_year:
        return None
    return ProposedAction(
        action_id=action_id("interview_invite", client_id, str(tax_year)),
        kind="interview_invite", client_id=client_id,
        title=f"Nothing started for {tax_year}",
        why=f"No engagement and no {tax_year} documents on file.",
        urgency="routine", template_key="interview_invite")


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
