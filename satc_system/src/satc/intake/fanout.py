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

3. **The engagement letter had nothing to say.** ``configs/comms/`` has the
   template and nothing produced the derived scope.
   :attr:`EngagementPlan.letter_facts` is a merge dictionary in the same shape
   ``comms.context.build_context`` produces — and under the same rule: **a key
   the practice holds no fact for is OMITTED, never blanked**, so
   ``RenderedDraft.unfilled`` marks it. In particular a fee is stated only when
   the quote is complete AND somebody actually agreed a rate plan; a fallback
   plan or unpriced work leaves the slot visibly empty rather than quoting a
   number nobody agreed.

   Producing the facts is not the same as the letter being fed, and this
   module can only do the first. The comms path builds its merge values in
   ``satc.app.comms_views._context`` and has never been given these; the seam
   that closes it is ``satc.intake.service.letter_facts_for_job``, which that
   function must layer OVER ``build_context``. Until it does, the letter still
   renders its scope and fee from standing wording rather than from what this
   engagement actually agreed.

RE-RUNNING IS SAFE BY CONSTRUCTION (principle 8). Every id here derives from
what the thing IS — the job from ``{client, workflow, jurisdiction, period}``
(without the jurisdiction the state engagement IS the federal one), a document
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
NO_FILING_DUTY: frozenset[str] = frozenset({
    "business_monthly_bookkeeping",
    "business_year_end_cleanup",
    "new_client_onboarding",
})
"""Workflows that discharge no filing duty. Stated explicitly rather than
inferred from absence: a filing workflow somebody forgets to register would
otherwise become service work silently, and lose its deadline without a word."""


class NoFilingDuty(Exception):
    """This workflow discharges no filing duty, so it has no statutory deadline.

    Not an error — an answer. Bookkeeping and onboarding are real work with real
    dates, but those dates are the PRACTICE'S and not the law's, and rendering
    them with a citation is principle 4 inverted. Raised rather than returned so
    a caller cannot absent-mindedly treat "no duty" as "duty unknown".
    """


# Workflows that file something, and what they file. Being IN here is what makes
# a statutory deadline computable.
ENTITY_TYPE_BY_WORKFLOW: dict[str, str] = {
    "personal_1040_core": "INDIVIDUAL",
    "personal_schedule_c": "INDIVIDUAL",
    "personal_rental_schedule_e": "INDIVIDUAL",
    "business_scorp_tax": "SCORP",
    "business_partnership_tax": "PARTNERSHIP",
}

# WHICH BASES COUNT AS KNOWING (principle 2).
#
# The same vocabulary :class:`satc.obligations.profile.ProfileFact` uses, and
# the same split: four ways of having been TOLD, and ``assumed_default``, which
# is not one of them. Anything else — including the empty string a caller that
# holds no provenance at all passes — is unsourced.
#
# This matters here more than almost anywhere else in the system. Whether an
# entity is an S corporation is ASSIGNED BY THE IRS IN WRITING (a Form 2553
# acceptance, a CP261 notice); it is not derivable from a name, a spreadsheet
# column, or "most small businesses are". An entity type is not a detail of a
# duty — it decides WHICH DUTY EXISTS, so a guessed one does not produce a
# slightly-off deadline, it produces a whole filing obligation for a form the
# taxpayer may not owe at all, keyed and merged into their obligation set where
# nothing can ever clear it. That is why an unsourced entity type is REFUSED
# here rather than flagged ``is_assumed`` and let through (principles 2 and 5).
RECORDED_BASES: frozenset[str] = frozenset({
    "agency_notice", "stated_by_client", "prior_filing", "observed_document",
})

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
                  entity_type: str = "", *, entity_type_basis: str = "") -> ObligationRule:
    """The cited filing rule this workflow discharges, or a refusal naming it.

    ``entity_type`` is the client's RECORDED entity type, and it wins when the
    caller has it — but only when ``entity_type_basis`` says how the practice
    knows (one of :data:`RECORDED_BASES`). A value with no basis is a value
    somebody's importer may have invented, and it is treated as unsourced.

    The workflow map is the other authority, and it is a different KIND of
    thing: it says what the owner sat down to prepare. "Prepare this client's
    1120-S" is a human act; "most small businesses are S-corps" is a guess. So
    an unsourced entity type may not overrule the owner's choice, and may not
    stand in for it either.

    Refuses in five distinguishable ways, because the next step differs each
    time: nothing says what is being filed; an unsourced entity type is the
    only thing offering to; an unsourced entity type CONTRADICTS the workflow
    the owner chose; the jurisdiction has no sourced rules (that refusal comes
    from ``rules_for_jurisdiction`` and names the file to create); or the
    jurisdiction is sourced but holds nothing for this entity.
    """
    # ASKED FIRST, before anything looks at the entity type. Bookkeeping does not
    # become a filing because the client happens to be an S-corp, and refusing it
    # for want of a sourced entity type made two of the four workflows the app
    # offers a business client unreachable — a worse failure than the one the
    # entity guard was added to prevent.
    if workflow.key in NO_FILING_DUTY:
        raise NoFilingDuty(
            f"{workflow.name} discharges no filing duty, so there is no statutory "
            f"deadline to compute. Its dates are the practice's own.")

    stated = (entity_type or "").strip().upper()
    from_workflow = ENTITY_TYPE_BY_WORKFLOW.get(workflow.key, "")

    if not from_workflow:
        # In NEITHER list. Deliberately a refusal rather than a shrug: treating
        # an unrecognised workflow as service work is how a filing workflow
        # someone forgot to register silently loses its deadline.
        raise ConfigError(
            f"SATC does not know whether workflow {workflow.key!r} files anything. "
            f"Add it to ENTITY_TYPE_BY_WORKFLOW with the return it prepares, or to "
            f"NO_FILING_DUTY if it is service work whose dates the practice sets. "
            f"Guessing either way puts a wrong date in front of a client.")

    if stated and entity_type_basis not in RECORDED_BASES:
        # An unsourced entity type cannot buy a citation. It can only agree with
        # something that already has standing — the return the owner chose to
        # prepare — in which case it is redundant and the choice is the
        # authority. Anything else is a guess about to become a deadline.
        record_it = (f"Record the entity type from the IRS acceptance letter (Form 2553 "
                     f"acceptance / CP261) or the last filed return, with its basis — one "
                     f"of {', '.join(sorted(RECORDED_BASES))}")
        if not from_workflow:
            raise ConfigError(
                f"SATC holds {stated!r} as this client's entity type but no record of how "
                f"it knows, and workflow {workflow.key!r} does not say what it files "
                f"either. Whether an entity is an S corporation is assigned by the IRS in "
                f"writing, so SATC will not turn an unsourced entity type into a cited "
                f"statutory deadline. {record_it}.")
        if stated != from_workflow:
            raise ConfigError(
                f"The client record says {stated!r} with no record of how it knows, and "
                f"workflow {workflow.key!r} prepares a {from_workflow} return. SATC will "
                f"not pick between an unsourced entity type and the return you chose to "
                f"prepare — one of them is wrong, and whether an entity is an S corporation "
                f"is assigned by the IRS in writing rather than settled by whichever was "
                f"typed last. {record_it}, or choose the workflow that matches it.")

    entity_type = stated if entity_type_basis in RECORDED_BASES and stated else from_workflow
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
             entity_type: str = "", entity_type_basis: str = "",
             ) -> tuple[ObligationInstance, ObligationRule, DueDates] | None:
    """Land this workflow's rule on the tax year: the duty, its rule, its dates.

    Returns ``None`` for work that files nothing — bookkeeping, onboarding —
    because "no statutory deadline" is a true answer about that engagement, not
    a failure to compute one. Callers must render it as an absence rather than
    reaching for the firm's own cutoff and dressing it in a citation.

    The returned :class:`ObligationInstance` carries the same
    ``obligation_key`` :func:`satc.obligations.profile.materialise` would
    produce, so a plan's duty and the client's materialised obligation set are
    the same row, not two rows that disagree.
    """
    try:
        rule = duty_rule_for(workflow, jurisdiction, entity_type,
                             entity_type_basis=entity_type_basis)
    except NoFilingDuty:
        return None
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
    """Work the previous answers called for that still needs a decision.

    Reported rather than quietly dropped. "They said no to the rental this
    year" and "somebody already spent an afternoon on the rental schedule" are
    both true at once, and only one of them is visible from the answers.

    NOT a list of everything that left scope. A row here is a row asking the
    owner for something — finish it, cancel it, or close the request behind it
    — and doing that thing makes the row go away next run. Work that left scope
    with nothing outstanding stays on the job and is not reported, because a row
    the owner can never clear is the one that teaches them to scroll past
    (principle 13).
    """

    template_id: str
    title: str
    status: str
    had_progress: bool
    """Somebody's work in flight, or an ask still sitting with the client.
    Either way there is something to lose — see :func:`_needs_a_decision`."""

    retained: bool
    """Kept on the job (flagged) rather than dropped. Always tracks
    :attr:`had_progress` on a reported row: nothing with anything at stake is
    ever deleted here, because cancelling is the owner's call, not the
    interview's."""

    why: str


def _keep_on_job(task: Task) -> bool:
    """Whether this task survives leaving scope — history is never deleted here.

    Anything but the state a task is born in: a status past ``not_started``, a
    note, a recorded completion, or an ask that was actually sent. A pristine
    never-started task loses nothing by being dropped, and keeping it would be
    the noise.

    Deliberately SEPARATE from whether the owner is told about it. Kept and
    reported used to be the same test, which is how a finished task became a
    permanent row — see :func:`_needs_a_decision`.
    """
    return bool(task.status != "not_started" or (task.notes or "").strip()
                or task.completion is not None or task.request_id)


def _ask_is_outstanding(task: Task, open_request_ids: set[str] | None) -> bool:
    """Whether this task's ask is still sitting open in the document register.

    ``open_request_ids`` is the register itself, from a caller that holds it
    (:func:`satc.intake.service.create_engagement_from_intake` does). Having
    EVER had a ``request_id`` is not the question — a satisfied request is
    closed, and a task reported forever because it once carried one is the row
    principle 13 is about.

    With no register in hand the best evidence available is the task: SATC's own
    ``reconcile_received`` completes the task when the request is satisfied, so
    a settled task is a settled ask. That is a reading of a recorded fact, not
    a guess about one.
    """
    if not task.request_id:
        return False
    if open_request_ids is None:
        return task.is_open
    return task.request_id in open_request_ids


def _needs_a_decision(task: Task, open_request_ids: set[str] | None) -> str:
    """What this out-of-scope task still needs from the owner — ``""`` if nothing.

    Two things can still be outstanding, and they are not the same thing.
    Somebody's WORK IN FLIGHT: an open task with progress on it, which somebody
    must either finish or cancel. And an ASK STILL OUT: a live row in the
    document register, which must be closed or the client will be chased for a
    document nobody wants any more.

    A task the owner has already dealt with — done, waived, cancelled — with
    nothing outstanding behind it needs no decision, so it gets no row. That is
    what makes the row CLEARABLE: doing the thing the row asks for makes it go
    away next run. It stays on the job either way (:func:`_keep_on_job`); what
    it stops doing is asking for attention it no longer needs.
    """
    if task.is_open and (task.status != "not_started" or (task.notes or "").strip()
                         or task.completion is not None):
        return (f"it is marked {task.status.replace('_', ' ')} — kept so the work "
                f"already done is not lost")
    if _ask_is_outstanding(task, open_request_ids):
        return ("the client has already been asked for it — kept so that request "
                "can be closed rather than left outstanding forever")
    return ""


def _out_of_scope(existing: list[Task], kept_template_ids: set[str],
                  open_request_ids: set[str] | None = None,
                  ) -> tuple[list[OutOfScope], list[Task]]:
    """What these answers took away: the rows to show, and the tasks to keep.

    Two returns because they answer different questions. Every task with any
    history is KEPT; only the ones with something still outstanding are
    REPORTED.
    """
    out: list[OutOfScope] = []
    keep: list[Task] = []
    for task in existing:
        if not task.template_id or task.template_id in kept_template_ids:
            continue
        kept = _keep_on_job(task)
        if kept:
            keep.append(task)
        decision = _needs_a_decision(task, open_request_ids)
        if decision:
            why = (f"{task.title!r} is no longer in scope for these answers, but "
                   f"{decision}. Cancel it if it truly does not apply.")
        elif kept:
            continue          # settled: kept on the job, nothing left to decide
        else:
            why = (f"{task.title!r} is no longer in scope for these answers and nobody "
                   f"had started it, so it has been dropped.")
        out.append(OutOfScope(template_id=task.template_id, title=task.title,
                              status=task.status, had_progress=bool(decision),
                              retained=bool(decision), why=why))
    return out, keep


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
        return self.duty.documents_due if self.duty is not None else None

    @property
    def files_something(self) -> bool:
        """Whether a statute has any opinion about when this is due.

        False for bookkeeping and onboarding. The screen must key its STATUTE
        badge on this rather than on the presence of a date — the job still has
        dates, they are just the practice's own (principle 4).
        """
        return self.duty is not None


# ---------------------------------------------------------------------------
# The fan-out itself
# ---------------------------------------------------------------------------

def fan_out(workflow: WorkflowDef, answers: dict[str, Any] | None = None, *,
            client_id: str, tax_year: int, today: date,
            engagements: Any = (), existing_tasks: Any = (),
            jurisdiction: str = "US", fiscal_year_end: date | None = None,
            entity_type: str = "", entity_type_basis: str = "",
            linked_clients: Any = (), relationships: Any = (),
            existing_jobs: Any = (), job_id: str = "",
            open_request_ids: Any = None,
            created_at: str = "", now: str | None = None) -> EngagementPlan:
    """Answers in; the whole engagement out.

    ``engagements`` are the billing :class:`~satc.models.work.Engagement`
    contracts (they decide the rate plan); ``existing_jobs`` are other jobs on
    file, which only the relationship-aware K-1 templates look at. Two
    different things that used to share a word.

    ``open_request_ids`` is the document register, from a caller that holds it:
    which asks are still outstanding, so a request that has already been
    satisfied stops being reported as a reason to keep a task (principle 13).
    ``None`` means the caller does not hold it, not that nothing is open.
    """
    from satc.intake.workflows import build_engagement

    landed = duty_for(workflow, client_id=client_id, tax_year=tax_year,
                      jurisdiction=jurisdiction, fiscal_year_end=fiscal_year_end,
                      entity_type=entity_type, entity_type_basis=entity_type_basis)

    if landed is None:
        # SERVICE WORK — bookkeeping, onboarding. It files nothing, so there is
        # no statutory deadline and no obligation_key, and both absences are the
        # truth rather than a gap. The tasks still need an anchor for their
        # day-offsets: the period end, which is a PRACTICE choice and is carried
        # as one. Nothing here may render with a citation (principle 4).
        duty, rule = None, None
        anchor = date(int(tax_year), 12, 31)
    else:
        duty, rule, _dues = landed
        anchor = duty.due

    # Derived, so re-running finds the same job rather than minting a second.
    #
    # JURISDICTION IS PART OF WHAT THIS JOB IS. Without it the federal and the
    # Massachusetts engagement for one client, one workflow and one year derive
    # the SAME id, and the second silently overwrites the first — two duties,
    # two deadlines, two sets of tasks, one row. The same composite the duty
    # itself is keyed on (principle 8).
    period_key = duty.period_key if duty is not None else f"{tax_year}"
    eng_id = job_id or _derived_id("engagement", client_id, workflow.key,
                                   (duty.jurisdiction if duty is not None
                                    else jurisdiction), period_key)

    existing = [t for t in (existing_tasks or [])]
    job = build_engagement(
        workflow, client_id=client_id, due_date=anchor, answers=answers,
        tax_year=tax_year, period_key=period_key,
        linked_clients=list(linked_clients or []), relationships=list(relationships or []),
        existing_engagements=list(existing_jobs or []), existing_tasks=existing,
        job_id=eng_id, created_at=created_at, now=now)

    # (2) The link the work queue orders on. Nothing else has ever written it.
    # Left EMPTY for service work: there is no duty, so a key pointing at one
    # would be a fabricated row in the client's obligation set.
    job.obligation_key = duty.obligation_key if duty is not None else ""

    # What a changed answer takes away — reported while anything is outstanding,
    # and kept whenever there is history, so nobody's work is deleted by an
    # answer changing.
    kept = {t.template_id for t in job.tasks if t.template_id}
    ids = None if open_request_ids is None else {str(r) for r in open_request_ids}
    gone, retained = _out_of_scope(existing, kept, ids)

    # ASKED BEFORE THE RETAINED WORK GOES BACK ON THE JOB, and that order is
    # load-bearing. A retained task is work these answers say we are NOT doing;
    # opening a fresh document request against it would ask the client for a
    # document the same call reports as out of scope.
    requests = _open_requests(job, workflow, client_id=client_id, tax_year=tax_year,
                              today=today, rule=rule)

    out_of_scope_templates = {t.template_id for t in retained}
    job.tasks.extend(retained)

    quote, quote_unavailable = _quote(workflow, answers or {}, client_id=client_id,
                                      tax_year=tax_year, engagements=engagements)

    return EngagementPlan(
        job=job, duty=duty, citation=(rule.source if rule is not None else ""),
        requests=tuple(requests), quote=quote, quote_unavailable=quote_unavailable,
        letter_facts=_letter_facts(workflow, job, duty, quote, tax_year=tax_year,
                                   out_of_scope_templates=out_of_scope_templates),
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
            blocking=blocking_class_for(
                doc_type,
                # No filing duty means no cited list of what blocks prep. The
                # three-way split is a RULE, so with no rule every ask is
                # non_blocking — stated, not guessed at from the doc type.
                rule.blocking_docs if rule is not None else ()),
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
                  quote: Any, *, tax_year: int,
                  out_of_scope_templates: set[str] | None = None) -> dict[str, str]:
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
    }

    # OMITTED, never blanked, when this work files nothing: RenderedDraft.unfilled
    # then marks it visibly rather than a letter promising a deadline that no
    # statute sets (principles 1 and 4).
    if duty is not None:
        # The COMPUTED statutory deadline, already shifted off weekends and
        # holidays. Never a date anyone typed.
        facts["due_date"] = duty.due.strftime("%B %d, %Y")

    # ONE CALL MUST NOT SAY TWO THINGS. ``job.tasks`` carries the retained
    # out-of-scope work as well as the scope, because a task somebody started is
    # never deleted by an answer changing — but a letter that asks the client
    # for a document the same plan reports as out of scope contradicts itself in
    # front of the client, and the client is the one who cannot see the plan.
    gone = out_of_scope_templates or set()
    asks = []
    for task in job.tasks:
        if task.audience != "client" or task.template_id in gone:
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
    # stated only when the total is genuinely the whole price — and it CARRIES
    # ITS MARKER. That name is filled from an ISSUED INVOICE TOTAL by
    # `comms.context.build_context`; a quote landing in the same slot is an
    # estimate standing where a bill stood, and a client holds a practice to a
    # number in a letter. The marker travels with the value because whoever
    # merges these dictionaries cannot be relied on to remember which key came
    # from where.
    #
    # Neither is guessed. Where the condition fails the key is simply absent and
    # the draft renders `[[ Fee: fill in ]]` — loudly unfinished beats quietly
    # wrong on a document a client signs.
    if _price_is_agreed(quote):
        facts["fee_terms"] = quote.client_sentence()
        if _total_is_whole(quote):
            facts["fee_amount_text"] = (
                f"${Decimal(str(quote.total)):,.2f} (estimate — not a bill)")

    # THE ENGAGEMENT'S OWN FIGURE, WHICH IS NOW THE ONLY ONE THERE IS.
    #
    # This catalogue stopped pricing returns on 5 September 2026 -- the package
    # ladder is the price, and `client-documents` owns the engagement. So
    # `_total_is_whole` is never true any more, and without this every letter
    # would render `[[ Fee: fill in ]]`: technically honest, useless in
    # practice, and a good way to have somebody type a number in by hand.
    #
    # Read back through the engagement ref, which is the same seam `collect`
    # resolves a drop folder on. It OVERWRITES anything set above, because a
    # figure the client is already holding outranks one derived here -- that
    # precedence is the whole point of settling which file is the price.
    #
    # Silence when the ref is not recorded or the record cannot be read: the
    # letter falls back to `[[ Fee: fill in ]]`, which is what "we do not know
    # yet" should look like on a document somebody signs.
    engagement_price = getattr(quote, "engagement_price", None)
    if engagement_price is not None and getattr(engagement_price, "is_priced", False):
        facts["fee_amount_text"] = (
            f"{engagement_price.total} (estimate — not a bill)")
        facts["fee_source"] = f"engagement {engagement_price.ref}"

    return facts
