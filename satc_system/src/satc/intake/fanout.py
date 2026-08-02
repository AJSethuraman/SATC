"""THE FAN-OUT — everything that follows from one set of interview answers.

The interview is the ORIGIN FACT of an engagement. The owner answers it once,
and what we need, what it costs, when it is due, and what the letter says are
all DERIVED from those answers. A second place to record "this client has a
rental" is a second place for it to be wrong, so there is one function that
turns answers into a whole :class:`EngagementPlan` and nothing downstream
re-derives any of it.

Three things this fixes, each of which was genuinely broken:

1. **The deadline was keyed in, not computed.** ``build_engagement`` takes a
   ``due_date`` argument, so a date somebody typed into a form drove every task
   date on the engagement. Here the deadline comes off the obligations
   calendar — a CITED rule landed on a real period and shifted for IRC §7503 —
   and the citation travels with it (principle 3). A jurisdiction with no
   sourced rules REFUSES by name; it never falls back to the federal calendar,
   for the reason ``rules_for_jurisdiction`` already refuses to.

2. **``Job.obligation_key`` was never written by anything.** It is the link the
   work queue matches a job to its duty on, so the queue's two heaviest
   ordering factors could not fire on a single real job. It is set here, from
   the duty the deadline came from — same composite key
   ``obligation_key()`` builds, so a plan's duty merges cleanly into the
   client's materialised obligation set.

3. **The engagement letter was not fed.** ``configs/comms/`` has the template
   and nothing gave it the derived scope. :attr:`EngagementPlan.letter_facts`
   is a merge dictionary in the same shape ``comms.context.build_context``
   produces — and under the same rule: **a key the practice holds no fact for
   is OMITTED, never blanked**, so ``RenderedDraft.unfilled`` marks it. In
   particular a fee is stated only when the quote is complete AND somebody
   actually agreed a rate plan; a fallback plan or unpriced work leaves the
   slot visibly empty rather than quoting a number nobody agreed.

RE-RUNNING IS SAFE BY CONSTRUCTION (principle 8). Every id here derives from
what the thing IS — the job from ``{client, workflow, period}``, a document
request from ``{client, year, job, template}`` — so the same answers twice
produce the same plan, byte for byte, and open no second request. A CHANGED
answer preserves progress by ``template_id`` (``build_engagement`` already
does that) and reports what left scope in :attr:`EngagementPlan.out_of_scope`:
work somebody had already started is KEPT on the job and flagged, never
silently deleted, because a task nobody can see is a task nobody can cancel.

WHAT IT DOES NOT DO: it writes nothing. It is a proposal the caller persists
(see ``satc.intake.service.create_engagement_from_intake``). Propose, never
dispose.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from satc.config import ConfigError
from satc.models.evidence import RequestedItem
from satc.models.intake import WorkflowDef
from satc.models.readiness import blocking_class_for
from satc.models.work import Job, Task
from satc.obligations.due_dates import DueDates, compute, tax_year as tax_year_period
from satc.obligations.profile import ObligationInstance, obligation_key
from satc.obligations.rules import ObligationRule, rules_for_jurisdiction

# WHICH ENTITY'S RETURN A WORKFLOW PREPARES — THE FALLBACK, NOT THE AUTHORITY.
#
# The authority is the client's RECORDED entity type, which every caller that
# has the client record passes in. This table is what a caller holding only the
# interview falls back to, and it is deliberately small: a workflow choice is
# what the owner clicked, not a fact about the taxpayer.
#
# Keyed on entity type rather than on a form number on purpose. Every
# jurisdiction's income-tax filing rule is scoped by `entity_types` — federal
# form_1040 and Massachusetts ma_form_1 are both the INDIVIDUAL filing duty —
# so selecting on the entity type resolves the right duty in any jurisdiction
# SATC holds rules for, with no per-state table here to fall out of date.
#
# A workflow absent from this map, with no recorded entity type supplied,
# discharges no statutory filing duty as far as SATC can tell. That is a real
# answer, not a gap: monthly bookkeeping and a year-end cleanup are work the
# practice agreed to do, and no statute has an opinion about when they are due.
# :func:`duty_rule_for` refuses those by name rather than inventing a deadline.
ENTITY_TYPE_BY_WORKFLOW: dict[str, str] = {
    "personal_1040_core": "INDIVIDUAL",
    "personal_schedule_c": "INDIVIDUAL",
    "personal_rental_schedule_e": "INDIVIDUAL",
    "business_scorp_tax": "SCORP",
    "business_partnership_tax": "PARTNERSHIP",
}

_ID_CHARS = 16
_BULLET = "  • "


def _derived_id(prefix: str, *parts: Any) -> str:
    """A stable id derived from what the thing IS (principle 8).

    Not from when it ran. ``opaque_id`` mints a fresh uuid every call, which is
    exactly right for a record a human creates once and wrong for one a
    re-runnable derivation produces — re-running the interview would open a
    second job and a second copy of every document request.
    """
    blob = "|".join(str(p) for p in parts)
    return f"{prefix}-{hashlib.sha256(blob.encode('utf-8')).hexdigest()[:_ID_CHARS]}"


def _bullets(lines) -> str:
    """A bullet block, or ``""`` when there is nothing to list.

    Same shape ``comms.context`` produces, because these values are merged into
    the same templates and a letter should not have two bullet styles in it.
    """
    items = [str(line).strip() for line in lines if str(line).strip()]
    return "\n".join(_BULLET + item for item in items)


# ---------------------------------------------------------------------------
# The duty behind the engagement — where the deadline comes from
# ---------------------------------------------------------------------------

def duty_rule_for(workflow: WorkflowDef, jurisdiction: str = "US",
                  entity_type: str = "") -> ObligationRule:
    """The cited filing rule this workflow discharges, or a refusal naming it.

    ``entity_type`` is the client's RECORDED entity type, and it wins when the
    caller has it. The workflow map is a fallback for callers that hold only
    the interview — a recorded fact about the taxpayer beats a table keyed on
    which form the owner clicked (principle 2).

    Refuses in three distinguishable ways, because the next step differs:
    nothing says what is being filed, the jurisdiction has no sourced rules
    (that refusal comes from ``rules_for_jurisdiction`` and names the file to
    create), or the jurisdiction is sourced but holds nothing for this entity.
    """
    entity_type = (entity_type or "").strip().upper() or \
        ENTITY_TYPE_BY_WORKFLOW.get(workflow.key, "")
    if not entity_type:
        raise ConfigError(
            f"Nothing says what workflow {workflow.key!r} files, so SATC cannot compute a "
            f"deadline for it. If this is bookkeeping or a cleanup, the dates on it are "
            f"the practice's own and not the law's — create it with "
            f"satc.intake.service.create_engagement and the date the practice agreed. If "
            f"it does prepare a return, pass the client's recorded entity_type, or add "
            f"{workflow.key!r} to ENTITY_TYPE_BY_WORKFLOW.")

    # Raises, with the file to create, when the jurisdiction is unsourced.
    available = rules_for_jurisdiction(jurisdiction)

    # kind == "file" and a NON-EMPTY entity_types: a rule that applies to any
    # entity (payroll, 1099s, sales tax) depends on what the client DOES, which
    # is a profile fact, not something a workflow choice can tell us.
    matches = [r for r in available
               if r.kind == "file" and r.entity_types and entity_type in r.entity_types]
    if not matches:
        raise ConfigError(
            f"No {jurisdiction.upper()} filing rule on file for an {entity_type} return, so the "
            f"deadline for workflow {workflow.key!r} cannot be computed. Add the rule to "
            f"configs/obligations/{jurisdiction.lower()}.yaml with its citation.")
    if len(matches) > 1:
        raise ConfigError(
            f"{jurisdiction.upper()} has {len(matches)} filing rules for an {entity_type} return "
            f"({', '.join(r.key for r in matches)}). SATC will not pick one — say which "
            f"duty workflow {workflow.key!r} discharges rather than letting it guess.")
    return matches[0]


def duty_for(workflow: WorkflowDef, *, client_id: str, tax_year: int,
             jurisdiction: str = "US", fiscal_year_end: date | None = None,
             entity_type: str = "",
             ) -> tuple[ObligationInstance, ObligationRule, DueDates]:
    """Land this workflow's rule on the tax year: the duty, its rule, its dates.

    The returned :class:`ObligationInstance` carries the same
    ``obligation_key`` :func:`satc.obligations.profile.materialise` would
    produce, so a plan's duty and the client's materialised obligation set are
    the same row, not two rows that disagree.
    """
    rule = duty_rule_for(workflow, jurisdiction, entity_type)
    period = tax_year_period(tax_year, fiscal_year_end=fiscal_year_end)
    dues = compute(rule, period)
    duty = ObligationInstance(
        obligation_key=obligation_key(client_id, rule.kind, rule.form,
                                      rule.jurisdiction, dues.period_key),
        client_id=client_id, rule_key=rule.key, kind=rule.kind, form=rule.form,
        jurisdiction=rule.jurisdiction, period_key=dues.period_key,
        statutory_due=dues.statutory, due=dues.due, shift_reason=dues.shift_reason,
        extended_due=dues.extended_due, extension_form=dues.extension_form,
        extension_condition=rule.extension.condition,
        documents_due=dues.documents_due, blocking_docs=rule.blocking_docs)
    return duty, rule, dues


# ---------------------------------------------------------------------------
# What a changed answer takes away
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OutOfScope:
    """Work the previous answers called for and these answers do not.

    Reported rather than quietly dropped. "They said no to the rental this
    year" and "somebody already spent an afternoon on the rental schedule" are
    both true at once, and only one of them is visible from the answers.
    """

    template_id: str
    title: str
    status: str
    had_progress: bool
    """Somebody's work, or an ask already sitting with the client. Either way
    there is something to lose — see :func:`_why_keep`."""

    retained: bool
    """Kept on the job (flagged) rather than dropped. Always tracks
    :attr:`had_progress`: nothing with anything at stake is ever deleted here,
    because cancelling is the owner's call, not the interview's."""

    why: str


def _why_keep(task: Task) -> str:
    """Why this task must survive leaving scope — ``""`` when nothing is at stake.

    Two different things are worth keeping and they are not the same thing.
    Somebody's WORK: a status past ``not_started``, a note, a recorded
    completion. And an ASK ALREADY OUT: a client task carrying a
    ``request_id`` has a row sitting in the document register, and dropping the
    task strands that row where nobody can ever close it — principle 13's worst
    case, a queue entry that can never be cleared.

    A never-started internal task with neither is the state a task is born in.
    Nothing is lost by dropping it, and keeping it would be the noise.
    """
    if (task.status != "not_started" or (task.notes or "").strip()
            or task.completion is not None):
        return (f"it is marked {task.status.replace('_', ' ')} — kept so the work "
                f"already done is not lost")
    if task.request_id:
        return ("the client has already been asked for it — kept so that request "
                "can be closed rather than left outstanding forever")
    return ""


def _out_of_scope(existing: list[Task], kept_template_ids: set[str]) -> list[OutOfScope]:
    out: list[OutOfScope] = []
    for task in existing:
        if not task.template_id or task.template_id in kept_template_ids:
            continue
        keep = _why_keep(task)
        why = (f"{task.title!r} is no longer in scope for these answers, but {keep}. "
               f"Cancel it if it truly does not apply."
               if keep else
               f"{task.title!r} is no longer in scope for these answers and nobody "
               f"had started it, so it has been dropped.")
        out.append(OutOfScope(template_id=task.template_id, title=task.title,
                              status=task.status, had_progress=bool(keep),
                              retained=bool(keep), why=why))
    return out


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EngagementPlan:
    """Everything that follows from one set of interview answers.

    Nothing here is persisted. The caller writes it — or looks at it and
    decides not to.
    """

    job: Job
    """Tasks, risk flags, the computed ``due_date`` and the ``obligation_key``."""

    duty: ObligationInstance
    """The statutory duty the deadline came from."""

    citation: str
    """The authority behind that deadline, verbatim from the rule's ``source``."""

    requests: tuple[RequestedItem, ...] = ()
    """Document requests this plan OPENS. Asks already open on a preserved task
    are not re-minted — "already exists as requested" is success."""

    quote: Any | None = None
    """A ``satc.billing.quote.Quote``, or ``None`` when it could not be produced."""

    quote_unavailable: str = ""
    """Why there is no quote. Empty when there is one."""

    letter_facts: dict[str, str] = field(default_factory=dict)
    """Merge values for ``configs/comms/`` — keys OMITTED, never blanked."""

    out_of_scope: tuple[OutOfScope, ...] = ()

    @property
    def obligation_key(self) -> str:
        return self.job.obligation_key

    @property
    def due_date(self) -> date | None:
        return self.job.due_date

    @property
    def tasks(self) -> list[Task]:
        return self.job.tasks

    @property
    def documents_due(self) -> date | None:
        """The firm's own cutoff. NOT law — see ``configs/firm_policy.yaml``."""
        return self.duty.documents_due


# ---------------------------------------------------------------------------
# The fan-out itself
# ---------------------------------------------------------------------------

def fan_out(workflow: WorkflowDef, answers: dict[str, Any] | None = None, *,
            client_id: str, tax_year: int, today: date,
            engagements: Any = (), existing_tasks: Any = (),
            jurisdiction: str = "US", fiscal_year_end: date | None = None,
            entity_type: str = "",
            linked_clients: Any = (), relationships: Any = (),
            existing_jobs: Any = (), job_id: str = "",
            created_at: str = "", now: str | None = None) -> EngagementPlan:
    """Answers in; the whole engagement out.

    ``engagements`` are the billing :class:`~satc.models.work.Engagement`
    contracts (they decide the rate plan); ``existing_jobs`` are other jobs on
    file, which only the relationship-aware K-1 templates look at. Two
    different things that used to share a word.
    """
    from satc.intake.workflows import build_engagement

    duty, rule, _dues = duty_for(workflow, client_id=client_id, tax_year=tax_year,
                                 jurisdiction=jurisdiction, fiscal_year_end=fiscal_year_end,
                                 entity_type=entity_type)

    # Derived, so re-running finds the same job rather than minting a second.
    eng_id = job_id or _derived_id("engagement", client_id, workflow.key, duty.period_key)

    existing = [t for t in (existing_tasks or [])]
    job = build_engagement(
        workflow, client_id=client_id, due_date=duty.due, answers=answers,
        tax_year=tax_year, period_key=duty.period_key,
        linked_clients=list(linked_clients or []), relationships=list(relationships or []),
        existing_engagements=list(existing_jobs or []), existing_tasks=existing,
        job_id=eng_id, created_at=created_at, now=now)

    # (2) The link the work queue orders on. Nothing else has ever written it.
    job.obligation_key = duty.obligation_key

    # What a changed answer takes away — reported, and kept when somebody had
    # already done it. Appended to the job so it stays visible and cancellable.
    kept = {t.template_id for t in job.tasks if t.template_id}
    gone = _out_of_scope(existing, kept)
    by_template = {t.template_id: t for t in existing}
    for item in gone:
        if item.retained:
            job.tasks.append(by_template[item.template_id])

    requests = _open_requests(job, workflow, client_id=client_id, tax_year=tax_year,
                              today=today, rule=rule)

    quote, quote_unavailable = _quote(workflow, answers or {}, client_id=client_id,
                                      tax_year=tax_year, engagements=engagements)

    return EngagementPlan(
        job=job, duty=duty, citation=rule.source,
        requests=tuple(requests), quote=quote, quote_unavailable=quote_unavailable,
        letter_facts=_letter_facts(workflow, job, duty, quote, tax_year=tax_year),
        out_of_scope=tuple(gone))


def _open_requests(job: Job, workflow: WorkflowDef, *, client_id: str, tax_year: int,
                   today: date, rule: ObligationRule) -> list[RequestedItem]:
    """One ``RequestedItem`` per client-facing ask that does not already have one.

    A task preserved from a previous run carries the ``request_id`` of the ask
    already sitting in the register — possibly already satisfied. Re-minting it
    would ask a client twice for a document they have already sent, which is
    the queue-becomes-noise failure in its purest form.

    What BLOCKS comes from the duty's OWN cited rule, not from a literal here
    and not from the 1040 rule regardless of what is being filed.
    """
    template_doc_types = {t.template_id: t.doc_type for t in workflow.tasks}
    out: list[RequestedItem] = []
    for task in job.tasks:
        if task.audience != "client" or task.request_id:
            continue
        doc_type = template_doc_types.get(task.template_id, task.title)
        request_id = _derived_id("req", client_id, tax_year, job.job_id, task.template_id)
        out.append(RequestedItem(
            request_id=request_id, client_id=client_id, tax_year=tax_year,
            doc_type=doc_type, request_text=task.client_request_text or task.title,
            blocking=blocking_class_for(doc_type, rule.blocking_docs),
            requested_at=today, task_id=task.task_id))
        task.request_id = request_id
    return out


def _quote(workflow: WorkflowDef, answers: dict[str, Any], *, client_id: str,
           tax_year: int, engagements: Any) -> tuple[Any | None, str]:
    """The price the same answers imply — or a plain statement of why there isn't one.

    Imported here rather than at module scope so the fan-out still works while
    the pricing seam is being built, and so a broken billing config cannot stop
    an interview from producing its tasks and its deadline. A missing quote is
    NAMED, never silently zero.
    """
    try:
        from satc.billing.quote import quote_for
    except ImportError:
        return None, ("No quote: satc.billing.quote is not installed, so nothing can "
                      "price these answers. The engagement letter's fee slot stays "
                      "visibly unfilled until it is.")
    try:
        return quote_for(workflow, answers, client_id=client_id, tax_year=tax_year,
                         engagements=engagements), ""
    except ConfigError as exc:
        return None, f"No quote: {exc}"


def _price_is_agreed(quote: Any) -> bool:
    """Whether anyone has actually decided what this client pays.

    A FALLBACK rate plan is the practice default applying because nobody sat
    down and priced this client — :class:`RatePlanOnFile` exists precisely to
    tell that apart from an agreement to pay full rate. An engagement letter
    that states a fee derived from a fallback claims a term of a contract
    nobody negotiated, so the slot stays visibly unfilled instead.
    """
    return quote is not None and not getattr(quote, "plan_is_fallback", True)


def _total_is_whole(quote: Any) -> bool:
    """Whether ``quote.total`` is the WHOLE price, not just the priced part.

    Work in :attr:`Quote.unpriced` — an hourly service, or one whose count the
    interview does not record — is real work that is missing from the total. A
    bare dollar figure carrying that omission reads as the full fee and is not.
    """
    return quote is not None and not getattr(quote, "unpriced", ())


def _scope_lines(quote: Any) -> list[str]:
    """What is in scope, in the words a client reads.

    Taken from the quote because the priced lines ARE the scope — the same
    answers produced both, so a letter promising work the invoice does not
    charge for cannot happen. Work the catalogue cannot price is still in
    scope and still listed; it is marked as not yet priced rather than left out,
    because scope and price are different questions and only one of them is open.
    """
    lines: list[str] = []
    for line in getattr(quote, "lines", ()) or ():
        describe = getattr(line, "describe", None)
        label = (describe() if callable(describe)
                 else str(getattr(line, "label", ""))).strip()
        if label:
            lines.append(label)
    for item in getattr(quote, "unpriced", ()) or ():
        label = str(getattr(item, "label", "") or item).strip()
        if label:
            lines.append(f"{label} — fee to be agreed")
    return lines


def _letter_facts(workflow: WorkflowDef, job: Job, duty: ObligationInstance,
                  quote: Any, *, tax_year: int) -> dict[str, str]:
    """Merge values for the engagement letter — omitting anything we don't hold.

    Layered ON TOP of ``comms.context.build_context``, which supplies who the
    client is. This supplies what was agreed. Every key here is a fact derived
    from the answers; a fact we do not have is simply absent, so
    ``RenderedDraft.unfilled`` marks it ``[[ Fee: fill in ]]`` rather than the
    letter going out looking finished.
    """
    facts: dict[str, str] = {
        "tax_year": str(tax_year),
        "client_id": job.client_id,
        "engagement_name": workflow.name,
        # The COMPUTED statutory deadline, already shifted off weekends and
        # holidays. Never a date anyone typed.
        "due_date": duty.due.strftime("%B %d, %Y"),
    }

    asks = []
    for task in job.tasks:
        if task.audience != "client":
            continue
        text = (task.client_request_text or task.title).strip()
        if text and text not in asks:
            asks.append(text)
    if asks:
        facts["requested_items"] = _bullets(asks)

    scope = _scope_lines(quote)
    if scope:
        facts["scope_of_services"] = _bullets(scope)

    # Two different facts, and they are held to different standards.
    #
    # `fee_terms` is the paragraph the engagement letter prints: the quote's own
    # honest sentence, which already names what it does NOT include. It needs an
    # agreed rate plan behind it and nothing more.
    #
    # `fee_amount_text` is a bare number with no room for a caveat, so it is
    # stated only when the total is genuinely the whole price.
    #
    # Neither is guessed. Where the condition fails the key is simply absent and
    # the draft renders `[[ Fee: fill in ]]` — loudly unfinished beats quietly
    # wrong on a document a client signs.
    if _price_is_agreed(quote):
        facts["fee_terms"] = quote.client_sentence()
        if _total_is_whole(quote):
            facts["fee_amount_text"] = f"${Decimal(str(quote.total)):,.2f}"

    return facts
