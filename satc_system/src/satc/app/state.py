"""Application state for the SATC prototype — backed by the SQLite store.

The durable data (clients, returns, documents, statuses, line items,
carryforwards, engagements) lives in the SQLite store and survives restarts. The
staging gate is a per-session working area, re-derived from the documents on
hand. This is the vault-side UI, so it may resolve client_id -> name from the
vault for display; everything it persists to the mart is de-identified.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from satc.config import load_extraction_map
from satc.fixtures import synthetic_documents
from satc.ingest import MapExtractor, StagingGate
from satc.models.mart import DataMart, DocumentRecord
from satc.persistence import SATCStore

# Status flow for a document in the repository.
DOC_FLOW = ["Requested", "Received", "Sent", "Signed", "N/A"]


@dataclass
class AppState:
    store: SATCStore = field(default_factory=lambda: SATCStore(os.environ.get("SATC_DATA_DIR")))
    mart: DataMart = field(default_factory=DataMart)
    names: dict[str, str] = field(default_factory=dict)
    gate: StagingGate = field(default_factory=StagingGate)

    def __post_init__(self) -> None:
        self.store.seed_if_empty()           # first run: populate from synthetic fixtures
        self.reload()
        # Build a per-session staging gate from the synthetic documents (working area).
        for doc in synthetic_documents():
            cfg = load_extraction_map(doc["doc_key"])
            self.gate.add(MapExtractor(cfg).extract(
                document_id=doc["document_id"], client_id="SATC-001000",
                tax_year=2024, labeled_fields=doc["labeled"]))

    def reload(self) -> None:
        self.mart = self.store.load_mart()
        self.names = self.store.names()

    # -- display helpers --------------------------------------------------
    def name(self, client_id: str) -> str:
        return self.names.get(client_id, client_id)

    def documents(self) -> list[DocumentRecord]:
        return self.mart.documents

    def outstanding(self) -> list[DocumentRecord]:
        return [d for d in self.mart.documents if d.status == "Requested"]

    def returns(self):
        return self.mart.returns

    def clients(self) -> list[str]:
        seen: list[str] = []
        for r in self.mart.returns:
            if r.client_id not in seen:
                seen.append(r.client_id)
        return seen

    # -- mutations (write through to the store) ---------------------------
    def set_document_status(self, document_id: str, status: str) -> None:
        if status not in DOC_FLOW:
            return
        self.store.set_document_status(document_id, status)   # durable
        for d in self.mart.documents:                          # keep view in sync
            if d.document_id == document_id:
                d.status = status

    def confirm_field(self, field_id: str) -> None:
        self.gate.confirm(field_id, by="preparer (UI)")

    def reject_field(self, field_id: str) -> None:
        self.gate.reject(field_id, by="preparer (UI)")

    def auto_confirm(self) -> int:
        return self.gate.auto_confirm_high(by="auto (UI)")

    # -- dashboard rollups ------------------------------------------------
    def pipeline_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.mart.returns:
            out[r.status] = out.get(r.status, 0) + 1
        return out

    def fees_total(self) -> float:
        return float(sum((e.fee_amount or 0) for e in self.mart.engagements))

    def fees_unpaid(self) -> float:
        return float(sum((e.fee_amount or 0) for e in self.mart.engagements if not e.paid))


STATE = AppState()
