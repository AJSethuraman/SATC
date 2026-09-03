"""Durable store of record — SQLite, with the vault and mart physically separated.

Two single-file databases (no server, no setup — sqlite3 is built into Python):
  * ``satc_vault.db`` — the IDENTITY VAULT (sensitive: legal name, full TIN,
    addresses, contacts). Kept in its own file, with its PII columns encrypted at
    rest (AES-256-GCM; see :mod:`satc.persistence.crypto`) and restrictive file
    permissions, so a copied/synced database yields no readable client data.
  * ``satc_mart.db``  — the WORKING DATA MART (de-identified: client_id, masked
    last-4, returns, line items, carryforwards, basis, payments, engagements,
    requested items, received documents). This is what the app reads/writes
    and what exports to Excel.

The dataclasses in :mod:`satc.models` are already SQL-shaped, so the mapping here
is mechanical. Money is stored as TEXT (Decimal string) to preserve precision;
dates as ISO text. Excel remains a first-class *export* (see
:mod:`satc.persistence.export`), not the store of record.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from satc.persistence.crypto import open_cipher


def _restrict_dir(path: Path) -> None:
    """Best-effort 0700 on the data dir (POSIX). On Windows NTFS ACLs apply."""
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _restrict_file(path: Path) -> None:
    """Best-effort 0600 on a database file (POSIX)."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

from satc.fixtures import synthetic_identities, synthetic_mart
from satc.models.identity import IdentityRecord, PublicClient
from satc.models.intake import Relationship
from satc.models.work import Engagement, Job, Task
from satc.models.mart import (
    Carryforward,
    DataMart,
    EstimatePayment,
    LineItem,
    OwnerBasis,
    ReturnRecord,
)
from satc.models.provenance import Provenance, SourceRef

def _default_dir() -> Path:
    """Where the SQLite databases live by default.

    In a dev checkout this is ``satc_system/build/data``. Inside a PyInstaller
    bundle that path points into a read-only temp extraction dir, so fall back to
    a per-user writable location instead. ``SATC_DATA_DIR`` (handled by the
    caller) always wins over this default.
    """
    if getattr(sys, "frozen", False):
        return Path.home() / ".satc" / "data"
    return Path(__file__).resolve().parents[3] / "build" / "data"


DEFAULT_DIR = _default_dir()

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
  tin_last4 TEXT, tin_masked TEXT, default_return_type TEXT, home_state TEXT,
  filing_status TEXT);
CREATE TABLE IF NOT EXISTS returns (
  return_key TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, return_type TEXT,
  jurisdiction TEXT, preparer_id TEXT, residency TEXT,
  refund_amount TEXT, balance_due_amount TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS line_items (
  line_item_key TEXT PRIMARY KEY, return_key TEXT, schedule TEXT, line_code TEXT,
  label TEXT, amount TEXT, text_value TEXT, source_kind TEXT, citation TEXT,
  confidence TEXT, produced_by TEXT, document_id TEXT);
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
  rate_plan_key TEXT, rate_plan_basis TEXT,
  PRIMARY KEY (client_id, tax_year));
CREATE TABLE IF NOT EXISTS requested_items (
  request_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, doc_type TEXT,
  request_text TEXT, blocking TEXT, status TEXT, not_applicable_reason TEXT,
  requested_at TEXT, satisfied_by_document_id TEXT, task_id TEXT,
  follow_up_round INTEGER);
CREATE TABLE IF NOT EXISTS received_documents (
  document_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, doc_type TEXT,
  obtained_how TEXT, obtained_at TEXT, furnished_by TEXT, channel TEXT,
  satisfies_request_id TEXT, classified_by TEXT, display_name TEXT,
  source_path TEXT, note TEXT);
-- plan_discount_pct/name/client_label are the RATE PLAN AS IT STOOD at issue.
-- Without them the discount was read live from rate_plans.yaml on every render,
-- so moving the household rate from 25% to 30% rewrote every household invoice
-- ever issued — an invoice the client paid 337.50 for came back saying 270.00.
-- An issued invoice states a transaction that already happened; no config edit
-- may change it.
CREATE TABLE IF NOT EXISTS invoices (
  invoice_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, plan_key TEXT,
  plan_basis TEXT, issued_on TEXT, due_on TEXT, paid_on TEXT, note TEXT,
  plan_discount_pct TEXT, plan_name TEXT, plan_client_label TEXT);
-- rate_adjusted says this line was priced AWAY from the catalogue, and it is
-- stored rather than re-derived because the catalogue hot-reloads: a rate that
-- moves next March must not retroactively turn an ordinary line into an adjusted
-- one. Dropping it lost the reduction REASON from summary_block() on every
-- reloaded invoice — so the printed copy and the covering email showed a smaller
-- number with no explanation, which is the one thing this module exists to stop.
CREATE TABLE IF NOT EXISTS invoice_lines (
  invoice_id TEXT, line_no INTEGER, service_code TEXT, label TEXT, quantity TEXT,
  standard_rate TEXT, note TEXT, performed_on TEXT, rate_adjusted INTEGER DEFAULT 0,
  PRIMARY KEY (invoice_id, line_no));
-- The payment ledger. payment_id is a content hash of the payment itself, so
-- PRIMARY KEY is what makes re-importing the same bank export a no-op instead
-- of a double count. invoice_id carries no FOREIGN KEY on purpose: an orphaned
-- attribution must still LOAD and be visible, not make the ledger unreadable.
-- sequence distinguishes two payments that are identical in every recorded
-- respect — two cheques, same morning, no reference. It is part of the hash, so
-- losing it here would silently merge them back together on the next reload.
CREATE TABLE IF NOT EXISTS payments (
  payment_id TEXT PRIMARY KEY, client_id TEXT, amount TEXT, received_on TEXT,
  method TEXT, reference TEXT, invoice_id TEXT, basis TEXT, note TEXT,
  sequence INTEGER DEFAULT 0);
-- What went OUT to the client. The outbound mirror of received_documents, and
-- the fact three derivations were waiting on: derive_stage cannot conclude
-- "delivered" without it, and refused to guess. deliverable_id is a content hash
-- of what was delivered, so recording the same delivery twice is once.
CREATE TABLE IF NOT EXISTS deliverables (
  deliverable_id TEXT PRIMARY KEY, client_id TEXT, tax_year INTEGER, kind TEXT,
  delivered_on TEXT, channel TEXT, delivered_by TEXT, return_key TEXT, note TEXT);
-- The record the autonomy ladder counts (docs/AUTONOMY-CHARTER.md §11): did the
-- owner send a rendered draft unchanged, or correct it, and why. approval_id is
-- a content hash of the decision itself (template, client, day, what was
-- rendered, what was sent, sequence) so logging the same decision twice is
-- once. reason carries a key from the five in satc.autonomy.approval.REASON_
-- CODES, or '' for an approval — never free text as the primary record. This
-- is a NEW table, so CREATE TABLE IF NOT EXISTS is the whole migration: an
-- existing store gets it created the next time it opens, same as every other
-- table here did when it was added. No ALTER is needed because there is no
-- existing table to alter.
CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY, template_key TEXT, client_id TEXT, decided_on TEXT,
  decided_by TEXT, rendered_hash TEXT, sent_hash TEXT, reason TEXT, note TEXT,
  sequence INTEGER DEFAULT 0, recorded_at TEXT);
CREATE TABLE IF NOT EXISTS filings (
  filing_id TEXT PRIMARY KEY, return_key TEXT, client_id TEXT, transmitted_at TEXT,
  transmitted_by TEXT, submission_id TEXT, ack_code TEXT, ack_date TEXT,
  reject_rule_id TEXT, reject_element TEXT, reject_message TEXT, attempt INTEGER,
  note TEXT);
CREATE TABLE IF NOT EXISTS relationships (
  rel_id TEXT PRIMARY KEY, from_client_id TEXT, to_client_id TEXT,
  relationship_type TEXT, ownership_pct TEXT, is_primary INTEGER, note TEXT);
-- A job carries NO stage column, and that is deliberate. The stage is DERIVED
-- from these rows by satc.work.stage.derive_stage; Job.stage is only ever a
-- cache of what that says, and a cache written to disk is a stale status field
-- wearing a new name (principle 3 — it lies the moment a document arrives).
-- What has to survive instead are the FACTS the derivation reads: every task's
-- status, audience, category, blocked_by and dates, below.
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY, client_id TEXT, workflow_key TEXT, engagement_type TEXT,
  tax_year INTEGER, period_key TEXT, due_date TEXT, intake_answers TEXT, risk_flags TEXT,
  created_at TEXT, updated_at TEXT, obligation_key TEXT);
CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY, job_id TEXT, template_id TEXT, title TEXT, category TEXT,
  audience TEXT, client_request_text TEXT, accepted_alternatives TEXT, why_needed TEXT,
  internal_instructions TEXT, suggested_date TEXT, status TEXT, notes TEXT,
  relationship_generated INTEGER, request_id TEXT, due_date TEXT, waived_reason TEXT,
  follow_up_round INTEGER, completed_by TEXT, completed_at TEXT, procedure TEXT,
  blocked_by TEXT, escalated_at TEXT);
CREATE TABLE IF NOT EXISTS workflow_overrides (
  workflow_key TEXT PRIMARY KEY, data TEXT);
-- Every movement in what the practice charges. NOT a mirror of
-- configs/billing/*.yaml — those files stay the source of truth and the owner
-- still edits them by hand — but the record of how they moved, which a file
-- cannot hold because a file only ever says what the price is now.
-- change_id is a content hash of the change itself, so recording the same
-- movement twice is once (principle 8).
-- changed_by is NULL when the author is genuinely unknown: an edit made outside
-- the app is recorded WITHOUT an author rather than credited to the engine that
-- noticed it. An ugly authorless row beats a gap, because a gap looks exactly
-- like nothing having happened.
-- not_before is the last date the OLD value was still on disk, so such an edit
-- is dated to an interval instead of to the day somebody opened the app.
-- recorded_at is when the ROW was written, not when the price moved: two
-- changes to the same service on one morning have no order without it, and
-- "what were we charging" would be answered by whichever hashed higher.
-- No client PII touches this table: subjects are catalogue codes.
CREATE TABLE IF NOT EXISTS price_changes (
  change_id TEXT PRIMARY KEY, kind TEXT, subject TEXT, field TEXT,
  old_value TEXT, new_value TEXT, changed_on TEXT, not_before TEXT,
  changed_by TEXT, note TEXT, recorded_at TEXT);
CREATE TABLE IF NOT EXISTS app_meta (k TEXT PRIMARY KEY, v TEXT);
-- THE AUTONOMY PRECONDITIONS GATE (charter §3): the three facts about the
-- MACHINE — an off-disk backup proven restorable, Tailnet Lock, MFA — that
-- have to hold before any streak anywhere is allowed to mean anything.
-- record_id is a content hash of what was confirmed (key, confirmed_on,
-- confirmed_by — see satc.autonomy.preconditions.precondition_id), so
-- recording the same day's confirmation twice (a reload, a double click)
-- lands on the same row rather than piling up (principle 8).
-- NOT client-scoped — this is a fact about the practice as a whole, not any
-- one client, so it is deliberately absent from _MART_TABLES_BY_CLIENT below.
-- This is a NEW table, so CREATE TABLE IF NOT EXISTS is the whole migration,
-- same reasoning as approvals above: an existing store gets it created the
-- next time it opens, and there is no existing table to ALTER.
-- MUST live here rather than a JSON file beside the store: `satc reset`
-- clears the databases in this directory and nothing else, and a file
-- living outside them is the one thing left standing after a reset wipes
-- everything this gate exists to hold back — verified as a real, durable
-- defect, not a theoretical one.
CREATE TABLE IF NOT EXISTS autonomy_preconditions (
  record_id TEXT PRIMARY KEY, key TEXT, confirmed_on TEXT,
  confirmed_by TEXT, note TEXT);
"""


def _d(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _pd(x: str | None) -> Decimal | None:
    return None if x in (None, "") else Decimal(x)


def _dt(x: date | None) -> str | None:
    return None if x is None else x.isoformat()


def _pdt(x: str | None) -> date | None:
    return None if x in (None, "") else date.fromisoformat(x)


# Every mart table keyed directly by client_id. A table missing from this list
# survives delete_client — which is not a tidiness problem: §10.28 requires
# returning a client's records, and a "deleted" client whose evidence rows are
# still on disk is a compliance defect, not a leak of disk space. New tables
# register HERE and nowhere else.
_MART_TABLES_BY_CLIENT = (
    "public_clients", "returns", "carryforwards", "owner_basis",
    "estimate_payments", "engagements", "jobs", "filings", "invoices",
    "payments", "deliverables", "requested_items", "received_documents",
    "approvals",
)

# Vault tables keyed by client_id.
_VAULT_TABLES_BY_CLIENT = ("identities", "vault_addresses", "vault_contacts")


def _ts(x) -> str | None:
    """A datetime -> ISO text. The store previously handled dates only."""
    return None if x is None else x.isoformat()


def _completion(row):
    """Rebuild a Completion from storage — history only, never a live actor."""
    from satc.models.work import Completion

    who = _pactor(_col(row, "completed_by"))
    when = _pts(_col(row, "completed_at"))
    if who is None or when is None:
        return None
    return Completion(by=who, at=when, procedure=_col(row, "procedure") or "")


def _pts(x: str | None):
    from datetime import datetime

    return None if x in (None, "") else datetime.fromisoformat(x)


def _col(row, name: str):
    """Read a column that may not exist on a store created by an older build.

    ``sqlite3.Row`` raises ``IndexError`` for an unknown key, and the migration
    runs at open time — but a row object held across a schema change would still
    blow up. Returning ``None`` keeps a load from failing on a column that is
    about to be added.
    """
    try:
        return row[name]
    except (IndexError, KeyError):
        return None


def _payment(row):
    """Rebuild a Payment from storage. Deliberately total — no row is refused.

    Every field comes back, including the two that carry the meaning and are the
    easiest to drop: the BASIS (how we know this payment belongs to that
    invoice) and the INVOICE_ID (empty when nobody has attributed it yet).
    """
    from satc.billing.payment import MatchBasis, Method, Payment

    problems: list[str] = []

    # TEXT in, Decimal out. A REAL column would round cents silently, and a
    # ledger that is out by a cent is a ledger nobody trusts.
    raw_amount = _col(row, "amount")
    try:
        amount = Decimal(str(raw_amount))
        if not amount.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ArithmeticError, ValueError, TypeError):
        # NEVER invented as zero and left looking ordinary (principle 1). Zero
        # keeps it out of every balance, and the note is what the owner sees.
        amount = Decimal("0.00")
        problems.append(f"amount unreadable in the store ({raw_amount!r}) — "
                        f"recorded as 0.00 until it is corrected")

    try:
        received_on = _pdt(_col(row, "received_on"))
    except (ValueError, TypeError):
        received_on = None
    if received_on is None:
        # A payment has to sit somewhere on a timeline for settled_on to mean
        # anything, and payment_id needs a date at all. The epoch is obviously
        # wrong on sight, which is the point — it reads as broken, not as a
        # plausible date somebody might act on.
        received_on = date(1970, 1, 1)
        problems.append(f"date unreadable in the store "
                        f"({_col(row, 'received_on')!r}) — shown as 1970-01-01")

    note = _col(row, "note") or ""
    if problems:
        note = " · ".join([note, *problems]) if note else " · ".join(problems)

    return Payment(
        client_id=_col(row, "client_id") or "",
        amount=amount,
        received_on=received_on,
        method=_penum(Method, _col(row, "method"), Method.OTHER),
        reference=_col(row, "reference") or "",
        # An invoice_id naming an invoice that no longer exists still loads. The
        # payment is a FACT; a stale attribution is something to SHOW the owner,
        # not a reason to hide the deposit.
        invoice_id=_col(row, "invoice_id") or "",
        basis=_penum(MatchBasis, _col(row, "basis"), MatchBasis.UNMATCHED),
        note=note,
        sequence=int(_col(row, "sequence") or 0))


def _enum(x) -> str:
    """An Enum member -> the stored value. Tolerates a bare string.

    Nothing stops a caller building a Payment with ``method="check"`` instead of
    ``Method.CHECK``, and a save that raised on it would lose the deposit over a
    type. Mirrors the same tolerance in satc.billing.payment.payment_id.
    """
    return str(getattr(x, "value", x) or "")


def _penum(kind, x, fallback):
    """A stored value -> its Enum member, for READING HISTORY ONLY.

    A value this build does not recognise — a renamed basis, a hand-edited row,
    a database from a newer version — must not stop the ledger loading. The
    refusals belong at reconciliation time, where a human is present to answer
    them, not at read time where there is only a stack trace (principle 5 is
    about not guessing, not about refusing to open the books).

    It comes back as the FALLBACK, which for a match basis is UNMATCHED: the
    weakest claim available, so an unreadable basis surfaces in the tray of
    payments nobody has attributed rather than passing as a match we cannot
    substantiate.
    """
    try:
        return kind(x)
    except ValueError:
        return fallback


def _actor(a) -> str | None:
    """An Actor -> its stable handle, for storage."""
    return None if a is None else a.handle


def _pactor(x: str | None):
    """A stored handle -> an Actor, for READING HISTORY ONLY.

    parse_handle never upgrades an unrecognised handle into a human, so a
    round-tripped actor cannot be used to assert humanity. See the warning in
    satc.models.actor.parse_handle: the result of this describes something that
    already happened and must never be passed into a gate as the actor
    performing a NEW act.
    """
    from satc.models.actor import parse_handle
    return None if x in (None, "") else parse_handle(x)


class SATCStore:
    """Facade over the vault + mart databases."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self.dir = Path(directory) if directory else DEFAULT_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        _restrict_dir(self.dir)
        vault_path = self.dir / "satc_vault.db"
        mart_path = self.dir / "satc_mart.db"
        self.vault = sqlite3.connect(vault_path, check_same_thread=False)
        self.mart = sqlite3.connect(mart_path, check_same_thread=False)
        for conn in (self.vault, self.mart):
            conn.row_factory = sqlite3.Row
        self.vault.executescript(_VAULT_DDL)
        self.mart.executescript(_MART_DDL)
        self.vault.commit()
        self.mart.commit()
        # Vault PII is encrypted at rest. The cipher's key is generated once and
        # sealed (DPAPI on Windows); see satc.persistence.crypto.
        self._cipher = open_cipher(self.dir)
        _restrict_file(vault_path)
        _restrict_file(mart_path)
        self._migrate()
        self._encrypt_vault_at_rest()

    def close(self) -> None:
        """Close both database connections.

        Long-lived in the app (one process, one store), but tests and any
        short-lived tool need this: on Windows an open SQLite handle keeps the
        file locked, so a temp directory cannot be cleaned up underneath it.
        Idempotent — closing twice is not an error.
        """
        for conn in (self.vault, self.mart):
            try:
                conn.close()
            except Exception:      # noqa: BLE001 - already closed is fine
                pass

    def __enter__(self) -> "SATCStore":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def _migrate(self) -> None:
        """Add columns introduced after a database was first created.

        ``CREATE TABLE IF NOT EXISTS`` never alters an existing table, so a store
        seeded by an older build is missing newer columns. Each migration is
        idempotent: skipped when the column is already present.
        """
        cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(public_clients)")}
        if "filing_status" not in cols:
            self.mart.execute("ALTER TABLE public_clients ADD COLUMN filing_status TEXT")
            self.mart.commit()

        # Provenance must survive a reload. Without these, Provenance was rebuilt
        # with produced_by=None on every load — and AppState.reload() runs after
        # EVERY mutation — so a model-produced value came back from SQLite
        # indistinguishable from a preparer entry, silently defeating the sticky
        # taint the staging gate depends on.
        li_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(line_items)")}
        for column in ("confidence", "produced_by", "document_id"):
            if column not in li_cols:
                self.mart.execute(f"ALTER TABLE line_items ADD COLUMN {column} TEXT")
        self.mart.commit()

        # The rate plan moved onto the engagement (the contract) from the
        # invoice. Positional INSERT means an older, narrower table would take
        # the plan key into a column that does not exist and fail the whole save.
        eng_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(engagements)")}
        for column in ("rate_plan_key", "rate_plan_basis"):
            if column not in eng_cols:
                self.mart.execute(f"ALTER TABLE engagements ADD COLUMN {column} TEXT")
        self.mart.commit()

        # The facts a job's STAGE is derived from. Without blocked_by, a task
        # waiting on earlier work in the same job came back off disk looking
        # startable — so a job the derivation calls "in_prep, waiting on its own
        # dependencies" read as ready to pick up, which is the optimistic
        # reading and the one that lets a return sit. obligation_key is the link
        # from a job to the duty it discharges, and escalated_at is when a chase
        # was escalated: both were written to nothing and silently lost.
        job_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(jobs)")}
        if "obligation_key" not in job_cols:
            self.mart.execute("ALTER TABLE jobs ADD COLUMN obligation_key TEXT")
        task_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(tasks)")}
        for column in ("blocked_by", "escalated_at"):
            if column not in task_cols:
                self.mart.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
        self.mart.commit()

        # MONEY COLUMNS ADDED AFTER THE FACT. Both of these were put in the DDL
        # and NOT here, which works perfectly on a fresh store and fails on every
        # existing one — and the tests all build fresh stores, so nothing caught
        # it. A live demo did, immediately: the positional INSERT supplied one
        # value too many, invoice_lines refused the whole write, and an invoice
        # was left ISSUED WITH NO LINES. A bill for zero pounds, in the register,
        # for work that was done.
        # The plan an invoice was ISSUED on. Same class of bug as the two below,
        # and the one with the worst consequence: without these an issued invoice
        # re-reads the live discount and silently restates what a client paid.
        inv_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(invoices)")}
        for column in ("plan_discount_pct", "plan_name", "plan_client_label"):
            if column not in inv_cols:
                self.mart.execute(f"ALTER TABLE invoices ADD COLUMN {column} TEXT")

        line_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(invoice_lines)")}
        if "rate_adjusted" not in line_cols:
            self.mart.execute(
                "ALTER TABLE invoice_lines ADD COLUMN rate_adjusted INTEGER DEFAULT 0")
        # recorded_at is what puts two same-day decisions in order — without it
        # a SHA-256 decides whether a correction demoted a pair or a later
        # approval accrued on top of it.
        apr_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(approvals)")}
        if apr_cols and "recorded_at" not in apr_cols:
            self.mart.execute("ALTER TABLE approvals ADD COLUMN recorded_at TEXT")

        pay_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(payments)")}
        if "sequence" not in pay_cols:
            self.mart.execute("ALTER TABLE payments ADD COLUMN sequence INTEGER DEFAULT 0")
        self.mart.commit()

        # THE PRICE RECORD. Every column is listed, not just the ones added
        # since — a table created by an earlier build is exactly what the DDL
        # above will not touch, and the two facts most likely to arrive late
        # here are the two that carry the honesty: not_before (an out-of-band
        # edit is dated to an interval) and note (why the author is blank).
        # Losing either turns "changed sometime that week, by we-do-not-know-who"
        # into a row that reads like an ordinary dated change nobody made.
        pc_cols = {r["name"] for r in self.mart.execute("PRAGMA table_info(price_changes)")}
        for column in ("kind", "subject", "field", "old_value", "new_value",
                       "changed_on", "not_before", "changed_by", "note",
                       "recorded_at"):
            if column not in pc_cols:
                self.mart.execute(f"ALTER TABLE price_changes ADD COLUMN {column} TEXT")
        self.mart.commit()

    def _encrypt_vault_at_rest(self) -> None:
        """Encrypt any legacy plaintext PII left by a pre-encryption build, then
        VACUUM so the old plaintext pages are reclaimed from the file (otherwise a
        freed page can still expose an SSN to ``strings``). Idempotent: rows already
        encrypted are unchanged, so this is a cheap no-op after the first run."""
        enc = self._cipher.encrypt
        changed = False

        def _rewrite(rows, table, pii_cols, key_cols):
            nonlocal changed
            for r in rows:
                current = [r[c] for c in pii_cols]
                new = [enc(v) for v in current]
                if new != current:
                    set_clause = ", ".join(f"{c}=?" for c in pii_cols)
                    where = " AND ".join(f"{k}=?" for k in key_cols)
                    self.vault.execute(f"UPDATE {table} SET {set_clause} WHERE {where}",
                                       (*new, *(r[k] for k in key_cols)))
                    changed = True

        _rewrite(self.vault.execute("SELECT * FROM identities").fetchall(),
                 "identities", ["legal_name", "tin"], ["client_id"])
        _rewrite(self.vault.execute("SELECT rowid, * FROM vault_addresses").fetchall(),
                 "vault_addresses", ["line1", "line2", "city", "state", "zip"], ["rowid"])
        _rewrite(self.vault.execute("SELECT rowid, * FROM vault_contacts").fetchall(),
                 "vault_contacts", ["name", "email", "phone"], ["rowid"])
        if changed:
            self.vault.commit()
            self.vault.execute("VACUUM")   # reclaim freelist pages holding old plaintext
            self.vault.commit()

    # -- lifecycle --------------------------------------------------------
    def is_empty(self) -> bool:
        return self.mart.execute("SELECT COUNT(*) FROM returns").fetchone()[0] == 0

    def get_meta(self, key: str) -> str | None:
        row = self.mart.execute("SELECT v FROM app_meta WHERE k=?", (key,)).fetchone()
        return row["v"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.mart.execute("INSERT OR REPLACE INTO app_meta VALUES (?,?)", (key, value))
        self.mart.commit()

    def seed_if_empty(self) -> bool:
        """Seed the built-in sample data once. Never re-seeds after the first run.

        The ``sample_seeded`` marker means a later "clear sample data" stays cleared
        across restarts instead of the empty store being re-seeded.
        """
        if self.get_meta("sample_seeded"):
            return False
        if not self.is_empty():
            self.set_meta("sample_seeded", "1")   # pre-existing store: adopt, don't re-seed
            return False
        for rec in synthetic_identities():
            self.upsert_identity(rec)
        self.save_mart(synthetic_mart())
        self.set_meta("sample_seeded", "1")
        return True

    # -- vault ------------------------------------------------------------
    def upsert_identity(self, rec: IdentityRecord) -> None:
        enc = self._cipher.encrypt
        self.vault.execute(
            "INSERT OR REPLACE INTO identities VALUES (?,?,?,?)",
            (rec.client_id, rec.entity_type, enc(rec.legal_name), enc(rec.tin)))
        self.vault.execute("DELETE FROM vault_addresses WHERE client_id=?", (rec.client_id,))
        for a in rec.addresses:
            self.vault.execute("INSERT INTO vault_addresses VALUES (?,?,?,?,?,?)",
                               (rec.client_id, enc(a.line1), enc(a.line2), enc(a.city),
                                enc(a.state), enc(a.zip)))
        self.vault.execute("DELETE FROM vault_contacts WHERE client_id=?", (rec.client_id,))
        for c in rec.contacts:
            self.vault.execute("INSERT INTO vault_contacts VALUES (?,?,?,?,?)",
                               (rec.client_id, enc(c.name), enc(c.email), enc(c.phone), c.role))
        self.vault.commit()

    def names(self) -> dict[str, str]:
        return {r["client_id"]: self._cipher.decrypt(r["legal_name"])
                for r in self.vault.execute("SELECT client_id, legal_name FROM identities")}

    def client_email(self, client_id: str) -> str:
        """First non-empty contact email for a client (from the vault), or ``""``.

        Empty emails stay empty ciphertext-free (see VaultCipher), so the
        ``email!=''`` filter still selects only rows that actually have one.
        """
        row = self.vault.execute(
            "SELECT email FROM vault_contacts WHERE client_id=? AND email!='' LIMIT 1",
            (client_id,)).fetchone()
        return self._cipher.decrypt(row["email"]) if row else ""

    # -- mart write -------------------------------------------------------
    def save_mart(self, mart: DataMart) -> None:
        m = self.mart
        for pc in mart.public_clients:
            m.execute("INSERT OR REPLACE INTO public_clients VALUES (?,?,?,?,?,?,?,?)",
                      (pc.client_id, pc.entity_type, pc.display_label, pc.tin_last4,
                       pc.tin_masked, pc.default_return_type, pc.home_state,
                       getattr(pc, "filing_status", "") or ""))
        for r in mart.returns:
            m.execute("INSERT OR REPLACE INTO returns VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (r.return_key, r.client_id, r.tax_year, r.return_type, r.jurisdiction,
                       r.preparer_id, r.residency, _d(r.refund_amount),
                       _d(r.balance_due_amount), r.note))
        for li in mart.line_items:
            prov = li.provenance
            ref = prov.source_ref if prov else None
            m.execute("INSERT OR REPLACE INTO line_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (li.line_item_key, li.return_key, li.schedule, li.line_code, li.label,
                       _d(li.amount), li.text_value,
                       prov.source_kind if prov else "",
                       # Citation is a TAX-LAW citation, never a filename. The
                       # document is referenced by id in its own column so the
                       # evidence chain survives without a client filename
                       # reaching the exported workbook.
                       (ref.citation or "") if ref else "",
                       prov.confidence if prov else "",
                       _actor(prov.produced_by) if prov else None,
                       (ref.document_id or "") if ref else ""))
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
            m.execute("INSERT OR REPLACE INTO engagements VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (e.client_id, e.tax_year, e.engagement_letter_status, _d(e.fee_amount),
                       int(e.invoiced), int(e.paid), e.preparer_id, e.note,
                       e.rate_plan_key, e.rate_plan_basis))
        self.save_requested_items(mart.requested_items)
        self.save_received_documents(mart.received_documents)
        m.commit()

    def delete_intake_line_items(self, return_key: str) -> None:
        """Remove intake-sourced (SOURCE_DOC) line items for a return.

        Lets ``post_confirmed`` *replace* a return's intake posting rather than
        accumulate it (``save_mart`` only upserts, so a line dropped from the gate
        would otherwise linger). Drake-output, carryforward, and preparer lines on
        the same return are left untouched.
        """
        self.mart.execute("DELETE FROM line_items WHERE return_key=? AND source_kind=?",
                          (return_key, "SOURCE_DOC"))
        self.mart.commit()

    def set_filing_status(self, client_id: str, filing_status: str) -> None:
        """Record a client's last-known filing status (non-PII; lives in the mart)."""
        self.mart.execute("UPDATE public_clients SET filing_status=? WHERE client_id=?",
                          (filing_status, client_id))
        self.mart.commit()

    # -- invoices ---------------------------------------------------------

    def save_invoices(self, invoices) -> None:
        """An invoice and its lines are ONE fact, so they are written as one.

        They were not, and a schema mismatch proved why: the invoice row wrote,
        the lines raised, and what stayed on disk was an ISSUED INVOICE WITH NO
        LINES — a bill for zero against work that had been done, sitting in the
        register looking exactly like an ordinary one. An invoice without its
        lines is not a partial record, it is a wrong one, so a failure anywhere
        in here leaves nothing behind.
        """
        try:
            self._write_invoices(invoices)
        except Exception:
            self.mart.rollback()
            raise

    def _write_invoices(self, invoices) -> None:
        for inv in invoices:
            self.mart.execute(
                "INSERT OR REPLACE INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (inv.invoice_id, inv.client_id, inv.tax_year, inv.plan_key,
                 inv.plan_basis, _dt(inv.issued_on), _dt(inv.due_on),
                 _dt(inv.paid_on), inv.note,
                 None if inv.plan_discount_pct is None else str(inv.plan_discount_pct),
                 inv.plan_name, inv.plan_client_label))
            self.mart.execute("DELETE FROM invoice_lines WHERE invoice_id=?",
                              (inv.invoice_id,))
            for n, line in enumerate(inv.lines):
                self.mart.execute(
                    "INSERT OR REPLACE INTO invoice_lines VALUES (?,?,?,?,?,?,?,?,?)",
                    (inv.invoice_id, n, line.service_code, line.label,
                     str(line.quantity), str(line.standard_rate), line.note,
                     _dt(line.performed_on), int(bool(line.rate_adjusted))))
        self.mart.commit()

    def load_invoices(self, client_id: str = "") -> list:
        from decimal import Decimal

        from satc.billing.invoice import Invoice, InvoiceLine

        lines_by_invoice: dict[str, list] = {}
        for r in self.mart.execute("SELECT * FROM invoice_lines ORDER BY invoice_id, line_no"):
            lines_by_invoice.setdefault(r["invoice_id"], []).append(InvoiceLine(
                service_code=r["service_code"], label=r["label"],
                quantity=Decimal(r["quantity"] or "1"),
                standard_rate=Decimal(r["standard_rate"] or "0"),
                note=r["note"] or "", performed_on=_pdt(r["performed_on"]),
                # _col, not r[...]: an invoice written by a build before this
                # column existed must still load.
                rate_adjusted=bool(_col(r, "rate_adjusted") or 0)))

        sql = "SELECT * FROM invoices"
        args: tuple = ()
        if client_id:
            sql += " WHERE client_id=?"
            args = (client_id,)
        return [Invoice(
            invoice_id=r["invoice_id"], client_id=r["client_id"],
            tax_year=r["tax_year"], plan_key=r["plan_key"] or "standard",
            plan_basis=r["plan_basis"] or "", issued_on=_pdt(r["issued_on"]),
            due_on=_pdt(r["due_on"]), paid_on=_pdt(r["paid_on"]),
            lines=lines_by_invoice.get(r["invoice_id"], []), note=r["note"] or "",
            # _col, not r[...]: an invoice written before these columns existed
            # must still load. It comes back with no stamped plan and therefore
            # falls back to the live catalogue — which is the old behaviour, and
            # is the honest answer for a record that never captured one.
            plan_discount_pct=_pd(_col(r, "plan_discount_pct")),
            plan_name=_col(r, "plan_name") or "",
            plan_client_label=_col(r, "plan_client_label") or "")
            for r in self.mart.execute(sql + " ORDER BY invoice_id", args)]

    # -- payments (the ledger behind "paid") -------------------------------

    def save_payments(self, payments) -> None:
        """Record money that arrived. Idempotent on ``payment_id``.

        ``Payment.payment_id`` is derived from the payment itself — client,
        amount, date, method, reference, sequence — so the same deposit written
        twice lands on the same primary key and REPLACES its row instead of
        becoming a second one. That is the whole defence against a re-imported
        bank export double-counting the practice's revenue (principle 8), and it
        is why this is an upsert and not an append.

        Attributing a payment does NOT change its id, so reconciling one updates
        its row rather than filing a second copy of the same money. Two payments
        that are genuinely separate but identical on paper differ by ``sequence``
        — see ``Payment.as_another_one``, which a human has to ask for.
        """
        for p in payments:
            self.mart.execute(
                "INSERT OR REPLACE INTO payments VALUES (?,?,?,?,?,?,?,?,?,?)",
                (p.payment_id, p.client_id, _d(p.amount), _dt(p.received_on),
                 _enum(p.method), p.reference, p.invoice_id, _enum(p.basis),
                 p.note, int(p.sequence)))
        self.mart.commit()

    def load_payments(self, client_id: str = "") -> list:
        """The ledger back off disk. Never raises on a row it finds odd.

        The BASIS round-trips with the payment because "how do we know this
        belongs to that invoice" outlives "what we concluded" — principle 2. A
        payment that came back having forgotten it was CHOSEN_BY_MODEL rather
        than named by its REFERENCE would have lost the only fact that lets a
        later reviewer tell a machine's guess from the bank's own statement.
        """
        sql = "SELECT * FROM payments"
        args: tuple = ()
        if client_id:
            sql += " WHERE client_id=?"
            args = (client_id,)
        return [_payment(r) for r in self.mart.execute(
            sql + " ORDER BY received_on, payment_id", args)]

    def load_unmatched_payments(self, client_id: str = "") -> list:
        """Money that arrived and has not been attributed to anything.

        This is the tray the owner actually works through, so it is asked for
        by the database rather than by loading the whole ledger and filtering —
        it is read on every reconciliation screen.

        "Unmatched" here is exactly ``not Payment.is_matched``: no invoice_id,
        or a basis that does not attribute (UNMATCHED, or a value this build
        cannot read — see ``_penum``). The attributing bases are taken from the
        enum rather than spelled out, so adding a rung to the ladder cannot
        leave this query quietly disagreeing with the model.
        """
        from satc.billing.payment import MatchBasis

        attributing = [b.value for b in MatchBasis if b is not MatchBasis.UNMATCHED]
        holes = ",".join("?" * len(attributing))
        sql = (f"SELECT * FROM payments WHERE (invoice_id IS NULL OR invoice_id=''"
               f" OR basis IS NULL OR basis NOT IN ({holes}))")
        args: list = list(attributing)
        if client_id:
            sql += " AND client_id=?"
            args.append(client_id)
        # Decoded by the same function as load_payments, so the tray and the
        # ledger can never disagree about what a row says.
        return [_payment(r) for r in self.mart.execute(
            sql + " ORDER BY received_on, payment_id", tuple(args))]

    # -- the price record (what the practice charges, and when it moved) ----

    _PRICE_COLUMNS = ("change_id", "kind", "subject", "field", "old_value",
                      "new_value", "changed_on", "not_before", "changed_by",
                      "note", "recorded_at")

    def save_price_changes(self, changes) -> None:
        """Record price movements. Idempotent on the content-derived change_id.

        The columns are NAMED rather than positional, which every other table
        here does not do — because this one has a migration that appends columns
        to a table an earlier build created. After an ALTER, the physical column
        order is creation order, not DDL order, and a positional INSERT would
        quietly file the actor's handle in ``not_before``. That is the same
        family of bug as the invoice_lines one, one step further along: the
        write succeeds, and the row is wrong.
        """
        holes = ",".join("?" * len(self._PRICE_COLUMNS))
        sql = (f"INSERT OR REPLACE INTO price_changes "
               f"({','.join(self._PRICE_COLUMNS)}) VALUES ({holes})")
        for c in changes:
            self.mart.execute(sql, (
                c.change_id, c.kind, c.subject, c.field, c.old_value, c.new_value,
                _dt(c.changed_on), _dt(c.not_before), _actor(c.changed_by), c.note,
                _ts(c.recorded_at)))
        self.mart.commit()

    def load_price_changes(self, subject: str = "") -> list:
        """The price record back off disk, oldest first.

        ``changed_by`` comes back as None when the column is NULL and STAYS
        None: an edit made outside the app has no author, and _pactor turning a
        blank into a system actor would put a name on the one row whose whole
        point is that nobody knows whose it is.
        """
        from satc.billing.history import PriceChange

        def _when(value):
            """A hand-edited date must not take the price screen down with it."""
            try:
                return _pdt(value)
            except (ValueError, TypeError):
                return None

        def _stamp(value):
            try:
                return _pts(value)
            except (ValueError, TypeError):
                return None

        sql = "SELECT * FROM price_changes"
        args: tuple = ()
        if subject:
            sql += " WHERE subject=?"
            args = (subject,)
        return [PriceChange(
            kind=_col(r, "kind") or "", subject=_col(r, "subject") or "",
            field=_col(r, "field") or "",
            old_value=_col(r, "old_value"), new_value=_col(r, "new_value"),
            # A change with no date could not be placed on a timeline at all, so
            # it is not silently dated today — the epoch reads as broken on
            # sight, which is what a row this damaged should look like.
            changed_on=_when(_col(r, "changed_on")) or date(1970, 1, 1),
            changed_by=_pactor(_col(r, "changed_by")),
            note=_col(r, "note") or "",
            not_before=_when(_col(r, "not_before")),
            recorded_at=_stamp(_col(r, "recorded_at")))
            for r in self.mart.execute(
                sql + " ORDER BY changed_on, recorded_at, change_id", args)]

    # -- filings (many per return) ----------------------------------------

    # -- deliverables (what went OUT) --------------------------------------

    def save_deliverables(self, deliverables) -> None:
        """Record what was sent. Idempotent on the content-derived id.

        The owner checking whether they already sent something, and then sending
        it, must not produce two deliveries — and a second delivery would move
        the settled_on of any promise measured from it (principle 8).
        """
        for d in deliverables:
            self.mart.execute(
                "INSERT OR REPLACE INTO deliverables VALUES (?,?,?,?,?,?,?,?,?)",
                (d.deliverable_id, d.client_id, int(d.tax_year), str(d.kind),
                 _dt(d.delivered_on), str(d.channel), d.delivered_by,
                 d.return_key, d.note))
        self.mart.commit()

    def load_deliverables(self, client_id: str = "") -> list:
        """What has gone out. Never raises on a row it finds odd.

        A deliverable naming a return that no longer exists still loads, for the
        same reason an orphaned payment attribution does: it is a FACT about
        something the practice did, and hiding it would lose the record of an
        act rather than tidy it.
        """
        from satc.models.deliverable import Deliverable

        sql = "SELECT * FROM deliverables"
        args: tuple = ()
        if client_id:
            sql += " WHERE client_id=?"
            args = (client_id,)
        out = []
        for r in self.mart.execute(sql + " ORDER BY delivered_on, deliverable_id", args):
            on = _pdt(_col(r, "delivered_on"))
            if on is None:
                # Obviously wrong on sight rather than plausible — a delivery
                # with no date cannot anchor a promise, and must not look as
                # though it can (principle 1).
                on = date(1970, 1, 1)
            out.append(Deliverable(
                client_id=_col(r, "client_id") or "",
                tax_year=int(_col(r, "tax_year") or 0),
                kind=_col(r, "kind") or "letter",
                delivered_on=on, channel=_col(r, "channel") or "portal",
                delivered_by=_col(r, "delivered_by") or "",
                return_key=_col(r, "return_key") or "",
                note=_col(r, "note") or ""))
        return out

    # -- approvals (charter §11 — the record the autonomy ladder counts) ---

    def save_approvals(self, approvals) -> None:
        """Record owner decisions on rendered drafts. Idempotent on ``approval_id``.

        ``Approval.approval_id`` is derived from the decision itself — template,
        client, day, what was rendered, what was sent, sequence — so the same
        decision written twice (a double-click, a re-import) lands on the same
        primary key and REPLACES its row rather than becoming a second one
        (principle 8). That includes a reason code being reclassified for the
        same decision: the row updates in place, because ``reason`` is not part
        of the id (see the note on ``approval_id``).
        """
        for a in approvals:
            self.mart.execute(
                "INSERT OR REPLACE INTO approvals "
                "(approval_id, template_key, client_id, decided_on, decided_by,"
                " rendered_hash, sent_hash, reason, note, sequence, recorded_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (a.approval_id, a.template_key, a.client_id, _dt(a.decided_on),
                 a.decided_by, a.rendered_hash, a.sent_hash, a.reason, a.note,
                 int(a.sequence), _ts(a.recorded_at)))
        self.mart.commit()

    def load_approvals(self, client_id: str = "") -> list:
        """The whole decision record back off disk. Never raises on a row it finds odd.

        An approval naming a template that no longer exists still loads — it is
        a FACT about something that happened, and hiding it would lose the
        record of an act rather than tidy it (same reasoning as an orphaned
        payment attribution or deliverable). Any refusal about an unknown
        template belongs at ``record_approval``/``record_correction`` time,
        where a human is present to fix it, not here.
        """
        from satc.autonomy.approval import Approval

        sql = "SELECT * FROM approvals"
        args: tuple = ()
        if client_id:
            sql += " WHERE client_id=?"
            args = (client_id,)
        out = []
        for r in self.mart.execute(sql + " ORDER BY decided_on, approval_id", args):
            on = _pdt(_col(r, "decided_on"))
            if on is None:
                # Obviously wrong on sight rather than plausible — a decision
                # with no date cannot sit on the streak timeline, and must not
                # look as though it can (principle 1).
                on = date(1970, 1, 1)
            out.append(Approval(
                template_key=_col(r, "template_key") or "",
                client_id=_col(r, "client_id") or "",
                decided_on=on, decided_by=_col(r, "decided_by") or "",
                rendered_hash=_col(r, "rendered_hash") or "",
                sent_hash=_col(r, "sent_hash") or "",
                reason=_col(r, "reason") or "", note=_col(r, "note") or "",
                sequence=int(_col(r, "sequence") or 0),
                # None on a row written before the column existed. all_approvals
                # sorts those first within their day — the honest place for
                # "we do not know when".
                recorded_at=_pts(_col(r, "recorded_at"))))
        return out

    # -- autonomy preconditions (charter §3 — the gate the ladder is held on) --

    def save_preconditions(self, records) -> None:
        """Record precondition confirmations. Idempotent on ``record_id``
        (principle 8): the same confirmation written twice — a reload, a
        double click, a re-import of the legacy JSON ledger — REPLACES its
        row rather than becoming a second one, exactly like ``save_approvals``.
        """
        for r in records:
            self.mart.execute(
                "INSERT OR REPLACE INTO autonomy_preconditions "
                "(record_id, key, confirmed_on, confirmed_by, note) VALUES (?,?,?,?,?)",
                (r.record_id, r.key, _dt(r.confirmed_on), r.confirmed_by, r.note))
        self.mart.commit()

    def load_preconditions(self) -> list:
        """Every recorded precondition confirmation, oldest first.

        Never raises on a row it finds odd — same discipline as
        :meth:`load_approvals`: a row this store cannot make sense of is
        skipped rather than believed or allowed to take the whole load down.
        """
        from satc.autonomy.preconditions import PreconditionRecord

        out = []
        for r in self.mart.execute(
                "SELECT * FROM autonomy_preconditions ORDER BY confirmed_on, key"):
            on = _pdt(_col(r, "confirmed_on"))
            key = _col(r, "key")
            if on is None or not key:
                continue
            try:
                out.append(PreconditionRecord(
                    key=key, confirmed_on=on,
                    confirmed_by=_col(r, "confirmed_by") or "",
                    note=_col(r, "note") or ""))
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def save_filings(self, filings) -> None:
        for f in filings:
            self.mart.execute(
                "INSERT OR REPLACE INTO filings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f.filing_id, f.return_key, f.client_id, _ts(f.transmitted_at),
                 _actor(f.transmitted_by), f.submission_id, f.ack_code,
                 _dt(f.ack_date), f.reject_rule_id, f.reject_element,
                 f.reject_message, int(f.attempt), f.note))
        self.mart.commit()

    def load_filings(self, return_key: str = "") -> list:
        from satc.models.filing import Filing

        sql = "SELECT * FROM filings"
        args: tuple = ()
        if return_key:
            sql += " WHERE return_key=?"
            args = (return_key,)
        sql += " ORDER BY attempt, filing_id"
        return [Filing(
            filing_id=r["filing_id"], return_key=r["return_key"], client_id=r["client_id"],
            transmitted_at=_pts(r["transmitted_at"]),
            transmitted_by=_pactor(r["transmitted_by"]),
            submission_id=r["submission_id"] or "", ack_code=r["ack_code"] or "",
            ack_date=_pdt(r["ack_date"]), reject_rule_id=r["reject_rule_id"] or "",
            reject_element=r["reject_element"] or "",
            reject_message=r["reject_message"] or "", attempt=r["attempt"] or 1,
            note=r["note"] or "") for r in self.mart.execute(sql, args)]

    # -- evidence (requested items + received documents) ------------------

    def save_requested_items(self, items) -> None:
        for i in items:
            self.mart.execute(
                "INSERT OR REPLACE INTO requested_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (i.request_id, i.client_id, i.tax_year, i.doc_type, i.request_text,
                 i.blocking, i.status, i.not_applicable_reason, _dt(i.requested_at),
                 i.satisfied_by_document_id, i.task_id, int(i.follow_up_round)))
        self.mart.commit()

    def load_requested_items(self, client_id: str = "") -> list:
        from satc.models.evidence import RequestedItem

        sql = "SELECT * FROM requested_items"
        args: tuple = ()
        if client_id:
            sql += " WHERE client_id=?"
            args = (client_id,)
        return [RequestedItem(
            request_id=r["request_id"], client_id=r["client_id"], tax_year=r["tax_year"],
            doc_type=r["doc_type"], request_text=r["request_text"] or "",
            blocking=r["blocking"] or "non_blocking", status=r["status"] or "outstanding",
            not_applicable_reason=r["not_applicable_reason"] or "",
            requested_at=_pdt(r["requested_at"]),
            satisfied_by_document_id=r["satisfied_by_document_id"] or "",
            task_id=r["task_id"] or "", follow_up_round=r["follow_up_round"] or 0)
            for r in self.mart.execute(sql, args)]

    def save_received_documents(self, docs) -> None:
        for d in docs:
            self.mart.execute(
                "INSERT OR REPLACE INTO received_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d.document_id, d.client_id, d.tax_year, d.doc_type, d.obtained_how,
                 _ts(d.obtained_at), d.furnished_by, d.channel, d.satisfies_request_id,
                 _actor(d.classified_by), d.display_name, d.source_path, d.note))
        self.mart.commit()

    def load_received_documents(self, client_id: str = "") -> list:
        from satc.models.evidence import ReceivedDocument

        sql = "SELECT * FROM received_documents"
        args: tuple = ()
        if client_id:
            sql += " WHERE client_id=?"
            args = (client_id,)
        return [ReceivedDocument(
            document_id=r["document_id"], client_id=r["client_id"], tax_year=r["tax_year"],
            doc_type=r["doc_type"], obtained_how=r["obtained_how"] or "unknown",
            obtained_at=_pts(r["obtained_at"]), furnished_by=r["furnished_by"] or "",
            channel=r["channel"] or "", satisfies_request_id=r["satisfies_request_id"] or "",
            classified_by=_pactor(r["classified_by"]), display_name=r["display_name"] or "",
            source_path=r["source_path"] or "", note=r["note"] or "")
            for r in self.mart.execute(sql, args)]

    def delete_client(self, client_id: str) -> None:
        """Remove a client everywhere — vault identity + every mart row keyed to it.

        Used to discard a mistakenly-added client and to clear the built-in sample
        clients. Engagement tasks are removed via their parent engagements.
        """
        return_keys = [r["return_key"] for r in self.mart.execute(
            "SELECT return_key FROM returns WHERE client_id=?", (client_id,))]
        eng_ids = [r["job_id"] for r in self.mart.execute(
            "SELECT job_id FROM jobs WHERE client_id=?", (client_id,))]
        for rk in return_keys:
            self.mart.execute("DELETE FROM line_items WHERE return_key=?", (rk,))
        for eid in eng_ids:
            self.mart.execute("DELETE FROM tasks WHERE job_id=?", (eid,))
        for table in _MART_TABLES_BY_CLIENT:
            self.mart.execute(f"DELETE FROM {table} WHERE client_id=?", (client_id,))
        self.mart.execute("DELETE FROM relationships WHERE from_client_id=? OR to_client_id=?",
                          (client_id, client_id))
        self.mart.commit()
        for table in _VAULT_TABLES_BY_CLIENT:
            self.vault.execute(f"DELETE FROM {table} WHERE client_id=?", (client_id,))
        self.vault.commit()

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

    def save_job(self, eng: Job) -> None:
        """Persist a job and (replace) its task list.

        Columns are NAMED rather than positional. A positional INSERT is only
        correct while the DDL's column order and the migration's order agree,
        and nothing forces them to: ``ALTER TABLE`` can only append, so a column
        added to the middle of the DDL — the natural place to put it, next to
        the ones it belongs with — lands at the END of every store that already
        exists. The two orders would then differ by build age, and each value
        would be written into its neighbour's column on exactly the machines
        that have history on them. Naming the columns removes the coupling
        rather than asking the next person to remember it.

        ``stage`` is not written, and there is no column for it. See the note on
        the jobs table: what the store owes the derivation is the facts, not the
        conclusion.
        """
        self.mart.execute(
            "INSERT OR REPLACE INTO jobs "
            "(job_id, client_id, workflow_key, engagement_type, tax_year, period_key,"
            " due_date, intake_answers, risk_flags, created_at, updated_at, obligation_key)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (eng.job_id, eng.client_id, eng.workflow_key, eng.engagement_type,
             eng.tax_year, eng.period_key, _dt(eng.due_date),
             json.dumps(eng.intake_answers), json.dumps(eng.risk_flags),
             eng.created_at, eng.updated_at, eng.obligation_key))
        self.mart.execute("DELETE FROM tasks WHERE job_id=?", (eng.job_id,))
        for t in eng.tasks:
            self._insert_task(t)
        self.mart.commit()

    def _insert_task(self, t: Task) -> None:
        c = t.completion
        self.mart.execute(
            "INSERT OR REPLACE INTO tasks "
            "(task_id, job_id, template_id, title, category, audience,"
            " client_request_text, accepted_alternatives, why_needed,"
            " internal_instructions, suggested_date, status, notes,"
            " relationship_generated, request_id, due_date, waived_reason,"
            " follow_up_round, completed_by, completed_at, procedure,"
            " blocked_by, escalated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t.task_id, t.job_id, t.template_id, t.title, t.category, t.audience,
             t.client_request_text, t.accepted_alternatives, t.why_needed,
             t.internal_instructions, _dt(t.suggested_date), t.status, t.notes,
             int(t.relationship_generated), t.request_id, _dt(t.due_date),
             t.waived_reason, int(t.follow_up_round),
             _actor(c.by) if c else None, _ts(c.at) if c else None,
             c.procedure if c else "",
             # JSON, not a delimited string: a task title is free text and can
             # contain whatever separator we picked.
             json.dumps(list(t.blocked_by)), _dt(t.escalated_at)))

    def save_task(self, t: Task) -> None:
        self._insert_task(t)
        self.mart.commit()

    # -- questionnaire (workflow) overrides -------------------------------
    def save_workflow_override(self, workflow_key: str, data: dict) -> None:
        self.mart.execute("INSERT OR REPLACE INTO workflow_overrides VALUES (?,?)",
                          (workflow_key, json.dumps(data)))
        self.mart.commit()

    def load_workflow_override(self, workflow_key: str) -> dict | None:
        row = self.mart.execute("SELECT data FROM workflow_overrides WHERE workflow_key=?",
                                (workflow_key,)).fetchone()
        return json.loads(row["data"]) if row else None

    def workflow_override_keys(self) -> set[str]:
        return {r["workflow_key"]
                for r in self.mart.execute("SELECT workflow_key FROM workflow_overrides")}

    def load_jobs(self) -> list[Job]:
        """Every job with its tasks. ``Job.stage`` comes back at its default.

        Nothing is restored into it because nothing is stored: ask
        :func:`satc.work.stage.derive_stage` where a loaded job stands. Every
        fact that derivation reads — each task's status, audience, category,
        ``blocked_by`` and dates — is rebuilt here.
        """
        tasks_by_eng: dict[str, list[Task]] = {}
        for r in self.mart.execute("SELECT * FROM tasks ORDER BY suggested_date, task_id"):
            tasks_by_eng.setdefault(r["job_id"], []).append(Task(
                task_id=r["task_id"], job_id=r["job_id"], template_id=r["template_id"],
                title=r["title"], category=r["category"], audience=r["audience"],
                client_request_text=r["client_request_text"] or "",
                accepted_alternatives=r["accepted_alternatives"] or "",
                why_needed=r["why_needed"] or "", internal_instructions=r["internal_instructions"] or "",
                suggested_date=_pdt(r["suggested_date"]),
                status=r["status"] or "not_started",
                notes=r["notes"] or "", relationship_generated=bool(r["relationship_generated"]),
                request_id=_col(r, "request_id") or "",
                due_date=_pdt(_col(r, "due_date")),
                waived_reason=_col(r, "waived_reason") or "",
                follow_up_round=_col(r, "follow_up_round") or 0,
                # A tuple, because that is what Task declares and what
                # derive_stage tests for truthiness. A legacy row has NULL here,
                # which is "nobody recorded a dependency" — the same thing an
                # empty list means, and the only reading available.
                blocked_by=tuple(json.loads(_col(r, "blocked_by") or "[]")),
                escalated_at=_pdt(_col(r, "escalated_at")),
                completion=_completion(r)))
        return [Job(
            job_id=r["job_id"], client_id=r["client_id"], workflow_key=r["workflow_key"],
            engagement_type=r["engagement_type"], tax_year=r["tax_year"],
            obligation_key=_col(r, "obligation_key") or "",
            period_key=_col(r, "period_key") or "",
            due_date=_pdt(r["due_date"]), intake_answers=json.loads(r["intake_answers"] or "{}"),
            risk_flags=json.loads(r["risk_flags"] or "[]"), created_at=r["created_at"] or "",
            updated_at=r["updated_at"] or "", tasks=tasks_by_eng.get(r["job_id"], []))
            for r in self.mart.execute("SELECT * FROM jobs ORDER BY created_at")]

    # -- mart read --------------------------------------------------------
    def load_mart(self) -> DataMart:
        m = self.mart
        mart = DataMart()
        mart.public_clients = [PublicClient(
            client_id=r["client_id"], entity_type=r["entity_type"], display_label=r["display_label"],
            tin_last4=r["tin_last4"], tin_masked=r["tin_masked"],
            default_return_type=r["default_return_type"], home_state=r["home_state"],
            filing_status=(r["filing_status"] or "" if "filing_status" in r.keys() else ""))
            for r in m.execute("SELECT * FROM public_clients ORDER BY client_id")]
        mart.returns = [ReturnRecord(
            return_key=r["return_key"], client_id=r["client_id"], tax_year=r["tax_year"],
            return_type=r["return_type"], jurisdiction=r["jurisdiction"],
            preparer_id=r["preparer_id"], residency=r["residency"],
            refund_amount=_pd(r["refund_amount"]), balance_due_amount=_pd(r["balance_due_amount"]),
            note=r["note"]) for r in m.execute("SELECT * FROM returns ORDER BY tax_year, return_key")]
        mart.line_items = [LineItem(
            line_item_key=r["line_item_key"], return_key=r["return_key"], schedule=r["schedule"],
            line_code=r["line_code"], label=r["label"], amount=_pd(r["amount"]),
            text_value=r["text_value"] or "",
            provenance=Provenance(
                source_kind=r["source_kind"] or "COMPUTED",
                confidence=_col(r, "confidence") or "HIGH",
                produced_by=_pactor(_col(r, "produced_by")),
                source_ref=SourceRef(citation=r["citation"] or "",
                                     document_id=_col(r, "document_id") or None)))
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
        mart.engagements = [Engagement(
            client_id=r["client_id"], tax_year=r["tax_year"],
            engagement_letter_status=r["engagement_letter_status"], fee_amount=_pd(r["fee_amount"]),
            invoiced=bool(r["invoiced"]), paid=bool(r["paid"]), preparer_id=r["preparer_id"],
            note=r["note"],
            # A row written before the rate plan lived on the contract has NULL
            # here. It reads back BLANK rather than "standard": nobody agreed a
            # plan on it, and rate_plan_for reports a blank key as a fallback,
            # not as a decision.
            rate_plan_key=_col(r, "rate_plan_key") or "",
            rate_plan_basis=_col(r, "rate_plan_basis") or "")
            for r in m.execute("SELECT * FROM engagements")]
        mart.requested_items = self.load_requested_items()
        mart.received_documents = self.load_received_documents()
        return mart

    def close(self) -> None:
        self.vault.close()
        self.mart.close()
