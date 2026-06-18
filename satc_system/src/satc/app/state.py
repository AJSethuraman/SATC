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
from satc.ingest.readers import (
    OllamaVisionReader,
    PdfFormReader,
    TesseractOcrReader,
    TextAnchorReader,
    VisionDocumentReader,
)
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
    # The client/year the current intake is for — set when reading a client's folder,
    # so Staging → Post targets the right return (defaults to the demo client).
    intake_context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.store.seed_if_empty()           # first run: populate from synthetic fixtures
        # Layer the practice's in-app questionnaire edits over the built-in workflows.
        from satc.intake.workflows import set_override_provider
        set_override_provider(self.store.load_workflow_override)
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

    def public_client(self, client_id: str):
        """The de-identified projection for a client (or ``None``)."""
        return next((c for c in self.mart.public_clients if c.client_id == client_id), None)

    def client_email(self, client_id: str) -> str:
        """A client's contact email (from the vault) for pre-filling drafts."""
        return self.store.client_email(client_id)

    def filing_status(self, client_id: str) -> str:
        pc = self.public_client(client_id)
        return getattr(pc, "filing_status", "") if pc else ""

    def set_filing_status(self, client_id: str, filing_status: str) -> None:
        self.store.set_filing_status(client_id, filing_status)
        self.reload()

    # -- new vs returning client (drives the branched interview) ----------
    def is_returning(self, client_id: str) -> bool:
        """A client we've worked with before — prior engagement OR a return on file."""
        if any(e.client_id == client_id for e in self.store.load_intake_engagements()):
            return True
        return any(r.client_id == client_id for r in self.mart.returns)

    def prior_engagement(self, client_id: str, workflow_key: str = ""):
        """Most recent prior engagement for a client — preferring the same workflow.

        Used to pre-fill a returning client's interview with last year's answers.
        """
        engs = [e for e in self.store.load_intake_engagements() if e.client_id == client_id]
        if workflow_key:
            same = [e for e in engs if e.workflow_key == workflow_key]
            if same:
                return same[-1]
        return engs[-1] if engs else None

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

        from satc.intake import reconcile_received

        self.intake_context = {"client_id": client_id, "tax_year": tax_year}
        self.gate = StagingGate()          # fresh working area for this intake
        files_read = 0
        fields_staged = 0
        reconciled = 0
        notes: list[str] = []
        allow_cloud = cloud_vision_enabled()   # OFF unless the practice opts in
        classifier = load_classifier(has_key=allow_cloud)
        base = Path(folder)
        # Read the folder recursively so a sorted, by-type tree (W-2/…, 1099-INT/…)
        # reads just like a flat folder. Skip a nested _SATC_Sorted copy (avoids
        # reading both an original and its sorted duplicate) and hidden files.
        files = []
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                rel = p.relative_to(base).parts
                if p.is_file() and "_SATC_Sorted" not in rel and not any(s.startswith(".") for s in rel):
                    files.append(p)

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
                    if c.classified:   # close the loop: does this satisfy an open request?
                        matched = reconcile_received(self.store, client_id=client_id, doc_type=c.label)
                        if matched is not None:
                            reconciled += 1
                            notes.append(f"{doc_id} → ✓ satisfies your request “{matched.doc_type}” "
                                         f"— marked Received.")
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
        if reconciled:
            self.reload()              # refresh documents view with the new Received statuses
        self.intake_summary = {"folder": folder, "files_read": files_read,
                               "fields_staged": fields_staged, "reconciled": reconciled,
                               "notes": notes}
        return self.intake_summary

    @staticmethod
    def _read_document(fpath: Path, cfg: dict, allow_cloud: bool):
        """Read one document via the local-first reader ladder.

        Order: fillable form fields → text layer → local OCR (Tesseract) → local
        vision (Ollama) → cloud vision (opt-in only). Everything before the last
        rung runs entirely on the machine. Returns ``(ReadResult|None, problem)``.
        """
        from satc.settings import ocr_enabled, ollama_enabled

        try:
            if fpath.suffix.lower() == ".pdf":
                result = PdfFormReader(cfg).read(str(fpath))      # 1) fillable form fields (local)
                if result.labeled_fields:
                    return result, ""
                result = TextAnchorReader(cfg).read(str(fpath))   # 2) text layer (local)
                if result.labeled_fields:
                    return result, ""
            if ocr_enabled():                                     # 3) local OCR (Tesseract)
                result = TesseractOcrReader(cfg).read(str(fpath))
                if result.labeled_fields:
                    return result, ""
            if ollama_enabled():                                  # 4) local vision (Ollama)
                result = OllamaVisionReader(cfg).read(str(fpath))
                if result.labeled_fields:
                    return result, ""
            if allow_cloud:                                       # 5) cloud vision (opt-in only)
                return VisionDocumentReader(cfg).read(str(fpath)), ""
            return None, "scan with no text layer — enable local OCR (Tesseract) or key it in manually."
        except Exception as exc:        # noqa: BLE001 - surface, don't crash
            return None, f"could not read ({exc})."

    # -- sort + re-label a folder (non-destructive preview/apply) ----------
    def sort_folder(self, folder: str, *, apply: bool = False, client_id: str = "",
                    tax_year: str = "", dest: str = ""):
        """Classify and (optionally) copy a folder's files into a clean tree.

        When ``client_id`` + ``tax_year`` are given, the clean copies land in that
        client's year folder in the document library — which is then a
        ready-to-read Intake folder (``plan.dest``).
        """
        from satc.ingest import sort_folder as _sort
        from satc.ingest.client_library import client_year_folder
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        target = dest or None
        if not target and client_id and tax_year:
            target = str(client_year_folder(client_id, tax_year, self.name(client_id)))
        return _sort(folder, target, apply=apply, classifier=load_classifier(has_key=has_key))

    def client_choices(self) -> list[tuple[str, str]]:
        """(client_id, display name) for every known client — for pickers."""
        ids = {pc.client_id for pc in self.mart.public_clients} | set(self.names)
        return sorted(((cid, self.name(cid)) for cid in ids), key=lambda x: x[1])

    # -- the last hop: post confirmed intake onto the return + data mart ---
    def post_confirmed(self, *, client_id: str | None = None, tax_year: int | None = None,
                       return_type: str = "1040", jurisdiction: str = "US") -> dict:
        """Write the gate's CONFIRMED values onto the client's return as line items.

        Only confirmed fields flow (the gate already enforces that), projected onto
        1040 line ids with aggregation (every W-2 box 1 summed into wages, etc.).
        The return is created if it doesn't exist; re-posting is idempotent.
        """
        client_id = client_id or self.intake_context.get("client_id") or "SATC-001000"
        tax_year = tax_year or self.intake_context.get("tax_year") or 2024
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

    # -- client intake & engagement workflows -----------------------------
    def intake_engagements(self) -> list:
        """All generated engagements (workflow instances), newest first."""
        return list(reversed(self.store.load_intake_engagements()))

    def engagement(self, engagement_id: str):
        return next((e for e in self.store.load_intake_engagements()
                     if e.engagement_id == engagement_id), None)

    def relationships(self) -> list:
        return self.store.load_relationships()

    def create_person_client(self, **kw) -> str:
        from satc.intake import create_person_client
        cid = create_person_client(self.store, **kw)
        self.reload()
        return cid

    def create_business_client(self, **kw) -> str:
        from satc.intake import create_business_client
        cid = create_business_client(self.store, **kw)
        self.reload()
        return cid

    def add_relationship(self, **kw):
        from satc.intake import add_relationship
        return add_relationship(self.store, **kw)

    def create_engagement(self, **kw):
        from satc.intake import create_engagement
        eng = create_engagement(self.store, **kw)
        self.reload()
        return eng

    def set_task_completed(self, task_id: str, completed: bool = True) -> None:
        """Mark an engagement task done/undone (durable)."""
        for eng in self.store.load_intake_engagements():
            for task in eng.tasks:
                if task.task_id == task_id:
                    task.completed = completed
                    self.store.save_task(task)
                    return

    def workflow_catalog(self) -> dict[str, list]:
        """Workflows offered per client type, for the intake screens."""
        from satc.intake.workflows import workflows_for_client_type
        return {ct: workflows_for_client_type(ct) for ct in ("person", "business")}

    # -- bulk client import (CSV / spreadsheet / Drake export) ------------
    def preview_client_import(self, *, csv_text: str | None = None, rows: list[dict] | None = None):
        """Parse a roster into previewed clients (new / duplicate / review)."""
        from satc.intake.service import preview_import
        return preview_import(self.store, csv_text=csv_text, rows=rows)

    def commit_client_import(self, parsed, *, include_duplicates: bool = False) -> list[str]:
        from satc.intake.service import commit_import
        ids = commit_import(self.store, parsed, include_duplicates=include_duplicates)
        self.reload()
        return ids

    def add_client_smart(self, **fields):
        """Smart single-add: detect person/business + normalize, then create."""
        from satc.intake import importer
        from satc.intake.service import commit_import
        parsed = importer.parse_one(**fields)
        ids = commit_import(self.store, [parsed], include_duplicates=True)
        self.reload()
        return (ids[0] if ids else None), parsed

    # -- questionnaire customization --------------------------------------
    def all_workflows(self) -> list:
        from satc.intake.workflows import list_workflows
        return list_workflows()

    def base_workflow(self, key: str):
        """The built-in workflow WITHOUT overrides (for showing originals in the editor)."""
        from satc.intake import workflows as wf
        provider, wf._OVERRIDE_PROVIDER = wf._OVERRIDE_PROVIDER, None
        try:
            return wf.load_workflow(key)
        finally:
            wf._OVERRIDE_PROVIDER = provider

    def workflow_override(self, key: str) -> dict:
        return self.store.load_workflow_override(key) or {}

    def save_workflow_override(self, key: str, data: dict) -> None:
        self.store.save_workflow_override(key, data)

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
