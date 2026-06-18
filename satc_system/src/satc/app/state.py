"""In-memory application state for the SATC desktop/web prototype.

Loads the synthetic data mart, identity vault, and a staging gate so the GUI has
something real to drive. This is the vault-side UI — it runs inside the firm with
access to client identities, so it may show names; the workbook / data-mart
artifacts it produces remain de-identified.

A single process-wide AppState backs the prototype; swapping it for a real
database later is a contained change (the models are already SQL-shaped).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from satc.config import load_extraction_map
from satc.fixtures import synthetic_documents, synthetic_identities, synthetic_mart
from satc.ingest import MapExtractor, StagingGate
from satc.models.mart import DataMart, DocumentRecord

# Status flow for a document in the repository.
DOC_FLOW = ["Requested", "Received", "Sent", "Signed", "N/A"]


@dataclass
class AppState:
    mart: DataMart = field(default_factory=synthetic_mart)
    names: dict[str, str] = field(default_factory=dict)
    gate: StagingGate = field(default_factory=StagingGate)

    def __post_init__(self) -> None:
        # Vault-side: resolve client_id -> legal name for display.
        self.names = {r.client_id: r.legal_name for r in synthetic_identities()}
        # Build a demo staging gate from the synthetic documents.
        for doc in synthetic_documents():
            cfg = load_extraction_map(doc["doc_key"])
            self.gate.add(MapExtractor(cfg).extract(
                document_id=doc["document_id"], client_id="SATC-001000",
                tax_year=2024, labeled_fields=doc["labeled"]))

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

    # -- mutations --------------------------------------------------------
    def set_document_status(self, document_id: str, status: str) -> None:
        for d in self.mart.documents:
            if d.document_id == document_id and status in DOC_FLOW:
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
