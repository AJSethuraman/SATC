"""Durable store of record — SQLite, with the vault and mart physically separated.

Two single-file databases (no server, no setup — sqlite3 is built into Python):
  * ``satc_vault.db`` — the IDENTITY VAULT (sensitive: legal name, full TIN,
    addresses, contacts). Kept in its own file so it can carry its own
    permissions/encryption and never co-mingles with de-identified data.
  * ``satc_mart.db``  — the WORKING DATA MART (de-identified: client_id, masked
    last-4, returns, line items, carryforwards, basis, payments, engagements,
    documents). This is what the app reads/writes and what exports to Excel.

The dataclasses in :mod:`satc.models` are already SQL-shaped, so the mapping here
is mechanical. Money is stored as TEXT (Decimal string) to preserve precision;
dates as ISO text. Excel remains a first-class *export* (see
:mod:`satc.persistence.export`), not the store of record.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from satc.fixtures import synthetic_identities, synthetic_mart
from satc.models.identity import IdentityRecord, PublicClient
from satc.models.intake import IntakeEngagement, IntakeTask, Relationship
from satc.models.mart import (
    Carryforward,
    DataMart,
    DocumentRecord,
    EngagementRecord,
    EstimatePayment,
    LineItem,
    OwnerBasis,
    ReturnRecord,
)
from satc.models.provenance import Provenance, SourceRef

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "build" / "data"

_VAULT_DDL = """
CREATE TABLE IF NOT EXISTS identities (
  client_id TEXT PRIMARY KEY, entity_type TEXT, legal_name TEXT, tin TEXT);
CREATE TABLE IF NOT EXISTS vault_addresses (
  client_id TEXT, line1 TEXT, line2 TEXT, city TEXT, state TEXT, zip TEXT);
CREATE TABLE IF NOT EXISTS vault_contacts (
  client_id TEXT, name TEXT, email TEXT, phone TEXT, role TEXT);
"""

_MART_DDL = """
CREATE TABLE IF NOT EXISTS public_clients (
  client_id TEXT PRIMARY KEY, entity_type TEXT, display_label TEXT,
  tin_last4 TEXT, tin_masked TEXT, default_return_type TEXT, home_state TEXT);
CREATE TABLE IF NOT EXISTS returns (
  return_key TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, return_type TEXT,
  jurisdiction TEXT, status TEXT, preparer_id TEXT, residency TEXT, is_extended INTEGER,
  filed_date TEXT, accepted_date TEXT, refund_amount TEXT, balance_due_amount TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS line_items (
  line_item_key TEXT PRIMARY KEY, return_key TEXT, schedule TEXT, line_code TEXT,
  label TEXT, amount TEXT, text_value TEXT, source_kind TEXT, citation TEXT);
CREATE TABLE IF NOT EXISTS carryforwards (
  cf_id TEXT PRIMARY KEY, client_id TEXT, return_type TEXT, jurisdiction TEXT, kind TEXT,
  tax_year_generated INTEGER, amount TEXT, applied_to_year INTEGER, expires_after_year INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS owner_basis (
  return_key TEXT, client_id TEXT, owner_id TEXT, tax_year INTEGER, beginning_balance TEXT,
  contributions TEXT, income_items TEXT, loss_items TEXT, distributions TEXT, ending_balance TEXT,
  debt_basis_beginning TEXT, debt_basis_ending TEXT, ownership_pct TEXT,
  PRIMARY KEY (return_key, owner_id, tax_year));
CREATE TABLE IF NOT EXISTS estimate_payments (
  payment_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, jurisdiction TEXT,
  period TEXT, amount TEXT, paid_date TEXT);
CREATE TABLE IF NOT EXISTS engagements (
  client_id TEXT, tax_year INTEGER, engagement_letter_status TEXT, fee_amount TEXT,
  invoiced INTEGER, paid INTEGER, preparer_id TEXT, note TEXT,
  PRIMARY KEY (client_id, tax_year));
CREATE TABLE IF NOT EXISTS documents (
  document_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, doc_type TEXT,
  status TEXT, as_of TEXT, sharepoint_link TEXT, actor TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS relationships (
  rel_id TEXT PRIMARY KEY, from_client_id TEXT, to_client_id TEXT,
  relationship_type TEXT, ownership_pct TEXT, is_primary INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS intake_engagements (
  engagement_id TEXT PRIMARY KEY, client_id TEXT, workflow_key TEXT, engagement_type TEXT,
  tax_year INTEGER, period_end TEXT, due_date TEXT, intake_answers TEXT, risk_flags TEXT,
  created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS intake_tasks (
  task_id TEXT PRIMARY KEY, engagement_id TEXT, template_id TEXT, title TEXT, category TEXT,
  audience TEXT, client_request_text TEXT, accepted_alternatives TEXT, why_needed TEXT,
  internal_instructions TEXT, suggested_date TEXT, completed INTEGER, notes TEXT,
  relationship_generated INTEGER, document_id TEXT);
"""


def _d(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _pd(x: str | None) -> Decimal | None:
    return None if x in (None, "") else Decimal(x)


def _dt(x: date | None) -> str | None:
    return None if x is None else x.isoformat()


def _pdt(x: str | None) -> date | None:
    return None if x in (None, "") else date.fromisoformat(x)


class SATCStore:
    """Facade over the vault + mart databases."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self.dir = Path(directory) if directory else DEFAULT_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.vault = sqlite3.connect(self.dir / "satc_vault.db", check_same_thread=False)
        self.mart = sqlite3.connect(self.dir / "satc_mart.db", check_same_thread=False)
        for conn in (self.vault, self.mart):
            conn.row_factory = sqlite3.Row
        self.vault.executescript(_VAULT_DDL)
        self.mart.executescript(_MART_DDL)
        self.vault.commit()
        self.mart.commit()

    # -- lifecycle --------------------------------------------------------
    def is_empty(self) -> bool:
        return self.mart.execute("SELECT COUNT(*) FROM returns").fetchone()[0] == 0

    def seed_if_empty(self) -> bool:
        if not self.is_empty():
            return False
        for rec in synthetic_identities():
            self.upsert_identity(rec)
        self.save_mart(synthetic_mart())
        return True

    # -- vault ------------------------------------------------------------
    def upsert_identity(self, rec: IdentityRecord) -> None:
        self.vault.execute(
            "INSERT OR REPLACE INTO identities VALUES (?,?,?,?)",
            (rec.client_id, rec.entity_type, rec.legal_name, rec.tin))
        self.vault.execute("DELETE FROM vault_addresses WHERE client_id=?", (rec.client_id,))
        for a in rec.addresses:
            self.vault.execute("INSERT INTO vault_addresses VALUES (?,?,?,?,?,?)",
                               (rec.client_id, a.line1, a.line2, a.city, a.state, a.zip))
        self.vault.execute("DELETE FROM vault_contacts WHERE client_id=?", (rec.client_id,))
        for c in rec.contacts:
            self.vault.execute("INSERT INTO vault_contacts VALUES (?,?,?,?,?)",
                               (rec.client_id, c.name, c.email, c.phone, c.role))
        self.vault.commit()

    def names(self) -> dict[str, str]:
        return {r["client_id"]: r["legal_name"]
                for r in self.vault.execute("SELECT client_id, legal_name FROM identities")}

    # -- mart write -------------------------------------------------------
    def save_mart(self, mart: DataMart) -> None:
        m = self.mart
        for pc in mart.public_clients:
            m.execute("INSERT OR REPLACE INTO public_clients VALUES (?,?,?,?,?,?,?)",
                      (pc.client_id, pc.entity_type, pc.display_label, pc.tin_last4,
                       pc.tin_masked, pc.default_return_type, pc.home_state))
        for r in mart.returns:
            m.execute("INSERT OR REPLACE INTO returns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (r.return_key, r.client_id, r.tax_year, r.return_type, r.jurisdiction,
                       r.status, r.preparer_id, r.residency, int(r.is_extended), _dt(r.filed_date),
                       _dt(r.accepted_date), _d(r.refund_amount), _d(r.balance_due_amount), r.note))
        for li in mart.line_items:
            sk = li.provenance.source_kind if li.provenance else ""
            cit = (li.provenance.short_source() if li.provenance else "")
            m.execute("INSERT OR REPLACE INTO line_items VALUES (?,?,?,?,?,?,?,?,?)",
                      (li.line_item_key, li.return_key, li.schedule, li.line_code, li.label,
                       _d(li.amount), li.text_value, sk, cit))
        for c in mart.carryforwards:
            m.execute("INSERT OR REPLACE INTO carryforwards VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (c.cf_id, c.client_id, c.return_type, c.jurisdiction, c.kind,
                       c.tax_year_generated, _d(c.amount), c.applied_to_year,
                       c.expires_after_year, c.note))
        for b in mart.owner_basis:
            m.execute("INSERT OR REPLACE INTO owner_basis VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (b.return_key, b.client_id, b.owner_id, b.tax_year, _d(b.beginning_balance),
                       _d(b.contributions), _d(b.income_items), _d(b.loss_items), _d(b.distributions),
                       _d(b.ending_balance), _d(b.debt_basis_beginning), _d(b.debt_basis_ending),
                       _d(b.ownership_pct)))
        for p in mart.estimate_payments:
            m.execute("INSERT OR REPLACE INTO estimate_payments VALUES (?,?,?,?,?,?,?)",
                      (p.payment_id, p.client_id, p.tax_year, p.jurisdiction, p.period,
                       _d(p.amount), _dt(p.paid_date)))
        for e in mart.engagements:
            m.execute("INSERT OR REPLACE INTO engagements VALUES (?,?,?,?,?,?,?,?)",
                      (e.client_id, e.tax_year, e.engagement_letter_status, _d(e.fee_amount),
                       int(e.invoiced), int(e.paid), e.preparer_id, e.note))
        for d in mart.documents:
            m.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?)",
                      (d.document_id, d.client_id, d.tax_year, str(d.doc_type), d.status,
                       _dt(d.as_of), d.sharepoint_link, d.actor, d.note))
        m.commit()

    def set_document_status(self, document_id: str, status: str) -> None:
        self.mart.execute("UPDATE documents SET status=? WHERE document_id=?", (status, document_id))
        self.mart.commit()

    # -- intake: relationships + engagements + tasks ----------------------
    def upsert_relationship(self, rel: Relationship) -> None:
        self.mart.execute("INSERT OR REPLACE INTO relationships VALUES (?,?,?,?,?,?,?)",
                          (rel.rel_id, rel.from_client_id, rel.to_client_id, rel.relationship_type,
                           rel.ownership_pct, int(rel.is_primary), rel.note))
        self.mart.commit()

    def load_relationships(self) -> list[Relationship]:
        return [Relationship(
            rel_id=r["rel_id"], from_client_id=r["from_client_id"], to_client_id=r["to_client_id"],
            relationship_type=r["relationship_type"], ownership_pct=r["ownership_pct"] or "",
            is_primary=bool(r["is_primary"]), note=r["note"] or "")
            for r in self.mart.execute("SELECT * FROM relationships ORDER BY rel_id")]

    def save_intake_engagement(self, eng: IntakeEngagement) -> None:
        """Persist an engagement and (replace) its task list."""
        self.mart.execute("INSERT OR REPLACE INTO intake_engagements VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (eng.engagement_id, eng.client_id, eng.workflow_key, eng.engagement_type,
                           eng.tax_year, eng.period_end, _dt(eng.due_date),
                           json.dumps(eng.intake_answers), json.dumps(eng.risk_flags),
                           eng.created_at, eng.updated_at))
        self.mart.execute("DELETE FROM intake_tasks WHERE engagement_id=?", (eng.engagement_id,))
        for t in eng.tasks:
            self._insert_task(t)
        self.mart.commit()

    def _insert_task(self, t: IntakeTask) -> None:
        self.mart.execute("INSERT OR REPLACE INTO intake_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (t.task_id, t.engagement_id, t.template_id, t.title, t.category, t.audience,
                           t.client_request_text, t.accepted_alternatives, t.why_needed,
                           t.internal_instructions, _dt(t.suggested_date), int(t.completed), t.notes,
                           int(t.relationship_generated), t.document_id))

    def save_task(self, t: IntakeTask) -> None:
        self._insert_task(t)
        self.mart.commit()

    def load_intake_engagements(self) -> list[IntakeEngagement]:
        tasks_by_eng: dict[str, list[IntakeTask]] = {}
        for r in self.mart.execute("SELECT * FROM intake_tasks ORDER BY suggested_date, task_id"):
            tasks_by_eng.setdefault(r["engagement_id"], []).append(IntakeTask(
                task_id=r["task_id"], engagement_id=r["engagement_id"], template_id=r["template_id"],
                title=r["title"], category=r["category"], audience=r["audience"],
                client_request_text=r["client_request_text"] or "",
                accepted_alternatives=r["accepted_alternatives"] or "",
                why_needed=r["why_needed"] or "", internal_instructions=r["internal_instructions"] or "",
                suggested_date=_pdt(r["suggested_date"]), completed=bool(r["completed"]),
                notes=r["notes"] or "", relationship_generated=bool(r["relationship_generated"]),
                document_id=r["document_id"] or ""))
        return [IntakeEngagement(
            engagement_id=r["engagement_id"], client_id=r["client_id"], workflow_key=r["workflow_key"],
            engagement_type=r["engagement_type"], tax_year=r["tax_year"], period_end=r["period_end"] or "",
            due_date=_pdt(r["due_date"]), intake_answers=json.loads(r["intake_answers"] or "{}"),
            risk_flags=json.loads(r["risk_flags"] or "[]"), created_at=r["created_at"] or "",
            updated_at=r["updated_at"] or "", tasks=tasks_by_eng.get(r["engagement_id"], []))
            for r in self.mart.execute("SELECT * FROM intake_engagements ORDER BY created_at")]

    # -- mart read --------------------------------------------------------
    def load_mart(self) -> DataMart:
        m = self.mart
        mart = DataMart()
        mart.public_clients = [PublicClient(
            client_id=r["client_id"], entity_type=r["entity_type"], display_label=r["display_label"],
            tin_last4=r["tin_last4"], tin_masked=r["tin_masked"],
            default_return_type=r["default_return_type"], home_state=r["home_state"])
            for r in m.execute("SELECT * FROM public_clients ORDER BY client_id")]
        mart.returns = [ReturnRecord(
            return_key=r["return_key"], client_id=r["client_id"], tax_year=r["tax_year"],
            return_type=r["return_type"], jurisdiction=r["jurisdiction"], status=r["status"],
            preparer_id=r["preparer_id"], residency=r["residency"], is_extended=bool(r["is_extended"]),
            filed_date=_pdt(r["filed_date"]), accepted_date=_pdt(r["accepted_date"]),
            refund_amount=_pd(r["refund_amount"]), balance_due_amount=_pd(r["balance_due_amount"]),
            note=r["note"]) for r in m.execute("SELECT * FROM returns ORDER BY tax_year, return_key")]
        mart.line_items = [LineItem(
            line_item_key=r["line_item_key"], return_key=r["return_key"], schedule=r["schedule"],
            line_code=r["line_code"], label=r["label"], amount=_pd(r["amount"]),
            text_value=r["text_value"] or "",
            provenance=Provenance(source_kind=r["source_kind"] or "COMPUTED",
                                  source_ref=SourceRef(citation=r["citation"] or "")))
            for r in m.execute("SELECT * FROM line_items")]
        mart.carryforwards = [Carryforward(
            cf_id=r["cf_id"], client_id=r["client_id"], return_type=r["return_type"],
            jurisdiction=r["jurisdiction"], kind=r["kind"], tax_year_generated=r["tax_year_generated"],
            amount=_pd(r["amount"]) or Decimal("0"), applied_to_year=r["applied_to_year"],
            expires_after_year=r["expires_after_year"], note=r["note"])
            for r in m.execute("SELECT * FROM carryforwards")]
        mart.owner_basis = [OwnerBasis(
            return_key=r["return_key"], client_id=r["client_id"], owner_id=r["owner_id"],
            tax_year=r["tax_year"], beginning_balance=_pd(r["beginning_balance"]) or Decimal("0"),
            contributions=_pd(r["contributions"]) or Decimal("0"),
            income_items=_pd(r["income_items"]) or Decimal("0"),
            loss_items=_pd(r["loss_items"]) or Decimal("0"),
            distributions=_pd(r["distributions"]) or Decimal("0"),
            ending_balance=_pd(r["ending_balance"]) or Decimal("0"),
            debt_basis_beginning=_pd(r["debt_basis_beginning"]) or Decimal("0"),
            debt_basis_ending=_pd(r["debt_basis_ending"]) or Decimal("0"),
            ownership_pct=_pd(r["ownership_pct"]))
            for r in m.execute("SELECT * FROM owner_basis")]
        mart.estimate_payments = [EstimatePayment(
            payment_id=r["payment_id"], client_id=r["client_id"], tax_year=r["tax_year"],
            jurisdiction=r["jurisdiction"], period=r["period"], amount=_pd(r["amount"]) or Decimal("0"),
            paid_date=_pdt(r["paid_date"])) for r in m.execute("SELECT * FROM estimate_payments")]
        mart.engagements = [EngagementRecord(
            client_id=r["client_id"], tax_year=r["tax_year"],
            engagement_letter_status=r["engagement_letter_status"], fee_amount=_pd(r["fee_amount"]),
            invoiced=bool(r["invoiced"]), paid=bool(r["paid"]), preparer_id=r["preparer_id"],
            note=r["note"]) for r in m.execute("SELECT * FROM engagements")]
        mart.documents = [DocumentRecord(
            document_id=r["document_id"], client_id=r["client_id"], tax_year=r["tax_year"],
            doc_type=r["doc_type"], status=r["status"], as_of=_pdt(r["as_of"]),
            sharepoint_link=r["sharepoint_link"] or "", actor=r["actor"] or "", note=r["note"] or "")
            for r in m.execute("SELECT * FROM documents ORDER BY document_id")]
        return mart

    def close(self) -> None:
        self.vault.close()
        self.mart.close()
