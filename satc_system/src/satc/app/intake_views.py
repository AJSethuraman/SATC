"""Client-intake & engagement screens (Flask blueprint).

Registered by :func:`satc.app.server.create_app`. Routes here drive the
new-client / interview flow and the engagement (requested-vs-received) view,
backed by :data:`satc.app.state.STATE`.

Screens (built out by the UI workstream):
  GET  /clients/new                  - choose person/business, create a client
  POST /clients/new                  - create the client, jump into intake
  GET  /intake/new                   - pick a client + workflow, answer the interview
  POST /intake/new                   - generate the engagement (opens Requested docs)
  GET  /intake/plan                  - the whole engagement the answers imply (reads only)
  GET  /engagements                  - list generated engagements
  GET  /engagements/<id>             - tasks grouped by category, risk flags, requests
  POST /engagements/<id>/tasks/<tid> - toggle a task complete
  GET  /engagements/<id>/email       - plain-text client request email
  GET  /engagements/<id>/print       - printable client request list
  GET  /engagements/<id>/print-internal - printable internal checklist
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from datetime import date

from flask import (
    Blueprint,
    Response,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from satc.app.state import STATE
from satc.config import ConfigError
from satc.intake.workflows import NEW_CLIENT_GATE

bp = Blueprint("intake", __name__)

# Filing statuses offered when capturing/confirming a client's situation.
FILING_STATUSES = [
    "Single",
    "Married filing jointly",
    "Married filing separately",
    "Head of household",
    "Qualifying surviving spouse",
]


def _public_client(client_id: str):
    """Look up a PublicClient by id (the de-identified projection)."""
    return next((c for c in STATE.mart.public_clients if c.client_id == client_id), None)


def _client_type(public_client) -> str:
    """Map an entity_type onto the workflow catalog's person/business split."""
    if public_client is None:
        return "person"
    return "business" if public_client.entity_type != "INDIVIDUAL" else "person"


@bp.route("/engagements")
def engagements():
    jobs = STATE.jobs()
    return render_template(
        "engagements.html", title="Engagements", engagements=jobs,
        # Counted HERE, not in the template. selectattr over a STATUS string
        # counts every task as done, because any non-empty string is truthy —
        # a 200 with a wrong number, which is worse than a crash.
        progress={j.job_id: j.progress() for j in jobs})


@bp.route("/clients/new", methods=["GET", "POST"])
def new_client():
    if request.method == "POST":
        kind = request.form.get("kind", "person")
        if kind == "business":
            cid = STATE.create_business_client(
                legal_name=request.form.get("legal_name", "").strip(),
                entity_type=request.form.get("entity_type", "SCORP"),
                ein=request.form.get("ein", "").strip(),
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
            )
        else:
            cid = STATE.create_person_client(
                first_name=request.form.get("first_name", "").strip(),
                last_name=request.form.get("last_name", "").strip(),
                ssn=request.form.get("ssn", "").strip(),
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
            )
        return redirect(url_for("intake.client_start", client_id=cid))
    return render_template("client_new.html", title="New client")


@bp.route("/clients/import", methods=["GET", "POST"], endpoint="import_clients")
def import_clients():
    """Bulk import (CSV / spreadsheet / Drake export) with a preview step."""
    from satc.intake.importer import CSV_TEMPLATE

    if request.method == "POST":
        text = ""
        upload = request.files.get("file")
        if upload is not None and upload.filename:
            text = upload.read().decode("utf-8", errors="ignore")
        if not text.strip():
            text = request.form.get("pasted", "")

        parsed = STATE.preview_client_import(csv_text=text)
        parsed_json = json.dumps([dataclasses.asdict(p) for p in parsed])
        new_count = sum(1 for p in parsed if p.status == "new")
        dup_count = sum(1 for p in parsed if p.status == "duplicate")
        review_count = sum(1 for p in parsed if p.status == "review")
        create_count = sum(1 for p in parsed if p.status != "duplicate")
        return render_template(
            "client_import_preview.html", title="Import clients",
            parsed=parsed, parsed_json=parsed_json,
            new_count=new_count, dup_count=dup_count, review_count=review_count,
            create_count=create_count)

    return render_template("client_import.html", title="Import clients",
                           csv_template=CSV_TEMPLATE)


@bp.route("/clients/import/confirm", methods=["POST"], endpoint="import_clients_confirm")
def import_clients_confirm():
    """Commit the previewed rows carried over as hidden JSON."""
    from satc.intake.importer import ParsedClient

    raw = request.form.get("parsed_json", "[]")
    try:
        rows = json.loads(raw)
    except (ValueError, TypeError):
        rows = []
    parsed = [ParsedClient(**d) for d in rows]
    include_duplicates = bool(request.form.get("include_duplicates"))
    STATE.commit_client_import(parsed, include_duplicates=include_duplicates)
    return redirect(url_for("intake.engagements"))


@bp.route("/clients/quick-add", methods=["POST"], endpoint="quick_add_client")
def quick_add_client():
    """Smart single-add, then flow straight into the interview."""
    client_id, _parsed = STATE.add_client_smart(
        name=request.form.get("name", ""),
        tin=request.form.get("tin", ""),
        entity_type=request.form.get("entity_type", ""),
        email=request.form.get("email", ""),
        phone=request.form.get("phone", ""),
        state=request.form.get("state", ""),
    )
    return redirect(url_for("intake.client_start", client_id=client_id))


def _int_or_none(raw: str):
    raw = (raw or "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _prior_summary(client_id: str) -> dict:
    """A compact "what we already know" summary for a returning client."""
    returns = sorted((r for r in STATE.returns() if r.client_id == client_id),
                     key=lambda r: r.tax_year, reverse=True)
    prior = STATE.prior_engagement(client_id)
    requested: list[str] = []
    if prior is not None:
        for t in prior.tasks:
            if t.audience == "client" and t.category not in requested:
                requested.append(t.category)
    return {
        "returns": [(r.tax_year, r.return_type, STATE.return_status(r.return_key))
                    for r in returns[:4]],
        "prior_year": prior.tax_year if prior else None,
        "requested_categories": requested,
    }


@bp.route("/clients/<client_id>/start", endpoint="client_start")
def client_start(client_id: str):
    """After a client exists, choose HOW to take them in — separate from creating them.

    Three intake modes: scan their documents, interview them manually, or email
    them an organizer to fill out themselves.
    """
    public_client = _public_client(client_id)
    if public_client is None:
        return redirect(url_for("intake.engagements"))
    return render_template(
        "client_start.html", title="New client", client_id=client_id,
        public_client=public_client, client_type=_client_type(public_client),
        returning=STATE.is_returning(client_id), filing_status=STATE.filing_status(client_id))


@bp.route("/intake/new", methods=["GET", "POST"])
def new_engagement():
    if request.method == "POST":
        client_id = request.form.get("client", "")
        workflow_key = request.form.get("workflow_key", "")
        # NOTE: due_date is deliberately NOT read off the form any more. The
        # deadline is computed from a cited rule (principle 3); a date typed
        # into a box drove the whole engagement, including its place in the
        # work queue.
        mode = request.form.get("mode", "")
        tax_year = _int_or_none(request.form.get("tax_year", ""))

        from satc.intake.workflows import load_workflow

        workflow = load_workflow(workflow_key)
        answers = {}
        for q in workflow.questions:
            if q.id == NEW_CLIENT_GATE:
                continue                       # set from the new/returning gate below
            val = request.form.get(f"q_{q.id}")
            if val is not None:
                answers[q.id] = val
        # Whether this is a new client is a RECORDED FACT — the practice either
        # has a prior engagement on file or it does not. Defaulting an absent
        # form field to "new" invented that answer for returning clients, and it
        # is the gate the whole interview branches on: it generated a different
        # engagement from the plan the owner had just read.
        if mode in ("new", "returning"):
            answers[NEW_CLIENT_GATE] = "yes" if mode == "new" else "no"
        else:
            answers[NEW_CLIENT_GATE] = "no" if STATE.is_returning(client_id) else "yes"

        filing_status = request.form.get("filing_status", "").strip()
        if filing_status:
            STATE.set_filing_status(client_id, filing_status)

        try:
            plan = STATE.create_engagement_from_intake(
                client_id=client_id, workflow_key=workflow_key,
                answers=answers, tax_year=tax_year)
        except (ConfigError, ValueError) as refused:
            # A jurisdiction with no sourced rules refuses rather than borrowing
            # the federal calendar. That refusal is the product; a 500 is not.
            # Re-rendered rather than redirected, so the answers survive it.
            return render_template(
                "intake_new.html", title="Intake", refusal=str(refused),
                client_id=client_id, public_client=_public_client(client_id),
                client_type=_client_type(_public_client(client_id)),
                workflows=STATE.workflow_catalog().get(
                    _client_type(_public_client(client_id)), []),
                workflow=workflow, mode=mode, returning=(mode == "returning"),
                prefill=answers, prior=STATE.prior_engagement(client_id, workflow_key),
                prior_summary={}, filing_statuses=FILING_STATUSES,
                filing_status=STATE.filing_status(client_id),
                gate_question=NEW_CLIENT_GATE)
        job = getattr(plan, "job", plan)
        return redirect(url_for("intake.engagement_detail", job_id=job.job_id))

    client_id = request.args.get("client", "")
    public_client = _public_client(client_id)
    client_type = _client_type(public_client)
    workflows = STATE.workflow_catalog().get(client_type, [])

    workflow_key = request.args.get("workflow", "")
    workflow = None
    mode = request.args.get("mode", "")
    prefill: dict[str, str] = {}
    prior = None
    if workflow_key:
        from satc.intake.workflows import load_workflow
        workflow = load_workflow(workflow_key)
        if not mode:                           # auto-detect, preparer can flip it
            mode = "returning" if STATE.is_returning(client_id) else "new"
        prior = STATE.prior_engagement(client_id, workflow_key)
        if mode == "returning" and prior is not None:
            prefill = dict(prior.intake_answers or {})

    returning = mode == "returning"
    return render_template(
        "intake_new.html", title="Intake",
        client_id=client_id, public_client=public_client, client_type=client_type,
        workflows=workflows, workflow=workflow, mode=mode, returning=returning,
        prefill=prefill, prior=prior,
        prior_summary=_prior_summary(client_id) if returning else {},
        filing_statuses=FILING_STATUSES, filing_status=STATE.filing_status(client_id),
        gate_question=NEW_CLIENT_GATE)


# ---------------------------------------------------------------------------
# THE ENGAGEMENT PLAN — everything that falls out of the interview, on one page
# ---------------------------------------------------------------------------
#
# The interview is the ORIGIN FACT of an engagement. What we will need from the
# client, what it will cost, when it is due and what we promised are all
# DERIVED from those answers rather than maintained beside them — a second
# place to record "this client has a rental" is a second place for it to be
# wrong. So this screen holds no facts of its own and derives nothing twice:
# one call to :func:`satc.intake.fanout.fan_out` produces the whole plan, and
# every panel below renders part of the same object.
#
# NOTHING HERE COMMITS. ``fan_out`` writes nothing; generating the engagement
# stays the click the owner makes, and drafting the letter stays a draft
# (principle 9). ``test_intake_app.py`` walks the AST of these functions to
# prove it.
#
# FOUR KINDS OF STATEMENT SHARE THIS PAGE AND MUST NOT READ ALIKE. Principle 4
# is a UI obligation here, not only a loading one:
#
#   statute      computed from a CITED rule; cannot be argued with.
#   firm_policy  the owner's own cutoff; no citation, changed over coffee.
#   promise      an SLA. Neither law nor a cutoff — breaking one costs an
#                apology, and the module that loads it REFUSES a citation.
#   estimate     a quote. Not a bill. Nobody has been charged anything.
#
# Each is marked in the MARKUP (``data-kind``) as well as in prose, because a
# template edit that rewrites the sentences must not be able to quietly make a
# promise look like a statute.


@dataclass(frozen=True, slots=True)
class Need:
    """One document the answers imply we will have to ask the client for."""

    doc_type: str
    title: str
    ask: str
    why: str
    alternatives: str
    blocking: str          # blocking | expected_late | non_blocking
    because: str
    """WHICH ANSWER put this on the list, in the owner's words.

    The point of the whole screen. A request whose cause cannot be named is a
    request nobody can defend to the client who asks why we want it."""

    by: date | None = None


# --- the seams other modules own ---------------------------------------------
#
# Each is a single call kept in its own function, so the screen's dependency on
# it is one patchable, testable point — and so a build without the engine
# produces a sentence rather than a stack trace (principle 10).

def _fan_out(workflow, answers: dict, *, client_id: str, tax_year: int, today: date,
             entity_type: str = ""):
    """Answers in, the whole engagement out. Writes nothing.

    ``entity_type`` is what :func:`_entity_type_for` decided is RELEVANT — not
    the client's recorded type handed over unconditionally. A workflow that files
    nothing gets nothing, so the engine's refusal survives contact with the
    screen.

    Deliberately NOT given the existing job's tasks. This screen shows what the
    answers imply IN FULL — an engagement already generated would otherwise come
    back with an empty request list, because ``fan_out`` correctly does not
    re-mint an ask already sitting in the register. What has actually arrived is
    the Engagement screen's question, not this one's.
    """
    from satc.intake.fanout import fan_out

    return fan_out(workflow, answers, client_id=client_id, tax_year=tax_year,
                   today=today, entity_type=entity_type,
                   engagements=list(STATE.mart.engagements))


def _entity_type_for(workflow, public_client) -> str:
    """The client's recorded entity type — WHEN this engagement files a return at all.

    A WORKFLOW ABSENT FROM ``ENTITY_TYPE_BY_WORKFLOW`` PREPARES NO RETURN,
    WHOEVER THE CLIENT IS. Monthly bookkeeping and a year-end cleanup are work
    the practice agreed to do and no statute has an opinion about when they are
    due, so ``duty_rule_for`` refuses them by name — and the screen used to
    defeat that refusal by handing over the client's entity type anyway. That
    answers a question nobody asked ("what would this taxpayer file *if* they
    were filing") and put a STATUTE badge, a computed March 16 and a citation to
    IRC §6072(b) on a bookkeeping engagement.

    The engine cannot make this call: from inside, a supplied entity type is a
    caller that has the client record, which is exactly what this screen is.
    Whether it is RELEVANT to the engagement being planned is the caller's
    question, and the answer is what the owner clicked.

    Where the workflow does declare a return, the record is passed through
    untouched and the engine decides — including refusing when the two disagree.
    A second opinion about which duty applies does not belong in a view.
    """
    from satc.intake.fanout import ENTITY_TYPE_BY_WORKFLOW

    if not ENTITY_TYPE_BY_WORKFLOW.get(workflow.key, ""):
        return ""
    return (getattr(public_client, "entity_type", "") or "").strip().upper()


def _sla_outcomes(*, started: dict, today: date):
    """Every promise on file, each either landed or honestly refused.

    ``compliance`` and not ``promised_by``: a bare ``None`` from ``promised_by``
    is not "kept" and not "fine", and a screen that rendered it as an empty cell
    would be the exact silence principle 1 forbids. ``compliance`` never returns
    nothing — it returns the refusal with the missing fact named.
    """
    from satc.work.sla import compliance, slas

    return [compliance(kind, started_on=started.get(spec.starts_when.key), today=today)
            for kind, spec in sorted(slas().items())]


def _recorded_starts(client_id: str) -> dict[str, date]:
    """The SLA clock-starts SATC actually records, for this client.

    Exactly one today. ``satc.work.sla.FACTS`` is candid that most ends of most
    promises are recorded nowhere — there is no inbound message, no "documents
    went complete" moment, no delivery fact — so those promises refuse by name
    and this function has nothing to offer them. The e-file rejection is the one
    both of whose ends are keyed off Drake and written down.

    Resolving a fact that would be refused anyway would be lookup nobody reads.
    """
    rejected = [f for f in STATE.filings()
                if getattr(f, "client_id", "") == client_id
                and getattr(f, "is_rejected", False) and f.ack_date]
    return {"efile_rejected": max(f.ack_date for f in rejected)} if rejected else {}


# --- reading the answers, and naming what they caused -------------------------

def _plan_answers(workflow, src, *, client_id: str) -> dict[str, str]:
    """The interview answers off the request, for THIS workflow's questions only.

    The same convention the generate form uses, and — since the fix to
    ``/intake/new`` — the same resolution of the new-vs-returning gate. That gate
    is a RECORDED FACT: the practice either has a prior engagement on file or it
    does not, and it is what the whole interview branches on. Leaving it out here
    while the generate route reads it off the record made the plan and the
    engagement two different derivations of the same answers, which is the one
    thing this screen exists not to be.
    """
    answers: dict[str, str] = {}
    for q in workflow.questions:
        if q.id == NEW_CLIENT_GATE:
            continue
        given = src.get(f"q_{q.id}")
        if given is not None:
            answers[q.id] = given
    mode = (src.get("mode") or "").strip()
    if mode in ("new", "returning"):
        answers[NEW_CLIENT_GATE] = "yes" if mode == "new" else "no"
    else:
        answers[NEW_CLIENT_GATE] = "no" if STATE.is_returning(client_id) else "yes"
    return answers


def _because(condition, labels: dict[str, str], answers: dict[str, str]) -> str:
    """Name the answer that caused a task, reading the condition it was gated on.

    Only the EXPLANATION lives here; whether the condition passes is
    ``evaluate_condition``'s business and is asked of the engine (principle 6).
    A question id the workflow no longer defines is printed as the id, because a
    prettified guess at what it once asked would be an invented value.
    """
    if not condition:
        return ""
    for joiner, key in ((" and ", "all"), (" or ", "any")):
        if key in condition:
            parts = [_because(c, labels, answers) for c in condition[key] or []]
            return joiner.join(p for p in parts if p)

    qid = str(condition.get("question_id", "") or "")
    label = labels.get(qid, qid) or "an unnamed question"
    given = str(answers.get(qid, "") or "").strip()
    if not given:
        return f"“{label}” has no answer recorded"
    return f"you answered “{given}” to “{label}”"


def _needs(plan, workflow) -> list[Need]:
    """The client asks this plan opens, each carrying the answer that caused it.

    The rows, the wording and the BLOCKING CLASS all come off the plan's own
    ``RequestedItem``s — what blocks is the duty's cited rule (Pub 1345 on a
    1040), not a literal in a view. Only the cause is assembled here, by reading
    the condition the engine has already evaluated.
    """
    labels = {q.id: q.label for q in workflow.questions}
    templates = {t.template_id: t for t in workflow.tasks}
    tasks = {t.task_id: t for t in plan.job.tasks}
    answers = plan.job.intake_answers or {}

    out: list[Need] = []
    for item in plan.requests:
        task = tasks.get(item.task_id)
        template = templates.get(task.template_id) if task is not None else None
        cause = _because(template.condition if template else None, labels, answers)
        out.append(Need(
            doc_type=str(item.doc_type), title=(task.title if task else str(item.doc_type)),
            ask=item.request_text, why=(task.why_needed if task else ""),
            alternatives=(task.accepted_alternatives if task else ""),
            blocking=item.blocking,
            because=(f"Because {cause}." if cause
                     else f"Asked on every {workflow.name} engagement."),
            by=(task.suggested_date if task else None)))
    return out


@dataclass(frozen=True, slots=True)
class BlockingBasis:
    """Where each of the three blocking classes actually comes from.

    Three headings, three DIFFERENT provenances, and only one of them has a
    citation at all:

    * *blocks prep* — the documents the duty's own rule lists in
      ``blocking_docs``, cited by its ``blocking_source`` (Pub 1345 on a 1040).
      That is **not** the deadline's citation: the rule that says when a return
      is due and the rule that says what must be in hand before originating it
      are two different rules answering two different questions.
    * *blocks filing, not prep* — no citation whatsoever. "A K-1 cannot exist in
      February" is a judgement written into
      ``satc.models.readiness.blocking_class_for`` as a Python literal. It is
      true, and nobody sourced it, and the screen must not dress it as law
      (principle 4).
    * *useful, not load-bearing* — the default for everything else.
    """

    form: str = ""
    docs: tuple[str, ...] = ()
    source: str = ""
    """The blocking list's OWN citation. Empty when the rule cites none."""

    gap: str = ""
    """Set when the rule names blocking documents and NO request matched one —
    an empty class that means "the classifier never fired", not "the file is
    clean". A split whose first bucket can never fill teaches the owner it does
    not matter (principle 13), so it says so instead of rendering empty."""


def _blocking_basis(plan, workflow, needs: list[Need]) -> BlockingBasis:
    """Which rule put a document in which class — read off the rule, not asserted."""
    from satc.obligations.rules import rule as obligation_rule

    if plan.duty is None:
        # Work that files nothing has no cited rule, so nothing here can be
        # attributed to one. An empty basis renders as "no rule says what blocks
        # this" rather than borrowing a citation from a duty that does not exist
        # — principle 4, and the reason bookkeeping must not read like a filing.
        return BlockingBasis(form="", docs=())

    try:
        rule = obligation_rule(plan.duty.rule_key)
    except ConfigError:
        # The duty came from somewhere this build's rule set no longer holds. The
        # duty's own copy of the blocking list survives; its citation does not,
        # and an uncited list is rendered as exactly that rather than borrowed.
        return BlockingBasis(form=plan.duty.form, docs=tuple(plan.duty.blocking_docs))

    basis = BlockingBasis(form=rule.form, docs=tuple(rule.blocking_docs),
                          source=rule.blocking_source)
    if not basis.docs or any(n.blocking == "blocking" for n in needs):
        return basis

    typed = ", ".join(sorted({n.doc_type for n in needs})) or "nothing at all"
    return dataclasses.replace(basis, gap=(
        f"Nothing on this plan blocks starting prep — and that is the classifier failing "
        f"to fire, not a clean file. The Form {basis.form} rule requires "
        f"{', '.join(basis.docs)} in hand before the return is originated, and no request "
        f"here is typed as one of them: the asks on this plan are typed {typed}. A request "
        f"typed as a BUCKET rather than as the form the rule names cannot match it, so "
        f"every document on this plan is being classed as optional, including the ones "
        f"that ask for exactly those forms. Type the ask as the form the rule names "
        f"(doc_type in configs/workflows/{workflow.key}.yaml), or teach "
        f"satc.models.readiness.blocking_class_for to match a form inside a bucket. Until "
        f"one of those happens, treat the split below as unanswered."))


def _fee_slot(plan) -> str:
    """Why the engagement letter's fee slot is empty, when it is.

    ``fan_out`` omits a key it holds no fact for rather than blanking it, so the
    draft renders ``[[ Fee: fill in ]]``. That is right on the letter and
    useless on this screen — here the owner wants to know WHICH of the two
    conditions failed, because they are different problems with different fixes.
    """
    if "fee_amount_text" in plan.letter_facts:
        return ""
    quote = plan.quote
    if quote is None:
        return (f"The letter cannot state a fee: {plan.quote_unavailable or 'there is no quote.'}")
    if getattr(quote, "plan_is_fallback", True):
        return ("The letter will not state a fee, because nobody has agreed a rate plan "
                "with this client — a letter quoting the practice default claims a term "
                "of a contract that was never negotiated. Agree a plan on the engagement "
                "first.")
    if getattr(quote, "unpriced", ()):
        return ("The letter will not state a bare figure, because the total leaves out "
                "the work below that has no price yet. It states the fee terms in words "
                "instead, which can say so.")
    return ""


@bp.route("/intake/plan", methods=["GET", "POST"], endpoint="engagement_plan")
def engagement_plan():
    """The whole engagement the interview implies — and not one write.

    Answer the interview and SEE what falls out of it: what we will need, what
    it will cost, when it is due, what we promised. Every section is derived
    from the same answers by one call, so they cannot disagree with each other,
    and nothing on the page is stored anywhere.
    """
    src = request.form if request.method == "POST" else request.args
    client_id = (src.get("client") or "").strip()
    workflow_key = (src.get("workflow") or src.get("workflow_key") or "").strip()
    public_client = _public_client(client_id)
    client_type = _client_type(public_client)
    year = _int_or_none(src.get("tax_year", ""))
    today = date.today()

    if not workflow_key:
        # Nothing has been asked yet. A picker, not a refusal — "which workflow"
        # is a question with an answer, and 404 is for a workflow that does not
        # exist rather than one nobody has named.
        return render_template(
            "engagement_plan.html", title="Engagement plan", workflow=None, plan=None,
            client_id=client_id, public_client=public_client,
            workflows=STATE.workflow_catalog().get(client_type, []),
            tax_year="" if year is None else year, today=today)

    try:
        from satc.intake.workflows import load_workflow
        workflow = load_workflow(workflow_key)
    except ConfigError as exc:
        abort(404, description=(
            f"{exc} There is no engagement to plan from a workflow SATC does not "
            f"have. Pick one from the interview screen, or add the config."))

    answers = _plan_answers(workflow, src, client_id=client_id)

    def screen(**extra):
        # Defaults merged rather than passed through ``**extra``, so a refusal
        # path renders the same template without every panel's variable having
        # to be repeated at each of the six places that can refuse.
        context = dict(
            title="Engagement plan",
            workflow=workflow, client_id=client_id, public_client=public_client,
            client_name=STATE.name(client_id) if client_id else "",
            tax_year="" if year is None else year, today=today, answers=answers,
            generate_url=url_for("intake.new_engagement"),
            letter_url=url_for("comms.comms", client=client_id,
                               template="engagement_letter",
                               tax_year="" if year is None else year),
            mode=(src.get("mode") or "").strip(),
            plan=None, refusal="", blocking=(), expected_late=(), other_needs=(),
            needs_total=0, blocking_basis=None,
            promises=(), promise_refusal="", fee_slot="")
        context.update(extra)
        return render_template("engagement_plan.html", **context)

    if year is None:
        # A deadline is a rule landed on a PERIOD. Without the year there is no
        # period, and every date on the page would be a guess (principles 1, 3).
        # ``is None`` and not falsiness: ``_int_or_none`` returns the integer 0
        # for ``tax_year=0``, and 0 is a year somebody typed, not a year nobody
        # gave. It gets the refusal below, which names it.
        return screen(refusal=(
            "Set the tax year. Every date on this page is a rule landed on a "
            "period, so until SATC knows which year this engagement is for there "
            "is nothing it can compute — and a plausible date would be worse than "
            "none."))

    try:
        plan = _fan_out(workflow, answers, client_id=client_id, tax_year=year,
                        today=today,
                        entity_type=_entity_type_for(workflow, public_client))
    except ImportError:
        return screen(refusal=(
            "satc.intake.fanout is not installed on this build, so nothing can turn "
            "these answers into an engagement. Generate it from the interview screen "
            "in the meantime."))
    except ConfigError as exc:
        # The designed refusal. A bookkeeping engagement discharges no statutory
        # duty, and an unsourced jurisdiction refuses by name rather than falling
        # back to the federal calendar. The message already says what to do; this
        # renders it instead of rewriting it (principles 5 and 10).
        return screen(refusal=str(exc))
    except ValueError as exc:
        # A year the calendar cannot represent at all — 0, negative, five digits.
        # ``obligations.due_dates.tax_year`` raises rather than inventing a
        # period, which is right; a stack trace in the browser is not the
        # refusal, it is the absence of one (principles 5 and 10). The bound is
        # not restated here: the calendar owns which years exist.
        return screen(refusal=(
            f"SATC cannot land a filing rule on tax year {year}: {exc}. A deadline is a "
            f"rule landed on a real period, so a year the calendar has no such period "
            f"for has no dates on it at all. Set the tax year to the year the return "
            f"is for."))

    needs = _needs(plan, workflow)
    promises, promise_refusal = [], ""
    try:
        promises = _sla_outcomes(started=_recorded_starts(client_id), today=today)
    except ImportError:
        promise_refusal = (
            "SATC holds no turnaround promises on this build — satc.work.sla is not "
            "installed, so nothing has been promised that this screen could show.")
    except ConfigError as exc:
        promise_refusal = str(exc)

    return screen(
        plan=plan,
        # WHAT WE NEED — the three-way blocking split, which means something: a
        # K-1 that cannot exist until September does not stop prep, and a screen
        # that lumps it in with a missing W-2 throws that away. Where each class
        # came FROM is a separate question with three separate answers, and only
        # one of them has a citation — see :class:`BlockingBasis`.
        blocking=[n for n in needs if n.blocking == "blocking"],
        expected_late=[n for n in needs if n.blocking == "expected_late"],
        other_needs=[n for n in needs if n.blocking == "non_blocking"],
        needs_total=len(needs), blocking_basis=_blocking_basis(plan, workflow, needs),
        # WHAT WE PROMISED, and WHY THE LETTER'S FEE SLOT IS EMPTY when it is.
        promises=promises, promise_refusal=promise_refusal, fee_slot=_fee_slot(plan))


@bp.route("/engagements/<job_id>", endpoint="engagement_detail")
def engagement_detail(job_id: str):
    eng = STATE.engagement(job_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))

    # Group tasks by category, preserving first-seen order.
    groups: list[tuple[str, list]] = []
    index: dict[str, int] = {}
    for task in eng.tasks:
        category = task.category or "General"
        if category not in index:
            index[category] = len(groups)
            groups.append((category, []))
        groups[index[category]][1].append(task)

    # Status of any document linked to a client request (Requested/Received badge).
    # A task points at the RequestedItem it opened; the item knows whether it
    # is still open. The old join went through a status string on a merged
    # register that could not say which lifecycle it meant.
    doc_status = {i.request_id: ("Received" if not i.is_open else "Requested")
                  for i in STATE.requested_items()}

    # Counted HERE, not in the template. selectattr('status') over a status
    # string counts every task as done, because any non-empty string is truthy
    # — a 200 with a wrong number, which is worse than a crash.
    done_count = eng.done_count()
    settled, total = eng.progress()

    client_tasks = [t for t in eng.tasks if t.audience == "client"]
    internal_tasks = [t for t in eng.tasks if t.audience != "client"]

    received = sum(1 for t in client_tasks
                   if (t.request_id and doc_status.get(t.request_id) == "Received")
                   or t.is_done)
    total_requests = len(client_tasks)

    return render_template(
        "engagement_detail.html", title="Engagements",
        eng=eng, groups=groups, doc_status=doc_status,
        client_tasks=client_tasks, internal_tasks=internal_tasks,
        received=received, total_requests=total_requests,
        done_count=done_count, settled=settled, total=total)


@bp.route("/engagements/<job_id>/tasks/<task_id>", methods=["POST"])
def toggle_task(job_id: str, task_id: str):
    eng = STATE.engagement(job_id)
    current = False
    if eng is not None:
        for task in eng.tasks:
            if task.task_id == task_id:
                current = task.is_done
                break
    STATE.set_task_completed(task_id, not current)
    return redirect(url_for("intake.engagement_detail", job_id=job_id))


@bp.route("/engagements/<job_id>/email")
def engagement_email(job_id: str):
    eng = STATE.engagement(job_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    try:
        from satc.intake.outputs import generate_client_request_email
    except ImportError:
        return Response("Client-comms output not available yet.", mimetype="text/plain")
    return Response(
        generate_client_request_email(eng, client_name=STATE.name(eng.client_id)),
        mimetype="text/plain")


@bp.route("/engagements/<job_id>/email/outlook", methods=["POST"],
          endpoint="engagement_email_outlook")
def engagement_email_outlook(job_id: str):
    """Pop a ready-to-send Outlook draft of the client request email."""
    eng = STATE.engagement(job_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    from satc.intake.email_draft import mailto_url, open_outlook_draft
    from satc.intake.outputs import build_request_email

    to = STATE.client_email(eng.client_id)
    subject, body = build_request_email(eng, client_name=STATE.name(eng.client_id))
    result = open_outlook_draft(to=to, subject=subject, body=body)
    return render_template(
        "draft_result.html", title="Engagements", result=result, what="request email",
        to=to, subject=subject, body=body,
        mailto=mailto_url(to=to, subject=subject, body=body),
        back_url=url_for("intake.engagement_detail", job_id=job_id),
        attachment_url="", attachment_name="")


# -- intake mode (c): email the client an organizer to fill out --------------

def _restrict(path, mode) -> None:
    import os
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _organizer_path(client_id: str, workflow_key: str):
    from pathlib import Path
    folder = Path(STATE.store.dir) / "organizers"
    folder.mkdir(parents=True, exist_ok=True)
    _restrict(folder, 0o700)   # organizer PDFs carry cleartext client names (M6)
    return folder / f"{client_id}_{workflow_key}_organizer.pdf"


def _write_organizer(client_id: str, workflow_key: str, *, returning: bool,
                     tax_year: int | None = None):
    """Generate the organizer PDF for a client+workflow and return (workflow, path)."""
    from satc.intake.outputs import generate_intake_organizer_pdf
    from satc.intake.workflows import load_workflow

    workflow = load_workflow(workflow_key)
    prior = STATE.prior_engagement(client_id, workflow_key)
    prefill = dict(prior.intake_answers) if (returning and prior is not None) else {}
    pdf = generate_intake_organizer_pdf(
        workflow, client_name=STATE.name(client_id), tax_year=tax_year, returning=returning,
        prefill=prefill, filing_status=STATE.filing_status(client_id))
    path = _organizer_path(client_id, workflow_key)
    path.write_bytes(pdf)
    _restrict(path, 0o600)   # cleartext client name — keep it owner-only (M6)
    return workflow, path


@bp.route("/intake/organizer", endpoint="organizer")
def organizer():
    """Pick a workflow, then preview/send the client a fillable organizer."""
    client_id = request.args.get("client", "")
    public_client = _public_client(client_id)
    if public_client is None:
        return redirect(url_for("intake.engagements"))
    client_type = _client_type(public_client)
    workflow_key = request.args.get("workflow", "")
    returning = STATE.is_returning(client_id)

    workflow = None
    if workflow_key:
        from satc.intake.workflows import load_workflow
        workflow = load_workflow(workflow_key)
    return render_template(
        "organizer.html", title="Intake", client_id=client_id, public_client=public_client,
        returning=returning, workflow=workflow,
        workflows=None if workflow else STATE.workflow_catalog().get(client_type, []),
        client_email=STATE.client_email(client_id), mode="returning" if returning else "new")


@bp.route("/intake/organizer.pdf", endpoint="organizer_pdf")
def organizer_pdf():
    client_id = request.args.get("client", "")
    workflow_key = request.args.get("workflow", "")
    if not (client_id and workflow_key) or _public_client(client_id) is None:
        return redirect(url_for("intake.engagements"))
    returning = request.args.get("mode", "") == "returning" or (
        not request.args.get("mode") and STATE.is_returning(client_id))
    _wf, path = _write_organizer(client_id, workflow_key, returning=returning,
                                 tax_year=_int_or_none(request.args.get("tax_year", "")))
    return send_file(path, mimetype="application/pdf", as_attachment=True,
                     download_name="tax_organizer.pdf")


@bp.route("/intake/organizer/email", methods=["POST"], endpoint="organizer_email")
def organizer_email():
    client_id = request.form.get("client", "")
    workflow_key = request.form.get("workflow_key", "")
    if not (client_id and workflow_key) or _public_client(client_id) is None:
        return redirect(url_for("intake.engagements"))
    returning = request.form.get("mode", "") == "returning"
    tax_year = _int_or_none(request.form.get("tax_year", ""))

    from satc.intake.email_draft import mailto_url, open_outlook_draft
    from satc.intake.outputs import build_organizer_email

    workflow, path = _write_organizer(client_id, workflow_key, returning=returning, tax_year=tax_year)
    subject, body = build_organizer_email(
        client_name=STATE.name(client_id), workflow=workflow, tax_year=tax_year, returning=returning)
    to = STATE.client_email(client_id)
    result = open_outlook_draft(to=to, subject=subject, body=body, attachments=[str(path)])
    return render_template(
        "draft_result.html", title="Intake", result=result, what="organizer email",
        to=to, subject=subject, body=body,
        mailto=mailto_url(to=to, subject=subject, body=body),
        back_url=url_for("intake.organizer", client=client_id, workflow=workflow_key),
        attachment_url=url_for("intake.organizer_pdf", client=client_id, workflow=workflow_key,
                               mode="returning" if returning else "new"),
        attachment_name="tax_organizer.pdf")


@bp.route("/engagements/<job_id>/print")
def engagement_print(job_id: str):
    eng = STATE.engagement(job_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    try:
        from satc.intake.outputs import generate_client_request_print_html
    except ImportError:
        return Response("Client-comms output not available yet.", mimetype="text/plain")
    return Response(
        generate_client_request_print_html(eng, client_name=STATE.name(eng.client_id)),
        mimetype="text/html")


@bp.route("/engagements/<job_id>/print-internal")
def engagement_print_internal(job_id: str):
    eng = STATE.engagement(job_id)
    if eng is None:
        return redirect(url_for("intake.engagements"))
    try:
        from satc.intake.outputs import generate_internal_checklist_print_html
    except ImportError:
        return Response("Client-comms output not available yet.", mimetype="text/plain")
    return Response(
        generate_internal_checklist_print_html(eng, client_name=STATE.name(eng.client_id)),
        mimetype="text/html")
