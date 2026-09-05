"""Intake service — turn interview answers into clients, engagements, and requests.

This is the seam between the checklist workflows and SATC's data model:

  * New clients are minted into the IDENTITY VAULT (sensitive name/TIN) with a
    de-identified projection in the mart — never plaintext PII in the working data.
  * An engagement's client-facing tasks each open a ``RequestedItem``
    (the expected-documents checklist), linked back to the task.
  * :func:`reconcile_received` closes the loop: when the document pipeline reports a
    received document of some type, the matching outstanding request flips to
    ``Received`` and its task completes — "asked for 7, received 4, waiting on 3".

Nothing here trusts the client's self-reported answers as fact; they drive what we
*request* and *review*, and confirmed values still flow through the staging gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from satc.ids import opaque_id
from satc.ingest.classify import wrong_year
from satc.models.actor import INTAKE, Actor
from satc.intake import matching
from satc.intake.importer import ParsedClient
from satc.intake.workflows import build_engagement, load_workflow
from satc.models.identity import IdentityRecord, PublicClient, VaultAddress, VaultContact
from satc.models.intake import Relationship
from satc.models.work import Job
from satc.models.evidence import RequestedItem
from satc.models.readiness import blocking_class_for

# Map the vault's entity type to the checklist app's person/business + tax treatment.
_ENTITY_TO_VIEW = {
    "INDIVIDUAL": ("person", ""),
    "SCORP": ("business", "sCorp"),
    "PARTNERSHIP": ("business", "partnership"),
    "CCORP": ("business", "cCorp"),
}


@dataclass(slots=True)
class ClientView:
    """A lightweight client handle the workflow engine reasons over (non-PII)."""

    client_id: str
    client_type: str          # "person" | "business"
    display_name: str
    tax_treatment: str = ""


def _client_view(public: PublicClient, name: str) -> ClientView:
    client_type, treatment = _ENTITY_TO_VIEW.get(public.entity_type, ("person", ""))
    return ClientView(client_id=public.client_id, client_type=client_type,
                      display_name=name or public.display_label, tax_treatment=treatment)


def next_client_id(store, prefix: str = "SATC") -> str:
    """Allocate the next opaque client handle (e.g. ``SATC-001000``)."""
    biggest = 0
    for pc in store.load_mart().public_clients:
        try:
            biggest = max(biggest, int(pc.client_id.split("-")[-1]))
        except (ValueError, IndexError):
            continue
    return f"{prefix}-{biggest + 1000:06d}"


def _save_public(store, rec: IdentityRecord) -> PublicClient:
    """Vault the identity and persist its de-identified projection to the mart."""
    store.upsert_identity(rec)
    public = rec.to_public() if rec.tin else PublicClient(
        client_id=rec.client_id, entity_type=rec.entity_type,
        display_label=f"Client {rec.client_id} ({rec.entity_type})",
        tin_last4="", tin_masked="", default_return_type=rec.default_return_type(),
        home_state=rec.home_state())
    mart = store.load_mart()
    mart.public_clients = [p for p in mart.public_clients if p.client_id != rec.client_id]
    mart.public_clients.append(public)
    store.save_mart(mart)
    return public


def create_person_client(store, *, first_name: str, last_name: str, ssn: str = "",
                         email: str = "", phone: str = "", address: dict | None = None,
                         client_id: str | None = None) -> str:
    """Create an individual client (vault + de-identified mart projection)."""
    cid = client_id or next_client_id(store)
    legal_name = f"{first_name.strip()} {last_name.strip()}".strip()
    rec = IdentityRecord(client_id=cid, entity_type="INDIVIDUAL", legal_name=legal_name, tin=ssn.strip(),
                         addresses=[_address(address)] if address else [],
                         contacts=[VaultContact(name=legal_name, email=email.strip(),
                                                phone=phone.strip(), role="Taxpayer")])
    _save_public(store, rec)
    return cid


def create_business_client(store, *, legal_name: str, entity_type: str = "", ein: str = "",
                           email: str = "", phone: str = "", address: dict | None = None,
                           client_id: str | None = None) -> str:
    """Create a business client (vault + de-identified mart projection).

    An entity type nobody stated is REFUSED rather than defaulted. This line
    used to read ``entity_type.strip().upper() or "SCORP"``, which recorded an
    S election nobody made — and an S election is assigned by the IRS in
    writing. Everything downstream then treated it as a fact about the taxpayer:
    which return is due, and when.
    """
    if not (entity_type or "").strip():
        raise ValueError(
            f"No entity type was given for {legal_name.strip() or 'this business'}, and "
            f"SATC will not pick one — whether an entity is an S corporation, a "
            f"partnership or a C corporation is assigned by the IRS in writing and it "
            f"decides which return is due and when. Take it from the acceptance letter "
            f"(Form 2553 acceptance / CP261) or the last filed return: SCORP, "
            f"PARTNERSHIP, CCORP.")
    cid = client_id or next_client_id(store)
    rec = IdentityRecord(client_id=cid, entity_type=entity_type.strip().upper(),
                         legal_name=legal_name.strip(), tin=ein.strip(),
                         addresses=[_address(address)] if address else [],
                         contacts=[VaultContact(name=legal_name.strip(), email=email.strip(),
                                                phone=phone.strip(), role="Officer")])
    _save_public(store, rec)
    return cid


def _address(data: dict | None) -> VaultAddress:
    data = data or {}
    return VaultAddress(line1=data.get("line1", ""), line2=data.get("line2", ""),
                        city=data.get("city", ""), state=data.get("state", ""), zip=data.get("zip", ""))


def add_relationship(store, *, from_client_id: str, to_client_id: str, relationship_type: str,
                     ownership_pct: str = "", is_primary: bool = False, note: str = "") -> Relationship:
    """Link two clients (e.g. a person who is a shareholder of a business)."""
    rel = Relationship(rel_id=opaque_id("relationship"), from_client_id=from_client_id,
                       to_client_id=to_client_id, relationship_type=relationship_type,
                       ownership_pct=ownership_pct, is_primary=is_primary, note=note)
    store.upsert_relationship(rel)
    return rel


def _linked_clients(store, client_id: str, relationships, names) -> list[ClientView]:
    public_by_id = {p.client_id: p for p in store.load_mart().public_clients}
    linked_ids = {r.to_client_id if r.from_client_id == client_id else r.from_client_id
                  for r in relationships
                  if client_id in (r.from_client_id, r.to_client_id)}
    return [_client_view(public_by_id[cid], names.get(cid, cid))
            for cid in linked_ids if cid in public_by_id]


def create_engagement(store, *, client_id: str, workflow_key: str, due_date: date | str,
                      answers: dict | None = None, tax_year: int | None = None,
                      period_key: str = "") -> Job:
    """Generate an engagement and open a ``Requested`` document for each client ask."""
    workflow = load_workflow(workflow_key)
    names = store.names()
    relationships = store.load_relationships()
    existing = store.load_jobs()
    linked = _linked_clients(store, client_id, relationships, names)
    my_rels = [r for r in relationships if client_id in (r.from_client_id, r.to_client_id)]

    eng = build_engagement(workflow, client_id=client_id, due_date=due_date, answers=answers,
                           tax_year=tax_year, period_key=period_key, linked_clients=linked,
                           relationships=my_rels, existing_engagements=existing)

    # Each client-facing task opens a Requested document (the expected-docs checklist).
    template_doc_types = {t.template_id: t.doc_type for t in workflow.tasks}
    mart = store.load_mart()
    for task in eng.tasks:
        if task.audience != "client":
            continue
        doc_type = template_doc_types.get(task.template_id, task.title)
        item = RequestedItem(
            request_id=opaque_id("req"), client_id=client_id, tax_year=tax_year or 0,
            doc_type=doc_type,
            request_text=task.client_request_text or task.title,
            # What BLOCKS comes from the cited obligation rule, not from a
            # literal here — see configs/obligations/federal.yaml (Pub 1345).
            blocking=blocking_class_for(doc_type, _blocking_docs()),
            requested_at=date.today(), task_id=task.task_id)
        task.request_id = item.request_id
        mart.requested_items.append(item)
    store.save_mart(mart)
    store.save_job(eng)
    return eng


def _job_jurisdiction(job) -> str:
    """Which jurisdiction's duty a job on file discharges.

    Read off ``obligation_key`` (``client/kind/form/JURISDICTION/period``)
    rather than stored twice — the key is already the composite identity of the
    duty, and a second copy of the jurisdiction is a second thing to disagree.

    A job with no ``obligation_key`` predates the fan-out, and every door that
    could create one before it took a keyed-in date with no jurisdiction at all,
    so it is federal. That is a reading of what the code could produce, not a
    guess about the taxpayer.
    """
    parts = (getattr(job, "obligation_key", "") or "").split("/")
    return parts[3].upper() if len(parts) >= 5 and parts[3].strip() else "US"


def create_engagement_from_intake(store, *, client_id: str, workflow_key: str,
                                  tax_year: int, answers: dict | None = None,
                                  today: date | None = None, jurisdiction: str = "US",
                                  fiscal_year_end: date | None = None,
                                  engagement_ref: str = ""):
    """Create an engagement from the interview alone — no keyed-in due date.

    The preferred door. :func:`create_engagement` above takes a ``due_date``
    argument, which means a date somebody typed into a form drives every task
    on the engagement; here the deadline is COMPUTED from the cited obligation
    rule for the entity and jurisdiction, the ``obligation_key`` is recorded so
    the work queue can find the duty behind the job, and the quote and the
    engagement letter's facts fall out of the same answers.

    Idempotent. Re-running with the same answers finds the same job and opens
    no second copy of any document request; re-running with CHANGED answers
    preserves progress and reports what left scope on
    :attr:`~satc.intake.fanout.EngagementPlan.out_of_scope`.

    Returns the whole :class:`~satc.intake.fanout.EngagementPlan`, not just the
    job, so the caller does not re-derive any of it.

    **IT ALSO CREATES THE CONTRACT ROW, which nothing used to.** Every use of
    ``mart.engagements`` in `src/` was a read until 4 September 2026: an
    :class:`~satc.models.work.Engagement` existed for the four demo clients and
    for nobody else. Generating an engagement here is the moment a real client
    acquires one for the year, so it is the moment the row comes into being.

    ``engagement_ref`` is the join to `client-documents` — the "2026-0001" the
    client sees on every letter, estimate and invoice. Optional, and blank is a
    legitimate state: `SATCStore.client_for_ref` refuses a blank rather than
    resolving an unplaced drop folder to whichever engagement loaded first.
    Passing one here is simply the earliest place it can be set; the engagement
    screen sets it afterwards for everything already on file.
    """
    from satc.intake.fanout import fan_out
    from satc.models.work import engagement_for

    workflow = load_workflow(workflow_key)
    names = store.names()
    relationships = store.load_relationships()
    jobs = store.load_jobs()
    mart = store.load_mart()
    linked = _linked_clients(store, client_id, relationships, names)
    my_rels = [r for r in relationships if client_id in (r.from_client_id, r.to_client_id)]

    # A job already on file for this client/workflow/year/JURISDICTION is the
    # SAME job. Its id and its tasks carry over so progress survives and nothing
    # duplicates — including a legacy job whose id was a uuid rather than a
    # derived one.
    #
    # Jurisdiction belongs in that test. Without it the Massachusetts return
    # matched the federal job for the same client, workflow and year, inherited
    # its id, and OVERWROTE it on save: two duties with two deadlines collapsed
    # into one row.
    period = str(tax_year)
    prior = next((j for j in jobs
                  if j.client_id == client_id and j.workflow_key == workflow_key
                  and (j.period_key or str(j.tax_year or "")) == period
                  and _job_jurisdiction(j) == (jurisdiction or "US").upper()), None)

    # The client's RECORDED entity type decides which filing rule applies — but
    # only when the practice can say how it knows. It is a fact on the client
    # record; the workflow key is only what the owner clicked, and the two
    # disagreeing is how a partnership gets a 1040 date.
    #
    # THE MART CANNOT SAY YET, which is exactly why this is read through
    # ``getattr`` and defaults to unsourced rather than to a basis. Nothing on
    # ``PublicClient`` records where its ``entity_type`` came from, so a value
    # the importer INVENTED (it defaults an unknown business to SCORP) is
    # indistinguishable from one an IRS acceptance letter established. Until
    # that field exists the value is treated as unsourced and ``fan_out``
    # refuses to build a citation on it; the day
    # ``IdentityRecord``/``PublicClient`` carry ``entity_type_basis``, this
    # starts honouring it with no change here.
    public = next((p for p in mart.public_clients if p.client_id == client_id), None)

    plan = fan_out(
        workflow, answers or {}, client_id=client_id, tax_year=tax_year,
        today=today or date.today(), engagements=mart.engagements,
        existing_tasks=prior.tasks if prior else [], jurisdiction=jurisdiction,
        fiscal_year_end=fiscal_year_end,
        entity_type=(public.entity_type if public else ""),
        entity_type_basis=str(getattr(public, "entity_type_basis", "") or ""),
        linked_clients=linked, relationships=my_rels,
        existing_jobs=jobs, job_id=prior.job_id if prior else "",
        # The register itself, so an ask that has already been satisfied stops
        # being a reason to keep reporting a task nobody has to do any more.
        open_request_ids={i.request_id for i in mart.requested_items
                          if i.client_id == client_id and i.is_open},
        created_at=prior.created_at if prior else "")

    if plan.requests:
        known = {i.request_id for i in mart.requested_items}
        # "Already exists as requested" is success, never a conflict — the ids
        # are derived, so this is a re-run guard rather than an error path.
        mart.requested_items.extend(r for r in plan.requests if r.request_id not in known)
        store.save_mart(mart)
    # THE CONTRACT ROW. `create=True` because this call is the one place that
    # genuinely means "this client has an engagement for this year" -- every
    # other reader must keep seeing silence for a client nobody has engaged.
    engagement = engagement_for(mart.engagements, client_id=client_id,
                                tax_year=tax_year, create=True)
    ref = (engagement_ref or "").strip()
    if ref and engagement.engagement_ref != ref:
        engagement.engagement_ref = ref
    store.save_mart(mart)
    store.save_job(plan.job)
    return plan


def letter_facts_for_job(store, job, *, today: date | None = None,
                         jurisdiction: str = "US") -> dict[str, str]:
    """What an engagement letter about ``job`` can honestly say. Writes nothing.

    THE HALF OF THE FAN-OUT'S THIRD CLAIM THAT IS NOT WIRED. ``fan_out``
    derives ``letter_facts``; the comms screen builds its merge values in
    ``satc.app.comms_views._context`` and has never been handed them, so the
    engagement letter renders its scope and its fee from standing wording
    rather than from what this engagement actually agreed. This is the seam
    that closes it, and the call site is one line::

        values = build_context(...)                        # who the client is
        values.update(letter_facts_for_job(STATE.store, engagement))

    In that order: a fact derived from the answers outranks wording a model
    drafted (principle 6). ``fee_amount_text`` is the one key both sides can
    fill, which is why the fan-out's value states that it is an estimate —
    ``build_context`` fills the same name from an ISSUED INVOICE total, and an
    estimate rendered as a bill is a number a client will hold us to.

    RECOMPUTED, NEVER STORED (principle 3). The job carries the answers; a
    second copy of "what we promised" beside them is a second thing to be
    wrong. Refuses the same way ``create_engagement_from_intake`` does — a job
    with no tax year has no computable statutory deadline, and a letter is not
    the place to discover that.
    """
    if not getattr(job, "tax_year", None):
        raise ValueError(
            f"Job {getattr(job, 'job_id', '?')} has no tax year on it, so nothing can "
            f"compute the deadline or the fee an engagement letter states. Regenerate "
            f"the engagement from intake, which records the year and the duty behind it.")

    from satc.intake.fanout import fan_out

    mart = store.load_mart()
    public = next((p for p in mart.public_clients
                   if p.client_id == job.client_id), None)
    plan = fan_out(
        load_workflow(job.workflow_key), dict(job.intake_answers or {}),
        client_id=job.client_id, tax_year=job.tax_year, today=today or date.today(),
        engagements=mart.engagements, existing_tasks=list(job.tasks),
        jurisdiction=_job_jurisdiction(job) or jurisdiction,
        entity_type=(public.entity_type if public else ""),
        entity_type_basis=str(getattr(public, "entity_type_basis", "") or ""),
        existing_jobs=[job], job_id=job.job_id,
        open_request_ids={i.request_id for i in mart.requested_items
                          if i.client_id == job.client_id and i.is_open},
        created_at=job.created_at)
    return plan.letter_facts


def find_match(store, *, client_id: str, doc_type: str,
               doc_year: int | None = None) -> RequestedItem | None:
    """The outstanding request an arriving document would satisfy. Reads only.

    A request's type AND its prose description (stored in ``note``) are both
    considered, so a received "W-2" satisfies a "core income documents" bundle.
    When several requests match, the most specific one wins.

    ``doc_year`` is the tax year read off the document, and it is filtered
    ASYMMETRICALLY: a year we could not read (None) blocks nothing, but a year we
    DID read which differs from the request's closes nothing. Measured 30 Aug
    2026, before this: a 2019 W-2 from a job the client left marked this year's
    W-2 request Received. See ``satc.ingest.classify.wrong_year``.
    """
    mart = store.load_mart()
    candidates = [i for i in mart.requested_items
                  if i.client_id == client_id and i.is_open
                  and matching.matches(doc_type, str(i.doc_type), i.request_text)
                  and not wrong_year(doc_year, i.tax_year)]
    if not candidates:
        return None
    return min(candidates,
               key=lambda i: matching.specificity(str(i.doc_type), i.request_text))


def _blocking_docs():
    """Which document types block, per the cited federal 1040 rule."""
    try:
        from satc.obligations.rules import rule
        return rule("form_1040").blocking_docs
    except Exception:  # noqa: BLE001 - config absent should not stop intake
        return ()


def reconcile_received(store, *, client_id: str, doc_type: str,
                       doc_year: int | None = None,
                       classified_by: Actor = INTAKE) -> RequestedItem | None:
    """Flip the best matching outstanding request to ``Received`` and complete its task.

    Called when the document pipeline classifies an arriving document; closes the
    loop between what was requested at intake and what has actually come in.

    **This is the only automatic durable write in the app**, which is why it is
    gated. It was previously reachable from ANY classifier rung — including the
    vision rung, where a MODEL decides what the document is — with no actor and
    no check. A model could therefore mark a client request satisfied, complete
    the task, and have it recorded as ordinary intake.

    A model-classified arrival now closes nothing. It is still reported, and
    :func:`find_match` names the request it *probably* satisfies, so the owner
    closes it in one click on the Documents screen. Propose, never dispose.
    """
    if classified_by.is_model:
        return None
    match = find_match(store, client_id=client_id, doc_type=doc_type,
                       doc_year=doc_year)
    if match is None:
        return None

    # A REQUEST NAMING SEVERAL FORMS IS SEVERAL ASKS WEARING ONE ROW.
    #
    # "Upload Forms 1099-INT, 1099-DIV and brokerage statements" used to be
    # closed by whichever of the three arrived first. The 1099-INT that came
    # next then found nothing open to satisfy, and the brokerage statement was
    # never chased at all -- the firm hit this in a live run on 31 Aug 2026.
    #
    # The firm's decision, 4 September 2026: it stays open until every named
    # part has arrived. So record what came, and only close when nothing is
    # left outstanding. A single-form request has no parts and takes the same
    # path it always did -- and so does a standing checklist that ends "and any
    # other income forms received", which names five forms and requires none of
    # them in particular. See `matching.needs_every_part`.
    if match.needs_every_part:
        arriving = matching.families(doc_type)
        match.parts = set(match.parts or set()) | arriving
        if match.outstanding_parts:
            store.save_requested_items([match])
            return match          # still open, and the caller can say what is left

    match.status = "satisfied"
    store.save_requested_items([match])
    for eng in store.load_jobs():
        for task in eng.tasks:
            if task.request_id == match.request_id and task.is_open:
                task.status = "done"
                store.save_task(task)
    return match


def outstanding_parts(item) -> set[str]:
    """Which forms a request still names and has not received.

    Empty for an ordinary single-form request, and empty for a bundle once the
    last part lands -- so ``not outstanding_parts(item)`` reads as "nothing
    left to chase" in both cases.
    """
    return item.outstanding_parts if item is not None else set()


# ---------------------------------------------------------------------------
# Bulk client import (CSV / spreadsheet / Drake export)
# ---------------------------------------------------------------------------

def existing_client_index(store) -> list[tuple[str, str]]:
    """(display name, TIN last-4) for every existing client — for dedup detection."""
    names = store.names()
    out: list[tuple[str, str]] = []
    for pc in store.load_mart().public_clients:
        out.append((names.get(pc.client_id, pc.display_label), pc.tin_last4 or ""))
    return out


def preview_import(store, *, csv_text: str | None = None, rows: list[dict] | None = None):
    """Parse a roster into previewed clients, flagged new / duplicate / review."""
    from satc.intake import importer

    existing = existing_client_index(store)
    if csv_text is not None:
        return importer.parse_csv(csv_text, existing=existing)
    return importer.parse_rows(rows or [], existing=existing)


def commit_import(store, parsed: list[ParsedClient], *, include_duplicates: bool = False) -> list[str]:
    """Create the previewed clients in the vault. Skips duplicates unless asked."""
    created: list[str] = []
    for pc in parsed:
        if pc.status == "duplicate" and not include_duplicates:
            continue
        if pc.kind == "business":
            cid = create_business_client(store, legal_name=pc.legal_name, entity_type=pc.entity_type,
                                         ein=pc.tin, email=pc.email, phone=pc.phone,
                                         address={"state": pc.state} if pc.state else None)
        else:
            cid = create_person_client(store, first_name=pc.first_name, last_name=pc.last_name,
                                       ssn=pc.tin, email=pc.email, phone=pc.phone,
                                       address={"state": pc.state} if pc.state else None)
        created.append(cid)
    return created
