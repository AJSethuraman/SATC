"""Intake service — turn interview answers into clients, engagements, and requests.

This is the seam between the checklist workflows and SATC's data model:

  * New clients are minted into the IDENTITY VAULT (sensitive name/TIN) with a
    de-identified projection in the mart — never plaintext PII in the working data.
  * An engagement's client-facing tasks each create a ``Requested`` DocumentRecord
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
from satc.intake import matching
from satc.intake.importer import ParsedClient
from satc.intake.workflows import build_engagement, load_workflow
from satc.models.identity import IdentityRecord, PublicClient, VaultAddress, VaultContact
from satc.models.intake import IntakeEngagement, Relationship
from satc.models.mart import DocumentRecord

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


def create_business_client(store, *, legal_name: str, entity_type: str = "SCORP", ein: str = "",
                           email: str = "", phone: str = "", address: dict | None = None,
                           client_id: str | None = None) -> str:
    """Create a business client (vault + de-identified mart projection)."""
    cid = client_id or next_client_id(store)
    rec = IdentityRecord(client_id=cid, entity_type=entity_type.strip().upper() or "SCORP",
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
                      period_end: str = "") -> IntakeEngagement:
    """Generate an engagement and open a ``Requested`` document for each client ask."""
    workflow = load_workflow(workflow_key)
    names = store.names()
    relationships = store.load_relationships()
    existing = store.load_intake_engagements()
    linked = _linked_clients(store, client_id, relationships, names)
    my_rels = [r for r in relationships if client_id in (r.from_client_id, r.to_client_id)]

    eng = build_engagement(workflow, client_id=client_id, due_date=due_date, answers=answers,
                           tax_year=tax_year, period_end=period_end, linked_clients=linked,
                           relationships=my_rels, existing_engagements=existing)

    # Each client-facing task opens a Requested document (the expected-docs checklist).
    template_doc_types = {t.template_id: t.doc_type for t in workflow.tasks}
    mart = store.load_mart()
    for task in eng.tasks:
        if task.audience != "client":
            continue
        doc = DocumentRecord(
            document_id=opaque_id("doc"), client_id=client_id, tax_year=tax_year or 0,
            doc_type=template_doc_types.get(task.template_id, task.title), status="Requested",
            as_of=date.today(), actor="intake", note=task.client_request_text or task.title)
        task.document_id = doc.document_id
        mart.documents.append(doc)
    store.save_mart(mart)
    store.save_intake_engagement(eng)
    return eng


def reconcile_received(store, *, client_id: str, doc_type: str,
                       doc_year: int | None = None) -> DocumentRecord | None:
    """Flip the best matching outstanding request to ``Received`` and complete its task.

    Called when the document pipeline classifies an arriving document; closes the
    loop between what was requested at intake and what has actually come in. A
    request's type AND its prose description (stored in ``note``) are both
    considered, so a received "W-2" satisfies a "core income documents" bundle.
    When several requests match, the most specific one wins.

    ``doc_year`` is the tax year read off the document, and it is filtered
    ASYMMETRICALLY: a year we could not read (None) blocks nothing, but a year we
    DID read which differs from the request's closes nothing. Measured 30 Aug
    2026, before this: a 2019 W-2 from a job the client left marked this year's
    W-2 request Received. See ``satc.ingest.classify.wrong_year``.
    """
    mart = store.load_mart()
    candidates = [d for d in mart.documents
                  if d.client_id == client_id and d.status == "Requested"
                  and matching.matches(doc_type, str(d.doc_type), d.note)
                  and not wrong_year(doc_year, d.tax_year)]
    if not candidates:
        return None
    match = min(candidates, key=lambda d: matching.specificity(str(d.doc_type), d.note))

    # A BUNDLE STAYS OPEN UNTIL EVERY FORM IT NAMES HAS ARRIVED. Found in a live
    # run, 31 Aug 2026: the request read "Upload Forms 1099-INT, 1099-DIV and
    # brokerage statements", the 1099-DIV arrived, the request went Received --
    # and the 1099-INT that came next found no open request to satisfy. The
    # packet reads complete while a named form is still missing, which is the
    # consolidated-1099 bug the firm already paid for, arriving from the other
    # direction.
    #
    # The firm: fix it. A bundle now records which of its forms have turned up
    # and closes only when none are outstanding; `outstanding_parts` says which
    # are still missing so a caller can put it in the note.
    #
    # WHAT THIS COSTS, and why it is still right. The shipped core-income
    # request reads "Upload Forms W-2, 1099-INT, 1099-DIV, 1099-B, 1099-G, and
    # any other income forms received" -- five forms, and a single W-2 used to
    # close all five. But most clients have no 1099-G, so that request will now
    # never close ITSELF, and a request that stays open forever is its own kind
    # of false report.
    #
    # Nothing here can know whether a client HAS a 1099-G; only the preparer
    # can. So the software stops guessing "complete" and says what is still
    # missing, and the preparer marks it Received from the Documents view when
    # they know that is everything. The pipeline feeds a human. Between the two
    # failures -- a request closed while a named form is missing, and a request
    # left open a person can close in one click -- only the first loses a
    # document.
    texts = (str(match.doc_type), match.note)
    if matching.is_bundle(*texts):
        arrived = match.parts | matching.families(doc_type)
        match.received_parts = " ".join(sorted(arrived))
        store.set_document_parts(match.document_id, match.received_parts)
        if matching.outstanding(texts, arrived):
            return match          # filed against the request; the request stays open

    store.set_document_status(match.document_id, "Received")
    match.status = "Received"
    for eng in store.load_intake_engagements():
        for task in eng.tasks:
            if task.document_id == match.document_id and not task.completed:
                task.completed = True
                store.save_task(task)
    return match


def outstanding_parts(record) -> set[str]:
    """Which forms a bundle request is still waiting on. Empty for a plain one."""
    texts = (str(record.doc_type), record.note)
    if not matching.is_bundle(*texts):
        return set()
    return matching.outstanding(texts, record.parts)


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
