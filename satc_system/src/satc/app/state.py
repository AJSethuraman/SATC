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
from pathlib import Path

from satc.config import load_extraction_map
from satc.fixtures import synthetic_documents
from satc.ids import return_key
from satc.ingest import (
    MAPPING_1040,
    MapExtractor,
    StagingGate,
    load_classifier,
    split_to_dir,
)
from satc.ingest.readers import PdfFormReader, TextAnchorReader, VisionDocumentReader
from satc.models.mart import DataMart, DocumentRecord, ReturnRecord
from satc.persistence import SATCStore
from satc.settings import cloud_vision_enabled

# Status flow for a document in the repository.
DOC_FLOW = ["Requested", "Received", "Sent", "Signed", "N/A"]

# Friendly names for the reader backends (shown in intake notes).
_READER_LABELS = {
    "PdfFormReader": "fillable form fields (free)",
    "TextAnchorReader": "text layer (free)",
}


@dataclass
class AppState:
    store: SATCStore = field(default_factory=lambda: SATCStore(os.environ.get("SATC_DATA_DIR")))
    mart: DataMart = field(default_factory=DataMart)
    names: dict[str, str] = field(default_factory=dict)
    gate: StagingGate = field(default_factory=StagingGate)
    intake_summary: dict = field(default_factory=dict)
    posted_summary: dict = field(default_factory=dict)

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

    # -- intake: actually read the files in a folder ----------------------
    def run_intake(self, folder: str, *, client_id: str = "SATC-001000",
                   tax_year: int = 2024) -> dict:
        """Read every file in ``folder`` and stage the values. Returns a summary.

        Each file is classified by *content* — not its name — so a W-2 named
        ``scan001.pdf`` is still recognized. A combined multi-form PDF is split into
        its parts first, and each document is read by the cheapest sufficient
        backend: fillable form fields, then the free text layer, then vision.
        """
        import tempfile

        self.gate = StagingGate()          # fresh working area for this intake
        files_read = 0
        fields_staged = 0
        notes: list[str] = []
        allow_cloud = cloud_vision_enabled()   # OFF unless the practice opts in
        classifier = load_classifier(has_key=allow_cloud)
        base = Path(folder)
        files = sorted(p for p in base.iterdir() if p.is_file()) if base.is_dir() else []

        with tempfile.TemporaryDirectory() as tmp:
            for path in files:
                parts = split_to_dir(path, tmp, classifier) if path.suffix.lower() == ".pdf" else []
                if parts:
                    notes.append(f"{path.name}: combined PDF — split into {len(parts)} documents.")
                    docs = [(c, fp, f"{path.name} ▸ part {i} · {c.label}")
                            for i, (c, fp) in enumerate(parts, start=1)]
                else:
                    c = classifier.classify_path(path)
                    docs = [(c, path, path.name)]

                for c, fpath, doc_id in docs:
                    how = f"detected by {c.method}" if c.classified else "could not identify"
                    if not c.extractable:
                        what = c.label if c.classified else "unrecognized document"
                        notes.append(f"{doc_id} → {what} ({how}): filed, not extracted.")
                        continue
                    cfg = load_extraction_map(c.key)
                    result, problem = self._read_document(fpath, cfg, allow_cloud)
                    if result is None:
                        notes.append(f"{doc_id} → {c.label} ({how}): {problem}")
                        continue
                    staged = MapExtractor(cfg).extract(
                        document_id=doc_id, client_id=client_id, tax_year=tax_year,
                        labeled_fields=result.labeled_fields, confidences=result.confidence_map())
                    self.gate.add(staged)
                    files_read += 1
                    fields_staged += len(staged.fields)
                    via = _READER_LABELS.get(result.backend, result.backend)
                    notes.append(f"{doc_id} → {c.label} ({how}): staged "
                                 f"{len(staged.fields)} fields via {via}.")

        self.gate.auto_confirm_high(by="auto (intake)")
        self.intake_summary = {"folder": folder, "files_read": files_read,
                               "fields_staged": fields_staged, "notes": notes}
        return self.intake_summary

    @staticmethod
    def _read_document(fpath: Path, cfg: dict, allow_cloud: bool):
        """Read one document via the local-first reader ladder.

        Returns ``(ReadResult|None, problem)``. The cloud vision rung runs only when
        the practice has explicitly opted in (``allow_cloud``); otherwise a scan is
        left for local OCR / manual entry and nothing leaves the machine.
        """
        try:
            if fpath.suffix.lower() == ".pdf":
                result = PdfFormReader(cfg).read(str(fpath))      # 1) fillable form fields (local)
                if result.labeled_fields:
                    return result, ""
                result = TextAnchorReader(cfg).read(str(fpath))   # 2) text layer (local)
                if result.labeled_fields:
                    return result, ""
                if allow_cloud:                                   # 3) cloud vision (opt-in only)
                    return VisionDocumentReader(cfg).read(str(fpath)), ""
                return None, "looks like a scan (no form fields or text) — needs local OCR or manual entry."
            if allow_cloud:
                return VisionDocumentReader(cfg).read(str(fpath)), ""
            return None, "image scan — needs local OCR or manual entry (cloud vision is off)."
        except Exception as exc:        # noqa: BLE001 - surface, don't crash
            return None, f"could not read ({exc})."

    # -- sort + re-label a folder (non-destructive preview/apply) ----------
    def sort_folder(self, folder: str, *, apply: bool = False):
        """Classify and (optionally) copy a folder's files into a clean tree."""
        from satc.ingest import sort_folder as _sort
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        return _sort(folder, apply=apply, classifier=load_classifier(has_key=has_key))

    # -- the last hop: post confirmed intake onto the return + data mart ---
    def post_confirmed(self, *, client_id: str = "SATC-001000", tax_year: int = 2024,
                       return_type: str = "1040", jurisdiction: str = "US") -> dict:
        """Write the gate's CONFIRMED values onto the client's return as line items.

        Only confirmed fields flow (the gate already enforces that), projected onto
        1040 line ids with aggregation (every W-2 box 1 summed into wages, etc.).
        The return is created if it doesn't exist; re-posting is idempotent.
        """
        rk = return_key(client_id, tax_year, return_type, jurisdiction)
        ret = next((r for r in self.mart.returns if r.return_key == rk), None)
        if ret is None:
            ret = ReturnRecord(return_key=rk, client_id=client_id, tax_year=tax_year,
                               return_type=return_type, jurisdiction=jurisdiction, status="In prep")
            self.mart.returns.append(ret)

        items = self.gate.to_line_items(rk, MAPPING_1040)
        keys = {li.line_item_key for li in items}
        # Replace any prior intake posting for these lines (idempotent re-post).
        self.mart.line_items = [li for li in self.mart.line_items if li.line_item_key not in keys]
        self.mart.line_items.extend(items)

        self.store.save_mart(self.mart)
        self.reload()
        self.posted_summary = {"return_key": rk, "posted": len(items),
                               "lines": [(li.label, float(li.amount) if li.amount is not None
                                          else li.text_value) for li in items]}
        return self.posted_summary

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
